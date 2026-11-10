"""Odin background task queue. No arbitrary shell execution."""
import ast
import base64
import contextlib
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai" / "agent"))
import pipeline

ROOT = Path.home() / "odin-workspace"
BASE = ROOT / "state" / "task-queue"
PENDING = BASE / "pending"
RUNNING = BASE / "running"
DONE = BASE / "done"



def task_session_path(task_id):
    """Return the checkpoint owned by one queued task."""
    if not isinstance(task_id, str):
        raise TypeError("task_id must be a string")

    if (
        len(task_id) != 12
        or any(
            char not in "0123456789abcdef"
            for char in task_id
        )
    ):
        raise ValueError("Invalid task id")

    return (
        ROOT
        / "state"
        / "task-sessions"
        / f"{task_id}.json"
    )

def setup():
    for folder in (PENDING, RUNNING, DONE):
        with pipeline.directory(ROOT, folder.relative_to(ROOT).parts, create=True):
            pass


def save(path, data):
    pipeline.publish(ROOT, path.relative_to(ROOT).parts, pipeline.json_bytes(data))


def submit(goal):
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 4000:
        raise ValueError("Goal must contain 1-4000 characters")
    setup()
    for _ in range(8):
        ident = uuid.uuid4().hex[:12]
        occupied = (PENDING / (ident + ".json"), RUNNING / (ident + ".json"),
                    DONE / (ident + ".json"), DONE / (ident + ".log"), task_session_path(ident))
        if any(os.path.lexists(path) for path in occupied):
            continue
        try:
            save(PENDING / (ident + ".json"), {"id": ident, "goal": goal,
                 "created": datetime.now(UTC).isoformat()})
        except FileExistsError:
            continue
        print(f"QUEUED: {ident}")
        return
    raise RuntimeError("Could not reserve a new task ID")



def failure_record(
    error,
    *,
    kind,
    phase,
    attempt=1,
    max_retries=0,
    retryable=False,
    manual_review=True,
):
    """Build structured, bounded failure metadata."""
    return {
        "kind": kind,
        "type": type(error).__name__,
        "message": str(error)[:500],
        "phase": phase,
        "attempt": attempt,
        "max_retries": max_retries,
        "retryable": bool(retryable),
        "manual_review_required": bool(manual_review),
        "recorded": datetime.now(UTC).isoformat(),
    }


def fail_task(source, error, *, kind="execution_error", phase="execute"):
    raw = pipeline.read(ROOT, source.relative_to(ROOT).parts, 262144)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise TypeError("Queue record must be an object")
    except (ValueError, TypeError, RecursionError) as record_error:
        data = {"id": source.stem, "goal": None,
                "record_read_error": type(record_error).__name__,
                "original_record_b64": base64.b64encode(raw).decode("ascii")}
    data["input_sha256"] = hashlib.sha256(raw).hexdigest()
    data["status"] = "failed"
    data["finished"] = datetime.now(UTC).isoformat()
    data["failure"] = failure_record(error, kind=kind, phase=phase,
                                    attempt=1, max_retries=0, retryable=False, manual_review=True)
    destination = DONE / source.name
    save(destination, data)
    if pipeline.read(ROOT, source.relative_to(ROOT).parts, 262144) != raw:
        raise RuntimeError("Queue source changed during failure recording")
    pipeline.unlink(ROOT, source.relative_to(ROOT).parts)
    return data


