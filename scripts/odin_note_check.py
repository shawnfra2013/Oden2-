"""One fixed, local-only check through Stage 5's normal HTTP session."""
import ast
import json
from http.client import HTTPConnection
from http.cookies import SimpleCookie


def byte_count_proposal(answer):
    """Compare a proposed expression as data. Never run generated code."""
    lines = answer.strip().splitlines()
    if len(lines) >= 3 and lines[0] in {"```", "```python"} and lines[-1] == "```":
        lines = lines[1:-1]
    proposal = "\n".join(lines).strip()
    accepted = False
    if 0 < len(proposal) <= 160:
        try:
            tree = ast.dump(ast.parse(proposal, mode="eval"))
            accepted = any(tree == ast.dump(ast.parse(expr, mode="eval")) for expr in (
                "len(text.encode())", "len(text.encode('utf-8'))", "len(text.encode('utf8'))"))
        except (ValueError, SyntaxError):
            pass
    return proposal[:160], accepted


def check(request_id, *, source=False, coding=False):
    conn = HTTPConnection("127.0.0.1", 8765, timeout=190)
    try:
        conn.request("GET", "/api/health")
        response = conn.getresponse()
        cookie = SimpleCookie()
        cookie.load(response.getheader("Set-Cookie", ""))
        health = json.loads(response.read(4096))
        if health.get("provider") != "local" or health.get("ai_enabled") is not True:
            raise ValueError("Local provider required")
        marker = "ODIN-" + request_id[:8]
        payload = {"message": "What is the project code? Reply with only the exact code.",
                   "local_options": {"reference": "The project code is " + marker + ".", "quick": True}}
        revision = None
        if source:
            conn.request("GET", "/api/source?symbol=local_settings")
            response = conn.getresponse()
            found = json.loads(response.read(12000))
            if response.status != 200 or len(found.get("matches", [])) != 1:
                raise ValueError("Missing unique source")
            item = found["matches"][0]
            if not item["label"].startswith("stage5/local_adapter.py:"):
                raise ValueError("Unexpected source")
            revision = found["revision"]
            marker = "8080"
            payload = {"message": "According to the supplied function, when ODIN_LOCAL_PORT is absent, "
                       "what default port does it use? Reply only with the number.",
                       "local_options": {"quick": True, "reference": item["reference"]}}
        if coding:
            payload = {"message": "Write one Python expression that returns the number of UTF-8 "
                       "bytes in the string named text. Reply only with the expression.",
                       "local_options": {"quick": True}}
        if "odin_session" not in cookie:
            raise ValueError("Missing session")
        conn.request("POST", "/api/chat", json.dumps(payload), {
            "Origin": "http://127.0.0.1:8765", "Content-Type": "application/json",
            "X-Odin-Request": "chat", "Cookie": "odin_session=" + cookie["odin_session"].value})
        response = conn.getresponse()
        data = json.loads(response.read(8192))
        if coding:
            proposal, accepted = byte_count_proposal(data.get("answer", ""))
            return {"match": response.status == 200 and accepted, "proposal": proposal,
                    "review": "pending", "http_status": response.status,
                    "elapsed_ms": data.get("elapsed_ms")}
        return {"match": response.status == 200 and data.get("answer", "").strip() == marker,
                **({"source_revision": revision} if source else {}),
                "http_status": response.status, "elapsed_ms": data.get("elapsed_ms")}
    finally:
        conn.close()
