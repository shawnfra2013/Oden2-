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

    def test_pending_result_is_attempted_once_per_poll_with_stale_inbox(self):
        mid = "dc" * 16
        msg = {"id": mid, "text": "test", "sender": "iphone", "to": "odin", "status": "read"}
        body = {"type": "reply", "for": mid, "text": "saved answer"}
        answer = Mock()
        send = Mock()

        def endpoint(token, payload=None):
            if payload is None:
                return {"source": "private-odin-relay", "messages": [msg]}
            if payload["type"] == "reply":
                return send(token, payload)
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            journal.claim(state, mid, "conversation")
            journal.save_result(state, mid, body)
            send.side_effect = TimeoutError()
            with (patch.object(client, "STATE", state),
                  patch.object(client, "LOCK_FILE", state / "poll.lock"),
                  patch.object(client, "STATUS_FILE", state / "relay-status.json"),
                  patch.object(client, "SEEN_FILE", state / "processed.json"),
                  patch.object(client, "request", endpoint),
                  patch.object(client.service_restart, "publish_pending")):
                client.poll_once("test", answer)
                send.assert_called_once_with("test", body)
                self.assertEqual(journal.report(state), [])
                client.poll_once("test", answer)
                self.assertEqual(send.call_count, 2)
                self.assertEqual(journal.report(state)[0]["failure_count"], 2)
                send.side_effect = None
                client.poll_once("test", answer)
                self.assertEqual(send.call_count, 3)
                answer.assert_not_called()
