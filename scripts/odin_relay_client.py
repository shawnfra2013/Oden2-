"""Private, message-only Odin ↔ iPhone agent relay.

This daemon NEVER executes arbitrary instructions, installs packages or
edits Git. It polls an authenticated HTTPS API, records delivery/read
receipts and replies using Odin's already configured conversational model.

Requires a locally entered token in $HOME/odin-workspace/state/odin-relay/token
(mode 0600). The matching secret must be configured in Vercel as
ODIN_DEVICE_RELAY_TOKEN; it is not stored in GitHub or published in receipts.
"""
import argparse
import contextlib
import fcntl
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "odin-relay"
TOKEN_FILE = STATE / "token"
SEEN_FILE = STATE / "processed.json"
LOCK_FILE = STATE / "poll.lock"
STATUS_FILE = STATE / "relay-status.json"
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


def status_reply(mode):
    """Only fixed, bounded read-only device tasks; no model-generated commands."""
    def command(*args, binary=False):
        result = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True,
            text=not binary, check=False, timeout=12
        )
        if result.returncode:
            raise RuntimeError("Read-only Git status check failed")
        return result.stdout

    head = command("rev-parse", "HEAD").strip()
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise RuntimeError("Invalid Git revision")
    tracked = command("status", "--porcelain", "--untracked-files=no")
    untracked = command("ls-files", "--others", "--exclude-standard", "-z", binary=True)
    details = ("head=" + head[:12] + " tracked_clean=" + str(not bool(tracked.strip())).lower()
               + " untracked_count=" + str(len([p for p in untracked.split(b"\0") if p])))
    if mode == "/task git-status":
        return "ODIN_TASK_COMPLETE verified=true task=git-status " + details
    if mode == "/task queue-status":
        queue = ROOT / "state" / "task-queue"
        counts = {
            key: sum(1 for _ in (queue / key).glob("*.json"))
            for key in ("pending", "running", "done")
        }
        return ("ODIN_TASK_COMPLETE verified=true task=queue-status "
                + " ".join(key + "=" + str(value) for key, value in counts.items())
                + " " + details)
    return "ODIN_STATUS_VERIFIED " + details


@contextlib.contextmanager
def exclusive_poll():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another Odin relay poll is already active") from None
        yield
    finally:
        os.close(fd)


def write_poll_status(handled, failed, count):
    """Keep private operational evidence without storing messages or keys."""
    record = {
        "checked_at": datetime.now(UTC).isoformat(),
        "processed": handled, "failed": failed, "inbox_count": count,
        "ok": failed == 0,
    }
    temp = STATE / ("relay-status-" + str(os.getpid()) + ".tmp")
    with temp.open("x", encoding="utf-8") as handle:
        os.chmod(temp, 0o600)
        json.dump(record, handle)
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(STATUS_FILE)


def normalized_action(text):
    """Recognize only exact read-only tasks; never parse free-form shell text."""
    command = " ".join(text.strip().lower().split())
    known = {
        "/ping": "ping",
        "ping odin": "ping",
        "/status": "git_status_summary",
        "device status": "git_status_summary",
        "show device status": "git_status_summary",
        "/task git-status": "git_status",
        "task git-status": "git_status",
        "git status": "git_status",
        "check git status": "git_status",
        "show git status": "git_status",
        "/task queue-status": "queue_status",
        "task queue-status": "queue_status",
        "queue status": "queue_status",
        "check queue status": "queue_status",
        "/ai-status": "ai_status",
        "ai status": "ai_status",
        "model status": "ai_status",
        "/ai-test": "ai_test",
    }
    if command in known:
        return known[command]
    if command.startswith(("/task", "task ", "/ai-")):
        return "unsupported_command"
    return None


def local_ai_status():
    """Read the running relay's AI environment, never the key's value."""
    stage5 = str(ROOT / "stage5")
    if stage5 not in sys.path:
        sys.path.insert(0, stage5)
    from chat_provider import provider_status

    return provider_status()


