"""Read bounded excerpts of committed Python functions from Odin's source."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(["git", "--no-pager", *args], cwd=ROOT, capture_output=True,
                          encoding="utf-8", timeout=4, check=False)


def lookup(symbol):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", symbol):
        raise ValueError("Enter a Python function name.")
    head = git("rev-parse", "--verify", "HEAD").stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError("Source revision unavailable")
    matches = git("grep", "-n", "-E", f"^[[:space:]]*(async )?def {symbol}\\(",
                  head, "--", "stage5/*.py", "scripts/*.py", "ai/agent/*.py")
    if matches.returncode not in (0, 1):
        raise RuntimeError("Source search unavailable")
    results = []
    for hit in matches.stdout.splitlines():
        _, path, lineno, _ = hit.split(":", 3)
        if path.rsplit("/", 1)[-1].startswith("test_"):
            continue
        start = int(lineno)
        source = git("show", f"{head}:{path}")
        if source.returncode:
            raise RuntimeError("Source excerpt unavailable")
        lines = source.stdout.splitlines()[start-1:start+14]
        excerpt = [lines[0]]
        for line in lines[1:]:
            if line.strip() and len(line)-len(line.lstrip()) <= len(lines[0])-len(lines[0].lstrip()):
                break
            excerpt.append(line)
        label = f"{path}:{start} @ {head[:12]}"
        reference = (label + "\n" + "\n".join(excerpt).rstrip()).encode()[:1500].decode(errors="ignore")
        results.append({"label": label, "reference": reference})
        if len(results) == 5:
            break
    return {"revision": head, "matches": results}
