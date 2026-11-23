import hmac
import json
import os
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from subprocess import TimeoutExpired

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
WORKSPACE = Path.home() / "odin-workspace"
HOST = "127.0.0.1"
PORT = 8765
MAX_INPUT = 4000

def task_counts():
    base = WORKSPACE / "state" / "task-queue"
    counts = {
        "pending": 0, "running": 0,
        "complete": 0, "failed": 0,
        "unverified": 0, "proposal_ready": 0,
        "other": 0
    }
    for folder in ("pending", "running"):
        directory = base / folder
        if directory.is_dir():
            counts[folder] = sum(
                1 for p in directory.iterdir()
                if p.name.endswith(".json") and not p.is_symlink()
            )
    directory = base / "done"
    if directory.is_dir():
        for path in directory.iterdir():
            if not path.name.endswith(".json") or path.is_symlink():
                continue
            try:
                if path.stat().st_size > 262144:
                    raise ValueError("Oversized record")
                data = json.loads(path.read_text())
                status = data.get("status") if isinstance(data, dict) else None
                if status not in counts or status in ("pending", "running"):
                    status = "other"
                counts[status] += 1
            except (OSError, ValueError, TypeError):
                counts["other"] += 1
    return counts

def ask_ai(question, history=None):
    from chat_provider import ask_model
    return ask_model(question, history)



