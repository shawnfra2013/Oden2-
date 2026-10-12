import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "odin-workspace"
TARGET = "docs/architecture.md"
MODEL = "openai/gpt-oss-120b"

def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT,
        capture_output=True, text=True
    , check=False)

def main():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print("ERROR: Groq key missing")
        return 1

    if git("status", "--porcelain").stdout.strip() not in (
        "?? ai/",
        ""
    ):
        print("STOP: Unexpected repository changes")
        return 1

    path = ROOT / TARGET
    if not path.is_file() or path.is_symlink():
        print("STOP: Target missing or unsafe")
        return 1

    original = path.read_text()
    task = " ".join(sys.argv[1:]) or "Improve clarity."

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You edit Markdown documents. Return ONLY "
                    "the complete replacement Markdown document. "
                    "No code fences, explanations, or patches. "
                    "Preserve verified facts. Do not invent features."
                )
            },
            {
                "role": "user",
                "content": (
                    f"TASK: {task}\n\n"
                    f"CURRENT DOCUMENT:\n{original}"
                )
            }
        ],
        "max_completion_tokens": 4096
    })

    result = subprocess.run(
        [
            "curl", "-fsS", "--max-time", "90",
            "https://api.groq.com/openai/v1/chat/completions",
            "-H", "Authorization: Bearer " + key,
            "-H", "Content-Type: application/json",
            "--data-binary", "@-"
        ],
        input=payload, text=True, capture_output=True
    , check=False)

    if result.returncode:
        print("ERROR: Groq request failed")
        return 1

    try:
        replacement = json.loads(result.stdout)[
            "choices"
        ][0]["message"]["content"].strip() + "\n"
    except (ValueError, KeyError, IndexError, TypeError):
        print("ERROR: Invalid model response")
        return 1

    if (
        not replacement.startswith("# ")
        or replacement.startswith("```")
        or len(replacement) < 100
        or len(replacement) > 20000
    ):
        print("REJECTED: Unexpected document format")
        return 1

    patch = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        replacement.splitlines(keepends=True),
        fromfile="a/" + TARGET,
        tofile="b/" + TARGET
    ))

    if not patch:
        print("No changes needed.")
        return 0

    state = ROOT / "state"
    state.mkdir(exist_ok=True)
    proposal = state / "architecture-proposal.diff"
    proposal.write_text(patch)
    proposal.chmod(0o600)

    check = git("apply", "--check", str(proposal))
    if check.returncode:
        print("REJECTED:", check.stderr)
        return 1

    print("\n=== VALIDATED PROPOSAL ===\n")
    print(patch[:20000])

    print("\nNo changes applied.")
    approval = input("Type APPLY to accept, or Enter to cancel: ")

    if approval != "APPLY":
        print("CANCELLED")
        return 0

    if path.read_text() != original:
        print("STOP: File changed during review")
        return 1

    applied = git("apply", str(proposal))
    if applied.returncode:
        print("ERROR:", applied.stderr)
        return 1

    print("APPLIED LOCALLY — NOT COMMITTED OR PUSHED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
