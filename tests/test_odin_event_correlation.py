"""Metadata-only GitHub event correlation regression tests."""
import unittest

from scripts.odin_event_correlation import correlate

SHA = "a" * 40


def event(delivery="delivery-1"):
    return {"delivery_id": delivery, "pr": 120, "head_sha": SHA, "action": "synchronize"}


def run(delivery="delivery-1", run_id="run-1"):
    return {"run_id": run_id, "delivery_id": delivery, "pr": 120, "head_sha": SHA}


class EventCorrelationTests(unittest.TestCase):
    def test_matching_event_and_run(self):
        result = correlate([event()], [run()])
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["authenticated_delivery"])

    def test_missing_run_is_blocked(self):
        self.assertIn("unmatched_delivery", str(correlate([event()], [])["findings"]))

    def test_orphan_run_is_blocked(self):
        self.assertIn("orphan_run", str(correlate([], [run()])["findings"]))

    def test_wrong_sha_is_blocked(self):
        bad = run()
        bad["head_sha"] = "b" * 40
        self.assertIn("mismatched_pr_or_sha", str(correlate([event()], [bad])["findings"]))

    def test_duplicate_delivery_and_run_are_detected(self):
        result = correlate([event(), event()], [run(), run(run_id="run-2")])
        self.assertIn("duplicate_delivery", str(result["findings"]))
        self.assertIn("duplicate_run", str(result["findings"]))

    def test_reused_run_id_for_distinct_deliveries_is_blocked(self):
        result = correlate([event("delivery-1"), event("delivery-2")],
                           [run("delivery-1", "same-run"), run("delivery-2", "same-run")])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("reused_run_id", str(result["findings"]))

    def test_unknown_fields_fail_closed(self):
        with self.assertRaises(ValueError):
            correlate([{**event(), "private_payload": "secret"}], [])

    def test_untrusted_ids_rejected(self):
        with self.assertRaises(ValueError):
            correlate([event("../unsafe")], [])


if __name__ == "__main__":
    unittest.main()
