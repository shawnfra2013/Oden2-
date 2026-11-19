"""Verify Odin Control through its existing authenticated API."""
import getpass
import json
import re
import time
import urllib.error
import urllib.request

ORIGIN = "https://odin-control.vercel.app"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = urllib.request.build_opener(NoRedirect())


def request(path, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        ORIGIN + "/api/" + path, data=data,
        headers={"Authorization": "Bearer " + token, "Origin": ORIGIN,
                 "Content-Type": "application/json"},
    )
    try:
        with OPENER.open(req, timeout=55) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, {}


def storage(token):
    status, body = request("relay", token)
    return status == 200 and body.get("connected") is True and body.get("source") == "private-odin-relay", f"HTTP {status}"


def cloud(token):
    status, body = request("chat", token, {"message": "Reply with ODIN_CLOUD_OK.", "history": []})
    answer = body.get("answer")
    return status == 200 and body.get("source") == "openai-api" and isinstance(answer, str) and bool(answer.strip()), f"HTTP {status}"


def ping(token):
    status, body = request("command", token, {"action": "ping"})
    request_id = body.get("id", "")
    if status != 202 or not re.fullmatch(r"[0-9a-f]{32}", request_id):
        return False, f"submission HTTP {status}"
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        status, body = request("status", token)
        if status == 200:
            for receipt in body.get("receipts", []):
                if receipt.get("id") == request_id and receipt.get("action") == "ping":
                    return (receipt.get("status") == "complete" and receipt.get("result", {}).get("alive") is True), f"receipt {request_id}"
        time.sleep(3)
    return False, f"no matching receipt within polling window for {request_id}"


def main():
    token = getpass.getpass("Odin Control access token: ")
    if not re.fullmatch(r"[A-Za-z0-9._~-]{32,256}", token):
        raise SystemExit("Invalid token format")
    passed = True
    for check in (storage, cloud, ping):
        try:
            ok, detail = check(token)
        except (OSError, ValueError):
            ok, detail = False, "transport or response error"
        print(f"{check.__name__}: {'PASS' if ok else 'FAIL'} ({detail})", flush=True)
        passed = passed and ok
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
