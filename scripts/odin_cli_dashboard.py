"""Compact, colorful and read-only Odin status for the Termux terminal.

Local status is free/offline. Public GitHub CI is opt-in and rate-limited
during watch. No models, private credentials, shell evaluation or service
changes are performed by this module. It cannot stream ChatGPT internals.
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
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SERVICES = ("odin-private-mailbox", "odin-git-sync", "odin-task-worker",
            "odin-local-model", "odin-stage5")
SHA = re.compile(r"[0-9a-f]{40}\Z")
RUN = re.compile(r"^run: .*: \(pid ([0-9]{1,9})\) ([0-9]+)s")
GITHUB_URL = ("https://api.github.com/repos/shawnfra2013/Oden2-/"
              "actions/runs?branch=main&per_page=8")
FETCH_INTERVAL = 120
COLORS = {
    "cyan": "\x1b[36m", "green": "\x1b[32m", "yellow": "\x1b[33m",
    "red": "\x1b[31m", "dim": "\x1b[2m", "reset": "\x1b[0m",
}


def safe_text(value: object, limit: int = 70) -> str:
    """No control sequences or newlines from process/network data in the TTY."""
    return "".join(ch for ch in str(value) if ch.isprintable() and ch != "\x1b")[:limit]


def use_color(*, stream=None, env=None) -> bool:
    output = sys.stdout if stream is None else stream
    settings = os.environ if env is None else env
    return ("NO_COLOR" not in settings and settings.get("TERM") != "dumb"
            and bool(getattr(output, "isatty", lambda: False)()))


def paint(value: object, color: str, enabled: bool) -> str:
    label = safe_text(value, 90)
    return COLORS[color] + label + COLORS["reset"] if enabled else label


def command(argv: list[str], timeout: int = 3) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def local_revision(root: Path = ROOT, runner=command) -> str | None:
    result = runner(["git", "-C", str(root), "rev-parse", "HEAD"])
    value = result.stdout.strip() if result and result.returncode == 0 else ""
    return value if SHA.fullmatch(value) else None


def service_state(name: str, *, prefix: Path | None = None,
                  runner=command) -> dict:
    if name not in SERVICES:
        raise ValueError("Unknown Odin service")
    prefix = (Path(os.environ["PREFIX"]) if prefix is None
              and "PREFIX" in os.environ else prefix)
    if prefix is None:
        return {"state": "UNVERIFIED"}
    service = prefix / "var" / "service" / name
    if not service.exists():
        return {"state": "NOT_INSTALLED"}
    result = runner(["sv", "status", str(service)])
    if result is None:
        return {"state": "UNVERIFIED"}
    message = result.stdout.strip()
    match = RUN.match(message)
    if result.returncode == 0 and match:
        return {"state": "RUNNING", "pid": int(match[1]),
                "uptime_s": int(match[2])}
    if message.startswith("down:"):
        return {"state": "STOPPED"}
    return {"state": "UNVERIFIED"}


def queue_depth(root: Path = ROOT) -> dict:
    queue = root / "state" / "task-queue"
    result = {}
    for name in ("pending", "running"):
        folder = queue / name
        if not folder.is_dir() or folder.is_symlink():
            result[name] = None
            continue
        try:
            result[name] = min(sum(p.is_file() and not p.is_symlink()
                                   for p in folder.iterdir()), 10000)
        except OSError:
            result[name] = None
    return result


def mailbox_checkout(*, home: Path | None = None,
                     prefix: Path | None = None) -> str:
    """Reuse preflight's launcher AND PID/cwd check, not a stale ping."""
    from scripts.odin_preflight import private_mailbox_launch_path

    try:
        result = private_mailbox_launch_path(
            home=Path.home() if home is None else home,
            prefix=(Path(os.environ["PREFIX"]) if prefix is None
                    and "PREFIX" in os.environ else prefix))
        return result["status"]
    except (OSError, ValueError, TypeError):
        return "UNVERIFIED"


def local_snapshot(*, root: Path = ROOT, prefix: Path | None = None,
                   home: Path | None = None) -> dict:
    local_home = Path.home() if home is None else home
    observed = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "observed_utc": observed,
        "source_sha": local_revision(root),
        "services": {name: service_state(name, prefix=prefix) for name in SERVICES},
        "mailbox_checkout": mailbox_checkout(home=local_home, prefix=prefix),
        "task_queue": queue_depth(root),
        "offline_profile": (local_home / ".config/odin-offline/enabled").is_file(),
        "physical_phone_verified": False,
    }


