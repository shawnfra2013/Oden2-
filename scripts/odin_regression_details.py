"""Bounded private diagnostics from known regression commands on the canonical checkout."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(root, args):
    return subprocess.run(args, cwd=root, capture_output=True, text=True, errors="replace", timeout=180)


def diagnose(root):
    sources = set(run(root, ["git", "ls-files"]).stdout.splitlines())
    result = {}
    for name, pattern in (("tests", "test*.py"), ("stage5", "test_*.py")):
        proc = run(root, [sys.executable, "-B", "-m", "unittest", "discover", "-s", name, "-p", pattern, "-q"])
        failures = []
        for segment in re.split(r"^={20,}\s*$", proc.stderr, flags=re.M)[1:]:
            header = re.search(r"^(FAIL|ERROR): (\w+) \(([\w.]+)\)", segment, re.M)
            if not header:
                continue
            module = header[3].split(".")[0]
            if name + "/" + module + ".py" not in sources:
                continue
            frames = []
            for path, line in re.findall(r'File "([^"]+)", line (\d+)', segment):
                rel = str(Path(path).relative_to(root)) if Path(path).is_relative_to(root) else ""
                if rel in sources:
                    frames.append(f"{rel}:{line}")
            kinds = re.findall(r"^([\w.]+(?:Error|Exception)):", segment, re.M)
            failures.append({"test": module + "." + header[2], "frames": frames[-4:],
                             "exception": kinds[-1][:60] if kinds else header[1]})
        result[name] = {"code": proc.returncode, "failures": failures[:12]}
    linter = shutil.which("ruff")
    if not linter:
        result["lint"] = {"available": False}
    else:
        proc = run(root, [linter, "check", ".", "--output-format", "json"])
        items = json.loads(proc.stdout or "[]")
        findings = []
        for item in items[:100]:
            path = Path(item["filename"])
            rel = str(path.relative_to(root)) if path.is_relative_to(root) else ""
            findings.append({"file": rel if rel in sources else "outside_tracked_source",
                             "line": item["location"]["row"], "rule": item["code"]})
        result["lint"] = {"version": run(root, [linter, "--version"]).stdout.strip(),
                          "code": proc.returncode, "findings": findings[:16]}
    return result
