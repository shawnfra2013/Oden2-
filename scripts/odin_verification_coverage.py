#!/usr/bin/env python3
"""Offline, fail-closed Odin verification coverage evaluator.

Input is explicitly supplied metadata, never an authenticated data fetch.
No private payloads, tokens, URLs or conversation text are printed.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
REQUEST = re.compile(r"^[0-9a-fA-F]{32}$")
STAGES = ("source", "device", "agent", "memory", "phone")
ALLOWED = {"PASS", "FAIL", "BLOCKED", "UNVERIFIED"}
UTC = dt.timezone.utc


def _timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC with Z suffix")
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() != dt.timedelta(0):
        raise ValueError("timestamp must be UTC")
    return result


def evaluate(document, *, now=None, max_age_seconds=900):
    """Return redacted status/next-action metadata, never raw evidence."""
    now = now or dt.datetime.now(UTC)
    expected = document.get("expected_sha")
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        raise ValueError("expected_sha must be a full lowercase Git SHA")
    if not isinstance(max_age_seconds, int) or max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    entries = document.get("evidence", [])
    if not isinstance(entries, list):
        raise ValueError("evidence must be an array")
    result = {}
    seen = set()
    for stage in STAGES:
        matching = [entry for entry in entries if isinstance(entry, dict) and entry.get("stage") == stage]
        status, reason = "UNVERIFIED", "missing_evidence"
        if len(matching) > 1:
            status, reason = "FAIL", "duplicate_stage_evidence"
        elif matching:
            item = matching[0]
            rid = item.get("request_id")
            if rid is not None and (not isinstance(rid, str) or not REQUEST.fullmatch(rid)):
                status, reason = "FAIL", "invalid_request_id"
            elif rid is not None and rid in seen:
                status, reason = "FAIL", "replayed_request_id"
            else:
                if rid is not None:
                    seen.add(rid)
                if item.get("source_sha") != expected:
                    status, reason = "UNVERIFIED", "source_sha_mismatch"
                else:
                    try:
                        age = (now - _timestamp(item.get("timestamp"))).total_seconds()
                    except (TypeError, ValueError):
                        status, reason = "UNVERIFIED", "invalid_timestamp"
                    else:
                        if age < 0 or age > max_age_seconds:
                            status, reason = "UNVERIFIED", "stale_or_future_evidence"
                        elif item.get("status") not in ALLOWED:
                            status, reason = "UNVERIFIED", "invalid_status"
                        else:
                            status = item["status"]
                            reason = "evidence_reported" if status != "PASS" else "check_proof"
                            # A status label is never sufficient proof of an executed check.
                            if status == "PASS":
                                if item.get("proof_kind") != stage or item.get("verified") is not True:
                                    status, reason = "UNVERIFIED", "missing_independent_proof"
                                elif stage in ("device", "agent", "memory", "phone") and not rid:
                                    status, reason = "UNVERIFIED", "missing_request_correlation"
                                elif stage == "agent" and not (
                                    item.get("agent_identity_verified") is True
                                    and item.get("action_executed") is True
                                    and item.get("source_revision_verified") is True
                                ):
                                    status, reason = "UNVERIFIED", "agent_action_not_authenticated"
        result[stage] = {"status": status, "reason": reason}
    return {"expected_sha": expected, "overall": (
        "FAIL" if any(v["status"] == "FAIL" for v in result.values()) else
        "BLOCKED" if any(v["status"] == "BLOCKED" for v in result.values()) else
        "PASS" if all(v["status"] == "PASS" for v in result.values()) else "UNVERIFIED"
    ), "stages": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path, help="Local redacted metadata JSON; never private payloads")
    parser.add_argument("--max-age-seconds", type=int, default=900)
    args = parser.parse_args()
    report = evaluate(json.loads(args.metadata.read_text(encoding="utf-8")),
                      max_age_seconds=args.max_age_seconds)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
