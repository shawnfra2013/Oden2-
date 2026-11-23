"""Bounded private event trace for Odin's existing GitHub mailbox.

Records only response correlation metadata after a successful private reply.
No payload content, model text, terminal stdout, credentials, or network calls.
The journal is supplemental evidence, not proof that an AI agent read a note.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "state/odin-traces"
ID = re.compile(r"[0-9a-f]{32}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
ACTION = re.compile(r"[a-z][a-z0-9_]{0,50}\Z")
STATES = frozenset({"complete", "expired", "rejected_or_failed", "unverified"})
MAX_LOG_BYTES = 2 * 1024 * 1024
FIELDS = frozenset({
    "schema", "id", "stage", "action", "status", "checked_at",
    "source_sha", "action_ms", "agent_read_verified", "device_phone_verified",
})


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Invalid trace UTC time")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid trace UTC time") from exc
    if dt.utcoffset() != timedelta(0):
        raise ValueError("Non-UTC trace time")
    return dt


def normalize(receipt: dict, source_sha: str) -> dict:
    """Whitelist fields; never copy untrusted result objects into the journal."""
    if not isinstance(receipt, dict):
        raise ValueError("Trace receipt must be an object")
    ident, action = receipt.get("id"), receipt.get("action")
    status, timestamp = receipt.get("status"), receipt.get("checked_at")
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise ValueError("Invalid trace request ID")
    if not isinstance(action, str) or not ACTION.fullmatch(action):
        raise ValueError("Invalid trace action")
    if status not in STATES or not isinstance(source_sha, str) or not SHA.fullmatch(source_sha):
        raise ValueError("Invalid trace state or local source SHA")
    _utc(timestamp)
    timing = receipt.get("timing")
    duration = timing.get("action_ms") if isinstance(timing, dict) else None
    if (duration is not None and
            (type(duration) not in (int, float) or not 0 <= duration <= 300000)):
        raise ValueError("Invalid trace duration")
    return {
        "schema": 1, "id": ident, "stage": "private_mailbox_reply",
        "action": action, "status": status, "checked_at": timestamp,
        "source_sha": source_sha, "action_ms": duration,
        "agent_read_verified": False, "device_phone_verified": False,
    }


def _records(raw: bytes) -> list[dict]:
    if len(raw) > MAX_LOG_BYTES:
        raise ValueError("Trace log exceeds bounded size")
    if not raw:
        return []
    if not raw.endswith(b"\n"):
        raise ValueError("Incomplete private trace line")
    records = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Malformed trace line") from exc
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise ValueError("Unexpected trace record schema")
        if item.get("schema") != 1:
            raise ValueError("Unsupported trace schema")
        normalize(item, item["source_sha"])
        records.append(item)
    return records


def append_bridge_reply(directory: Path, receipt: dict, source_sha: str) -> bool:
    """Append once per request ID under a local exclusive Linux file lock."""
    record = normalize(receipt, source_sha)
    directory = Path(directory)
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError("Unsafe trace directory")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    file = directory / "events.jsonl"
    if file.is_symlink():
        raise ValueError("Unsafe trace file")
    fd = os.open(file, os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_LOG_BYTES:
            raise ValueError("Unsafe trace log")
        os.lseek(fd, 0, os.SEEK_SET)
        prior = _records(os.read(fd, MAX_LOG_BYTES + 1))
        for item in prior:
            if item["id"] == record["id"] and item["stage"] == record["stage"]:
                if item != record:
                    raise ValueError("Conflicting replayed private trace")
                return False
        encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if details.st_size + len(encoded) > MAX_LOG_BYTES:
            raise ValueError("Private trace log full")
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    return True


def summarize(directory: Path = TRACE_DIR, *, hours: int = 1,
              now: datetime | None = None) -> dict:
    if type(hours) is not int or not 1 <= hours <= 24:
        raise ValueError("Invalid trace lookback")
    observed = datetime.now(UTC) if now is None else now
    if observed.tzinfo is None or observed.utcoffset() != timedelta(0):
        raise ValueError("Trace clock must be UTC")
    directory = Path(directory)
    file = directory / "events.jsonl"
    if directory.is_symlink() or file.is_symlink():
        raise ValueError("Unsafe trace journal path")
    if not file.is_file():
        return {"scope": "private_mailbox_metadata", "events": 0,
                "status_counts": {}, "incidents": [], "agent_read_verified": False}
    fd = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        records = _records(os.read(fd, MAX_LOG_BYTES + 1))
    finally:
        os.close(fd)
    cutoff = observed - timedelta(hours=hours)
    selected = [r for r in records if cutoff <= _utc(r["checked_at"]) <= observed]
    counts = {name: sum(r["status"] == name for r in selected) for name in sorted(STATES)}
    incidents = [
        {"id": r["id"], "code": r["status"], "checked_at": r["checked_at"]}
        for r in selected if r["status"] != "complete"
    ]
    return {
        "scope": "private_mailbox_metadata", "events": len(selected),
        "status_counts": counts, "incidents": incidents[-25:],
        "incidents_truncated": len(incidents) > 25,
        "agent_read_verified": False, "device_phone_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=1)
    args = parser.parse_args()
    try:
        report = summarize(hours=args.hours)
    except (OSError, ValueError) as exc:
        print("PRIVATE_TRACE_UNVERIFIED:", type(exc).__name__)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
