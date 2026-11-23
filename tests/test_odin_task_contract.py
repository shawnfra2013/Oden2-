"""Offline task contract tests: exact scope, missing tests, and unsafe expansions."""
import copy
import unittest
from scripts import odin_task_contract as task


class OdinTaskContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "schema": 1,
            "issue_number": 98,
            "base_sha": "a" * 40,
            "allowed_paths": ["scripts/example.py", "tests/test_example.py"],
            "required_tests": ["odin_checks", "ruff"],
            "acceptance_criteria": ["One bounded change with a regression test."],
            "max_review_rounds": 2,
        }
        self.observed = {
            "issue_number": 98,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_paths": ["scripts/example.py", "tests/test_example.py"],
            "tests": {"odin_checks": True, "ruff": True},
            "review_round": 1,
        }

    def evaluate(self):
        return task.evaluate_contract(self.contract, self.observed)

    def test_complete_scope_is_source_candidate_not_authentication(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["evidence_authenticated"])
        self.assertFalse(result["device_verified"])

    def test_missing_required_test_fails(self):
        self.observed["tests"].pop("ruff")
        result = self.evaluate()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("missing_test:ruff", result["reasons"])

    def test_failed_required_test_fails(self):
        self.observed["tests"]["odin_checks"] = False
        self.assertIn("failed_test:odin_checks", self.evaluate()["reasons"])

    def test_unapproved_path_fails(self):
        self.observed["changed_paths"].append("secrets/local.env")
        self.assertIn("out_of_scope_paths", self.evaluate()["reasons"])

    def test_extra_path_in_contract_must_be_approved_not_wildcard(self):
        for path in ("../outside", "scripts/../bad.py", "/absolute", "a/*.py", "a\\b"):
            with self.subTest(path=path):
                self.contract["allowed_paths"] = [path]
                with self.assertRaises(ValueError):
                    self.evaluate()

    def test_claimed_code_change_requires_new_revision(self):
        self.observed["head_sha"] = self.contract["base_sha"]
        result = self.evaluate()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("unchanged_head_sha", result["reasons"])

    def test_duplicate_changed_paths_fail_closed(self):
        self.observed["changed_paths"] = [
            "scripts/example.py", "scripts/example.py", "tests/test_example.py",
        ]
        result = self.evaluate()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("duplicate_changed_paths", result["reasons"])

    def test_duplicate_out_of_scope_paths_record_both_failures(self):
        self.observed["changed_paths"] = ["secrets/local.env", "secrets/local.env"]
        result = self.evaluate()
        self.assertIn("duplicate_changed_paths", result["reasons"])
        self.assertIn("out_of_scope_paths", result["reasons"])

    def test_wrong_issue_or_revision_fails(self):
        self.observed["issue_number"] = 99
        self.observed["base_sha"] = "c" * 40
        self.assertIn("issue_mismatch", self.evaluate()["reasons"])
        self.assertIn("base_sha_mismatch", self.evaluate()["reasons"])

    def test_review_round_budget_fails(self):
        self.observed["review_round"] = 3
        self.assertIn("review_budget_exceeded", self.evaluate()["reasons"])

    def test_malformed_or_broad_contract_rejected(self):
        self.contract["max_review_rounds"] = 9
        with self.assertRaises(ValueError):
            self.evaluate()
        self.contract["max_review_rounds"] = 2
        self.contract["shell_command"] = "bash"
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_schema_boolean_cannot_masquerade_as_schema_one(self):
        self.contract["schema"] = True
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_unhashable_required_test_is_safe_validation_error(self):
        self.contract["required_tests"] = [["odin_checks"]]
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_control_character_paths_are_rejected(self):
        for invalid in ("scripts/hello\\n.py", "scripts/hello\\x00.py", "scripts/test\\t.py"):
            with self.subTest(invalid=invalid):
                self.observed["changed_paths"] = [invalid]
                self.assertIn("invalid_changed_paths", self.evaluate()["reasons"])

    def test_unbounded_changed_paths_fail_closed(self):
        self.observed["changed_paths"] = ["scripts/example.py"] * 51
        self.assertIn("invalid_changed_paths", self.evaluate()["reasons"])

    def test_unknown_evidence_field_is_rejected(self):
        self.observed["device_verified"] = True
        with self.assertRaises(ValueError):
            self.evaluate()

    def test_empty_changed_paths_does_not_pass(self):
        self.observed["changed_paths"] = []
        self.assertEqual(self.evaluate()["status"], "FAIL")

    def test_unexpected_evidence_shapes_fail_closed(self):
        examples = ({"odin_checks": "pass", "ruff": True}, [],
                    {"odin_checks": 1, "ruff": True})
        for case in examples:
            with self.subTest(case=case):
                self.observed["tests"] = copy.deepcopy(case)
                self.assertEqual(self.evaluate()["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
