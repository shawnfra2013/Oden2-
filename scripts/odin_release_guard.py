"""Fail-closed, source-only GitHub release readiness check.

Never contacts a device, publishes a release, makes a model call, or writes GitHub.
It checks public source commits and completed GitHub Actions for one exact SHA.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com/repos/shawnfra2013/Oden2-"
SHA = re.compile(r"[0-9a-f]{40}\Z")
WORKFLOWS = (
    "Odin Checks",
    "Offline chat browser acceptance",
    "Odin CodeQL Security Scan",
)


def github_json(path, *, token=None):
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Invalid GitHub API path")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Odin-release-guard",
    }
    key = token if token is not None else os.environ.get("GITHUB_TOKEN")
    if key:
        headers["Authorization"] = "Bearer " + key
    with urlopen(Request(API + path, headers=headers), timeout=12) as response:
        return json.load(response)


def evaluate(expected, *, fetch=github_json):
    """Independently verify branch identity and all required exact-SHA push runs."""
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        raise ValueError("Invalid 40-character source SHA")
    report = {
        "schema": 1,
        "observed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "expected_sha": expected,
        "main_sha": None,
        "source_status": "UNVERIFIED",
        "checks": {name: "UNVERIFIED" for name in WORKFLOWS},
        "safe_for_source_release": False,
        "device_status": "UNVERIFIED",
        "phone_status": "UNVERIFIED",
        "reason": "",
    }
    try:
        main = fetch("/branches/main")
        actual = main.get("commit", {}).get("sha")
        if not isinstance(actual, str) or not SHA.fullmatch(actual):
            raise ValueError("Invalid current main SHA")
        report["main_sha"] = actual
        if actual != expected:
            report["source_status"] = "FAIL"
            report["reason"] = "Requested SHA is not current main"
            return report
        data = fetch("/actions/runs?branch=main&event=push&per_page=100")
        runs = data.get("workflow_runs", [])
        if not isinstance(runs, list):
            raise ValueError("Invalid workflow run list")
        matches = {}
        for item in runs:
            if not isinstance(item, dict):
                continue
            if item.get("head_sha") != expected or item.get("event") != "push":
                continue
            name = item.get("name")
            if name not in WORKFLOWS:
                continue
            if name not in matches:
                matches[name] = item
        for name in WORKFLOWS:
            item = matches.get(name)
            if item is None or item.get("status") != "completed":
                continue
            report["checks"][name] = (
                "PASS" if item.get("conclusion") == "success" else "FAIL"
            )
        states = set(report["checks"].values())
        report["source_status"] = (
            "FAIL" if "FAIL" in states else
            "PASS" if states == {"PASS"} else "UNVERIFIED"
        )
        report["reason"] = (
            "All exact-SHA source gates passed" if report["source_status"] == "PASS"
            else "Some exact-SHA source checks failed or are unavailable"
        )
        report["safe_for_source_release"] = report["source_status"] == "PASS"
    except (OSError, ValueError, TypeError, KeyError, TimeoutError) as exc:
        report["reason"] = "GitHub verification unavailable: " + type(exc).__name__
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--json-path", type=Path)
    args = parser.parse_args(argv)
    status = evaluate(args.expected_sha)
    serialized = json.dumps(status, indent=2, sort_keys=True) + "\n"
    print(serialized, end="")
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(serialized, encoding="utf-8")
    return 0 if status["safe_for_source_release"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
