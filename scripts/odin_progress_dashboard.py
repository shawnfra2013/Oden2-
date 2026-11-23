"""Local source-only task proof timeline and held-out coding progress summary.

This consumes bounded, pre-collected metadata. It cannot independently
authenticate a model, grader, private receipt or physical device.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.odin_feedback_progress import ORDER, validate_milestones
from scripts.odin_coding_benchmark import compare

MAX_REPORT_BYTES = 131072


def dashboard(data: dict) -> dict:
    if not isinstance(data, dict) or set(data) != {
        "schema", "issue_number", "request_id", "base_sha", "events", "benchmark"
    }:
        raise ValueError("Unexpected evidence dashboard fields")
    if (type(data["schema"]) is not int or data["schema"] != 1
            or type(data["issue_number"]) is not int or data["issue_number"] < 1):
        raise ValueError("Invalid dashboard identity")
    events = data["events"]
    stages = validate_milestones(
        events, request_id=data["request_id"], original_sha=data["base_sha"]
    )
    claimed = [entry["state"] for entry in events]
    benchmark = data["benchmark"]
    comparison = compare(benchmark) if benchmark is not None else None
    summary = None
    if comparison is not None:
        summary = {
            "status": comparison["status"],
            "reason": comparison.get("reason"),
            "case_count": comparison.get("case_count"),
            "baseline_passed_claimed": comparison.get("baseline_passed"),
            "candidate_passed_claimed": comparison.get("candidate_passed"),
            "delta_passed_claimed": comparison.get("delta_passed"),
            "grader_claims_authenticated": False,
            "promotion_authorized": False,
        }
    # A provided event or benchmark is never independently authenticated by a
    # local renderer. Presentation must not promote a claim to live proof.
    return {
        "status": "UNVERIFIED",
        "issue_number": data["issue_number"],
        "request_id": data["request_id"],
        "last_claimed_sha": stages["last_sha"],
        "claimed_stages": [
            {"stage": event["state"], "checked_at": event["checked_at"],
             "evidence_ref": event["evidence_ref"]}
            for event in events
        ],
        "next_claimed_stage": ORDER[len(claimed)] if len(claimed) < len(ORDER) else None,
        "missing_stages": list(ORDER[len(claimed):]),
        "benchmark": summary,
        "agent_action_independently_verified": False,
        "source_checks_independently_verified": False,
        "device_verified": False,
        "phone_verified": False,
        "automatic_model_promotion": False,
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Odin evidence and coding progress",
        f"Issue #{result['issue_number']} · overall UNVERIFIED (claims need external proof)",
        "",
        "## Supervised task timeline",
    ]
    if result["claimed_stages"]:
        for item in result["claimed_stages"]:
            lines.append(f"- Claimed {item['stage']} at {item['checked_at']}; reference: {item['evidence_ref']}")
    else:
        lines.append("- No task milestones were supplied")
    lines.extend(["", "## Evidence still required"])
    lines.extend(f"- {name}" for name in result["missing_stages"])
    if not result["missing_stages"]:
        lines.append("- Authenticate every claimed stage independently")
    lines.extend(["", "## Held-out coding comparison"])
    comparison = result["benchmark"]
    if comparison is None:
        lines.append("- No independently graded held-out comparison supplied")
    else:
        lines.append(
            f"- Claimed {comparison['baseline_passed_claimed']}/{comparison['case_count']}"
            f" baseline versus {comparison['candidate_passed_claimed']}/{comparison['case_count']}"
            f" candidate; delta {comparison['delta_passed_claimed']}"
        )
        lines.append("- Grader authentication, weight promotion, device and phone: UNVERIFIED")
    return "\n".join(lines) + "\n"


def read_report(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_REPORT_BYTES:
        raise ValueError("Unsafe dashboard metadata")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()
    try:
        result = dashboard(read_report(args.metadata))
    except (ValueError, OSError, TypeError, KeyError):
        result = {
            "status": "UNVERIFIED", "reason": "invalid_or_missing_evidence",
            "agent_action_independently_verified": False,
            "device_verified": False, "automatic_model_promotion": False,
        }
    if args.format == "markdown" and "issue_number" in result:
        print(render_markdown(result), end="")
    else:
        print(json.dumps(result, sort_keys=True))
    return 0 if "issue_number" in result else 2


if __name__ == "__main__":
    raise SystemExit(main())
