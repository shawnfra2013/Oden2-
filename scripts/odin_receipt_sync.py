"""Validate offline source-test receipts before private GitHub mailbox transfer.

Purely local checks. Never executes a receipt, calls an AI model, or exposes logs.
Only the existing private mailbox service may publish validated items.
"""
from __future__ import annotations

import json
import os
import re
import stat
from datetime import datetime, timedelta
from pathlib import Path

RECEIPT_DIR = Path.home() / "odin-workspace" / "state" / "codespace-receipts"
REMOTE_PREFIX = "bridge/local-source-receipts"
MAX_BYTES = 4096
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
CHECK_NAMES = frozenset({
    "documentation", "structure", "python_tests", "workstation_tests",
    "browser_tests", "ruff", "preflight",
})
REQUIRED = frozenset({
    "schema", "scope", "id", "started_at", "completed_at", "source_sha",
    "status", "checks", "device_connection", "phone_connection",
})


def remote_path(receipt_id: str) -> str:
    if not isinstance(receipt_id, str) or not ID_RE.fullmatch(receipt_id):
        raise ValueError("Invalid receipt ID")
    return f"{REMOTE_PREFIX}/{receipt_id}.json"


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 35:
        raise ValueError("Invalid receipt timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid receipt timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Receipt timestamp must be UTC")
    return parsed


def validate_bytes(raw: bytes, expected_id: str) -> dict:
    """Accept only exact bounded source-test fields, not arbitrary device logs."""
    remote_path(expected_id)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("Invalid receipt size")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ValueError("Malformed receipt") from exc
    if not isinstance(data, dict) or set(data) != REQUIRED:
        raise ValueError("Unexpected receipt fields")
    if (type(data["schema"]) is not int or data["schema"] != 1
            or data["scope"] != "local_source_only" or data["id"] != expected_id):
        raise ValueError("Invalid receipt identity or scope")
    sha = data["source_sha"]
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("Invalid source revision")
    if (data["device_connection"] != "not_checked"
            or data["phone_connection"] != "not_checked"):
        raise ValueError("Local source receipt cannot certify device/phone")
    if _timestamp(data["completed_at"]) < _timestamp(data["started_at"]):
        raise ValueError("Completion precedes start")
    checks = data["checks"]
    if not isinstance(checks, list) or len(checks) != len(CHECK_NAMES):
        raise ValueError("Incorrect source check count")
    seen = set()
    for check in checks:
        if not isinstance(check, dict) or set(check) != {
            "name", "status", "exit_code", "duration_ms",
        }:
            raise ValueError("Unexpected source check fields")
        name, result = check["name"], check["status"]
        code, duration = check["exit_code"], check["duration_ms"]
        if (name not in CHECK_NAMES or name in seen or result not in {"PASS", "FAIL"}
                or type(code) is not int or not 0 <= code <= 255
                or type(duration) is not int or not 0 <= duration <= 250000
                or (code == 0) != (result == "PASS")):
            raise ValueError("Invalid source check")
        seen.add(name)
    if seen != CHECK_NAMES:
        raise ValueError("Missing source checks")
    outcome = "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL"
    if data["status"] != outcome:
        raise ValueError("Receipt overall status does not match checks")
    return data


def local_candidates(directory: Path = RECEIPT_DIR):
    """Skip unsafe filenames and symlinks; malformed items do not block the queue."""
    if directory.is_symlink() or not directory.is_dir():
        return []
    return [
        path for path in sorted(directory.glob("*.json"))
        if ID_RE.fullmatch(path.stem) and not path.is_symlink()
    ]


def load_local(path: Path) -> bytes:
    """No-follow bounded read; detect concurrent/partial writes by validation."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
            raise ValueError("Unsafe source receipt")
        raw = stream.read(MAX_BYTES + 1)
    validate_bytes(raw, path.stem)
    return raw
