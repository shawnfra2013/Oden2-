"""Optional OpenAI Responses API backend for Odin's local AI conversation.

No API key or conversation is written to GitHub. Only selected bounded turns
are sent over HTTPS. This is separate from the ChatGPT app conversation.
"""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def ask_openai(question, history=None):
    if os.environ.get("ODIN_STAGE5_ENABLE_AI") != "1":
        raise RuntimeError("AI is disabled")
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("ODIN_OPENAI_MODEL", "").strip()
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
        "max_output_tokens": 700,
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
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        # Do not expose API keys, provider body or raw network errors.
        raise RuntimeError("OpenAI request unavailable") from None
    if len(body) > MAX_BYTES:
        raise ValueError("OpenAI response exceeds size limit")
    try:
        data = json.loads(body)
        if not isinstance(data, dict) or not isinstance(data.get("output"), list):
            raise ValueError("Invalid response shape")
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
        return answer
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError("Invalid OpenAI response") from exc