def github_ci(fetch=urlopen) -> dict:
    """Untrusted public GitHub source metadata only; no auth or private JSON."""
    request = Request(GITHUB_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Odin-Termux-Source-Monitor",
    })
    try:
        with fetch(request, timeout=5) as response:
            data = json.loads(response.read(80000))
    except (HTTPError, URLError, OSError, ValueError, TypeError, TimeoutError):
        return {"status": "UNVERIFIED", "reason": "github_unavailable"}
    runs = data.get("workflow_runs") if isinstance(data, dict) else None
    if not isinstance(runs, list):
        return {"status": "UNVERIFIED", "reason": "invalid_github_schema"}
    # A workflow can be successful for an obsolete Git SHA. Never label it current.
    candidates = []
    for run in runs[:8]:
        if not isinstance(run, dict) or not SHA.fullmatch(str(run.get("head_sha", ""))):
            continue
        if run.get("name") not in {
            "Odin Checks", "Offline chat browser acceptance",
            "Odin CodeQL Security Scan",
        }:
            continue
        candidates.append({
            "sha": run["head_sha"],
            "name": safe_text(run["name"], 36),
            "status": run.get("status") if run.get("status") in
                {"queued", "in_progress", "completed", "waiting"} else "unknown",
            "conclusion": run.get("conclusion") if run.get("conclusion") in
                {"success", "failure", "cancelled", "timed_out", "skipped"} else None,
        })
    return {"status": "SOURCE_ONLY", "runs": candidates[:4]}


def render(snapshot: dict, github: dict | None = None, *, color: bool = False) -> str:
    lines = [paint("ODIN 2  |  CONTROL TERMINAL", "cyan", color),
             paint("Local read-only view | no model calls", "dim", color),
             "-----------------------------------------"]
    sha = snapshot.get("source_sha")
    lines.append("CHECKOUT   " + (sha[:12] if isinstance(sha, str) and SHA.fullmatch(sha)
                                  else "UNVERIFIED"))
    mailbox = snapshot.get("mailbox_checkout")
    shade = "green" if mailbox == "PASS" else "red" if mailbox == "FAIL" else "yellow"
    lines.append("MAILBOX    " + paint(mailbox, shade, color)
                 + " (launcher + PID/cwd)")
    for name, item in snapshot.get("services", {}).items():
        state = item.get("state", "UNVERIFIED")
        shade = "green" if state == "RUNNING" else "red" if state == "STOPPED" else "yellow"
        detail = (f" pid={item['pid']} up={item['uptime_s']}s"
                  if state == "RUNNING" and "pid" in item else "")
        lines.append(f"{name[:18]:18} " + paint(state, shade, color) + detail)
    q = snapshot.get("task_queue", {})
    lines.append("TASK QUEUE pending={} running={}".format(
        q.get("pending") if q.get("pending") is not None else "?",
        q.get("running") if q.get("running") is not None else "?"))
    lines.append("LOCAL AI   " + ("profile selected (reply unverified)"
                                   if snapshot.get("offline_profile")
                                   else "profile not confirmed"))
    if github is None:
        lines.append("GITHUB CI  not requested (add --github)")
    elif github.get("status") != "SOURCE_ONLY":
        lines.append("GITHUB CI  " + paint("UNVERIFIED", "yellow", color))
    else:
        runs = github.get("runs", [])
        local = snapshot.get("source_sha")
        matches = [run for run in runs if run["sha"] == local]
        if not matches:
            lines.append("GITHUB CI  no matching checkout SHA in recent runs")
        for run in matches[:3]:
            state = run["conclusion"] or run["status"]
            shade = "green" if state == "success" else "red" if state == "failure" else "yellow"
            lines.append("CI {}: {}".format(run["name"][:23], paint(state, shade, color)))
    lines.append(paint("GitHub CI != installed device; phone UNVERIFIED", "dim", color))
    return "\n".join(lines)


def watch(*, root: Path = ROOT, interval: int = 10, github: bool = False,
          iterations: int | None = None, sleeper=time.sleep,
          output=sys.stdout, clock=time.monotonic) -> None:
    if not 5 <= interval <= 60:
        raise ValueError("Refresh must be 5-60 seconds")
    cached = None
    last_github = None
    count = 0
    ansi = use_color(stream=output)
    while iterations is None or count < iterations:
        now = clock()
        if github and (last_github is None or now - last_github >= FETCH_INTERVAL):
            cached = github_ci()
            last_github = now
        body = render(local_snapshot(root=root), cached if github else None, color=ansi)
        if ansi:
            output.write("\x1b[H\x1b[2J")
        output.write(body + "\n")
        output.flush()
        count += 1
        if iterations is None or count < iterations:
            sleeper(interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("status", "watch"), nargs="?", default="status")
    parser.add_argument("--github", action="store_true",
                        help="Opt in to public GitHub source CI polling (120s cache)")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "watch":
        try:
            watch(interval=args.interval, github=args.github)
        except KeyboardInterrupt:
            print("\nOdin monitor stopped.")
        return 0
    snapshot = local_snapshot()
    remote = github_ci() if args.github else None
    print(render(snapshot, remote, color=not args.no_color and use_color()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
