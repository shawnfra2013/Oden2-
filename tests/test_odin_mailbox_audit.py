"""Read-only mailbox incident auditor and private evidence journal regressions."""
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts import odin_mailbox_audit as audit


class MailboxAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, 7, 40, tzinfo=UTC)
        self.ident = "a" * 32
        self.request = {
            "version": 1, "id": self.ident, "action": "ping",
            "created_at": "2026-11-23T07:38:00Z",
            "expires_at": "2026-11-23T07:53:00Z",
        }
        self.response = {
            "version": 1, "id": self.ident, "action": "ping",
            "status": "complete", "checked_at": "2026-11-23T07:39:05Z",
            "result": {"alive": True},
        }

    def run_audit(self, req=None, reply=None, **kwargs):
        return audit.audit_messages(
            {self.ident + ".json": self.request if req is None else req},
            {} if reply is False else {self.ident + ".json": self.response if reply is None else reply},
            now=self.now, **kwargs,
        )

    def test_matched_ping_and_elapsed_time(self):
        result = self.run_audit()
        self.assertEqual(result["counts"]["matched"], 1)
        self.assertEqual(result["max_response_latency_s"], 65)
        self.assertEqual(result["incidents"], [])
        self.assertFalse(result["device_live_verified"])
        self.assertFalse(result["agent_read_verified"])

    def test_pending_and_stalled_missing_reply(self):
        self.request["created_at"] = "2026-11-23T07:39:30Z"
        report = self.run_audit(reply=False)
        self.assertEqual(report["counts"]["pending"], 1)
        self.assertFalse(report["incidents"])
        self.request["created_at"] = "2026-11-23T07:36:30Z"
        report = self.run_audit(reply=False)
        self.assertEqual(report["counts"]["stalled"], 1)
        self.assertEqual(report["incidents"][0]["code"], "stalled")

    def test_expired_without_reply_is_reported(self):
        self.request["created_at"] = "2026-11-23T07:15:00Z"
        self.request["expires_at"] = "2026-11-23T07:25:00Z"
        r = self.run_audit(reply=False)
        self.assertEqual(r["counts"]["expired_without_reply"], 1)
        self.assertEqual(r["incidents"][0]["id"], self.ident)

    def test_explicit_expiry_rejection_and_unverified(self):
        for status, action in (
            ("expired", "none"), ("rejected_or_failed", "none"),
            ("unverified", "ping"),
        ):
            with self.subTest(status=status):
                reply = {**self.response, "status": status, "action": action}
                report = self.run_audit(reply=reply)
                key = "rejected" if status == "rejected_or_failed" else status
                self.assertEqual(report["counts"][key], 1)
                self.assertEqual(len(report["incidents"]), 1)

    def test_refuse_wrong_id_action_and_pre_request_response(self):
        for changed, problem in (
            ({"id": "b" * 32}, "malformed_response"),
            ({"action": "stage5_health"}, "action_mismatch"),
            ({"checked_at": "2026-11-23T07:30:00Z"}, "response_before_request"),
            ({"status": "UNKNOWN"}, "malformed_response"),
        ):
            with self.subTest(case=problem):
                result = self.run_audit(reply={**self.response, **changed})
                self.assertEqual(result["incidents"][0]["code"], problem)

    def test_ping_cannot_be_complete_if_alive_false(self):
        outcome = self.run_audit(reply={**self.response, "result": {"alive": False}})
        self.assertEqual(outcome["incidents"][0]["code"], "ping_not_alive")
        self.assertEqual(outcome["counts"]["matched"], 0)

    def test_rejection_of_arbitrary_shell_is_recorded_not_executed(self):
        req = {**self.request, "action": "shell", "command": "whoami"}
        reply = {**self.response, "action": "none", "status": "rejected_or_failed", "result": {}}
        report = self.run_audit(req=req, reply=reply)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertNotIn("whoami", str(report))
        self.assertNotIn("command", str(report))
        self.assertFalse(report["agent_read_verified"])

    def test_hide_private_messages_and_late_historical_events(self):
        req = {**self.request, "secret": "confidential-note"}
        reply = {**self.response, "result": {"alive": True, "secret": "private-response"}}
        report = self.run_audit(req=req, reply=reply)
        self.assertNotIn("confidential-note", str(report))
        self.assertNotIn("private-response", str(report))
        req["created_at"] = "2026-11-22T07:38:00Z"
        req["expires_at"] = "2026-11-22T07:53:00Z"
        report = self.run_audit(req=req, reply=reply)
        self.assertEqual(report["considered"], 0)

    def test_malformed_file_and_request_fields(self):
        report = audit.audit_messages(
            {"../bad.json": self.request,
             self.ident + ".json": {**self.request, "id": "b" * 32}},
            {}, now=self.now,
        )
        self.assertEqual(report["counts"]["malformed"], 2)
        self.assertIn("malformed_request", [x["code"] for x in report["incidents"]])

    def test_completed_allowlisted_mailbox_audit_is_not_an_incident(self):
        req = {**self.request, "action": "mailbox_audit"}
        reply = {**self.response, "action": "mailbox_audit",
                 "result": {"scope": "private_mailbox_metadata", "matched": 1}}
        report = self.run_audit(req=req, reply=reply)
        self.assertEqual(report["counts"]["matched"], 1)
        self.assertEqual(report["counts"]["malformed"], 0)
        self.assertEqual(report["incidents"], [])
        self.assertFalse(report["agent_read_verified"])

    def test_unexpected_completed_shell_action_is_not_treated_as_success(self):
        request = {**self.request, "action": "shell"}
        reply = {**self.response, "action": "shell"}
        result = self.run_audit(req=request, reply=reply)
        self.assertEqual(result["counts"]["matched"], 0)
        self.assertEqual(result["incidents"][0]["code"], "unexpected_action_complete")

    def test_future_messages_and_orphan_responses_reported(self):
        request = {
            **self.request,
            "created_at": "2026-11-23T08:00:00Z",
            "expires_at": "2026-11-23T08:15:00Z",
        }
        result = self.run_audit(req=request, reply=False)
        self.assertEqual(result["incidents"][0]["code"], "future_request")
        response = {**self.response, "checked_at": "2026-11-23T08:00:00Z"}
        result = self.run_audit(reply=response)
        self.assertEqual(result["incidents"][0]["code"], "response_in_future")
        result = audit.audit_messages({}, {self.ident + ".json": self.response}, now=self.now)
        self.assertEqual(result["incidents"][0]["code"], "orphan_response")

    def test_reject_directory_segment_even_with_valid_hex_filename(self):
        result = audit.audit_messages(
            {"../" + self.ident + ".json": self.request},
            {}, now=self.now,
        )
        self.assertEqual(result["counts"]["malformed"], 1)

    def test_strict_bounded_config(self):
        for kwargs in ({"hours": 0}, {"hours": 25}, {"pending_after_seconds": 5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_audit(**kwargs)

    def test_audit_reports_are_immutable_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "audit"
            first = audit.save_report(self.run_audit(), location)
            second = audit.save_report(self.run_audit(), location)
            self.assertNotEqual(first, second)
            self.assertEqual(first.stat().st_mode & 0o777, 0o600)
            self.assertEqual(second.stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(list(location.glob("*.json"))), 2)
            self.assertEqual(location.stat().st_mode & 0o777, 0o700)

    def test_refuse_symlinked_report_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory)
            (location / "alias").symlink_to(location / "destination")
            with self.assertRaises(ValueError):
                audit.save_report(self.run_audit(), location / "alias")

    def test_git_reader_rejects_wrong_refs_and_paths(self):
        with self.assertRaises(ValueError):
            audit.git_records(Path("/tmp"), "refs/heads/production", "bridge/requests/")
        with self.assertRaises(ValueError):
            audit.git_records(Path("/tmp"), "HEAD", "secrets/")

    def test_no_local_mailbox_fails_without_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                audit.inspect_local(Path(directory) / "missing", hours=1)


if __name__ == "__main__":
    unittest.main()
