"""Full sweep is one bounded, private, no-model diagnostic request (#148)."""
import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import odin_full_sweep as sweep
from scripts import odin_github_bridge as bridge
from scripts import odin_mailbox_audit as audit


class FullSweepTests(unittest.TestCase):
    SHA = "a" * 40
    ID = "f" * 32

    def request(self):
        now = datetime(2026, 11, 23, 19, 0, tzinfo=UTC)
        return {
            "version": 1, "id": self.ID, "action": "full_sweep",
            "created_at": bridge.iso(now),
            "expires_at": bridge.iso(now + timedelta(minutes=15)),
        }

    def sample(self, *, incident_count=0, preflight_state="PASS"):
        request = self.request()
        replies = {
            "ping": {"alive": True, "revision": self.SHA, "pid": 123},
            "stage5_health": {
                "reachable": True, "ready": True, "provider": "local",
                "ai_enabled": True,
            },
        }
        status = Mock(side_effect=lambda action: replies[action])
        health = Mock(return_value={
            "head": self.SHA, "queue_pending": 0, "queue_running": 0,
            "services": {n: {"state": "running"} for n in sweep.SERVICE_NAMES},
        })
        preflight = Mock(return_value={
            "checks": [{"check": "private_mailbox_runtime_checkout",
                        "status": preflight_state}],
        })
        audit_fn = Mock(return_value={
            "considered": 6,
            "counts": {"matched": 6, "pending": 1, "malformed": 0,
                       "stalled": 0, "rejected": 0},
            "incident_count_shown": incident_count,
            "incidents_truncated": False,
        })
        report = sweep.inspect(
            request, status_fn=status, health_fn=health,
            outbox=Path("/fake/private/outbox"), preflight_fn=preflight,
            audit_fn=audit_fn,
        )
        self.assertEqual([x.args[0] for x in status.call_args_list],
                         ["ping", "stage5_health"])
        health.assert_called_once_with()
        preflight.assert_called_once_with("device")
        audit_fn.assert_called_once_with(Path("/fake/private/outbox"), hours=1)
        return report

    def test_private_only_schema_rejects_shell_and_extra_fields(self):
        request = self.request()
        self.assertIn("full_sweep", bridge.PRIVATE_ACTIONS)
        self.assertNotIn("full_sweep", bridge.ACTIONS)
        self.assertIn("full_sweep", audit.ACTIONS_SAFE)
        with patch.object(bridge, "private_mailbox", True):
            self.assertEqual(
                bridge.validate_request(json.dumps(request), self.ID,
                                        now=datetime(2026, 11, 23, 19, 0, tzinfo=UTC)),
                request)
            for mutation in ({"command": "id"}, {"expected_sha": self.SHA}):
                with self.assertRaises(ValueError):
                    bridge.validate_request(json.dumps({**request, **mutation}),
                                            self.ID, now=datetime(2026, 11, 23, 19, 0, tzinfo=UTC))
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.validate_request(json.dumps(request), self.ID,
                                        now=datetime(2026, 11, 23, 19, 0, tzinfo=UTC))

    def test_one_reply_reports_proof_boundaries(self):
        report = self.sample()
        self.assertTrue(report["alive"])
        self.assertEqual(report["pid"], 123)
        self.assertEqual(report["revision"], self.SHA)
        self.assertEqual(report["source_consistency"], "PASS")
        self.assertEqual(report["preflight_checks"]["private_mailbox_runtime_checkout"], "PASS")
        self.assertEqual(report["mailbox"]["status"], "PASS")
        self.assertEqual(report["queue"], {"pending": 0, "running": 0})
        self.assertEqual(report["overall"], "UNVERIFIED")
        self.assertIn("model_inference_this_sweep", report["unverified_gates"])
        self.assertFalse(report["release_approved"])
        self.assertFalse(report["device_change_performed"])
        self.assertNotIn("/fake/private", json.dumps(report))

    def test_bad_incident_or_service_failure_is_fail(self):
        report = self.sample(incident_count=1)
        self.assertEqual(report["mailbox"]["status"], "FAIL")
        self.assertEqual(report["overall"], "FAIL")
        report = self.sample(preflight_state="FAIL")
        self.assertEqual(report["overall"], "FAIL")

    def test_missing_one_probe_is_unverified_not_success(self):
        request = self.request()
        report = sweep.inspect(
            request,
            status_fn=lambda _action: (_ for _ in ()).throw(OSError("private token text")),
            health_fn=lambda: {},
            outbox=Path("/fake/private/outbox"),
            preflight_fn=lambda mode: {},
            audit_fn=lambda path, hours: {},
        )
        self.assertFalse(report["alive"])
        self.assertEqual(report["mailbox"]["status"], "UNVERIFIED")
        self.assertEqual(report["source_consistency"], "UNVERIFIED")
        self.assertEqual(report["overall"], "UNVERIFIED")
        self.assertNotIn("private token text", json.dumps(report))

    def test_private_bridge_dispatch_calls_fixed_sweep_only(self):
        req = self.request()
        with patch.object(bridge, "private_mailbox", True), \
             patch.object(sweep, "inspect", return_value={"overall": "UNVERIFIED"}) as mocked:
            result = bridge.status_action("full_sweep", req)
        self.assertEqual(result["overall"], "UNVERIFIED")
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["outbox"], bridge.OUTBOX)
        with patch.object(bridge, "private_mailbox", False):
            with self.assertRaises(ValueError):
                bridge.status_action("full_sweep", req)


if __name__ == "__main__":
    unittest.main()
