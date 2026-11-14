"""Offline regression tests for inference provenance."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai/agent"))
import inference_receipt
import orchestrator


class InferenceReceiptTests(unittest.TestCase):

    def test_direct_entrypoint_order(self):
        from pathlib import Path
        source = Path(__file__).resolve().parents[1] / "ai/agent/orchestrator.py"
        text = source.read_text()
        wrapper = text.index("def respond(question, task_id=None):")
        entry = text.index('if __name__ == "__main__":')
        self.assertLess(wrapper, entry)

    def test_capture_and_isolation(self):
        token = inference_receipt.begin()
        try:
            inference_receipt.record(
                {"id": "test-123", "model": "model-a",
                 "usage": {"total_tokens": 42}},
                "model-a",
            )
            saved = inference_receipt.receipts()
            self.assertEqual(saved[0]["response_id"], "test-123")
            self.assertEqual(saved[0]["usage"]["total_tokens"], 42)
            self.assertFalse(saved[0]["independently_verified"])
        finally:
            inference_receipt.finish(token)
        self.assertEqual(inference_receipt.receipts(), [])

    def test_malformed_metadata_and_restore(self):
        token = inference_receipt.begin()
        try:
            inference_receipt.record(
                {"id": None, "usage": "invalid"}, "model-a"
            )
            self.assertIsNone(inference_receipt.receipts()[0]["response_id"])
            self.assertEqual(inference_receipt.receipts()[0]["usage"], {})
            saved = inference_receipt.receipts()
            inference_receipt.restore(saved)
            self.assertEqual(len(inference_receipt.receipts()), 2)
        finally:
            inference_receipt.finish(token)

    def test_checkpoint_persistence(self):
        task_id = "abcdef123456"

        def fake_ask(messages, tokens=1400):
            inference_receipt.record(
                {"id": "offline-001", "model": "model-a",
                 "usage": {"total_tokens": 28}},
                orchestrator.MODEL,
            )
            return json.dumps({
                "action": "finish", "answer": "Offline test complete"
            })

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(orchestrator, "ROOT", root), \
                 patch.object(orchestrator, "ask", side_effect=fake_ask), \
                 patch.object(orchestrator, "bridge_event"):
                orchestrator.respond("Offline test", task_id=task_id)

            path = root / "state/task-sessions" / f"{task_id}.json"
            saved = json.loads(path.read_text())
            self.assertEqual(saved["status"], "unverified")
            self.assertEqual(
                saved["inference"][0]["response_id"], "offline-001"
            )
            self.assertFalse(
                saved["inference"][0]["independently_verified"]
            )
        self.assertEqual(inference_receipt.receipts(), [])


    def test_interactive_resume_preserves_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "state/odin-agent-session.json"
            session.parent.mkdir(parents=True)
            session.write_text(json.dumps({
                "schema": 1,
                "task_id": None,
                "step": 1,
                "status": "running",
                "messages": [
                    {"role": "system", "content": orchestrator.SYSTEM},
                    {"role": "user", "content": "Offline resume test"},
                ],
                "execution": [],
                "inference": [{
                    "provider": "groq",
                    "requested_model": orchestrator.MODEL,
                    "response_model": orchestrator.MODEL,
                    "response_id": "previous-001",
                    "usage": {"total_tokens": 20},
                }],
            }))

            def fake_ask(messages, tokens=1400):
                inference_receipt.record({
                    "id": "new-002",
                    "model": orchestrator.MODEL,
                    "usage": {"total_tokens": 15},
                }, orchestrator.MODEL)
                return json.dumps({
                    "action": "finish",
                    "answer": "Resume test complete",
                })

            with patch.object(orchestrator, "ROOT", root), \
                 patch.object(orchestrator, "ask", side_effect=fake_ask), \
                 patch.object(orchestrator, "bridge_event"):
                orchestrator.respond("resume")

            saved = json.loads(session.read_text())
            ids = [item["response_id"] for item in saved["inference"]]
            self.assertEqual(ids, ["previous-001", "new-002"])
            self.assertEqual(saved["status"], "unverified")

        self.assertEqual(inference_receipt.receipts(), [])


if __name__ == "__main__":
    unittest.main()
