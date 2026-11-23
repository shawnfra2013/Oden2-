"""Safe, fixed Issue 71 private preview integration with no device/network use."""
import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import odin_github_bridge as bridge
from scripts import odin_mailbox_migrate as migrate
from scripts import odin_mailbox_audit as auditor


class MigrationPreviewBridgeTests(unittest.TestCase):
    ID = "9" * 32
    SHA = "a" * 40

    def request(self):
        now = datetime(2026, 11, 23, 15, 30, tzinfo=UTC)
        return {
            "version": 1, "id": self.ID, "action": "mailbox_migration_preview",
            "created_at": bridge.iso(now),
            "expires_at": bridge.iso(now + timedelta(minutes=15)),
            "expected_sha": self.SHA,
        }

    def test_private_only_exact_identity_scope(self):
        now = datetime(2026, 11, 23, 15, 30, tzinfo=UTC)
        req = self.request()
        self.assertIn("mailbox_migration_preview", bridge.PRIVATE_ACTIONS)
        self.assertNotIn("mailbox_migration_preview", bridge.ACTIONS)
        self.assertIn("mailbox_migration_preview", auditor.ACTIONS_SAFE)
        with patch.object(bridge, "private_mailbox", True):
            self.assertEqual(bridge.validate_request(json.dumps(req), self.ID, now=now), req)
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps({**req, "command": "pwd"}), self.ID, now=now)
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps({**req, "expected_sha": "main"}), self.ID, now=now)
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps(req), self.ID, now=now)

    def test_success_censors_private_paths_and_cannot_apply(self):
        plan = {"status": "READY", "sha": self.SHA, "pid": 123,
                "state": "/private/path", "source": "/tmp/pilot",
                "destination": "/private/destination"}
        with patch.object(bridge, "private_mailbox", True), \
             patch.dict("os.environ", {"PREFIX": "/fake/prefix"}), \
             patch.object(bridge, "git", return_value=self.SHA), \
             patch.object(migrate, "check", return_value=plan) as check:
            result = bridge.status_action("mailbox_migration_preview", self.request())
        check.assert_called_once_with(Path.home(), Path("/fake/prefix"), self.SHA)
        self.assertEqual(result["preflight_status"], "READY")
        self.assertTrue(result["migration_candidate"])
        self.assertFalse(result["device_change_performed"])
        self.assertNotIn("/private", json.dumps(result))
        self.assertNotIn("apply", json.dumps(result))

    def test_noncanonical_and_revision_mismatch_block(self):
        with patch.object(bridge, "private_mailbox", True), \
             patch.dict("os.environ", {"PREFIX": "/fake/prefix"}), \
             patch.object(bridge, "git", return_value="b" * 40), \
             patch.object(migrate, "check") as check:
            result = bridge.status_action("mailbox_migration_preview", self.request())
        self.assertEqual(result["reason"], "running_revision_mismatch")
        self.assertEqual(result["preflight_status"], "BLOCKED")
        check.assert_not_called()

    def test_blocked_local_state_returns_fixed_reason(self):
        with patch.object(bridge, "private_mailbox", True), \
             patch.dict("os.environ", {"PREFIX": "/fake/prefix"}), \
             patch.object(bridge, "git", return_value=self.SHA), \
             patch.object(migrate, "check", side_effect=migrate.MigrationBlocked(
                 "Canonical private state already exists; manual reconciliation required"
             )):
            result = bridge.status_action("mailbox_migration_preview", self.request())
        self.assertEqual(result["preflight_status"], "BLOCKED")
        self.assertEqual(result["reason"], "destination_collision")
        self.assertFalse(result["device_change_performed"])

    def test_no_private_context_rejected(self):
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.status_action("mailbox_migration_preview", self.request())


if __name__ == "__main__":
    unittest.main()
