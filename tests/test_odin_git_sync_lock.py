"""Offline regression tests for Odin's crash-safe OS-managed Git-sync lock."""
import fcntl
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import odin_git_sync_lock as guard


class KernelSyncLockTests(unittest.TestCase):
    def test_contention_skips_without_launching_a_second_sync(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            called = []

            def first():
                called.append("first")
                result = guard.locked_run(root, lambda: called.append("second") or 0)
                self.assertEqual(result, 0)
                return 0

            self.assertEqual(guard.locked_run(root, first), 0)
            self.assertEqual(called, ["first"])
            log = (root / "logs" / "git-sync.log").read_text()
            self.assertIn("SKIP: active Git-sync process holds kernel lock", log)
            self.assertEqual(guard.locked_run(root, lambda: 0), 0)

    def test_kernel_lock_released_after_abrupt_process_kill(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / "state"
            state.mkdir()
            lock = state / guard.LOCK_NAME
            script = (
                "import fcntl,os,sys,time;"
                "fd=os.open(sys.argv[1],os.O_CREAT|os.O_RDWR,0o600);"
                "fcntl.flock(fd,fcntl.LOCK_EX);"
                "print('locked',flush=True);time.sleep(30)"
            )
            child = subprocess.Popen(
                [sys.executable, "-c", script, str(lock)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            try:
                self.assertEqual(child.stdout.readline().strip(), "locked")
                self.assertEqual(guard.locked_run(root, lambda: self.fail(
                    "Competing process must not run")), 0)
            finally:
                child.kill()
                child.communicate(timeout=5)
            self.assertEqual(guard.locked_run(root, lambda: 0), 0)

    def test_lock_is_private_regular_file_and_legacy_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = root / "state" / "git-sync.lock"
            legacy.mkdir(parents=True)
            self.assertEqual(guard.locked_run(root, lambda: 0), 0)
            lock = root / "state" / guard.LOCK_NAME
            self.assertTrue(lock.is_file())
            self.assertEqual(lock.stat().st_mode & 0o077, 0)
            self.assertTrue(legacy.is_dir())

    def test_symlink_lock_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / "state"
            state.mkdir()
            target = root / "user-data"
            target.write_text("preserve")
            (state / guard.LOCK_NAME).symlink_to(target)
            self.assertEqual(guard.locked_run(root, lambda: self.fail(
                "Symlink should prevent execution")), 1)
            self.assertEqual(target.read_text(), "preserve")

    def test_sync_failure_propagates_to_existing_supervisor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(guard.locked_run(root, lambda: 17), 17)
            self.assertEqual(guard.locked_run(root, lambda: 0), 0)

    def test_normal_exit_releases_lock_without_deleting_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(guard.locked_run(root, lambda: 0), 0)
            lock = root / "state" / guard.LOCK_NAME
            with lock.open("rb") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    unittest.main()
