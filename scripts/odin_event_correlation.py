"""Validate metadata-only GitHub event and reviewer-run correlations.

Pure analysis: no webhooks, network calls, database writes, or private payloads.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{40}\Z")
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,127}\Z")
EVENTS = frozenset({"opened", "ready_for_review", "synchronize",
                    "review_submitted", "review_comment"})


def correlate(events: list[dict], runs: list[dict]) -> dict:
    if not isinstance(events, list) or not isinstance(runs, list) or len(events) > 500 or len(runs) > 500:
        raise ValueError("Invalid event/run count")
    deliveries, observed = set(), {}
    findings = []
    for event in events:
        if not isinstance(event, dict) or set(event) != {"delivery_id", "pr", "head_sha", "action"}:
            raise ValueError("Invalid event metadata")
        delivery, pr, sha, action = (event[k] for k in ("delivery_id", "pr", "head_sha", "action"))
        if not isinstance(delivery, str) or not ID.fullmatch(delivery):
            raise ValueError("Invalid delivery ID")
        if type(pr) is not int or pr < 1 or not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Invalid PR/head SHA")
        if action not in EVENTS:
            raise ValueError("Unsupported event action")
        if delivery in deliveries:
            findings.append({"delivery_id": delivery, "reason": "duplicate_delivery"})
        deliveries.add(delivery)
        observed[delivery] = (pr, sha)
    matched = set()
    for run in runs:
        if not isinstance(run, dict) or set(run) != {"run_id", "delivery_id", "pr", "head_sha"}:
            raise ValueError("Invalid run metadata")
        run_id, delivery, pr, sha = (run[k] for k in ("run_id", "delivery_id", "pr", "head_sha"))
        if not isinstance(run_id, str) or not ID.fullmatch(run_id):
            raise ValueError("Invalid run ID")
        if not isinstance(delivery, str) or not ID.fullmatch(delivery):
            raise ValueError("Invalid run delivery ID")
        if type(pr) is not int or pr < 1 or not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Invalid run PR/head SHA")
        if delivery not in observed:
            findings.append({"delivery_id": delivery, "reason": "orphan_run"})
        elif observed[delivery] != (pr, sha):
            findings.append({"delivery_id": delivery, "reason": "mismatched_pr_or_sha"})
        elif delivery in matched:
            findings.append({"delivery_id": delivery, "reason": "duplicate_run"})
        else:
            matched.add(delivery)
    for delivery in sorted(deliveries - matched):
        findings.append({"delivery_id": delivery, "reason": "unmatched_delivery"})
    return {"status": "PASS" if not findings else "BLOCKED",
            "event_count": len(events), "run_count": len(runs),
            "matched_count": len(matched), "findings": findings,
            "authenticated_delivery": False, "device_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.metadata.stat().st_size > 262144 or args.metadata.is_symlink():
            raise ValueError("Unsafe metadata file")
        data = json.loads(args.metadata.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"events", "runs"}:
            raise ValueError("Unexpected metadata")
        result = correlate(data["events"], data["runs"])
    except (OSError, ValueError, TypeError):
        result = {"status": "UNVERIFIED", "reason": "invalid_metadata",
                  "authenticated_delivery": False, "device_verified": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
