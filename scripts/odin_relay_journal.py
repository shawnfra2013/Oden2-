"""Private relay execution claims, delivery outbox, and recurring failure cases."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta


@contextmanager
def journal(state):
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = state / "relay-journal.sqlite3"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    db = sqlite3.connect(path)
    try:
        with db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, action TEXT NOT NULL, phase TEXT NOT NULL, body TEXT);
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY, request_id TEXT, action TEXT, phase TEXT,
                    reason TEXT, at TEXT, case_id INTEGER, attempt INTEGER);
                CREATE TABLE IF NOT EXISTS deliveries(id TEXT PRIMARY KEY, attempts INTEGER DEFAULT 0);
                CREATE INDEX IF NOT EXISTS failure_signature
                    ON failures(action,phase,reason,at);
                CREATE TABLE IF NOT EXISTS investigations (
                    id INTEGER PRIMARY KEY, action TEXT, phase TEXT, reason TEXT,
                    opened TEXT, latest TEXT, state TEXT DEFAULT 'open');
                CREATE UNIQUE INDEX IF NOT EXISTS one_open_case
                    ON investigations(action,phase,reason) WHERE state='open';
            """)
            yield db
    finally:
        db.close()


def fail(db, mid, action, phase, reason, attempt=None):
    moment = datetime.now(UTC)
    at = moment.isoformat()
    cutoff = (moment - timedelta(hours=1)).isoformat()
    signature = (action, phase, reason)
    if attempt is None:
        prior, = db.execute("SELECT count(*) FROM failures WHERE request_id IS ? AND action=? AND phase=?",
                            (mid, action, phase)).fetchone()
        attempt = prior + 1
    db.execute("INSERT INTO failures(request_id,action,phase,reason,at,attempt) VALUES(?,?,?,?,?,?)",
               (mid, *signature, at, attempt))
    count, = db.execute("SELECT count(*) FROM failures WHERE action=? AND phase=? AND reason=? AND at>=?",
                        (*signature, cutoff)).fetchone()
    if count >= 2 or reason == "outcome_unknown":
        db.execute("INSERT OR IGNORE INTO investigations(action,phase,reason,opened,latest) VALUES(?,?,?,?,?)",
                   (*signature, at, at))
    row = db.execute("SELECT id FROM investigations WHERE action=? AND phase=? AND reason=? AND state='open'",
                     signature).fetchone()
    if row:
        db.execute("UPDATE investigations SET latest=? WHERE id=?", (at, row[0]))
        db.execute("UPDATE failures SET case_id=? WHERE action=? AND phase=? AND reason=? AND at>=? AND case_id IS NULL",
                   (row[0], *signature, cutoff))


def claim(state, mid, action):
    with journal(state) as db:
        if db.execute("INSERT OR IGNORE INTO jobs VALUES(?,?,'running',NULL)", (mid, action)).rowcount:
            return True
        phase, = db.execute("SELECT phase FROM jobs WHERE id=?", (mid,)).fetchone()
        if phase == "running":
            interrupted(db, mid, action)
        return False


def interrupted(db, mid, action):
    fail(db, mid, action, "execute", "outcome_unknown")
    body = {"type":"receipt", "for":mid, "state":"failed", "reason":"task_failed"}
    db.execute("UPDATE jobs SET phase='pending',body=? WHERE id=?", (json.dumps(body), mid))


def save_result(state, mid, body):
    with journal(state) as db:
        db.execute("UPDATE jobs SET phase='pending', body=? WHERE id=?", (json.dumps(body), mid))


def failure(state, mid, action, phase, reason):
    with journal(state) as db:
        fail(db, mid, action, phase, reason)


def deliver(state, token, mid, send):
    with journal(state) as db:
        phase, raw, action = db.execute("SELECT phase,body,action FROM jobs WHERE id=?", (mid,)).fetchone()
    if phase == "sent":
        return True
    if phase != "pending":
        return False
    with journal(state) as db:
        db.execute("INSERT OR IGNORE INTO deliveries VALUES(?,0)", (mid,))
        db.execute("UPDATE deliveries SET attempts=attempts+1 WHERE id=?", (mid,))
        attempt, = db.execute("SELECT attempts FROM deliveries WHERE id=?", (mid,)).fetchone()
    try:
        send(token, json.loads(raw))
    except (RuntimeError, OSError, ValueError) as error:
        if getattr(error, "code", None) != 409 or json.loads(raw)["type"] != "reply":
            with journal(state) as db:
                fail(db, mid, action, "publish_result", getattr(error, "reason_code", type(error).__name__), attempt)
            return False
    with journal(state) as db:
        db.execute("UPDATE jobs SET phase='sent', body=NULL WHERE id=?", (mid,))
    return True


def resend(state, token, send):
    if not (state / "relay-journal.sqlite3").is_file():
        return
    with journal(state) as db:
        for mid, action in db.execute("SELECT id,action FROM jobs WHERE phase='running'").fetchall():
            interrupted(db, mid, action)
        ids = db.execute("SELECT id FROM jobs WHERE phase='pending' ORDER BY rowid").fetchall()
    for (mid,) in ids:
        deliver(state, token, mid, send)

def report(state):
    if not (state / "relay-journal.sqlite3").is_file():
        return []
    with journal(state) as db:
        db.row_factory = sqlite3.Row
        cases = db.execute("SELECT * FROM investigations ORDER BY id DESC LIMIT 30").fetchall()
        result = []
        for case in cases:
            count, = db.execute("SELECT count(*) FROM failures WHERE case_id=?", (case["id"],)).fetchone()
            events = db.execute("SELECT request_id,phase,reason,at,attempt FROM failures WHERE case_id=? "
                                "ORDER BY id DESC LIMIT 20", (case["id"],)).fetchall()
            result.append({**dict(case), "failure_count": count, "recent_events": [dict(e) for e in events]})
        return result
