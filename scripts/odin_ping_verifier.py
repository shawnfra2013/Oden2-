"""Read-only, request-bound Odin ping receipt verification.

Consumes two local JSON objects. Does not contact GitHub, send commands,
activate a model, or assert anything about an unobserved device.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

ID = re.compile(r"[0-9a-f]{32}\Z")
REQUEST_FIELDS = {"version", "id", "action", "created_at", "expires_at"}
RECEIPT_FIELDS = {"version", "id", "action", "status", "checked_at", "result"}
FRESH_FOR = timedelta(minutes=5)
MAX_FILE_SIZE = 8192


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Invalid UTC timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("Non-UTC timestamp")
    return result


def verify_ping(request: dict, receipt: dict | None, *, now: datetime | None = None) -> dict:
    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise ValueError("Unexpected request envelope")
    ident = request["id"]
    if (type(request["version"]) is not int or request["version"] != 1
            or not isinstance(ident, str) or not ID.fullmatch(ident)
            or request["action"] != "ping"):
        raise ValueError("Not a supported ping request")
    created, expires = utc(request["created_at"]), utc(request["expires_at"])
    if not timedelta(0) < expires - created <= timedelta(hours=1):
        raise ValueError("Invalid expiry window")
    observed = datetime.now(UTC) if now is None else now
    if observed.tzinfo is None or observed.utcoffset() != timedelta(0):
        raise ValueError("Observation time must be UTC")
    base = {"request_id": ident, "action": "ping",
            "device_verified": False, "source_ci_verified": False,
            "status": "UNVERIFIED", "reason": "no_matching_receipt",
            "checked_at": None}
    if receipt is None:
        if expires < observed:
            base["reason"] = "request_expired_without_receipt"
        return base
    if (not isinstance(receipt, dict) or
            set(receipt) not in (RECEIPT_FIELDS, RECEIPT_FIELDS | {"timing"})):
        raise ValueError("Unexpected receipt envelope")
    if (type(receipt["version"]) is not int or receipt["version"] != 1
            or receipt["id"] != ident or receipt["action"] != "ping"):
        return {**base, "status": "FAIL", "reason": "receipt_identity_mismatch"}
    checked = utc(receipt["checked_at"])
    base["checked_at"] = receipt["checked_at"]
    if checked < created or checked > observed + timedelta(minutes=1):
        return {**base, "status": "FAIL", "reason": "invalid_receipt_order"}
    if not isinstance(receipt["result"], dict):
        return {**base, "status": "FAIL", "reason": "invalid_result"}
    if receipt["status"] != "complete":
        return {**base, "status": "FAIL", "reason": "device_not_completed"}
    if receipt["result"].get("alive") is not True:
        return {**base, "status": "FAIL", "reason": "ping_not_alive"}
    if observed - checked > FRESH_FOR:
        return {**base, "status": "UNVERIFIED", "reason": "stale_receipt"}
    return {**base, "status": "PASS", "reason": "request_bound_alive",
            "device_verified": True}


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Unsafe receipt file")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    try:
        request = read_json(args.request)
        receipt = read_json(args.receipt) if args.receipt else None
        result = verify_ping(request, receipt)
    except (ValueError, OSError, TypeError):
        result = {"status": "UNVERIFIED", "reason": "invalid_evidence",
                  "device_verified": False, "source_ci_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
