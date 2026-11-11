import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__:
    from . import pipeline
else:
    import pipeline

ROOT = Path.home() / "odin-workspace"
API = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
ROLES = {"research", "coder", "reviewer", "tester", "device"}


def command(args):
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )


def ask(messages, tokens=1400):
    key = os.environ.get("GROQ_API_KEY", "").strip()

    if not key or any(c in key for c in '\r\n"\\'):
        raise RuntimeError("Groq key missing or malformed")

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_completion_tokens": tokens,
        "reasoning_effort": "low",
        "stream": False,
    })

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "request.json"
        source.write_text(payload)
        source.chmod(0o600)

        config = "\n".join([
            "silent",
            "show-error",
            "fail",
            "max-time = 90",
            'request = "POST"',
            f'url = "{API}"',
            f'header = "Authorization: Bearer {key}"',
            'header = "Content-Type: application/json"',
            f'data-binary = "@{source}"',
        ])

        import time

        for attempt in range(3):
            response = subprocess.run(
                ["curl", "--config", "-"],
                input=config,
                text=True,
                capture_output=True,
                check=False,
                timeout=100,
            )

            if response.returncode == 0:
                try:
                    data = json.loads(response.stdout)
                except ValueError as exc:
                    raise RuntimeError(
                        "Groq returned invalid JSON"
                    ) from exc

                if not isinstance(data, dict):
                    raise RuntimeError("Groq response must be an object")
                if data.get("choices"):
                    break

                error = data.get("error", {})
                error = error if isinstance(error, dict) else {}
                raise RuntimeError(
                    "Groq API error: "
                    + str(error.get("code") or error.get("type") or "unknown")
                )

            if response.returncode != 22 or attempt == 2:
                raise RuntimeError(
                    f"Groq request failed: curl exit {response.returncode}"
                )

            time.sleep(2 ** attempt)
        else:
            raise RuntimeError("Groq retries exhausted")

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("Invalid Groq choices")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise TypeError("Invalid Groq message")
    content = message["content"]
    if not content.strip():
        usage = data.get("usage", {})
        usage = usage if isinstance(usage, dict) else {}
        print("MODEL FINISH:", choice.get("finish_reason"))
        print("COMPLETION TOKENS:", usage.get("completion_tokens"))
        print(
            "REASONING TOKENS:",
            "unavailable",
        )
        raise RuntimeError("Groq returned empty content")
    return content


def tracked_files():
    result = command(["git", "ls-files"])

    if result.returncode:
        raise RuntimeError("Git file inventory unavailable")

    return result.stdout.splitlines()



