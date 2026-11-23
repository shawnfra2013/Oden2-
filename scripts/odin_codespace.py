"""Opt-in Codespaces source command runner with local, non-secret receipts.

Not a device shell, private-mailbox receiver, deployment agent or model call.
Run inside an authenticated Codespace using VS Code Tasks or its terminal.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "state" / "codespace-receipts"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def sha_at(root: Path = ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and SHA_RE.fullmatch(sha) else None


def tool_version(argv: list[str]) -> bool:
    try:
        result = subprocess.run(argv, capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def status(root: Path = ROOT) -> dict:
    """Source environment status only; never imply device connectivity."""
    return {
        "schema": 1,
        "scope": "codespace_source_only",
        "checked_at": utc_now(),
        "source_sha": sha_at(root),
        "codespace_present": os.environ.get("CODESPACES") == "true",
        "python_ready": tool_version([sys.executable, "--version"]),
        "node_ready": tool_version(["node", "--version"]),
        "git_ready": tool_version(["git", "--version"]),
        "device_connection": "not_checked",
        "tailscale_connection": "not_checked",
    }


def check_commands(root: Path = ROOT) -> list[tuple[str, list[str]]]:
    ruff = root / ".venv" / "bin" / "ruff"
    ruff_exe = str(ruff) if ruff.is_file() else (shutil.which("ruff") or "ruff")
    browser_tests = sorted((root / "mobile" / "tests").glob("*.test.js"))
    return [
        ("documentation", [sys.executable, "-B", "scripts/check_active_docs.py"]),
        ("structure", [sys.executable, "-B", "scripts/check_odin_structure.py"]),
        ("python_tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py", "-q"]),
        ("workstation_tests", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "stage5", "-p", "test_*.py", "-q"]),
        ("browser_tests", ["node", "--test", *[str(p.relative_to(root)) for p in browser_tests]]),
        ("ruff", [ruff_exe, "check", "."]),
        ("preflight", [sys.executable, "-B", "scripts/odin_preflight.py", "--mode", "source"]),
    ]


def execute_check(name: str, argv: list[str], root: Path = ROOT) -> dict:
    """No shell interpretation or private terminal logs in the JSON receipt."""
    began = time.monotonic()
    try:
        result = subprocess.run(
            argv, cwd=root, text=True, capture_output=True, check=False,
            timeout=240, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        code = result.returncode
        if code:
            print(f"{name} failed (exit {code})", file=sys.stderr)
            for line in result.stderr.splitlines()[-12:]:
                print(line, file=sys.stderr)
    except subprocess.TimeoutExpired:
        code = 124
        print(f"{name} timed out", file=sys.stderr)
    except OSError as exc:
        code = 127
        print(f"{name} could not start: {type(exc).__name__}", file=sys.stderr)
    return {
        "name": name,
        "status": "PASS" if code == 0 else "FAIL",
        "exit_code": code,
        "duration_ms": int((time.monotonic() - began) * 1000),
    }


def run_tests(root: Path = ROOT) -> dict:
    started = utc_now()
    results = [execute_check(name, argv, root) for name, argv in check_commands(root)]
    return {
        "schema": 1,
        "scope": "codespace_source_only",
        "id": uuid.uuid4().hex,
        "started_at": started,
        "completed_at": utc_now(),
        "source_sha": sha_at(root),
        "status": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL",
        "checks": results,
        "device_connection": "not_checked",
        "phone_connection": "not_checked",
    }


def save_receipt(receipt: dict, directory: Path = RECEIPTS) -> Path:
    """Local, gitignored receipt; never publish it to public GitHub."""
    if not re.fullmatch(r"[0-9a-f]{32}", receipt.get("id", "")):
        raise ValueError("Invalid receipt ID")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (receipt["id"] + ".json")
    with path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, sort_keys=True, indent=2)
        handle.write("\n")
    path.chmod(0o600)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "test"))
    args = parser.parse_args(argv)
    if args.action == "status":
        print(json.dumps(status(), indent=2, sort_keys=True))
        return 0
    result = run_tests()
    location = save_receipt(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Local evidence: {location}")
    print("GitHub Actions and private device receipts are separate proof channels.")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
