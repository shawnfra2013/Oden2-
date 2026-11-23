import http.client
import json
import os
import threading
import unittest
from http.server import HTTPServer
from unittest.mock import patch

import phone_access
import server


class PhoneAccessTests(unittest.TestCase):
    def setUp(self):
        self.http = HTTPServer(("127.0.0.1", 0), server.Handler)
        self.http.allowed_peer = "127.0.0.2"
        self.http.request_host = f"127.0.0.1:{self.http.server_port}"
        self.http.session_token = "test-session"
        self.http.chat_lock = threading.BoundedSemaphore(1)
        thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)

    def request(self, method, path, *, peer="127.0.0.2", headers=None, body=None):
        connection = http.client.HTTPConnection(
            self.http.request_host, timeout=3, source_address=(peer, 0),
        )
        try:
            connection.request(method, path, headers=headers or {}, body=body)
            response = connection.getresponse()
            return response.status, response.getheader("Set-Cookie"), response.read()
        finally:
            connection.close()

    def test_enrollment_requires_distinct_tailnet_ipv4_addresses(self):
        self.assertEqual(phone_access.addresses(["100.70.0.1", "100.70.0.2"]),
                         ("100.70.0.1", "100.70.0.2"))
        for invalid in (["0.0.0.0", "100.70.0.2"], ["192.168.1.2", "100.70.0.2"],
                        ["100.70.0.2", "100.70.0.2"]):
            with self.assertRaises(ValueError):
                phone_access.addresses(invalid)

    def test_only_enrolled_peer_gets_session_and_live_status(self):
        status, session, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("odin_session=test-session", session)
        self.assertEqual(self.request("GET", "/api/health", peer="127.0.0.3",
                                      headers={"X-Forwarded-For": "127.0.0.2"})[:2],
                         (403, None))
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "other"})[:2],
                         (403, None))

    def test_phone_same_origin_chat_has_no_cloud_fallback(self):
        headers = {"Origin": "http://" + self.http.request_host,
                   "Content-Type": "application/json", "X-Odin-Request": "chat",
                   "Cookie": "odin_session=test-session"}
        body = json.dumps({"message": "Check local inference"})
        with patch.dict(os.environ, {"ODIN_STAGE5_ENABLE_AI": "1", "ODIN_STAGE5_PROVIDER": "openai"}):
            with patch.object(server, "ask_ai") as model:
                self.assertEqual(self.request("POST", "/api/chat", headers=headers, body=body)[0],
                                 503)
                model.assert_not_called()
        with patch.dict(os.environ, {"ODIN_STAGE5_ENABLE_AI": "1", "ODIN_STAGE5_PROVIDER": "local"}):
            with patch("local_adapter.ask_local", return_value="Local answer") as model:
                self.assertEqual(self.request("POST", "/api/chat", body=body, headers={
                    **headers, "Origin": "http://other",
                })[0], 403)
                self.assertEqual(self.request("POST", "/api/chat", body=body, headers={
                    **headers, "Cookie": "",
                })[0], 403)
                model.assert_not_called()
                status, _, reply = self.request("POST", "/api/chat", headers=headers, body=body)
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(reply)["answer"], "Local answer")
                model.assert_called_once()

    def test_restart_requires_session_and_exact_request(self):
        headers = {"Origin": "http://" + self.http.request_host,
                   "Content-Type": "application/json", "X-Odin-Request": "chat",
                   "Cookie": "odin_session=test-session"}
        request_id = "abc0" * 8
        with patch("scripts.odin_service_restart.start_restart", return_value=True) as restart:
            for bad in ({"id": request_id, "service": "sshd"}, {"id": "bad"}):
                self.assertEqual(self.request("POST", "/api/restart", headers=headers,
                                              body=json.dumps(bad))[0], 400)
            restart.assert_not_called()
            self.assertEqual(self.request("POST", "/api/restart", headers=headers,
                                          body=json.dumps({"id": request_id}))[0], 202)
            restart.assert_called_once_with(request_id)
