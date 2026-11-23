"""Validate claimed review-round-trip milestones without treating claims as authority.

This pure validator cannot authenticate GitHub/device evidence and never
executes feedback, invokes a model, installs software, or updates a PR.
"""
from __future__ import annotations

import re
from datetime import datetime

ID = re.compile(r"[0-9a-f]{32}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
ORDER = (
    "submitted", "device_received", "agent_tool_read",
    "action_proposed", "code_changed", "source_verified",
)
REQUIRED = frozenset({"state", "request_id", "head_sha", "checked_at", "evidence_ref"})


def validate_milestones(events, *, request_id, original_sha):
    """Fail-closed ordering for one issue/PR and request across a revision loop."""
    if not isinstance(request_id, str) or not ID.fullmatch(request_id):
        raise ValueError("Bad request ID")
    if not isinstance(original_sha, str) or not SHA.fullmatch(original_sha):
        raise ValueError("Bad original SHA")
    if not isinstance(events, list) or len(events) > len(ORDER):
        raise ValueError("Bad event list")
    next_stage = 0
    last_timestamp = None
    current_sha = original_sha
    observed = []
    seen_evidence = set()
    for event in events:
        if not isinstance(event, dict) or set(event) != REQUIRED:
            raise ValueError("Unknown receipt event fields")
        state = event["state"]
        if not isinstance(state, str) or next_stage >= len(ORDER) or state != ORDER[next_stage]:
            raise ValueError("Out of order or duplicate state")
        if event["request_id"] != request_id:
            raise ValueError("Mismatched request ID")
        head_sha = event["head_sha"]
        if not isinstance(head_sha, str) or not SHA.fullmatch(head_sha):
            raise ValueError("Invalid head SHA")
        if state == "code_changed":
            if head_sha == current_sha:
                raise ValueError("Code change requires new SHA")
            current_sha = head_sha
        elif head_sha != current_sha:
            raise ValueError("Unexpected SHA change before code stage")
        evidence = event["evidence_ref"]
        if (not isinstance(evidence, str) or not 1 <= len(evidence) <= 300
                or any(ord(c) < 32 or ord(c) == 127 for c in evidence)):
            raise ValueError("Invalid evidence reference")
        if evidence in seen_evidence:
            raise ValueError("Replayed evidence reference")
        seen_evidence.add(evidence)
        timestamp = event["checked_at"]
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            raise ValueError("Bad UTC time")
        try:
            moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid time") from exc
        if last_timestamp and moment < last_timestamp:
            raise ValueError("Event timestamps out of order")
        last_timestamp = moment
        observed.append(state)
        next_stage += 1
    return {
        "received": "device_received" in observed,
        "read_by_agent_tool": "agent_tool_read" in observed,
        "code_change_claimed": "code_changed" in observed,
        "source_ci_claimed": "source_verified" in observed,
        "stage": observed[-1] if observed else "UNVERIFIED",
        "last_sha": current_sha,
        "request_id": request_id,
        "evidence_independently_verified": False,
        "physical_device_verified": False,
        "automatic_followup_implemented": False,
    }
