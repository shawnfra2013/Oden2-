"""Read-only integrity check of Odin's generated project-memory index.

Does not read private mail, mutate the database, or claim device verification.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from scripts import odin_project_memory as memory


def audit(root: Path = memory.ROOT, db_path: Path | None = None) -> dict:
    root = Path(root)
    documents, fingerprint = memory._read_documents(root)
    revision = memory._revision(root)
    index = memory._db_path(root, db_path)
    findings = []
    if (index.is_symlink() or index.parent.is_symlink()
            or index.parent.parent.is_symlink()):
        findings.append("unsafe_index_path")
    elif not index.is_file():
        findings.append("missing_index")
    else:
        try:
            with closing(sqlite3.connect(f"file:{index}?mode=ro", uri=True)) as db:
                integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    findings.append("sqlite_integrity_failed")
                meta_rows = db.execute("SELECT key,value FROM meta").fetchall()
                meta = dict(meta_rows)
                if len(meta) != len(meta_rows):
                    findings.append("duplicate_metadata_keys")
                if meta.get("schema") != "1":
                    findings.append("unexpected_schema")
                if meta.get("content_sha256") != fingerprint:
                    findings.append("stale_document_fingerprint")
                if meta.get("local_git_sha") != revision:
                    findings.append("stale_git_revision")
                rows = db.execute("SELECT path,heading,body FROM snippets").fetchall()
                allowed = {name for name, _ in documents}
                if any(path not in allowed for path, _, _ in rows):
                    findings.append("unapproved_source_path")
                if len(rows) != len(set(rows)):
                    findings.append("duplicate_snippets")
                expected = [(name, heading, body)
                            for name, content in documents
                            for heading, body in memory._parts(content)]
                if rows != expected:
                    findings.append("index_content_mismatch")
        except sqlite3.DatabaseError:
            findings.append("unreadable_index")
    return {
        "status": "PASS" if not findings else "FAIL",
        "findings": sorted(set(findings)),
        "local_source_sha": revision,
        "document_count": len(documents),
        "device_verified": False,
        "private_content_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=memory.ROOT)
    args = parser.parse_args()
    try:
        result = audit(args.root)
    except (OSError, ValueError, UnicodeError, sqlite3.Error) as exc:
        result = {"status": "UNVERIFIED", "error_type": type(exc).__name__,
                  "device_verified": False, "private_content_included": False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
