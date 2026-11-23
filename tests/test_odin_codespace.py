"""Local Codespaces runner safety and receipt tests (no internet/device access)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_codespace as dev


class CodespacesTests(unittest.TestCase):
    def test_status_does_not_claim_device_access(self):
        with patch.dict("os.environ", {"CODESPACES": "true"}):
            report = dev.status()
        self.assertEqual(report["scope"], "local_source_only")
        self.assertEqual(report["device_connection"], "not_checked")
        self.assertEqual(report["tailscale_connection"], "not_checked")

    def test_check_commands_have_no_shell_or_remote_actions(self):
        commands = dev.check_commands()
        self.assertEqual(len(commands), 7)
        for name, argv in commands:
            self.assertIsInstance(name, str)
            self.assertIsInstance(argv, list)
            self.assertNotIn("ssh", argv)
            self.assertNotIn("tailscale", argv)
            self.assertNotIn("rm", argv)
            self.assertNotIn("curl", argv)

    def test_receipts_are_private_and_do_not_contain_terminal_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = {
                "id": "a" * 32,
                "schema": 1,
                "checks": [{"name": "test", "status": "FAIL", "exit_code": 1}],
                "device_connection": "not_checked",
            }
            path = dev.save_receipt(receipt, Path(temp) / "state")
            self.assertEqual(json.loads(path.read_text()), receipt)
            self.assertFalse(path.read_text().count("stderr"))
            with self.assertRaises(FileExistsError):
                dev.save_receipt(receipt, Path(temp) / "state")

    def test_test_runner_fails_closed(self):
        with patch.object(dev, "check_commands", return_value=[("broken", ["missing-program"])]):
            with patch.object(dev, "execute_check", return_value={"name": "broken", "status": "FAIL", "exit_code": 127}):
                result = dev.run_tests()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["phone_connection"], "not_checked")

    def test_validation_rejects_invalid_receipt_id(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                dev.save_receipt({"id": "../outside"}, Path(temp))


if __name__ == "__main__":
    unittest.main()
