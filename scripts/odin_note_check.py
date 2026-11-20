"""One fixed, local-only check through Stage 5's normal HTTP session."""
import json
from http.client import HTTPConnection
from http.cookies import SimpleCookie


def check(request_id, *, source=False):
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
        if "odin_session" not in cookie:
            raise ValueError("Missing session")
        conn.request("POST", "/api/chat", json.dumps(payload), {
            "Origin": "http://127.0.0.1:8765", "Content-Type": "application/json",
            "X-Odin-Request": "chat", "Cookie": "odin_session=" + cookie["odin_session"].value})
        response = conn.getresponse()
        data = json.loads(response.read(8192))
        return {"match": response.status == 200 and data.get("answer", "").strip() == marker,
                **({"source_revision": revision} if source else {}),
                "http_status": response.status, "elapsed_ms": data.get("elapsed_ms")}
    finally:
        conn.close()
