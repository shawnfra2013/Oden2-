"""OpenAI backend tests use mocks only; no live requests or credentials."""
import io
import json
import os
import unittest
from unittest.mock import patch

import chat_provider
import openai_adapter


class OpenAIAdapterTests(unittest.TestCase):
    SETTINGS = {
        "ODIN_STAGE5_ENABLE_AI": "1",
        "ODIN_STAGE5_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-only-value",
        "ODIN_OPENAI_MODEL": "test-model",
    }

    def fake_response(self, message="ODIN_OK"):
        data = {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": message}],
            }],
        }
        return io.BytesIO(json.dumps(data).encode("utf-8"))

    def test_openai_request_uses_no_server_storage(self):
        def fake_urlopen(request, timeout):
            self.assertEqual(timeout, 40)
            self.assertEqual(request.full_url, openai_adapter.ENDPOINT)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-only-value")
            payload = json.loads(request.data)
            self.assertFalse(payload["store"])
            self.assertEqual(payload["max_output_tokens"], 700)
            self.assertEqual(payload["input"][-1], {"role": "user", "content": "Hello"})
            return self.fake_response()

        with patch.dict(os.environ, self.SETTINGS):
            with patch.object(openai_adapter, "urlopen", side_effect=fake_urlopen):
                self.assertEqual(openai_adapter.ask_openai("Hello"), "ODIN_OK")

    def test_chat_provider_uses_openai_option(self):
        with patch.dict(os.environ, self.SETTINGS):
            with patch.object(chat_provider, "ask_openai", create=True):
                with patch("openai_adapter.ask_openai", return_value="HI") as fn:
                    self.assertEqual(chat_provider.ask_model("hi"), "HI")
                    fn.assert_called_once_with("hi", None)

    def test_groq_stays_default(self):
        with patch.dict(os.environ, {"ODIN_STAGE5_PROVIDER": "groq"}):
            with patch.object(chat_provider, "ask_bounded", return_value="GROQ") as fn:
                self.assertEqual(chat_provider.ask_model("hello"), "GROQ")
                fn.assert_called_once_with("hello", None)

    def test_reject_missing_key_without_request(self):
        env = dict(self.SETTINGS)
        env["OPENAI_API_KEY"] = ""
        with patch.dict(os.environ, env):
            with patch.object(openai_adapter, "urlopen", side_effect=AssertionError):
                with self.assertRaises(RuntimeError):
                    openai_adapter.ask_openai("Hello")

    def test_reject_bad_model(self):
        env = dict(self.SETTINGS)
        env["ODIN_OPENAI_MODEL"] = ""
        with patch.dict(os.environ, env):
            with self.assertRaises(RuntimeError):
                openai_adapter.ask_openai("Hello")

    def test_reject_malformed_response(self):
        with patch.dict(os.environ, self.SETTINGS):
            with patch.object(openai_adapter, "urlopen", return_value=io.BytesIO(b"{}")):
                with self.assertRaises(ValueError):
                    openai_adapter.ask_openai("Hello")

    def test_preserves_bounded_history(self):
        history = [
            {"role": "user", "content": "Previous"},
            {"role": "assistant", "content": "Answer"},
        ]

        def fake_urlopen(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(len(payload["input"]), 3)
            self.assertEqual(payload["input"][0]["content"], "Previous")
            return self.fake_response("next")

        with patch.dict(os.environ, self.SETTINGS):
            with patch.object(openai_adapter, "urlopen", side_effect=fake_urlopen):
                self.assertEqual(openai_adapter.ask_openai("Next", history), "next")


if __name__ == "__main__":
    unittest.main()
