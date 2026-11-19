"""Offline validation tests for the GitHub-backed Odin bridge."""
import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from scripts import odin_github_bridge as bridge


class BridgeRequestTests(unittest.TestCase):
    ID = "0123456789abcdef0123456789abcdef"

    def setUp(self):
        self.now = datetime(2026, 11, 18, 22, 0, tzinfo=UTC)
        self.request = {
            "version": 1,
            "id": self.ID,
            "action": "ping",
            "created_at": bridge.iso(self.now - timedelta(minutes=1)),
            "expires_at": bridge.iso(self.now + timedelta(minutes=29)),
        }

    def decode(self):
        return bridge.validate_request(
            json.dumps(self.request), self.ID, now=self.now
        )

    def test_accept_valid_ping(self):
        self.assertEqual(self.decode()["action"], "ping")

    def test_accept_only_declared_read_only_actions(self):
        for action in bridge.ACTIONS:
            with self.subTest(action=action):
                self.request["action"] = action
                self.assertEqual(self.decode()["action"], action)

    def test_reject_arbitrary_shell_command(self):
        self.request["action"] = "sh -c 'id'"
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_extra_payload_field(self):
        self.request["command"] = "echo hidden"
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_id_mismatch(self):
        self.request["id"] = "f" * 32
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_expired_request(self):
        self.request["expires_at"] = bridge.iso(self.now - timedelta(seconds=1))
        with self.assertRaises(bridge.ExpiredRequest):
            self.decode()

    def test_reject_expiry_over_one_hour(self):
        self.request["expires_at"] = bridge.iso(self.now + timedelta(hours=2))
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_future_created_at(self):
        self.request["created_at"] = bridge.iso(self.now + timedelta(minutes=6))
        self.request["expires_at"] = bridge.iso(self.now + timedelta(minutes=30))
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_oversized_request(self):
        with self.assertRaises(ValueError):
            bridge.validate_request("x" * 4097, self.ID, now=self.now)

    def test_reject_invalid_id_filename(self):
        with self.assertRaises(ValueError):
            bridge.validate_request(json.dumps(self.request), "../evil", now=self.now)

    def test_invalid_json_rejected(self):
        with self.assertRaises(ValueError):
            bridge.validate_request("{", self.ID, now=self.now)

    def test_ping_has_no_remote_or_shell_side_effects(self):
        with patch.object(bridge, "run", side_effect=AssertionError("run")):
            self.assertEqual(
                bridge.status_action("ping"),
                {"alive": True, "bridge_version": 1},
            )

    def test_reject_unknown_operation(self):
        with self.assertRaises(ValueError):
            bridge.status_action("exec")


if __name__ == "__main__":
    unittest.main()
