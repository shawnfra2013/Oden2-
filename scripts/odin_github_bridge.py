"""GitHub-backed, allowlisted Odin status bridge (no arbitrary shell requests).

Inbox and outbox are separate branches, never the checked-out main branch.
Only fixed, read-only diagnostic actions are accepted. Public-repo receipts
contain structured booleans/counts, never command output or local file names.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "github-bridge"
OUTBOX = STATE / "outbox"
INBOX_BRANCH = "odin-bridge-inbox"
OUTBOX_BRANCH = "odin-bridge-outbox"
ACTIONS = frozenset({"ping", "repo_status", "services", "stage5_health", "checks"})
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
REQUEST_KEYS = {"version", "id", "action", "created_at", "expires_at"}
ORIGINS = {
    "git@github.com:shawnfra2013/Oden2-.git",
    "https://github.com/shawnfra2013/Oden2-.git",
}
POLL_SECONDS = 60


class ExpiredRequest(ValueError):
    """A request is authentic in shape but no longer actionable."""


def utcnow():
    return datetime.now(UTC)


def iso(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Timestamp must be UTC")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("Timestamp needs timezone")
    return dt


def validate_request(raw, expected_id, now=None):
    """Validate a bounded, expiring command-free GitHub request."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 4096:
        raise ValueError("Invalid request size")
    if not ID_PATTERN.fullmatch(expected_id):
        raise ValueError("Invalid ID")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or set(payload) != REQUEST_KEYS:
        raise ValueError("Invalid request fields")
    if payload["version"] != 1 or payload["id"] != expected_id:
        raise ValueError("Invalid version or ID")
    if payload["action"] not in ACTIONS:
        raise ValueError("Action not allowlisted")
    created = parse_utc(payload["created_at"])
    expires = parse_utc(payload["expires_at"])
    current = now or utcnow()
    if not timedelta(0) < expires - created <= timedelta(hours=1):
        raise ValueError("Invalid expiry window")
    if created > current + timedelta(minutes=5):
        raise ValueError("Request issued in the future")
    if expires <= current:
        raise ExpiredRequest("Expired")
    return payload


def run(argv, *, cwd=ROOT, timeout=45, allow_failure=False):
    result = subprocess.run(
        argv, cwd=cwd, text=True, capture_output=True,
        timeout=timeout, check=False,
    )
    if result.returncode and not allow_failure:
        raise RuntimeError("Command failed: " + argv[0])
    return result


def git(*args, cwd=ROOT, timeout=45):
    return run(["git", *args], cwd=cwd, timeout=timeout).stdout.strip()


def checked_origin():
    origin = git("remote", "get-url", "origin")
    if origin not in ORIGINS:
        raise RuntimeError("Unexpected GitHub origin; refusing bridge")
    return origin


def log(message):
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / "agent.log"
    if path.exists() and path.stat().st_size > 131072:
        path.replace(STATE / "agent.previous.log")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(iso(utcnow()) + " " + message + "\n")
    print(message, flush=True)


def ensure_outbox(origin):
    if not (OUTBOX / ".git").is_dir():
        if OUTBOX.exists():
            raise RuntimeError("Outbox path exists but is not a Git clone")
        STATE.mkdir(parents=True, exist_ok=True)
        run(
            ["git", "clone", "--quiet", "--single-branch", "--no-tags",
             "--branch", OUTBOX_BRANCH, origin, str(OUTBOX)],
            timeout=90,
        )
        git("config", "user.name", "Odin Bridge", cwd=OUTBOX)
        git("config", "user.email", "odin-bridge@users.noreply.github.com", cwd=OUTBOX)
    if git("branch", "--show-current", cwd=OUTBOX) != OUTBOX_BRANCH:
        raise RuntimeError("Unexpected outbox branch")
    if git("remote", "get-url", "origin", cwd=OUTBOX) != origin:
        raise RuntimeError("Unexpected outbox origin")
    if git("status", "--porcelain", cwd=OUTBOX):
        raise RuntimeError("Outbox has uncommitted changes; refusing edits")
    git("pull", "--ff-only", "origin", OUTBOX_BRANCH, cwd=OUTBOX, timeout=90)
    ahead = int(git("rev-list", "--count", "origin/" + OUTBOX_BRANCH + "..HEAD", cwd=OUTBOX))
    if ahead:
        git("push", "origin", "HEAD:refs/heads/" + OUTBOX_BRANCH, cwd=OUTBOX, timeout=90)


