import os
import unittest
from unittest.mock import patch

from scripts import odin_relay_client as relay
from scripts import odin_wake as wake


class DirectMailboxTests(unittest.TestCase):
    @patch.dict(os.environ, {"ODIN_LEGACY_RELAY_ORIGIN": ""})
    def test_unconfigured_services_wait_without_reading_credentials(self):
        with patch.object(wake, "read_token") as token, patch.object(wake.time, "sleep") as sleep:
            wake.wait_for_work("bridge", 60)
            sleep.assert_called_once_with(60)
            token.assert_not_called()
        with patch.object(relay, "read_token") as token:
            relay.main(["--once"])
            token.assert_not_called()

    @patch.dict(os.environ, {"ODIN_LEGACY_RELAY_ORIGIN": "http://legacy.invalid/"})
    def test_requires_explicit_https_origin(self):
        with self.assertRaises(ValueError):
            relay.legacy_origin()