def recover():
    """Quarantine interrupted work. Never blindly replay it."""
    for path in sorted(RUNNING.glob("*.json")):
        try:
            data = json.loads(path.read_text())

            if not isinstance(data, dict):
                raise TypeError(
                    "Queue record must be an object"
                )

            task_id = data.get("id")

            if (
                not isinstance(task_id, str)
                or task_id != path.stem
            ):
                raise ValueError(
                    "Running record ownership mismatch"
                )

            task_session_path(task_id)

            data["status"] = "interrupted"
            data["finished"] = datetime.now(
                UTC
            ).isoformat()

            data["failure"] = failure_record(
                RuntimeError(
                    "Worker stopped before task completion"
                ),
                kind="interrupted",
                phase="recovery",
                attempt=1,
                max_retries=0,
                retryable=False,
                manual_review=True,
            )

            data["recovery"] = {
                "action": "quarantined",
                "replayed": False,
                "manual_review_required": True,
                "recorded": datetime.now(
                    UTC
                ).isoformat(),
            }

            destination = DONE / path.name

            if destination.exists():
                raise RuntimeError(
                    "Done record already exists; "
                    "refusing recovery overwrite"
                )

            save(
                destination,
                data,
            )

            path.unlink()

            print(
                f"TASK {path.stem}: "
                "interrupted - manual review required",
                flush=True,
            )

        except (
            OSError,
            ValueError,
            RuntimeError,
            KeyError,
            TypeError,
        ) as error:
            try:
                fail_task(
                    path,
                    error,
                    kind="recovery_error",
                    phase="recovery",
                )

                print(
                    f"TASK {path.stem}: "
                    "recovery failed - manual review required",
                    flush=True,
                )

            except (
                OSError,
                ValueError,
                RuntimeError,
                KeyError,
                TypeError,
            ) as final_error:
                print(
                    f"TASK {path.stem}: "
                    "RECOVERY QUARANTINE FAILED: "
                    f"{type(final_error).__name__}: "
                    f"{str(final_error)[:150]}",
                    flush=True,
                )


def verified_git_status():
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Git status failed")
    return result.stdout or "CLEAN\n"




def proposal_paths(name, task_id, invocation_id):
    pipeline.target_parts(name)
    relative = pipeline.proposal_parts(task_id, invocation_id)
    return ROOT.joinpath(*relative, "candidate.py"), ROOT.joinpath(*relative, "metadata.json")


def verify_proposal(name, task, invocation_id, task_id):
    source, receipt = pipeline.receipt(ROOT, name, task, task_id, invocation_id)
    ast.parse(source.decode("utf-8"))
    lint = subprocess.run(
        ["ruff", "check", "--no-cache", "--stdin-filename", name, "-"],
        input=source.decode("utf-8"), text=True, capture_output=True,
        timeout=30, check=False, cwd=ROOT,
    )
    if lint.returncode != 0:
        raise ValueError("Independent Ruff verification failed")
    checked, current = pipeline.receipt(ROOT, name, task, task_id, invocation_id)
    if checked != source or current != receipt:
        raise ValueError("Proposal changed during independent verification")
    return {**receipt, "verified": True, "fresh": "invocation-bound"}

def execute(path):
    raw = pipeline.read(ROOT, path.relative_to(ROOT).parts, 262144)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("Queue record must be an object")
    task_id = pipeline.task_id(data.get("id"))
    if task_id != path.stem:
        raise ValueError("Queue record ownership mismatch")
    goal = data.get("goal")
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 4000:
        raise ValueError("Invalid queued goal")
    log = DONE / (task_id + ".log")
    if goal.startswith("PROPOSE "):
        import shlex

        arguments = shlex.split(goal[8:])
        if len(arguments) != 2:
            raise ValueError("Expected target and quoted task")
        invocation = uuid.uuid4().hex
        data["invocation_id"] = invocation
        result = subprocess.run(
            [sys.executable, str(ROOT / "ai/agent/proposal_builder.py"),
             arguments[0], arguments[1], "--task-id", task_id,
             "--invocation-id", invocation], cwd=ROOT, capture_output=True,
            text=True, timeout=180, check=False,
        )
        pipeline.publish(ROOT, log.relative_to(ROOT).parts,
                         (result.stdout + result.stderr).encode("utf-8"))
        if result.returncode != 0:
            raise RuntimeError("Proposal builder exited nonzero")
        data["verification"] = verify_proposal(arguments[0], arguments[1], invocation, task_id)
        data["status"] = "proposal_ready"
        data["exit_code"] = result.returncode
    elif goal.strip().lower() in {"git status", "check git status", "show git status", "git status --short"}:
        output = verified_git_status()
        pipeline.publish(ROOT, log.relative_to(ROOT).parts, ("VERIFIED GIT STATUS:\n" + output).encode())
        data["status"] = "complete"
        data["verification"] = {"kind": "git_status", "returncode": 0,
                                "sha256": hashlib.sha256(output.encode()).hexdigest()}
    else:
        import orchestrator

        with pipeline.directory(ROOT, log.relative_to(ROOT).parts[:-1]) as parent:
            fd = os.open(log.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=parent)
        with os.fdopen(fd, "w") as output, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            orchestrator.respond(goal, task_id=task_id)
        session = task_session_path(task_id)
        checkpoint = json.loads(pipeline.read(ROOT, session.relative_to(ROOT).parts, 300000))
        if not isinstance(checkpoint, dict) or checkpoint.get("task_id") != task_id:
            raise ValueError("Checkpoint ownership mismatch")
        data["status"] = "unverified"
        data["checkpoint"] = str(session)
        data["verification"] = {"task_outcome_verified": False,
                                "reason": "No deterministic acceptance contract for conversational tasks"}
    data["finished"] = datetime.now(UTC).isoformat()
    data["log"] = str(log)
    save(DONE / path.name, data)
    pipeline.unlink(ROOT, path.relative_to(ROOT).parts)
    print(f"TASK {task_id}: {data['status']}", flush=True)



