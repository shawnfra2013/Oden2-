"""Record when an explicit local tool presents one stored review note.

A tool presentation is NOT proof an AI model read, understood or followed the
note. This module never executes feedback, edits GitHub, or calls a model.
Only its small, validated metadata receipt may reach the private outbox.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    from .odin_review_feedback import DEFAULT_INBOX, validate_feedback
except ImportError:
    from odin_review_feedback import DEFAULT_INBOX, validate_feedback

DEFAULT_OBSERVED = DEFAULT_INBOX.parent / "feedback-tool-observed"
ID = re.compile(r"[0-9a-f]{32}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "scope", "id", "issue_number", "pr_number", "head_sha",
    "reference_receipt_id", "decision", "note_sha256", "presented_at",
    "tool", "action_executed", "agent_identity_verified",
    "source_revision_verified",
})
MAX_RECEIPT_BYTES = 1800
REMOTE_PREFIX = "bridge/feedback-tool-receipts"


def remote_path(feedback_id: str) -> str:
    if not isinstance(feedback_id, str) or not ID.fullmatch(feedback_id):
        raise ValueError("Invalid feedback receipt ID")
    return f"{REMOTE_PREFIX}/{feedback_id}.json"


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Timestamp must be UTC")
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid feedback timestamp") from exc
    if when.utcoffset() != timedelta(0):
        raise ValueError("Feedback timestamp is not UTC")
    return when


def validate_tool_receipt(raw: bytes, expected_id: str) -> dict:
    remote_path(expected_id)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RECEIPT_BYTES:
        raise ValueError("Invalid tool receipt size")
    try:
        value = json.loads(raw)
    except (TypeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Malformed tool receipt") from exc
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("Unexpected feedback receipt fields")
    if (type(value["schema"]) is not int or value["schema"] != 1
            or value["scope"] != "local_feedback_tool_presented"
            or value["id"] != expected_id
            or value["tool"] != "odin_review_feedback.inspect"):
        raise ValueError("Invalid feedback receipt identity")
    if (not isinstance(value["head_sha"], str) or not SHA.fullmatch(value["head_sha"])
            or not isinstance(value["reference_receipt_id"], str)
            or not ID.fullmatch(value["reference_receipt_id"])
            or not isinstance(value["note_sha256"], str)
            or not DIGEST.fullmatch(value["note_sha256"])):
        raise ValueError("Invalid feedback provenance")
    for key in ("issue_number", "pr_number"):
        if type(value[key]) is not int or not 1 <= value[key] <= 1000000:
            raise ValueError("Invalid feedback identifier")
    if value["decision"] not in {"hold", "revise", "review_ready"}:
        raise ValueError("Unsupported feedback decision")
    if (value["action_executed"] is not False
            or value["agent_identity_verified"] is not False
            or value["source_revision_verified"] is not False):
        raise ValueError("Tool presentation cannot claim agent action")
    _utc(value["presented_at"])
    return value


def read_bounded(path: Path, max_bytes: int) -> bytes:
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError("Unsafe feedback file or directory")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as source:
        meta = os.fstat(source.fileno())
        if not stat.S_ISREG(meta.st_mode) or not 0 < meta.st_size <= max_bytes:
            raise ValueError("Unsafe feedback file size/type")
        content = source.read(max_bytes + 1)
    if not 0 < len(content) <= max_bytes:
        raise ValueError("Unsafe feedback read size")
    return content


def _serialize(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def save_tool_receipt(value: dict, directory: Path = DEFAULT_OBSERVED) -> Path:
    encoded = _serialize(value)
    validate_tool_receipt(encoded, value["id"])
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("Unsafe tool receipt directory")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / (value["id"] + ".json")
    if destination.is_symlink():
        raise ValueError("Unsafe tool receipt destination")
    if destination.exists():
        existing = validate_tool_receipt(read_bounded(destination, MAX_RECEIPT_BYTES), value["id"])
        for field in FIELDS - {"presented_at"}:
            if existing[field] != value[field]:
                raise ValueError("Conflicting tool receipt ID")
        return destination
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".pending-", delete=False) as handle:
            temp = Path(handle.name)
            os.fchmod(handle.fileno(), 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Hard link inserts only if no immutable ID already exists.
        try:
            os.link(temp, destination, follow_symlinks=False)
        except FileExistsError:
            existing = validate_tool_receipt(read_bounded(destination, MAX_RECEIPT_BYTES), value["id"])
            for field in FIELDS - {"presented_at"}:
                if existing[field] != value[field]:
                    raise ValueError("Conflicting tool receipt ID") from None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return destination


def inspect_feedback(
    feedback_id: str, *, inbox: Path = DEFAULT_INBOX,
    receipt_dir: Path = DEFAULT_OBSERVED, now: datetime | None = None,
) -> dict:
    """Present an existing note and atomically leave metadata for private sync."""
    remote_path(feedback_id)
    inbox = Path(inbox)
    if inbox.is_symlink():
        raise ValueError("Unsafe review inbox")
    raw = read_bounded(inbox / (feedback_id + ".json"), 2048)
    try:
        message = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Malformed stored feedback") from exc
    if not isinstance(message, dict) or message.get("id") != feedback_id:
        raise ValueError("Stored feedback ID mismatch")
    safe = validate_feedback(message)
    clock = datetime.now(UTC) if now is None else now
    if clock.tzinfo is None or clock.utcoffset() != timedelta(0):
        raise ValueError("Tool presentation clock must be UTC")
    receipt = {
        "schema": 1, "scope": "local_feedback_tool_presented",
        "id": feedback_id, "issue_number": safe["issue_number"],
        "pr_number": safe["pr_number"], "head_sha": safe["head_sha"],
        "reference_receipt_id": safe["reference_receipt_id"],
        "decision": safe["decision"],
        "note_sha256": hashlib.sha256(safe["feedback_note"].encode("utf-8")).hexdigest(),
        "presented_at": clock.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tool": "odin_review_feedback.inspect",
        "action_executed": False, "agent_identity_verified": False,
        "source_revision_verified": False,
    }
    save_tool_receipt(receipt, directory=receipt_dir)
    return {
        "untrusted_feedback": {"id": feedback_id, **safe},
        "local_tool_receipt": {
            "id": feedback_id, "scope": "local_feedback_tool_presented",
            "action_executed": False, "agent_identity_verified": False,
        },
    }


def local_candidates(directory: Path | None = None) -> list[Path]:
    directory = Path(DEFAULT_OBSERVED if directory is None else directory)
    if directory.is_symlink() or not directory.is_dir():
        return []
    return [
        file for file in sorted(directory.glob("*.json"))
        if ID.fullmatch(file.stem) and not file.is_symlink()
    ]


def load_candidate(path: Path) -> bytes:
    if not ID.fullmatch(path.stem):
        raise ValueError("Invalid tool receipt file name")
    raw = read_bounded(path, MAX_RECEIPT_BYTES)
    validate_tool_receipt(raw, path.stem)
    return raw
