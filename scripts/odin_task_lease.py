"""Offline-safe, exclusive source-task leases (issue #97).

No network, inference, shell, branch checkout, merge or device actions.
The caller must independently verify the observed GitHub base SHA and scope.
"""
from __future__ import annotations

import json
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath

DEFAULT_DB = Path(__file__).resolve().parents[1] / "state" / "task-leases" / "leases.sqlite3"
SHA = re.compile(r"[0-9a-f]{40}\Z")
LEASE_ID = re.compile(r"[0-9a-f]{32}\Z")
ACTOR = re.compile(r"[a-zA-Z0-9_.-]{1,60}\Z")
BRANCH = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._/-]{0,120}\Z")


def _safe_paths(paths: object) -> list[str]:
    if not isinstance(paths, list) or not 1 <= len(paths) <= 50:
        raise ValueError("Invalid lease path list")
    for value in paths:
        if (not isinstance(value, str) or not 1 <= len(value) <= 180
                or "\\" in value or "*" in value or "?" in value
                or value.startswith("/") or not PurePosixPath(value).parts
                or any(part in {"", ".", ".."} for part in value.split("/"))
                or str(PurePosixPath(value)) != value):
            raise ValueError("Invalid lease path")
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate lease path")
    return sorted(paths)


def _utc_now(now: datetime | None = None) -> datetime:
    instant = datetime.now(UTC) if now is None else now
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("Lease time must be UTC")
    return instant


def _stamp(instant: datetime) -> str:
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _connect(db_path: Path):
    if db_path.is_symlink() or db_path.parent.is_symlink():
        raise ValueError("Unsafe lease database path")
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    db_path.chmod(0o600)
    return db


def _prepare(db):
    db.execute(
        "CREATE TABLE IF NOT EXISTS leases("
        "id TEXT PRIMARY KEY, issue INTEGER NOT NULL, owner TEXT NOT NULL,"
        "branch TEXT NOT NULL, base_sha TEXT NOT NULL, paths TEXT NOT NULL,"
        "created_at TEXT NOT NULL, expires_at TEXT NOT NULL,"
        "state TEXT NOT NULL CHECK(state IN ('active','expired','released')))"
    )


def acquire(
    db_path: Path, *, issue: int, owner: str, branch: str,
    base_sha: str, observed_sha: str, paths: list[str],
    ttl_seconds: int = 900, now: datetime | None = None, lease_id: str | None = None,
) -> dict:
    """Atomically claim one issue and non-overlapping source paths.

    The caller supplies an independently checked observed_sha. A local claim
    is not external proof of GitHub ownership, authorization, or task execution.
    """
    if type(issue) is not int or issue < 1:
        raise ValueError("Invalid issue")
    if not isinstance(owner, str) or not ACTOR.fullmatch(owner):
        raise ValueError("Invalid worker")
    if (not isinstance(branch, str) or not BRANCH.fullmatch(branch)
            or ".." in branch or branch.endswith("/") or branch.endswith(".lock")):
        raise ValueError("Invalid branch")
    if (not isinstance(base_sha, str) or not SHA.fullmatch(base_sha)
            or not isinstance(observed_sha, str) or not SHA.fullmatch(observed_sha)):
        raise ValueError("Invalid revision")
    if type(ttl_seconds) is not int or not 60 <= ttl_seconds <= 3600:
        raise ValueError("Invalid lease duration")
    selected = _safe_paths(paths)
    instant = _utc_now(now)
    if base_sha != observed_sha:
        return {"status": "STALE_BASE", "issue": issue, "lease_acquired": False}
    ident = secrets.token_hex(16) if lease_id is None else lease_id
    if not isinstance(ident, str) or not LEASE_ID.fullmatch(ident):
        raise ValueError("Invalid lease ID")
    expires = _stamp(instant + timedelta(seconds=ttl_seconds))
    started = _stamp(instant)
    with _connect(Path(db_path)) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            _prepare(db)
            # Keep expired records for audit: never erase another worker's work.
            db.execute(
                "UPDATE leases SET state='expired' WHERE state='active' AND expires_at<=?",
                (started,),
            )
            rows = db.execute(
                "SELECT id,issue,branch,paths FROM leases WHERE state='active'"
            ).fetchall()
            conflicts = [
                row[0] for row in rows
                if row[1] == issue or row[2] == branch
                or set(json.loads(row[3])) & set(selected)
            ]
            if conflicts:
                db.execute("ROLLBACK")
                return {
                    "status": "CONFLICT", "issue": issue,
                    "lease_acquired": False, "active_conflict_count": len(conflicts),
                }
            db.execute(
                "INSERT INTO leases VALUES(?,?,?,?,?,?,?,?,?)",
                (ident, issue, owner, branch, base_sha, json.dumps(selected),
                 started, expires, "active"),
            )
            db.execute("COMMIT")
        except sqlite3.Error:
            db.execute("ROLLBACK")
            raise
    return {
        "status": "ACQUIRED", "lease_id": ident, "issue": issue,
        "branch": branch, "base_sha": base_sha, "created_at": started,
        "expires_at": expires, "lease_acquired": True,
        "external_evidence_verified": False,
    }


def release(db_path: Path, lease_id: str, owner: str) -> dict:
    """Release only the original worker's lease; retain immutable ID/history."""
    if not isinstance(lease_id, str) or not LEASE_ID.fullmatch(lease_id):
        raise ValueError("Invalid lease ID")
    if not isinstance(owner, str) or not ACTOR.fullmatch(owner):
        raise ValueError("Invalid worker")
    db_path = Path(db_path)
    if not db_path.is_file() or db_path.is_symlink():
        return {"status": "MISSING", "released": False}
    with _connect(db_path) as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT owner,state FROM leases WHERE id=?", (lease_id,)
            ).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                return {"status": "MISSING", "released": False}
            if row[0] != owner:
                db.execute("ROLLBACK")
                return {"status": "OWNER_MISMATCH", "released": False}
            if row[1] != "active":
                db.execute("ROLLBACK")
                return {"status": "ALREADY_INACTIVE", "released": False}
            db.execute("UPDATE leases SET state='released' WHERE id=?", (lease_id,))
            db.execute("COMMIT")
        except sqlite3.Error:
            db.execute("ROLLBACK")
            raise
    return {"status": "RELEASED", "released": True, "lease_id": lease_id}


def local_summary(db_path: Path = DEFAULT_DB) -> dict:
    """Read-only count; no lease identities, credentials, or command output."""
    db_path = Path(db_path)
    if not db_path.is_file() or db_path.is_symlink():
        return {"active": 0, "expired": 0, "released": 0}
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as db:
        rows = db.execute("SELECT state,COUNT(*) FROM leases GROUP BY state").fetchall()
    return {name: dict(rows).get(name, 0) for name in ("active", "expired", "released")}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status",))
    args = parser.parse_args()
    if args.action == "status":
        print(json.dumps(local_summary(), sort_keys=True))
