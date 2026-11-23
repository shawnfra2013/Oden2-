"""Odin model and read-only status portal; leaves the existing 'ai' executable intact.

The shell hook handles any capitalization of ai and forwards the original
orchestrator unchanged unless an explicit portal subcommand is used.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_AI = Path.home() / ".local/bin/ai"
MODEL_CHAT = ROOT / "scripts/odin_chat.py"
MONITOR = ROOT / "scripts/odin_cli_dashboard.py"
SERVICES = ("odin-git-sync", "odin-task-worker", "odin-local-model",
            "odin-stage5", "odin-private-mailbox")


def legacy(argv: list[str], *, binary: Path = LEGACY_AI) -> int:
    if not binary.is_file() or not os.access(binary, os.X_OK):
        print("Original ~/.local/bin/ai executable not found; refusing to replace it.",
              file=sys.stderr)
        return 2
    return subprocess.call([str(binary), *argv])


def model_chat(provider: str, *, consent: bool = False) -> int:
    from stage5.offline_profile import enabled as offline_enabled

    env = os.environ.copy()
    if provider == "local":
        if not offline_enabled():
            print("Local-only model profile not enabled. No remote fallback.",
                  file=sys.stderr)
            return 2
        env.update(ODIN_STAGE5_PROVIDER="local", ODIN_STAGE5_ENABLE_AI="1")
    else:
        if offline_enabled():
            print("Offline-only profile is locked; cloud switch refused.",
                  file=sys.stderr)
            return 2
        if not consent or provider not in {"groq", "openai"}:
            print("Cloud may cost money: require --provider and --confirm CLOUD-MAY-COST.",
                  file=sys.stderr)
            return 2
        token = "GROQ_API_KEY" if provider == "groq" else "OPENAI_API_KEY"
        if not env.get(token):
            print("Configured cloud credential missing; no request sent.", file=sys.stderr)
            return 2
        if provider == "openai" and not env.get("ODIN_OPENAI_MODEL"):
            print("ODIN_OPENAI_MODEL missing; no request sent.", file=sys.stderr)
            return 2
        env.update(ODIN_STAGE5_PROVIDER=provider, ODIN_STAGE5_ENABLE_AI="1")
    return subprocess.call([sys.executable, "-B", str(MODEL_CHAT)], cwd=ROOT, env=env)


def service_up(name: str, *, confirm: str, prefix: Path | None = None) -> int:
    """Explicit, local-only and allowlisted; never an automatic boot hook."""
    from scripts.odin_cli_dashboard import service_state
    from scripts.odin_preflight import private_mailbox_launch_path

    if name not in SERVICES or confirm != "START-ODIN-SERVICE":
        print("Refused: select a known service with --confirm START-ODIN-SERVICE.",
              file=sys.stderr)
        return 2
    prefix = Path(os.environ.get("PREFIX", "")) if prefix is None else prefix
    if not str(prefix) or not (prefix / "var/service" / name / "run").is_file():
        print("Service launcher not installed; refusing start.", file=sys.stderr)
        return 2
    state = service_state(name, prefix=prefix)
    if state["state"] == "RUNNING":
        print(f"{name} is already running; unchanged.")
        return 0
    if state["state"] != "STOPPED":
        print("Service status is not confirmed down; no change.", file=sys.stderr)
        return 2
    if name == "odin-private-mailbox":
        ready = private_mailbox_launch_path(prefix=prefix, home=Path.home())
        if ready["status"] != "PASS":
            print("Issue #71: private mailbox cwd has not passed; start blocked.",
                  file=sys.stderr)
            return 2
    result = subprocess.run(["sv", "-w", "15", "up", str(prefix / "var/service" / name)],
                            text=True, capture_output=True, timeout=25, check=False)
    if result.returncode:
        print("Runit service did not start; inspect local service.", file=sys.stderr)
        return 1
    return 0 if service_state(name, prefix=prefix)["state"] == "RUNNING" else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    cmd = args[0].lower() if args else "menu"
    if cmd in {"status", "watch"}:
        return subprocess.call([sys.executable, "-B", str(MONITOR), cmd, *args[1:]],
                               cwd=ROOT)
    if cmd in {"help", "menu"}:
        print("ODIN 2 | AI TERMINAL")
        print("ai / AI / Ai / aI   original orchestrator unchanged")
        print("ai status           local source, mailbox and services")
        print("ai watch --github   live terminal with cached GitHub CI")
        print("ai local            explicitly selected offline chat")
        print("ai online --provider groq|openai --confirm CLOUD-MAY-COST")
        print("ai services         read-only supervised service status")
        print("ai services up SERVICE --confirm START-ODIN-SERVICE")
        print("No automatic AI call, cloud fallback or service restart.")
        return 0
    if cmd == "local" and len(args) == 1:
        return model_chat("local")
    if cmd == "online":
        parser = argparse.ArgumentParser(prog="ai online")
        parser.add_argument("--provider", choices=["groq", "openai"], required=True)
        parser.add_argument("--confirm", default="")
        options = parser.parse_args(args[1:])
        return model_chat(options.provider,
                          consent=options.confirm == "CLOUD-MAY-COST")
    if cmd == "services":
        if len(args) == 1:
            from scripts.odin_cli_dashboard import service_state
            for name in SERVICES:
                print(f"{name:20} {service_state(name)['state']}")
            return 0
        if len(args) == 5 and args[1] == "up" and args[3] == "--confirm":
            return service_up(args[2], confirm=args[4])
        print("Usage: ai services [up SERVICE --confirm START-ODIN-SERVICE]",
              file=sys.stderr)
        return 2
    print("Unknown portal command. Try ai menu.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
