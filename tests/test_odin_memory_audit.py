"""Offline regression checks for read-only memory integrity auditing."""
import contextlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_memory_audit as auditor
from scripts import odin_project_memory as memory


class MemoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/PROJECT_MEMORY.md").write_text(
            "# Canonical\n\n## Evidence\nUnique memory statement.\n",
            encoding="utf-8")
        self.db = self.root / "state/project-memory/index.sqlite3"
        self.rev = patch.object(memory, "_revision", return_value="a" * 40)
        self.rev.start()
        self.addCleanup(self.rev.stop)

    def check(self):
        with patch.object(auditor.memory, "_revision", return_value="a" * 40):
            return auditor.audit(self.root)

    def test_missing_index_is_failure_without_creating_one(self):
        self.assertIn("missing_index", self.check()["findings"])
        self.assertFalse(self.db.exists())

    def test_fresh_index_passes_and_does_not_write(self):
        memory.ensure_index(self.root)
        before = self.db.read_bytes()
        self.assertEqual(self.check()["status"], "PASS")
        self.assertEqual(self.db.read_bytes(), before)

    def test_changed_document_is_detected(self):
        memory.ensure_index(self.root)
        with (self.root / "docs/PROJECT_MEMORY.md").open("a") as out:
            out.write("\nNew evidence.\n")
        self.assertIn("stale_document_fingerprint", self.check()["findings"])

    def test_duplicate_and_unapproved_snippets_are_detected(self):
        memory.ensure_index(self.root)
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            original = db.execute("SELECT path,heading,body FROM snippets LIMIT 1").fetchone()
            db.execute("INSERT INTO snippets(path,heading,body) VALUES(?,?,?)", original)
            db.execute("INSERT INTO snippets(path,heading,body) VALUES(?,?,?)",
                       ("private/mailbox.txt", "secret", "do not expose"))
            db.commit()
        result = self.check()
        self.assertIn("duplicate_snippets", result["findings"])
        self.assertIn("unapproved_source_path", result["findings"])
        self.assertNotIn("do not expose", str(result))

    def test_symlinked_state_directory_is_rejected_without_reading_target(self):
        memory.ensure_index(self.root)
        other = self.root / "external-state"
        (self.root / "state").rename(other)
        (self.root / "state").symlink_to(other, target_is_directory=True)
        result = self.check()
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("unsafe_index_path", result["findings"])

    def test_corrupt_index_fails_closed(self):
        memory.ensure_index(self.root)
        self.db.write_bytes(b"not a sqlite database")
        self.assertIn("unreadable_index", self.check()["findings"])


if __name__ == "__main__":
    unittest.main()
