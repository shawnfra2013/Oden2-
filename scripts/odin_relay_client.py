"""Private, message-only Odin ↔ iPhone agent relay.

This daemon NEVER executes arbitrary instructions, installs packages or
edits Git. It polls an authenticated HTTPS API, records delivery/read
receipts and replies using Odin's already configured conversational model.

Requires a locally entered token in $HOME/odin-workspace/state/odin-relay/token
(mode 0600). The matching secret must be configured in Vercel as
ODIN_DEVICE_RELAY_TOKEN; it is not stored in GitHub or published in receipts.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "odin-relay"
TOKEN_FILE = STATE / "token"
SEEN_FILE = STATE / "processed.json"
API = "https://odin-control.vercel.app/api/relay"
MAX_RESPONSE = 150000
POLL_SECONDS = 45


def read_token():
    if not TOKEN_FILE.is_file():
        raise RuntimeError("Private relay pairing token not installed")
    if TOKEN_FILE.stat().st_mode & 0o077:
        raise RuntimeError("Relay token file must be chmod 600")
    value = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if len(value) < 32 or len(value) > 256:
        raise RuntimeError("Invalid relay token length")
    return value


def request(token, payload=None):
    body = None if payload is None else json.dumps(
        payload, separators=(",", ":")).encode("utf-8")
    req = Request(
        API,
        data=body,
        method="GET" if body is None else "POST",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            **({"Content-Length": str(len(body))} if body is not None else {}),
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            content = response.read(MAX_RESPONSE + 1)
            if len(content) > MAX_RESPONSE:
                raise ValueError("Relay response exceeded limit")
            return json.loads(content)
    except HTTPError as error:
        # A status code is safe to log; do not print response bodies, tokens
        # or message text in this supervised background process.
        raise RuntimeError(f"Odin relay HTTP {error.code} on {req.get_method()}") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("Odin relay transport unavailable") from None


def load_seen():
    try:
        obj = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            return {x for x in obj if isinstance(x, str) and len(x) == 32}
    except (FileNotFoundError, ValueError, OSError):
        pass
    return set()


def save_seen(ids):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = SEEN_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(sorted(ids)[-300:]), encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(SEEN_FILE)


def handle_message(token, msg, seen, answer_fn):
    mid = msg.get("id")
    if not isinstance(mid, str) or len(mid) != 32 or any(
        x not in "0123456789abcdef" for x in mid
    ):
        return False
    if mid in seen or msg.get("to") != "odin" or msg.get("sender") != "iphone":
        return False
    text = msg.get("text")
    if not isinstance(text, str) or not 0 < len(text.strip()) <= 2000:
        return False
    if msg.get("status") in ("replied", "failed"):
        seen.add(mid)
        return False

    # Best-effort idempotency: a repeated receipt is harmless; duplicate
    # replies are also refused server-side by their original message ID.
    if msg.get("status") == "queued":
        request(token, {"type": "receipt", "for": mid, "state": "delivered"})
    request(token, {"type": "receipt", "for": mid, "state": "read"})
    try:
        # A transport test is deliberately not AI inference or a shell command.
        # It works when model credentials are unavailable, proving the real
        # Odin process received and replied to the authenticated message.
        answer = (
            "ODIN_RELAY_PONG — reply generated on the Odin device; "
            "AI inference not used."
            if text.strip() == "/ping" else answer_fn(text)
        )
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("No model response")
        answer = answer.strip()[:2000]
    except (RuntimeError, ValueError, OSError):
        request(token, {"type": "receipt", "for": mid, "state": "failed"})
        seen.add(mid)
        save_seen(seen)
        return True
    try:
        request(token, {"type": "reply", "for": mid, "text": answer})
    except RuntimeError:
        # Do not mark processed. A retry may receive a server-side conflict
        # when it already accepted a reply; status will resolve on next poll.
        return False
    seen.add(mid)
    save_seen(seen)
    return True


def respond_with_odin(text):
    # The existing local CLI reuses the existing bounded model and SQLite
    # history. No model output is executed as a command.
    from odin_chat import (
        DB_FILE,
        SESSION_FILE,
        ConversationStore,
        load_session,
        reply,
        save_session,
    )

    store = ConversationStore(DB_FILE)
    previous = load_session(store, SESSION_FILE)
    current, answer = reply(store, text, previous)
    save_session(current, SESSION_FILE)
    return answer


def poll_once(token, answer_fn=respond_with_odin):
    payload = request(token)
    if payload.get("source") != "private-odin-relay":
        raise RuntimeError("Unexpected relay response")
    seen = load_seen()
    processed = 0
    for msg in payload.get("messages", [])[:30]:
        if handle_message(token, msg, seen, answer_fn):
            processed += 1
    return processed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--serve", action="store_true")
    args = parser.parse_args(argv)
    token = read_token()
    if args.serve:
        while True:
            try:
                poll_once(token)
            except (RuntimeError, ValueError, OSError) as error:
                print(f"Private relay poll failed: {error}", file=sys.stderr, flush=True)
            time.sleep(POLL_SECONDS)
    else:
        print("Handled private messages:", poll_once(token))


if __name__ == "__main__":
    main()
