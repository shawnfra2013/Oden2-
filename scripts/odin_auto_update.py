"""Opt-in, CI-gated, fast-forward-only Odin source updater.

Runs within the existing Git sync loop. Does not delete private state,
reset branches, or force-push. A verified pull reloads active Odin services.
"""
import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FLAG = ROOT / "state" / "auto-update.enabled"
RESULT = ROOT / "state" / "auto-update-result.json"
ROLLOUT_RESULT = ROOT / "state" / "last-auto-rollout.json"
SAFE_PULL = ROOT / "scripts" / "odin-safe-pull.sh"
REPO = "shawnfra2013/Oden2-"
ORIGINS = {
    "git@github.com:shawnfra2013/Oden2-.git",
    "https://github.com/shawnfra2013/Oden2-.git",
}
SHA = re.compile(r"[0-9a-f]{40}\Z")
WORKFLOWS_URL = (
    "https://api.github.com/repos/" + REPO
    + "/actions/workflows/odin-checks.yml/runs?"
    "branch=main&event=push&per_page=3"
)


def result_record(status, reason, before=None, target=None, after=None):
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": status,
        "reason": reason,
        "before": before,
        "target": target,
        "after": after,
    }


def save_result(record, destination=RESULT):
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=destination.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(record, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)


def save_rollout(evidence, reload_status):
    save_result({**evidence, "reload_status": reload_status}, ROLLOUT_RESULT)


def flag_is_enabled(path=FLAG):
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            return False
        return path.read_text(encoding="ascii") == "enabled\n"
    except (FileNotFoundError, OSError, UnicodeError):
        return False


def change_flag(enable, path=FLAG):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise RuntimeError("Refusing symlinked update-control file")
    if enable:
        temp = path.with_name(path.name + ".tmp")
        if temp.exists() or temp.is_symlink():
            raise RuntimeError("Temporary update-control file already exists")
        with temp.open("x", encoding="ascii") as handle:
            os.chmod(temp, 0o600)
            handle.write("enabled\n")
            handle.flush()
            os.fsync(handle.fileno())
        temp.replace(path)
    elif path.exists():
        path.unlink()


def git(*args, root=ROOT, timeout=60):
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        check=False, timeout=timeout
    )
    if completed.returncode:
        raise RuntimeError("Git command failed: " + " ".join(args[:2]))
    return completed.stdout.strip()


def ci_has_passed(target, payload):
    """Require a completed, successful push run on the exact target of main."""
    if not SHA.fullmatch(target) or not isinstance(payload, dict):
        return False
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        return False
    return any(
        isinstance(run, dict)
        and run.get("head_sha") == target
        and run.get("head_branch") == "main"
        and run.get("event") == "push"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and isinstance(run.get("head_repository"), dict)
        and run["head_repository"].get("full_name") == REPO
        for run in runs
    )


