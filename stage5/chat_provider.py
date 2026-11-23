"""Single explicit provider selector shared by Odin browser and CLI chat."""
import os

from inference_adapter import ask_bounded


def provider_name(environ=None):
    """Select the one backend from the process, never from browser claims."""
    env = os.environ if environ is None else environ
    name = str(env.get("ODIN_STAGE5_PROVIDER", "groq")).strip().lower()
    if name not in {"groq", "openai", "local"}:
        raise RuntimeError("Unknown Odin AI provider")
    return name


def ask_model(question, history=None, *, expected_provider=None):
    provider = provider_name()
    if expected_provider is not None and provider != expected_provider:
        raise RuntimeError("Configured provider changed; model request blocked")
    if provider == "local":
        from local_adapter import ask_local
        return ask_local(question, history)
    if provider == "openai":
        from openai_adapter import ask_openai
        return ask_openai(question, history)
    return ask_bounded(question, history)


def provider_status(environ=None):
    """Return nonsecret readiness facts for the selected on-device provider.

    This does not contact a model and cannot prove that credentials are valid.
    It checks the environment *visible to the process asking*.
    """
    env = os.environ if environ is None else environ
    if environ is None:
        from offline_profile import activate
        env = dict(env)
        activate(env)
    try:
        name = provider_name(env)
    except RuntimeError:
        name = "invalid"
    enabled = env.get("ODIN_STAGE5_ENABLE_AI") == "1"
    if name == "local":
        from local_adapter import local_settings
        try:
            local_settings(env)
            configured = True
        except ValueError:
            configured = False
        return {"provider": name, "enabled": enabled, "credential_present": False,
                "model_configured": configured, "ready": enabled and configured,
                "reason": "ai_disabled" if not enabled else (
                    "configured_not_tested" if configured else "model_missing")}
    if name == "groq":
        credential = bool(str(env.get("GROQ_API_KEY", "")).strip())
        model_configured = True  # Existing orchestrator pins a known model.
    elif name == "openai":
        import re

        credential = bool(str(env.get("OPENAI_API_KEY", "")).strip())
        model_configured = re.fullmatch(
            r"[A-Za-z0-9._-]{1,100}", str(env.get("ODIN_OPENAI_MODEL", "")).strip()
        ) is not None
    else:
        return {
            "provider": "invalid", "enabled": enabled,
            "credential_present": False, "model_configured": False,
            "ready": False, "reason": "invalid_provider",
        }
    reason = (
        "ai_disabled" if not enabled
        else "credential_missing" if not credential
        else "model_missing" if not model_configured
        else "configured_not_tested"
    )
    return {
        "provider": name, "enabled": enabled,
        "credential_present": credential, "model_configured": model_configured,
        "ready": reason == "configured_not_tested", "reason": reason,
    }