def ai_status_reply():
    state = local_ai_status()
    return ("ODIN_AI_STATUS "
            + " ".join(
                key + "=" + str(state[key]).lower()
                if isinstance(state[key], bool) else key + "=" + state[key]
                for key in ("provider", "enabled", "credential_present",
                            "model_configured", "ready", "reason")
            ))


def failure_code(error, action):
    """Return one fixed diagnostic code without leaking provider exceptions."""
    if action in {"git_status", "git_status_summary", "queue_status"}:
        return "task_failed"
    if action == "ai_status":
        return "status_unavailable"
    try:
        state = local_ai_status()
        if not state["ready"]:
            return state["reason"]
    except (RuntimeError, ValueError, OSError, ImportError):
        return "provider_unavailable"
    if isinstance(error, TimeoutError):
        return "provider_timeout"
    if isinstance(error, (ValueError, TypeError)):
        return "model_response_invalid"
    return "provider_unavailable"


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
        action = normalized_action(text)
        if action == "ping":
            answer = ("ODIN_RELAY_PONG — reply generated on the Odin device; "
                      "AI inference not used.")
        elif action == "git_status_summary":
            answer = status_reply("/status")
        elif action == "git_status":
            answer = status_reply("/task git-status")
        elif action == "queue_status":
            answer = status_reply("/task queue-status")
        elif action == "ai_status":
            answer = ai_status_reply()
        elif action == "unsupported_command":
            answer = ("ODIN_TASK_REJECTED: supported: /ping, /status, "
                      "/task git-status, /task queue-status, /ai-status, /ai-test")
        elif action == "ai_test":
            result = answer_fn("Reply briefly with the words Odin AI ready.")
            answer = ("ODIN_AI_TEST_RESPONSE (provider answer, not task proof): "
                      + result)
        else:
            # Normal conversation uses the existing provider and local SQLite
            # history. A model answer is not a verified device action.
            answer = answer_fn(text)
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty model or task response")
        answer = answer.strip()[:2000]
    except (RuntimeError, ValueError, OSError, ImportError, TypeError) as error:
        request(token, {
            "type": "receipt", "for": mid, "state": "failed",
            "reason": failure_code(error, normalized_action(text))
        })
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
    with exclusive_poll():
        payload = request(token)
        if payload.get("source") != "private-odin-relay":
            raise RuntimeError("Unexpected relay response")
        messages = payload.get("messages", [])
        if not isinstance(messages, list) or len(messages) > 200:
            raise RuntimeError("Unexpected private relay message count")
        seen = load_seen()
        processed, failed, inspected = 0, 0, 0
        for msg in messages:
            if not isinstance(msg, dict):
                failed += 1
                continue
            if msg.get("sender") != "iphone" or msg.get("to") != "odin":
                continue
            if msg.get("id") in seen or msg.get("status") in ("replied", "failed"):
                continue
            if inspected >= 30:
                break
            inspected += 1
            try:
                if handle_message(token, msg, seen, answer_fn):
                    processed += 1
            except (RuntimeError, ValueError, OSError) as error:
                failed += 1
                # Never log a prompt, model response, private URL, or key.
                print("ODIN_RELAY_MESSAGE_FAILURE id_tail="
                      + str(msg.get("id", ""))[-6:] + " type="
                      + type(error).__name__, file=sys.stderr, flush=True)
                # Continue other independent messages instead of blocking the
                # entire inbox behind one failed receipt.
        write_poll_status(processed, failed, len(messages))
        if failed:
            raise RuntimeError(str(failed) + " private message(s) failed; see relay-status.json")
        return processed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--serve", action="store_true")
    mode.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.status:
        try:
            record = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            print("Private relay status:", json.dumps(record, sort_keys=True))
        except (FileNotFoundError, OSError, ValueError):
            print("Private relay status: no completed poll record")
        return
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
