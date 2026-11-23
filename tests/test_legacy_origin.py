import os
import unittest
from unittest.mock import patch

from scripts import odin_relay_client as relay


class DirectMailboxTests(unittest.TestCase):
    @patch.dict(os.environ, {"ODIN_LEGACY_RELAY_ORIGIN": "https://legacy.invalid"})
    def test_retired_cli_never_reads_credentials_or_polls(self):
        with patch.object(relay, "read_token") as token, patch.object(relay, "poll_once") as poll:
            relay.main(["--once"])
            token.assert_not_called()
            poll.assert_not_called()

    @patch.dict(os.environ, {"ODIN_LEGACY_RELAY_ORIGIN": "http://legacy.invalid/"})
    def test_requires_explicit_https_origin(self):
        with self.assertRaises(ValueError):
            relay.legacy_origin()