def quarantine(source, reason):
    raw = pipeline.read(ROOT, source.relative_to(ROOT).parts, 262144)
    record = {"status": "quarantined", "reason": reason, "source": source.name,
              "original_sha256": hashlib.sha256(raw).hexdigest(),
              "original_record_b64": base64.b64encode(raw).decode("ascii"),
              "manual_review_required": True, "replayed": False,
              "recorded": datetime.now(UTC).isoformat()}
    destination = BASE / "quarantine" / (uuid.uuid4().hex + ".json")
    save(destination, record)
    pipeline.unlink(ROOT, source.relative_to(ROOT).parts)
    print(f"TASK {source.stem}: quarantined; existing evidence preserved", flush=True)


def cycle():
    for source in sorted(PENDING.glob("*.json")):
        destination = RUNNING / source.name
        claimed = False
        collision = any(os.path.lexists(p) for p in (
            destination, DONE / source.name, DONE / (source.stem + ".log"),
            ROOT / "state/task-sessions" / source.name,
        ))
        try:
            if collision:
                quarantine(source, "evidence_collision")
                continue
            pipeline.move_new(ROOT, source.relative_to(ROOT).parts, destination.relative_to(ROOT).parts)
            claimed = True
            execute(destination)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, SyntaxError, RecursionError,
                subprocess.TimeoutExpired) as error:
            active = destination if claimed else source
            try:
                if not claimed:
                    quarantine(active, "claim_failed")
                elif os.path.lexists(DONE / active.name):
                    quarantine(active, "done_collision_after_claim")
                else:
                    fail_task(active, error,
                              kind="timeout" if isinstance(error, subprocess.TimeoutExpired) else "execution_error",
                              phase="execute")
                    print(f"TASK {source.stem}: failed; manual review required", flush=True)
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as final_error:
                print(f"TASK {source.stem}: FAILURE RECORD ERROR: {type(final_error).__name__}", flush=True)


def main():
    if sys.argv[1:] == ["--self-test"]:
        pipeline.task_id("012345abcdef")
        pipeline.invocation_id("0" * 32)
        print("ID CONTRACT SELF-TEST PASS; full suite: tests/test_stage4.py")
        return
    setup()
    if len(sys.argv) >= 2 and sys.argv[1] == "--submit":
        submit(" ".join(sys.argv[2:]))
        return
    with pipeline.directory(ROOT, BASE.relative_to(ROOT).parts) as parent:
        fd = os.open("worker.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
    with os.fdopen(fd, "r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Worker already running")
            return
        recover()
        while True:
            cycle()
            if "--once" in sys.argv:
                break
            time.sleep(3)


if __name__ == "__main__":
    main()
