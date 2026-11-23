"""Release guard test suite: missing CI must never become source release approval."""
import unittest

from scripts import odin_release_guard as guard


class ReleaseGuardTests(unittest.TestCase):
    SHA = "a" * 40

    def test_all_exact_sha_push_checks_pass(self):
        result = guard.evaluate(self.SHA, fetch=self.fetch())
        self.assertEqual(result["source_status"], "PASS")
        self.assertTrue(result["safe_for_source_release"])
        self.assertEqual(result["device_status"], "UNVERIFIED")
        self.assertEqual(result["phone_status"], "UNVERIFIED")

    def fetch(self, *, main=None, omit=(), status=None, event="push", sha=None):
        actual = self.SHA if main is None else main
        matching = self.SHA if sha is None else sha
        runs = [
            {"name": name, "head_sha": matching, "event": event,
             "status": "completed", "conclusion": "success"}
            for name in guard.WORKFLOWS if name not in omit
        ]
        if status:
            for name, values in status.items():
                for run in runs:
                    if run["name"] == name:
                        run.update(values)

        def fake(path):
            if path == "/branches/main":
                return {"commit": {"sha": actual}}
            if path.startswith("/actions/runs?"):
                return {"workflow_runs": runs}
            raise AssertionError("Unexpected API call: " + path)
        return fake

    def test_missing_codeql_is_unverified(self):
        report = guard.evaluate(
            self.SHA, fetch=self.fetch(omit={"Odin CodeQL Security Scan"})
        )
        self.assertEqual(report["source_status"], "UNVERIFIED")
        self.assertFalse(report["safe_for_source_release"])

    def test_running_checks_do_not_pass(self):
        report = guard.evaluate(
            self.SHA,
            fetch=self.fetch(status={"Odin Checks": {"status": "in_progress",
                                                     "conclusion": None}}),
        )
        self.assertEqual(report["source_status"], "UNVERIFIED")
        self.assertFalse(report["safe_for_source_release"])

    def test_failed_check_is_fail(self):
        report = guard.evaluate(
            self.SHA,
            fetch=self.fetch(status={"Odin Checks": {"conclusion": "failure"}}),
        )
        self.assertEqual(report["source_status"], "FAIL")
        self.assertFalse(report["safe_for_source_release"])

    def test_old_main_and_stale_commit_fail(self):
        report = guard.evaluate(self.SHA, fetch=self.fetch(main="b" * 40))
        self.assertEqual(report["source_status"], "FAIL")
        self.assertFalse(report["safe_for_source_release"])
        report = guard.evaluate(self.SHA, fetch=self.fetch(sha="b" * 40))
        self.assertEqual(report["source_status"], "UNVERIFIED")

    def test_pull_request_run_cannot_count_as_main_push(self):
        report = guard.evaluate(self.SHA, fetch=self.fetch(event="pull_request"))
        self.assertEqual(report["source_status"], "UNVERIFIED")

    def test_bad_sha_fails_input_validation(self):
        for value in ("123", "G" * 40, None, 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                guard.evaluate(value, fetch=self.fetch())

    def test_bad_response_never_approves(self):
        for fake in (
            lambda _: {},
            lambda _: (_ for _ in ()).throw(OSError("offline")),
        ):
            report = guard.evaluate(self.SHA, fetch=fake)
            self.assertFalse(report["safe_for_source_release"])
            self.assertNotEqual(report["source_status"], "PASS")


if __name__ == "__main__":
    unittest.main()
