"""Bounded, non-executing two-way review-feedback inbox for Odin.

Private GitHub mailbox submits reviewed feedback; the local coding agent may
inspect it, but this module NEVER executes a note, edits source, or starts a task.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

REQUEST_FIELDS = frozenset({
    "issue_number", "pr_number", "head_sha", "reference_receipt_id",
    "decision", "feedback_note",
})
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
DECISIONS = frozenset({"revise", "hold", "review_ready"})
MAX_NOTE_LENGTH = 600
DEFAULT_INBOX = Path(__file__).resolve().parents[1] / "state" / "github-bridge-private" / "review-feedback"


def validate_feedback(request):
    """Validate fields only; remote SHA/receipt authenticity is separately checked."""
    if not isinstance(request, dict):
        raise ValueError("Feedback must be an object")
    for key in ("issue_number", "pr_number"):
        value = request.get(key)
        if type(value) is not int or not 1 <= value <= 1000000:
            raise ValueError("Invalid " + key)
    if not isinstance(request.get("head_sha"), str) or not SHA_RE.fullmatch(request["head_sha"]):
        raise ValueError("Invalid feedback head SHA")
    if not isinstance(request.get("reference_receipt_id"), str) or not ID_RE.fullmatch(request["reference_receipt_id"]):
        raise ValueError("Invalid reference receipt ID")
    if request.get("decision") not in DECISIONS:
        raise ValueError("Unsupported review decision")
    note = request.get("feedback_note")
    if (not isinstance(note, str) or not 1 <= len(note) <= MAX_NOTE_LENGTH
            or any(ord(char) < 32 or ord(char) == 127 for char in note)):
        raise ValueError("Invalid feedback note")
    return {key: request[key] for key in sorted(REQUEST_FIELDS)}


def record_feedback(request, *, inbox=DEFAULT_INBOX):
    """Save one immutable feedback item after the bridge's expiry/schema checks.

    The receipt means only that feedback was stored; it does not approve a PR,
    authorize a deployment, prove a referenced SHA is current, or run an agent.
    """
    data = validate_feedback(request)
    feedback_id = request.get("id")
    if not isinstance(feedback_id, str) or not ID_RE.fullmatch(feedback_id):
        raise ValueError("Invalid feedback ID")
    inbox = Path(inbox)
    if inbox.is_symlink():
        raise ValueError("Unsafe feedback directory")
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / (feedback_id + ".json")
    if path.is_symlink():
        raise ValueError("Unsafe feedback file")
    payload = {"version": 1, "id": feedback_id, **data}
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError("Conflicting feedback ID")
    else:
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=inbox, prefix=".pending-", delete=False) as stream:
                temp = Path(stream.name)
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
    return {
        "feedback_id": feedback_id, "reference_receipt_id": data["reference_receipt_id"],
        "issue_number": data["issue_number"], "pr_number": data["pr_number"],
        "head_sha": data["head_sha"], "decision": data["decision"],
        "recorded": True, "source_revision_verified": False,
        "action_executed": False, "needs_agent_review": True,
    }


def list_feedback(*, inbox=DEFAULT_INBOX, limit=5):
    """Return bounded, clearly untrusted pending feedback for a local agent."""
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Invalid limit")
    inbox = Path(inbox)
    if inbox.is_symlink() or not inbox.is_dir():
        return []
    items = []
    for path in sorted(inbox.glob("*.json"), reverse=True)[:limit]:
        if path.is_symlink() or not ID_RE.fullmatch(path.stem) or path.stat().st_size > 2048:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("id") != path.stem:
                continue
            data = validate_feedback(payload)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        items.append({"id": path.stem, **data, "trusted": False, "action_executed": False})
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Read, never act on, feedback")
    args = parser.parse_args(argv)
    if not args.list:
        parser.error("Only --list is supported")
    print(json.dumps({"untrusted_review_feedback": list_feedback()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
