import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_github_bridge as bridge
from scripts import odin_inference_probe as inference
from stage5 import openai_adapter


class PrivateInferenceTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(inference, "CONFIG", root))
        self.key = root / "key"
        self.key.write_text("fixture-value")
        self.key.chmod(0o600)
        self.identifier = "ab" * 16

    def test_private_fixed_request_and_durable_replay(self):
        def respond(request, timeout):
            payload = json.loads(request.data)
            self.assertFalse(payload["store"])
            self.assertEqual(payload["max_output_tokens"], 96)
            self.assertIn(self.identifier, payload["input"][0]["content"])
            body = {"id": "resp_fixture", "model": inference.MODEL, "status": "completed",
                    "output": [{"type": "message", "content": [{"type": "output_text",
                                "text": f"ODIN-{self.identifier}-63"}]}]}
            return io.BytesIO(json.dumps(body).encode())
        with patch.object(openai_adapter, "urlopen", side_effect=respond) as call:
            with self.assertRaises(ValueError):
                bridge.status_action("inference_probe", {"id": self.identifier})
            with patch.object(bridge, "private_mailbox", True):
                result = bridge.status_action("inference_probe", {"id": self.identifier})
                self.assertTrue(result["match"])
                self.assertEqual(result["response_id"], "resp_fixture")
                self.assertEqual(inference.probe(self.identifier), result)
                call.assert_called_once()

    def test_opt_in_and_failure_budget(self):
        with patch.object(inference, "request_answer", side_effect=ValueError) as call:
            self.key.chmod(0o644)
            self.assertEqual(inference.probe(self.identifier)["reason"], "local_opt_in_required")
            self.key.chmod(0o600)
            for n in (1, 2):
                self.assertEqual(inference.probe(f"{n:032x}")["reason"], "provider_request_failed")
            self.assertEqual(inference.probe(self.identifier)["reason"], "daily_limit")
            self.assertEqual(call.call_count, 2)

    def test_interrupted_attempt_is_never_resubmitted(self):
        with patch.object(inference, "request_answer", side_effect=KeyboardInterrupt) as call:
            with self.assertRaises(KeyboardInterrupt):
                inference.probe(self.identifier)
            self.assertEqual(inference.probe(self.identifier)["reason"], "prior_attempt_outcome_unknown")
            call.assert_called_once()
