"""Offline tests for Odin private message client; no keys or network."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_relay_client as client


class OdinRelayTests(unittest.TestCase):
    ID = "0123456789abcdef0123456789abcdef"

    def message(self, status="queued"):
        return {
            "id": self.ID,
            "to": "odin",
            "sender": "iphone",
            "text": "Hi Odin",
            "status": status,
        }

    def test_sends_delivery_read_and_reply_receipts(self):
        calls = []

        def fake_request(_token, body=None):
            calls.append(body)
            return {"accepted": True}

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(client, "STATE", Path(folder)),
            patch.object(client, "SEEN_FILE", Path(folder) / "seen.json"),
            patch.object(client, "request", side_effect=fake_request),
        ):
                seen = set()
                success = client.handle_message(
                    "not-a-real-token", self.message(), seen, lambda _: "Hi phone"
                )
                self.assertTrue(success)
                self.assertIn(self.ID, seen)
                self.assertEqual([x["state"] for x in calls[:2]], ["delivered", "read"])
                self.assertEqual(calls[2]["type"], "reply")
                self.assertEqual(calls[2]["text"], "Hi phone")
                self.assertIn(self.ID, client.load_seen())

    def test_transport_ping_proves_device_reply_without_ai_model(self):
        calls = []

        def fake_request(_token, body=None):
            calls.append(body)
            return {"accepted": True}

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(client, "STATE", Path(folder)),
            patch.object(client, "SEEN_FILE", Path(folder) / "seen.json"),
            patch.object(client, "request", side_effect=fake_request),
        ):
            message = {**self.message(), "text": "/ping"}
            seen = set()
            self.assertTrue(client.handle_message(
                "not-a-real-token", message, seen,
                lambda _: self.fail("Model must never run for /ping"),
            ))
            self.assertEqual(calls[-1]["type"], "reply")
            self.assertIn("ODIN_RELAY_PONG", calls[-1]["text"])
            self.assertIn(self.ID, seen)

    def test_does_not_repeat_processed_message(self):
        with patch.object(client, "request", side_effect=AssertionError):
            self.assertFalse(
                client.handle_message("token", self.message(), {self.ID}, lambda _: "")
            )

    def test_rejects_untrusted_and_invalid_messages(self):
        with patch.object(client, "request", side_effect=AssertionError):
            for msg in (
                {**self.message(), "to": "public"},
                {**self.message(), "text": ""},
                {**self.message(), "id": "../secret"},
            ):
                self.assertFalse(client.handle_message("token", msg, set(), lambda _: ""))

    def test_model_error_reports_failed_without_commands(self):
        calls = []

        def fake_request(_, body=None):
            calls.append(body)
            return {}

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(client, "STATE", Path(folder)),
            patch.object(client, "SEEN_FILE", Path(folder) / "seen.json"),
            patch.object(client, "request", side_effect=fake_request),
        ):
                seen = set()
                def bad_model(_):
                    raise RuntimeError("Model is not configured")
                self.assertTrue(
                    client.handle_message("token", self.message(), seen, bad_model)
                )
                self.assertEqual(calls[-1]["state"], "failed")
                self.assertIn(self.ID, seen)


if __name__ == "__main__":
    unittest.main()
