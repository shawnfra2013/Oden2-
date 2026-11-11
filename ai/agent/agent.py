import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path.home() / "odin-workspace"
MODEL = "openai/gpt-oss-120b"
API = "https://api.groq.com/openai/v1/chat/completions"

def ask(question):
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing")

    files = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True
    ).stdout.splitlines()

    context = []
    for name in files:
        path = ROOT / name
        if (
            path.is_file()
            and path.stat().st_size < 30000
            and path.suffix in (".py", ".sh", ".md", ".yml", ".yaml")
        ):
            context.append(
                f"FILE: {name}\n{path.read_text(errors='replace')}"
            )

    messages = [
        {
            "role": "system",
            "content": (
                "You are Odin Agent, a coding assistant for an AYN Odin 2 "
                "running Termux. Analyze the supplied repository files. "
                "Never claim to have executed commands or changed files. "
                "Explain precise fixes. Preserve existing working systems. "
                "Do not expose secrets."
            )
        },
        {
            "role": "user",
            "content": (
                "\n\n".join(context)[:40000]
                + "\n\nUSER TASK:\n"
                + question
            )
        }
    ]

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": 2048,
        "stream": False
    })

    if any(ch in key for ch in '\r\n"\\'):
        raise RuntimeError("GROQ_API_KEY contains unsupported characters")

    import tempfile

    with tempfile.TemporaryDirectory(prefix="odin-cli-") as directory:
        body = Path(directory) / "request.json"
        body.touch(mode=0o600, exist_ok=False)
        body.write_text(payload, encoding="utf-8")

        config = "\n".join([
            "silent",
            "show-error",
            "fail",
            "max-time = 90",
            'request = "POST"',
            f'url = "{API}"',
            f'header = "Authorization: Bearer {key}"',
            'header = "Content-Type: application/json"',
            f'data-binary = "@{body}"',
        ]) + "\n"

        result = subprocess.run(
            ["curl", "--config", "-"],
            input=config,
            text=True,
            capture_output=True,
            timeout=100,
            check=False,
        )

    if result.returncode:
        raise RuntimeError(
            f"Groq request failed (curl exit {result.returncode})"
        )

    response = json.loads(result.stdout)

    if "error" in response:
        raise RuntimeError("Groq returned an API error")

    print(response["choices"][0]["message"]["content"])

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python agent.py "your task"')
        sys.exit(1)

    ask(" ".join(sys.argv[1:]))
