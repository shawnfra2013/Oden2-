import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import odin_relay_client as client
from scripts import odin_relay_journal as journal


class DisconnectHoldTests(unittest.TestCase):
    def test_only_dedicated_ping_defers_delivery_across_restart(self):
        mid = "01" * 16
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            self.assertEqual(client.normalized_action("/ping-disconnect-test"), "disconnect_test")
            journal.claim(state, mid, "disconnect_test")
            body = {"type": "reply", "for": mid, "text": "PONG"}
            with patch.object(journal.time, "time", return_value=100):
                journal.save_result(state, mid, body)
                send = Mock()
                journal.resend(state, "token", send)
                send.assert_not_called()
            with patch.object(journal.time, "time", return_value=191):
                send.side_effect = TimeoutError()
                journal.resend(state, "token", send)
                send.side_effect = None
                journal.resend(state, "token", send)
                journal.resend(state, "token", send)
                self.assertEqual(send.call_count, 2)
                self.assertEqual(send.call_args.args[1], body)
