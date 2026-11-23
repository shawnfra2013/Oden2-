"""Offline acceptance tests: bounded supervised restart, no arbitrary commands."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import odin_service_restart as restart


class OdinServiceRestartTests(unittest.TestCase):
    MID = "ab" * 16

    def create(self, directory, mid=MID):
        state = directory / "state"
        self.assertTrue(restart.reserve_restart(mid, state_dir=state, clock=lambda: 1000))
        return state / (mid + ".json")

    def test_restarting_requires_existing_supervised_services(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_dir = root / "state"
            record = self.create(root)
            prefix = root / "prefix"
            base = prefix / "var" / "service"
            for name in restart.MANDATORY:
                service = base / name
                service.mkdir(parents=True)
                (service / "run").write_text("#!/bin/sh\n")
            invoked = []

            def fake_call(action, path):
                invoked.append((action, path.name))
                return SimpleNamespace(returncode=0,
                                       stdout="run: ready" if action == "status" else "")

            code = restart.run_restarts(
                self.MID, state_dir=state_dir, prefix=prefix, call=fake_call)
            self.assertEqual(code, 0)
            data = json.loads(record.read_text())
            self.assertEqual(data["phase"], "finished")
            self.assertIn("verified=true", data["reply"])
            self.assertIn("odin-github-bridge:not_configured", data["reply"])
            self.assertEqual(
                [name for verb, name in invoked if verb == "restart"],
                ["odin-git-sync", "odin-task-worker"],
            )
            self.assertEqual(restart.run_restarts(
                self.MID, state_dir=state_dir, prefix=prefix, call=fake_call), 2)

    def test_only_requested_service_is_restarted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root / "state"
            service = "odin-stage5"
            for name in restart.SERVICES:
                path = root / "var" / "service" / name
                path.mkdir(parents=True)
                (path / "run").touch()
            self.assertTrue(restart.reserve_restart(self.MID, state_dir=state, service=service))
            with self.assertRaises(ValueError):
                restart.reserve_restart("ef" * 16, state_dir=state, service="sshd")
            def call(action, path):
                self.assertEqual(path.name, service)
                return SimpleNamespace(returncode=0, stdout="run: ok")
            self.assertEqual(restart.run_restarts(self.MID, state_dir=state, prefix=root, call=call), 0)

    def test_runit_symlink_service_entry_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_dir = root / "state"
            record = self.create(root)
            prefix = root / "prefix"
            base = prefix / "var" / "service"
            base.mkdir(parents=True)
            for name in restart.MANDATORY:
                target = root / "service-definitions" / name
                target.mkdir(parents=True)
                (target / "run").write_text("#!/bin/sh\\n")
                (base / name).symlink_to(target, target_is_directory=True)
            invoked = []
            def fake_call(action, path):
                invoked.append((action, path.name))
                return SimpleNamespace(returncode=0,
                                       stdout="run: ok" if action == "status" else "")
            result = restart.run_restarts(
                self.MID, state_dir=state_dir, prefix=prefix, call=fake_call)
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(record.read_text())["phase"], "finished")
            self.assertEqual([n for a, n in invoked if a == "restart"],
                             ["odin-git-sync", "odin-task-worker"])

    def test_health_failure_cannot_claim_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_dir = root / "state"
            record = self.create(root)
            prefix = root / "prefix"
            base = prefix / "var" / "service"
            for name in restart.MANDATORY:
                service = base / name
                service.mkdir(parents=True)
                (service / "run").write_text("#!/bin/sh\n")
            def fake_call(action, path):
                if action == "restart" and path.name == "odin-task-worker":
                    return SimpleNamespace(returncode=1, stdout="")
                return SimpleNamespace(returncode=0,
                                       stdout="run: ready" if action == "status" else "")
            with patch.object(restart.time, "sleep"):
                code = restart.run_restarts(self.MID, state_dir=state_dir,
                                            prefix=prefix, call=fake_call)
            self.assertEqual(code, 1)
            result = json.loads(record.read_text())
            self.assertIn("verified=false", result["reply"])
            self.assertIn("odin-task-worker:restart_failed", result["reply"])

    def test_missing_required_service_cannot_claim_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = self.create(root)
            code = restart.run_restarts(self.MID, state_dir=record.parent,
                                        prefix=root / "no-service-root")
            self.assertEqual(code, 1)
            self.assertIn("verified=false", json.loads(record.read_text())["reply"])

    def test_rate_limit_preserves_first_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.create(root)
            state = root / "state"
            self.assertFalse(restart.reserve_restart(self.MID, state_dir=state,
                                                    clock=lambda: 1001))
            self.assertFalse(restart.reserve_restart("cd" * 16, state_dir=state,
                                                    clock=lambda: 1100))
            self.assertTrue(restart.reserve_restart("cd" * 16, state_dir=state,
                                                   clock=lambda: 1700))

    def test_detached_launch_no_secret_arguments(self):
        with patch.object(restart, "reserve_restart", return_value=True), \
             patch.object(restart.subprocess, "Popen") as popen:
            self.assertTrue(restart.start_restart(self.MID))
            argv = popen.call_args.args[0]
            self.assertEqual(argv[-2:], ["--execute", self.MID])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            self.assertTrue(popen.call_args.kwargs["close_fds"])
            self.assertNotIn("token", " ".join(argv).lower())

    def test_bad_id_does_not_become_shell_argv(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            restart.reserve_restart("abc; reboot", state_dir=Path(folder))
        self.assertEqual(restart.SERVICES[-1], "odin-stage5")
        self.assertNotIn("sshd", restart.SERVICES)


if __name__ == "__main__":
    unittest.main()
