"""Keyless chat with a user-managed OpenAI-compatible loopback server."""
import json
import os
import re
from http.client import HTTPConnection

from inference_adapter import bounded_history


def local_settings(env):
    model = env.get("ODIN_LOCAL_MODEL", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model):
        raise ValueError("Set ODIN_LOCAL_MODEL to the served model ID")
    port = int(env.get("ODIN_LOCAL_PORT", "8080"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid local model port")
    return model, port


def ask_local(question, history=None):
    if os.environ.get("ODIN_STAGE5_ENABLE_AI") != "1":
        raise RuntimeError("AI disabled")
    if not isinstance(question, str) or not 0 < len(question.strip()) <= 4000:
        raise ValueError("Invalid question")
    model, port = local_settings(os.environ)
    messages = [*bounded_history(history), {"role": "user", "content": question}]
    body = json.dumps(dict(model=model, messages=messages, max_tokens=700, stream=False))
    connection = HTTPConnection("127.0.0.1", port, timeout=180)
    try:
        connection.request("POST", "/v1/chat/completions", body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError("Local model unavailable")
        data = response.read(262145)
        if len(data) > 262144:
            raise ValueError("Oversized local model response")
        try:
            answer = json.loads(data)["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("Invalid local model response") from exc
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty local model answer")
        return answer.strip()
    finally:
        connection.close()
