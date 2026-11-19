"""Offline tests for independent Odin message processing and verified local tasks."""
import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import odin_relay_client as relay


class RelayHardeningTests(unittest.TestCase):
    def test_old_messages_do_not_starve_new_message(self):
        msgs = [
            {"id": f"{i:032x}", "sender": "iphone", "to": "odin",
             "text": "/ping", "status": "replied"}
            for i in range(45)
        ]
        msgs.append({"id": "f" * 32, "sender": "iphone", "to": "odin",
                     "text": "/ping", "status": "queued"})
        seen = []
        with (
            patch.object(relay, "exclusive_poll", return_value=contextlib.nullcontext()),
            patch.object(relay, "request",
                         return_value={"source": "private-odin-relay", "messages": msgs}),
            patch.object(relay, "load_seen", return_value=set()),
            patch.object(relay, "write_poll_status") as record,
            patch.object(relay, "handle_message", side_effect=lambda _t, msg, _s, _a:
                         seen.append(msg["id"]) or True),
        ):
            self.assertEqual(relay.poll_once("not-a-token"), 1)
            self.assertEqual(seen, ["f" * 32])
            record.assert_called_once_with(1, 0, len(msgs))

    def test_one_failed_message_does_not_block_second(self):
        items = [
            {"id": "a" * 32, "sender": "iphone", "to": "odin",
             "text": "one", "status": "queued"},
            {"id": "b" * 32, "sender": "iphone", "to": "odin",
             "text": "/ping", "status": "queued"},
        ]
        observed = []

        def handler(_token, msg, _seen, _answer):
            observed.append(msg["id"])
            if msg["id"] == "a" * 32:
                raise RuntimeError("private error")
            return True

        with (
            patch.object(relay, "exclusive_poll", return_value=contextlib.nullcontext()),
            patch.object(relay, "request", return_value={
                "source": "private-odin-relay", "messages": items,
            }),
            patch.object(relay, "load_seen", return_value=set()),
            patch.object(relay, "write_poll_status") as record,
            patch.object(relay, "handle_message", side_effect=handler),
            patch("sys.stderr"),
        ):
            with self.assertRaisesRegex(RuntimeError, "1 private message"):
                relay.poll_once("not-a-token")
            self.assertEqual(observed, ["a" * 32, "b" * 32])
            record.assert_called_once_with(1, 1, 2)

    def test_readonly_task_commands_only(self):
        def git_run(command, **_kw):
            if command[1:3] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(returncode=0, stdout="e" * 40 + "\n")
            if command[1:3] == ["status", "--porcelain"]:
                return SimpleNamespace(returncode=0, stdout="")
            if command[1:3] == ["ls-files", "--others"]:
                return SimpleNamespace(returncode=0, stdout=b"one\0two\0")
            raise AssertionError(command)

        with tempfile.TemporaryDirectory() as folder, (
            patch.object(relay, "ROOT", Path(folder)),
            patch.object(subprocess, "run", side_effect=git_run),
        ):
            for folder_name, count in (("pending", 2), ("running", 0), ("done", 1)):
                path = Path(folder) / "state" / "task-queue" / folder_name
                path.mkdir(parents=True)
                for i in range(count):
                    (path / f"{i}.json").write_text("{}")
            result = relay.status_reply("/task git-status")
            self.assertIn("ODIN_TASK_COMPLETE", result)
            self.assertIn("tracked_clean=true", result)
            self.assertIn("untracked_count=2", result)
            queues = relay.status_reply("/task queue-status")
            self.assertIn("pending=2", queues)
            self.assertIn("done=1", queues)
            self.assertIn("running=0", queues)

    def test_unknown_task_does_not_execute_provider(self):
        calls = []

        def mock_request(_token, body=None):
            if body is not None:
                calls.append(body)
            return {"status": "ok"}

        item = {"id": "f" * 32, "sender": "iphone", "to": "odin",
                "status": "queued", "text": "/task delete everything"}
        with tempfile.TemporaryDirectory() as folder, (
            patch.object(relay, "STATE", Path(folder)),
            patch.object(relay, "SEEN_FILE", Path(folder) / "seen.json"),
            patch.object(relay, "request", side_effect=mock_request),
        ):
            result = relay.handle_message(
                "token", item, set(), lambda _: self.fail("AI must not run")
            )
            self.assertTrue(result)
            self.assertEqual(calls[-1]["type"], "reply")
            self.assertIn("ODIN_TASK_REJECTED", calls[-1]["text"])

    def test_poll_lock_is_exclusive(self):
        with tempfile.TemporaryDirectory() as folder, (
            patch.object(relay, "STATE", Path(folder)),
            patch.object(relay, "LOCK_FILE", Path(folder) / "poll.lock"),
        ):
            with relay.exclusive_poll():
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    with relay.exclusive_poll():
                        pass


if __name__ == "__main__":
    unittest.main()
