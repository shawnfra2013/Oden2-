#!/usr/bin/env python3
"""Read-only GitHub evidence collector. Never emits private receipt contents."""
import argparse
import datetime as dt
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE_REPO = "shawnfra2013/Oden2-"
PRIVATE_REPO = "shawnfra2013/Odin-private-bridge"
BRANCH = "odin-bridge-outbox"
SHA = re.compile(r"^[0-9a-f]{40}$")
RID = re.compile(r"^[0-9a-fA-F]{32}$")
API = "https://api.github.com/repos/"
REQUIRED_CHECKS = {"Validate Odin Project", "browser", "CodeQL"}
UTC = dt.timezone.utc


def fetch_json(url, token=None):
    """Fixed API hosts/paths only; credentials never appear in URLs or output."""
    if not url.startswith(API) or not any(
        url.startswith(API + repo + "/") for repo in (SOURCE_REPO, PRIVATE_REPO)
    ):
        raise ValueError("GitHub repository API path not allowed")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "odin-evidence-reader"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=15) as response:
        return json.load(response)


def _utc(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0) else None
    except ValueError:
        return None


def check_source(sha, fetch=fetch_json):
    data = fetch(API + SOURCE_REPO + "/commits/" + sha + "/check-runs?per_page=100")
    runs = data.get("check_runs", [])
    status = {}
    for name in REQUIRED_CHECKS:
        matching = [r for r in runs if r.get("name") == name and r.get("head_sha") == sha]
        if len(matching) != 1:
            status[name] = "UNVERIFIED"
        elif matching[0].get("status") != "completed":
            status[name] = "UNVERIFIED"
        elif matching[0].get("conclusion") == "success" and _utc(matching[0].get("completed_at")):
            status[name] = "PASS"
        elif matching[0].get("conclusion") in ("failure", "timed_out", "cancelled", "action_required"):
            status[name] = "FAIL"
        else:
            status[name] = "UNVERIFIED"
    return {"status": "PASS" if all(s == "PASS" for s in status.values()) else
            "FAIL" if "FAIL" in status.values() else "UNVERIFIED", "checks": status}


def check_private_source_receipts(sha, token, fetch=fetch_json):
    """Metadata-only: never return full receipts or URLs to private files."""
    if not token:
        return {"status": "UNVERIFIED", "reason": "private_auth_missing", "matched_count": 0}
    path = API + PRIVATE_REPO + "/contents/bridge/local-source-receipts?ref=" + BRANCH
    try:
        files = fetch(path, token)
    except (HTTPError, URLError, ValueError, OSError):
        return {"status": "UNVERIFIED", "reason": "private_access_failed", "matched_count": 0}
    if not isinstance(files, list):
        return {"status": "UNVERIFIED", "reason": "private_listing_invalid", "matched_count": 0}
    seen = set()
    matched = 0
    conflicting = False
    invalid = False
    for entry in files:
        name = entry.get("name", "")
        if not isinstance(name, str) or not name.endswith(".json") or not RID.fullmatch(name[:-5]):
            invalid = True
            continue
        rid = name[:-5].lower()
        if rid in seen:
            conflicting = True
            continue
        seen.add(rid)
        # Never follow arbitrary API URLs from the listing.
        file_path = API + PRIVATE_REPO + "/contents/bridge/local-source-receipts/" + name + "?ref=" + BRANCH
        try:
            receipt = fetch(file_path, token)
        except (HTTPError, URLError, ValueError, OSError):
            invalid = True
            continue
        if not isinstance(receipt, dict) or not isinstance(receipt.get("id"), str) or receipt["id"].lower() != rid:
            conflicting = True
            continue
        if not SHA.fullmatch(str(receipt.get("source_sha", ""))):
            invalid = True
            continue
        when = _utc(receipt.get("completed_at"))
        if not when:
            invalid = True
            continue
        if (dt.datetime.now(UTC) - when).total_seconds() not in range(0, 86401):
            continue
        if receipt.get("source_sha") == sha and receipt.get("status") in ("complete", "completed", "PASS", "success"):
            matched += 1
    return {"status": "FAIL" if conflicting else "UNVERIFIED",
            "reason": "conflicting_ids" if conflicting else
                      "invalid_metadata" if invalid else "source_only_not_device_proof",
            "matched_count": matched}


def collect(sha, token=None, fetch=fetch_json):
    if not SHA.fullmatch(sha):
        raise ValueError("exact lowercase 40-character SHA required")
    try:
        source = check_source(sha, fetch)
    except (HTTPError, URLError, ValueError, OSError, KeyError, TypeError):
        source = {"status": "UNVERIFIED", "reason": "source_api_unavailable"}
    private = check_private_source_receipts(sha, token, fetch)
    return {"source_sha": sha, "source": source, "local_source_receipts": private,
            "device": "UNVERIFIED", "agent": "UNVERIFIED",
            "memory": "UNVERIFIED", "phone": "UNVERIFIED",
            "note": "Public CI and local-source receipts never certify physical operation"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    try:
        report = collect(args.sha, os.environ.get("ODIN_GITHUB_READ_TOKEN"))
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["source"].get("status") == "PASS" and report["local_source_receipts"]["status"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
