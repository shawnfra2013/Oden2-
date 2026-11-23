"""Offline tests for non-authoritative, redacted progress summaries."""
import unittest

from scripts.odin_progress_dashboard import dashboard, render_markdown

ID = "a" * 32
BASE = "b" * 40
CHANGED = "c" * 40
TIME = "2026-11-23T10:00:00Z"


def task():
    return {"schema": 1, "issue_number": 99, "request_id": ID,
            "base_sha": BASE, "events": [], "benchmark": None}


def event(stage, sha=BASE):
    return {"state": stage, "request_id": ID, "head_sha": sha,
            "checked_at": TIME, "evidence_ref": f"evidence:local-only:{stage}"}


def bench():
    return {"baseline_sha": BASE, "candidate_sha": CHANGED,
            "cases": [{"id": f"holdout-{i}", "baseline_pass": i == 0,
                       "candidate_pass": i <= 2, "grader_verified": True,
                       "heldout_attested": True} for i in range(5)]}


class ProgressDashboardTests(unittest.TestCase):
    def test_no_records_cannot_be_green(self):
        result = dashboard(task())
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["next_claimed_stage"], "submitted")
        self.assertFalse(result["agent_action_independently_verified"])

    def test_partial_timeline_stays_claimed(self):
        data = task()
        data["events"] = [event("submitted"), event("device_received")]
        result = dashboard(data)
        self.assertEqual(len(result["claimed_stages"]), 2)
        self.assertEqual(result["next_claimed_stage"], "agent_tool_read")
        self.assertFalse(result["device_verified"])

    def test_full_claims_still_require_independent_proof(self):
        data = task()
        data["events"] = [
            event("submitted"), event("device_received"),
            event("agent_tool_read"), event("action_proposed"),
            event("code_changed", CHANGED), event("source_verified", CHANGED),
        ]
        result = dashboard(data)
        self.assertEqual(result["missing_stages"], [])
        self.assertFalse(result["source_checks_independently_verified"])

    def test_benchmark_claim_does_not_promote_model(self):
        data = task()
        data["benchmark"] = bench()
        result = dashboard(data)
        self.assertEqual(result["benchmark"]["delta_passed_claimed"], 2)
        self.assertFalse(result["benchmark"]["promotion_authorized"])
        self.assertFalse(result["benchmark"]["grader_claims_authenticated"])
        self.assertIn("UNVERIFIED", render_markdown(result))

    def test_rejects_out_of_order_or_mismatched_stage(self):
        data = task()
        data["events"] = [event("device_received")]
        with self.assertRaises(ValueError):
            dashboard(data)
        data["events"] = [event("submitted", CHANGED)]
        with self.assertRaises(ValueError):
            dashboard(data)

    def test_rejects_replayed_milestone_evidence(self):
        data = task()
        data["events"] = [event("submitted"), event("device_received")]
        data["events"][1]["evidence_ref"] = data["events"][0]["evidence_ref"]
        with self.assertRaisesRegex(ValueError, "Replayed evidence reference"):
            dashboard(data)

    def test_rejects_injected_private_data(self):
        data = task()
        data["raw_chat"] = "private"
        with self.assertRaises(ValueError):
            dashboard(data)

    def test_rejects_duplicate_benchmark_case(self):
        data = task()
        data["benchmark"] = bench()
        data["benchmark"]["cases"][1]["id"] = data["benchmark"]["cases"][0]["id"]
        with self.assertRaises(ValueError):
            dashboard(data)


if __name__ == "__main__":
    unittest.main()
