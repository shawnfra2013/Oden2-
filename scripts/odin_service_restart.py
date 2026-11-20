"""Authenticated, allowlisted restart of Odin's existing runit services.

The private relay queues one exact restart request. This *detached helper*
restarts configured services (relay LAST) and records a durable outcome.
The restarted relay publishes the final private reply on its next poll.
No arbitrary command, reboot, package change, credential or Git edit.
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST_DIR = ROOT / "state" / "odin-relay" / "restarts"
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
SERVICES = ("odin-git-sync", "odin-task-worker", "odin-github-bridge",
            "odin-stage5", "odin-private-relay")
MANDATORY = frozenset({"odin-git-sync", "odin-task-worker",
                       "odin-private-relay"})
COOLDOWN_SECONDS = 600
STALE_SECONDS = 300


def now():
    return time.time()


def record_path(message_id):
    if not ID_RE.fullmatch(message_id):
        raise ValueError("Invalid private restart request ID")
    return REQUEST_DIR / (message_id + ".json")


def read_record(path):
    if path.is_symlink():
        raise ValueError("Unsafe restart record path")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not ID_RE.fullmatch(data.get("id", "")):
        raise ValueError("Invalid restart record")
    return data


def save_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".odin-restart-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(record, output, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def reserve_restart(message_id, *, state_dir=REQUEST_DIR, clock=now, service=None):
    """Create an idempotent durable intent. Return False for rate-limited."""
    if service is not None and service not in SERVICES:
        raise ValueError("Invalid restart service")
    path = state_dir / (message_id + ".json")
    if not ID_RE.fullmatch(message_id):
        raise ValueError("Invalid private restart request ID")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    gate = state_dir / "request.lock"
    fd = os.open(gate, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if path.exists():
            return False
        instant = clock()
        for other in state_dir.glob("*.json"):
            try:
                row = read_record(other)
            except (OSError, ValueError, TypeError):
                # Do not auto-delete private state, and do not bypass
                # a cooldown based on malformed records.
                raise RuntimeError("Cannot verify restart history") from None
            if 0 <= instant - row.get("created_at", instant) < COOLDOWN_SECONDS:
                return False
        # Exclusive create prevents duplicate launch of an identical ID.
        claim = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(claim, "w", encoding="utf-8") as file:
            json.dump({"id": message_id, "phase": "queued",
                       "created_at": instant, "service": service}, file)
            file.flush()
            os.fsync(file.fileno())
        return True
    finally:
        os.close(fd)


def start_restart(message_id, *, service=None):
    """Schedule in a detached process; no token or secret in argv."""
    if not reserve_restart(message_id, service=service):
        return False
    try:
        subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()),
             "--execute", message_id],
            cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True,
        )
    except OSError:
        path = record_path(message_id)
        data = read_record(path)
        data["phase"] = "finished"
        data["completed_at"] = now()
        data["reply"] = ("ODIN_SERVICES_RESTART_RESULT verified=false "
                         "reason=helper_launch_failed")
        save_record(path, data)
        return True
    return True


def svc_call(cmd, path, *, timeout=25):
    return subprocess.run(["sv", cmd, str(path)], check=False,
                          capture_output=True, text=True, timeout=timeout)


def restart_configured(*, state_dir=REQUEST_DIR, prefix=None, call=svc_call,
                       after_update=False, service=None):
    if service is not None and (service not in SERVICES or after_update):
        raise ValueError("Invalid restart service")
    targets = SERVICES if service is None else (service,)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state_dir / "execution.lock",
                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "rb") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return "ODIN_SERVICES_RESTART_RESULT verified=false reason=restart_in_progress", False
        return restart_under_lock(prefix, call, after_update, targets)


def restart_under_lock(prefix, call, after_update, targets):
    base = Path(prefix or os.environ.get(
        "PREFIX", "/data/data/com.termux/files/usr")) / "var" / "service"
    outcome = {}
    for name in targets:
        if after_update and name == "odin-git-sync":
            outcome[name] = "next_sync_cycle"
            continue
        service = base / name
        # Runit service entries may legitimately be symlinks to their
        # source definitions; the service name itself remains allowlisted.
        if not service.is_dir() or not (service / "run").is_file():
            required = name in MANDATORY and not (after_update and name == "odin-private-relay")
            outcome[name] = "missing" if required or len(targets) == 1 else "not_configured"
            continue
        try:
            previous_pid = None
            if after_update:
                prior = call("status", service)
                if prior.returncode or not prior.stdout.startswith(("run: ", "down: ")):
                    outcome[name] = "health_failed"
                    continue
                if prior.stdout.startswith("down: "):
                    outcome[name] = "inactive"
                    continue
                previous = re.search(r"\(pid (\d+)\)", prior.stdout)
                if not previous:
                    outcome[name] = "health_failed"
                    continue
                previous_pid = previous.group(1)
            result = call("restart", service)
            if result.returncode:
                outcome[name] = "restart_failed"
                continue
            # sv restart may return as the new service is just starting.
            running = False
            for _ in range(4):
                check = call("status", service)
                running = check.returncode == 0 and check.stdout.startswith("run: ")
                if running and after_update:
                    current = re.search(r"\(pid (\d+)\)", check.stdout)
                    running = bool(current and current.group(1) != previous_pid)
                    if running:
                        try:
                            running = Path("/proc", current.group(1), "cwd").resolve(strict=True) == ROOT
                        except OSError:
                            running = False
                if running:
                    break
                time.sleep(0.5)
            outcome[name] = "running" if running else "health_failed"
        except (OSError, subprocess.TimeoutExpired):
            outcome[name] = "timeout_or_unavailable"
    configured = [name for name, state in outcome.items() if state not in {"not_configured", "next_sync_cycle", "inactive"}]
    healthy = bool(configured) and all(outcome[name] == "running" for name in configured)
    status = "true" if healthy else "false"
    # Fixed allowlist and bounded status strings, no diagnostics or secrets.
    summary = ",".join(name + ":" + outcome[name] for name in targets)
    reply = ("ODIN_SERVICES_RESTART_RESULT verified=" + status
             + " managed=" + str(len(configured))
             + " running=" + str(sum(outcome[n] == "running" for n in targets))
             + " services=" + summary)
    return reply, healthy


def run_restarts(message_id, *, root=ROOT, state_dir=REQUEST_DIR,
                 prefix=None, call=svc_call):
    """Only known, already-configured Odin runit services. Relay last."""
    path = state_dir / (message_id + ".json")
    data = read_record(path)
    if data["phase"] != "queued":
        return 2
    data["phase"] = "running"
    save_record(path, data)
    data["reply"], healthy = restart_configured(
        state_dir=state_dir, prefix=prefix, call=call, service=data.get("service"))
    data["phase"] = "finished"
    data["completed_at"] = now()
    save_record(path, data)
    return 0 if healthy else 1


def pending_replies(*, state_dir=REQUEST_DIR, clock=now):
    """Report interrupted operations as failures, not false success."""
    if not state_dir.exists():
        return []
    pending = []
    for path in sorted(state_dir.glob("*.json")):
        try:
            row = read_record(path)
            if row["phase"] in ("queued", "running") and (
                clock() - row["created_at"] > STALE_SECONDS
            ):
                row["phase"] = "finished"
                row["completed_at"] = clock()
                row["reply"] = ("ODIN_SERVICES_RESTART_RESULT verified=false "
                                "reason=helper_interrupted")
                save_record(path, row)
            if row["phase"] == "finished":
                pending.append((path, row))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return pending[:10]


def publish_pending(token, send, *, state_dir=REQUEST_DIR):
    """Relay resumes delivery after it restarts; never claim before reply."""
    count = 0
    for path, row in pending_replies(state_dir=state_dir):
        try:
            send(token, {"type": "reply", "for": row["id"], "text": row["reply"]})
        except RuntimeError as error:
            # A prior accepted reply can return a duplicate/409 response;
            # retryable network failure stays queued for the next poll.
            if "HTTP 409" not in str(error):
                continue
        row["phase"] = "reported"
        row["reported_at"] = now()
        save_record(path, row)
        count += 1
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute")
    mode.add_argument("--local", action="store_true")
    mode.add_argument("--after-update", action="store_true")
    args = parser.parse_args(argv)
    if args.local or args.after_update:
        reply, healthy = restart_configured(after_update=args.after_update)
        print(reply, flush=True)
        return 0 if healthy else 1
    if not ID_RE.fullmatch(args.execute):
        parser.error("Invalid restart request ID")
    return run_restarts(args.execute)


if __name__ == "__main__":
    raise SystemExit(main())
