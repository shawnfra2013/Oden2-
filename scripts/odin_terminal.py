"""Read-only colorful Odin status. Local runit plus rate-limited PUBLIC GitHub CI."""
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
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from scripts.odin_preflight import private_mailbox_launch_path

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/repos/shawnfra2013/Oden2-"
NAMES = ("odin-private-mailbox", "odin-git-sync", "odin-task-worker")
SHA = re.compile(r"[0-9a-f]{40}\Z")
PID = re.compile(r"\(pid ([0-9]{1,9})\)")
PALETTES = {"neon": (36, 32, 33, 31), "ocean": (34, 36, 33, 31),
            "ember": (33, 32, 93, 31), "mono": (0, 0, 0, 0)}


def safe(value, limit=60):
    return " ".join("".join(" " if ord(c) < 32 or ord(c) == 127 else c
                            for c in str(value)).split())[:limit]


def command(argv, cwd=None):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=3, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def local(root=ROOT, prefix=None):
    prefix = os.environ.get("PREFIX") if prefix is None else prefix
    sha = command(["git", "rev-parse", "HEAD"], cwd=root)
    sha = sha if isinstance(sha, str) and SHA.fullmatch(sha) else None
    services = {}
    for name in NAMES:
        path = Path(prefix) / "var/service" / name if prefix else None
        if path is None:
            state, pid = "UNVERIFIED", None
        elif not path.exists() and not path.is_symlink():
            state, pid = "NOT_INSTALLED", None
        else:
            answer = command(["sv", "status", str(path)])
            match = PID.search(answer or "")
            state = ("RUNNING" if answer and answer.startswith("run:") and match
                     else "DOWN" if answer and answer.startswith("down:")
                     else "UNVERIFIED")
            pid = int(match[1]) if state == "RUNNING" else None
        services[name] = {"state": state, "pid": pid}
    if prefix:
        mailbox = private_mailbox_launch_path(prefix=Path(prefix), home=Path.home())["status"]
    else:
        mailbox = "UNVERIFIED"
    queue = {}
    for part in ("pending", "running"):
        path = root / "state/task-queue" / part
        try:
            queue[part] = (min(sum(1 for f in path.iterdir() if f.is_file()), 9999)
                           if path.is_dir() and not path.is_symlink() else None)
        except OSError:
            queue[part] = None
    trace = None
    path = root / "state/odin-traces/events.jsonl"
    try:
        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 2097152:
            with path.open("rb") as stream:
                stream.seek(max(0, path.stat().st_size - 16384))
                raw = stream.read()
            if raw.endswith(b"\n") and raw.splitlines():
                row = json.loads(raw.splitlines()[-1])
                if row.get("status") in ("complete", "expired", "rejected_or_failed"):
                    trace = {"action": safe(row.get("action")),
                             "status": row["status"],
                             "checked_at": safe(row.get("checked_at"))}
    except (OSError, ValueError, TypeError, UnicodeError, AttributeError):
        pass
    return {"checked_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "local_sha": sha, "services": services, "mailbox_cwd": mailbox,
            "queue": queue, "local_trace_only": trace,
            "agent_attached": False, "iphone_verified": False}


def public_get(path):
    if not path.startswith("/") or ".." in path or "://" in path:
        return None
    request = Request(API + path, headers={"User-Agent": "Odin-Terminal-ReadOnly",
                                           "Accept": "application/vnd.github+json"})
    try:
        with urlopen(request, timeout=4) as reply:
            raw = reply.read(262145)
        return json.loads(raw) if len(raw) <= 262144 else None
    except (OSError, HTTPError, URLError, TimeoutError, ValueError):
        return None


def github(get=public_get, issue=None):
    result = {"main_sha": None, "ci": "UNVERIFIED", "runs": [],
              "recent": [], "source": "public_only"}
    branch = get("/branches/main")
    commit = branch.get("commit") if isinstance(branch, dict) else None
    sha = commit.get("sha") if isinstance(commit, dict) else None
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        return result
    result["main_sha"] = sha
    actions = get("/actions/runs?branch=main&per_page=20")
    names = ("Odin Checks", "Offline chat browser acceptance",
             "Odin CodeQL Security Scan")
    runs = actions.get("workflow_runs") if isinstance(actions, dict) else None
    if isinstance(runs, list):
        for name in names:
            current = next((x for x in runs if isinstance(x, dict)
                            and x.get("head_sha") == sha and x.get("name") == name), None)
            if current is None:
                state = "UNVERIFIED"
            elif current.get("conclusion") == "success" and current.get("status") == "completed":
                state = "PASS"
            elif current.get("conclusion") in ("failure", "timed_out", "action_required"):
                state = "FAIL"
            elif current.get("status") in ("queued", "in_progress", "waiting"):
                state = "RUNNING"
            else:
                state = "UNVERIFIED"
            result["runs"].append({"name": name, "state": state})
        states = [r["state"] for r in result["runs"]]
        result["ci"] = ("FAIL" if "FAIL" in states else
                        "PASS" if all(x == "PASS" for x in states) else
                        "RUNNING" if "RUNNING" in states else "UNVERIFIED")
    items = get("/issues?state=open&sort=updated&per_page=6")
    if isinstance(items, list):
        for x in items[:6]:
            if isinstance(x, dict) and type(x.get("number")) is int:
                result["recent"].append({"number": x["number"],
                                         "kind": "PR" if x.get("pull_request") else "Issue",
                                         "title": safe(x.get("title"), 48)})
    if issue and not any(x["number"] == issue for x in result["recent"]):
        focused = get("/issues/" + str(issue))
        if isinstance(focused, dict) and focused.get("number") == issue:
            result["recent"].insert(0, {"number": issue, "kind": "Issue",
                                         "title": safe(focused.get("title"), 48)})
    return result


