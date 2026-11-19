from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts import odin_relay_client as relay
from scripts import odin_restart_services as restart


class RestartTests(TestCase):
    def test_relay_acknowledges_before_launch_and_only_for_exact_command(self):
        events = []
        message = {
            "id": "a" * 32, "sender": "iphone", "to": "odin",
            "text": "Restart all services", "status": "queued",
        }
        with (
            patch.object(relay, "request", side_effect=lambda _, data: events.append(data["type"])),
            patch.object(relay, "save_seen"),
            patch.object(relay.subprocess, "Popen", side_effect=lambda *a, **kw: events.append("restart")),
        ):
            relay.handle_message("token", message, set(), lambda _: self.fail("Unexpected inference"))
        self.assertEqual(events, ["receipt", "receipt", "reply", "restart"])
        self.assertNotEqual(relay.normalized_action("restart all services; uptime"), "restart_services")

    def test_manual_and_automatic_service_selection(self):
        with TemporaryDirectory() as directory:
            prefix = Path(directory)
            for name in restart.SERVICES:
                service = prefix / "var" / "service" / name
                service.mkdir(parents=True)
                (service / "run").touch()

            def run(args, **kwargs):
                action, path = args[-2:]
                if action == "restart":
                    restarted.append(path.name)
                    return CompletedProcess(args, 0, "")
                if path.name == "odin-github-bridge" and path.name not in restarted:
                    return CompletedProcess(args, 0, "down: bridge: 1s")
                pid = 34 if path.name in restarted else 12
                return CompletedProcess(args, 0, f"run: {path}: (pid {pid}) 1s")

            with patch.dict("os.environ", PREFIX=directory), patch.object(restart.subprocess, "run", side_effect=run):
                restarted = []
                _, verified = restart.restart_services(after_update=True)
                self.assertTrue(verified)
                self.assertEqual(restarted, ["odin-task-worker", "odin-private-relay"])
                restarted = []
                _, verified = restart.restart_services()
                self.assertTrue(verified)
                self.assertEqual(restarted, list(restart.SERVICES))
