"""Issue #97: exclusive task leases, conflicts, expiry and concurrency."""
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

from scripts import odin_task_lease as leases


class TaskLeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "task-leases" / "leases.sqlite3"
        self.now = datetime(2026, 11, 23, 7, 20, tzinfo=UTC)
        self.params = dict(
            issue=97, owner="worker-a", branch="feature/lease-a",
            base_sha="a" * 40, observed_sha="a" * 40,
            paths=["scripts/odin_task_lease.py"], now=self.now,
            lease_id="1" * 32,
        )

    def claim(self, **changes):
        return leases.acquire(self.db, **{**self.params, **changes})

    def test_acquire_records_permanent_unique_id_and_source_only(self):
        outcome = self.claim()
        self.assertEqual(outcome["status"], "ACQUIRED")
        self.assertEqual(outcome["lease_id"], "1" * 32)
        self.assertFalse(outcome["external_evidence_verified"])
        self.assertEqual(leases.local_summary(self.db)["active"], 1)
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)

    def test_duplicate_issue_and_same_path_conflict(self):
        self.claim()
        self.assertEqual(self.claim(lease_id="2" * 32)["status"], "CONFLICT")
        self.assertEqual(
            self.claim(issue=98, branch="feature/lease-b", lease_id="3" * 32)["status"],
            "CONFLICT",
        )
        self.assertEqual(leases.local_summary(self.db)["active"], 1)

    def test_branch_conflict_and_independent_work(self):
        self.claim()
        self.assertEqual(
            self.claim(issue=99, paths=["tests/test_safe.py"], lease_id="4" * 32)["status"],
            "CONFLICT",
        )
        other = self.claim(
            issue=99, branch="feature/unrelated", paths=["tests/test_safe.py"],
            lease_id="4" * 32,
        )
        self.assertEqual(other["status"], "ACQUIRED")
        self.assertEqual(leases.local_summary(self.db)["active"], 2)

    def test_parent_directory_claim_blocks_child_path(self):
        self.claim(paths=["scripts"])
        result = self.claim(
            issue=98, branch="feature/subdir", lease_id="8" * 32,
            paths=["scripts/new_module.py"],
        )
        self.assertEqual(result["status"], "CONFLICT")

    def test_child_claim_blocks_parent_directory(self):
        self.claim(paths=["scripts/odin_task_lease.py"])
        result = self.claim(
            issue=98, branch="feature/parent", lease_id="9" * 32,
            paths=["scripts"],
        )
        self.assertEqual(result["status"], "CONFLICT")

    def test_stale_sha_fails_without_creating_database(self):
        outcome = self.claim(observed_sha="b" * 40)
        self.assertEqual(outcome["status"], "STALE_BASE")
        self.assertFalse(self.db.exists())

    def test_expiry_preserves_history_and_releases_scope(self):
        first = self.claim(ttl_seconds=60)
        second = self.claim(
            lease_id="2" * 32, now=self.now + timedelta(seconds=60),
        )
        self.assertEqual(first["status"], "ACQUIRED")
        self.assertEqual(second["status"], "ACQUIRED")
        self.assertEqual(leases.local_summary(self.db)["expired"], 1)
        self.assertEqual(leases.local_summary(self.db)["active"], 1)
        with sqlite3.connect(self.db) as db:
            states = dict(db.execute("SELECT id,state FROM leases").fetchall())
        self.assertEqual(states["1" * 32], "expired")
        self.assertEqual(states["2" * 32], "active")

    def test_release_wrong_owner_denied_and_idempotent(self):
        self.claim()
        self.assertEqual(leases.release(self.db, "1" * 32, "other")["status"], "OWNER_MISMATCH")
        self.assertEqual(leases.local_summary(self.db)["active"], 1)
        self.assertEqual(leases.release(self.db, "1" * 32, "worker-a")["status"], "RELEASED")
        self.assertEqual(leases.release(self.db, "1" * 32, "worker-a")["status"], "ALREADY_INACTIVE")
        self.assertEqual(leases.local_summary(self.db)["released"], 1)

    def test_immutable_id_cannot_be_reused_after_release(self):
        self.claim()
        leases.release(self.db, "1" * 32, "worker-a")
        with self.assertRaises(sqlite3.IntegrityError):
            self.claim(issue=99, branch="feature/new", lease_id="1" * 32)

    def test_concurrent_claims_have_single_winner(self):
        barrier = Barrier(2)

        def attempt(i):
            barrier.wait(timeout=5)
            return self.claim(
                owner=f"worker-{i}", branch=f"feature/{i}", lease_id=f"{i:032x}",
            )["status"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, (1, 2)))
        self.assertCountEqual(outcomes, ["ACQUIRED", "CONFLICT"])
        self.assertEqual(leases.local_summary(self.db)["active"], 1)

    def test_reject_unsafe_paths_and_invalid_fields(self):
        for path in ("../secret", "/etc/passwd", "scripts/../secret", "a/*.py",
                     "scripts//file.py", "a\\b", "dir/./file"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.claim(paths=[path])
        for change in ({"issue": True}, {"ttl_seconds": 3601},
                       {"branch": "feature/../bad"}, {"owner": "bad owner"},
                       {"lease_id": "../../bad"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.claim(**change)
        self.assertFalse(self.db.exists())

    def test_readonly_summary_is_empty_before_any_claim(self):
        self.assertEqual(leases.local_summary(self.db),
                         {"active": 0, "expired": 0, "released": 0})


if __name__ == "__main__":
    unittest.main()
