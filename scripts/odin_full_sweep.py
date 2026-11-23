"""One private mailbox round-trip that summarizes fixed read-only device checks.

This action never runs an AI model, fetches GitHub, restarts services, writes
configuration or executes request-supplied commands. The bridge publishes
the normal authenticated request-bound reply after this function returns.
An isolated device sweep cannot prove GitHub exact-main CI, a model answer,
network disconnection, or iPhone acceptance.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

try:
    from .odin_preflight import build_report
    from .odin_mailbox_audit import inspect_local
except ImportError:  # Direct Termux script entrypoint
    from odin_preflight import build_report
    from odin_mailbox_audit import inspect_local

ID = re.compile(r"[0-9a-f]{32}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
STATES = frozenset({"PASS", "FAIL", "UNVERIFIED"})
SERVICE_NAMES = ("odin-private-mailbox", "odin-git-sync", "odin-task-worker",
                 "odin-stage5")
AUDIT_KEYS = ("matched", "pending", "stalled", "expired", "expired_without_reply",
              "rejected", "malformed", "unverified")


def _attempt(callback):
    """Failure of one optional diagnostic does not suppress the other facts."""
    try:
        value = callback()
        return value if isinstance(value, dict) else {}
    except Exception:  # Never return exception strings, filenames, or secrets.
        return {}


def _int(value):
    return value if type(value) is int and 0 <= value <= 1000000 else None


def inspect(request, *, status_fn, health_fn, outbox: Path,
            preflight_fn=build_report, audit_fn=inspect_local):
    """Collect one report for an already validated private mailbox request."""
    if (not isinstance(request, dict)
            or request.get("action") != "full_sweep"
            or not isinstance(request.get("id"), str)
            or not ID.fullmatch(request["id"])):
        raise ValueError("Invalid full sweep request")
    if not isinstance(outbox, Path):
        raise ValueError("Invalid private mailbox path")

    # Each call is fixed-source and read-only. No model invocation.
    ping = _attempt(lambda: status_fn("ping"))
    preflight = _attempt(lambda: preflight_fn("device"))
    health = _attempt(health_fn)
    workstation = _attempt(lambda: status_fn("stage5_health"))
    audit = _attempt(lambda: audit_fn(outbox, hours=1))

    ping_sha = ping.get("revision")
    health_sha = health.get("head")
    ping_sha = ping_sha if isinstance(ping_sha, str) and SHA.fullmatch(ping_sha) else None
    health_sha = health_sha if isinstance(health_sha, str) and SHA.fullmatch(health_sha) else None
    source_agreement = ("PASS" if ping_sha and ping_sha == health_sha else
                        "FAIL" if ping_sha and health_sha and ping_sha != health_sha else
                        "UNVERIFIED")

    checks = {}
    for entry in preflight.get("checks", []) if isinstance(preflight.get("checks"), list) else []:
        if isinstance(entry, dict):
            name, state = entry.get("check"), entry.get("status")
            if (isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,70}", name)
                    and state in STATES and len(checks) < 32):
                checks[name] = state

    services = {}
    raw_services = health.get("services")
    if not isinstance(raw_services, dict):
        raw_services = {}
    for name in SERVICE_NAMES:
        value = raw_services.get(name)
        state = value.get("state") if isinstance(value, dict) else None
        services[name] = ("PASS" if state == "running" else
                          "FAIL" if state == "down" else "UNVERIFIED")

    raw_counts = audit.get("counts")
    raw_counts = raw_counts if isinstance(raw_counts, dict) else {}
    audit_counts = {key: _int(raw_counts.get(key)) for key in AUDIT_KEYS}
    incidents = audit.get("incidents")
    incident_count = _int(audit.get("incident_count_shown"))
    if incident_count is None and isinstance(incidents, list):
        incident_count = len(incidents)
    audit_state = (
        "UNVERIFIED" if not audit or incident_count is None
        else "FAIL" if incident_count or audit.get("incidents_truncated")
        or any((audit_counts.get(key) or 0) > 0 for key in
               ("stalled", "expired_without_reply", "malformed", "rejected", "unverified"))
        else "PASS"
    )
    workstation_state = (
        "PASS" if workstation.get("reachable") is True and workstation.get("ready") is True
        else "UNVERIFIED"
    )
    ping_state = "PASS" if ping.get("alive") is True else "UNVERIFIED"

    all_states = list(checks.values()) + list(services.values()) + [
        source_agreement, audit_state, workstation_state, ping_state,
    ]
    # An explicit user-observed inference test is recorded in the issue, but
    # this safe diagnostic does not repeat it or claim an offline proof.
    all_states.append("UNVERIFIED")
    overall = ("FAIL" if "FAIL" in all_states else
               "UNVERIFIED" if "UNVERIFIED" in all_states else "PASS")

    provider = workstation.get("provider")
    pid = _int(ping.get("pid"))
    return {
        "schema_version": 1,
        "scope": "private_read_only_full_sweep",
        "request_id": request["id"],
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "alive": ping.get("alive") is True,
        "pid": pid,
        "revision": ping_sha,
        "source_consistency": source_agreement,
        "preflight_checks": checks,
        "services": services,
        "queue": {"pending": _int(health.get("queue_pending")),
                  "running": _int(health.get("queue_running"))},
        "workstation": {"status": workstation_state,
                        "provider": provider if provider in {"local", "groq", "openai", "invalid"} else None,
                        "ai_enabled": workstation.get("ai_enabled") is True},
        "mailbox": {"status": audit_state,
                    "considered": _int(audit.get("considered")),
                    "counts": audit_counts,
                    "incident_count": incident_count},
        "unverified_gates": ["github_exact_main", "model_inference_this_sweep",
                             "network_offline", "iphone_cellular", "agent_action"],
        "overall": overall,
        "release_approved": False,
        "device_change_performed": False,
    }
