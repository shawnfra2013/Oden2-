"""Regression tests for the offline evidence coverage evaluator."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "coverage_gate", Path(__file__).resolve().parents[1] / "scripts" / "odin_verification_coverage.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SHA = "a" * 40
NOW = dt.datetime(2026, 11, 23, 20, 0, tzinfo=dt.timezone.utc)


def evidence(stage, **overrides):
    row = {"stage": stage, "status": "PASS", "verified": True,
           "proof_kind": stage, "source_sha": SHA, "timestamp": "2026-11-23T19:59:00Z"}
    if stage != "source":
        row["request_id"] = ("%032x" % (1 + module.STAGES.index(stage)))
    row.update(overrides)
    return row


class VerificationCoverageTests(unittest.TestCase):
    def check(self, rows):
        return module.evaluate({"expected_sha": SHA, "evidence": rows}, now=NOW)

    def test_missing_is_unverified(self):
        self.assertEqual(self.check([])["overall"], "UNVERIFIED")

    def test_source_only_does_not_verify_device(self):
        report = self.check([evidence("source")])
        self.assertEqual(report["stages"]["device"]["status"], "UNVERIFIED")

    def test_stale_and_mismatched_are_unverified(self):
        self.assertEqual(self.check([evidence("source", timestamp="2026-11-23T19:00:00Z")])["stages"]["source"]["status"], "UNVERIFIED")
        self.assertEqual(self.check([evidence("source", source_sha="b" * 40)])["stages"]["source"]["status"], "UNVERIFIED")

    def test_duplicate_and_replay_fail(self):
        self.assertEqual(self.check([evidence("source"), evidence("source")])["overall"], "FAIL")
        rid = "f" * 32
        report = self.check([evidence("device", request_id=rid),
                             evidence("memory", request_id=rid)])
        self.assertEqual(report["stages"]["memory"]["reason"], "replayed_request_id")

    def test_agent_needs_authenticated_action(self):
        row = evidence("agent", agent_identity_verified=False, action_executed=False,
                       source_revision_verified=False)
        self.assertEqual(self.check([row])["stages"]["agent"]["reason"], "agent_action_not_authenticated")

    def test_full_valid_metadata(self):
        rows = [evidence(stage) for stage in module.STAGES]
        rows[2].update(agent_identity_verified=True, action_executed=True, source_revision_verified=True)
        self.assertEqual(self.check(rows)["overall"], "PASS")

    def test_invalid_timestamp_does_not_crash(self):
        self.assertEqual(self.check([evidence("source", timestamp=None)])["stages"]["source"]["status"], "UNVERIFIED")

    def test_invalid_expected_sha_rejected(self):
        with self.assertRaises(ValueError):
            module.evaluate({"expected_sha": "abc"}, now=NOW)


if __name__ == "__main__":
    unittest.main()
