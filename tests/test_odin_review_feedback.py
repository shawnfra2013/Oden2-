"""Safety and round-trip tests for private review-feedback communication."""
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import odin_github_bridge as bridge
from scripts import odin_review_feedback as review


class ReviewFeedbackTests(unittest.TestCase):
    ID = "0123456789abcdef0123456789abcdef"
    REF = "abcdef0123456789abcdef0123456789"

    def setUp(self):
        self.now = datetime(2026, 11, 23, tzinfo=UTC)
        self.req = {
            "version": 1, "id": self.ID, "action": "review_feedback",
            "created_at": bridge.iso(self.now),
            "expires_at": bridge.iso(self.now + timedelta(minutes=15)),
            "issue_number": 86, "pr_number": 93,
            "head_sha": "a" * 40,
            "reference_receipt_id": self.REF,
            "decision": "revise",
            "feedback_note": "Add test coverage for duplicate request IDs.",
        }

    def validate(self, *, private=True):
        with patch.object(bridge, "private_mailbox", private):
            return bridge.validate_request(json.dumps(self.req), self.ID, now=self.now)

    def test_private_feedback_only(self):
        self.assertEqual(self.validate()["decision"], "revise")
        with self.assertRaises(ValueError):
            self.validate(private=False)

    def test_reject_extra_unknown_fields(self):
        self.req["command"] = "rm -rf /"
        with self.assertRaises(ValueError):
            self.validate()

    def test_reject_invalid_source_identifiers(self):
        for key, bad in (
            ("issue_number", True), ("pr_number", 0),
            ("head_sha", "a" * 39), ("reference_receipt_id", "../oops"),
            ("decision", "merge"), ("feedback_note", ""),
            ("feedback_note", "A\nB"),
        ):
            with self.subTest(key=key, bad=bad):
                old = self.req[key]
                self.req[key] = bad
                with self.assertRaises(ValueError):
                    self.validate()
                self.req[key] = old

    def test_reject_invalid_receipt_reference(self):
        self.req["reference_receipt_id"] = "X" * 32
        with self.assertRaises(ValueError):
            self.validate()

    def test_reject_oversized_and_expired_request(self):
        self.req["feedback_note"] = "x" * 601
        with self.assertRaises(ValueError):
            self.validate()
        self.req["feedback_note"] = "review"
        self.req["created_at"] = bridge.iso(self.now - timedelta(minutes=10))
        self.req["expires_at"] = bridge.iso(self.now - timedelta(seconds=1))
        with self.assertRaises(bridge.ExpiredRequest):
            self.validate()

    def test_record_roundtrip_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory) / "private-feedback"
            with patch.object(bridge, "private_mailbox", True), \
                    patch.object(bridge, "STATE", Path(directory)):
                validated = self.validate()
                receipt = bridge.status_action("review_feedback", validated)
                self.assertTrue(receipt["recorded"])
                self.assertFalse(receipt["source_revision_verified"])
                self.assertFalse(receipt["action_executed"])
                self.assertEqual(receipt["reference_receipt_id"], self.REF)
                self.assertEqual(receipt, bridge.status_action("review_feedback", validated))
                stored = review.list_feedback(inbox=Path(directory) / "review-feedback")
                self.assertEqual(stored[0]["id"], self.ID)
                self.assertFalse(stored[0]["trusted"])
                self.assertIn("duplicate request", stored[0]["feedback_note"])
            self.assertFalse(inbox.exists())  # only the explicit state directory is touched

    def test_replay_cannot_replace_different_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            inbox = Path(directory) / "feedback"
            review.record_feedback(self.req, inbox=inbox)
            self.req["feedback_note"] = "Replace original"
            with self.assertRaises(ValueError):
                review.record_feedback(self.req, inbox=inbox)

    def test_reject_unsafe_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "link").symlink_to(path / "real")
            with self.assertRaises(ValueError):
                review.record_feedback(self.req, inbox=path / "link")

    def test_no_private_message_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.req["feedback_note"] = "run adb shell and deploy now"
            with patch.object(bridge, "private_mailbox", True):
                review.record_feedback(self.req, inbox=Path(directory))
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)
            self.assertFalse(review.list_feedback(inbox=Path(directory))[0]["action_executed"])

    def test_public_status_cannot_accept_review(self):
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.status_action("review_feedback", self.req)


if __name__ == "__main__":
    unittest.main()