def render(device, remote=None, width=76, theme="neon", color=False, issue=None):
    width = max(54, min(105, width))
    palette = PALETTES[theme] if color else (0, 0, 0, 0)
    span = width - 4

    def row(name, value, tone=0):
        value = safe(value, 32)
        name = safe(name, max(0, span - len(value) - 1))
        painted = ("\x1b[" + str(palette[tone]) + "m" + value + "\x1b[0m"
                   if palette[tone] else value)
        return "│ " + name + " " * (span - len(name) - len(value)) + painted + " │"

    def section(name):
        item = " " + name + " "
        return "├" + "─" + item + "─" * (width - len(item) - 3) + "┤"

    local_sha = device.get("local_sha")
    remote_sha = remote.get("main_sha") if remote else None
    result = ["╭" + "─" * (width - 2) + "╮",
              row("ODIN 2 / TERMINAL", "READ ONLY"), section("SOURCE + TERMUX"),
              row("Local checkout", local_sha[:12] if local_sha else "UNKNOWN"),
              row("GitHub main", remote_sha[:12] if remote_sha else "UNKNOWN"),
              row("Exact revision", "PASS" if local_sha and local_sha == remote_sha else
                  "FAIL" if local_sha and remote_sha else "UNVERIFIED",
                  1 if local_sha and local_sha == remote_sha else 2)]
    for name in NAMES:
        entry = device.get("services", {}).get(name, {})
        state = entry.get("state", "UNVERIFIED")
        pid = entry.get("pid")
        result.append(row(name, state + ((" pid " + str(pid)) if pid else ""),
                          1 if state == "RUNNING" else 3 if state == "DOWN" else 2))
    cwd = device.get("mailbox_cwd", "UNVERIFIED")
    result.append(row("Mailbox launcher / process cwd", cwd,
                      1 if cwd == "PASS" else 3 if cwd == "FAIL" else 2))
    queue = device.get("queue", {})
    result.append(row("Tasks queued / running", " / ".join(
        str(queue.get(x)) if queue.get(x) is not None else "?"
        for x in ("pending", "running"))))
    trace = device.get("local_trace_only")
    result.append(row("Last local trace", (trace["action"] + " / " + trace["status"])
                      if trace else "NOT OBSERVED"))
    result.append(section("GITHUB ACTIVITY"))
    ci = remote.get("ci") if remote else "OFFLINE"
    result.append(row("Exact-main CI", ci, 1 if ci == "PASS" else 2))
    for run in (remote.get("runs", []) if remote else []):
        result.append(row(run["name"], run["state"], 1 if run["state"] == "PASS" else 2))
    recent = remote.get("recent", []) if remote else []
    if issue:
        recent = sorted(recent, key=lambda x: 0 if x["number"] == issue else 1)
    for item in recent[:3]:
        result.append(row(item["kind"] + " #" + str(item["number"]), item["title"]))
    if not recent:
        result.append(row("Recent issues / PRs", "NOT AVAILABLE"))
    result += [section("PROOF BOUNDARY"),
               row("ChatGPT tool stream", "NOT CONNECTED", 2),
               row("Agent action / phone acceptance", "UNVERIFIED", 2),
               row("Snapshot UTC", device.get("checked_utc", "UNKNOWN")),
               "╰" + "─" * (width - 2) + "╯"]
    return "\n".join(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--theme", choices=tuple(PALETTES), default="neon")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--github-interval", type=int, default=300)
    parser.add_argument("--issue", type=int)
    args = parser.parse_args(argv)
    if (not 2 <= args.interval <= 60 or not 300 <= args.github_interval <= 3600
            or args.watch and args.json or
            args.issue is not None and not 1 <= args.issue <= 100000):
        parser.error("Invalid interval, issue or output combination")
    if args.watch and not sys.stdout.isatty():
        print("Watch requires an interactive terminal.", file=sys.stderr)
        return 2
    color = (sys.stdout.isatty() and not args.plain and args.theme != "mono"
             and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb")
    remote, last = None, None
    if args.watch:
        print("\x1b[?25l", end="", flush=True)
    try:
        while True:
            now = time.monotonic()
            if not args.offline and (last is None or now - last >= args.github_interval):
                remote = github(issue=args.issue)
                last = now
            device = local()
            if args.json:
                print(json.dumps({"device": device, "github": remote,
                                  "chatgpt_live_stream": False}, sort_keys=True))
            else:
                value = render(device, remote,
                               width=shutil.get_terminal_size((76, 24)).columns,
                               theme=args.theme, color=color, issue=args.issue)
                print(("\x1b[2J\x1b[H" if args.watch else "") + value, flush=True)
            if not args.watch:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        if args.watch:
            print("\x1b[0m\x1b[?25h", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
