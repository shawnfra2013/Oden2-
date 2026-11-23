"""Fixture tests; no real GitHub API or device requests."""
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts import check_active_docs, odin_project_snapshot as snapshot

SHA = "a" * 40


class SnapshotTests(unittest.TestCase):
    def fake(self, url):
        if url.endswith("/branches/main"):
            return {"commit": {"sha": SHA}}
        if "/actions/runs?" in url:
            return {"workflow_runs": [
                {"head_sha": "b" * 40, "event": "push", "name": "Odin Checks",
                 "created_at": "2026-11-22T21:00:00Z", "status": "completed",
                 "conclusion": "success"},
                {"head_sha": SHA, "event": "push", "name": "Odin Checks",
                 "created_at": "2026-11-22T21:01:00Z", "status": "completed",
                 "conclusion": "success"},
            ]}
        if "/issues?" in url:
            return [{"number": 69, "title": "Cellular test"},
                    {"number": 70, "title": "Tailscale routing"},
                    {"number": 1000, "title": "PR", "pull_request": {}}]
        raise AssertionError(url)

    def test_exact_sha_and_privacy(self):
        state = snapshot.collect(self.fake, datetime(2026, 11, 22, 22, 0, tzinfo=UTC))
        self.assertEqual(state["main_sha"], SHA)
        self.assertEqual(state["source_ci"], "passed exact main SHA")
        self.assertEqual(len(state["issues"]), 2)
        report = snapshot.render_status(state)
        self.assertIn("2026-11-22T22:00:00Z", report)
        self.assertIn("private mailbox excluded", report)
        self.assertIn("#69", snapshot.render_handoff(state))

    def test_wrong_sha_cannot_pass(self):
        def fetch(url):
            response = self.fake(url)
            if "/actions/runs?" in url:
                response["workflow_runs"] = [response["workflow_runs"][0]]
            return response
        self.assertNotIn("passed exact", snapshot.collect(fetch)["source_ci"])

    def test_unavailable_source_is_not_success(self):
        def fail(_url):
            raise OSError("offline")
        state = snapshot.collect(fail)
        self.assertIsNone(state["main_sha"])
        self.assertEqual(state["source_ci"], "unverified")
        self.assertEqual(len(state["errors"]), 2)

    def test_guard_rejects_obsolete_active_text_and_allows_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in check_active_docs.REQUIRED:
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("Odin Local Workstation\n", encoding="utf-8")
            archive = root / "docs/archive/older.md"
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_text("historical Vercel endpoint", encoding="utf-8")
            self.assertEqual(check_active_docs.check(root), [])
            (root / "README.md").write_text("Use Vercel now", encoding="utf-8")
            self.assertTrue(any("retired host" in x for x in check_active_docs.check(root)))
            (root / "README.md").write_text("Open Stage 5", encoding="utf-8")
            self.assertTrue(any("obsolete phase" in x for x in check_active_docs.check(root)))


if __name__ == "__main__":
    unittest.main()
