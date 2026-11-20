"""Fixed private diagnostic. The on-device key file enables this capability."""
import json
import os
import re
import sqlite3
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

# Support the runit launcher's direct script entry point.
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stage5.openai_adapter import MODEL_PATTERN, ProviderError, request_answer

CONFIG = Path.home() / ".config" / "odin-private-inference"
MODEL = "gpt-4.1-mini"
DAILY_LIMIT = 2


def load_key():
    with os.fdopen(os.open(CONFIG / "key", os.O_RDONLY | os.O_NOFOLLOW), "r") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("Private key file required")
        key = handle.read(1025).strip()
        if not key or len(key) > 1024 or not key.isascii() or any(c.isspace() for c in key):
            raise ValueError("Invalid key file")
        return key


def failure(reason):
    return {"provider": "openai", "requested_model": MODEL, "match": False, "reason": reason}


def probe(request_id):
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise ValueError("Invalid probe ID")
    from stage5.offline_profile import enabled
    if enabled():
        return failure("local_only_profile")
    try:
        key = load_key()
    except (OSError, ValueError):
        return failure("local_opt_in_required")

    # Shared across service checkout upgrades. Commit before HTTPS so an
    # interrupted call cannot spend twice, even when its outcome is unknown.
    try:
        return run_attempt(request_id, key)
    except sqlite3.Error:
        return failure("local_journal_error")


def run_attempt(request_id, key):
    db = sqlite3.connect(CONFIG / "attempts.sqlite3", timeout=5)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, day TEXT, result TEXT)")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT result FROM attempts WHERE id=?", (request_id,)).fetchone()
        if row:
            return json.loads(row[0]) if row[0] else failure("prior_attempt_outcome_unknown")
        day = datetime.now(UTC).date().isoformat()
        count = db.execute("SELECT count(*) FROM attempts WHERE day=?", (day,)).fetchone()[0]
        if count >= DAILY_LIMIT:
            return failure("daily_limit")
        db.execute("INSERT INTO attempts VALUES (?, ?, NULL)", (request_id, day))
        db.commit()
        prompt = f"Token: {request_id}. Multiply 7 by 9. Reply only with ODIN-<token>-<product>."
        try:
            answer, data = request_answer(prompt, None, key=key, model=MODEL, max_tokens=96)
            response_id, model = data.get("id"), data.get("model")
            if not (isinstance(response_id, str) and re.fullmatch(r"resp_[A-Za-z0-9_-]{1,160}", response_id)
                    and isinstance(model, str) and MODEL_PATTERN.fullmatch(model)
                    and data.get("status") == "completed"):
                result = failure("incomplete_provider_evidence")
            else:
                result = {"provider": "openai", "requested_model": MODEL, "model": model,
                          "response_id": response_id, "match": answer == f"ODIN-{request_id}-63"}
                if not result["match"]:
                    result["reason"] = "answer_mismatch"
        except ProviderError as exc:
            result = failure(exc.reason)
        except (OSError, ValueError, RuntimeError):
            result = failure("provider_request_failed")
        db.execute("UPDATE attempts SET result=? WHERE id=?", (json.dumps(result), request_id))
        db.commit()
        return result
    finally:
        db.close()
