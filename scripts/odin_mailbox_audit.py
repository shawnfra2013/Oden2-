"""Read-only private mailbox correlation and incident audit for Odin.

Works only against an already-present local private Git clone. Never fetches,
pushes, authenticates, executes mailbox content, or prints private message text.
An audit snapshot is not proof of an agent read, a live shell, or phone access.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAILBOX = ROOT / "state" / "github-bridge-private" / "outbox"
LOG_DIR = ROOT / "state" / "mailbox-audits"
ID = re.compile(r"[0-9a-f]{32}\Z")
MAX_ITEMS = 1500
MAX_REQUEST_SIZE = 18000
MAX_RESPONSE_SIZE = 18000
ACTIONS_SAFE = frozenset({
    "ping", "stage5_health", "staging_probe", "stage5_note_check",
    "stage5_source_check", "stage5_coding_review", "practice_next",
    "practice_followup", "regression_details", "review_feedback",
    "inference_probe", "encrypted_chat", "install_offline_model",
    "mailbox_audit", "mailbox_migration_preview",
})
TERMINAL = frozenset({"complete", "expired", "rejected_or_failed", "unverified"})


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 35:
        raise ValueError("Invalid UTC timestamp")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamp") from exc
    if instant.utcoffset() != timedelta(0):
        raise ValueError("Timestamp is not UTC")
    return instant


def _request(name: str, data: object) -> tuple[str, datetime, datetime, str]:
    ident = Path(name).stem
    if not ID.fullmatch(ident) or not isinstance(data, dict):
        raise ValueError("Invalid request identity")
    if data.get("id") != ident or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Request ID/version mismatch")
    action = data.get("action")
    if not isinstance(action, str) or len(action) > 50:
        raise ValueError("Invalid request action")
    created = _utc(data.get("created_at"))
    expires = _utc(data.get("expires_at"))
    if not timedelta(0) < expires - created <= timedelta(hours=1):
        raise ValueError("Invalid request expiry")
    return ident, created, expires, action


def _response(name: str, data: object) -> tuple[str, datetime, str, str]:
    ident = Path(name).stem
    if not ID.fullmatch(ident) or not isinstance(data, dict):
        raise ValueError("Invalid response identity")
    if data.get("id") != ident or type(data.get("version")) is not int or data["version"] != 1:
        raise ValueError("Response ID/version mismatch")
    status, action = data.get("status"), data.get("action")
    if status not in TERMINAL or not isinstance(action, str) or len(action) > 50:
        raise ValueError("Invalid response status/action")
    checked_at = _utc(data.get("checked_at"))
    return ident, checked_at, status, action


def audit_messages(
    requests: dict[str, object],
    responses: dict[str, object],
    *, now: datetime | None = None, hours: int = 1,
    pending_after_seconds: int = 150,
) -> dict:
    """Compare private request/response metadata, never echo payload content.

    A missing response after the deadline is a delivery incident, not proof
    that Odin failed or that a command was executed. The caller decides what
    to do with a finding; no automatic retry or command execution occurs.
    """
    instant = datetime.now(UTC) if now is None else now
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("Audit clock must be UTC")
    if type(hours) is not int or not 1 <= hours <= 24:
        raise ValueError("Audit lookback must be 1..24 hours")
    if type(pending_after_seconds) is not int or not 30 <= pending_after_seconds <= 3600:
        raise ValueError("Invalid pending threshold")
    if len(requests) > MAX_ITEMS or len(responses) > MAX_ITEMS:
        raise ValueError("Mailbox tree exceeds audit bounds")
    cutoff = instant - timedelta(hours=hours)
    incidents = []
    counts = {"matched": 0, "pending": 0, "stalled": 0,
              "expired_without_reply": 0, "rejected": 0,
              "expired": 0, "unverified": 0, "malformed": 0}
    latencies = []
    considered = 0
    for name, data in sorted(requests.items()):
        if not name.endswith(".json") or not ID.fullmatch(Path(name).stem) or name != Path(name).stem + ".json":
            counts["malformed"] += 1
            continue
        ident = Path(name).stem
        try:
            _, created, expires, action = _request(name, data)
        except (ValueError, TypeError):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "malformed_request"})
            continue
        if created > instant + timedelta(minutes=5):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "future_request"})
            continue
        if created < cutoff:
            continue
        considered += 1
        filename = ident + ".json"
        if filename not in responses:
            if instant >= expires:
                status = "expired_without_reply"
            elif (instant - created).total_seconds() >= pending_after_seconds:
                status = "stalled"
            else:
                status = "pending"
            counts[status] += 1
            if status != "pending":
                incidents.append({"id": ident, "code": status})
            continue
        try:
            _, checked_at, status, response_action = _response(filename, responses[filename])
        except (ValueError, TypeError):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "malformed_response"})
            continue
        if checked_at > instant + timedelta(minutes=5):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "response_in_future"})
            continue
        if checked_at < created - timedelta(seconds=1):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "response_before_request"})
            continue
        if response_action not in {action, "none"} or (response_action == "none" and status == "complete"):
            counts["malformed"] += 1
            incidents.append({"id": ident, "code": "action_mismatch"})
            continue
        if status == "complete":
            if action not in ACTIONS_SAFE:
                counts["malformed"] += 1
                incidents.append({"id": ident, "code": "unexpected_action_complete"})
                continue
            if action == "ping" and responses[filename].get("result", {}).get("alive") is not True:
                counts["malformed"] += 1
                incidents.append({"id": ident, "code": "ping_not_alive"})
                continue
            counts["matched"] += 1
        elif status == "rejected_or_failed":
            counts["rejected"] += 1
            incidents.append({"id": ident, "code": "rejected_or_failed"})
        else:
            counts[status] += 1
            incidents.append({"id": ident, "code": status})
        latencies.append(max(0, round((checked_at - created).total_seconds())))
    # A fresh response without any corresponding local inbox request may be a
    # replay, partial fetch, or corrupted clone; do not infer its origin.
    for name, data in sorted(responses.items()):
        if name in requests:
            continue
        try:
            ident, checked_at, _, _ = _response(name, data)
        except (ValueError, TypeError):
            continue
        if cutoff <= checked_at <= instant + timedelta(minutes=5):
            incidents.append({"id": ident, "code": "orphan_response"})
    report = {
        "schema": 1,
        "scope": "private_mailbox_metadata",
        "checked_at": instant.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window_hours": hours,
        "considered": considered,
        "counts": counts,
        "max_response_latency_s": max(latencies) if latencies else None,
        "incidents": incidents[:100],
        "incidents_truncated": len(incidents) > 100,
        "device_live_verified": False,
        "agent_read_verified": False,
    }
    return report


def _git(mailbox: Path, *argv: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(mailbox), *argv], capture_output=True,
        text=True, errors="replace", timeout=20, check=False,
    )
    if result.returncode:
        raise RuntimeError("Private mailbox snapshot unavailable")
    if len(result.stdout) > 500000:
        raise RuntimeError("Private mailbox tree response too large")
    return result.stdout


def git_records(mailbox: Path, reference: str, prefix: str, *, limit: int = MAX_ITEMS) -> dict:
    """Use only current local Git objects; never call the network."""
    if reference not in {"HEAD", "origin/odin-bridge-inbox"}:
        raise ValueError("Unsafe Git reference")
    if prefix not in {"bridge/requests/", "bridge/responses/"}:
        raise ValueError("Unsafe Git path")
    names = _git(mailbox, "ls-tree", "-r", "--name-only", reference, "--", prefix)
    names = names.splitlines()
    if len(names) > limit:
        raise RuntimeError("Mailbox tree exceeds bounded scan limit")
    records = {}
    max_bytes = MAX_REQUEST_SIZE if prefix.endswith("requests/") else MAX_RESPONSE_SIZE
    for name in names:
        expected_name = name[len(prefix):]
        if not name.startswith(prefix) or not ID.fullmatch(Path(expected_name).stem):
            continue
        if name != prefix + Path(expected_name).stem + ".json":
            continue
        raw = _git(mailbox, "show", reference + ":" + name)
        if len(raw.encode("utf-8")) > max_bytes:
            records[expected_name] = None
            continue
        try:
            records[expected_name] = json.loads(raw)
        except json.JSONDecodeError:
            records[expected_name] = None
    return records


def inspect_local(mailbox: Path = MAILBOX, *, hours: int = 1, now: datetime | None = None) -> dict:
    if mailbox.is_symlink() or not (mailbox / ".git").is_dir():
        raise RuntimeError("No validated local private mailbox clone")
    # HEAD is the private outbox; its branch and origin are checked by the
    # existing supervised bridge, not inferred by this read-only scan.
    if _git(mailbox, "branch", "--show-current").strip() != "odin-bridge-outbox":
        raise RuntimeError("Unexpected private outbox branch")
    inbox = git_records(mailbox, "origin/odin-bridge-inbox", "bridge/requests/")
    outbox = git_records(mailbox, "HEAD", "bridge/responses/")
    return audit_messages(inbox, outbox, hours=hours, now=now)


def save_report(report: dict, directory: Path = LOG_DIR) -> Path:
    """Preserve each audit snapshot as a separate, private, append-only file."""
    if directory.is_symlink():
        raise ValueError("Unsafe report directory")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    filename = report["checked_at"].replace(":", "").replace("-", "") + "-" + uuid.uuid4().hex + ".json"
    target = directory / filename
    payload = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    if len(payload) > 24000:
        raise ValueError("Audit report exceeds safe size")
    with target.open("xb") as handle:
        os.chmod(target, 0o600)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=1)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()
    try:
        report = inspect_local(hours=args.hours)
        if args.save:
            path = save_report(report)
            print("Private audit saved:", path, file=sys.stderr)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("MAILBOX_AUDIT_ERROR: " + type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 1 if report["incidents"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
