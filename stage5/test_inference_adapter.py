import os
import sys
import unittest
from unittest.mock import patch

import inference_adapter as adapter


class AdapterTests(unittest.TestCase):
    def test_success(self):
        command = [
            sys.executable, "-c",
            'import json; print(json.dumps({"answer":"MOCK_OK"}))',
        ]
        self.assertEqual(
            adapter.run_bounded(command, {"question": "test"}),
            "MOCK_OK",
        )

    def test_deadline(self):
        command = [
            sys.executable, "-c",
            "import time; time.sleep(5)",
        ]
        with self.assertRaises(TimeoutError):
            adapter.run_bounded(command, {}, deadline=0.2)

    def test_invalid_response(self):
        command = [
            sys.executable, "-c",
            'print("not JSON")',
        ]
        with self.assertRaises(ValueError):
            adapter.run_bounded(command, {})

    def test_failed_process(self):
        command = [
            sys.executable, "-c",
            "import sys; sys.exit(2)",
        ]
        with self.assertRaises(RuntimeError):
            adapter.run_bounded(command, {})

    def test_disabled(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaises(RuntimeError),
        ):
            adapter.ask_bounded("test")


if __name__ == "__main__":
    unittest.main()
