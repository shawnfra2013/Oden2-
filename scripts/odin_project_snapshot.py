"""Read-only public GitHub source status and handoff; no private mailbox reads."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.github.com/repos/shawnfra2013/Oden2-"
SHA = re.compile(r"^[0-9a-f]{40}$")
ISSUE_URL = "https://github.com/shawnfra2013/Oden2-/issues"


def fetch_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Odin-public-project-snapshot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API + "/"):
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(url, headers=headers), timeout=10) as response:
        return json.load(response)


def collect(fetch=fetch_json, now=None) -> dict:
    observed = now or datetime.now(UTC)
    state = {
        "observed_at": observed.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "main_sha": None, "source_ci": "unverified", "issues": [], "errors": [],
        "device": "not checked: private mailbox excluded from public artifacts",
        "phone": "not verified by source CI; real cellular test required",
    }
    try:
        branch = fetch(API + "/branches/main")
        value = branch.get("commit", {}).get("sha")
        if not isinstance(value, str) or not SHA.fullmatch(value):
            raise ValueError("unexpected main SHA")
        state["main_sha"] = value
    except (ValueError, TypeError, KeyError, OSError, TimeoutError) as exc:
        state["errors"].append("main unavailable: " + type(exc).__name__)
    if state["main_sha"]:
        try:
            runs = fetch(API + "/actions/runs?branch=main&per_page=40").get("workflow_runs", [])
            matches = [r for r in runs if r.get("head_sha") == state["main_sha"]
                       and r.get("event") == "push" and r.get("name") == "Odin Checks"]
            if matches:
                latest = sorted(matches, key=lambda r: r.get("created_at") or "", reverse=True)[0]
                conclusion = latest.get("conclusion")
                state["source_ci"] = (
                    "passed exact main SHA" if latest.get("status") == "completed"
                    and conclusion == "success"
                    else "not passed: " + str(conclusion or latest.get("status") or "unknown")
                )
            else:
                state["source_ci"] = "no matching completed push check found"
        except (ValueError, TypeError, KeyError, OSError, TimeoutError) as exc:
            state["errors"].append("CI unavailable: " + type(exc).__name__)
    try:
        issues = fetch(API + "/issues?state=open&per_page=100")
        if not isinstance(issues, list):
            raise ValueError("unexpected issue response")
        for entry in issues:
            if "pull_request" in entry:
                continue
            number = entry.get("number")
            title = entry.get("title")
            if isinstance(number, int) and isinstance(title, str):
                state["issues"].append({"number": number, "title": title[:140]})
    except (ValueError, TypeError, KeyError, OSError, TimeoutError) as exc:
        state["errors"].append("issues unavailable: " + type(exc).__name__)
    return state


def render_status(state: dict) -> str:
    sha = state["main_sha"] or "unavailable"
    issues = state["issues"]
    lines = [
        "# Odin public project status — time-stamped snapshot", "",
        f"Observed (UTC): **{state['observed_at']}**", "",
        "- GitHub main SHA: " + chr(96) + sha + chr(96),
        f"- Source CI: **{state['source_ci']}**",
        f"- Physical Odin: **{state['device']}**",
        f"- iPhone viewer: **{state['phone']}**",
        f"- Open issues reported: **{len(issues)}**",
    ]
    lines += ["", "## Open task links", ""]
    for issue in issues:
        label = issue["title"].replace("\n", " ").replace("]", "")
        lines.append(f"- [#{issue['number']} — {label}]({ISSUE_URL}/{issue['number']})")
    if not issues:
        lines.append("No issue data was returned; an empty result is not proof of completion.")
    if state["errors"]:
        lines += ["", "## Data unavailable", ""]
        lines += ["- " + item for item in state["errors"]]
    lines += ["", "Source checks do not verify installed code, a private device response, Tailscale, or cellular chat.",
              "See docs/RELEASE_GATES.md and docs/ODIN_RUNTIME.md.", ""]
    return "\n".join(lines)


def render_handoff(state: dict) -> str:
    sha = state["main_sha"] or "unavailable"
    lines = [
        "# Odin session handoff — generated public checkpoint", "",
        f"Generated (UTC): **{state['observed_at']}**", "",
        "- Last observed public main SHA: " + chr(96) + sha + chr(96),
        f"- Source checks on that SHA: {state['source_ci']}",
        "- Private Odin receipt: not checked in public artifact; submit a fresh private request to verify.",
        "- Tailscale route: not confirmed by this artifact.",
        "- iPhone cellular viewer: not tested by this artifact.",
        "", "## Resume at these tasks", "",
    ]
    for issue in state["issues"]:
        lines.append(f"- [Issue #{issue['number']}]({ISSUE_URL}/{issue['number']}) — {issue['title'].replace(chr(10), ' ')}")
    if not state["issues"]:
        lines.append("- Check the open GitHub issue tracker directly.")
    lines += ["", "## Next required evidence", "",
              "1. Check exact-SHA GitHub source CI.",
              "2. Match a new private device request with a complete time-stamped receipt.",
              "3. Test the approved HTTPS viewer on a real iPhone over cellular, including reopen and encrypted reply.",
              "4. Update the linked issue and docs/HANDOFF.md with device and phone results.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/odin-project-snapshot"))
    args = parser.parse_args()
    state = collect()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "status.md").write_text(render_status(state), encoding="utf-8")
    (args.output_dir / "handoff.md").write_text(render_handoff(state), encoding="utf-8")
    print("Wrote public status and handoff; private device and phone verification remain separate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
