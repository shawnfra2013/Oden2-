"""Private offline source-receipt transfer contract and recovery regressions."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_github_bridge as bridge
from scripts import odin_receipt_sync as sync


def fixture(receipt_id="a" * 32, status="PASS"):
    names = sorted(sync.CHECK_NAMES)
    checks = [
        {"name": name, "status": "FAIL" if status == "FAIL" and i == 0 else "PASS",
         "exit_code": 1 if status == "FAIL" and i == 0 else 0, "duration_ms": 15}
        for i, name in enumerate(names)
    ]
    return {
        "schema": 1, "scope": "local_source_only", "id": receipt_id,
        "started_at": "2026-11-23T07:00:00+00:00",
        "completed_at": "2026-11-23T07:01:00+00:00",
        "source_sha": "b" * 40, "status": status, "checks": checks,
        "device_connection": "not_checked", "phone_connection": "not_checked",
    }


def encoded(data):
    return (json.dumps(data, sort_keys=True) + "\n").encode()


class SourceReceiptValidationTests(unittest.TestCase):
    def test_accept_passing_and_failing_offline_receipts(self):
        for status in ("PASS", "FAIL"):
            with self.subTest(status=status):
                report = fixture(status=status)
                self.assertEqual(sync.validate_bytes(encoded(report), report["id"])["status"], status)

    def test_reject_extra_fields_private_logs_and_fake_device_proof(self):
        for key, value in (
            ("shell_output", "token=example"),
            ("device_connection", "connected"),
            ("phone_connection", "connected"),
            ("source_sha", "not-a-sha"),
        ):
            with self.subTest(field=key):
                report = fixture()
                report[key] = value
                with self.assertRaises(ValueError):
                    sync.validate_bytes(encoded(report), report["id"])

    def test_reject_bad_ids_large_receipts_and_status_forgery(self):
        report = fixture()
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), "../evil")
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report) + b"x" * 4096, report["id"])
        report["status"] = "FAIL"
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), report["id"])

    def test_reject_missing_and_duplicate_checks(self):
        report = fixture()
        report["checks"][1]["name"] = report["checks"][0]["name"]
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), report["id"])
        report = fixture()
        report["checks"].pop()
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), report["id"])

    def test_reject_non_utc_and_backward_times(self):
        report = fixture()
        report["started_at"] = "2026-11-23T09:00:00+01:00"
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), report["id"])
        report = fixture()
        report["completed_at"] = "2026-11-22T06:00:00+00:00"
        with self.assertRaises(ValueError):
            sync.validate_bytes(encoded(report), report["id"])

    def test_symlink_is_not_queued(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            normal = root / ("a" * 32 + ".json")
            normal.write_bytes(encoded(fixture()))
            (root / ("c" * 32 + ".json")).symlink_to(normal)
            names = [path.name for path in sync.local_candidates(root)]
            self.assertEqual(names, [normal.name])


class PrivateReceiptBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.local = self.base / "local"
        self.local.mkdir()
        self.outbox = self.base / "outbox"
        self.outbox.mkdir()
        self.state = self.base / "state"
        self.state.mkdir()
        self.rec = fixture()
        self.content = encoded(self.rec)
        (self.local / (self.rec["id"] + ".json")).write_bytes(self.content)
        for cmd in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "odin-test@example.invalid"],
            ["git", "config", "user.name", "Odin Test"],
        ):
            subprocess.run(cmd, cwd=self.outbox, check=True, capture_output=True)
        (self.outbox / "seed.txt").write_text("seed\n")
        for cmd in (["git", "add", "seed.txt"], ["git", "commit", "-q", "-m", "seed"]):
            subprocess.run(cmd, cwd=self.outbox, check=True, capture_output=True)
        for obj, field, value in (
            (bridge, "STATE", self.state), (bridge, "OUTBOX", self.outbox),
            (bridge, "private_mailbox", True), (sync, "RECEIPT_DIR", self.local),
        ):
            patcher = patch.object(obj, field, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def target(self):
        return self.outbox / sync.remote_path(self.rec["id"])

    def test_first_push_and_second_poll_are_idempotent(self):
        with patch.object(bridge, "outbox_git", return_value="") as push:
            self.assertEqual(bridge.publish_local_source_receipts(), 1)
            self.assertEqual(bridge.publish_local_source_receipts(), 0)
            self.assertEqual(push.call_count, 1)
        self.assertEqual(self.target().read_bytes(), self.content)
        self.assertTrue((self.local / (self.rec["id"] + ".json")).exists())
        self.assertFalse((self.state / "pending-source-receipt.json").exists())
        self.assertEqual(json.loads((self.state / "source-receipt-last-push.json").read_text())["receipt_id"], self.rec["id"])

    def test_offline_push_retries_without_duplicate_commit(self):
        with patch.object(bridge, "outbox_git", side_effect=RuntimeError("network unavailable")):
            with self.assertRaises(RuntimeError):
                bridge.publish_local_source_receipts()
        self.assertTrue(self.target().is_file())
        self.assertFalse((self.state / "pending-source-receipt.json").exists())
        self.assertFalse((self.state / "source-receipt-last-push.json").exists())
        # The existing ensure_outbox checks for ahead commits and pushes after reconnection.
        count = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=self.outbox,
                               capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(count, "2")
        with patch.object(bridge, "outbox_git", return_value="") as push:
            self.assertEqual(bridge.publish_local_source_receipts(), 0)
            push.assert_not_called()
        self.assertTrue((self.local / (self.rec["id"] + ".json")).is_file())

    def test_recover_after_journal_written_before_commit(self):
        (self.state / "pending-source-receipt.json").write_bytes(self.content)
        bridge.recover_pending_source_receipt()
        self.assertEqual(self.target().read_bytes(), self.content)
        bridge.recover_pending_source_receipt()  # idempotent
        self.assertFalse((self.state / "pending-source-receipt.json").exists())

    def test_existing_conflicting_remote_id_fails_closed(self):
        self.target().parent.mkdir(parents=True)
        self.target().write_text("different")
        with self.assertRaises(RuntimeError):
            bridge.publish_local_source_receipts()
        self.assertEqual(self.target().read_text(), "different")
        self.assertTrue((self.local / (self.rec["id"] + ".json")).exists())


if __name__ == "__main__":
    unittest.main()
