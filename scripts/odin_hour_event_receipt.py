"""Redacted, immutable GitHub PR event evidence for ODIN-HOUR reviews.

Run only inside a read-only GitHub Actions job. Captures event-payload head SHA,
not a current, potentially changed head fetched later. Does not issue comments,
read private mail, execute PR code, call a model, or start a Work task.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from datetime import UTC, datetime
from pathlib import Path

REPO = "shawnfra2013/Oden2-"
SHA = re.compile(r"[0-9a-f]{40}\Z")
ACTIONS = frozenset({"opened", "synchronize", "reopened", "ready_for_review", "review_requested"})
MAX_EVENT_BYTES = 512000


def capture(event: object, *, run_id: int, attempt: int = 1,
            now: datetime | None = None) -> dict:
    """Return metadata only, with no PR description, comments, or credentials."""
    if not isinstance(event, dict):
        raise ValueError("Invalid GitHub event body")
    if type(run_id) is not int or not 1 <= run_id <= 10**16:
        raise ValueError("Invalid Actions run ID")
    if type(attempt) is not int or not 1 <= attempt <= 100:
        raise ValueError("Invalid Actions attempt")
    if event.get("action") not in ACTIONS:
        raise ValueError("Unsupported PR event")
    pr = event.get("pull_request")
    repository = event.get("repository")
    if not isinstance(pr, dict) or not isinstance(repository, dict):
        raise ValueError("Missing PR or repository")
    if repository.get("full_name") != REPO:
        raise ValueError("Unexpected event repository")
    title = pr.get("title")
    if not isinstance(title, str) or not title.startswith("[ODIN-HOUR]"):
        raise ValueError("Not a marked ODIN-HOUR pull request")
    number = pr.get("number")
    if type(number) is not int or number < 1 or event.get("number") != number:
        raise ValueError("Invalid PR number")
    head, base = pr.get("head"), pr.get("base")
    if not isinstance(head, dict) or not isinstance(base, dict):
        raise ValueError("Missing PR revisions")
    head_repo = head.get("repo")
    if not isinstance(head_repo, dict) or head_repo.get("full_name") != REPO:
        raise ValueError("Cross-repository PR is not eligible")
    head_sha, base_sha = head.get("sha"), base.get("sha")
    if (not isinstance(head_sha, str) or not SHA.fullmatch(head_sha)
            or not isinstance(base_sha, str) or not SHA.fullmatch(base_sha)):
        raise ValueError("Invalid event-time revisions")
    if "after" in event and event["after"] != head_sha:
        raise ValueError("Inconsistent synchronize event SHA")
    observed = datetime.now(UTC) if now is None else now
    if observed.tzinfo is None or observed.utcoffset().total_seconds() != 0:
        raise ValueError("Capture time must be UTC")
    return {
        "schema": 1, "scope": "github_pr_event_metadata",
        "repository": REPO, "pr_number": number,
        "event_action": event["action"], "event_head_sha": head_sha,
        "event_base_sha": base_sha, "actions_run_id": run_id,
        "run_attempt": attempt,
        "captured_at": observed.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "evidence_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
        "head_sha_from_original_github_event": True,
        "work_delivery_head_sha_verified": False,
        "device_action_verified": False,
        "raw_event_stored": False,
    }


def read_event(path: Path) -> object:
    if path.is_symlink():
        raise ValueError("Symlinked GitHub event path")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_EVENT_BYTES:
            raise ValueError("Unsafe or oversized GitHub event")
        raw = os.read(descriptor, MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            raise ValueError("Oversized GitHub event")
    finally:
        os.close(descriptor)
    return json.loads(raw)


def save_receipt(path: Path, record: dict) -> None:
    """Exclusive write prevents a retry from replacing prior event evidence."""
    if path.is_symlink():
        raise ValueError("Unsafe receipt location")
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(encoded) > 3000 or not path.parent.is_dir():
        raise ValueError("Unsafe event receipt")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(encoded)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    try:
        record = capture(read_event(args.event_file),
                         run_id=args.run_id, attempt=args.attempt)
        save_receipt(args.output, record)
    except (OSError, ValueError, TypeError) as exc:
        print("EVENT_RECEIPT_BLOCKED:", type(exc).__name__)
        return 2
    print(json.dumps({
        "status": "RECORDED", "pr_number": record["pr_number"],
        "event_head_sha": record["event_head_sha"],
        "run_id": record["actions_run_id"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
