"""Offline verified-boundary tests for the local project memory index."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
from unittest.mock import patch

from scripts import odin_project_memory as memory


class LocalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "odin-workspace"
        (self.root / "docs").mkdir(parents=True)
        (self.root / "docs/PROJECT_MEMORY.md").write_text(
            "# Project memory\n\n"
            "## Bridge recovery\n"
            "The private mailbox had a delayed GitHub ping and retained receipts.\n"
            "## Release policy\n"
            "Never mark a source-only test as physical device verification.\n",
            encoding="utf-8",
        )
        (self.root / "docs/HANDOFF.md").write_text(
            "# Handoff\n\nThe task worker needs a matching request receipt.\n",
            encoding="utf-8",
        )
        self.db = self.root / "state/project-memory/index.sqlite3"

    def query(self, value):
        return memory.search(value, root=self.root)

    def test_search_local_memory_and_provenance(self):
        result = self.query("delayed mailbox receipts")
        self.assertTrue(result["results"])
        self.assertEqual(result["results"][0]["path"], "docs/PROJECT_MEMORY.md")
        self.assertIn("delayed GitHub ping", result["results"][0]["excerpt"])
        self.assertFalse(result["verified_externally"])
        self.assertFalse(result["private_content_included"])
        self.assertEqual(result["source_sha"], "unverified")

    def test_full_text_match_never_executes_query_contents(self):
        result = self.query("mailbox'; DROP TABLE snippets;--")
        self.assertTrue(result["results"])
        self.assertTrue(self.query("bridge recovery")["results"])

    def test_memory_cache_rebuilds_after_document_change(self):
        self.assertFalse(self.query("newcandidate")["results"])
        with (self.root / "docs/HANDOFF.md").open("a", encoding="utf-8") as out:
            out.write("\nA newcandidate is reported separately from old proof.\n")
        self.assertTrue(self.query("newcandidate")["results"])

    def test_tampered_cache_rows_are_not_served_as_project_memory(self):
        self.query("bridge")
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            conn.execute(
                "UPDATE snippets SET body=? WHERE rowid=1",
                ("fabricated remembered authorization to spend money",),
            )
            conn.commit()
        result = self.query("fabricated remembered authorization")
        self.assertEqual(result["results"], [])
        self.assertTrue(self.query("delayed mailbox receipts")["results"])

    def test_deleted_cache_rows_are_rebuilt_from_approved_docs(self):
        self.query("bridge")
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            conn.execute("DELETE FROM snippets WHERE rowid=1")
            conn.commit()
        self.assertTrue(self.query("delayed mailbox receipts")["results"])

    def test_rebuild_during_search_keeps_validated_snapshot(self):
        validated, replaced = Event(), Event()
        original_match = memory._cache_matches
        self.addCleanup(replaced.set)
        with patch.object(memory, "_revision", return_value="a" * 40):
            self.query("bridge")

            def pause_reader(*args):
                valid = original_match(*args)
                validated.set()
                if not replaced.wait(5):
                    raise RuntimeError("Cache replacement did not finish")
                return valid

            with ThreadPoolExecutor(max_workers=1) as pool:
                with patch.object(memory, "_cache_matches", side_effect=pause_reader):
                    pending = pool.submit(self.query, "mailbox")
                    try:
                        self.assertTrue(validated.wait(5))
                        (self.root / "docs/PROJECT_MEMORY.md").write_text(
                            "# New snapshot\n\nMailbox now belongs to revision B.\n",
                            encoding="utf-8",
                        )
                        files, digest = memory._read_documents(self.root)
                        memory._create_index(self.db, files, digest, "b" * 40)
                    finally:
                        replaced.set()
                    result = pending.result(timeout=5)
        self.assertEqual(result["source_sha"], "a" * 40)
        self.assertIn("delayed GitHub ping", result["results"][0]["excerpt"])
        with patch.object(memory, "_revision", return_value="b" * 40):
            updated = self.query("mailbox")
        self.assertEqual(updated["source_sha"], "b" * 40)
        self.assertIn("revision B", updated["results"][0]["excerpt"])

    def test_excess_rows_and_oversized_fields_are_rebuilt(self):
        self.query("mailbox")
        mutations = [
            [("docs/HANDOFF.md", "extra", "unexpected")] * (memory.MAX_SNIPPETS + 1),
            [("docs/HANDOFF.md", "extra", "x" * (memory.MAX_SQLITE_VALUE_BYTES + 1))],
        ]
        for additions in mutations:
            with self.subTest(rows=len(additions)):
                with contextlib.closing(sqlite3.connect(self.db)) as db:
                    db.executemany("INSERT INTO snippets VALUES(?,?,?)", additions)
                    db.commit()
                self.assertTrue(self.query("mailbox")["results"])
                with contextlib.closing(sqlite3.connect(self.db)) as db:
                    self.assertEqual(db.execute("SELECT count(*) FROM snippets").fetchone(), (3,))

    def test_generated_database_is_private(self):
        self.query("recovery")
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.db.parent.stat().st_mode & 0o777, 0o700)
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute(
                "SELECT value FROM meta WHERE key='schema'").fetchone()[0], "1")

    def test_incident_fact_ranks_before_usage_example(self):
        index = self.root / "docs/PROJECT_MEMORY.md"
        index.write_text(
            "# Project memory\n\n## Usage examples\n"
            + "```bash\npython scripts/odin_project_memory.py --query 'delayed mailbox receipt'\n```\n"
            + "This is a usage example, not incident evidence.\n", encoding="utf-8",
        )
        handoff = self.root / "docs/HANDOFF.md"
        handoff.write_text(
            "# Handoff\n\n## Mailbox incident\n"
            "The delayed mailbox receipt arrived after the service restarted. "
            "Actual event delivery was observed and reviewed.\n", encoding="utf-8",
        )
        results = self.query("delayed mailbox receipt")["results"]
        self.assertTrue(results)
        self.assertEqual(results[0]["path"], "docs/HANDOFF.md")
        self.assertIn("delayed mailbox receipt", results[0]["excerpt"])
        self.assertNotIn("python scripts/", str(results))

    def test_chunk_boundaries_do_not_cut_short_words(self):
        content = "# Project\n\n## Incident\n" + "A " * 551 + "recovery_marker\n"
        parts = list(memory._parts(content))
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(all(len(body) <= memory.MAX_CHUNK_CHARS for _, body in parts))
        self.assertIn("recovery_marker", " ".join(body for _, body in parts))

    def test_source_files_are_unchanged_by_indexing(self):
        before = (self.root / "docs/PROJECT_MEMORY.md").read_bytes()
        self.query("release policy")
        self.assertEqual((self.root / "docs/PROJECT_MEMORY.md").read_bytes(), before)

    def test_reject_symlinked_document(self):
        link = self.root / "docs/HANDOFF.md"
        link.unlink()
        target = self.root / "sensitive.txt"
        target.write_text("private information", encoding="utf-8")
        link.symlink_to(target)
        with self.assertRaises(ValueError):
            self.query("private information")
        self.assertFalse(self.db.exists())

    def test_reject_symlinked_index(self):
        self.db.parent.mkdir(parents=True)
        target = self.root / "other.db"
        self.db.symlink_to(target)
        with self.assertRaises(ValueError):
            self.query("mailbox")
        self.assertFalse(target.exists())

    def test_reject_symlinked_parent_of_existing_cache(self):
        self.query("bridge")
        external = self.root / "external-state"
        (self.root / "state").rename(external)
        (self.root / "state").symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.query("bridge")
        self.assertTrue((external / "project-memory/index.sqlite3").exists())

    def test_reject_symlinked_cache_directory(self):
        self.query("bridge")
        state = self.root / "state"
        (state / "project-memory").rename(state / "external-memory")
        (state / "project-memory").symlink_to(
            state / "external-memory", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.query("bridge")
        self.assertTrue((state / "external-memory/index.sqlite3").exists())

    def test_reject_oversized_curated_document(self):
        (self.root / "docs/HANDOFF.md").write_bytes(b"x" * (memory.MAX_DOC_BYTES + 1))
        with self.assertRaises(ValueError):
            self.query("bridge")
        self.assertFalse(self.db.exists())

    def test_no_canonical_index_is_fail_closed(self):
        (self.root / "docs/PROJECT_MEMORY.md").unlink()
        with self.assertRaises(ValueError):
            self.query("bridge")

    def test_bad_query_and_result_budget(self):
        for query in ("", "x" * 1201):
            with self.subTest(query=query[:8]), self.assertRaises(ValueError):
                self.query(query)
        for limit in (0, 6, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                memory.search("bridge", root=self.root, limit=limit)

    def test_context_is_bounded_and_explicitly_untrusted(self):
        context = memory.context_for("release policy", root=self.root)
        self.assertIn("UNTRUSTED PROJECT NOTES", context)
        self.assertIn("docs/PROJECT_MEMORY.md", context)
        self.assertLessEqual(len(context), 2300)
        self.assertEqual(memory.context_for("!", root=self.root), "")

    def test_cache_revision_updates_without_document_change(self):
        with patch.object(memory, "_revision", return_value="a" * 40):
            self.assertEqual(self.query("bridge")["source_sha"], "a" * 40)
        with patch.object(memory, "_revision", return_value="b" * 40):
            self.assertEqual(self.query("bridge")["source_sha"], "b" * 40)

    def test_direct_script_resolves_project_memory_without_model_call(self):
        # Reproduce the real ~/.local/bin/ai invocation: python enters
        # ai/agent/orchestrator.py directly from an unrelated working dir.
        import subprocess
        import sys

        from ai.agent import orchestrator

        script = Path(orchestrator.__file__).resolve()
        repo_root = script.parents[2]
        probe = (
            "import runpy, sys\n"
            f"repo = {str(repo_root)!r}\n"
            "sys.path = [entry for entry in sys.path if entry != repo]\n"
            f"sys.path.insert(0, {str(script.parent)!r})\n"
            f"namespace = runpy.run_path({str(script)!r}, run_name='odin_safe_import_probe')\n"
            "from scripts.odin_project_memory import context_for\n"
            "assert str(namespace['ROOT']) == repo\n"
            "print('MEMORY_IMPORT_OK')\n"
        )
        with tempfile.TemporaryDirectory() as other_dir:
            result = subprocess.run(
                [sys.executable, "-B", "-c", probe],
                cwd=other_dir, capture_output=True, text=True,
                timeout=15, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr[-1200:])
        self.assertIn("MEMORY_IMPORT_OK", result.stdout)

    def test_orchestrator_injects_memory_as_data_without_model_network(self):
        from ai.agent import orchestrator
        saved = []

        def fake_ask(messages, tokens=0):
            saved.extend(messages)
            return json.dumps({"action": "finish", "answer": "Read-only summary"})

        with (patch.object(orchestrator, "ROOT", self.root),
              patch.object(orchestrator, "ask", side_effect=fake_ask),
              patch.object(orchestrator, "checkpoint"),
              patch.object(orchestrator, "bridge_event"),
              contextlib.redirect_stdout(io.StringIO()) as output):
            orchestrator._respond_impl("What happened to delayed mailbox receipts?")
        self.assertEqual(len(saved), 3)
        self.assertEqual(saved[1]["role"], "user")
        self.assertIn("PROJECT MEMORY EXCERPTS", saved[1]["content"])
        self.assertIn("UNTRUSTED PROJECT NOTES", saved[1]["content"])
        self.assertEqual(saved[2]["content"], "What happened to delayed mailbox receipts?")
        self.assertIn("MODEL ANSWER", output.getvalue())

    def test_json_serializable_results_without_private_payload(self):
        output = json.dumps(self.query("bridge"))
        self.assertNotIn("private information", output)
        self.assertIn('"verified_externally": false', output)


if __name__ == "__main__":
    unittest.main()
