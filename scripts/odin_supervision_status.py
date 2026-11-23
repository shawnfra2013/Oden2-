"""Generate a redacted, fail-closed Odin supervision status from verified metadata.

Source-only dashboard data adapter; no network calls, private mail or device commands.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{40}\Z")
STATES = frozenset({"PASS", "FAIL", "BLOCKED", "UNVERIFIED"})


def summarize(data: dict) -> dict:
    required = {"git_sha", "ci", "event_delivery", "memory_index",
                "feedback_action", "device_install", "last_receipt_utc"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("Unexpected dashboard fields")
    sha = data["git_sha"]
    if sha is not None and (not isinstance(sha, str) or not SHA.fullmatch(sha)):
        raise ValueError("Invalid Git revision")
    for key in ("ci", "event_delivery", "memory_index", "feedback_action", "device_install"):
        if data[key] not in STATES:
            raise ValueError("Invalid evidence state")
    timestamp = data["last_receipt_utc"]
    if timestamp is not None and (not isinstance(timestamp, str)
                                  or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp)):
        raise ValueError("Invalid receipt timestamp")
    components = {key: data[key] for key in
                  ("ci", "event_delivery", "memory_index", "feedback_action", "device_install")}
    if any(state == "FAIL" for state in components.values()):
        overall = "FAIL"
    elif any(state == "BLOCKED" for state in components.values()):
        overall = "BLOCKED"
    elif any(state == "UNVERIFIED" for state in components.values()) or sha is None or timestamp is None:
        overall = "UNVERIFIED"
    else:
        overall = "PASS"
    return {"status": overall, "git_sha": sha, "components": components,
            "last_receipt_utc": timestamp, "read_only": True,
            "live_device_probe_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.metadata.is_symlink() or args.metadata.stat().st_size > 8192:
            raise ValueError("Unsafe metadata")
        result = summarize(json.loads(args.metadata.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        result = {"status": "UNVERIFIED", "reason": "invalid_metadata",
                  "read_only": True, "live_device_probe_performed": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
