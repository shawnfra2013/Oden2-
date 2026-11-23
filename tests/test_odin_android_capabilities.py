"""Offline Android capability inventory tests; no subprocesses or Android access."""
import unittest

from scripts import odin_android_capabilities as android


class AndroidInventoryTests(unittest.TestCase):
    def test_no_tool_presence_implies_android_authorization(self):
        calls = []
        def found(name):
            calls.append(name)
            return "/mock/bin/" + name
        report = android.inventory(which=found, environ={"ANDROID_ROOT": "/system"})
        self.assertEqual(report["android_environment"], "POSSIBLE")
        self.assertEqual(report["device_verification"], "UNVERIFIED")
        self.assertEqual(len(calls), len(android.COMMANDS))
        for item in report["capabilities"]:
            self.assertEqual(item["operational"], "UNVERIFIED")
        self.assertEqual(report["capabilities"][0]["binary"], "DETECTED")

    def test_missing_tools_not_falsely_verified(self):
        report = android.inventory(which=lambda name: None, environ={})
        self.assertEqual(report["android_environment"], "UNVERIFIED")
        for item in report["capabilities"]:
            self.assertEqual(item["operational"], "UNVERIFIED")
        self.assertEqual(report["capabilities"][0]["binary"], "NOT_DETECTED")

    def test_failed_path_detection_does_not_silently_pass(self):
        def raise_error(_name):
            raise OSError("unavailable")
        report = android.inventory(which=raise_error, environ={})
        self.assertEqual(report["capabilities"][0]["binary"], "UNVERIFIED")

    def test_every_capability_has_distinct_id_and_permission_class(self):
        report = android.inventory(which=lambda name: None, environ={})
        ids = [item["id"] for item in report["capabilities"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item["permission_class"] for item in report["capabilities"]))
        self.assertIn("accessibility", ids)
        self.assertIn("secure_ipc", ids)
        self.assertIn("physical_buttons", ids)


if __name__ == "__main__":
    unittest.main()
