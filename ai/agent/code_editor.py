import ast
import difflib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.home() / "odin-workspace"
MODEL = "openai/gpt-oss-120b"
API = "https://api.groq.com/openai/v1/chat/completions"


def run(args, **kwargs):
    return subprocess.run(
        args, cwd=ROOT, capture_output=True,
        text=True, check=False, **kwargs
    )


def validate(text, suffix):
    if suffix == ".py":
        try:
            ast.parse(text)
            return True, "Python syntax valid"
        except SyntaxError as exc:
            return False, str(exc)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", delete=True
    ) as temp:
        temp.write(text)
        temp.flush()
        result = run(["bash", "-n", temp.name])
        return result.returncode == 0, result.stderr


def main():
    if len(sys.argv) < 3:
        print('Usage: python ai/agent/code_editor.py FILE "TASK"')
        return 1

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print("ERROR: Groq key missing")
        return 1

    filename = sys.argv[1]
    task = " ".join(sys.argv[2:])

    tracked = run(["git", "ls-files", "--", filename])
    if tracked.returncode or filename not in tracked.stdout.splitlines():
        print("STOP: Target must be tracked by Git")
        return 1

    if not filename.startswith(("ai/", "tests/")):
        print("STOP: Only AI and test modules are editable initially")
        return 1

    path = ROOT / filename
    if path.suffix not in (".py", ".sh"):
        print("STOP: Only Python and Bash supported")
        return 1

    if path.is_symlink() or not path.is_file():
        print("STOP: Invalid target")
        return 1

    if not path.resolve().is_relative_to(ROOT.resolve()):
        print("STOP: Path outside repository")
        return 1

    status = run(["git", "status", "--porcelain"])
    if status.returncode or status.stdout.strip():
        print("STOP: Repository has pending changes")
        return 1

    original = path.read_text()
    if len(original) > 30000:
        print("STOP: File too large")
        return 1

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert Python and Bash coding agent. "
                    "Return only the COMPLETE replacement source file. "
                    "No Markdown fences or explanations. "
                    "Preserve existing functionality and interfaces. "
                    "Do not add destructive commands or secret access."
                )
            },
            {
                "role": "user",
                "content": (
                    f"FILE: {filename}\nTASK: {task}\n"
                    f"ORIGINAL SOURCE:\n{original}"
                )
            }
        ],
        "max_completion_tokens": 8192,
        "stream": False
    })

    with tempfile.TemporaryDirectory() as tempdir:
        request = Path(tempdir) / "request.json"
        request.write_text(payload)
        request.chmod(0o600)

        # Keep the API key out of process arguments.
        config = "\n".join([
            "silent",
            "show-error",
            "fail",
            "max-time = 120",
            'request = "POST"',
            f'url = "{API}"',
            f'header = "Authorization: Bearer {key}"',
            'header = "Content-Type: application/json"',
            f'data-binary = "@{request}"'
        ])

        if any(c in key for c in '\r\n"\\'):
            print("STOP: Invalid API key format")
            return 1

        response = run(
            ["curl", "--config", "-"],
            input=config
        )

    if response.returncode:
        print("ERROR: API request failed")
        return 1

    try:
        new = json.loads(response.stdout)[
            "choices"
        ][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        print("ERROR: Invalid AI response")
        return 1

    if not isinstance(new, str):
        print("ERROR: Missing source code")
        return 1

    new = new.strip() + "\n"

    if new.startswith("```") or len(new) > 60000:
        print("REJECTED: Unexpected response format")
        return 1

    valid, reason = validate(new, path.suffix)

    if not valid:
        print("REJECTED: Syntax validation failed")
        print(reason)
        return 1

    if new == original:
        print("No changes needed")
        return 0

    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile="a/" + filename,
        tofile="b/" + filename
    ))

    print("=== PROPOSED CHANGES ===")
    print(diff[:30000])
    print("=== SYNTAX: PASS ===")

    approval = input("Type APPLY to approve: ").strip()
    if approval != "APPLY":
        print("CANCELLED")
        return 0

    if path.read_text() != original:
        print("STOP: Original file changed")
        return 1

    if run(["git", "status", "--porcelain"]).stdout.strip():
        print("STOP: Repository changed during review")
        return 1

    path.write_text(new)

    if path.suffix == ".py":
        result = run(["ruff", "check", filename])
        if result.returncode:
            path.write_text(original)
            print("RUFF FAILED — ORIGINAL RESTORED")
            print(result.stdout[:2000])
            return 1

    result = run(["git", "diff", "--check", "--", filename])
    if result.returncode:
        path.write_text(original)
        print("DIFF CHECK FAILED — ORIGINAL RESTORED")
        return 1

    print("APPLIED AND LOCALLY VALIDATED")
    print("NOT COMMITTED OR PUSHED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