def read_ci_payload(target):
    if not SHA.fullmatch(target):
        raise ValueError("Invalid CI target revision")
    request = Request(WORKFLOWS_URL + "&head_sha=" + target, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Odin-Safe-Auto-Update",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(request, timeout=15) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise RuntimeError("GitHub workflow response too large")
    return json.loads(raw)


def update_once(root=ROOT, fetch_ci=None, git_cmd=None, run_cmd=None, before_pull=None):
    if git_cmd is None:
        def git_cmd(*args):
            return git(*args, root=root)
    if run_cmd is None:
        run_cmd = subprocess.run
    old, target = None, None
    try:
        if git_cmd("branch", "--show-current") != "main":
            return result_record("blocked", "branch_not_main")
        if git_cmd("remote", "get-url", "origin") not in ORIGINS:
            return result_record("blocked", "unexpected_origin")
        if git_cmd("status", "--porcelain", "--untracked-files=no"):
            return result_record("blocked", "tracked_changes")
        old = git_cmd("rev-parse", "HEAD")
        if not SHA.fullmatch(old):
            return result_record("blocked", "invalid_local_revision")
        git_cmd("fetch", "origin", "main")
        target = git_cmd("rev-parse", "origin/main")
        if not SHA.fullmatch(target):
            return result_record("blocked", "invalid_remote_revision", old)
        if target == old:
            return result_record("current", "already_up_to_date", old, target, old)
        if git_cmd("merge-base", old, target) != old:
            return result_record("blocked", "diverged", old, target)
        payload = fetch_ci(target) if fetch_ci else read_ci_payload(target)
        if not ci_has_passed(target, payload):
            return result_record("waiting", "ci_not_passed", old, target)
        if before_pull is not None:
            before_pull(target)
        completed = run_cmd(
            ["bash", str(root / "scripts" / "odin-safe-pull.sh")],
            cwd=root, env=dict(os.environ, ODIN_EXPECTED_SHA=target),
            capture_output=True, text=True,
            check=False, timeout=120
        )
        if completed.returncode:
            return result_record("blocked", "safe_pull_refused", old, target)
        after = git_cmd("rev-parse", "HEAD")
        if after != target:
            return result_record("blocked", "revision_mismatch", old, target, after)
        # The caller records this source result before attempting service reload.
        return result_record("updated", "source_updated",
                             old, target, after)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            json.JSONDecodeError, TypeError):
        return result_record("error", "update_check_failed", old, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enable", action="store_true")
    mode.add_argument("--disable", action="store_true")
    mode.add_argument("--status", action="store_true")
    mode.add_argument("--is-enabled", action="store_true")
    mode.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if args.is_enabled:
        return 0 if flag_is_enabled() else 1
    if args.enable:
        change_flag(True)
        print("Safe source updates and post-update service reload enabled.")
        return 0
    if args.disable:
        change_flag(False)
        print("Safe source updates disabled.")
        return 0
    if args.status:
        print("Auto-update:", "enabled" if flag_is_enabled() else "disabled")
        try:
            print("Last result:", RESULT.read_text(encoding="utf-8").strip())
        except FileNotFoundError:
            print("Last result: none")
        return 0
    if not flag_is_enabled():
        return 0
    # The preceding version recorded a pull but could not reload services.
    try:
        previous = json.loads(RESULT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = None
    def mark_pending(target):
        save_rollout({"revision": target, "checked_at": datetime.now(UTC).isoformat(), "attempts": 0}, "pending")

    record = update_once(before_pull=mark_pending)
    try:
        try:
            rollout = json.loads(ROLLOUT_RESULT.read_text())
        except FileNotFoundError:
            rollout = {}
        if not isinstance(rollout, dict):
            raise ValueError("Invalid rollout evidence")
        revision = record["after"]
        same = rollout.get("revision") == revision
        retry = same and rollout.get("reload_status") in {"pending", "unverified"}
        interrupted = (isinstance(previous, dict) and previous.get("status") == "updated"
                       and previous.get("after") == revision and not same)
        needs_reload = record["status"] == "updated" or (
            record["status"] == "current" and (retry or interrupted))
        if needs_reload:
            attempts = rollout.get("attempts", 0) if retry else 0
            if attempts >= 3:
                print("Reload attempt limit reached for", revision, file=sys.stderr)
                return 1
            evidence = {"revision": revision, "checked_at": record["checked_at"], "attempts": attempts + 1}
            save_rollout(evidence, "pending")
        save_result(record)
        if needs_reload:
            try:
                result = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "scripts" / "odin_service_restart.py"), "--after-update"],
                    cwd=ROOT, check=False, timeout=200,
                )
                healthy = result.returncode == 0 and git("rev-parse", "HEAD") == revision
            except (OSError, subprocess.TimeoutExpired):
                healthy = False
            save_rollout(evidence, "verified" if healthy else "unverified")
            if not healthy:
                return 1
    except (OSError, ValueError, TypeError, RuntimeError):
        print("ODIN_UPDATE_FAILURE: rollout evidence unavailable", file=sys.stderr)
        return 1
    print("ODIN_UPDATE", record["status"], record["reason"], record["after"] or "", flush=True)
    return 1 if record["status"] in {"blocked", "error"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
