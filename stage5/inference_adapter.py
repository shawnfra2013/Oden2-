"""Isolated, bounded access to Odin's existing Groq orchestrator."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DEADLINE_SECONDS = 45

CHILD_CODE = """
import contextlib
import io
import json
import sys

sys.path.insert(0, sys.argv[1])

request = json.loads(sys.stdin.read())
question = request["question"]

with contextlib.redirect_stdout(io.StringIO()):
    import orchestrator
    answer = orchestrator.ask([
    {
        "role": "system",
        "content": (
            "You are Odin, a helpful AI assistant. "
            "Never claim to have executed actions without evidence."
        ),
    },
    *request.get("history", []),
    {"role": "user", "content": question},
], tokens=700)

if not isinstance(answer, str) or not answer.strip():
    raise ValueError("Invalid model response")

sys.stdout.write(json.dumps({"answer": answer}))
"""


def run_bounded(command, payload, deadline=DEADLINE_SECONDS):
    """Execute one child process with a wall-clock deadline."""
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        output, _ = proc.communicate(
            input=json.dumps(payload).encode(),
            timeout=deadline,
        )
    except subprocess.TimeoutExpired as exc:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise TimeoutError("Inference deadline exceeded") from exc
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError("Inference subprocess failed")

    if len(output) > 1048576:
        raise ValueError("Inference response too large")

    try:
        result = json.loads(output)
        answer = result["answer"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("Invalid inference response") from exc

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Empty inference response")

    return answer


def bounded_history(history):
    """Keep the newest complete turns inside the inference budget."""
    if history is None:
        return []
    if not isinstance(history, list):
        raise TypeError("Invalid history")
    selected = []
    remaining = 12000
    for message in reversed(history[-12:]):
        if not isinstance(message, dict):
            raise TypeError("Invalid history message")
        if set(message) != {"role", "content"}:
            raise ValueError("Invalid history fields")
        role, content = message["role"], message["content"]
        if role not in ("user", "assistant") or not isinstance(content, str):
            raise ValueError("Invalid history role or content")
        content = content[:4000]
        if len(content) > remaining:
            break
        selected.append({"role": role, "content": content})
        remaining -= len(content)
    if selected and selected[-1]["role"] == "assistant":
        selected.pop()
    return list(reversed(selected))


def ask_bounded(question, history=None):
    if os.environ.get("ODIN_STAGE5_ENABLE_AI") != "1":
        raise RuntimeError("AI disabled")
    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError("Groq credentials unavailable")
    if not isinstance(question, str) or not 0 < len(question.strip()) <= 4000:
        raise ValueError("Invalid question")

    agent_dir = WORKSPACE / "ai" / "agent"
    if not (agent_dir / "orchestrator.py").is_file():
        raise RuntimeError("Orchestrator unavailable")

    return run_bounded(
        [sys.executable, "-c", CHILD_CODE, str(agent_dir)],
        {"question": question, "history": bounded_history(history)},
    )
