"""Fail CI on mismatched Odin service/port manifests and active source paths.

This is a *static* check. It cannot prove Android sockets or private HTTPS are live.
No credentials, network calls or model requests are involved.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
ACTIVE_ENTRYPOINTS = (
    "mobile/server.js", "mobile/app.js", "stage5/server.py", "stage5/app.js",
    "services/git-sync/run", "services/stage5/run",
    "services/odin-github-bridge/run", "ODIN_WORKFLOW.md", "AGENTS.md",
)
JSON_FILES = (
    "config/odin-services.json", "mobile/package.json",
    "mobile/package-lock.json", "mobile/ui-settings.json",
    "mobile/manifest.webmanifest",
)
BANNED_HOST = re.compile(r"(?i)vercel(?:\.app)?|@vercel/blob")
ALLOWED_INSTALLATION = {"tracked_launcher", "device_generated_launcher"}
ALLOWED_STATE = {"tracked_optional", "external_optional"}


def manifest_errors(manifest: dict, root: Path) -> list[str]:
    errors: list[str] = []
    if manifest.get("version") != 1:
        errors.append("Unsupported service registry version")
    if manifest.get("canonical_workflow") != "ODIN_WORKFLOW.md":
        errors.append("Canonical workflow does not point to ODIN_WORKFLOW.md")
    if not (root / "ODIN_WORKFLOW.md").is_file():
        errors.append("Missing canonical workflow instructions")
    seen_ids: set[str] = set()
    for service in manifest.get("services", []):
        name = service.get("id")
        if not isinstance(name, str) or name in seen_ids:
            errors.append(f"Duplicate or invalid service ID: {name}")
        seen_ids.add(name)
        entry = service.get("entry")
        if not isinstance(entry, str) or not (root / entry).is_file():
            errors.append(f"Missing service entrypoint: {entry}")
        installation = service.get("installation")
        if installation not in ALLOWED_INSTALLATION:
            errors.append(f"Unsupported service installation type: {name}")
        run = service.get("run")
        if installation == "tracked_launcher":
            if not isinstance(run, str) or not (root / run).is_file():
                errors.append(f"Missing runit launcher for {name}: {run}")
            elif entry not in (root / run).read_text(encoding="utf-8"):
                errors.append(f"Launcher for {name} does not reference {entry}")
        elif run is not None:
            errors.append(f"Untracked dynamic launcher listed as file for {name}")
    listeners: set[tuple[str, int]] = set()
    for item in manifest.get("listeners", []):
        ident = item.get("id")
        if not isinstance(ident, str) or ident in seen_ids:
            errors.append(f"Duplicate or invalid listener ID: {ident}")
        seen_ids.add(ident)
        host = item.get("host")
        port = item.get("port")
        if host != "127.0.0.1" or type(port) is not int or not 1 <= port <= 65535:
            errors.append(f"Unsafe/default listener address for {ident}: {host}:{port}")
            continue
        address = (host, port)
        if address in listeners:
            errors.append(f"Listener collision on {host}:{port}")
        listeners.add(address)
        if item.get("state") not in ALLOWED_STATE:
            errors.append(f"Unknown listener state for {ident}")
        entry = item.get("entry")
        marker = item.get("source_marker")
        source = root / entry if isinstance(entry, str) else None
        if source is None or not source.is_file():
            errors.append(f"Missing listener source for {ident}: {entry}")
        elif not isinstance(marker, str) or marker not in source.read_text(encoding="utf-8"):
            errors.append(f"Port/default marker differs in source for {ident}")
        for guide in ("docs/ODIN_RUNTIME.md", "docs/SERVICE_REGISTRY.md"):
            file = root / guide
            if not file.is_file() or str(port) not in file.read_text(encoding="utf-8"):
                errors.append(f"Port {port} missing from {guide}")
    network = manifest.get("private_network", {})
    if network.get("selected") != "Tailscale":
        errors.append("Configured private network must be Tailscale")
    planned = network.get("planned_phone_port")
    if network.get("planned_phone_port_active") is not False:
        errors.append("Draft phone port must not be treated as verified active")
    if any(port == planned for _, port in listeners):
        errors.append("Draft phone port is incorrectly registered as an active listener")
    for entry in manifest.get("intentionally_retained_paths", []):
        if not (root / entry).is_file():
            errors.append(f"Retained migration evidence missing: {entry}")
        for service in manifest.get("services", []):
            if service.get("entry") == entry:
                errors.append(f"Legacy relay unexpectedly registered as active: {entry}")
    return errors


def active_link_errors(root: Path) -> list[str]:
    errors = []
    paths = [root / "README.md", root / "ODIN_WORKFLOW.md", root / "AGENTS.md"]
    paths.extend(sorted((root / "docs").glob("*.md")))
    paths.append(root / "mobile/README.md")
    for file in paths:
        if not file.is_file():
            continue
        for match in LINK_RE.finditer(file.read_text(encoding="utf-8")):
            target = match.group(1).strip().split("#", 1)[0].split("?", 1)[0]
            if not target or target.startswith(("/", "http:", "https:", "mailto:")):
                continue
            if target.startswith("<") or " " in target:
                continue  # A title or non-file example, not a bare relative path
            resolved = (file.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"Broken active Markdown link: {file.relative_to(root)} -> {target}")
    return errors


def mobile_route_errors(root: Path) -> list[str]:
    file = root / "mobile/server.js"
    if not file.is_file():
        return ["Missing mobile server entrypoint"]
    code = file.read_text(encoding="utf-8")
    block = re.search(r'const routes = new Map\(\[([^\]]+)\]\.map', code)
    if not block:
        return ["Cannot inspect the mobile API route table"]
    errors = []
    for name in re.findall(r'"([a-z-]+)"', block.group(1)):
        if not (root / "mobile/api" / (name + ".js")).is_file():
            errors.append(f"Dead mobile API route: {name}")
    for asset in ("index.html", "styles.css", "app.js", "chat-route.js",
                  "encrypted-chat.js", "manifest.webmanifest", "ui-settings.json"):
        if not (root / "mobile" / asset).is_file():
            errors.append(f"Missing served mobile asset: {asset}")
    for asset in ("index.html", "style.css", "app.js", "device-controls.js"):
        if not (root / "stage5" / asset).is_file():
            errors.append(f"Missing workstation browser asset: {asset}")
    return errors


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for name in JSON_FILES:
        path = root / name
        if not path.is_file():
            errors.append(f"Missing required JSON: {name}")
        else:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                errors.append(f"Invalid JSON: {name}")
    manifest_path = root / "config/odin-services.json"
    if manifest_path.is_file():
        try:
            registry = json.loads(manifest_path.read_text(encoding="utf-8"))
            errors.extend(manifest_errors(registry, root))
        except (ValueError, OSError, TypeError) as exc:
            errors.append(f"Cannot validate service registry: {type(exc).__name__}")
    for entry in ACTIVE_ENTRYPOINTS:
        path = root / entry
        if not path.is_file():
            errors.append(f"Missing active entrypoint: {entry}")
        elif BANNED_HOST.search(path.read_text(encoding="utf-8")):
            errors.append(f"Retired hosting reference in active entrypoint: {entry}")
    errors.extend(active_link_errors(root))
    errors.extend(mobile_route_errors(root))
    return errors


def main() -> int:
    errors = check()
    if errors:
        print("Odin structural check FAILED:\n" + "\n".join(errors))
        return 1
    print("Odin structural check PASS: tracked entrypoints, references and defaults match.")
    print("Reminder: GitHub CI cannot check live Android processes, model readiness or phone HTTPS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