class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def send_body(self, status, body, kind="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if kind.startswith("text/html") or (status == 200 and self.path == "/api/health"):
            token = getattr(self.server, "session_token", None)
            if token:
                self.send_header(
                    "Set-Cookie",
                    "odin_session=" + token +
                    "; Path=/; HttpOnly; SameSite=Strict"
                )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; "
                         "style-src 'self'; "
                         "script-src 'self'; "
                         "object-src 'none'; "
                         "base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def json_body(self, status, data):
        self.send_body(status, json.dumps(data).encode())

    def authorized_host(self):
        host = getattr(self.server, "request_host", f"{HOST}:{PORT}")
        return (self.client_address[0] == getattr(self.server, "allowed_peer", HOST)
                and self.headers.get_all("Host") == [host])

    def do_GET(self):
        if not self.authorized_host():
            self.json_body(403, {"error": "Invalid host"})
            return
        path = urlsplit(self.path).path
        if path == "/":
            self.send_body(200, (ROOT / "index.html").read_bytes(),
                           "text/html; charset=utf-8")
        elif path == "/style.css":
            self.send_body(
                200, (ROOT / "style.css").read_bytes(),
                "text/css; charset=utf-8"
            )
        elif path == "/api/ui-edits":
            from scripts.odin_ui_edits import current
            try:
                self.json_body(200, current())
            except (OSError, ValueError, RuntimeError, TimeoutExpired):
                self.json_body(503, {"error": "Offline edit store unavailable"})
        elif path == "/icon.svg":
            self.send_body(200, (ROOT / "icon.svg").read_bytes(), "image/svg+xml")
        elif path in {"/app.js", "/device-controls.js", "/ui-settings.js", "/local-tools.js"}:
            self.send_body(
                200, (ROOT / path[1:]).read_bytes(),
                "text/javascript; charset=utf-8"
            )
        elif path == "/api/health":
            self.json_body(200, {
                "service": "odin-stage5",
                "status": "ready",
                "mode": "isolated",
                "ai_enabled": os.environ.get("ODIN_STAGE5_ENABLE_AI") == "1",
                "provider": os.environ.get("ODIN_STAGE5_PROVIDER", "groq"),
                "worker_connected": False
            })
        elif path in {"/api/practice", "/api/practice-followup"}:
            from scripts.odin_practice import notebook
            try:
                self.json_body(200, notebook(followup=path.endswith("-followup")))
            except (sqlite3.Error, OSError, ValueError):
                self.json_body(503, {"error": "Practice notebook unavailable"})
        elif path == "/api/restart":
            from scripts.odin_service_restart import restart_status
            request_id = parse_qs(urlsplit(self.path).query).get("id", [""])[0]
            try:
                self.json_body(200, restart_status(request_id))
            except (OSError, ValueError):
                self.json_body(404, {"error": "Restart receipt unavailable"})
        elif path == "/api/source":
            from source_lookup import lookup
            if os.environ.get("ODIN_STAGE5_PROVIDER") != "local":
                self.json_body(409, {"error": "Local provider required"})
                return
            params = parse_qs(urlsplit(self.path).query)
            if set(params) != {"symbol"} or len(params["symbol"]) != 1:
                self.json_body(400, {"error": "Enter one function name"})
                return
            try:
                self.json_body(200, lookup(params["symbol"][0]))
            except ValueError:
                self.json_body(400, {"error": "Invalid function name"})
            except (RuntimeError, OSError, TimeoutExpired):
                self.json_body(503, {"error": "Source unavailable"})
        elif path == "/api/tasks":
            self.json_body(200, {"counts": task_counts(),
                                 "access": "read_only"})
        else:
            self.json_body(404, {"error": "Not found"})

    def do_POST(self):
        if not self.authorized_host():
            self.json_body(403, {"error": "Invalid host"})
            return
        host = getattr(self.server, "request_host", f"{HOST}:{PORT}")
        if self.headers.get_all("Origin") != [f"http://{host}"]:
            self.json_body(403, {"error": "Invalid origin"})
            return
        if self.headers.get("X-Odin-Request") != "chat":
            self.json_body(403, {"error": "Invalid request"})
            return
        token = getattr(self.server, "session_token", None)
        cookie = self.headers.get("Cookie", "")
        supplied = ""
        for part in cookie.split(";"):
            name, separator, value = part.strip().partition("=")
            if separator and name == "odin_session":
                supplied = value
                break
        if not token or not hmac.compare_digest(supplied, token):
            self.json_body(403, {"error": "Session authentication required"})
            return
        path = urlsplit(self.path).path
        if path not in {"/api/chat", "/api/ui-edits", "/api/restart"}:
            self.json_body(404, {"error": "Not found"})
            return
        if self.headers.get("Content-Type") != "application/json":
            self.json_body(415, {"error": "JSON required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= 8192:
            self.json_body(413, {"error": "Invalid request size"})
            return
        try:
            data = json.loads(self.rfile.read(length))
            if path == "/api/restart":
                from scripts.odin_service_restart import ID_RE, start_restart
                if (not isinstance(data, dict) or set(data) != {"id"}
                        or not isinstance(data["id"], str) or not ID_RE.fullmatch(data["id"])):
                    raise ValueError("Invalid restart request")
                try:
                    accepted = start_restart(data["id"])
                except (OSError, RuntimeError):
                    self.json_body(503, {"error": "Restart unavailable"})
                    return
                self.json_body(202 if accepted else 409, {
                    "accepted": accepted,
                    "error": "" if accepted else "Restart already requested or cooling down",
                })
                return
            if path == "/api/ui-edits":
                from scripts.odin_ui_edits import approve
                if not isinstance(data, dict) or set(data) != {"settings", "version"}:
                    raise ValueError("Invalid edit")
                try:
                    self.json_body(200, approve(data["settings"], data["version"]))
                except ValueError as exc:
                    self.json_body(400, {"error": str(exc)})
                except (OSError, RuntimeError, TimeoutExpired):
                    self.json_body(409, {"error": "Could not save. Reload and review your settings."})
                return
            question = data.get("message") if isinstance(data, dict) else None
            if not isinstance(question, str) or not 0 < len(question.strip()) <= MAX_INPUT:
                raise ValueError("Invalid message")
        except (ValueError, UnicodeDecodeError):
            self.json_body(400, {"error": "Invalid JSON or message"})
            return
        conversation_id = data.get("conversation_id")
        if conversation_id is not None and (
            not isinstance(conversation_id, str)
            or len(conversation_id) != 32
            or any(char not in "0123456789abcdef" for char in conversation_id)
        ):
            self.json_body(400, {"error": "Invalid conversation ID"})
            return
        if (getattr(self.server, "allowed_peer", HOST) != HOST
                and os.environ.get("ODIN_STAGE5_PROVIDER") != "local"):
            self.json_body(503, {"error": "Phone chat requires Odin's local model"})
            return
        if os.environ.get("ODIN_STAGE5_ENABLE_AI") != "1":
            self.json_body(503, {"error": "AI not enabled yet"})
            return
        options = data.get("local_options")
        if "local_options" in data:
            if os.environ.get("ODIN_STAGE5_PROVIDER") != "local":
                self.json_body(409, {"error": "Local provider required"})
                return
            if (not isinstance(options, dict) or set(options) != {"reference", "quick"}
                    or type(options["quick"]) is not bool or not isinstance(options["reference"], str)
                    or len(options["reference"].encode("utf-8", "surrogatepass")) > 1600):
                self.json_body(400, {"error": "Invalid local chat options"})
                return
        lock = getattr(self.server, "chat_lock", None)
        if lock is None:
            self.json_body(503, {"error": "Chat concurrency unavailable"})
            return
        if not lock.acquire(blocking=False):
            self.json_body(429, {"error": "AI request already in progress"})
            return
        try:
            try:
                store = getattr(self.server, "conversations", None)
                if conversation_id is not None and (store is None or not store.exists(conversation_id)):
                    self.json_body(404, {"error": "Conversation not found"})
                    return
                history = store.get_messages(conversation_id, limit=12) if conversation_id else None
                started = time.monotonic()
                if options:
                    from local_adapter import ask_local
                    answer = ask_local(question, history, **options)
                else:
                    answer = ask_ai(question) if history is None else ask_ai(question, history)
                elapsed_ms = round((time.monotonic() - started) * 1000)
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("Empty or invalid model response")
                if store is not None:
                    conversation_id = conversation_id or store.create()
                    store.append_turn(conversation_id, question, answer)
            except (
                sqlite3.Error,
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                TimeoutError,
                KeyError,
            ) as exc:
                print(
                    "AI request failed:",
                    type(exc).__name__,
                    flush=True,
                )
                self.json_body(
                    502,
                    {"error": "AI request failed; inspect server status"},
                )
                return
            self.json_body(200, {
                "answer": answer,
                "elapsed_ms": elapsed_ms,
                "verification": "unverified",
                "persisted": store is not None,
                **({"conversation_id": conversation_id} if store is not None else {})
            })
        finally:
            lock.release()

    def log_message(self, format, *args):
        pass

def main():
    from offline_profile import activate
    from phone_access import start
    activate(os.environ)
    if os.environ.get("ODIN_STAGE5_PROVIDER") != "local":
        os.environ["ODIN_STAGE5_PROVIDER"] = "local"
        os.environ["ODIN_STAGE5_ENABLE_AI"] = "0"
    from conversation_store import ConversationStore

    db_path = Path(os.environ.get("ODIN_STAGE5_DB", Path(__file__).resolve().parent.parent / "state" / "conversations.db"))
    store = ConversationStore(db_path)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.conversations = store
    server.daemon_threads = True
    server.chat_lock = threading.BoundedSemaphore(1)
    server.session_token = secrets.token_urlsafe(32)
    stop_phone = start(server, Handler)
    print(f"Odin web app: http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_phone.set()
        server.server_close()

if __name__ == "__main__":
    main()
