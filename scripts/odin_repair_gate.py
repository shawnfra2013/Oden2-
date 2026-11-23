"""Pure, fail-closed review decision gate for a two-revision Odin coding task.

Does not execute candidates, modify Git branches, or grant autonomous authority.
"""
from __future__ import annotations

import json
import re

SHA = re.compile(r"[0-9a-f]{40}\Z")
STATES = frozenset({"pending", "pass", "fail", "blocked"})


def decide(task: dict) -> dict:
    required = {"base_sha", "head_sha", "revision_round", "tests",
                "review", "feedback_read", "agent_action", "device_verified"}
    if not isinstance(task, dict) or set(task) != required:
        raise ValueError("Invalid task state")
    for key in ("base_sha", "head_sha"):
        if not isinstance(task[key], str) or not SHA.fullmatch(task[key]):
            raise ValueError("Invalid source SHA")
    round_number = task["revision_round"]
    if type(round_number) is not int or round_number < 0 or round_number > 2:
        raise ValueError("Revision budget exceeded")
    if any(task[key] not in STATES for key in ("tests", "review")):
        raise ValueError("Invalid verification status")
    if any(type(task[key]) is not bool for key in
           ("feedback_read", "agent_action", "device_verified")):
        raise ValueError("Invalid receipt evidence")
    reasons = []
    if task["tests"] != "pass":
        reasons.append("tests_not_passed")
    if task["review"] != "pass":
        reasons.append("review_not_passed")
    if task["feedback_read"] and not task["agent_action"]:
        reasons.append("feedback_read_without_verified_action")
    if task["device_verified"] and (task["tests"] != "pass" or task["review"] != "pass"):
        reasons.append("device_claim_without_source_acceptance")
    if not reasons:
        action = "review_for_merge"
    elif round_number >= 2:
        action = "escalate"
    elif task["tests"] == "fail" or task["review"] == "fail":
        action = "request_one_revision"
    else:
        action = "await_evidence"
    return {"status": "PASS" if not reasons else "BLOCKED",
            "next_action": action, "reasons": reasons,
            "head_sha": task["head_sha"], "revision_round": round_number,
            "automatic_merge_authorized": False,
            "device_verified": task["device_verified"]}


def main() -> int:
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.state.is_symlink() or args.state.stat().st_size > 8192:
            raise ValueError("Unsafe task state")
        result = decide(json.loads(args.state.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        result = {"status": "UNVERIFIED", "next_action": "escalate",
                  "automatic_merge_authorized": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
