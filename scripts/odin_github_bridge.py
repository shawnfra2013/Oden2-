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
PRIVATE_ACTIONS = frozenset({"ping", "stage5_health", "staging_probe", "inference_probe", "encrypted_chat", "install_offline_model", "stage5_note_check", "stage5_source_check", "stage5_coding_review", "practice_next", "practice_followup", "regression_details", "review_feedback", "mailbox_audit"})
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
    if private_mailbox and payload.get("action") == "review_feedback":
        required = required | {
            "issue_number", "pr_number", "head_sha", "reference_receipt_id",
            "decision", "feedback_note",
        }
        if __package__:
            from .odin_review_feedback import validate_feedback
        else:
            from odin_review_feedback import validate_feedback
        validate_feedback(payload)
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
    if private_mailbox:
        recover_pending_source_receipt()
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
    if action == "mailbox_audit":
        if not private_mailbox:
            raise ValueError("Private mailbox audit requires an authenticated private bridge")
        if __package__:
            from .odin_mailbox_audit import inspect_local, save_report
        else:
            from odin_mailbox_audit import inspect_local, save_report
        # Fixed read-only scan of the already-fetched local clone, not a
        # general purpose CLI or user-selected filesystem/network endpoint.
        report = inspect_local(OUTBOX, hours=1)
        save_report(report)
        safe_codes = frozenset({
            "malformed_request", "malformed_response", "response_before_request",
            "response_in_future", "future_request", "orphan_response",
            "stalled", "expired_without_reply", "rejected_or_failed", "expired",
            "unverified", "action_mismatch", "ping_not_alive",
            "unexpected_action_complete",
        })
        incidents = [
            {"id": item["id"], "code": item["code"]}
            for item in report["incidents"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
            and ID_PATTERN.fullmatch(item["id"])
            and isinstance(item.get("code"), str)
            and item["code"] in safe_codes
        ]
        return {
            "scope": "private_mailbox_metadata",
            "audited_at": report["checked_at"],
            "revision": git("rev-parse", "HEAD"),
            "considered": report["considered"],
            "counts": report["counts"],
            "max_response_latency_s": report["max_response_latency_s"],
            "incident_count_shown": min(12, len(incidents)),
            "incidents": incidents[:12],
            "incidents_truncated": report["incidents_truncated"] or len(incidents) > 12,
            "agent_read_verified": False,
            "device_phone_verified": False,
        }
    if action == "review_feedback":
        if not private_mailbox or request is None:
            raise ValueError("Private feedback requires a validated request")
        if __package__:
            from .odin_review_feedback import record_feedback
        else:
            from odin_review_feedback import record_feedback
        return record_feedback(request, inbox=STATE / "review-feedback")
    if action == "regression_details" and private_mailbox:
        if __package__:
            from .odin_regression_details import diagnose
        else:
            from odin_regression_details import diagnose
        return diagnose(Path.home() / "odin-workspace")
    if action in {"practice_next", "practice_followup"} and private_mailbox:
        if __package__:
            from .odin_practice import practice
        else:
            from odin_practice import practice
        return practice(request["id"], followup=action == "practice_followup")
    if action in {"stage5_note_check", "stage5_source_check", "stage5_coding_review"}:
        if not private_mailbox:
            raise ValueError("Private mailbox required")
        if __package__:
            from .odin_note_check import check
        else:
            from odin_note_check import check
        return check(request["id"], source=action == "stage5_source_check", coding=action == "stage5_coding_review")
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
            try:
                raw = (STATE / "source-receipt-last-push.json").read_bytes()
                latest = json.loads(raw) if len(raw) <= 512 else {}
                if (isinstance(latest, dict)
                        and ID_PATTERN.fullmatch(str(latest.get("receipt_id", "")))):
                    result["last_source_receipt_push"] = latest
            except (OSError, ValueError, TypeError):
                pass
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
            result = {
                "disconnect_test_ready": test_ready,
                "reachable": True,
                "ready": data.get("status") == "ready",
                "ai_enabled": data.get("ai_enabled") is True,
            }
            if data.get("provider") in {"local", "groq", "openai", "invalid"}:
                result["provider"] = data["provider"]
            if data.get("ai_reason") in {
                "configured_not_tested", "ai_disabled", "credential_missing",
                "model_missing", "invalid_provider",
            }:
                result["ai_reason"] = data["ai_reason"]
            return result
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


def source_receipt_module():
    if __package__:
        from . import odin_receipt_sync
    else:
        import odin_receipt_sync
    return odin_receipt_sync


def recover_pending_source_receipt():
    """Finish a source-receipt commit after interruption without losing evidence."""
    intent = STATE / "pending-source-receipt.json"
    if not intent.exists():
        return
    # The journal records only previously validated, bounded local source evidence.
    raw = intent.read_bytes()
    if len(raw) > 4096:
        raise RuntimeError("Oversized source receipt journal")
    module = source_receipt_module()
    try:
        item = json.loads(raw)
        receipt_id = item["id"]
        module.validate_bytes(raw, receipt_id)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise RuntimeError("Invalid pending source receipt") from exc
    relative = module.remote_path(receipt_id)
    destination = OUTBOX / relative
    if destination.is_symlink() or destination.resolve() != destination:
        raise RuntimeError("Unsafe source receipt destination")
    if destination.exists() and destination.read_bytes() != raw:
        raise RuntimeError("Conflicting private source receipt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        atomic_state_file(destination, raw)
    git("add", "--", relative, cwd=OUTBOX)
    if git("diff", "--cached", "--name-only", "--", relative, cwd=OUTBOX):
        git("commit", "--only", "-m", "Odin local source receipt " + receipt_id,
            "--", relative, cwd=OUTBOX)
    intent.unlink()


def publish_local_source_receipts(max_per_poll=3):
    """Retry immutable local receipts through the current private outbox clone."""
    if not private_mailbox:
        return 0
    module = source_receipt_module()
    published = 0
    for candidate in module.local_candidates():
        if published >= max_per_poll:
            break
        try:
            raw = module.load_local(candidate)
        except (OSError, ValueError, TypeError):
            log("Skipping invalid offline source receipt")
            continue
        relative = module.remote_path(candidate.stem)
        destination = OUTBOX / relative
        if destination.is_symlink() or destination.resolve() != destination:
            raise RuntimeError("Unsafe private source receipt path")
        if destination.exists():
            if destination.read_bytes() != raw:
                raise RuntimeError("Conflicting source receipt ID in private mailbox")
            continue  # Already committed and pushed, or ahead for retry on next poll.
        journal = STATE / "pending-source-receipt.json"
        if journal.exists():
            recover_pending_source_receipt()
        atomic_state_file(journal, raw)
        recover_pending_source_receipt()
        # On a network failure, the committed outbox stays ahead; ensure_outbox
        # retries the push on the next poll. Never delete the local receipt.
        outbox_git("push", "origin", "HEAD:refs/heads/" + OUTBOX_BRANCH, timeout=90)
        atomic_state_file(STATE / "source-receipt-last-push.json",
                          json.dumps({"receipt_id": candidate.stem,
                                      "checked_at": iso(utcnow())}).encode())
        published += 1
    return published


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
    if private_mailbox:
        try:
            sent = publish_local_source_receipts()
            if sent:
                log("Uploaded " + str(sent) + " private source receipt(s)")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            # Preserve the existing diagnostic request/reply path even when
            # optional offline receipt shipping is temporarily unavailable.
            log("Local receipt delivery deferred: " + type(exc).__name__)
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
            status = "complete" if action not in {"inference_probe", "stage5_note_check", "stage5_source_check", "stage5_coding_review", "practice_next", "practice_followup"} or details["match"] else "unverified"
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