def execution_result(arg):
    import shlex

    allowed = {
        ("pwd",),
        ("ls", "-la"),
        ("git", "status"),
        ("git", "status", "--short"),
        ("git", "diff", "--check"),
        ("git", "ls-files"),
        ("git", "log", "-3", "--oneline"),
        ("ruff", "check", "ai/agent/"),
        ("python", "-m", "compileall", "-q", "ai/agent"),
        ("adb", "devices"),
    }

    try:
        argv = shlex.split(arg)
    except ValueError:
        return {"argv": [], "returncode": None, "error": "invalid_command", "stdout": "", "stderr": ""}

    if tuple(argv) not in allowed:
        return {"argv": argv, "returncode": None, "error": "denied", "stdout": "", "stderr": ""}

    try:
        result = subprocess.run(
            argv,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": argv, "returncode": None, "error": type(exc).__name__, "stdout": "", "stderr": ""}

    return {"argv": argv, "returncode": result.returncode, "error": None,
            "stdout": result.stdout[:5000], "stderr": result.stderr[:2000]}


def execute_safe(arg):
    return json.dumps(execution_result(arg), ensure_ascii=True)


def tool(action, arg):
    if action == "exec":
        return execute_safe(arg)

    if action == "status":
        return command(["git", "status", "--short"]).stdout[:3000]

    if action == "list":
        return "\n".join(tracked_files())[:6000]

    if action == "read":
        if (
            arg not in tracked_files()
            or not arg.endswith(
                (".py", ".sh", ".md", ".yaml", ".yml")
            )
        ):
            return "DENIED: Not an allowed tracked text file"

        path = ROOT / arg

        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(ROOT.resolve())
        ):
            return "DENIED: Unsafe file"

        return path.read_text(errors="replace")[:12000]

    if action == "checks":
        result = command(["ruff", "check", "ai/agent/"])
        return (
            f"Ruff exit={result.returncode}\n"
            f"{(result.stdout + result.stderr)[:3000]}"
        )

    if action == "device":
        result = command(["adb", "devices"])
        return (
            f"ADB exit={result.returncode}\n"
            f"{result.stdout[:2000]}"
        )

    if action == "delegate":
        role, _, task = arg.partition(":")

        if role.strip() not in ROLES or not task.strip():
            return "DENIED: Invalid specialist or task"

        inventory = tracked_files()
        context = []

        for name in inventory:
            path = ROOT / name
            if (
                path.is_file()
                and not path.is_symlink()
                and path.suffix in {".py", ".sh", ".md", ".yml", ".yaml"}
                and path.stat().st_size <= 12000
            ):
                context.append(
                    f"FILE: {name}\\n"
                    f"{path.read_text(errors='replace')}"
                )

        result = ask([
            {
                "role": "system",
                "content": (
                    f"You are the {role.strip()} specialist "
                    "for Odin 2. Analyze supplied repository evidence. "
                    "Distinguish verified facts from recommendations. "
                    "Never claim to have executed commands."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TASK:\\n{task[:3000]}\\n\\n"
                    f"REPOSITORY:\\n{chr(10).join(context)[:24000]}"
                ),
            },
        ], tokens=3000)

        return result[:5500]

    return "DENIED: Unknown tool"


SYSTEM = """
You are the Odin 2 multi-agent orchestrator.

Choose tools, inspect their results, delegate work to
specialists, and answer the user's request.

Respond as ONE JSON object only:

{
 "action": "status|list|read|checks|device|delegate|exec|finish",
 "arg": "",
 "answer": ""
}

For delegate, use arg formatted as role:task.

Specialist roles:
research, coder, reviewer, tester, device.

When finished, set action to finish and put your
final response in answer.

You have at most six tool calls per request.

Never claim changes were executed unless a tool
explicitly verifies them.

Use exec for allowlisted commands only. No arbitrary shell commands, installations, file edits,
Git commits, or pushes are permitted.
"""




def task_session_path(task_id=None):
    """Return the interactive or task-owned checkpoint path."""
    if task_id is None:
        return ROOT / "state" / "odin-agent-session.json"

    if not isinstance(task_id, str):
        raise TypeError("task_id must be a string")

    if (
        len(task_id) != 12
        or any(
            char not in "0123456789abcdef"
            for char in task_id
        )
    ):
        raise ValueError("Invalid task_id")

    return (
        ROOT
        / "state"
        / "task-sessions"
        / f"{task_id}.json"
    )


def checkpoint(messages, step, status, task_id=None, evidence=None):
    target = task_session_path(task_id)
    data = {"schema": 1, "task_id": task_id, "step": step, "status": status,
            "messages": messages, "execution": evidence or []}
    pipeline.publish(ROOT, target.relative_to(ROOT).parts, pipeline.json_bytes(data), replace=True)



