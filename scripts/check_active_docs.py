"""Fail CI if obsolete deployment instructions reappear in current Odin docs."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "CHANGELOG.md", "docs/ODIN_RUNTIME.md",
    "docs/ODIN_GITHUB_BRIDGE.md", "docs/OFFLINE_CHAT.md",
    "docs/RELEASE_GATES.md", "docs/DECISIONS.md", "docs/TASK_BOARD.md",
    "docs/PROJECT_STATUS.md", "docs/HANDOFF.md", "mobile/README.md",
)
BANNED = {
    "retired host/provider": re.compile(r"(?i)vercel|@vercel|\.vercel\.app"),
    "retired-host opt-in": re.compile(r"\bODIN_ENABLE_LEGACY_RELAY\b"),
    "user-facing obsolete phase": re.compile(r"(?i)\bstage\s+5\b"),
}


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for required in REQUIRED:
        if not (root / required).is_file():
            errors.append(f"Missing current guide: {required}")
    paths = [root / "README.md", root / "CHANGELOG.md", root / "mobile/README.md"]
    paths.extend(sorted((root / "docs").glob("*.md")))
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        content = path.read_text(encoding="utf-8")
        for name, pattern in BANNED.items():
            for match in pattern.finditer(content):
                line = content.count("\n", 0, match.start()) + 1
                errors.append(f"{rel}:{line}: {name}")
    runtime = root / "docs/ODIN_RUNTIME.md"
    if runtime.is_file() and "Odin Local Workstation" not in runtime.read_text(encoding="utf-8"):
        errors.append("Canonical runtime is missing the local workstation identity")
    return errors


def main() -> int:
    issues = check()
    if issues:
        print("Active documentation guard FAILED:\n" + "\n".join(issues))
        return 1
    print("Active documentation guard PASS: current guides separated from archive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
