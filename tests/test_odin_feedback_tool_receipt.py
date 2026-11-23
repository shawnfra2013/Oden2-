"""Local feedback tool-presentation proof, no inferred agent execution."""
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts import odin_feedback_tool_receipt as tool
from scripts import odin_review_feedback as review


class FeedbackToolReceiptTests(unittest.TestCase):
    ID = "a" * 32

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inbox = self.root / "feedback"
        self.output = self.root / "tool-observed"
        self.note = {
            "version": 1,
            "id": self.ID,
            "issue_number": 99,
            "pr_number": 112,
            "head_sha": "c" * 40,
            "reference_receipt_id": "b" * 32,
            "decision": "revise",
            "feedback_note": "Add a deterministic guard for incorrect input.",
        }
        review.record_feedback(self.note, inbox=self.inbox)
        self.now = datetime(2026, 11, 23, 8, 5, tzinfo=UTC)

    def inspect(self, **changes):
        return tool.inspect_feedback(
            self.ID, inbox=self.inbox, receipt_dir=self.output,
            now=self.now, **changes,
        )

    def receipt(self):
        return self.output / (self.ID + ".json")

    def test_maximum_unicode_note_reaches_both_readers(self):
        note_id = "f" * 32
        note = "\U0001f30d" * review.MAX_NOTE_LENGTH
        payload = {**self.note, "id": note_id, "feedback_note": note}
        self.assertTrue(review.record_feedback(payload, inbox=self.inbox)["recorded"])
        self.assertGreater((self.inbox / (note_id + ".json")).stat().st_size, 2048)
        listed = {item["id"]: item for item in review.list_feedback(inbox=self.inbox)}
        with self.subTest(reader="list"):
            self.assertIn(note_id, listed)
            self.assertEqual(listed[note_id]["feedback_note"], note)
        with self.subTest(reader="inspect"):
            result = tool.inspect_feedback(note_id, inbox=self.inbox, receipt_dir=self.output)
            self.assertEqual(result["untrusted_feedback"]["feedback_note"], note)
            record = json.loads(tool.load_candidate(self.output / (note_id + ".json")))
            self.assertEqual(record["note_sha256"], hashlib.sha256(note.encode()).hexdigest())
            self.assertNotIn("feedback_note", record)

    def test_oversized_stored_note_skipped_without_receipt(self):
        path = self.inbox / (self.ID + ".json")
        path.write_bytes(path.read_bytes().ljust(review.MAX_STORED_FEEDBACK_BYTES + 1, b" "))
        self.assertEqual(review.list_feedback(inbox=self.inbox), [])
        with self.assertRaises(ValueError):
            self.inspect()
        self.assertFalse(self.output.exists())

    def test_unpaired_surrogate_rejected_before_storage(self):
        for note_id, escaped in (("d" * 32, r'"\ud800"'), ("e" * 32, r'"\udfff"')):
            with self.subTest(escaped=escaped):
                payload = {**self.note, "id": note_id, "feedback_note": json.loads(escaped)}
                with self.assertRaisesRegex(ValueError, "Invalid feedback note"):
                    review.record_feedback(payload, inbox=self.inbox)
                self.assertFalse((self.inbox / (note_id + ".json")).exists())
        self.assertFalse(self.output.exists())

    def test_explicit_inspection_presents_note_and_creates_nonexecuting_receipt(self):
        result = self.inspect()
        self.assertIn("deterministic guard", result["untrusted_feedback"]["feedback_note"])
        self.assertFalse(result["local_tool_receipt"]["agent_identity_verified"])
        self.assertFalse(result["local_tool_receipt"]["action_executed"])
        raw = tool.load_candidate(self.receipt())
        record = tool.validate_tool_receipt(raw, self.ID)
        self.assertEqual(record["scope"], "local_feedback_tool_presented")
        self.assertEqual(record["note_sha256"], hashlib.sha256(self.note["feedback_note"].encode()).hexdigest())
        self.assertNotIn("deterministic guard", raw.decode())
        self.assertNotIn("feedback_note", raw.decode())
        self.assertEqual(self.receipt().stat().st_mode & 0o777, 0o600)

    def test_reinspection_preserves_original_first_tool_receipt(self):
        self.inspect()
        before = self.receipt().read_bytes()
        self.inspect()
        self.assertEqual(self.receipt().read_bytes(), before)
        self.assertEqual(len(list(self.output.glob("*.json"))), 1)

    def test_reinspection_after_changed_note_fails_closed(self):
        self.inspect()
        saved = self.receipt().read_bytes()
        payload = {**self.note, "feedback_note": "Changed review"}
        (self.inbox / (self.ID + ".json")).write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.inspect()
        self.assertEqual(self.receipt().read_bytes(), saved)

    def test_refuse_traversal_and_mismatched_ids(self):
        with self.assertRaises(ValueError):
            tool.inspect_feedback("../escape", inbox=self.inbox, receipt_dir=self.output)
        self.note["id"] = "d" * 32
        (self.inbox / (self.ID + ".json")).write_text(json.dumps(self.note), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.inspect()

    def test_refuse_symlinked_note_and_receipt_directory(self):
        current = self.inbox / (self.ID + ".json")
        current.unlink()
        current.symlink_to(self.root / "target")
        with self.assertRaises(ValueError):
            self.inspect()
        current.unlink()
        review.record_feedback(self.note, inbox=self.inbox)
        self.output.symlink_to(self.root / "other", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.inspect()

    def test_forged_tool_success_and_extra_fields_are_rejected(self):
        self.inspect()
        record = json.loads(self.receipt().read_text())
        for change in (
            {"action_executed": True},
            {"agent_identity_verified": True},
            {"source_revision_verified": True},
            {"command": "shell"},
            {"note_sha256": "bad"},
        ):
            with self.subTest(change=change):
                modified = {**record, **change}
                with self.assertRaises(ValueError):
                    tool.validate_tool_receipt(json.dumps(modified).encode(), self.ID)

    def test_invalid_local_receipts_are_skipped_for_private_upload(self):
        self.inspect()
        (self.output / ("d" * 32 + ".json")).symlink_to(self.receipt())
        (self.output / "invalid.json").write_text("{}")
        self.assertEqual([x.name for x in tool.local_candidates(self.output)], [self.ID + ".json"])
        with self.assertRaises(ValueError):
            tool.load_candidate(self.output / "invalid.json")

    def test_no_automatic_ack_for_read_only_list(self):
        feedback = review.list_feedback(inbox=self.inbox)
        self.assertEqual(feedback[0]["id"], self.ID)
        self.assertFalse(self.output.exists())

    def test_missing_note_does_not_create_ack(self):
        (self.inbox / (self.ID + ".json")).unlink()
        with self.assertRaises(FileNotFoundError):
            self.inspect()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
