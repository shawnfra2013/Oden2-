"""A finite offline practice set. Claim one case and persist the device's own notes."""
import argparse
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

try:
    from .odin_note_check import check
except ImportError:
    from odin_note_check import check

# These disclosed practice items must never be used as a held-out promotion test.
CASES = (
    ("python", "What does [4, 7, 9][-2] evaluate to in Python?", "", "7"),
    ("files", "Which profile is active?", "default=cloud\nactive=local\nbackup=none", "local"),
    ("workflow", "What is the next action?", "If tests fail, inspect. If tests pass, review. Tests failed.", "inspect"),
    ("python", "What does len('é'.encode('utf-8')) evaluate to?", "", "2"),
    ("files", "What is the retry interval in seconds?", "timeout_s=25\nretry_s=12\nlimit=3", "12"),
    ("workflow", "What is the next action?", "Failed checks need diagnosis. Passed checks need review. Checks passed.", "review"),
    ("python", "What does sum([2, 5, 8][1:]) evaluate to?", "", "13"),
    ("files", "Which port is the active port?", "previous_port=8080\nactive_port=18080", "18080"),
    ("workflow", "Which model should be used?", "Use local by default. Cloud needs explicit approval. Approval absent.", "local"),
)


def notes_path():
    return Path.home() / ".local/share/odin-practice/notes.sqlite3"


def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS practice_v1("
               "id TEXT PRIMARY KEY, idx INTEGER UNIQUE NOT NULL, state TEXT NOT NULL, result TEXT)")


def summary(db):
    rows = db.execute("SELECT idx,state FROM practice_v1 ORDER BY idx").fetchall()
    misses = [CASES[i][0] for i, state in rows if state == "miss"]
    repeat = sorted({skill for skill in misses if misses.count(skill) >= 2})
    return {"total": len(CASES), "attempted": len(rows),
            "passed": sum(state == "pass" for _, state in rows),
            "missed": len(misses), "review_skills": repeat,
            "training_decision": "investigate_repeated_errors" if repeat else "keep_current_weights"}


def notebook(path=None):
    path = path or notes_path()
    if not path.is_file():
        return {"notes": [], "total": len(CASES), "training_decision": "keep_current_weights"}
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("SELECT idx,state,result FROM practice_v1 ORDER BY idx").fetchall()
        return {**summary(db), "notes": [json.loads(result) if result else
                {"case": i+1, "state": state} for i, state, result in rows]}


def practice(request_id, *, path=None, assess=check):
    path = path or notes_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(path, timeout=8)) as db:
        db.execute("BEGIN IMMEDIATE")
        initialize(db)
        prior = db.execute("SELECT state,result FROM practice_v1 WHERE id=?", (request_id,)).fetchone()
        if prior:
            return json.loads(prior[1]) if prior[1] else {"state": "already_claimed", "match": False}
        index = db.execute("SELECT COUNT(*) FROM practice_v1").fetchone()[0]
        if index >= len(CASES):
            return {**summary(db), "state": "finished", "match": True}
        db.execute("INSERT INTO practice_v1 VALUES(?,?,'claimed',NULL)", (request_id, index))
        db.commit()
        skill, question, reference, expected = CASES[index]
        past = db.execute("SELECT idx,state FROM practice_v1 WHERE idx < ? ORDER BY idx DESC", (index,))
        last = next((state for i, state in past if CASES[i][0] == skill and state in {"pass", "miss"}), None)
        reminder = ""
        if last == "miss":
            reminder = {"python": "Trace the expression one operation at a time.",
                        "files": "Use the exact field the question asks about.",
                        "workflow": "Match the observed condition to the stated rule."}[skill]
        try:
            outcome = assess(request_id, exercise=(question, (reference + "\n" + reminder).strip(), expected))
            state = ("pass" if outcome["match"] else "miss") if outcome["http_status"] == 200 else "unavailable"
        except (RuntimeError, ValueError, OSError) as exc:
            outcome = {"match": False, "error": type(exc).__name__}
            state = "unavailable"
        result = {**outcome, "state": state, "case": index+1, "skill": skill,
                  "question": question, "reference": reference, "reminder": reminder, "expected": expected,
                  "at": datetime.now(UTC).isoformat()}
        db.execute("UPDATE practice_v1 SET state=? WHERE id=?", (state, request_id))
        result.update(summary(db))
        result["note"] = {"pass": "Matched the answer key on this example.",
                          "miss": "Review the supplied context and compare the answer with the key.",
                          "unavailable": "Check the local service before evaluating the model."}[state]
        db.execute("UPDATE practice_v1 SET result=? WHERE id=?", (json.dumps(result), request_id))
        db.commit()
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--next", action="store_true", help="Run one remaining local example")
    args = parser.parse_args()
    print(json.dumps(practice(secrets.token_hex(16)) if args.next else notebook(), indent=2))
