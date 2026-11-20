"""Exercise the private mailbox against disposable Git repositories."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import odin_github_bridge as bridge


def git(directory, *args):
    return subprocess.run(
        ["git", *args], cwd=directory, capture_output=True, text=True, check=True,
    ).stdout.strip()


class PrivateMailboxIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(temporary)
        self.remote = self.root / "mailbox.git"
        self.seed = self.root / "seed"
        git(self.root, "init", "--bare", str(self.remote))
        git(self.root, "init", str(self.seed))
        git(self.seed, "config", "user.name", "Test")
        git(self.seed, "config", "user.email", "test@example.invalid")
        git(self.seed, "commit", "--allow-empty", "-m", "Seed")
        git(self.seed, "push", str(self.remote), f"HEAD:refs/heads/{bridge.OUTBOX_BRANCH}")
        state = self.root / "state"
        self.enterContext(patch.multiple(
            bridge, private_mailbox=True, STATE=state, OUTBOX=state / "outbox",
            PRIVATE_ORIGIN=str(self.remote),
        ))
        self.enterContext(patch.object(bridge, "checked_origin", return_value=str(self.remote)))
        self.enterContext(patch.object(bridge, "mailbox_git_args", return_value=["git"]))

    def request(self, number, **overrides):
        request_id = f"{number:032x}"
        now = bridge.utcnow()
        payload = {
            "version": 1, "id": request_id, "action": "staging_probe",
            "created_at": bridge.iso(now - timedelta(minutes=2)),
            "expires_at": bridge.iso(now + timedelta(minutes=10)),
        }
        payload.update(overrides)
        self.write_request(request_id, json.dumps(payload))
        return request_id

    def write_request(self, request_id, content):
        path = self.seed / "bridge" / "requests" / f"{request_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def publish(self):
        git(self.seed, "add", ".")
        git(self.seed, "commit", "-m", "Requests")
        git(self.seed, "push", str(self.remote), f"HEAD:refs/heads/{bridge.INBOX_BRANCH}")

    def receipt(self, request_id):
        path = f"{bridge.OUTBOX_BRANCH}:bridge/responses/{request_id}.json"
        return json.loads(git(self.remote, "show", path))

    def test_failed_publish_reuses_saved_commit_on_next_cycle(self):
        request_id = self.request(1)
        self.publish()
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o700)
        with self.assertRaises(RuntimeError):
            bridge.process_once()
        saved = git(bridge.OUTBOX, "rev-parse", "HEAD")
        hook.unlink()

        with patch.object(bridge, "status_action") as action:
            self.assertEqual(bridge.process_once(), 0)
            self.assertEqual(bridge.process_once(), 0)
            action.assert_not_called()

        self.assertEqual(git(self.remote, "rev-parse", bridge.OUTBOX_BRANCH), saved)
        receipt = self.receipt(request_id)
        payload = f"odin-staging-probe:{request_id}\n".encode()
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["result"], {
            "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        })
        self.assertIn("picked_up_at", receipt["timing"])
        self.assertGreaterEqual(receipt["timing"]["action_ms"], 0)

    def test_invalid_requests_do_not_execute_or_block_valid_work(self):
        rejected = [
            self.request(1, action="checks"),
            self.request(2, path="example.txt"),
            self.request(3, command="example"),
            self.request(4, version=True),
        ]
        for number, content in ((5, "{"), (6, " " * 4097)):
            request_id = f"{number:032x}"
            self.write_request(request_id, content)
            rejected.append(request_id)
        expired = self.request(7, expires_at=bridge.iso(bridge.utcnow() - timedelta(minutes=1)))
        valid = self.request(8)
        self.publish()

        with patch.object(bridge, "status_action", wraps=bridge.status_action) as action:
            self.assertEqual(bridge.process_once(), 5)
            self.assertEqual(bridge.process_once(), 3)
            self.assertEqual(bridge.process_once(), 0)
            action.assert_called_once()
            self.assertEqual(action.call_args.args[1]["id"], valid)
        for request_id in rejected:
            self.assertEqual(self.receipt(request_id)["status"], "rejected_or_failed")
        self.assertEqual(self.receipt(expired)["status"], "expired")
        self.assertEqual(self.receipt(valid)["status"], "complete")

    def test_only_direct_request_path_can_claim_receipt(self):
        nested_id = self.request(1)
        directory = self.seed / "bridge" / "requests"
        nested = directory / "000"
        nested.mkdir()
        (directory / f"{nested_id}.json").rename(nested / f"{nested_id}.json")
        valid = self.request(2)
        (nested / f"{valid}.json").write_text("{}", encoding="utf-8")
        self.publish()

        self.assertEqual(bridge.process_once(), 1)
        self.assertEqual(self.receipt(valid)["status"], "complete")
        self.assertFalse((bridge.OUTBOX / "bridge" / "responses" / f"{nested_id}.json").exists())

    def test_private_inference_receipt_reaches_git_outbox(self):
        from scripts import odin_inference_probe as inference
        identifier = self.request(11, action="inference_probe")
        self.publish()
        (self.root / "key").write_text("test-only-value")
        (self.root / "key").chmod(0o600)
        response = (f"ODIN-{identifier}-63", {"id": "resp_fixture", "model": inference.MODEL,
                                               "status": "completed"})
        with patch.object(inference, "CONFIG", self.root), patch.object(
            inference, "request_answer", return_value=response
        ) as provider:
            self.assertEqual(bridge.process_once(), 1)
            self.assertEqual(bridge.process_once(), 0)
            provider.assert_called_once()
        receipt = self.receipt(identifier)
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(receipt["action"], "inference_probe")
        self.assertTrue(receipt["result"]["match"])
        self.assertIn("picked_up_at", receipt["timing"])
        self.assertNotIn("test-only-value", json.dumps(receipt))
