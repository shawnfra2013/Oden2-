"""Private Odin trace journal regressions: redaction, no replay, no runaway log."""
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from scripts import odin_trace_log as traces


class OdinTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name) / "state/odin-traces"
        self.when = datetime(2026, 11, 23, 9, 40, tzinfo=UTC)
        self.receipt = {
            "id": "a" * 32, "action": "ping", "status": "complete",
            "checked_at": "2026-11-23T09:39:00Z",
            "result": {"secret": "NEVER_WRITE_PRIVATE_CHAT", "alive": True},
            "timing": {"action_ms": 22},
        }
        self.sha = "f" * 40

    def record(self, receipt=None):
        return traces.append_bridge_reply(
            self.directory, self.receipt if receipt is None else receipt, self.sha,
        )

    def test_append_only_once_with_private_permissions(self):
        self.assertTrue(self.record())
        self.assertFalse(self.record())
        file = self.directory / "events.jsonl"
        self.assertEqual(len(file.read_text().splitlines()), 1)
        self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)

    def test_untrusted_result_does_not_enter_log(self):
        self.record()
        saved = (self.directory / "events.jsonl").read_text()
        self.assertNotIn("NEVER_WRITE_PRIVATE_CHAT", saved)
        row = json.loads(saved)
        self.assertEqual(row["id"], "a" * 32)
        self.assertFalse(row["agent_read_verified"])
        self.assertFalse(row["device_phone_verified"])

    def test_conflicting_replay_fails_without_replacing_first_receipt(self):
        self.record()
        source = (self.directory / "events.jsonl").read_bytes()
        with self.assertRaises(ValueError):
            self.record({**self.receipt, "status": "unverified"})
        self.assertEqual((self.directory / "events.jsonl").read_bytes(), source)

    def test_all_receipt_statuses_including_errors_are_visible(self):
        self.record()
        for index, status in enumerate(("expired", "rejected_or_failed", "unverified"), 1):
            self.record({
                **self.receipt, "id": f"{index:032x}", "status": status,
                "timing": {},
            })
        report = traces.summarize(self.directory, hours=1, now=self.when)
        self.assertEqual(report["events"], 4)
        self.assertEqual(report["status_counts"]["complete"], 1)
        self.assertEqual(report["status_counts"]["rejected_or_failed"], 1)
        self.assertEqual(len(report["incidents"]), 3)
        self.assertFalse(report["agent_read_verified"])

    def test_no_journal_is_not_claimed_as_zero_real_events(self):
        report = traces.summarize(self.directory, hours=1, now=self.when)
        self.assertEqual(report["events"], 0)
        self.assertFalse(report["agent_read_verified"])

    def test_invalid_id_action_status_or_time_cannot_be_journaled(self):
        changes = (
            {"id": "../bad"},
            {"action": "shell; cat secret"},
            {"status": "unknown"},
            {"checked_at": "this-morning"},
            {"timing": {"action_ms": -1}},
            {"timing": {"action_ms": True}},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.record({**self.receipt, **change})
        self.assertFalse((self.directory / "events.jsonl").exists())

    def test_incomplete_prior_record_blocks_append_without_deletion(self):
        self.directory.mkdir(parents=True)
        file = self.directory / "events.jsonl"
        file.write_bytes(b'{"partial":true}')
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(file.read_bytes(), b'{"partial":true}')

    def test_symlinked_trace_file_or_directory_is_blocked(self):
        self.directory.mkdir(parents=True)
        target = Path(self.tmp.name) / "outside.txt"
        target.write_text("confidential")
        file = self.directory / "events.jsonl"
        file.symlink_to(target)
        with self.assertRaises(ValueError):
            self.record()
        file.unlink()
        self.directory.rmdir()
        self.directory.symlink_to(Path(self.tmp.name) / "other", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(target.read_text(), "confidential")

    def test_oversized_existing_log_is_preserved(self):
        self.directory.mkdir(parents=True)
        file = self.directory / "events.jsonl"
        file.write_bytes(b"x" * (traces.MAX_LOG_BYTES + 1))
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(file.stat().st_size, traces.MAX_LOG_BYTES + 1)

    def test_existing_bridge_can_log_metadata_without_a_new_service(self):
        from scripts import odin_github_bridge as bridge
        with (patch.object(bridge, "private_mailbox", True),
              patch.object(bridge, "ROOT", self.directory.parent.parent),
              patch.object(bridge, "git", return_value=self.sha),
              patch.object(bridge, "log") as log):
            self.assertTrue(bridge.record_private_trace(self.receipt))
        log.assert_not_called()
        self.assertEqual(traces.summarize(
            self.directory, now=self.when)["events"], 1)

    def test_optional_trace_error_never_fails_a_completed_mailbox_reply(self):
        from scripts import odin_github_bridge as bridge
        with (patch.object(bridge, "private_mailbox", True),
              patch.object(bridge, "ROOT", self.directory.parent.parent),
              patch.object(bridge, "git", return_value="INVALID"),
              patch.object(bridge, "log") as log):
            self.assertFalse(bridge.record_private_trace(self.receipt))
        log.assert_called_once()
        self.assertNotIn("NEVER_WRITE_PRIVATE_CHAT", log.call_args.args[0])

    def test_summary_filters_old_events_without_erasing_history(self):
        self.record()
        report = traces.summarize(
            self.directory, hours=1, now=datetime(2026, 11, 24, 9, 40, tzinfo=UTC),
        )
        self.assertEqual(report["events"], 0)
        self.assertEqual(len((self.directory / "events.jsonl").read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
