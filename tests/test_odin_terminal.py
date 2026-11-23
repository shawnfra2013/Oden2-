"""Read-only Odin terminal regression tests; no device or network calls."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_terminal as term


class TerminalTests(unittest.TestCase):
    def test_missing_device_not_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(term, "command", return_value=None):
                output = term.local(root=Path(tmp), prefix="")
        self.assertEqual(output["mailbox_cwd"], "UNVERIFIED")
        self.assertEqual(output["services"]["odin-private-mailbox"]["state"], "UNVERIFIED")
        self.assertEqual(output["services"]["odin-local-model"]["state"], "UNVERIFIED")
        self.assertEqual(output["services"]["odin-stage5"]["state"], "UNVERIFIED")
        self.assertIsNone(output["queue"]["pending"])

    def test_source_checks_must_match_main(self):
        sha = "a" * 40
        def get(path):
            if path == "/branches/main":
                return {"commit": {"sha": sha}}
            if path.startswith("/actions/runs"):
                return {"workflow_runs": [
                    {"name": name, "head_sha": sha, "status": "completed", "conclusion": "success"}
                    for name in ("Odin Checks", "Offline chat browser acceptance",
                                 "Odin CodeQL Security Scan")]}
            return []
        self.assertEqual(term.github(get)["ci"], "PASS")

    def test_other_sha_not_verified(self):
        def get(path):
            if path == "/branches/main":
                return {"commit": {"sha": "a" * 40}}
            if path.startswith("/actions/runs"):
                return {"workflow_runs": [
                    {"name": "Odin Checks", "head_sha": "b" * 40, "status": "completed",
                     "conclusion": "success"}]}
            return []
        self.assertEqual(term.github(get)["ci"], "UNVERIFIED")

    def test_remote_failure_unknown(self):
        self.assertEqual(term.github(lambda _path: None)["ci"], "UNVERIFIED")

    def test_escape_removed(self):
        self.assertNotIn("\x1b", term.safe("\x1b[31msecret\x1b[0m"))

    def test_render_no_escape_and_cwd_failure(self):
        data = {"checked_utc": "2026-11-23T15:00:00Z", "local_sha": "a" * 40,
                "mailbox_cwd": "FAIL", "services": {}, "queue": {}}
        result = term.render(data, width=68)
        self.assertIn("FAIL", result)
        self.assertNotIn("\x1b", result)
        self.assertTrue(all(len(x) <= 68 for x in result.splitlines()))

    def test_offline_json_does_not_access_network(self):
        with patch.dict(os.environ, {"PREFIX": ""}):
            with patch.object(term, "github", side_effect=AssertionError("network")):
                with patch.object(term, "command", return_value=None):
                    stream = io.StringIO()
                    with patch("sys.stdout", stream):
                        self.assertEqual(term.main(["--offline", "--json"]), 0)
        self.assertIsNone(json.loads(stream.getvalue())["github"])

    def test_source_no_shell_or_credentials(self):
        raw = Path(term.__file__).read_text()
        for word in ("shell=True", "ODIN_PRIVATE_MAILBOX_TOKEN", "sk-proj",
                     "api.openai.com"):
            self.assertNotIn(word, raw)


if __name__ == "__main__":
    unittest.main()
