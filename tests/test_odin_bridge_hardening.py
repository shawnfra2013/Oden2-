"""Offline safety tests for read-only GitHub bridge update preflight."""
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import odin_github_bridge as bridge


class PreflightSafetyTests(unittest.TestCase):
    ID = "abcdeffedcba00001111222233334444"
    SHA = "a" * 40

    def request(self, action="preflight_release"):
        now = datetime(2026, 11, 18, 22, tzinfo=UTC)
        data = {
            "version": 1, "id": self.ID, "action": action,
            "created_at": bridge.iso(now),
            "expires_at": bridge.iso(now + timedelta(minutes=30)),
        }
        if action in bridge.REVISION_ACTIONS:
            data["expected_sha"] = self.SHA
        return data, now

    def test_preflight_requires_exact_sha(self):
        data, now = self.request()
        self.assertEqual(
            bridge.validate_request(json.dumps(data), self.ID, now=now)["expected_sha"],
            self.SHA,
        )
        del data["expected_sha"]
        with self.assertRaises(ValueError):
            bridge.validate_request(json.dumps(data), self.ID, now=now)

    def test_rejects_injected_command(self):
        data, now = self.request()
        data["command"] = "sh -c 'id'"
        with self.assertRaises(ValueError):
            bridge.validate_request(json.dumps(data), self.ID, now=now)

    def test_preflight_matches_correct_remote_no_collisions(self):
        responses = {
            ("rev-parse", "HEAD"): "b" * 40,
            ("branch", "--show-current"): "main",
            ("rev-parse", "origin/main"): self.SHA,
        }

        def fake_git(*args, **kwargs):
            if args[:2] == ("fetch", "--quiet"):
                return ""
            return responses[args]

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "diff"] and "-z" in cmd:
                return SimpleNamespace(returncode=0, stdout="src/new.py\0")
            if cmd[:2] == ["git", "ls-files"]:
                return SimpleNamespace(returncode=0, stdout="):\0main\0")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(bridge, "git", side_effect=fake_git), \
                patch.object(bridge, "run", side_effect=fake_run), \
                patch.object(bridge, "checked_origin", return_value=True):
            result = bridge.status_action("preflight_release", {"expected_sha": self.SHA})
        self.assertTrue(result["safe_to_attempt_pull"])
        self.assertFalse(result["applied"])
        self.assertEqual(result["untracked_count"], 2)

    def test_preflight_rejects_new_file_collision(self):
        def fake_git(*args, **kwargs):
            if args[:2] == ("fetch", "--quiet"):
                return ""
            if args == ("rev-parse", "HEAD"):
                return "b" * 40
            if args == ("branch", "--show-current"):
                return "main"
            if args == ("rev-parse", "origin/main"):
                return self.SHA
            raise AssertionError(args)

        def fake_run(cmd, **kwargs):
            if cmd[:2] == ["git", "diff"] and "-z" in cmd:
                return SimpleNamespace(returncode=0, stdout="src/new.py\0")
            if cmd[:2] == ["git", "ls-files"]:
                return SimpleNamespace(returncode=0, stdout="src\0")
            return SimpleNamespace(returncode=0, stdout="")

        with patch.object(bridge, "git", side_effect=fake_git), \
                patch.object(bridge, "run", side_effect=fake_run), \
                patch.object(bridge, "checked_origin", return_value=True):
            result = bridge.status_action("preflight_release", {"expected_sha": self.SHA})
        self.assertFalse(result["safe_to_attempt_pull"])
        self.assertEqual(result["untracked_collisions"], 1)

    def test_other_requests_still_disallow_expected_sha(self):
        data, now = self.request("ping")
        data["expected_sha"] = self.SHA
        with self.assertRaises(ValueError):
            bridge.validate_request(json.dumps(data), self.ID, now=now)

    def test_process_lock_file_lives_under_ignored_state(self):
        with tempfile.TemporaryDirectory() as name, \
                patch.object(bridge, "STATE", Path(name)), \
                patch.object(bridge, "process_locked", return_value=0):
            self.assertEqual(bridge.process_once(), 0)
            self.assertTrue((Path(name) / "agent.lock").exists())


if __name__ == "__main__":
    unittest.main()
