"""Offline tests for live-status safety, stale evidence and terminal rendering."""
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from scripts import odin_cli_dashboard as dashboard

SHA = "a" * 40


class DashboardTests(unittest.TestCase):
    def test_running_down_and_missing_services(self):
        with tempfile.TemporaryDirectory() as temp:
            prefix = Path(temp)
            (prefix / "var/service/odin-task-worker").mkdir(parents=True)
            running = lambda *_a: subprocess.CompletedProcess(
                [], 0, stdout="run: /service/odin-task-worker: (pid 123) 42s\n"
            )
            state = dashboard.service_state("odin-task-worker", prefix=prefix,
                                            runner=running)
            self.assertEqual(state, {"state": "RUNNING", "pid": 123, "uptime_s": 42})
            down = lambda *_a: subprocess.CompletedProcess(
                [], 1, stdout="down: /service/odin-task-worker: 0s\n"
            )
            self.assertEqual(dashboard.service_state(
                "odin-task-worker", prefix=prefix, runner=down)["state"], "STOPPED")
            self.assertEqual(dashboard.service_state(
                "odin-local-model", prefix=prefix)["state"], "NOT_INSTALLED")

    def test_untrusted_service_name_and_missing_prefix_fail_closed(self):
        with self.assertRaises(ValueError):
            dashboard.service_state("../../system")
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(dashboard.service_state(
                "odin-private-mailbox")["state"], "UNVERIFIED")

    def test_queue_depth_and_missing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "state/task-queue/pending").mkdir(parents=True)
            (root / "state/task-queue/pending/task.json").write_text("{}")
            q = dashboard.queue_depth(root)
            self.assertEqual(q["pending"], 1)
            self.assertIsNone(q["running"])

    def test_ci_matches_exact_local_sha_and_not_device(self):
        record = {"workflow_runs": [
            {"name": "Odin Checks", "head_sha": SHA, "status": "completed",
             "conclusion": "success"},
            {"name": "Untrusted", "head_sha": SHA, "status": "completed",
             "conclusion": "success"},
        ]}
        class Reply:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, _limit):
                return json.dumps(record).encode()
        ci = dashboard.github_ci(fetch=lambda *_a, **_k: Reply())
        self.assertEqual(ci["status"], "SOURCE_ONLY")
        self.assertEqual(len(ci["runs"]), 1)
        snapshot = {"source_sha": SHA, "mailbox_checkout": "UNVERIFIED",
                    "services": {}, "task_queue": {}, "offline_profile": False}
        shown = dashboard.render(snapshot, ci)
        self.assertIn("CI Odin Checks: success", shown)
        self.assertIn("phone UNVERIFIED", shown)
        snapshot["source_sha"] = "b" * 40
        self.assertIn("no matching checkout SHA", dashboard.render(snapshot, ci))

    def test_github_network_failure_is_unknown(self):
        def offline(*_args, **_kwargs):
            raise URLError("offline")
        self.assertEqual(dashboard.github_ci(fetch=offline)["status"], "UNVERIFIED")

    def test_ansi_only_on_interactive_tty(self):
        self.assertNotIn("\x1b", dashboard.safe_text("\x1b[31mINJECT\n"))
        output = io.StringIO()
        self.assertFalse(dashboard.use_color(stream=output, env={"TERM": "xterm"}))
        self.assertFalse(dashboard.use_color(stream=output, env={"NO_COLOR": "1"}))

    def test_watch_caches_ci_for_two_minutes(self):
        snap = {"source_sha": SHA, "services": {}, "mailbox_checkout": "UNVERIFIED",
                "task_queue": {}, "offline_profile": False}
        output = io.StringIO()
        with patch.object(dashboard, "local_snapshot", return_value=snap), \
             patch.object(dashboard, "github_ci", return_value={"status": "UNVERIFIED"}) as gh:
            times = iter([0, 10, 130])
            dashboard.watch(interval=10, iterations=3, github=True,
                            sleeper=lambda _seconds: None, output=output,
                            clock=lambda: next(times))
        self.assertEqual(gh.call_count, 2)
        self.assertEqual(output.getvalue().count("ODIN 2"), 3)


if __name__ == "__main__":
    unittest.main()
