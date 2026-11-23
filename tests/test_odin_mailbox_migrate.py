"""Guarded Termux migration tests never touch real services or private Git."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_mailbox_migrate as migration


class MailboxMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.prefix = root / "termux"
        self.prefix.mkdir()
        self.canonical = self.home / "odin-workspace"
        self.canonical.mkdir()
        (self.canonical / "state").mkdir()
        (self.canonical / "owner-file.txt").write_text("preserve me")
        self.old = self.home / "odin-pr45-test.test"
        self.old.mkdir()
        self.private = self.old / "state/github-bridge-private"
        outbox = self.private / "outbox"
        (outbox / ".git").mkdir(parents=True)
        (outbox / "bridge/responses").mkdir(parents=True)
        (outbox / "bridge/responses" / ("a" * 32 + ".json")).write_text("receipt")
        (self.private / "agent.log").write_text("log must survive")
        self.service = self.prefix / "var/service/odin-private-mailbox"
        self.service.mkdir(parents=True)
        self.launcher = self.service / "run"
        self.launcher.write_text(
            f"#!{self.prefix}/bin/bash\n"
            "set -eu\n"
            f"cd {self.old}\n"
            f"exec {self.prefix}/bin/python -u -B "
            "scripts/odin_github_bridge.py --private-mailbox --serve\n"
        )
        self.launcher.chmod(0o700)
        self.proc = root / "proc"
        (self.proc / "4242").mkdir(parents=True)
        self.cwd = self.proc / "4242/cwd"
        self.cwd.symlink_to(self.old, target_is_directory=True)
        self.head = "a" * 40
        self.up = True
        self.fail_first_up = False
        self.transitions = []

        def git(path, *args):
            args = tuple(args)
            if path == self.canonical:
                if args == ("rev-parse", "HEAD"):
                    return self.head
                if args == ("branch", "--show-current"):
                    return "main"
                if args in (("diff", "--name-only"),
                            ("diff", "--cached", "--name-only")):
                    return ""
            if path == outbox:
                return {
                    ("branch", "--show-current"): "odin-bridge-outbox",
                    ("remote", "get-url", "origin"): migration.PRIVATE_REMOTE,
                    ("status", "--porcelain"): "",
                    ("rev-list", "--count", "origin/odin-bridge-outbox..HEAD"): "0",
                }[args]
            raise AssertionError("Unexpected Git read")

        def command(argv, timeout=20):
            if argv[:2] == ["sv", "status"]:
                if self.up:
                    return f"run: {self.service}: (pid 4242) 50s"
                return f"down: {self.service}: 50s"
            self.assertEqual(argv[:3], ["sv", "-w", "15"])
            self.assertEqual(argv[4], str(self.service))
            action = argv[3]
            self.transitions.append(action)
            if action == "down":
                self.up = False
                return "ok: down:"
            if action == "up":
                if self.fail_first_up:
                    self.fail_first_up = False
                    raise migration.MigrationBlocked("Injected service start failure")
                self.up = True
                raw = self.launcher.read_text()
                target = self.canonical if f"cd {self.canonical}" in raw else self.old
                self.cwd.unlink()
                self.cwd.symlink_to(target, target_is_directory=True)
                return "ok: run:"
            raise AssertionError("Unrecognized transition")

        self.git_patcher = patch.object(migration, "_git", side_effect=git)
        self.run_patcher = patch.object(migration, "_run", side_effect=command)
        self.git_patcher.start()
        self.run_patcher.start()
        self.addCleanup(self.git_patcher.stop)
        self.addCleanup(self.run_patcher.stop)

    def preview(self):
        return migration.check(self.home, self.prefix, self.head,
                               proc_root=self.proc)

    def apply(self, confirm=migration.CONFIRM):
        return migration.apply(self.home, self.prefix, self.head, confirm,
                               proc_root=self.proc)

    def test_preview_is_readonly_and_reports_exact_source(self):
        before = self.launcher.read_bytes()
        report = self.preview()
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["sha"], self.head)
        self.assertEqual(report["source"], str(self.old))
        self.assertEqual(self.launcher.read_bytes(), before)
        self.assertFalse((self.canonical / "state/github-bridge-private").exists())
        self.assertEqual(self.transitions, [])

    def test_approval_and_exact_source_sha_are_required(self):
        with self.assertRaises(migration.MigrationBlocked):
            self.apply(confirm="")
        with self.assertRaises(migration.MigrationBlocked):
            migration.check(self.home, self.prefix, "b" * 40, proc_root=self.proc)
        self.assertTrue(self.up)
        self.assertEqual(self.transitions, [])

    def test_preserves_private_state_and_untracked_files_on_success(self):
        done = self.apply()
        self.assertEqual(done["status"], "MIGRATED")
        self.assertEqual(self.transitions, ["down", "up"])
        self.assertTrue(self.private.is_dir())
        moved = self.canonical / "state/github-bridge-private"
        self.assertEqual((moved / "agent.log").read_text(), "log must survive")
        self.assertTrue((moved / "outbox/.git").is_dir())
        self.assertEqual((moved / "agent.log").stat().st_mode & 0o777, 0o600)
        self.assertEqual(moved.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.canonical / "owner-file.txt").read_text(), "preserve me")
        self.assertEqual(self.cwd.resolve(), self.canonical.resolve())
        self.assertTrue(Path(done["launcher_backup"]).is_file())
        self.assertIn(f"cd {self.old}", Path(done["launcher_backup"]).read_text())

    def test_canonical_state_collision_fails_before_service_stop(self):
        destination = self.canonical / "state/github-bridge-private"
        destination.mkdir()
        (destination / "owner.log").write_text("do not overwrite")
        with self.assertRaises(migration.MigrationBlocked):
            self.apply()
        self.assertEqual((destination / "owner.log").read_text(), "do not overwrite")
        self.assertEqual(self.transitions, [])

    def test_pending_journals_always_block(self):
        for name in migration.PENDING:
            marker = self.private / name
            marker.write_text("unsent")
            with self.subTest(journal=name), self.assertRaises(migration.MigrationBlocked):
                self.preview()
            marker.unlink()
        self.assertEqual(self.transitions, [])

    def test_launcher_cannot_contain_unexpected_shell_commands(self):
        original = self.launcher.read_text()
        self.launcher.write_text(original + "rm -rf $HOME\n")
        with self.assertRaises(migration.MigrationBlocked):
            self.preview()
        self.launcher.write_text(original.replace(" --serve", " --other"))
        with self.assertRaises(migration.MigrationBlocked):
            self.preview()
        self.assertEqual(self.transitions, [])

    def test_stale_live_process_blocks_switch(self):
        self.cwd.unlink()
        self.cwd.symlink_to(self.canonical, target_is_directory=True)
        with self.assertRaises(migration.MigrationBlocked):
            self.preview()
        self.assertEqual(self.transitions, [])

    def test_symlinked_private_state_file_blocks_copy(self):
        target = self.home / "private-key-elsewhere"
        target.write_text("never-copy")
        (self.private / "outbox/key").symlink_to(target)
        with self.assertRaises(migration.MigrationBlocked):
            self.preview()
        self.assertEqual(self.transitions, [])

    def test_start_failure_restores_original_launcher_and_service(self):
        self.fail_first_up = True
        with self.assertRaises(migration.MigrationBlocked):
            self.apply()
        self.assertIn(f"cd {self.old}", self.launcher.read_text())
        self.assertEqual(self.cwd.resolve(), self.old.resolve())
        self.assertEqual(self.transitions, ["down", "up", "down", "up"])
        self.assertTrue(self.private.is_dir())
        self.assertTrue((self.canonical / "state/github-bridge-private").exists())

    def test_abandoned_staging_copy_blocks_reapply(self):
        leftover = self.canonical / "state/.private-mailbox-copy-interrupted"
        leftover.mkdir()
        (leftover / "saved-evidence").write_text("preserve")
        with self.assertRaises(migration.MigrationBlocked):
            self.preview()
        self.assertEqual(self.transitions, [])
        self.assertEqual((leftover / "saved-evidence").read_text(), "preserve")

    def test_simultaneous_attempts_fail_without_stop(self):
        with patch.object(migration.fcntl, "flock", side_effect=BlockingIOError):
            with self.assertRaises(migration.MigrationBlocked):
                self.apply()
        self.assertEqual(self.transitions, [])
        self.assertTrue(self.private.is_dir())

    def test_new_journal_after_stop_forces_safe_restart(self):
        original = migration._private_state
        calls = []

        def inspect(state):
            calls.append(state)
            if len(calls) == 2:
                (state / "pending-receipt.json").write_text("new intent")
            return original(state)

        with patch.object(migration, "_private_state", side_effect=inspect):
            with self.assertRaises(migration.MigrationBlocked):
                self.apply()
        self.assertEqual(self.transitions, ["down", "up"])
        self.assertEqual(self.cwd.resolve(), self.old.resolve())
        self.assertIn(f"cd {self.old}", self.launcher.read_text())
        self.assertTrue((self.private / "pending-receipt.json").is_file())
        self.assertFalse((self.canonical / "state/github-bridge-private").exists())

    def test_already_canonical_does_not_change_service(self):
        self.launcher.write_text(self.launcher.read_text().replace(
            f"cd {self.old}", f"cd {self.canonical}",
        ))
        self.cwd.unlink()
        self.cwd.symlink_to(self.canonical, target_is_directory=True)
        result = self.apply()
        self.assertEqual(result["status"], "ALREADY_CANONICAL")
        self.assertEqual(self.transitions, [])


if __name__ == "__main__":
    unittest.main()
