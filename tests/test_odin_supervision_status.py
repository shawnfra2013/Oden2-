"""Source-only supervision health summary regression tests."""
import unittest
from datetime import UTC, datetime

from scripts.odin_supervision_status import summarize


def data(**changes):
    obj = {"git_sha": "a" * 40, "ci": "PASS", "event_delivery": "PASS",
           "memory_index": "PASS", "feedback_action": "PASS",
           "device_install": "PASS", "last_receipt_utc": "2026-11-23T10:00:00Z"}
    obj.update(changes)
    return obj


class StatusTests(unittest.TestCase):
    def test_all_evidence_passes(self):
        self.assertEqual(summarize(data(), now=datetime(2026, 11, 23, 10, 1, tzinfo=UTC))["status"], "PASS")

    def test_unknown_device_is_not_green(self):
        self.assertEqual(summarize(data(device_install="UNVERIFIED"))["status"], "UNVERIFIED")

    def test_failed_ci_dominates(self):
        self.assertEqual(summarize(data(ci="FAIL", device_install="UNVERIFIED"))["status"], "FAIL")

    def test_blocked_feedback(self):
        self.assertEqual(summarize(data(feedback_action="BLOCKED"))["status"], "BLOCKED")

    def test_missing_receipt_unverified(self):
        self.assertEqual(summarize(data(last_receipt_utc=None))["status"], "UNVERIFIED")

    def test_stale_receipt_is_unverified(self):
        result = summarize(data(), now=datetime(2026, 11, 23, 11, 0, tzinfo=UTC))
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertFalse(result["receipt_fresh"])

    def test_future_receipt_cannot_pass(self):
        result = summarize(data(), now=datetime(2026, 11, 23, 9, 59, tzinfo=UTC))
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_invalid_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            summarize(data(last_receipt_utc="2026-02-31T10:00:00Z"))

    def test_injected_fields_rejected(self):
        with self.assertRaises(ValueError):
            summarize({**data(), "private_message": "secret"})

    def test_invalid_sha_rejected(self):
        with self.assertRaises(ValueError):
            summarize(data(git_sha="main"))


if __name__ == "__main__":
    unittest.main()
