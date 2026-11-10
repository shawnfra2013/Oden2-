"""Generate isolated Python proposals without changing project files."""

import ast
import subprocess
import sys
import uuid
from pathlib import Path

if __package__:
    from . import orchestrator, pipeline
else:
    import orchestrator
    import pipeline

ROOT = Path.home() / "odin-workspace"
PROPOSALS = ROOT / "state" / "proposals"


def target_path(name):
    pipeline.target_parts(name)
    pipeline.baseline(ROOT, name)
    return ROOT / name


def validate(source, name):
    ast.parse(source)

    result = subprocess.run(
        ["ruff", "check", "--no-cache", "--stdin-filename", name, "-"],
        input=source,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        cwd=ROOT,
    )

    if result.returncode:
        raise ValueError(result.stdout + result.stderr)


def autofix(source, name):
    """Apply Ruff safe fixes in a temporary directory."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / Path(name).name
        candidate.write_text(source)

        subprocess.run(
            ["ruff", "check", "--fix", str(candidate)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        return candidate.read_text()


def build(name, task, *, task_id=None, invocation_id=None):
    target_path(name)

    if not isinstance(task, str) or len(task) > 4000 or not task.strip():
        raise ValueError("Invalid task")

    baseline_sha256, original = pipeline.baseline(ROOT, name)
    invocation_id = invocation_id or uuid.uuid4().hex
    destination_parts = pipeline.reserve(ROOT, task_id, invocation_id)

    if len(original) > 30000:
        raise ValueError("Existing module too large")

    messages = [
        {
            "role": "system",
            "content": (
                "You are Odin's Python module builder. "
                "Return only complete Python source code. "
                "No Markdown. No explanations. "
                "Keep functions small, modular and testable. "
                "Preserve existing interfaces when editing. "
                "Do not embed secrets or perform destructive operations."
            ),
        },
        {
            "role": "user",
            "content": (
                f"TARGET: {name}\n"
                f"TASK: {task}\n"
                f"EXISTING SOURCE:\n{original}"
            ),
        },
    ]

    source = orchestrator.ask(messages, tokens=6000).strip() + "\n"

    if source.startswith("```") or len(source.encode('utf-8')) > pipeline.MAX_SOURCE:
        raise ValueError("Invalid model output")

    for attempt in range(3):
        source = autofix(source, name)
        try:
            validate(source, name)
            break
        except (SyntaxError, ValueError) as exc:
            if attempt == 2:
                raise ValueError(
                    "Proposal failed validation after 3 attempts"
                ) from exc

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a Python code repair agent. "
                        "Return ONLY the complete corrected Python file. "
                        "No Markdown or explanations. "
                        "Fix ALL reported Ruff and syntax errors. "
                        "Use modern Python 3.13 typing. "
                        "Never use broad except Exception. "
                        "Keep the existing functionality."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"FILE: {name}\n"
                        f"VALIDATION ERRORS:\n{str(exc)[:10000]}\n"
                        f"CURRENT SOURCE:\n{source}"
                    ),
                },
            ]

            print(f"REPAIR ATTEMPT {attempt + 1}/2", flush=True)
            source = orchestrator.ask(
                messages, tokens=6000
            ).strip() + "\n"

            if source.startswith("```") or len(source.encode('utf-8')) > pipeline.MAX_SOURCE:
                raise ValueError("Invalid repair response") from None

    encoded = source.encode("utf-8")
    if not encoded or len(encoded) > pipeline.MAX_SOURCE:
        raise ValueError("Invalid candidate byte size")
    if pipeline.baseline(ROOT, name)[0] != baseline_sha256:
        raise ValueError("Target changed during generation")
    import hashlib

    metadata = {
        "schema": pipeline.SCHEMA,
        "target": name, "task": task, "task_id": task_id,
        "invocation_id": invocation_id,
        "baseline_sha256": baseline_sha256,
        "sha256": hashlib.sha256(encoded).hexdigest(), "size": len(encoded),
        "syntax": "passed", "ruff": "passed", "applied": False,
    }
    pipeline.publish(ROOT, (*destination_parts, "candidate.py"), encoded)
    pipeline.publish(ROOT, (*destination_parts, "metadata.json"), pipeline.json_bytes(metadata))
    _, receipt = pipeline.receipt(ROOT, name, task, task_id, invocation_id)
    print("PROPOSAL READY:", receipt["artifact"])
    print("SYNTAX: PASS")
    print("RUFF: PASS")
    print("PROJECT FILES: UNCHANGED")
    return receipt


def main():
    import argparse

    if sys.argv[1:] == ["--self-test"]:
        pipeline.target_parts("ai/agent/example.py")
        pipeline.target_parts("tests/test_example.py")
        print("PATH CONTRACT SELF-TEST PASS")
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("task", nargs="+")
    parser.add_argument("--task-id")
    parser.add_argument("--invocation-id")
    args = parser.parse_args()
    build(args.name, " ".join(args.task), task_id=args.task_id, invocation_id=args.invocation_id)


if __name__ == "__main__":
    main()
