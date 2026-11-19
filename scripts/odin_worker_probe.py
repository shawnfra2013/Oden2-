"""Prove an existing queue worker executed one fixed, request-bound Git status job."""
import hashlib
import json
import re
from datetime import UTC, datetime

try:
    from .odin_worker import pipeline
except ImportError:
    from odin_worker import pipeline


def probe(root, request_id):
    if not re.fullmatch("[0-9a-f]{32}", request_id):
        raise ValueError("Invalid probe ID")
    task = request_id[:12]
    file = task + ".json"
    base = ("state", "task-queue")
    # Follow the forward-only lifecycle in order so a concurrent move is visible.
    for phase in ("pending", "running", "done"):
        try:
            data = json.loads(pipeline.read(root, (*base, phase, file), 262144))
        except FileNotFoundError:
            continue
        if (data.get("id"), data.get("probe_id"), data.get("goal")) != (task, request_id, "git status"):
            raise ValueError("Queue evidence collision")
        if phase != "done":
            return None
        if data.get("status") != "complete":
            raise ValueError("Worker check incomplete")
        proof = data.get("verification", {})
        log = pipeline.read(root, (*base, phase, task + ".log"), 1048576)
        prefix = b"VERIFIED GIT STATUS:\n"
        if (not log.startswith(prefix) or proof.get("kind") != "git_status"
                or proof.get("returncode") != 0
                or hashlib.sha256(log[len(prefix):]).hexdigest() != proof.get("sha256")):
            raise ValueError("Worker evidence mismatch")
        return {"verified": True}
    record = {"id": task, "probe_id": request_id, "goal": "git status",
              "created": datetime.now(UTC).isoformat()}
    pipeline.publish(root, (*base, "pending", file), pipeline.json_bytes(record))
    return None
