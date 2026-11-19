"""Offline contract tests for Odin's CI-gated source updater."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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
        self.assertIn("restart_not_automatic", result["reason"])

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
            git_cmd=self.make_git(), fetch_ci=lambda: self.ci(conclusion="failure")
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
