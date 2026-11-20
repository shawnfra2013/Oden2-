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
