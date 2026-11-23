"""Proof-stage tests for task-specific bidirectional review receipt tracking."""
import copy
import unittest

from scripts import odin_feedback_progress as progress


class FeedbackProgressTests(unittest.TestCase):
    ID = "1" * 32
    OLD = "a" * 40
    NEW = "b" * 40

    def setUp(self):
        self.events = [
            {
                "state": label,
                "request_id": self.ID,
                "head_sha": self.NEW if i >= 4 else self.OLD,
                "checked_at": f"2026-11-23T06:{i:02d}:00Z",
                "evidence_ref": f"receipts/{i:02d}.json",
            }
            for i, label in enumerate(progress.ORDER)
        ]

    def check(self, events=None):
        return progress.validate_milestones(
            self.events if events is None else events,
            request_id=self.ID, original_sha=self.OLD
        )

    def test_delivery_alone_cannot_claim_read_or_correction(self):
        result = self.check(self.events[:2])
        self.assertTrue(result["received"])
        self.assertFalse(result["read_by_agent_tool"])
        self.assertFalse(result["code_change_claimed"])
        self.assertFalse(result["source_ci_claimed"])

    def test_agent_read_not_evidence_of_fix(self):
        result = self.check(self.events[:3])
        self.assertTrue(result["read_by_agent_tool"])
        self.assertFalse(result["code_change_claimed"])

    def test_complete_claim_requires_separate_external_verification(self):
        result = self.check()
        self.assertEqual(result["stage"], "source_verified")
        self.assertEqual(result["last_sha"], self.NEW)
        self.assertFalse(result["evidence_independently_verified"])
        self.assertFalse(result["physical_device_verified"])
        self.assertFalse(result["automatic_followup_implemented"])

    def test_duplicate_and_skipped_stage_rejected(self):
        for case in (self.events[:1] + self.events[:1], self.events[:2] + self.events[3:]):
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.check(case)

    def test_stale_or_changed_commit_before_code_update_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[2]["head_sha"] = self.NEW
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_code_stage_must_create_new_sha(self):
        changed = copy.deepcopy(self.events)
        changed[4]["head_sha"] = self.OLD
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_mismatched_receipt_id_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[1]["request_id"] = "2" * 32
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_reused_evidence_reference_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[2]["evidence_ref"] = changed[1]["evidence_ref"]
        with self.assertRaisesRegex(ValueError, "Replayed evidence reference"):
            self.check(changed)

    def test_reverse_timestamp_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[2]["checked_at"] = "2026-11-23T05:00:00Z"
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_extra_fields_rejected(self):
        changed = copy.deepcopy(self.events)
        changed[3]["command"] = "shell"
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_empty_or_oversized_state_list_rejected(self):
        self.assertEqual(self.check([])["stage"], "UNVERIFIED")
        with self.assertRaises(ValueError):
            self.check(self.events + self.events[:1])


if __name__ == "__main__":
    unittest.main()
