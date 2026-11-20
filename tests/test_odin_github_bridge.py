"""Offline validation tests for the GitHub-backed Odin bridge."""
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import odin_github_bridge as bridge


class BridgeRequestTests(unittest.TestCase):
    ID = "0123456789abcdef0123456789abcdef"

    def setUp(self):
        self.now = datetime(2026, 11, 18, 22, 0, tzinfo=UTC)
        self.request = {
            "version": 1,
            "id": self.ID,
            "action": "ping",
            "created_at": bridge.iso(self.now - timedelta(minutes=1)),
            "expires_at": bridge.iso(self.now + timedelta(minutes=29)),
        }

    def decode(self):
        return bridge.validate_request(
            json.dumps(self.request), self.ID, now=self.now
        )


    def test_staging_probe_is_private_only(self):
        self.request["action"] = "staging_probe"
        with self.assertRaises(ValueError):
            self.decode()
        with patch.object(bridge, "private_mailbox", True):
            self.assertEqual(self.decode()["action"], "staging_probe")
            self.request["path"] = "arbitrary.txt"
            with self.assertRaises(ValueError):
                self.decode()

    def test_staging_probe_reports_checksum_and_cleans_up(self):
        payload = f"odin-staging-probe:{self.ID}\n".encode("ascii")
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            with patch.object(bridge, "STATE", state), patch.object(bridge, "private_mailbox", True):
                receipt = bridge.status_action("staging_probe", {"id": self.ID})
            self.assertEqual(list(state.iterdir()), [])
        self.assertEqual(receipt, {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })

    def test_accept_explicit_commit_verification(self):
        self.request["action"] = "verify_release"
        self.request["expected_sha"] = "a" * 40
        self.assertEqual(self.decode()["expected_sha"], "a" * 40)

    def test_verification_requires_expected_sha(self):
        self.request["action"] = "verify_release"
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_short_or_malformed_commit_sha(self):
        self.request["action"] = "verify_release"
        for candidate in ("b" * 39, "Z" * 40, "abc", 42, None):
            with self.subTest(candidate=candidate):
                self.request["expected_sha"] = candidate
                with self.assertRaises(ValueError):
                    self.decode()

    def test_no_extra_sha_allowed_on_ping(self):
        self.request["expected_sha"] = "a" * 40
        with self.assertRaises(ValueError):
            self.decode()

    def test_release_match_runs_checks_without_writing(self):
        expected = "a" * 40

        def fake_git(*args, **kwargs):
            if args[:2] == ("rev-parse", "HEAD"):
                return expected
            if args[:2] == ("branch", "--show-current"):
                return "main"
            raise AssertionError(f"Unexpected git operation: {args}")

        with patch.object(bridge, "git", side_effect=fake_git), \
                patch.object(
                    bridge, "run",
                    return_value=SimpleNamespace(returncode=0),
                ) as mock_run:
            result = bridge.status_action(
                "verify_release", {"expected_sha": expected}
            )
        self.assertTrue(result["verified"])
        self.assertTrue(result["tests_ran"])
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(mock_run.call_count, 5)

    def test_release_mismatch_skips_regression_tests(self):
        with patch.object(bridge, "git") as mock_git, \
                patch.object(
                    bridge, "run",
                    return_value=SimpleNamespace(returncode=0),
                ) as mock_run:
            mock_git.side_effect = ["b" * 40, "main"]
            result = bridge.status_action(
                "verify_release", {"expected_sha": "a" * 40}
            )
        self.assertFalse(result["verified"])
        self.assertFalse(result["revision_matches"])
        self.assertFalse(result["tests_ran"])
        self.assertEqual(mock_run.call_count, 2)

    def test_revision_change_during_tests_invalidates_result(self):
        expected = "a" * 40
        with patch.object(bridge, "git") as mock_git, \
                patch.object(
                    bridge, "run",
                    return_value=SimpleNamespace(returncode=0),
                ):
            mock_git.side_effect = [expected, "main", "b" * 40]
            result = bridge.status_action(
                "verify_release", {"expected_sha": expected}
            )
        self.assertFalse(result["verified"])
        self.assertTrue(result["tests_ran"])

    def test_accept_valid_ping(self):
        self.assertEqual(self.decode()["action"], "ping")

    def test_accept_only_declared_read_only_actions(self):
        for action in bridge.ACTIONS - bridge.REVISION_ACTIONS:
            with self.subTest(action=action):
                self.request["action"] = action
                self.assertEqual(self.decode()["action"], action)

    def test_reject_arbitrary_shell_command(self):
        self.request["action"] = "sh -c 'id'"
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_extra_payload_field(self):
        self.request["command"] = "echo hidden"
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_id_mismatch(self):
        self.request["id"] = "f" * 32
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_expired_request(self):
        self.request["expires_at"] = bridge.iso(self.now - timedelta(seconds=1))
        with self.assertRaises(bridge.ExpiredRequest):
            self.decode()

    def test_reject_expiry_over_one_hour(self):
        self.request["expires_at"] = bridge.iso(self.now + timedelta(hours=2))
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_future_created_at(self):
        self.request["created_at"] = bridge.iso(self.now + timedelta(minutes=6))
        self.request["expires_at"] = bridge.iso(self.now + timedelta(minutes=30))
        with self.assertRaises(ValueError):
            self.decode()

    def test_reject_oversized_request(self):
        with self.assertRaises(ValueError):
            bridge.validate_request("x" * 4097, self.ID, now=self.now)

    def test_reject_invalid_id_filename(self):
        with self.assertRaises(ValueError):
            bridge.validate_request(json.dumps(self.request), "../evil", now=self.now)

    def test_invalid_json_rejected(self):
        with self.assertRaises(ValueError):
            bridge.validate_request("{", self.ID, now=self.now)

    def test_ping_has_no_remote_or_shell_side_effects(self):
        with patch.object(bridge, "run", side_effect=AssertionError("run")):
            self.assertEqual(
                bridge.status_action("ping"),
                {"alive": True, "bridge_version": 1},
            )

    def test_reject_unknown_operation(self):
        with self.assertRaises(ValueError):
            bridge.status_action("exec")


if __name__ == "__main__":
    unittest.main()
