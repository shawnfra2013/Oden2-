"""Read-only scoped task handoff for an actually attached coding agent.

This validates a proposed source-only contract, not task authorization.
It does not launch Codespaces, prompt a model, execute untrusted commands,
create a branch, or edit the handheld.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from scripts.odin_codespace import ROOT, sha_at
from scripts.odin_task_contract import validate_contract

MAX_BYTES = 16000


def tracked_clean(root: Path = ROOT) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root, capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return not result.stdout.strip()


def handoff(contract: dict, *, local_sha: str | None,
            clean: bool | None) -> dict:
    checked = validate_contract(contract)
    matches = local_sha == checked["base_sha"]
    ready = matches and clean is True
    return {
        "status": "READY_FOR_OPERATOR_ATTACHED_AGENT" if ready else "BLOCKED",
        "issue_number": checked["issue_number"],
        "expected_base_sha": checked["base_sha"],
        "observed_local_sha": local_sha,
        "revision_matches": matches,
        "tracked_clean": clean,
        "allowed_paths": checked["allowed_paths"],
        "required_tests": checked["required_tests"],
        "acceptance_criteria": checked["acceptance_criteria"],
        "max_review_rounds": checked["max_review_rounds"],
        "source_only": True,
        "operator_authorization_verified": False,
        "coding_agent_attached_verified": False,
        "device_connection": "not_checked",
        "codespace_started": False,
    }


def read_contract(file: Path) -> dict:
    if file.is_symlink() or not file.is_file() or not 0 < file.stat().st_size <= MAX_BYTES:
        raise ValueError("Unsafe contract file")
    return json.loads(file.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = handoff(read_contract(args.contract), local_sha=sha_at(),
                         clean=tracked_clean())
    except (ValueError, OSError, TypeError):
        result = {
            "status": "BLOCKED", "reason": "invalid_contract_or_source",
            "coding_agent_attached_verified": False,
            "operator_authorization_verified": False,
            "device_connection": "not_checked",
            "codespace_started": False,
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "READY_FOR_OPERATOR_ATTACHED_AGENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
