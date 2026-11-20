"""GitHub-backed, allowlisted Odin status bridge (no arbitrary shell requests).

Inbox and outbox are separate branches, never the checked-out main branch.
Only fixed, read-only diagnostic actions are accepted. Public-repo receipts
contain structured booleans/counts, never command output or local file names.
"""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
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
ACTIONS = frozenset({
    "ping", "repo_status", "services", "stage5_health",
    "checks", "verify_release", "preflight_release", "odin_health", "worker_probe",
})
REVISION_ACTIONS = frozenset({"verify_release", "preflight_release"})
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
REQUEST_KEYS = {"version", "id", "action", "created_at", "expires_at"}
ORIGINS = {
    "git@github.com:shawnfra2013/Oden2-.git",
    "https://github.com/shawnfra2013/Oden2-.git",
}
POLL_SECONDS = 60
PRIVATE_ORIGIN = "git@github.com:shawnfra2013/Odin-private-bridge.git"
PRIVATE_ACTIONS = frozenset({"ping", "stage5_health", "staging_probe", "inference_probe", "encrypted_chat", "install_offline_model", "stage5_note_check"})
private_mailbox = False


def mailbox_git_args():
    if not private_mailbox:
        return ["git"]
    key = Path.home() / ".ssh" / "odin_private_bridge_ed25519"
    ssh = shlex.join([
        "ssh", "-i", str(key), "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=yes",
    ])
    return ["git", "-c", "core.sshCommand=" + ssh]


def outbox_git(*args, timeout=45):
    return run([*mailbox_git_args(), *args], cwd=OUTBOX, timeout=timeout).stdout.strip()


def enable_private_mailbox():
    global private_mailbox, STATE, OUTBOX
    private_mailbox = True
    STATE = ROOT / "state" / "github-bridge-private"
    OUTBOX = STATE / "outbox"


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
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > (18000 if private_mailbox else 4096):
        raise ValueError("Invalid request size")
    if not ID_PATTERN.fullmatch(expected_id):
        raise ValueError("Invalid ID")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("Invalid request object")
    required = REQUEST_KEYS | ({"expected_sha"} if payload.get("action") in REVISION_ACTIONS else set())
    if private_mailbox and payload.get("action") == "install_offline_model":
        required = required | {"expected_sha"}
        if not isinstance(payload.get("expected_sha"), str) or not SHA_PATTERN.fullmatch(payload["expected_sha"]):
            raise ValueError("Invalid installation revision")
    if private_mailbox and payload.get("action") == "encrypted_chat":
        required = required | {"sealed"}
        if not isinstance(payload.get("sealed"), str):
            raise ValueError("Missing encrypted message")
    elif len(raw.encode("utf-8")) > 4096:
        raise ValueError("Oversized diagnostic request")
    if set(payload) != required:
        raise ValueError("Invalid request fields")
    if type(payload["version"]) is not int or payload["version"] != 1 or payload["id"] != expected_id:
        raise ValueError("Invalid version or ID")
    allowed = PRIVATE_ACTIONS if private_mailbox else ACTIONS
    if payload["action"] not in allowed:
        raise ValueError("Action not allowlisted")
    if payload["action"] in REVISION_ACTIONS:
        expected = payload["expected_sha"]
        if not isinstance(expected, str) or not SHA_PATTERN.fullmatch(expected):
            raise ValueError("Invalid expected commit SHA")
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
            [*mailbox_git_args(), "clone", "--quiet", "--single-branch", "--no-tags",
             "--branch", OUTBOX_BRANCH, origin, str(OUTBOX)],
            timeout=90,
        )
        git("config", "user.name", "Odin Bridge", cwd=OUTBOX)
        git("config", "user.email", "odin-bridge@users.noreply.github.com", cwd=OUTBOX)
    if git("branch", "--show-current", cwd=OUTBOX) != OUTBOX_BRANCH:
        raise RuntimeError("Unexpected outbox branch")
    if git("remote", "get-url", "origin", cwd=OUTBOX) != origin:
        raise RuntimeError("Unexpected outbox origin")
    recover_pending_receipt()
    if git("status", "--porcelain", cwd=OUTBOX):
        raise RuntimeError("Outbox has uncommitted changes; refusing edits")
    outbox_git("pull", "--ff-only", "origin", OUTBOX_BRANCH, timeout=90)
    ahead = int(git("rev-list", "--count", "origin/" + OUTBOX_BRANCH + "..HEAD", cwd=OUTBOX))
    if ahead:
        outbox_git("push", "origin", "HEAD:refs/heads/" + OUTBOX_BRANCH, timeout=90)


