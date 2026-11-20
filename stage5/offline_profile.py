"""Persistent local-only selection for an enrolled Odin."""
from pathlib import Path

MODEL = "qwen2.5-coder-3b"
PORT = "18080"


def enabled():
    return (Path.home() / ".config" / "odin-offline" / "enabled").is_file()


def activate(env):
    if enabled():
        env.update(ODIN_STAGE5_ENABLE_AI="1", ODIN_STAGE5_PROVIDER="local",
                   ODIN_LOCAL_MODEL=MODEL, ODIN_LOCAL_PORT=PORT)
