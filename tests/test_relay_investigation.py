import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import odin_relay_client as client
from scripts import odin_relay_journal as journal


class InvestigationTests(unittest.TestCase):
    def test_disconnect_and_reconnect_deliver_one_execution(self):
        mid = "be" * 16
        msg = {"id": mid, "text": "test", "sender": "iphone", "to": "odin", "status": "queued"}
        answer = Mock(return_value="saved answer")
        sent = []
        def send(token, body):
            if body["type"] == "reply":
                sent.append(body.copy())
                if len(sent) < 3:
                    raise TimeoutError("injected transport timeout")
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(client, "STATE", state), patch.object(client, "request", send):
                self.assertFalse(client.handle_message("test", msg, set(), answer))
                journal.resend(state, "test", send)
                journal.resend(state, "test", send)
                self.assertTrue(client.handle_message("test", msg, set(), answer))
            answer.assert_called_once()
            self.assertEqual(len(sent), 3)
            self.assertTrue(all(payload == sent[0] for payload in sent))
            case, = journal.report(state)
            self.assertEqual((case["failure_count"], case["phase"]), (2, "publish_result"))
            self.assertEqual([x["attempt"] for x in case["recent_events"]], [2, 1])
            self.assertTrue(all(x["request_id"] == mid for x in case["recent_events"]))

    def test_unknown_outcome_creates_case_without_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            mid = "ab" * 16
            self.assertTrue(journal.claim(state, mid, "conversation"))
            send = Mock()
            journal.resend(state, "test", send)
            self.assertEqual(send.call_args.args[1]["state"], "failed")
            self.assertEqual(journal.report(state)[0]["reason"], "outcome_unknown")
            self.assertFalse(journal.claim(state, mid, "conversation"))
