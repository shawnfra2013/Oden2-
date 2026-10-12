import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.home() / "odin-workspace"
PATCH = ROOT / "state" / "agent-proposal.diff"
MODEL = "openai/gpt-oss-120b"
API = "https://api.groq.com/openai/v1/chat/completions"


def run(*args):
    return subprocess.run(
        args, cwd=ROOT, text=True, capture_output=True
    , check=False)


def main():
    if len(sys.argv) < 2:
        print('Usage: python ai/agent/repair.py "describe the fix"')
        return 1

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print("ERROR: GROQ_API_KEY missing")
        return 1

    if not ROOT.is_dir() or not (ROOT / ".git").exists():
        print("ERROR: Odin Git repository missing")
        return 1

    # Do not modify a repository with existing tracked changes.
    if run("git", "diff", "--quiet").returncode != 0:
        print("STOP: Uncommitted tracked changes exist.")
        return 1

    if run("git", "diff", "--cached", "--quiet").returncode != 0:
        print("STOP: Staged changes exist.")
        return 1

    if run("git", "branch", "--show-current").stdout.strip() != "main":
        print("STOP: Expected main branch.")
        return 1

    tracked = run("git", "ls-files")
    if tracked.returncode:
        print("ERROR: Cannot list repository files.")
        return 1

    files = []
    for name in tracked.stdout.splitlines():
        path = ROOT / name
        if (
            path.is_file()
            and path.suffix in {".py", ".sh", ".md", ".yml", ".yaml"}
            and path.stat().st_size < 20000
        ):
            files.append(f"FILE: {name}\n{path.read_text(errors='replace')}")

    task = " ".join(sys.argv[1:])

    prompt = (
        "You are a code repair agent. Return ONLY a valid unified "
        "Git diff starting with 'diff --git'. No Markdown fences. "
        "Modify existing tracked files only. Do not delete files, "
        "change secrets, GitHub workflows, security protections, "
        "or service startup files. Keep changes minimal. "
        "Do not include credentials. If no safe change is possible, "
        "reply NO_SAFE_PATCH.\n\n"
        "TASK:\n" + task + "\n\nREPOSITORY:\n"
        + "\n\n".join(files)[:45000]
    )

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 4096,
        "stream": False
    })

    # Temporary request file is private and removed afterward.
    with tempfile.TemporaryDirectory(prefix="odin-agent-") as tmp:
        request_file = Path(tmp) / "request.json"
        request_file.write_text(payload)
        request_file.chmod(0o600)

        # Pass credentials via stdin, not command-line arguments.
        if any(c in key for c in '\r\n"\\'):
            print("ERROR: Invalid key format")
            return 1

        config = (
            'silent\nshow-error\nfail\n'
            'max-time = 120\n'
            'request = "POST"\n'
            f'url = "{API}"\n'
            f'header = "Authorization: Bearer {key}"\n'
            'header = "Content-Type: application/json"\n'
            f'data-binary = "@{request_file}"\n'
        )

        result = subprocess.run(
            ["curl", "--config", "-"],
            input=config,
            text=True,
            capture_output=True
        , check=False)

    if result.returncode:
        print("ERROR: Groq request failed.")
        print("curl exit:", result.returncode)
        return 1

    try:
        data = json.loads(result.stdout)
        answer = data["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError):
        print("ERROR: Unexpected Groq response")
        return 1

    if answer == "NO_SAFE_PATCH":
        print("Agent could not produce a safe patch.")
        return 0

    if answer.startswith("```"):
        answer = re.sub(r"^```[^\n]*\n", "", answer)
        answer = re.sub(r"\n```$", "", answer)

    if not answer.startswith("diff --git "):
        print("REJECTED: Agent did not return a valid Git diff.")
        print(answer[:1500])
        return 1

    if re.search(
        r"gsk_[A-Za-z0-9_-]{20,}|"
        r"ghp_[A-Za-z0-9]+|"
        r"github_pat_[A-Za-z0-9_]+|"
        r"BEGIN [A-Z ]*PRIVATE KEY",
        answer
    ):
        print("REJECTED: Possible secret in patch")
        return 1

    PATCH.parent.mkdir(parents=True, exist_ok=True)
    PATCH.write_text(answer.rstrip() + "\n")
    PATCH.chmod(0o600)

    check = run("git", "apply", "--check", str(PATCH))
    if check.returncode:
        print("REJECTED: Patch failed Git validation.")
        print(check.stderr[:1500])
        return 1

    paths = run("git", "apply", "--numstat", str(PATCH))
    tracked_names = set(tracked.stdout.splitlines())

    if paths.returncode:
        print("REJECTED: Cannot inspect patch paths.")
        return 1

    for line in paths.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            print("REJECTED: Invalid patch entry")
            return 1
        name = parts[2]
        if (
            name not in tracked_names
            or not name.startswith(("ai/", "docs/", "scripts/", "tests/"))
            or name.startswith(("services/", "boot/"))
            or name == "scripts/git-sync.sh"
            or name.endswith((".yml", ".yaml"))
        ):
            print("REJECTED: Protected or untracked path:", name)
            return 1

    print("\n=== PROPOSED PATCH ===\n")
    print(answer[:25000])

    approval = input("\nApply this patch? Type APPLY: ").strip()
    if approval != "APPLY":
        print("CANCELLED: No changes applied.")
        return 0

    applied = run("git", "apply", str(PATCH))
    if applied.returncode:
        print("ERROR: Patch application failed.")
        return 1

    print("\n=== VERIFY ===")

    failed = False
    for name in tracked_names:
        path = ROOT / name
        if not path.is_file():
            continue
        if name.endswith(".py"):
            test = subprocess.run(
                ["python", "-c",
                 "import ast,sys; ast.parse(open(sys.argv[1]).read())",
                 str(path)],
                capture_output=True, text=True
            , check=False)
        elif name.endswith(".sh"):
            test = subprocess.run(
                ["bash", "-n", str(path)],
                capture_output=True, text=True
            , check=False)
        else:
            continue

        if test.returncode:
            print("FAILED:", name)
            failed = True

    if failed:
        reverse = run("git", "apply", "-R", str(PATCH))
        print("SYNTAX FAILED. Rollback:",
              "SUCCESS" if reverse.returncode == 0 else "FAILED")
        return 1

    print("SYNTAX CHECKS: PASS")
    print("Changes are local only. No commit or push performed.")
    print("Review with: git diff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
