"""Batch integration test: two private messages plus one bounded task."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_relay_client as relay


class ThreeMessageTests(unittest.TestCase):
    def test_multiple_messages_and_task_have_independent_receipts(self):
        messages = [
            {"id": "1" * 32, "sender": "iphone", "to": "odin",
             "status": "queued", "text": "/ping"},
            {"id": "2" * 32, "sender": "iphone", "to": "odin",
             "status": "queued", "text": "Explain the status"},
            {"id": "3" * 32, "sender": "iphone", "to": "odin",
             "status": "queued", "text": "/task git-status"},
        ]
        outbound = []

        def request(_token, data=None):
            if data is None:
                return {"source": "private-odin-relay", "messages": messages}
            outbound.append(data)
            return {"status": "accepted"}

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(relay, "STATE", Path(folder)),
            patch.object(relay, "LOCK_FILE", Path(folder) / "poll.lock"),
            patch.object(relay, "SEEN_FILE", Path(folder) / "processed.json"),
            patch.object(relay, "STATUS_FILE", Path(folder) / "relay-status.json"),
            patch.object(relay, "request", side_effect=request),
            patch.object(relay, "status_reply",
                         return_value="ODIN_TASK_COMPLETE verified=true task=git-status"),
        ):
            count = relay.poll_once(
                "not-a-secret", answer_fn=lambda question:
                "AI_MODEL_TEST_ANSWER: " + question
            )
            self.assertEqual(count, 3)
            receipt_counts = {mid: 0 for mid in ("1" * 32, "2" * 32, "3" * 32)}
            replies = {}
            for message in outbound:
                if message["type"] == "receipt":
                    receipt_counts[message["for"]] += 1
                elif message["type"] == "reply":
                    replies[message["for"]] = message["text"]
            self.assertEqual(list(receipt_counts.values()), [2, 2, 2])
            self.assertIn("ODIN_RELAY_PONG", replies["1" * 32])
            self.assertIn("AI_MODEL_TEST_ANSWER", replies["2" * 32])
            self.assertIn("ODIN_TASK_COMPLETE", replies["3" * 32])
            status = json.loads((Path(folder) / "relay-status.json").read_text())
            self.assertEqual(status["processed"], 3)
            self.assertEqual(status["failed"], 0)
            self.assertTrue(status["ok"])
            self.assertEqual(len(relay.load_seen()), 3)
            # No duplicate processing of the same messages on the next poll.
            self.assertEqual(relay.poll_once("not-a-secret"), 0)


if __name__ == "__main__":
    unittest.main()
