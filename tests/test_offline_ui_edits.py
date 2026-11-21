import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import odin_ui_edits as edits


class OfflineEditsTests(unittest.TestCase):
    def test_offline_approval_then_reconnect_and_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "work"
            remote = Path(tmp) / "remote.git"
            root.mkdir()
            edits.git(root, "init", "-b", "main")
            settings = {"accent": "original", "size": "standard", "heading": ""}
            (root / "mobile").mkdir()
            (root / edits.FILE).write_text(json.dumps(settings))
            edits.git(root, "add", edits.FILE)
            edits.git(root, "-c", "user.name=Test", "-c", "user.email=test@localhost", "commit", "-m", "Baseline")
            base = edits.git(root, "rev-parse", "HEAD")
            edits.git(root, "remote", "add", "origin", str(remote))
            before = edits.current(root)
            custom = dict(settings, heading="Offline chat", accent="teal")
            queued = edits.approve(custom, before["version"], root)
            self.assertEqual(edits.current(root)["settings"], custom)
            self.assertEqual(edits.git(root, "status", "--porcelain"), "")
            with self.assertRaises(ValueError):
                edits.approve(settings, before["version"], root)
            with self.assertRaises(RuntimeError):
                edits.sync(root, allowed={str(remote)})
            self.assertEqual(edits.current(root)["pending"], 1)
            subprocess.run(["git", "init", "--bare", str(remote)], capture_output=True, check=True)
            edits.git(root, "push", "origin", "main")
            edits.sync(root, allowed={str(remote)})
            edits.sync(root, allowed={str(remote)})
            self.assertEqual(edits.current(root)["pending"], 0)
            self.assertEqual(edits.git(remote, "rev-parse", queued["branch"]), queued["latest"])
            self.assertEqual(edits.read_at(remote, queued["branch"]), custom)
            self.assertEqual(edits.git(remote, "rev-parse", "main"), base)
