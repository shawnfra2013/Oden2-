"""Supervised one-service Termux private-mailbox migration to canonical Odin.

Dry-run is default; --apply requires an explicit phrase and exact target SHA.
No Git fetch/push, user-file deletion, key handling, or unrelated restarts.
Private state is COPIED, not moved; the old checkout remains for rollback.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{40}\Z")
PID = re.compile(r"^run: .*: \(pid ([0-9]{1,9})\) [0-9]+s")
PRIVATE_REMOTE = "git@github.com:shawnfra2013/Odin-private-bridge.git"
PENDING = (
    "pending-receipt.json",
    "pending-source-receipt.json",
    "pending-feedback-tool-receipt.json",
)
MAX_FILES = 20000
MAX_BYTES = 250 * 1024 * 1024
CONFIRM = "MIGRATE-ODIN-MAILBOX"


class MigrationBlocked(RuntimeError):
    """A migration gate did not pass; preserve all original state."""


def _run(argv: list[str], *, timeout: int = 20) -> str:
    try:
        result = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MigrationBlocked("Required local command unavailable") from exc
    if result.returncode:
        raise MigrationBlocked("Required local command failed: " + argv[0])
    return result.stdout.strip()


def _git(path: Path, *args: str) -> str:
    return _run(["git", "-C", str(path), *args], timeout=20)


def _launcher_source(script: str, home: Path, prefix: Path) -> Path:
    """Accept only the existing 4-line fixed Python mailbox service."""
    lines = script.strip().splitlines()
    if (len(lines) != 4 or lines[0] != f"#!{prefix}/bin/bash"
            or lines[1] != "set -eu"
            or lines[3] != (
                f"exec {prefix}/bin/python -u -B "
                "scripts/odin_github_bridge.py --private-mailbox --serve"
            )):
        raise MigrationBlocked("Unexpected private mailbox launcher contents")
    try:
        parts = shlex.split(lines[2], comments=True)
    except ValueError as exc:
        raise MigrationBlocked("Invalid launcher directory syntax") from exc
    if len(parts) != 2 or parts[0] != "cd":
        raise MigrationBlocked("Unexpected mailbox working-directory command")
    raw = parts[1]
    if raw.startswith("$HOME/"):
        raw = str(home / raw[6:])
    elif raw == "$HOME":
        raw = str(home)
    target = Path(raw)
    if not target.is_absolute() or target.is_symlink():
        raise MigrationBlocked("Unsafe mailbox launch directory")
    target = target.resolve(strict=True)
    if not target.is_relative_to(home.resolve(strict=True)):
        raise MigrationBlocked("Mailbox checkout is outside Termux HOME")
    if target != home / "odin-workspace" and not target.name.startswith("odin-pr45-test."):
        raise MigrationBlocked("Launcher does not use the verified test checkout")
    return target


def _safe_tree(directory: Path) -> None:
    """Do not copy links, special files, or unexpectedly large private state."""
    if directory.is_symlink() or not directory.is_dir():
        raise MigrationBlocked("Private state root unavailable or unsafe")
    files, bytes_seen = 0, 0
    for root, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs + names:
            target = Path(root) / name
            mode = target.lstat().st_mode
            if stat.S_ISLNK(mode) or not (
                stat.S_ISDIR(mode) or stat.S_ISREG(mode)
            ):
                raise MigrationBlocked("Unsafe private state file")
            files += 1
            if stat.S_ISREG(mode):
                bytes_seen += target.stat().st_size
            if files > MAX_FILES or bytes_seen > MAX_BYTES:
                raise MigrationBlocked("Private state too large for safe migration")


def _private_state(state: Path) -> None:
    _safe_tree(state)
    if any((state / marker).exists() for marker in PENDING):
        raise MigrationBlocked("Unsent private receipt journal; reconcile first")
    outbox = state / "outbox"
    if not (outbox / ".git").is_dir():
        raise MigrationBlocked("Missing private outbox Git clone")
    if _git(outbox, "branch", "--show-current") != "odin-bridge-outbox":
        raise MigrationBlocked("Unexpected private outbox branch")
    if _git(outbox, "remote", "get-url", "origin") != PRIVATE_REMOTE:
        raise MigrationBlocked("Unexpected private outbox remote")
    if _git(outbox, "status", "--porcelain"):
        raise MigrationBlocked("Private outbox has pending file changes")
    if _git(outbox, "rev-list", "--count", "origin/odin-bridge-outbox..HEAD") != "0":
        raise MigrationBlocked("Unpushed private outbox commits")


def _service_pid(service: Path) -> int:
    result = _run(["sv", "status", str(service)], timeout=10)
    match = PID.match(result)
    if match is None:
        raise MigrationBlocked("Private mailbox is not confirmed running")
    return int(match[1])


def check(home: Path, prefix: Path, expected_sha: str, *,
          proc_root: Path = Path("/proc")) -> dict:
    if not SHA.fullmatch(expected_sha):
        raise MigrationBlocked("Invalid requested source SHA")
    home = home.resolve(strict=True)
    prefix = prefix.resolve(strict=True)
    canonical = home / "odin-workspace"
    service = prefix / "var/service/odin-private-mailbox"
    launcher = service / "run"
    if (not canonical.is_dir() or service.is_symlink()
            or launcher.is_symlink() or not launcher.is_file()):
        raise MigrationBlocked("Missing or unsafe canonical checkout/service")
    if _git(canonical, "rev-parse", "HEAD") != expected_sha:
        raise MigrationBlocked("Canonical checkout is not the approved source SHA")
    if _git(canonical, "branch", "--show-current") != "main":
        raise MigrationBlocked("Canonical checkout is not main")
    if _git(canonical, "diff", "--name-only") or _git(canonical, "diff", "--cached", "--name-only"):
        raise MigrationBlocked("Canonical tracked changes present")
    text = launcher.read_text(encoding="utf-8")
    source = _launcher_source(text, home, prefix)
    pid = _service_pid(service)
    current_cwd = (proc_root / str(pid) / "cwd").resolve(strict=True)
    if current_cwd != source:
        raise MigrationBlocked("Launcher and live process use different checkout")
    if source == canonical:
        return {"status": "ALREADY_CANONICAL", "sha": expected_sha,
                "source": str(source), "pid": pid}
    source_state = source / "state/github-bridge-private"
    dest_state = canonical / "state/github-bridge-private"
    if dest_state.exists() or dest_state.is_symlink():
        raise MigrationBlocked("Canonical private state already exists; manual reconciliation required")
    _private_state(source_state)
    return {
        "status": "READY", "sha": expected_sha, "source": str(source),
        "canonical": str(canonical), "service": str(service),
        "launcher": str(launcher), "pid": pid,
        "state": str(source_state), "destination": str(dest_state),
    }


def _atomic_launcher(path: Path, text: str, mode: int) -> None:
    fd, filename = tempfile.mkstemp(prefix=".odin-mailbox-run-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(filename, mode)
        os.replace(filename, path)
    finally:
        if os.path.lexists(filename):
            os.unlink(filename)


def _sv(direction: str, service: Path) -> None:
    if direction not in {"up", "down"}:
        raise MigrationBlocked("Unsupported service transition")
    _run(["sv", "-w", "15", direction, str(service)], timeout=25)


def _verify_started(service: Path, canonical: Path,
                    proc_root: Path = Path("/proc")) -> int:
    for _ in range(5):
        try:
            pid = _service_pid(service)
            if (proc_root / str(pid) / "cwd").resolve(strict=True) == canonical:
                return pid
        except (OSError, MigrationBlocked):
            pass
        time.sleep(0.5)
    raise MigrationBlocked("Restarted service did not reach canonical checkout")


def apply(home: Path, prefix: Path, expected_sha: str, confirmation: str, *,
          proc_root: Path = Path("/proc")) -> dict:
    if confirmation != CONFIRM:
        raise MigrationBlocked("Explicit migration approval phrase required")
    plan = check(home, prefix, expected_sha, proc_root=proc_root)
    if plan["status"] == "ALREADY_CANONICAL":
        return plan
    canonical, source = Path(plan["canonical"]), Path(plan["source"])
    service, launcher = Path(plan["service"]), Path(plan["launcher"])
    destination, previous = Path(plan["destination"]), Path(plan["state"])
    old = launcher.read_text(encoding="utf-8")
    replacement = old.replace("cd " + str(source) + "\n", "cd " + str(canonical) + "\n", 1)
    if replacement == old or replacement.count("cd ") != 1:
        raise MigrationBlocked("Launcher substitution does not match exactly")
    backup_dir = home / ".odin-preservation"
    if backup_dir.is_symlink():
        raise MigrationBlocked("Unsafe backup directory")
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = backup_dir / ("private-mailbox-run-" + uuid.uuid4().hex + ".bak")
    with backup.open("x", encoding="utf-8") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(old)
        output.flush()
        os.fsync(output.fileno())
    stopped, changed = False, False
    try:
        _sv("down", service)
        stopped = True
        # Stop creates a stable snapshot. Recheck journal and outbox state.
        _private_state(previous)
        if destination.exists() or destination.is_symlink():
            raise MigrationBlocked("Canonical private state appeared during stop")
        _safe_tree(previous)
        staging = destination.parent / (".private-mailbox-copy-" + uuid.uuid4().hex)
        try:
            shutil.copytree(previous, staging, symlinks=False)
            _safe_tree(staging)
            for walk_root, walk_dirs, walk_files in os.walk(staging):
                os.chmod(walk_root, 0o700)
                for name in walk_files:
                    os.chmod(Path(walk_root) / name, 0o600)
            if destination.exists() or destination.is_symlink():
                raise MigrationBlocked("Canonical destination collision")
            staging.rename(destination)
        finally:
            if staging.exists():
                # Never delete private staged data silently on a failed transfer.
                raise MigrationBlocked("Unfinished private state copy requires inspection")
        _atomic_launcher(launcher, replacement, launcher.stat().st_mode & 0o777)
        changed = True
        _sv("up", service)
        new_pid = _verify_started(service, canonical, proc_root=proc_root)
        return {"status": "MIGRATED", "sha": expected_sha, "pid": new_pid,
                "launcher_backup": str(backup),
                "old_private_state_preserved": True}
    except BaseException:
        if stopped:
            if changed:
                try:
                    _sv("down", service)
                except (OSError, MigrationBlocked):
                    pass
                _atomic_launcher(launcher, old, launcher.stat().st_mode & 0o777)
            try:
                _sv("up", service)
            except (OSError, MigrationBlocked):
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    prefix = os.environ.get("PREFIX")
    if not prefix:
        print(json.dumps({"status": "BLOCKED", "reason": "Termux PREFIX missing"}))
        return 2
    try:
        if args.apply:
            report = apply(Path.home(), Path(prefix), args.expected_sha, args.confirm)
        else:
            report = check(Path.home(), Path(prefix), args.expected_sha)
    except (OSError, MigrationBlocked, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
