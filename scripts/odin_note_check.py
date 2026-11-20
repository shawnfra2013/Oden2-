"""One fixed, local-only check through Stage 5's normal HTTP session."""
import json
from http.client import HTTPConnection
from http.cookies import SimpleCookie


def check(request_id):
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
        if "odin_session" not in cookie:
            raise ValueError("Missing session")
        conn.request("POST", "/api/chat", json.dumps(payload), {
            "Origin": "http://127.0.0.1:8765", "Content-Type": "application/json",
            "X-Odin-Request": "chat", "Cookie": "odin_session=" + cookie["odin_session"].value})
        response = conn.getresponse()
        data = json.loads(response.read(8192))
        return {"match": response.status == 200 and data.get("answer", "").strip() == marker,
                "http_status": response.status, "elapsed_ms": data.get("elapsed_ms")}
    finally:
        conn.close()
