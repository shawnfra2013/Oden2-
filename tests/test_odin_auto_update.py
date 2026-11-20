"""Offline contract tests for Odin's CI-gated source updater."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import odin_auto_update as updater


class UpdateSafetyTests(unittest.TestCase):
    OLD = "a" * 40
    TARGET = "b" * 40

    @classmethod
    def ci(cls, sha=None, conclusion="success", event="push"):
        return {"workflow_runs": [{
            "head_sha": sha or cls.TARGET,
            "head_branch": "main",
            "event": event,
            "status": "completed",
            "conclusion": conclusion,
            "head_repository": {"full_name": updater.REPO},
        }]}

    def make_git(self, *, dirty=False, branch="main", origin=None, diverged=False):
        origins = updater.ORIGINS
        remote = origin or min(origins)

        def fake(*args):
            table = {
                ("branch", "--show-current"): branch,
                ("remote", "get-url", "origin"): remote,
                ("status", "--porcelain", "--untracked-files=no"): " M README.md" if dirty else "",
                ("rev-parse", "origin/main"): self.TARGET,
                ("fetch", "origin", "main"): "",
                ("merge-base", self.OLD, self.TARGET): ("c" * 40 if diverged else self.OLD),
            }
            if args == ("rev-parse", "HEAD"):
                return self.TARGET if self.updated else self.OLD
            return table[args]
        return fake

    def setUp(self):
        self.updated = False

    def test_exact_ci_approval_required(self):
        self.assertTrue(updater.ci_has_passed(self.TARGET, self.ci()))
        self.assertFalse(updater.ci_has_passed(self.TARGET, self.ci(self.OLD)))
        self.assertFalse(updater.ci_has_passed(self.TARGET, self.ci(event="pull_request")))
        self.assertFalse(updater.ci_has_passed(self.TARGET, self.ci(conclusion="failure")))
        self.assertFalse(updater.ci_has_passed(self.TARGET, {"workflow_runs": []}))
        self.assertFalse(updater.ci_has_passed("untrusted", self.ci()))

    def test_workflow_query_filters_exact_head_and_bounds_page(self):
        with patch.object(updater, "urlopen") as open_url:
            response = open_url.return_value.__enter__.return_value
            response.read.return_value = json.dumps(self.ci()).encode()
            self.assertTrue(updater.ci_has_passed(self.TARGET, updater.read_ci_payload(self.TARGET)))
            url = open_url.call_args.args[0].full_url
            self.assertIn("&head_sha=" + self.TARGET, url)
            self.assertIn("per_page=3&", url)
            with self.assertRaises(ValueError):
                updater.read_ci_payload("invalid")

    def test_good_release_uses_exact_sha_and_safe_pull(self):
        def run(cmd, **kwargs):
            self.assertEqual(cmd[0], "bash")
            self.assertTrue(cmd[1].endswith("/scripts/odin-safe-pull.sh"))
            self.assertEqual(kwargs["env"]["ODIN_EXPECTED_SHA"], self.TARGET)
            self.assertEqual(kwargs["timeout"], 120)
            self.updated = True
            return SimpleNamespace(returncode=0)

        result = updater.update_once(
            root=Path("/odin-workspace"),
            git_cmd=self.make_git(),
            fetch_ci=self.ci,
            run_cmd=run,
        )
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["after"], self.TARGET)
        self.assertEqual(result["reason"], "source_updated")

    def test_reload_only_after_saved_update_or_verified_transition(self):
        legacy = updater.result_record("updated", "source_updated_restart_not_automatic",
                                       self.OLD, self.TARGET, self.TARGET)
        for status, revision, expected in (
            ("updated", self.TARGET, True),
            ("current", self.TARGET, True),
            ("current", self.OLD, False),
            ("waiting", self.TARGET, False),
        ):
            with self.subTest(status=status, revision=revision), tempfile.TemporaryDirectory() as directory:
                result = Path(directory) / "update.json"
                result.write_text(json.dumps(legacy))
                current = updater.result_record(status, "test", self.OLD, self.TARGET, revision)

                def reload_services(args, *, result=result, status=status, **kwargs):
                    self.assertEqual(args[-1], "--after-update")
                    self.assertEqual(json.loads(result.read_text())["status"], status)
                    return SimpleNamespace(returncode=0)

                with (
                    patch.object(updater, "RESULT", result),
                    patch.object(updater, "git", return_value=revision),
                    patch.object(updater, "ROLLOUT_RESULT", result.with_name("rollout.json")),
                    patch.object(updater, "flag_is_enabled", return_value=True),
                    patch.object(updater, "update_once", return_value=current),
                    patch.object(updater, "save_result", side_effect=lambda data, destination=result: destination.write_text(json.dumps(data))),
                    patch.object(updater.subprocess, "run", side_effect=reload_services) as launch,
                ):
                    updater.main(["--once"])
                    self.assertEqual(launch.called, expected)
                    evidence = result.with_name("rollout.json")
                    if expected:
                        saved = json.loads(evidence.read_text())
                        self.assertEqual(saved["revision"], self.TARGET)
                        self.assertEqual(saved["reload_status"], "verified")
                        with patch.object(updater, "update_once", return_value=updater.result_record(
                            "current", "already_up_to_date", self.TARGET, self.TARGET, self.TARGET
                        )):
                            updater.main(["--once"])
                        self.assertEqual(json.loads(evidence.read_text()), saved)
                        self.assertEqual(launch.call_count, 1)
                    else:
                        self.assertFalse(evidence.exists())

    def test_failed_reload_is_retried_three_times_and_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result"
            rollout = path.with_name("rollout")
            statuses = ["updated", "current", "current", "current"]
            records = [updater.result_record(status, "test", self.OLD, self.TARGET, self.TARGET)
                       for status in statuses]
            persist = updater.save_result
            with (
                patch.object(updater, "RESULT", path),
                patch.object(updater, "ROLLOUT_RESULT", rollout),
                patch.object(updater, "flag_is_enabled", return_value=True),
                patch.object(updater, "update_once", side_effect=records),
                patch.object(updater, "save_result", side_effect=lambda data, destination=path: persist(data, destination)),
                patch.object(updater.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as restart,
            ):
                self.assertEqual([updater.main(["--once"]) for _ in statuses], [1, 1, 1, 1])
            self.assertEqual(restart.call_count, 3)
            self.assertEqual(json.loads(rollout.read_bytes())["reload_status"], "unverified")

    def test_dirty_checkout_refused_before_fetch(self):
        result = updater.update_once(git_cmd=self.make_git(dirty=True))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "tracked_changes")

    def test_unknown_origin_refused(self):
        result = updater.update_once(git_cmd=self.make_git(origin="https://example.invalid/x"))
        self.assertEqual(result["reason"], "unexpected_origin")

    def test_diverged_checkout_refused(self):
        result = updater.update_once(git_cmd=self.make_git(diverged=True))
        self.assertEqual(result["reason"], "diverged")

    def test_ci_pending_keeps_source_unchanged(self):
        result = updater.update_once(
            git_cmd=self.make_git(), fetch_ci=lambda sha: self.ci(sha, conclusion="failure")
        )
        self.assertEqual(result["status"], "waiting")
        self.assertEqual(result["reason"], "ci_not_passed")
        self.assertFalse(self.updated)

    def test_untrusted_branch_refused(self):
        result = updater.update_once(git_cmd=self.make_git(branch="feature/test"))
        self.assertEqual(result["reason"], "branch_not_main")

    def test_safe_pull_refusal_not_reported_as_updated(self):
        result = updater.update_once(
            root=Path("/odin-workspace"),
            git_cmd=self.make_git(), fetch_ci=self.ci,
            run_cmd=lambda *args, **kw: SimpleNamespace(returncode=1),
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "safe_pull_refused")

    def test_opt_in_is_private_and_off_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            flag = Path(folder) / "auto-update.enabled"
            self.assertFalse(updater.flag_is_enabled(flag))
            updater.change_flag(True, flag)
            self.assertTrue(updater.flag_is_enabled(flag))
            self.assertEqual(flag.stat().st_mode & 0o077, 0)
            updater.change_flag(False, flag)
            self.assertFalse(updater.flag_is_enabled(flag))

    def test_result_saved_without_prompts_or_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            record = updater.result_record("blocked", "diverged", self.OLD, self.TARGET)
            updater.save_result(record, path)
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertIn('"reason": "diverged"', path.read_text())

    def test_timeout_returns_bounded_failure(self):
        def run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="git", timeout=120)
        outcome = updater.update_once(
            root=Path("/odin-workspace"), git_cmd=self.make_git(),
            fetch_ci=self.ci, run_cmd=run
        )
        self.assertEqual(outcome["status"], "error")
        self.assertEqual(outcome["reason"], "update_check_failed")


if __name__ == "__main__":
    unittest.main()
