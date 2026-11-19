"""SQLite storage for completed browser chat turns."""

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4


class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id),
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_by_conversation
                    ON messages(conversation_id, id);
            """)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create(self):
        conversation_id = uuid4().hex
        with closing(self._connect()) as connection, connection:
            connection.execute("INSERT INTO conversations(id) VALUES (?)", (conversation_id,))
        return conversation_id

    def exists(self, conversation_id):
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,),
            ).fetchone()
            return row is not None

    def append_turn(self, conversation_id, question, answer):
        with closing(self._connect()) as connection, connection:
            connection.executemany(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                [(conversation_id, "user", question), (conversation_id, "assistant", answer)],
            )

    def get_messages(self, conversation_id, limit=-1):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            )
            return [{"role": role, "content": content} for role, content in reversed(rows.fetchall())]
