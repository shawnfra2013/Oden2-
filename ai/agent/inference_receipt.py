"""Bounded, non-sensitive inference provenance."""
from contextvars import ContextVar

_ACTIVE = ContextVar("odin_inference_receipts", default=None)


def begin():
    """Start collecting receipts for one task."""
    return _ACTIVE.set([])


def finish(token):
    """End collection and restore previous context."""
    _ACTIVE.reset(token)


def receipts():
    """Return the current task's receipts."""
    active = _ACTIVE.get()
    return list(active) if active is not None else []


def record(response, requested_model):
    """Record provider metadata, never prompts or credentials."""
    active = _ACTIVE.get()
    if active is None:
        return

    response_id = response.get("id")
    model = response.get("model")
    usage = response.get("usage")

    def valid_text(value):
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:/-"
        return (
            isinstance(value, str)
            and 0 < len(value) <= 160
            and all(char in allowed for char in value)
        )

    def valid_tokens(value):
        return type(value) is int and 0 <= value <= 1000000000

    safe_usage = {}
    if isinstance(usage, dict):
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if valid_tokens(usage.get(key)):
                safe_usage[key] = usage[key]

    active.append({
        "provider": "groq",
        "requested_model": requested_model,
        "response_model": model if valid_text(model) else None,
        "response_id": response_id if valid_text(response_id) else None,
        "usage": safe_usage,
        "provider_request_traceable": valid_text(response_id),
        "independently_verified": False,
    })


def restore(saved):
    """Restore only validated receipts from a checkpoint."""
    active = _ACTIVE.get()
    if active is None or not isinstance(saved, list):
        return
    for item in saved:
        if not isinstance(item, dict):
            continue
        provider = item.get("provider")
        if provider != "groq":
            continue
        record_data = {
            "id": item.get("response_id"),
            "model": item.get("response_model"),
            "usage": item.get("usage"),
        }
        record(record_data, item.get("requested_model"))
