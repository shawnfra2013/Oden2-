import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import odin_worker as worker
from scripts.odin_worker_probe import probe


class WorkerProbeTests(unittest.TestCase):
    def test_queued_offline_processed_by_separate_worker_and_verified_after_exit(self):
        import os
        with tempfile.TemporaryDirectory() as home:
            root = Path(home) / "odin-workspace"
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            request = "abc123" * 5 + "dd"
            self.assertIsNone(probe(root, request))
            self.assertIsNone(probe(root, request))
            subprocess.run([sys.executable, worker.__file__, "--once"], check=True,
                           env={**os.environ, "HOME": home}, timeout=15)
            self.assertEqual(probe(root, request), {"verified": True})
            done = root / "state/task-queue/done"
            (done / (request[:12] + ".log")).write_text("tampered")
            with self.assertRaises(ValueError):
                probe(root, request)
            self.assertEqual(len(list(done.glob("*.json"))), 1)
            self.assertEqual(json.loads(next(done.glob("*.json")).read_text())["status"], "complete")
