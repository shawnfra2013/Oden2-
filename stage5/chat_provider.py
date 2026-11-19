"""Single explicit provider selector shared by Odin browser and CLI chat."""
import os

from inference_adapter import ask_bounded


def provider_name():
    name = os.environ.get("ODIN_STAGE5_PROVIDER", "groq").strip().lower()
    if name not in {"groq", "openai"}:
        raise RuntimeError("Unknown Odin AI provider")
    return name


def ask_model(question, history=None):
    if provider_name() == "openai":
        from openai_adapter import ask_openai
        return ask_openai(question, history)
    return ask_bounded(question, history)
