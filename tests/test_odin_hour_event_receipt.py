"""Immutable and redacted ODIN-HOUR GitHub event evidence regressions."""
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from scripts import odin_hour_event_receipt as receipt


class OdinHourEventReceiptTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 23, 9, 15, tzinfo=UTC)
        self.event = {
            "action": "synchronize", "number": 119,
            "repository": {"full_name": "shawnfra2013/Oden2-"},
            "pull_request": {
                "number": 119, "title": "[ODIN-HOUR] Test new commit",
                "body": "CONFIDENTIAL USER CONTENT SHOULD NOT BE COPIED",
                "head": {"sha": "a" * 40, "repo": {"full_name": "shawnfra2013/Oden2-"}},
                "base": {"sha": "b" * 40},
            },
            "before": "c" * 40, "after": "a" * 40,
            "sender": {"login": "example"},
            "installation": {"access_tokens": "NEVER_COPY"},
        }

    def capture(self, **changes):
        return receipt.capture(self.event, run_id=45142086688, now=self.now, **changes)

    def test_immutable_original_event_head(self):
        item = self.capture()
        self.assertEqual(item["event_head_sha"], "a" * 40)
        self.assertEqual(item["event_action"], "synchronize")
        self.assertEqual(item["pr_number"], 119)
        self.assertTrue(item["head_sha_from_original_github_event"])
        self.assertFalse(item["work_delivery_head_sha_verified"])
        self.assertFalse(item["device_action_verified"])

    def test_no_untrusted_content_in_receipt(self):
        raw = json.dumps(self.capture())
        self.assertNotIn("CONFIDENTIAL", raw)
        self.assertNotIn("NEVER_COPY", raw)
        self.assertNotIn("sender", raw)

    def test_mismatched_synchronize_sha_fails_closed(self):
        self.event["after"] = "d" * 40
        with self.assertRaises(ValueError):
            self.capture()

    def test_missing_sha_fails_closed(self):
        self.event["pull_request"]["head"]["sha"] = None
        with self.assertRaises(ValueError):
            self.capture()

    def test_wrong_repository_or_fork_fails_closed(self):
        self.event["pull_request"]["head"]["repo"]["full_name"] = "someone/other"
        with self.assertRaises(ValueError):
            self.capture()
        self.event["pull_request"]["head"]["repo"]["full_name"] = receipt.REPO
        self.event["repository"]["full_name"] = "someone/other"
        with self.assertRaises(ValueError):
            self.capture()

    def test_unmarked_or_comment_event_cannot_trigger(self):
        self.event["pull_request"]["title"] = "A normal PR"
        with self.assertRaises(ValueError):
            self.capture()
        self.event["pull_request"]["title"] = "[ODIN-HOUR] Test"
        self.event["action"] = "issue_comment"
        with self.assertRaises(ValueError):
            self.capture()

    def test_valid_actions_and_strict_numbers(self):
        for action in ("opened", "reopened", "ready_for_review", "review_requested"):
            with self.subTest(action=action):
                self.event["action"] = action
                self.event.pop("after", None)
                self.assertEqual(self.capture()["event_action"], action)
        for number in (0, True, 10**17):
            with self.subTest(number=number), self.assertRaises(ValueError):
                receipt.capture(self.event, run_id=number)

    def test_response_is_exclusive_and_mode_600(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            receipt.save_receipt(path, self.capture())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                receipt.save_receipt(path, self.capture())
            self.assertEqual(json.loads(path.read_text())["event_head_sha"], "a" * 40)

    def test_refuse_symlinked_event_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "raw.json"
            target.write_text(json.dumps(self.event))
            event_alias = root / "alias.json"
            event_alias.symlink_to(target)
            with self.assertRaises(ValueError):
                receipt.read_event(event_alias)
            output_alias = root / "output.json"
            output_alias.symlink_to(root / "unwanted")
            with self.assertRaises(ValueError):
                receipt.save_receipt(output_alias, self.capture())

    def test_reject_oversized_event_without_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            event = Path(tmp) / "too-large.json"
            event.write_bytes(b"x" * (receipt.MAX_EVENT_BYTES + 1))
            with self.assertRaises(ValueError):
                receipt.read_event(event)

    def test_read_and_capture_stays_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "github-event.json"
            path.write_text(json.dumps(self.event), encoding="utf-8")
            record = receipt.capture(receipt.read_event(path), run_id=123, now=self.now)
            self.assertEqual(record["evidence_url"],
                             "https://github.com/shawnfra2013/Oden2-/actions/runs/123")
            self.assertFalse(record["raw_event_stored"])


if __name__ == "__main__":
    unittest.main()
