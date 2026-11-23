"""Offline, metadata-only held-out coding comparison tests."""
import unittest

from scripts.odin_coding_benchmark import compare


def report():
    return {"baseline_sha": "a" * 40, "candidate_sha": "b" * 40,
            "cases": [{"id": f"case-{i}", "baseline_pass": i < 2,
                       "candidate_pass": i < 4, "grader_verified": True,
                       "heldout_attested": True} for i in range(5)]}


class BenchmarkTests(unittest.TestCase):
    def test_improvement_is_reported_without_promotion(self):
        result = compare(report())
        self.assertEqual(result["delta_passed"], 2)
        self.assertFalse(result["promotion_authorized"])
        self.assertFalse(result["grader_claims_authenticated"])

    def test_regression_fails(self):
        data = report()
        for case in data["cases"]:
            case["candidate_pass"] = False
        self.assertEqual(compare(data)["status"], "FAIL")

    def test_missing_grader_proof_blocks(self):
        data = report()
        data["cases"][0]["grader_verified"] = False
        self.assertEqual(compare(data)["status"], "BLOCKED")

    def test_disclosed_cases_block(self):
        data = report()
        data["cases"][0]["heldout_attested"] = False
        self.assertEqual(compare(data)["status"], "BLOCKED")

    def test_duplicate_case_rejected(self):
        data = report()
        data["cases"][1]["id"] = data["cases"][0]["id"]
        with self.assertRaises(ValueError):
            compare(data)

    def test_missing_or_invented_fields_rejected(self):
        data = report()
        data["cases"][0]["test_code"] = "untrusted"
        with self.assertRaises(ValueError):
            compare(data)


if __name__ == "__main__":
    unittest.main()
