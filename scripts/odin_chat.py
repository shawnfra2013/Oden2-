"""Odin's local persistent AI CLI; not the ChatGPT app conversation.

Run: python -B scripts/odin_chat.py
Or:  python -B scripts/odin_chat.py --once "Hello Odin"
All chat text stays in local SQLite and the selected model provider.
The public GitHub status bridge does not receive conversations.
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "stage5"))

from chat_provider import ask_model, provider_name  # noqa: E402
from conversation_store import ConversationStore  # noqa: E402

STATE = ROOT / "state" / "odin-chat-cli"
SESSION_FILE = STATE / "conversation_id"
DB_FILE = ROOT / "state" / "conversations.db"
ID_RE = re.compile(r"[0-9a-f]{32}\Z")


def load_session(store, session_file=SESSION_FILE):
    try:
        identifier = session_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not ID_RE.fullmatch(identifier):
        raise ValueError("Invalid locally saved conversation ID")
    return identifier if store.exists(identifier) else None


def save_session(identifier, session_file=SESSION_FILE):
    if not ID_RE.fullmatch(identifier):
        raise ValueError("Invalid conversation ID")
    session_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(session_file.parent, 0o700)
    temp = session_file.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        os.chmod(temp, 0o600)
        handle.write(identifier + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(session_file)


def reply(store, question, identifier=None):
    if not isinstance(question, str) or not 0 < len(question.strip()) <= 4000:
        raise ValueError("Enter a question (1-4000 characters)")
    if identifier and not store.exists(identifier):
        raise ValueError("Conversation not found")
    history = store.get_messages(identifier, limit=12) if identifier else None
    answer = ask_model(question, history)
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("AI returned no answer")
    identifier = identifier or store.create()
    store.append_turn(identifier, question, answer)
    return identifier, answer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", metavar="MESSAGE", help="Send one question")
    parser.add_argument("--new", action="store_true", help="Start a fresh chat")
    args = parser.parse_args(argv)

    provider = provider_name()
    store = ConversationStore(DB_FILE)
    identifier = None if args.new else load_session(store)
    print(f"Odin AI CLI | provider={provider} | persistent local chat")
    print("This is an independent AI session, not your live ChatGPT app thread.")

    def send(question, current_id):
        new_id, answer = reply(store, question, current_id)
        save_session(new_id)
        print("Odin:", answer, flush=True)
        return new_id

    if args.once is not None:
        try:
            send(args.once, identifier)
            return 0
        except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
            print("AI request failed:", type(exc).__name__, file=sys.stderr)
            return 1

    print("Commands: :new (new conversation), :status, :quit")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question == ":quit":
            break
        if question == ":new":
            identifier = None
            SESSION_FILE.unlink(missing_ok=True)
            print("Fresh conversation; prior local history preserved.")
            continue
        if question == ":status":
            print(f"Provider: {provider}; conversation: {'active' if identifier else 'new'}")
            continue
        if not question:
            continue
        try:
            identifier = send(question, identifier)
        except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
            print("AI request failed:", type(exc).__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
