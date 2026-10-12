import subprocess
from pathlib import Path

ROOT = Path.home() / "odin-workspace"
AGENT = ROOT / "ai/agent/agent.py"

def main():
    history = []
    print("ODIN AI | GPT-OSS 120B")
    print("Type exit to quit.\n")

    while True:
        try:
            question = input("odin > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if question.lower() in ("exit", "quit"):
            break

        if not question:
            continue

        context = "\n".join(history[-8:])
        task = (
            "Previous conversation:\n" + context
            + "\n\nCurrent request:\n" + question
        )

        result = subprocess.run(
            ["python", str(AGENT), task],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False
        )

        if result.returncode:
            print("Agent error:", result.stderr[:500])
            continue

        answer = result.stdout.strip()
        print("\n" + answer + "\n")

        history.append("USER: " + question)
        history.append("ASSISTANT: " + answer)

if __name__ == "__main__":
    main()