def bridge_event(event):
    """Report lifecycle metadata without sending prompts or credentials."""
    allowed = {
        "task-started", "task-progress",
        "task-completed", "task-failed",
    }
    if event not in allowed:
        return
    reporter = Path.home() / ".local/libexec/odin-bridge-event"
    if not reporter.is_file():
        return
    try:
        with open(ROOT / "logs" / "bridge-events.log", "a") as log:
            subprocess.Popen(
                [str(reporter), event],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError:
        pass



def respond(question, task_id=None):
    state = task_session_path(task_id)
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Invalid question")
    if question.lower() == "resume":
        if task_id is not None:
            raise ValueError("Queued tasks cannot use interactive resume")
        saved = json.loads(pipeline.read(ROOT, state.relative_to(ROOT).parts, 300000))
        if not isinstance(saved, dict) or saved.get("task_id") is not None:
            raise ValueError("Invalid interactive checkpoint")
        if saved.get("status") in {"complete", "unverified"}:
            print("Previous conversation finished; outcome requires review.")
            return
        messages, start = saved["messages"], saved["step"]
        evidence = saved.get("execution", [])
        if not isinstance(messages, list) or not isinstance(evidence, list) or type(start) is not int:
            raise ValueError("Invalid checkpoint fields")
    else:
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
        start, evidence = 0, []
        bridge_event("task-started")
    aliases = {"status": "git status --short", "checks": "ruff check ai/agent/", "device": "adb devices"}
    for number in range(start, 6):
        checkpoint(messages, number, "running", task_id, evidence)
        raw = ask(messages, tokens=3000)
        if not isinstance(raw, str):
            raise TypeError("Model response must be text")
        cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
        instruction = json.loads(cleaned)
        if not isinstance(instruction, dict):
            raise TypeError("Model instruction must be an object")
        action = instruction.get("action")
        if not isinstance(action, str) or action not in {"finish", "exec", "status", "checks", "device", "list", "read", "delegate"}:
            raise ValueError("Invalid model action")
        if action == "finish":
            import re

            answer = instruction.get("answer")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Empty final answer")
            checkpoint(messages, number, "unverified", task_id, evidence)
            failed = any(e.get("error") is not None or e.get("returncode") != 0 for e in evidence)
            request = next((str(m.get("content", "")) for m in messages if m.get("role") == "user"), question)
            write_verbs = r"propose|create|write|modify|edit|install|apply|delete|commit|push|generate|implement|save|repair|fix"
            negated = re.sub(
                rf"\b(?:do not|don't|never)\s+(?:{write_verbs})\b",
                "",
                request,
                flags=re.IGNORECASE,
            )
            write_requested = re.search(
                rf"\b(?:{write_verbs})\b",
                negated,
                re.IGNORECASE,
            )
            if write_requested:
                print("UNVERIFIED: Conversational tools cannot apply project changes. Use the proposal queue.")
            elif failed:
                print("UNVERIFIED: At least one command failed or was denied. Inspect structured evidence.")
            else:
                print("MODEL ANSWER (task outcome unverified):")
                print(answer)
            # Outcome is unverified, not a confirmed failure.
            # Do not emit a terminal success/failure event.
            return
        arg = instruction.get("arg", "")
        if not isinstance(arg, str) or len(arg) > 4000:
            raise ValueError("Invalid tool argument")
        print(f"[{number + 1}/6] {action}: {arg[:90]}")
        try:
            if action == "exec" or action in aliases:
                record = execution_result(arg if action == "exec" else aliases[action])
                record = {**record, "task_id": task_id, "sequence": number + 1, "action": action}
                evidence.append(record)
                result = json.dumps(record, ensure_ascii=True)
            else:
                result = tool(action, arg)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            result = "TOOL ERROR: " + type(error).__name__
        messages.extend([{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"TOOL RESULT ({action}):\n{result[:12000]}\nContinue or finish."}])
        checkpoint(messages, number + 1, "running", task_id, evidence)
        bridge_event("task-progress")
    print("Tool limit reached. Task checkpoint preserved for review.")

def main():
    if "--self-test" in sys.argv:
        print("STATUS:", repr(tool("status", "")))
        print("TRACKED FILES:", len(tracked_files()))
        print("ROLES:", ", ".join(sorted(ROLES)))
        print("SELF-TEST PASS")
        return

    print("ODIN ORCHESTRATOR | GPT-OSS 120B")
    print("Specialist delegation + read-only device tools")
    print("Type exit to quit.\n")

    while True:
        try:
            question = input("odin > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExited")
            return

        if question.lower() in {"exit", "quit"}:
            return

        if question:
            try:
                respond(question)
            except (
                ValueError,
                TypeError,
                RuntimeError,
                OSError,
                subprocess.TimeoutExpired,
            ) as exc:
                print(
                    f"ERROR: {type(exc).__name__}: "
                    f"{str(exc)[:200]}"
                )


if __name__ == "__main__":
    main()
