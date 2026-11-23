"""Private-only bounded mailbox audit action; no command or secret forwarding."""
import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from scripts import odin_github_bridge as bridge
from scripts import odin_mailbox_audit as audit


class MailboxAuditBridgeTests(unittest.TestCase):
    ID = "8" * 32

    def setUp(self):
        self.now = datetime(2026, 11, 23, 7, 45, tzinfo=UTC)
        self.request = {
            "version": 1, "id": self.ID, "action": "mailbox_audit",
            "created_at": bridge.iso(self.now),
            "expires_at": bridge.iso(self.now + timedelta(minutes=15)),
        }
        self.result = {
            "schema": 1,
            "scope": "private_mailbox_metadata",
            "checked_at": "2026-11-23T07:45:01Z",
            "considered": 4,
            "counts": {"matched": 2, "stalled": 1, "pending": 1},
            "max_response_latency_s": 61,
            "incidents": [
                {"id": "a" * 32, "code": "stalled", "private_note": "never transmit"},
                {"id": "b" * 32, "code": "bogus", "message": "payload"},
                {"id": "c" * 32, "code": ["unsafe"]},
            ],
            "incidents_truncated": False,
        }

    def test_action_is_only_in_private_allowlist(self):
        self.assertIn("mailbox_audit", bridge.PRIVATE_ACTIONS)
        self.assertNotIn("mailbox_audit", bridge.ACTIONS)
        self.assertNotIn("shell", bridge.PRIVATE_ACTIONS)
        with patch.object(bridge, "private_mailbox", True):
            self.assertEqual(
                bridge.validate_request(json.dumps(self.request), self.ID, now=self.now)["action"],
                "mailbox_audit",
            )
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps(self.request), self.ID, now=self.now)

    def test_malformed_parameters_fail_closed(self):
        self.request["command"] = "rm -rf /"
        with patch.object(bridge, "private_mailbox", True):
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps(self.request), self.ID, now=self.now)

    def test_action_returns_bounded_private_metadata_only(self):
        with patch.object(bridge, "private_mailbox", True), \
                patch.object(audit, "inspect_local", return_value=self.result) as inspect, \
                patch.object(audit, "save_report") as save, \
                patch.object(bridge, "git", return_value="a" * 40) as git:
            result = bridge.status_action("mailbox_audit", self.request)
        inspect.assert_called_once_with(bridge.OUTBOX, hours=1)
        save.assert_called_once_with(self.result)
        git.assert_called_once_with("rev-parse", "HEAD")
        self.assertEqual(result["scope"], "private_mailbox_metadata")
        self.assertEqual(result["revision"], "a" * 40)
        self.assertEqual(result["incidents"], [{"id": "a" * 32, "code": "stalled"}])
        self.assertFalse(result["agent_read_verified"])
        self.assertFalse(result["device_phone_verified"])
        self.assertNotIn("never transmit", json.dumps(result))
        self.assertNotIn("payload", json.dumps(result))
        self.assertNotIn("private_note", json.dumps(result))

    def test_private_action_does_not_swallow_audit_error(self):
        with patch.object(bridge, "private_mailbox", True), \
                patch.object(audit, "inspect_local", side_effect=RuntimeError("missing clone")):
            with self.assertRaises(RuntimeError):
                bridge.status_action("mailbox_audit", self.request)

    def test_public_status_action_rejects_even_without_request(self):
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.status_action("mailbox_audit", None)


if __name__ == "__main__":
    unittest.main()