def fetch_inbox():
    git("fetch", "--quiet", "origin",
        "refs/heads/" + INBOX_BRANCH + ":refs/remotes/origin/" + INBOX_BRANCH,
        timeout=90)


def status_action(action):
    if action == "ping":
        return {"alive": True, "bridge_version": 1}
    if action == "repo_status":
        tracked_clean = (
            run(["git", "diff", "--quiet"], allow_failure=True).returncode == 0
            and run(["git", "diff", "--cached", "--quiet"], allow_failure=True).returncode == 0
        )
        files = git("ls-files", "--others", "--exclude-standard")
        return {
            "head": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "tracked_clean": tracked_clean,
            "untracked_count": len(files.splitlines()) if files else 0,
        }
    if action == "services":
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        values = {}
        for name in ("odin-git-sync", "odin-task-worker"):
            path = str(Path(prefix) / "var" / "service" / name)
            result = run(["sv", "status", path], timeout=10, allow_failure=True)
            values[name] = (
                result.returncode == 0 and result.stdout.startswith("run: ")
            )
        return values
    if action == "stage5_health":
        try:
            with urlopen("http://127.0.0.1:8765/api/health", timeout=4) as response:
                data = json.loads(response.read(4096))
            return {
                "reachable": True,
                "ready": data.get("status") == "ready",
                "ai_enabled": data.get("ai_enabled") is True,
            }
        except (OSError, ValueError, URLError):
            return {"reachable": False}
    if action == "checks":
        checks = [
            ("stage4", [sys.executable, "-B", "-m", "unittest", "discover",
                        "-s", "tests", "-p", "test*.py", "-q"]),
            ("stage5", [sys.executable, "-B", "-m", "unittest", "discover",
                        "-s", "stage5", "-p", "test_*.py", "-q"]),
            ("ruff", ["ruff", "check", "."]),
        ]
        result = {}
        for name, command in checks:
            try:
                result[name + "_passed"] = (
                    run(command, timeout=90, allow_failure=True).returncode == 0
                )
            except (OSError, subprocess.TimeoutExpired):
                result[name + "_passed"] = False
        return result
    raise ValueError("Unsupported action")


def send_response(request_id, payload):
    relative = Path("bridge") / "responses" / (request_id + ".json")
    destination = OUTBOX / relative
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    git("add", "--", relative.as_posix(), cwd=OUTBOX)
    git("commit", "-m", "Odin bridge response " + request_id, cwd=OUTBOX)
    git("push", "origin", "HEAD:refs/heads/" + OUTBOX_BRANCH, cwd=OUTBOX, timeout=90)


def process_once():
    origin = checked_origin()
    ensure_outbox(origin)
    fetch_inbox()
    ref = "origin/" + INBOX_BRANCH
    names = git("ls-tree", "-r", "--name-only", ref, "--", "bridge/requests")
    processed = 0
    for name in names.splitlines():
        if processed >= 5:
            break
        if not name.startswith("bridge/requests/") or not name.endswith(".json"):
            continue
        request_id = Path(name).stem
        if not ID_PATTERN.fullmatch(request_id):
            continue
        if (OUTBOX / "bridge" / "responses" / (request_id + ".json")).exists():
            continue
        action = "none"
        try:
            raw = git("show", ref + ":" + name, timeout=20)
            request = validate_request(raw, request_id)
            action = request["action"]
            details = status_action(action)
            status = "complete"
        except ExpiredRequest:
            details, status = {}, "expired"
        except (OSError, ValueError, TypeError, RuntimeError,
                subprocess.TimeoutExpired):
            details, status = {}, "rejected_or_failed"
        receipt = {
            "version": 1, "id": request_id, "action": action,
            "status": status, "checked_at": iso(utcnow()),
            "result": details,
        }
        send_response(request_id, receipt)
        processed += 1
        log("Published " + request_id + " status=" + status)
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="Run one polling cycle")
    group.add_argument("--serve", action="store_true", help="Poll every 60 seconds")
    args = parser.parse_args()
    if args.serve:
        while True:
            try:
                process_once()
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                log("Poll error: " + type(exc).__name__)
            time.sleep(POLL_SECONDS)
    else:
        print("Processed requests:", process_once())


if __name__ == "__main__":
    main()
