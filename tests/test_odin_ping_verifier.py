"""No-network, request-bound ping evidence verification."""
import unittest
from datetime import UTC, datetime, timedelta

from scripts.odin_ping_verifier import verify_ping

NOW = datetime(2026, 11, 23, 14, 0, tzinfo=UTC)
ID = "a" * 32


def time(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def request():
    return {"version": 1, "id": ID, "action": "ping",
            "created_at": time(-4), "expires_at": time(10)}


def receipt():
    return {"version": 1, "id": ID, "action": "ping",
            "status": "complete", "checked_at": time(-2),
            "result": {"alive": True, "bridge_version": 1}}


class PingVerifierTests(unittest.TestCase):
    def test_matching_fresh_ping(self):
        result = verify_ping(request(), receipt(), now=NOW)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["device_verified"])
        self.assertFalse(result["source_ci_verified"])

    def test_missing_is_unverified(self):
        self.assertEqual(verify_ping(request(), None, now=NOW)["status"], "UNVERIFIED")

    def test_expiry_does_not_create_false_failure(self):
        req = request()
        req["expires_at"] = time(-1)
        self.assertEqual(verify_ping(req, None, now=NOW)["reason"],
                         "request_expired_without_receipt")

    def test_stale_receipt_is_not_live(self):
        req = request()
        req["created_at"] = time(-30)
        req["expires_at"] = time(10)
        old = receipt()
        old["checked_at"] = time(-10)
        self.assertEqual(verify_ping(req, old, now=NOW)["status"], "UNVERIFIED")

    def test_different_request_is_a_failure(self):
        wrong = receipt()
        wrong["id"] = "b" * 32
        self.assertEqual(verify_ping(request(), wrong, now=NOW)["status"], "FAIL")

    def test_not_alive_and_rejected_fail(self):
        item = receipt()
        item["result"]["alive"] = False
        self.assertEqual(verify_ping(request(), item, now=NOW)["reason"], "ping_not_alive")
        item["status"] = "rejected_or_failed"
        self.assertEqual(verify_ping(request(), item, now=NOW)["status"], "FAIL")

    def test_no_shell_or_extra_fields(self):
        req = request()
        req["command"] = "sh"
        with self.assertRaises(ValueError):
            verify_ping(req, None, now=NOW)

    def test_invalid_clock_order_fails(self):
        item = receipt()
        item["checked_at"] = time(-6)
        self.assertEqual(verify_ping(request(), item, now=NOW)["status"], "FAIL")

    def test_future_receipt_cannot_be_live(self):
        item = receipt()
        item["checked_at"] = time(5)
        self.assertEqual(verify_ping(request(), item, now=NOW)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
