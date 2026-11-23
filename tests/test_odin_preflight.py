"""Preflight safety contract: fail closed; no model, browser, or external call."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_preflight as preflight


class PreflightTests(unittest.TestCase):
    def test_current_source_checks_pass_without_live_device_claims(self):
        checks = preflight.static_checks()
        self.assertTrue(checks)
        self.assertFalse([x for x in checks if x["status"] == "FAIL"])
        report = preflight.build_report("source")
        self.assertEqual(report["release_approved"], False)
        self.assertEqual(report["status"], "UNVERIFIED")
        self.assertIn("iphone_cellular", [x["check"] for x in report["checks"]])

    def test_missing_or_invalid_git_revision_not_silently_passed(self):
        def missing(_args):
            return None
        self.assertEqual(preflight.repo_revision(runner=missing)["status"], "UNVERIFIED")

        def broken(_args):
            return subprocess.CompletedProcess([], 0, stdout="garbage\n")
        self.assertEqual(preflight.repo_revision(runner=broken)["status"], "FAIL")

    def test_missing_required_runit_service_blocks_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = preflight.service_status("odin-private-mailbox", prefix=Path(tmp))
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(result["required"])
            optional = preflight.service_status("odin-stage5", prefix=Path(tmp))
            self.assertEqual(optional["status"], "UNVERIFIED")

    def test_running_service_requires_valid_supervisor_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "var/service/odin-private-mailbox").mkdir(parents=True)
            def runner(_cmd, timeout=5):
                return subprocess.CompletedProcess([], 0,
                    stdout="run: /tmp/service/odin-private-mailbox: (pid 31415) 5s\n")
            with patch.object(preflight.shutil, "which", return_value="/bin/sv"):
                state = preflight.service_status("odin-private-mailbox",
                                                 prefix=root, runner=runner)
            self.assertEqual(state["status"], "PASS")
            def uncertain(_cmd, timeout=5):
                return subprocess.CompletedProcess([], 0, stdout="unexpected state\n")
            with patch.object(preflight.shutil, "which", return_value="/bin/sv"):
                state = preflight.service_status("odin-private-mailbox",
                                                 prefix=root, runner=uncertain)
            self.assertEqual(state["status"], "UNVERIFIED")

    def test_offline_model_tcp_never_issues_chat_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(preflight.local_model_status(home)["status"], "UNVERIFIED")
            marker = home / ".config/odin-offline/enabled"
            marker.parent.mkdir(parents=True)
            marker.touch()
            class Connection:
                def close(self):
                    pass
            def connector(address, timeout):
                self.assertEqual(address, ("127.0.0.1", 18080))
                self.assertEqual(timeout, 3)
                return Connection()
            self.assertEqual(preflight.local_model_status(home, connector)["status"],
                             "PASS")
            def unavailable(_address, _timeout):
                raise ConnectionRefusedError()
            self.assertEqual(preflight.local_model_status(home, unavailable)["status"],
                             "FAIL")

    def test_read_only_health_does_not_claim_inference(self):
        class Reply:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, _length):
                return b'{"status":"ready","ai_configured":true}'
        def opener(url, timeout):
            self.assertEqual(url, "http://127.0.0.1:8765/api/health")
            self.assertEqual(timeout, 3)
            return Reply()
        result = preflight.workstation_status(opener)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("inference not tested", result["detail"])

    def test_live_network_without_evidence_never_promotes_to_pass(self):
        with patch.object(preflight.shutil, "which", return_value=None):
            result = preflight.private_network_status()
        self.assertEqual(result["status"], "UNVERIFIED")

    def test_invalid_status_not_silenced(self):
        with self.assertRaises(ValueError):
            preflight.record("test", "ignored", "broken")

    def test_json_schema_public_and_no_secret_collection(self):
        report = preflight.build_report("source")
        data = json.dumps(report)
        self.assertIn('"release_approved": false', data)
        self.assertNotIn("ODIN_PRIVATE_MAILBOX_TOKEN", data)
        self.assertNotIn("GROQ_API_KEY", data)


if __name__ == "__main__":
    unittest.main()
