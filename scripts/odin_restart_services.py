"""Restart only Odin's installed Termux runit services and report their status."""
import argparse
import fcntl
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state" / "odin-relay"
RESULT = STATE / "restart-result.txt"
SERVICES = (
    "odin-git-sync",
    "odin-task-worker",
    "odin-github-bridge",
    "odin-private-relay",
)
RUNNING = re.compile(r"^run: .*?: \(pid ([0-9]+)\)")


def write_result(status):
    temp = RESULT.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"{status} at={datetime.now(UTC).isoformat()}\n")
    temp.replace(RESULT)


def restart_services(after_update=False):
    prefix = Path(os.environ["PREFIX"])
    sv = prefix / "bin" / "sv"
    results = {}

    def command(action, service):
        return subprocess.run(
            [sv, "-w", "15", action, service],
            capture_output=True, text=True, timeout=20, check=False,
        )

    for name in SERVICES:
        if after_update and name == "odin-git-sync":
            # The supervisor invokes the current sync script on each cycle.
            results[name] = "reload_on_next_cycle"
            continue
        service = prefix / "var" / "service" / name
        if not (service / "run").is_file():
            results[name] = "not_installed"
            continue
        try:
            initial = command("status", service)
            before = RUNNING.match(initial.stdout)
            if after_update and (initial.returncode or (not before and not initial.stdout.startswith("down: "))):
                results[name] = "unverified"
                continue
            if after_update and before is None:
                results[name] = "inactive"
                continue
            restarted = command("restart", service)
            final = command("status", service)
            after = RUNNING.match(final.stdout)
            verified = (
                restarted.returncode == final.returncode == 0 and after
                and (before is None or before[1] != after[1])
            )
            results[name] = "running" if verified else "unverified"
        except (OSError, subprocess.TimeoutExpired):
            results[name] = "unverified"

    complete = "unverified" not in results.values() and (
        after_update or "running" in results.values()
    )
    details = " ".join(f"{name}={status}" for name, status in results.items())
    return f"ODIN_RESTART_COMPLETE verified={str(complete).lower()} {details}", complete


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after-update", action="store_true")
    args = parser.parse_args(argv)
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(STATE / "restart.lock", os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    with os.fdopen(fd, "rb") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("ODIN_RESTART_ALREADY_RUNNING")
            return 1
        write_result("ODIN_RESTART_RUNNING")
        try:
            result, complete = restart_services(after_update=args.after_update)
        except KeyError:
            result, complete = "ODIN_RESTART_COMPLETE verified=false reason=termux_prefix_missing", False
        write_result(result)
        print(result)
        return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
