"""Optional OpenAI Responses API backend for Odin's local AI conversation.

No API key or conversation is written to GitHub. Only selected bounded turns
are sent over HTTPS. This is separate from the ChatGPT app conversation.
"""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __package__:
    from .inference_adapter import bounded_history
else:
    from inference_adapter import bounded_history

ENDPOINT = "https://api.openai.com/v1/responses"
MAX_BYTES = 524288
MODEL_PATTERN = re.compile(r"[a-zA-Z0-9._-]{1,100}\Z")

INSTRUCTIONS = (
    "You are Odin, an AI assistant running in an AYN Odin 2 Termux "
    "workstation. Be clear about what you know versus what you verified. "
    "Never claim to have executed terminal commands, tested device changes, "
    "pushed to GitHub, or accessed the live ChatGPT app session without a "
    "specific verification receipt. Suggest safe, reviewable development "
    "steps and respect the user's confirmation gates. You cannot execute "
    "commands in this chat interface."
)


class ProviderError(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("OpenAI request unavailable")


def ask_openai(question, history=None):
    if os.environ.get("ODIN_STAGE5_ENABLE_AI") != "1":
        raise RuntimeError("AI is disabled")
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("ODIN_OPENAI_MODEL", "").strip()
    return request_answer(question, history, key=key, model=model)[0]


def request_answer(question, history, *, key, model, max_tokens=700):
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    if not MODEL_PATTERN.fullmatch(model):
        raise RuntimeError("ODIN_OPENAI_MODEL is not configured")
    if not isinstance(question, str) or not 0 < len(question.strip()) <= 4000:
        raise ValueError("Invalid question")

    prompt = [
        *bounded_history(history),
        {"role": "user", "content": question.strip()},
    ]
    payload = {
        "model": model,
        "instructions": INSTRUCTIONS,
        "input": prompt,
        "max_output_tokens": max_tokens,
        "store": False,
    }
    request = Request(
        ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            body = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        exc.close()
        reason = {401: "authentication", 403: "permission", 404: "model_unavailable",
                  429: "quota_or_rate_limit"}.get(exc.code, "provider_http_error")
        raise ProviderError(reason) from None
    except (URLError, OSError, TimeoutError):
        # Do not expose API keys, provider body or raw network errors.
        raise ProviderError("network_error") from None
    if len(body) > MAX_BYTES:
        raise ValueError("OpenAI response exceeds size limit")
    try:
        data = json.loads(body)
        if not isinstance(data, dict) or not isinstance(data.get("output"), list):
            raise TypeError("Invalid response shape")
        parts = [
            content["text"]
            for item in data["output"]
            if isinstance(item, dict) and item.get("type") == "message"
            and isinstance(item.get("content"), list)
            for content in item["content"]
            if isinstance(content, dict) and content.get("type") == "output_text"
            and isinstance(content.get("text"), str)
        ]
        answer = "\n".join(parts).strip()
        if not answer or len(answer) > 20000:
            raise ValueError("Empty or oversized model answer")
        return answer, data
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Invalid OpenAI response") from exc
