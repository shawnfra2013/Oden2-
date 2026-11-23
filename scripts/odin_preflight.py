"""Read-only source/device preflight; no paid model, restart, or GitHub write.

PASS is an observed check, FAIL is a demonstrated problem, and UNVERIFIED
means evidence is missing. This report never claims iPhone cellular acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"[0-9a-f]{40}\Z")
STATES = {"PASS", "FAIL", "UNVERIFIED"}


def record(name: str, status: str, detail: str, *, required: bool = False) -> dict:
    if status not in STATES:
        raise ValueError("Invalid preflight status")
    return {"check": name, "status": status, "required": required, "detail": detail}


def run_command(argv: list[str], timeout: int = 5) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            argv, capture_output=True, text=True, check=False, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def repo_revision(root: Path = ROOT, runner=run_command) -> dict:
    result = runner(["git", "-C", str(root), "rev-parse", "HEAD"])
    if result is None or result.returncode:
        return record("source_sha", "UNVERIFIED", "Cannot read local Git revision", required=True)
    sha = result.stdout.strip()
    if not SHA.fullmatch(sha):
        return record("source_sha", "FAIL", "Git returned an invalid revision", required=True)
    return record("source_sha", "PASS", f"Checkout revision {sha}", required=True)


def static_checks(root: Path = ROOT) -> list[dict]:
    try:
        if __package__:
            from . import check_active_docs, check_odin_structure
        else:
            import check_active_docs
            import check_odin_structure
        doc_issues = check_active_docs.check(root)
        structure_issues = check_odin_structure.check(root)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        return [record("source_validation", "FAIL",
                       f"Static validation crashed: {type(exc).__name__}", required=True)]
    result = [
        record("active_documentation", "FAIL" if doc_issues else "PASS",
               "; ".join(doc_issues[:8]) if doc_issues else "Canonical docs and archive rules match",
               required=True),
        record("source_structure", "FAIL" if structure_issues else "PASS",
               "; ".join(structure_issues[:8]) if structure_issues else
               "JSON, file paths, entrypoints and default port registry match",
               required=True),
    ]
    bridge = root / "scripts/odin_github_bridge.py"
    mobile = root / "mobile/api/encrypted-chat.js"
    try:
        bridge_text = bridge.read_text(encoding="utf-8")
        mobile_text = mobile.read_text(encoding="utf-8")
    except OSError:
        result.append(record("private_mailbox_contract", "FAIL",
                             "Missing an active mailbox implementation", required=True))
        return result
    required_bridge = (
        'INBOX_BRANCH = "odin-bridge-inbox"',
        'OUTBOX_BRANCH = "odin-bridge-outbox"',
        '"encrypted_chat"',
        'parser.add_argument("--private-mailbox"',
    )
    required_mobile = (
        '"odin-bridge-inbox"', '"odin-bridge-outbox"',
        'ODIN_PRIVATE_MAILBOX_TOKEN', '"/api/encrypted-chat"',
    )
    # The route is registered by mobile/server.js, not in the API module.
    server_text = (root / "mobile/server.js").read_text(encoding="utf-8")
    mismatches = [item for item in required_bridge if item not in bridge_text]
    mismatches += [item for item in required_mobile[:3] if item not in mobile_text]
    if '"encrypted-chat"' not in server_text:
        mismatches.append("mobile encrypted chat route")
    result.append(record("private_mailbox_contract", "FAIL" if mismatches else "PASS",
                         "Missing or mismatched: " + ", ".join(mismatches) if mismatches
                         else "Private inbox/outbox and encrypted route source wiring agree",
                         required=True))
    return result


def service_status(name: str, *, prefix: Path | None, runner=run_command) -> dict:
    required = name in {"odin-private-mailbox", "odin-git-sync"}
    if prefix is None:
        return record("service_" + name, "UNVERIFIED",
                      "No Termux PREFIX; supervisor not inspected", required=required)
    service = prefix / "var/service" / name
    if not service.exists() and not service.is_symlink():
        return record("service_" + name, "FAIL" if required else "UNVERIFIED",
                      "Service launcher not installed on this device", required=required)
    if shutil.which("sv") is None:
        return record("service_" + name, "UNVERIFIED",
                      "runit 'sv' command unavailable", required=required)
    proc = runner(["sv", "status", str(service)], timeout=5)
    if proc is None:
        return record("service_" + name, "UNVERIFIED",
                      "Supervisor status timed out or could not run", required=required)
    text = proc.stdout.strip()
    if proc.returncode == 0 and text.startswith("run:"):
        return record("service_" + name, "PASS", "runit reports a running service",
                      required=required)
    if text.startswith("down:"):
        return record("service_" + name, "FAIL" if required else "UNVERIFIED",
                      "runit reports service down", required=required)
    return record("service_" + name, "UNVERIFIED",
                  "Unrecognized supervisor response (not promoted to PASS)", required=required)



def private_mailbox_launch_path(
    *, prefix: Path | None, home: Path, proc_root: Path = Path("/proc"),
    runner=run_command,
) -> dict:
    """Read-only: verify both runit launcher and live process use canonical Odin.

    This catches the case where GitHub/~/odin-workspace is updated, but runit
    continues executing an older checkout under a temporary test directory.
    No service restart, process signal, or command taken from the launcher.
    """
    label = "private_mailbox_runtime_checkout"
    if prefix is None:
        return record(label, "UNVERIFIED", "Termux service root unavailable", required=True)
    service = prefix / "var/service/odin-private-mailbox"
    launcher = service / "run"
    try:
        source = launcher.read_text(encoding="utf-8")
    except OSError:
        return record(label, "UNVERIFIED", "Cannot inspect mailbox launcher", required=True)
    if len(source) > 8192:
        return record(label, "FAIL", "Unexpectedly large mailbox launcher", required=True)
    expected = (home / "odin-workspace").resolve()
    targets = []
    for line in source.splitlines():
        if not re.match(r"^\s*cd\s+", line):
            continue
        try:
            fields = shlex.split(line, comments=True)
        except ValueError:
            return record(label, "UNVERIFIED", "Cannot parse mailbox launcher directory", required=True)
        if len(fields) != 2 or fields[0] != "cd":
            return record(label, "UNVERIFIED", "Unrecognized mailbox launcher directory", required=True)
        target_text = fields[1]
        if target_text == "$HOME":
            target_text = str(home)
        elif target_text.startswith("$HOME/"):
            target_text = str(home / target_text[6:])
        target = Path(target_text)
        if not target.is_absolute():
            return record(label, "UNVERIFIED", "Relative mailbox launcher directory", required=True)
        targets.append(target.resolve())
    if len(targets) != 1:
        return record(label, "UNVERIFIED", "Mailbox launcher directory not uniquely identified",
                      required=True)
    if targets[0] != expected:
        return record(label, "FAIL", "Mailbox launcher targets a noncanonical checkout",
                      required=True)
    result = runner(["sv", "status", str(service)], timeout=5)
    if result is None or result.returncode:
        return record(label, "UNVERIFIED", "Cannot obtain running mailbox PID", required=True)
    match = re.search(r"\(pid ([0-9]{1,9})\)", result.stdout)
    if not result.stdout.startswith("run:") or match is None:
        return record(label, "UNVERIFIED", "Mailbox service is not confirmed running",
                      required=True)
    try:
        observed = (proc_root / match[1] / "cwd").resolve(strict=True)
    except OSError:
        return record(label, "UNVERIFIED", "Cannot inspect live mailbox process directory",
                      required=True)
    if observed != expected:
        return record(label, "FAIL", "Running mailbox process uses a noncanonical checkout",
                      required=True)
    return record(label, "PASS", "Launcher and running mailbox use canonical checkout",
                  required=True)


def workstation_status(opener=urlopen) -> dict:
    try:
        with opener("http://127.0.0.1:8765/api/health", timeout=3) as response:
            if response.status != 200:
                return record("local_workstation_http", "FAIL", "Health route returned non-200")
            data = json.loads(response.read(8192))
        if data.get("status") != "ready":
            return record("local_workstation_http", "FAIL", "Workstation is not ready")
        return record("local_workstation_http", "PASS",
                      "Local workstation health HTTP 200; model inference not tested")
    except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError):
        return record("local_workstation_http", "UNVERIFIED",
                      "Local health endpoint unavailable; does not establish live model")


def local_model_status(home: Path, connector=socket.create_connection) -> dict:
    marker = home / ".config/odin-offline/enabled"
    if not marker.is_file():
        return record("offline_model_tcp", "UNVERIFIED",
                      "Local-only profile not enabled; no model request performed")
    try:
        connection = connector(("127.0.0.1", 18080), timeout=3)
        connection.close()
        return record("offline_model_tcp", "PASS",
                      "Local model TCP port accepts connections; inference unverified")
    except OSError:
        return record("offline_model_tcp", "FAIL",
                      "Local-only profile enabled but model port 18080 unavailable", required=True)


def private_network_status(runner=run_command) -> dict:
    if shutil.which("tailscale") is None:
        return record("tailscale_status", "UNVERIFIED",
                      "No Tailscale CLI; Android VPN/app may still exist")
    proc = runner(["tailscale", "status", "--json"], timeout=5)
    if proc is None or proc.returncode:
        return record("tailscale_status", "UNVERIFIED",
                      "Tailscale CLI did not return a usable status")
    try:
        state = json.loads(proc.stdout).get("BackendState")
    except (ValueError, TypeError, AttributeError):
        return record("tailscale_status", "UNVERIFIED", "Unrecognized Tailscale status JSON")
    return record("tailscale_status", "PASS" if state == "Running" else "UNVERIFIED",
                  "Tailnet CLI running; HTTPS Serve and iPhone still unverified"
                  if state == "Running" else "Tailnet CLI not connected")


def device_checks(prefix: Path | None = None, home: Path | None = None) -> list[dict]:
    root = prefix if prefix is not None else (
        Path(os.environ["PREFIX"]) if os.environ.get("PREFIX") else None
    )
    user_home = home or Path.home()
    checks = [
        service_status(name, prefix=root)
        for name in ("odin-private-mailbox", "odin-git-sync",
                     "odin-task-worker", "odin-stage5")
    ]
    checks.append(private_mailbox_launch_path(prefix=root, home=user_home))
    checks.extend((
        workstation_status(),
        local_model_status(user_home),
        private_network_status(),
        record("device_checkout_matches_main", "UNVERIFIED",
               "Local source SHA does not prove latest GitHub main or a service reload",
               required=True),
        record("model_inference", "UNVERIFIED",
               "No model call is made during preflight; requires separately approved test"),
        record("tailscale_https", "UNVERIFIED",
               "HTTPS Serve origin, TLS and access policy require device/iPhone proof",
               required=True),
        record("iphone_cellular", "UNVERIFIED",
               "Real iPhone Wi-Fi-off encrypted chat and Home Screen acceptance not tested",
               required=True),
    ))
    return checks


def build_report(mode: str, root: Path = ROOT) -> dict:
    checks = [repo_revision(root), *static_checks(root)]
    if mode == "device":
        checks += device_checks()
    else:
        checks.extend((
            record("physical_odin", "UNVERIFIED",
                   "Source CI cannot see actual supervised services or bound sockets"),
            record("tailscale_https", "UNVERIFIED",
                   "Source CI cannot verify private HTTPS or iPhone enrollment"),
            record("iphone_cellular", "UNVERIFIED",
                   "Source CI cannot validate a real cellular iPhone"),
        ))
    failures = sum(item["status"] == "FAIL" for item in checks)
    unknowns = sum(item["status"] == "UNVERIFIED" for item in checks)
    return {
        "schema_version": 1, "mode": mode,
        "observed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "FAIL" if failures else "UNVERIFIED" if unknowns else "PASS",
        "release_approved": False,
        "summary": {"pass": len(checks) - failures - unknowns,
                    "fail": failures, "unverified": unknowns},
        "checks": checks,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("source", "device"), default="source")
    parser.add_argument("--json-path", type=Path)
    parser.add_argument("--strict", action="store_true",
                        help="Fail if any required check is not PASS, including device/phone")
    options = parser.parse_args(argv)
    report = build_report(options.mode)
    for item in report["checks"]:
        print(f"{item['status']:10} {item['check']}: {item['detail']}")
    print("Summary:", json.dumps(report["summary"], sort_keys=True))
    print("Release approval: BLOCKED (real device/phone acceptance is separate)")
    if options.json_path is not None:
        options.json_path.parent.mkdir(parents=True, exist_ok=True)
        options.json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["summary"]["fail"]:
        return 1
    if options.strict and any(x["required"] and x["status"] != "PASS"
                              for x in report["checks"]):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