def fetch_inbox():
    if private_mailbox:
        outbox_git(
            "fetch", "--quiet", "origin",
            "refs/heads/" + INBOX_BRANCH + ":refs/remotes/origin/" + INBOX_BRANCH,
            timeout=90,
        )
        return
    git("fetch", "--quiet", "origin",
        "refs/heads/" + INBOX_BRANCH + ":refs/remotes/origin/" + INBOX_BRANCH,
        timeout=90)


HEALTH_SERVICES = ("odin-private-mailbox", "odin-git-sync", "odin-task-worker", "odin-github-bridge", "odin-stage5", "odin-private-relay")
RUN_STATUS = re.compile(r"^run: .*: \(pid ([0-9]{1,9})\) ([0-9]{1,9})s(?:,|$)")
SYNC_REASONS = frozenset({
    "already_up_to_date", "source_updated", "source_updated_restart_not_automatic",
    "branch_not_main", "unexpected_origin", "tracked_changes", "invalid_local_revision",
    "invalid_remote_revision", "diverged", "ci_not_passed", "safe_pull_refused",
    "revision_mismatch", "update_check_failed",
})


def rollout_summary():
    try:
        with (ROOT / "state" / "last-auto-rollout.json").open("rb") as handle:
            raw = handle.read(4097)
        data = json.loads(raw) if len(raw) <= 4096 else {}
        revision = data["revision"]
        checked_at = datetime.fromisoformat(data["checked_at"])
        reload_status = data["reload_status"]
        if (SHA_PATTERN.fullmatch(revision) and checked_at.tzinfo is not None
                and reload_status in ("pending", "verified", "unverified")):
            return {
                "revision": revision,
                "checked_at": iso(checked_at.astimezone(UTC)),
                "reload_status": reload_status,
            }
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        pass
    return None


def heartbeat_age(path):
    try:
        with path.open("rb") as handle:
            raw = handle.read(4097)
        data = json.loads(raw) if len(raw) <= 4096 else {}
        checked_at = datetime.fromisoformat(data["checked_at"])
        age = int((utcnow() - checked_at).total_seconds())
        return age if 0 <= age < 1_000_000 else None
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None


def queue_depth(path):
    try:
        with os.scandir(path) as entries:
            return sum(
                1 for entry in entries
                if entry.name.endswith(".json") and entry.is_file(follow_symlinks=False)
            )
    except OSError:
        return None


def health_summary():
    """Public snapshot with bounded enums and counters, never raw log text."""
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    services = {}
    for name in HEALTH_SERVICES:
        path = prefix / "var" / "service" / name
        if not (path / "run").is_file():
            services[name] = {"state": "not_configured"}
            continue
        try:
            result = run(["sv", "status", str(path)], timeout=4, allow_failure=True)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            services[name] = {"state": "unknown"}
            continue
        match = RUN_STATUS.match(result.stdout.strip())
        if result.returncode == 0 and match:
            services[name] = {"state": "running", "pid": int(match[1]), "uptime_s": int(match[2])}
        else:
            services[name] = {"state": "down" if result.stdout.startswith("down: ") else "unknown"}

    try:
        with (ROOT / "state" / "auto-update-result.json").open("rb") as handle:
            raw = handle.read(4097)
        result = json.loads(raw) if len(raw) <= 4096 else {}
    except (OSError, ValueError):
        result = {}
    reason = result.get("reason") if isinstance(result, dict) else None
    return {
        **status_action("repo_status"),
        "services": services,
        "sync_reason": reason if isinstance(reason, str) and reason in SYNC_REASONS else "unknown",
        "stage5_reachable": status_action("stage5_health")["reachable"],
        "last_rollout": rollout_summary(),
        "worker_heartbeat_age_s": heartbeat_age(ROOT / "state/task-queue/worker-status.json"),
        "relay_poll_age_s": heartbeat_age(ROOT / "state/odin-relay/relay-status.json"),
        "queue_pending": queue_depth(ROOT / "state/task-queue/pending"),
        "queue_running": queue_depth(ROOT / "state/task-queue/running"),
    }


