import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.odin_practice import CASES, notebook, practice


class PracticeTests(unittest.TestCase):
    def test_journal_replay_limit_and_training_signal(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "notes"
            assess = Mock(return_value={"http_status": 200, "match": False, "answer":"wrong"})
            first = practice("first", path=path, assess=assess)
            self.assertEqual(practice("first", path=path, assess=assess), first)
            for i in range(1, len(CASES)):
                row = practice(str(i), path=path, assess=assess)
            self.assertEqual(row["review_skills"], ["files", "python", "workflow"])
            self.assertEqual(practice("end", path=path, assess=assess)["state"], "finished")
            self.assertEqual(assess.call_count, len(CASES))
            self.assertEqual(len(notebook(path)["notes"]), len(CASES))

    def test_unavailable_does_not_score_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            row = practice("test", path=Path(temporary) / "notes", assess=Mock(side_effect=OSError))
            self.assertEqual(row["missed"], 0)
            self.assertEqual(row["training_decision"], "keep_current_weights")

    def test_followup_has_own_limit_and_preserves_baseline(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary, patch("pathlib.Path.home", return_value=Path(temporary)):
            def assess(_, *, exercise):
                return {"http_status": 200, "match": True, "answer": exercise[2]}
            practice("original", assess=assess)
            for i in range(4):
                result = practice(str(i), assess=assess, followup=True)
                self.assertEqual(result["total"], 4)
            self.assertEqual(practice("end", followup=True)["state"], "finished")
            self.assertEqual(notebook()["attempted"], 1)
            self.assertEqual(notebook(followup=True)["passed"], 4)

    def test_review_recognizes_workflow_word_but_preserves_file_case_and_raw_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "notes"
            def assess(_, *, exercise):
                return {"http_status": 200, "match": False, "answer": exercise[2].upper()}
            for i in range(3):
                practice(str(i), path=path, assess=assess)
            book = notebook(path)
            self.assertEqual(book["exact_passed"], 0)
            self.assertEqual(book["passed"], 1)
            self.assertEqual(book["notes"][1]["reviewed_state"], "miss")
            self.assertEqual(book["notes"][2]["state"], "miss")
            self.assertEqual(book["notes"][2]["reviewed_state"], "pass")
