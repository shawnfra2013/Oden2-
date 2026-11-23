import http.client
import json
import threading
import unittest
from http.server import HTTPServer

import server


class Stage55Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http = HTTPServer(("127.0.0.1", 0), server.Handler)
        cls.http.session_token = "offline-test-token"
        cls.http.chat_lock = threading.BoundedSemaphore(1)
        cls.thread = threading.Thread(
            target=cls.http.serve_forever, daemon=True
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        port = self.http.server_port
        connection = http.client.HTTPConnection(
            "127.0.0.1", port, timeout=5
        )
        values = {
            "Host": "127.0.0.1:8765",
            "Cookie": "odin_session=offline-test-token"
        }
        if headers:
            values.update(headers)
        connection.request(
            method, path, body=body, headers=values
        )
        response = connection.getresponse()
        status = response.status
        content = response.read()
        connection.close()
        return status, content

    def test_interface_updated(self):
        html = (server.ROOT / "index.html").read_text()
        self.assertIn("<title>Odin AI Workstation</title>", html)
        self.assertIn('id="message"', html)
        self.assertIn('id="tasks"', html)

    def test_loopback_binding(self):
        self.assertEqual(server.HOST, "127.0.0.1")

    def test_health_endpoint(self):
        status, content = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        data = json.loads(content)
        self.assertEqual(data["mode"], "isolated")
        self.assertFalse(data["worker_connected"])

    def test_task_endpoint_read_only(self):
        status, content = self.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        data = json.loads(content)
        self.assertEqual(data["access"], "read_only")

    def test_invalid_host_rejected(self):
        status, _ = self.request(
            "GET", "/api/health",
            headers={"Host": "untrusted.example"}
        )
        self.assertEqual(status, 403)

    def test_cross_origin_post_rejected(self):
        status, _ = self.request(
            "POST", "/api/chat",
            body=json.dumps({"message": "hello"}),
            headers={
                "Origin": "http://untrusted.example",
                "Content-Type": "application/json",
                "X-Odin-Request": "chat"
            }
        )
        self.assertEqual(status, 403)

    def test_missing_request_header_rejected(self):
        status, _ = self.request(
            "POST", "/api/chat",
            body=json.dumps({"message": "hello"}),
            headers={
                "Origin": "http://127.0.0.1:8765",
                "Content-Type": "application/json"
            }
        )
        self.assertEqual(status, 403)

    def test_invalid_json_rejected(self):
        status, _ = self.request(
            "POST", "/api/chat",
            body="{invalid",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "Content-Type": "application/json",
                "X-Odin-Request": "chat"
            }
        )
        self.assertEqual(status, 400)

    def test_ai_disabled_by_default(self):
        import os
        original = os.environ.pop(
            "ODIN_STAGE5_ENABLE_AI", None
        )
        try:
            status, _ = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "hello"}),
                headers={
                    "Origin": "http://127.0.0.1:8765",
                    "Content-Type": "application/json",
                    "X-Odin-Request": "chat"
                }
            )
            self.assertEqual(status, 503)
        finally:
            if original is not None:
                os.environ["ODIN_STAGE5_ENABLE_AI"] = original

    def test_no_worker_import(self):
        source = (server.ROOT / "server.py").read_text()
        self.assertNotIn("import odin_worker", source)


    def test_missing_session_rejected(self):
        status, _ = self.request(
            "POST", "/api/chat",
            body=json.dumps({"message": "hello"}),
            headers={
                "Cookie": "",
                "Origin": "http://127.0.0.1:8765",
                "Content-Type": "application/json",
                "X-Odin-Request": "chat"
            }
        )
        self.assertEqual(status, 403)

    def test_wrong_session_rejected(self):
        status, _ = self.request(
            "POST", "/api/chat",
            body=json.dumps({"message": "hello"}),
            headers={
                "Cookie": "odin_session=incorrect",
                "Origin": "http://127.0.0.1:8765",
                "Content-Type": "application/json",
                "X-Odin-Request": "chat"
            }
        )
        self.assertEqual(status, 403)

    def test_external_assets(self):
        for route in ("/style.css", "/app.js"):
            status, content = self.request("GET", route)
            self.assertEqual(status, 200)
            self.assertGreater(len(content), 20)

    def test_no_inline_script(self):
        html = (server.ROOT / "index.html").read_text()
        self.assertIn('src="/app.js"', html)
        self.assertIn('href="/style.css"', html)
        self.assertNotIn("<style>", html)
        self.assertNotIn("<script>", html)

    def test_session_cookie_issued(self):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.http.server_port, timeout=5
        )
        connection.request(
            "GET", "/",
            headers={"Host": "127.0.0.1:8765"}
        )
        response = connection.getresponse()
        cookie = response.getheader("Set-Cookie", "")
        response.read()
        connection.close()
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)


    def test_chat_busy_rejected(self):
        from unittest.mock import patch

        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        self.assertTrue(self.http.chat_lock.acquire(False))
        try:
            with patch.dict(
                "os.environ",
                {"ODIN_STAGE5_ENABLE_AI": "1"},
            ):
                status, content = self.request(
                    "POST", "/api/chat",
                    body=json.dumps({"message": "test"}),
                    headers=headers,
                )
            self.assertEqual(status, 429)
            self.assertIn(b"already in progress", content)
        finally:
            self.http.chat_lock.release()

    def test_mock_ai_response(self):
        from unittest.mock import patch

        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        with patch.dict(
            "os.environ",
            {"ODIN_STAGE5_ENABLE_AI": "1"},
        ), patch.object(server, "ask_ai", return_value="MOCK_OK"):
            status, content = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "test"}),
                headers=headers,
            )
        self.assertEqual(status, 200)
        data = json.loads(content)
        self.assertEqual(data["answer"], "MOCK_OK")
        self.assertEqual(data["verification"], "unverified")
        self.assertFalse(data["persisted"])

    def test_empty_ai_response_rejected(self):
        from unittest.mock import patch

        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        with patch.dict(
            "os.environ",
            {"ODIN_STAGE5_ENABLE_AI": "1"},
        ), patch.object(server, "ask_ai", return_value=""):
            status, _ = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "test"}),
                headers=headers,
            )
        self.assertEqual(status, 502)

    def test_stale_provider_never_calls_model(self):
        from unittest.mock import patch

        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        with (
            patch.dict("os.environ", {
                "ODIN_STAGE5_ENABLE_AI": "1",
                "ODIN_STAGE5_PROVIDER": "openai",
            }),
            patch.object(server, "ask_ai", side_effect=AssertionError("model called")) as ai,
        ):
            status, payload = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "Test", "expected_provider": "local"}),
                headers=headers,
            )
            self.assertEqual(status, 409)
            self.assertIn(b"Model selection changed", payload)
            ai.assert_not_called()

    def test_non_string_provider_rejected_without_server_error(self):
        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        for provider in ([], {}, 42, True):
            status, _ = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "Test", "expected_provider": provider}),
                headers=headers,
            )
            self.assertEqual(status, 400)

    def test_invalid_expected_provider_rejected(self):
        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        status, _ = self.request(
            "POST", "/api/chat",
            body=json.dumps({"message": "Test", "expected_provider": "automatic"}),
            headers=headers,
        )
        self.assertEqual(status, 400)

    def test_chat_reports_actual_backend_provider(self):
        from unittest.mock import patch

        headers = {
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/json",
            "X-Odin-Request": "chat",
        }
        with (
            patch.dict("os.environ", {
                "ODIN_STAGE5_ENABLE_AI": "1", "ODIN_STAGE5_PROVIDER": "local"
            }),
            patch.object(server, "ask_ai", return_value="ON_DEVICE"),
        ):
            status, payload = self.request(
                "POST", "/api/chat",
                body=json.dumps({"message": "Hi", "expected_provider": "local"}),
                headers=headers,
            )
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(payload)["provider"], "local")

    def test_real_server_uses_threading(self):
        self.assertIn(
            "ThreadingHTTPServer((HOST, PORT), Handler)",
            (server.ROOT / "server.py").read_text(),
        )

    def test_socket_timeout_configured(self):
        self.assertIn(
            "self.connection.settimeout(15)",
            (server.ROOT / "server.py").read_text(),
        )


if __name__ == "__main__":
    unittest.main()
