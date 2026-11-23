"""Offline regression tests for authenticated GitHub evidence adapter."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "github_evidence", Path(__file__).resolve().parents[1] / "scripts" / "odin_verification_github.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA = "a" * 40


class GithubEvidenceTests(unittest.TestCase):
    def test_source_exact_head_pass(self):
        def fetch(url):
            return {"check_runs": [
                {"name": name, "head_sha": SHA, "status": "completed",
                 "conclusion": "success", "completed_at": "2026-11-23T20:00:00Z"}
                for name in m.REQUIRED_CHECKS
            ]}
        self.assertEqual(m.check_source(SHA, fetch)["status"], "PASS")

    def test_wrong_head_never_passes(self):
        def fetch(url):
            return {"check_runs": [
                {"name": name, "head_sha": "b" * 40, "status": "completed",
                 "conclusion": "success", "completed_at": "2026-11-23T20:00:00Z"}
                for name in m.REQUIRED_CHECKS
            ]}
        self.assertEqual(m.check_source(SHA, fetch)["status"], "UNVERIFIED")

    def test_failed_ci_is_fail(self):
        def fetch(url):
            return {"check_runs": [
                {"name": name, "head_sha": SHA, "status": "completed",
                 "conclusion": "failure" if name == "browser" else "success",
                 "completed_at": "2026-11-23T20:00:00Z"}
                for name in m.REQUIRED_CHECKS
            ]}
        self.assertEqual(m.check_source(SHA, fetch)["status"], "FAIL")

    def test_missing_private_auth_is_unverified(self):
        self.assertEqual(m.check_private_source_receipts(SHA, None)["status"], "UNVERIFIED")

    def test_private_conflict_fails_without_payload_leak(self):
        rid = "a" * 32
        def fetch(url, token):
            if "?" in url and "/local-source-receipts?" in url:
                return [{"name": rid + ".json"}]
            return {"id": "b" * 32, "source_sha": SHA, "status": "PASS",
                    "completed_at": "2026-11-23T20:00:00+00:00"}
        result = m.check_private_source_receipts(SHA, "secret", fetch)
        self.assertEqual(result["status"], "FAIL")
        self.assertNotIn("secret", str(result))

    def test_utc_offset_accepted(self):
        self.assertIsNotNone(m._utc("2026-11-23T20:00:00+00:00"))
        self.assertIsNone(m._utc("2026-11-23T20:00:00+02:00"))


if __name__ == "__main__":
    unittest.main()
