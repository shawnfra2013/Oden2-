"""Tests for bounded no-execution coding agent handoff."""
import unittest

from scripts.odin_agent_handoff import handoff

SHA = "a" * 40


def contract(**changes):
    result = {
        "schema": 1, "issue_number": 97, "base_sha": SHA,
        "allowed_paths": ["scripts/example.py", "tests/test_example.py"],
        "required_tests": ["odin_checks", "ruff"],
        "acceptance_criteria": ["Verify a scoped change independently."],
        "max_review_rounds": 2,
    }
    result.update(changes)
    return result


class HandoffTests(unittest.TestCase):
    def test_ready_is_not_an_attached_agent(self):
        item = handoff(contract(), local_sha=SHA, clean=True)
        self.assertEqual(item["status"], "READY_FOR_OPERATOR_ATTACHED_AGENT")
        self.assertFalse(item["coding_agent_attached_verified"])
        self.assertFalse(item["operator_authorization_verified"])
        self.assertFalse(item["codespace_started"])

    def test_stale_or_dirty_checkout_blocks(self):
        self.assertEqual(handoff(contract(), local_sha="b" * 40, clean=True)["status"], "BLOCKED")
        self.assertEqual(handoff(contract(), local_sha=SHA, clean=False)["status"], "BLOCKED")
        self.assertEqual(handoff(contract(), local_sha=SHA, clean=None)["status"], "BLOCKED")

    def test_scope_prevents_arbitrary_command(self):
        with self.assertRaises(ValueError):
            handoff(contract(shell="bash -c bad"), local_sha=SHA, clean=True)

    def test_disallows_unsafe_file_path_and_excess_rounds(self):
        with self.assertRaises(ValueError):
            handoff(contract(allowed_paths=["../private"]), local_sha=SHA, clean=True)
        with self.assertRaises(ValueError):
            handoff(contract(max_review_rounds=3), local_sha=SHA, clean=True)

    def test_required_tests_and_task_identity_preserved(self):
        result = handoff(contract(), local_sha=SHA, clean=True)
        self.assertEqual(result["issue_number"], 97)
        self.assertEqual(result["required_tests"], ["odin_checks", "ruff"])
        self.assertEqual(result["max_review_rounds"], 2)


if __name__ == "__main__":
    unittest.main()
