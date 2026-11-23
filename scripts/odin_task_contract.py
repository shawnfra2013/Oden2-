"""Deterministic task-scope and acceptance checks; no model or device access.

A proposed coding change must match its task-specific contract. This validator
does not authorize a new task or grant file-write permissions.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import PurePosixPath, Path

HEX_SHA = re.compile(r"[0-9a-f]{40}\Z")
ALLOWED_TESTS = frozenset({
    "odin_checks", "offline_browser", "ruff", "python_unittest",
    "stage5_unittest", "node_tests", "secret_scan", "preflight_source",
})
CONTRACT_KEYS = frozenset({
    "schema", "issue_number", "base_sha", "allowed_paths", "required_tests",
    "acceptance_criteria", "max_review_rounds",
})
RESULT_KEYS = frozenset({
    "issue_number", "base_sha", "head_sha", "changed_paths",
    "tests", "review_round",
})


def _safe_path(value):
    """Require exact relative tracked-style file paths, no wildcards or traversal."""
    if not isinstance(value, str) or not 1 <= len(value) <= 180:
        return False
    if ("\\" in value or "*" in value or "?" in value
            or value.startswith("/") or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and all(part not in ("", ".", "..") for part in parts) and "/".join(parts) == value


def validate_contract(contract):
    if not isinstance(contract, dict) or set(contract) != CONTRACT_KEYS:
        raise ValueError("Unknown or missing task contract fields")
    if type(contract["schema"]) is not int or contract["schema"] != 1 or type(contract["issue_number"]) is not int or contract["issue_number"] < 1:
        raise ValueError("Invalid contract schema or issue")
    if not isinstance(contract["base_sha"], str) or not HEX_SHA.fullmatch(contract["base_sha"]):
        raise ValueError("Invalid approved base SHA")
    paths = contract["allowed_paths"]
    if not isinstance(paths, list) or not 1 <= len(paths) <= 50 or any(not _safe_path(x) for x in paths) or len(paths) != len(set(paths)):
        raise ValueError("Invalid allowed file paths")
    tests = contract["required_tests"]
    if not isinstance(tests, list) or not 1 <= len(tests) <= len(ALLOWED_TESTS) or any(not isinstance(x, str) or x not in ALLOWED_TESTS for x in tests) or len(tests) != len(set(tests)):
        raise ValueError("Invalid required source tests")
    criteria = contract["acceptance_criteria"]
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 12 or any(not isinstance(x, str) or not 8 <= len(x) <= 300 for x in criteria):
        raise ValueError("Missing or invalid acceptance criteria")
    if type(contract["max_review_rounds"]) is not int or not 0 <= contract["max_review_rounds"] <= 2:
        raise ValueError("Unsafe revision budget")
    return contract


def evaluate_contract(contract, observed):
    """PASS only when expected paths and all required exact-SHA checks pass.

    The checks supplied as observed evidence must be independently verified by
    GitHub. This function's pure result is not proof of the evidence's origin.
    """
    contract = validate_contract(contract)
    reasons = []
    if not isinstance(observed, dict) or set(observed) != RESULT_KEYS:
        raise ValueError("Unknown or missing observed result fields")
    if type(observed["issue_number"]) is not int or observed["issue_number"] != contract["issue_number"]:
        reasons.append("issue_mismatch")
    if observed["base_sha"] != contract["base_sha"]:
        reasons.append("base_sha_mismatch")
    if not isinstance(observed["head_sha"], str) or not HEX_SHA.fullmatch(observed["head_sha"]):
        reasons.append("invalid_head_sha")
    elif observed["head_sha"] == contract["base_sha"]:
        reasons.append("unchanged_head_sha")
    paths = observed["changed_paths"]
    if not isinstance(paths, list) or not 1 <= len(paths) <= 50 or any(not _safe_path(x) for x in paths):
        reasons.append("invalid_changed_paths")
    else:
        if len(paths) != len(set(paths)):
            reasons.append("duplicate_changed_paths")
        if set(paths) - set(contract["allowed_paths"]):
            reasons.append("out_of_scope_paths")
    if type(observed["review_round"]) is not int or observed["review_round"] > contract["max_review_rounds"] or observed["review_round"] < 0:
        reasons.append("review_budget_exceeded")
    tests = observed["tests"]
    if not isinstance(tests, dict) or any(type(k) is not str or type(v) is not bool for k, v in tests.items()):
        reasons.append("invalid_test_evidence")
    else:
        for name in contract["required_tests"]:
            if name not in tests:
                reasons.append("missing_test:" + name)
            elif tests[name] is not True:
                reasons.append("failed_test:" + name)
    return {"status": "PASS" if not reasons else "FAIL",
            "issue_number": contract["issue_number"],
            "head_sha": observed["head_sha"],
            "reasons": reasons,
            "evidence_authenticated": False,
            "device_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    result = evaluate_contract(contract, evidence)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
