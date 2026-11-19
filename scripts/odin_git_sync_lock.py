"""Crash-safe, OS-managed exclusive lock for Odin's existing Git sync.

Runs scripts/git-sync.sh inside a kernel flock held by this Python process.
The lock automatically releases on normal exit, exceptions, SIGKILL and
Termux termination. No stale directory cleanup or additional daemon.
"""
import fcntl
import os
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_NAME = "git-sync.flock"
INNER_ARG = "--under-odin-sync-lock"


def record(log, message):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as output:
        output.write(datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S ")
                     + message + "\n")


def locked_run(root=ROOT, action=None):
    """Return sync exit status; an active competing sync is a logged skip.

    action is injectable solely for the offline locking regression tests.
    No untrusted message is allowed to choose the invoked executable.
    """
    lock = root / "state" / LOCK_NAME
    log = root / "logs" / "git-sync.log"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        fd = os.open(lock, flags, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or info.st_mode & 0o077):
                record(log, "ERROR: Git-sync lock has unsafe ownership or permissions")
                return 1
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                record(log, "SKIP: active Git-sync process holds kernel lock")
                return 0
            if action is not None:
                return int(action())
            result = subprocess.run(
                ["bash", str(root / "scripts" / "git-sync.sh"), INNER_ARG],
                cwd=root, check=False,
            )
            return result.returncode if result.returncode >= 0 else 128 - result.returncode
        finally:
            # Closing the FD releases the kernel lock even after an error.
            os.close(fd)
    except (OSError, ValueError, RuntimeError) as error:
        record(log, "ERROR: Cannot run Git-sync lock: " + type(error).__name__)
        return 1


def main():
    if len(sys.argv) != 1:
        print("No arguments accepted", file=sys.stderr)
        return 2
    return locked_run()


if __name__ == "__main__":
    raise SystemExit(main())
