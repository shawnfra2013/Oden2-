"""Odin CLI conversation storage tests; no live inference."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import odin_chat
from stage5.conversation_store import ConversationStore


class OdinCliTests(unittest.TestCase):
    def test_reply_creates_and_reuses_chat(self):
        with tempfile.TemporaryDirectory() as location:
            store = ConversationStore(Path(location) / "chat.db")
            with patch.object(odin_chat, "ask_model", side_effect=["A", "B"]) as model:
                chat_id, first = odin_chat.reply(store, "Hello")
                same_id, second = odin_chat.reply(store, "Follow up", chat_id)
            self.assertEqual((first, second), ("A", "B"))
            self.assertEqual(chat_id, same_id)
            self.assertEqual(
                [m["role"] for m in store.get_messages(chat_id)],
                ["user", "assistant", "user", "assistant"],
            )
            self.assertEqual(model.call_args.args[1][-1]["content"], "A")

    def test_session_pointer_is_local_and_resumable(self):
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            store = ConversationStore(base / "chat.db")
            chat_id = store.create()
            pointer = base / "cli" / "conversation_id"
            odin_chat.save_session(chat_id, pointer)
            self.assertEqual(odin_chat.load_session(store, pointer), chat_id)
            self.assertEqual(pointer.stat().st_mode & 0o777, 0o600)

    def test_invalid_pointer_rejected(self):
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            store = ConversationStore(base / "chat.db")
            pointer = base / "conversation_id"
            pointer.write_text("../somewhere")
            with self.assertRaises(ValueError):
                odin_chat.load_session(store, pointer)


if __name__ == "__main__":
    unittest.main()