def staging_probe(request_id):
    if not private_mailbox or not ID_PATTERN.fullmatch(request_id):
        raise ValueError("Invalid private staging probe")
    payload = f"odin-staging-probe:{request_id}\n".encode("ascii")
    with tempfile.TemporaryDirectory(prefix="staging-", dir=STATE) as staging:
        path = Path(staging) / "probe.txt"
        path.write_bytes(payload)
        actual = path.read_bytes()
        if actual != payload:
            raise ValueError("Staging readback mismatch")
    return {"bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest()}


def model_capacity():
    """Read the Termux home volume and kernel memory without a model call."""
    info = {"architecture": os.uname().machine,
            "llama_server_installed": shutil.which("llama-server") is not None,
            "llama_cli_installed": shutil.which("llama-cli") is not None,
            "aider_installed": shutil.which("aider") is not None}
    try:
        info["disk_free_bytes"] = shutil.disk_usage(Path.home()).free
    except OSError:
        pass
    try:
        mem = Path("/proc/meminfo").read_text()
        for field, key in (("MemAvailable", "ram_available_bytes"), ("MemTotal", "ram_total_bytes")):
            match = re.search(r"^" + field + r":\s+(\d+) kB$", mem, re.MULTILINE)
            if match:
                info[key] = int(match[1]) * 1024
    except OSError:
        pass
    return info


def status_action(action, request=None):
    if action == "stage5_note_check":
        if not private_mailbox:
            raise ValueError("Private mailbox required")
        if __package__:
            from .odin_note_check import check
        else:
            from odin_note_check import check
        return check(request["id"])
    if action == "install_offline_model":
        if not private_mailbox:
            raise ValueError("Private mailbox required")
        canonical = Path.home() / "odin-workspace"
        expected = request["expected_sha"]
        for checkout in (ROOT, canonical):
            if (git("rev-parse", "HEAD", cwd=checkout) != expected
                    or git("status", "--porcelain", "--untracked-files=no", cwd=checkout)
                    or git("remote", "get-url", "origin", cwd=checkout) not in ORIGINS):
                raise ValueError("Unexpected installation checkout")
        # Read executable content only from the reviewed Git object.
        installer = git("show", expected + ":scripts/odin-install-offline.sh", cwd=canonical)
        evidence = STATE / ("offline-install-" + request["id"])
        if not evidence.exists():
            atomic_state_file(evidence, b'{"state":"interrupted_or_running"}')
            with (STATE / "offline-install.log").open("wb") as log_file:
                proc = subprocess.run(["bash", "-eu", "-o", "pipefail", "-c", installer],
                                      cwd=canonical, stdin=subprocess.DEVNULL,
                                      stdout=log_file, stderr=subprocess.STDOUT,
                                      timeout=3600, check=False)
            result = {"state": "ready" if proc.returncode == 0 else "failed",
                      "exit_code": proc.returncode, **model_capacity()}
            with (STATE / "offline-install.log").open("rb") as handle:
                handle.seek(max(0, os.fstat(handle.fileno()).st_size - 8192))
                tail = handle.read().decode(errors="replace")
            for label, pattern in (("package_unavailable", "Unable to locate package"),
                                   ("package_error", "dpkg: error"), ("checksum", "checksum differs"),
                                   ("download_error", "curl: ("), ("coding_check", "coding check did not match"),
                                   ("startup", "readiness check"), ("ui", "Stage 5 local provider still unverified")):
                if pattern in tail:
                    result["detail"] = label
            atomic_state_file(evidence, json.dumps(result).encode())
        return json.loads(evidence.read_text())
    if action == "encrypted_chat":
        if not private_mailbox:
            raise ValueError("Private mailbox required")
        try:
            if __package__:
                from .odin_encrypted_chat import reply
            else:
                from odin_encrypted_chat import reply
            return reply(request)
        except ImportError as exc:
            raise RuntimeError("Encrypted chat dependency unavailable") from exc
    if action == "inference_probe":
        if not private_mailbox:
            raise ValueError("Private mailbox required")
        if __package__:
            from .odin_inference_probe import probe
        else:
            from odin_inference_probe import probe
        return probe(request["id"])
    if action == "staging_probe":
        return staging_probe(request["id"])
    if action == "worker_probe":
        try:
            from .odin_worker_probe import probe
        except ImportError:
            from odin_worker_probe import probe
        return probe(ROOT, request["id"])
    if action == "odin_health":
        return health_summary()
    if action == "ping":
        result = {"alive": True, "bridge_version": 1}
        if private_mailbox:
            result.update(revision=git("rev-parse", "HEAD"), pid=os.getpid(), model_capacity=model_capacity())
        return result
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
            try:
                with urlopen("http://127.0.0.1:8765/api/disconnect-test", timeout=3) as test:
                    test_ready = json.loads(test.read(4096)).get("state") in {"waiting", "pending", "sent"}
            except (ValueError, OSError, AttributeError):
                test_ready = False
            return {
                "disconnect_test_ready": test_ready,
                "reachable": True,
                "ready": data.get("status") == "ready",
                "ai_enabled": data.get("ai_enabled") is True,
            }
        except (OSError, ValueError, URLError):
            return {"reachable": False}

    if action == "preflight_release":
        if request is None:
            raise ValueError("Preflight needs an expected SHA")
        expected = request["expected_sha"]
        if not isinstance(expected, str) or not SHA_PATTERN.fullmatch(expected):
            raise ValueError("Invalid expected commit SHA")
        checked_origin()
        before = git("rev-parse", "HEAD")
        branch = git("branch", "--show-current")
        tracked_clean = (
            run(["git", "diff", "--quiet"], allow_failure=True).returncode == 0
            and run(["git", "diff", "--cached", "--quiet"], allow_failure=True).returncode == 0
        )
        git("fetch", "--quiet", "origin", "main", timeout=90)
        remote = git("rev-parse", "origin/main")
        ancestor = (
            run(
                ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
                allow_failure=True,
            ).returncode == 0
        )
        incoming = run(
            ["git", "diff", "--no-renames", "--diff-filter=AMT", "--name-only", "-z",
             "HEAD", "origin/main"]
        ).stdout.split("\0")
        untracked = run(
            ["git", "ls-files", "--others", "-z"]
        ).stdout.split("\0")
        incoming = [p for p in incoming if p]
        untracked = [p for p in untracked if p]
        collisions = sum(
            new == old or new.startswith(old + "/") or old.startswith(new + "/")
            for new in incoming for old in untracked
        )
        can_attempt = (
            branch == "main" and tracked_clean and ancestor
            and remote == expected and collisions == 0
        )
        return {
            "expected_sha": expected,
            "local_sha": before, "remote_main_sha": remote,
            "branch_main": branch == "main",
            "tracked_clean": tracked_clean,
            "fast_forward_possible": ancestor,
            "target_matches": remote == expected,
            "untracked_count": len(untracked),
            "untracked_collisions": collisions,
            "safe_to_attempt_pull": can_attempt,
            "applied": False,
        }
    if action == "verify_release":
        if request is None:
            raise ValueError("Release verification needs an expected SHA")
        expected = request["expected_sha"]
        if not isinstance(expected, str) or not SHA_PATTERN.fullmatch(expected):
            raise ValueError("Invalid expected commit SHA")
        before = git("rev-parse", "HEAD")
        branch = git("branch", "--show-current")
        tracked_clean = (
            run(["git", "diff", "--quiet"], allow_failure=True).returncode == 0
            and run(["git", "diff", "--cached", "--quiet"], allow_failure=True).returncode == 0
        )
        aligned = before == expected and branch == "main" and tracked_clean
        report = {
            "expected_sha": expected, "head_before": before,
            "branch_main": branch == "main", "tracked_clean": tracked_clean,
            "revision_matches": before == expected, "tests_ran": False,
            "verified": False,
        }
        if not aligned:
            return report
        checks = status_action("checks")
        after = git("rev-parse", "HEAD")
        report.update({
            "head_after": after, "tests_ran": True,
            "checks": checks,
            "verified": all(checks.values()) and after == expected,
        })
        return report
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


def atomic_state_file(path, content):
    with tempfile.NamedTemporaryFile(dir=STATE, delete=False) as tmp:
        temp = Path(tmp.name)
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            os.replace(temp, path)
            parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        finally:
            temp.unlink(missing_ok=True)


def recover_pending_receipt():
    intent = STATE / "pending-receipt.json"
    if not intent.exists():
        return
    content = intent.read_bytes()
    request_id = json.loads(content)["id"]
    if not isinstance(request_id, str) or not ID_PATTERN.fullmatch(request_id):
        raise RuntimeError("Invalid pending receipt")
    relative = f"bridge/responses/{request_id}.json"
    path = OUTBOX / relative
    if path.resolve() != path or path.is_symlink():
        raise RuntimeError("Unexpected receipt path")
    if path.exists() and path.read_bytes() != content:
        raise RuntimeError("Conflicting local receipt")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        atomic_state_file(path, content)
    git("add", "--", relative, cwd=OUTBOX)
    if git("diff", "--cached", "--name-only", "--", relative, cwd=OUTBOX):
        git("commit", "--only", "-m", "Odin bridge response " + request_id, "--", relative, cwd=OUTBOX)
    intent.unlink()


def send_response(request_id, payload):
    if (OUTBOX / "bridge" / "responses" / (request_id + ".json")).exists():
        return
    content = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    atomic_state_file(STATE / "pending-receipt.json", content)
    recover_pending_receipt()
    outbox_git("push", "origin", "HEAD:refs/heads/" + OUTBOX_BRANCH, timeout=90)


def process_once():
    # One writer at a time: avoid two agent instances publishing duplicate
    # receipts or running concurrent check requests on the same checkout.
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "agent.lock").open("a+b") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another Odin bridge instance is active") from exc
        try:
            return process_locked()
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def process_locked():
    origin = checked_origin()
    ensure_outbox(PRIVATE_ORIGIN if private_mailbox else origin)
    fetch_inbox()
    inbox_git = outbox_git if private_mailbox else git
    ref = "origin/" + INBOX_BRANCH
    checkpoint = STATE / "completed-scan"
    inbox_head = inbox_git("rev-parse", ref)
    scan_key = inbox_head + ":" + outbox_git("rev-parse", "HEAD")
    if checkpoint.is_file() and checkpoint.read_text() == scan_key:
        return 0
    names = inbox_git("ls-tree", "-r", "--name-only", ref, "--", "bridge/requests")
    processed = 0
    for name in names.splitlines():
        if processed >= 5:
            break
        if not name.startswith("bridge/requests/") or not name.endswith(".json"):
            continue
        request_id = Path(name).stem
        if not ID_PATTERN.fullmatch(request_id) or name != f"bridge/requests/{request_id}.json":
            continue
        if (OUTBOX / "bridge" / "responses" / (request_id + ".json")).exists():
            continue
        action = "none"
        try:
            # Check blob size before reading content from an untrusted inbox.
            blob_size = int(inbox_git("cat-file", "-s", ref + ":" + name))
            if blob_size > (18000 if private_mailbox else 4096):
                raise ValueError("Oversized request blob")
            raw = inbox_git("show", ref + ":" + name, timeout=20)
            request = validate_request(raw, request_id)
            action = request["action"]
            picked_up_at = utcnow()
            started = time.monotonic()
            details = status_action(action, request)
            if action == "worker_probe" and details is None:
                continue
            status = "complete" if action not in {"inference_probe", "stage5_note_check"} or details["match"] else "unverified"
            if action == "install_offline_model" and details.get("state") != "ready":
                status = "unverified"
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
        if private_mailbox and status == "complete":
            receipt["timing"] = {
                "picked_up_at": picked_up_at.isoformat(timespec="milliseconds"),
                "action_ms": round((time.monotonic() - started) * 1000),
            }
        send_response(request_id, receipt)
        processed += 1
        log("Published " + request_id + " status=" + status)
    if not processed and private_mailbox:
        atomic_state_file(checkpoint, scan_key.encode())
    return processed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="Run one polling cycle")
    group.add_argument("--serve", action="store_true", help="Poll every 60 seconds")
    parser.add_argument("--private-mailbox", action="store_true", help="Use the private pilot repository")
    args = parser.parse_args()
    if args.private_mailbox:
        enable_private_mailbox()
    if args.serve:
        try:
            from .odin_wake import wait_for_work
        except ImportError:
            from odin_wake import wait_for_work
        while True:
            try:
                process_once()
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                log("Poll error: " + type(exc).__name__)
            if private_mailbox:
                time.sleep(POLL_SECONDS)
            else:
                wait_for_work("bridge", POLL_SECONDS)
    else:
        print("Processed requests:", process_once())


if __name__ == "__main__":
    main()
