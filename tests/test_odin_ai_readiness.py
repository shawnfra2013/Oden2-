"""Offline tests for safe AI readiness and friendly task routing."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_relay_client as client


class AiReadinessTests(unittest.TestCase):
    MID = "ab" * 16

    def message(self, text):
        return {"id": self.MID, "to": "odin", "sender": "iphone",
                "text": text, "status": "queued"}

    def exercise(self, text, response, status=None):
        calls = []

        def fake_request(_token, body=None):
            calls.append(body)
            return {"accepted": True}

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(client, "STATE", Path(folder)),
            patch.object(client, "SEEN_FILE", Path(folder) / "seen.json"),
            patch.object(client, "request", side_effect=fake_request),
            patch.object(client, "status_reply",
                         return_value="ODIN_TASK_COMPLETE verified=true task=git-status"),
        ):
            self.assertTrue(client.handle_message("device", self.message(text),
                                                  set(), response))
            self.assertEqual(calls[0]["state"], "delivered")
            self.assertEqual(calls[1]["state"], "read")
            if status is not None:
                self.assertEqual(calls[-1]["type"], "receipt")
                self.assertEqual(calls[-1]["state"], "failed")
                self.assertEqual(calls[-1]["reason"], status)
            return calls

    def test_normalize_exact_friendly_readonly_task_only(self):
        for cmd in ("Task git-status", "check git status",
                    "SHOW   GIT STATUS", "/task git-status"):
            self.assertEqual(client.normalized_action(cmd), "git_status")
            calls = self.exercise(cmd, lambda _: self.fail("No model expected"))
            self.assertIn("ODIN_TASK_COMPLETE", calls[-1]["text"])
        self.assertEqual(client.normalized_action("task git-status; rm *"),
                         "unsupported_command")
        self.assertIsNone(client.normalized_action("Can you explain Git?"))

    def test_status_reports_readiness_not_credentials(self):
        private = "secret-do-not-include-in-output"
        with patch.dict(os.environ, {
            "ODIN_STAGE5_ENABLE_AI": "1",
            "ODIN_STAGE5_PROVIDER": "groq",
            "GROQ_API_KEY": private,
        }, clear=True):
            status = client.local_ai_status()
            self.assertTrue(status["ready"])
            self.assertEqual(status["reason"], "configured_not_tested")
            reply = client.ai_status_reply()
            self.assertIn("provider=groq", reply)
            self.assertIn("ready=true", reply)
            self.assertNotIn(private, reply)

    def test_unconfigured_provider_is_diagnostic_only(self):
        with patch.dict(os.environ, {}, clear=True):
            reply = client.ai_status_reply()
            self.assertIn("enabled=false", reply)
            self.assertIn("reason=ai_disabled", reply)
            calls = self.exercise("/ai-status", lambda _: self.fail("No AI request"))
            self.assertIn("ODIN_AI_STATUS", calls[-1]["text"])

    def test_missing_key_is_safe_failed_receipt(self):
        with patch.object(client, "local_ai_status", return_value={
            "ready": False, "reason": "credential_missing",
        }):
            self.exercise("Hello Odin", lambda _: (_ for _ in ()).throw(
                RuntimeError("raw-provider-exception-must-never-leave-device")
            ), status="credential_missing")

    def test_timeout_reports_bounded_failure(self):
        with patch.object(client, "local_ai_status", return_value={
            "ready": True, "reason": "configured_not_tested",
        }):
            self.exercise("Hello Odin", lambda _: (_ for _ in ()).throw(
                TimeoutError("secret-provider-timeout-details")
            ), status="provider_timeout")

    def test_ai_test_invokes_model_only_by_explicit_request(self):
        observed = []
        calls = self.exercise("/ai-test", lambda text: observed.append(text) or "Ready")
        self.assertEqual(len(observed), 1)
        self.assertIn("ODIN_AI_TEST_RESPONSE", calls[-1]["text"])

    def test_unrecognized_task_never_executes_model(self):
        calls = self.exercise("/task delete private data",
                              lambda _: self.fail("Model should not execute task"))
        self.assertIn("ODIN_TASK_REJECTED", calls[-1]["text"])


if __name__ == "__main__":
    unittest.main()
