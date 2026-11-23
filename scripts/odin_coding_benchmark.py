"""Compare independently graded held-out coding outcomes without executing model code.

Input is an approved metadata-only benchmark receipt, not training examples.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
CASE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def compare(report: dict) -> dict:
    if not isinstance(report, dict) or set(report) != {"baseline_sha", "candidate_sha", "cases"}:
        raise ValueError("Unexpected benchmark report")
    if any(not isinstance(report[k], str) or not SHA.fullmatch(report[k])
           for k in ("baseline_sha", "candidate_sha")):
        raise ValueError("Invalid revision")
    if report["baseline_sha"] == report["candidate_sha"]:
        raise ValueError("Candidate and baseline must use distinct revisions")
    cases = report["cases"]
    if not isinstance(cases, list) or not 5 <= len(cases) <= 200:
        raise ValueError("Invalid held-out set size")
    ids = set()
    before = after = 0
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "baseline_pass",
                                                      "candidate_pass", "grader_verified",
                                                      "heldout_attested"}:
            raise ValueError("Unexpected case fields")
        ident = case["id"]
        if not isinstance(ident, str) or not CASE.fullmatch(ident) or ident in ids:
            raise ValueError("Invalid or duplicate case")
        ids.add(ident)
        for field in ("baseline_pass", "candidate_pass", "grader_verified", "heldout_attested"):
            if type(case[field]) is not bool:
                raise ValueError("Invalid case evidence")
        if not case["grader_verified"] or not case["heldout_attested"]:
            return {"status": "BLOCKED", "reason": "missing_independent_holdout_proof",
                    "promotion_authorized": False}
        before += case["baseline_pass"]
        after += case["candidate_pass"]
    # A tie demonstrates only non-regression in the supplied claims, not
    # improvement. Do not let it appear as a successful self-improvement gate.
    outcome = "PASS" if after > before else "FAIL" if after < before else "BLOCKED"
    return {"status": outcome,
            "reason": "no_measured_gain" if after == before else "measured_comparison",
            "case_count": len(cases), "baseline_passed": before,
            "candidate_passed": after, "delta_passed": after - before,
            "improvement_observed": after > before,
            "promotion_authorized": False, "device_verified": False,
            "grader_claims_authenticated": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.report.is_symlink() or args.report.stat().st_size > 65536:
            raise ValueError("Unsafe report")
        result = compare(json.loads(args.report.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        result = {"status": "UNVERIFIED", "reason": "invalid_report",
                  "promotion_authorized": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
