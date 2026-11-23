"""Private mailbox delivery of explicit, non-executing local tool observations."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_feedback_tool_receipt as receipts
from scripts import odin_github_bridge as bridge
from scripts import odin_review_feedback as review


class FeedbackToolBridgeTests(unittest.TestCase):
    ID = "c" * 32

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inbox = self.root / "feedback"
        self.local = self.root / "tool"
        self.outbox = self.root / "outbox"
        self.state = self.root / "state"
        self.outbox.mkdir()
        self.state.mkdir()
        message = {
            "version": 1, "id": self.ID, "issue_number": 99,
            "pr_number": 112, "head_sha": "d" * 40,
            "reference_receipt_id": "b" * 32, "decision": "hold",
            "feedback_note": "Wait for exact reviewed source results.",
        }
        review.record_feedback(message, inbox=self.inbox)
        receipts.inspect_feedback(self.ID, inbox=self.inbox, receipt_dir=self.local)
        self.payload = (self.local / (self.ID + ".json")).read_bytes()
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "test@example.invalid"],
            ["git", "config", "user.name", "Odin Test"],
        ):
            subprocess.run(cmd, cwd=self.outbox, check=True, capture_output=True)
        (self.outbox / "seed.txt").write_text("seed\n")
        for cmd in (["git", "add", "seed.txt"], ["git", "commit", "-q", "-m", "seed"]):
            subprocess.run(cmd, cwd=self.outbox, check=True, capture_output=True)
        for obj, field, value in (
            (bridge, "STATE", self.state),
            (bridge, "OUTBOX", self.outbox),
            (bridge, "private_mailbox", True),
            (receipts, "DEFAULT_OBSERVED", self.local),
        ):
            p = patch.object(obj, field, value)
            p.start()
            self.addCleanup(p.stop)

    def destination(self):
        return self.outbox / receipts.remote_path(self.ID)

    def test_first_delivery_and_second_poll_are_idempotent(self):
        with patch.object(bridge, "outbox_git", return_value="") as send:
            self.assertEqual(bridge.publish_local_feedback_tool_receipts(), 1)
            self.assertEqual(bridge.publish_local_feedback_tool_receipts(), 0)
            send.assert_called_once()
        self.assertEqual(self.destination().read_bytes(), self.payload)
        self.assertTrue((self.local / (self.ID + ".json")).is_file())
        self.assertNotIn("Wait for exact", self.destination().read_text())

    def test_failed_push_retains_commit_and_local_evidence(self):
        with patch.object(bridge, "outbox_git", side_effect=RuntimeError("network unavailable")):
            with self.assertRaises(RuntimeError):
                bridge.publish_local_feedback_tool_receipts()
        self.assertTrue(self.destination().is_file())
        self.assertTrue((self.local / (self.ID + ".json")).is_file())
        self.assertFalse((self.state / "pending-feedback-tool-receipt.json").exists())
        count = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"], cwd=self.outbox,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(count, "2")

    def test_resume_uncommitted_pending_journal_without_rewriting(self):
        (self.state / "pending-feedback-tool-receipt.json").write_bytes(self.payload)
        bridge.recover_pending_feedback_tool_receipt()
        self.assertEqual(self.destination().read_bytes(), self.payload)
        bridge.recover_pending_feedback_tool_receipt()
        self.assertFalse((self.state / "pending-feedback-tool-receipt.json").exists())

    def test_refuse_conflicting_private_receipt_id(self):
        target = self.destination()
        target.parent.mkdir(parents=True)
        target.write_text("conflicting content")
        with self.assertRaises(RuntimeError):
            bridge.publish_local_feedback_tool_receipts()
        self.assertEqual(target.read_text(), "conflicting content")
        self.assertTrue((self.local / (self.ID + ".json")).is_file())

    def test_refuse_redirected_outbox_directory(self):
        other = self.root / "elsewhere"
        other.mkdir()
        (self.outbox / "bridge").symlink_to(other, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            bridge.publish_local_feedback_tool_receipts()
        self.assertEqual(list(other.iterdir()), [])

    def test_invalid_receipt_skipped_not_published(self):
        (self.local / (self.ID + ".json")).write_text('{"action_executed":true}')
        with patch.object(bridge, "outbox_git", return_value="") as send:
            self.assertEqual(bridge.publish_local_feedback_tool_receipts(), 0)
            send.assert_not_called()
        self.assertFalse(self.destination().exists())

    def test_pending_feedback_tool_receipt_never_reports_execution(self):
        with patch.object(bridge, "outbox_git", return_value=""):
            bridge.publish_local_feedback_tool_receipts()
        uploaded = json.loads(self.destination().read_text())
        self.assertFalse(uploaded["action_executed"])
        self.assertFalse(uploaded["agent_identity_verified"])
        self.assertFalse(uploaded["source_revision_verified"])


if __name__ == "__main__":
    unittest.main()
