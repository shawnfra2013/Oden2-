"""Isolated, bounded access to Odin's existing Groq orchestrator."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path.home() / "odin-workspace"
DEADLINE_SECONDS = 45

CHILD_CODE = """
import contextlib
import io
import json
import sys

sys.path.insert(0, sys.argv[1])

question = json.loads(sys.stdin.read())["question"]

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


def ask_bounded(question):
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
        {"question": question},
    )
