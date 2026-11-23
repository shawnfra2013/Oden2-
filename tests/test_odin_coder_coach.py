"""Coding coach: honest static feedback and immutable proposal receipts."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.agent import pipeline
from scripts import odin_coder_coach as coach


class SourceCritiqueTests(unittest.TestCase):
    def test_candidate_needs_tests_not_automatic_pass(self):
        review = coach.critique(
            "def total(items):\n    return sum(items)\n",
            "def total(items):\n    return sum(x * 2 for x in items)\n",
        )
        self.assertEqual(review["status"], "candidate_needs_verified_tests")
        self.assertEqual(review["codes"], [])
        self.assertFalse(review["functional_tests_verified"])
        self.assertFalse(review["security_review_verified"])

    def test_noop_edit_is_not_accepted(self):
        review = coach.critique(
            "def total(items):\n    return sum(items)\n",
            "def total(items):  # cosmetic only\n    return sum(items)\n",
        )
        self.assertEqual(review["status"], "revision_required")
        self.assertIn("no_semantic_change", review["codes"])

    def test_public_interface_removed_is_flagged(self):
        review = coach.critique(
            "def total(items):\n    return sum(items)\n",
            "def new_total(items):\n    return sum(items)\n",
        )
        self.assertIn("public_symbols_removed", review["codes"])
        self.assertEqual(review["public_removed"], ["total"])

    def test_public_signature_changed_is_flagged(self):
        review = coach.critique(
            "def total(items):\n    return sum(items)\n",
            "def total(items, scale=2):\n    return sum(items) * scale\n",
        )
        self.assertIn("public_signatures_changed", review["codes"])
        self.assertEqual(review["public_signatures_changed"], ["total"])

    def test_new_sensitive_calls_require_review(self):
        review = coach.critique(
            "def total(items):\n    return sum(items)\n",
            "import subprocess\n"
            "def total(items):\n    subprocess.run(['true'])\n    return sum(items)\n",
        )
        self.assertEqual(review["status"], "revision_required")
        self.assertEqual(review["new_sensitive_calls"], ["subprocess.run"])

    def test_existing_sensitive_call_does_not_create_false_new_flag(self):
        review = coach.critique(
            "import subprocess\n"
            "def total(items):\n    subprocess.run(['true'])\n    return sum(items)\n",
            "import subprocess\n"
            "def total(items):\n    subprocess.run(['true'])\n    return sum(items) + 1\n",
        )
        self.assertNotIn("sensitive_calls_added", review["codes"])

    def test_invalid_syntax_and_oversized_candidate_fail_closed(self):
        result = coach.critique("", "def broken(:\n")
        self.assertIn("syntax_invalid", result["codes"])
        with self.assertRaises(ValueError):
            coach.critique("", "a" * (pipeline.MAX_SOURCE + 1))


class ReceiptReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        (self.root / "ai/agent").mkdir(parents=True)
        self.name = "ai/agent/example.py"
        self.original = "def total(items):\n    return sum(items)\n"
        (self.root / self.name).write_text(self.original)
        self.owner = "a" * 12
        self.invocation = "b" * 32
        self.task = "Make total double the result without changing its interface."
        self.candidate = "def total(items):\n    return 2 * sum(items)\n"
        self.parts = pipeline.reserve(self.root, self.owner, self.invocation)
        self._store_candidate(self.candidate)

    def _store_candidate(self, content):
        raw = content.encode("utf-8")
        sha, _ = pipeline.baseline(self.root, self.name)
        metadata = {
            "schema": pipeline.SCHEMA, "target": self.name,
            "task": self.task, "task_id": self.owner,
            "invocation_id": self.invocation,
            "baseline_sha256": sha,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw), "syntax": "passed", "ruff": "passed",
            "applied": False,
        }
        pipeline.publish(self.root, (*self.parts, "candidate.py"), raw)
        pipeline.publish(self.root, (*self.parts, "metadata.json"),
                         pipeline.json_bytes(metadata))

    def test_approved_receipt_is_critically_reviewed_and_not_executed(self):
        # The model proposal is never executed; only its AST is inspected.
        with patch("subprocess.run", side_effect=AssertionError("Executed proposal!")):
            report = coach.review_proposal(
                self.root, self.name, self.task, self.owner, self.invocation,
            )
        self.assertEqual(report["status"], "candidate_needs_verified_tests")
        self.assertFalse(report["model_weights_updated"])
        self.assertFalse(report["candidate_deployed"])
        self.assertFalse(report["training_example_approved"])
        self.assertEqual(report["candidate_sha256"],
                         hashlib.sha256(self.candidate.encode()).hexdigest())
        saved = json.loads((self.root.joinpath(*self.parts) / "critique.json").read_text())
        self.assertEqual(saved, report)
        self.assertEqual((self.root / self.name).read_text(), self.original)

    def test_no_overwrite_or_duplicate_training_record(self):
        first = coach.review_proposal(self.root, self.name, self.task,
                                      self.owner, self.invocation)
        location = self.root.joinpath(*self.parts) / "critique.json"
        before = location.read_bytes()
        second = coach.review_proposal(self.root, self.name, self.task,
                                       self.owner, self.invocation)
        self.assertEqual(first, second)
        self.assertEqual(location.read_bytes(), before)
        self.assertEqual(len(list(location.parent.glob("critique.json"))), 1)

    def test_conflicting_existing_critique_is_not_overwritten(self):
        location = self.root.joinpath(*self.parts) / "critique.json"
        location.write_bytes(b'{"unexpected":true}\n')
        with self.assertRaises(ValueError):
            coach.review_proposal(self.root, self.name, self.task,
                                  self.owner, self.invocation)
        self.assertEqual(location.read_bytes(), b'{"unexpected":true}\n')

    def test_baseline_move_blocks_review_and_preserves_original(self):
        (self.root / self.name).write_text("def total(items):\n    return 123\n")
        with self.assertRaises(ValueError):
            coach.review_proposal(self.root, self.name, self.task,
                                  self.owner, self.invocation)
        self.assertFalse((self.root.joinpath(*self.parts) / "critique.json").exists())

    def test_mismatched_task_metadata_blocks_review(self):
        with self.assertRaises(ValueError):
            coach.review_proposal(self.root, self.name, "Different task",
                                  self.owner, self.invocation)
        self.assertFalse((self.root.joinpath(*self.parts) / "critique.json").exists())

    def test_public_feedback_does_not_copy_source_or_original_task(self):
        report = coach.review_proposal(
            self.root, self.name, self.task, self.owner, self.invocation,
        )
        serialized = json.dumps(report)
        self.assertNotIn("Make total double", serialized)
        self.assertNotIn("def total", serialized)
        self.assertNotIn("return 2 * sum", serialized)
        self.assertIn("candidate_sha256", serialized)


if __name__ == "__main__":
    unittest.main()
