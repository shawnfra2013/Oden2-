"""Offline structural checks: no device, model, credentials, or network calls."""
import copy
import json
import unittest
from pathlib import Path

from scripts import check_odin_structure as structure

ROOT = Path(__file__).resolve().parents[1]


class OdinStructureTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT / "config/odin-services.json").read_text())

    def test_repository_matches_declared_source_structure(self):
        self.assertEqual(structure.check(ROOT), [])

    def test_colliding_port_is_rejected(self):
        bad = copy.deepcopy(self.registry)
        bad["listeners"][1]["port"] = bad["listeners"][0]["port"]
        self.assertTrue(any("collision" in e for e in structure.manifest_errors(bad, ROOT)))

    def test_missing_launcher_is_rejected(self):
        bad = copy.deepcopy(self.registry)
        bad["services"][0]["run"] = "services/nonexistent/run"
        self.assertTrue(any("Missing runit" in e for e in structure.manifest_errors(bad, ROOT)))

    def test_draft_tailnet_port_not_falsely_active(self):
        bad = copy.deepcopy(self.registry)
        bad["private_network"]["planned_phone_port_active"] = True
        self.assertTrue(any("Draft phone port" in e for e in structure.manifest_errors(bad, ROOT)))

    def test_retired_hostname_is_rejected_in_live_entrypoint(self):
        self.assertRegex("https://old.vercel.app/", structure.BANNED_HOST)
        self.assertNotRegex((ROOT / "mobile/server.js").read_text(), structure.BANNED_HOST)


if __name__ == "__main__":
    unittest.main()
