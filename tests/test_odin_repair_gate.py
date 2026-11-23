"""Tests for bounded, non-executing repair decisions."""
import unittest

from scripts.odin_repair_gate import decide

SHA = "a" * 40


def state(**changes):
    result = {"base_sha": SHA, "head_sha": "b" * 40, "revision_round": 0,
              "tests": "pass", "review": "pass", "feedback_read": False,
              "agent_action": False, "device_verified": False}
    result.update(changes)
    return result


class RepairGateTests(unittest.TestCase):
    def test_pass_never_authorizes_merge(self):
        result = decide(state())
        self.assertEqual(result["next_action"], "review_for_merge")
        self.assertFalse(result["automatic_merge_authorized"])

    def test_unchanged_source_cannot_pass(self):
        result = decide(state(head_sha=SHA))
        self.assertIn("source_revision_unchanged", result["reasons"])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["automatic_merge_authorized"])

    def test_failure_allows_one_bounded_revision(self):
        self.assertEqual(decide(state(tests="fail"))["next_action"], "request_one_revision")

    def test_second_failed_revision_escalates(self):
        self.assertEqual(decide(state(tests="fail", revision_round=2))["next_action"], "escalate")

    def test_missing_evidence_waits(self):
        self.assertEqual(decide(state(tests="pending"))["next_action"], "await_evidence")

    def test_feedback_read_not_same_as_action(self):
        self.assertIn("feedback_read_without_verified_action",
                      decide(state(feedback_read=True))["reasons"])

    def test_agent_action_requires_independent_feedback_read(self):
        result = decide(state(agent_action=True))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["next_action"], "await_evidence")
        self.assertIn("agent_action_without_verified_feedback_read", result["reasons"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_consistent_read_and_action_do_not_claim_device_install(self):
        result = decide(state(feedback_read=True, agent_action=True))
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["device_verified"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_unreviewed_device_claim_is_blocked(self):
        self.assertIn("device_claim_without_source_acceptance",
                      decide(state(review="fail", device_verified=True))["reasons"])

    def test_invalid_round_and_untrusted_field_rejected(self):
        for item in (state(revision_round=3), state(revision_round=True),
                     {**state(), "shell": "rm -rf /"}):
            with self.assertRaises(ValueError):
                decide(item)


if __name__ == "__main__":
    unittest.main()
