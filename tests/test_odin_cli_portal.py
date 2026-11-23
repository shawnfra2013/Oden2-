"""AI portal tests (never invoke live models, cloud APIs or runit)."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_cli_portal as portal


class PortalTests(unittest.TestCase):
    def test_status_routes_to_monitor_not_original_ai(self):
        with patch.object(portal.subprocess, "call", return_value=0) as invoke:
            self.assertEqual(portal.main(["status"]), 0)
        args = invoke.call_args.args[0]
        self.assertIn("bin/odin", args[0])
        self.assertNotIn(".local/bin/ai", args[0])

    def test_missing_original_ai_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(portal.legacy([], binary=Path(temp) / "missing"), 2)

    def test_cloud_requires_confirmation_and_offline_lock_is_authoritative(self):
        with patch("stage5.offline_profile.enabled", return_value=False), \
             patch.dict("os.environ", {"GROQ_API_KEY": "fixture"}, clear=True), \
             patch.object(portal.subprocess, "call") as invoke:
            self.assertEqual(portal.model_chat("groq"), 2)
            invoke.assert_not_called()
        with patch("stage5.offline_profile.enabled", return_value=True), \
             patch.object(portal.subprocess, "call") as invoke:
            self.assertEqual(portal.model_chat("groq", consent=True), 2)
            invoke.assert_not_called()

    def test_local_profile_missing_never_falls_back_online(self):
        with patch("stage5.offline_profile.enabled", return_value=False), \
             patch.object(portal.subprocess, "call") as invoke:
            self.assertEqual(portal.model_chat("local"), 2)
            invoke.assert_not_called()

    def test_service_start_blocks_unsafe_name_and_confirmation(self):
        with patch.object(portal.subprocess, "run") as invoke:
            self.assertEqual(portal.service_up("odin-private-mailbox", confirm=""), 2)
            self.assertEqual(portal.service_up("rm", confirm="START-ODIN-SERVICE"), 2)
            invoke.assert_not_called()

    def test_help_and_unknown_are_side_effect_free(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(portal.main(["menu"]), 0)
        self.assertEqual(portal.main(["not-a-command"]), 2)


if __name__ == "__main__":
    unittest.main()
