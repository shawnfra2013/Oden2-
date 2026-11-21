"""Save an approved UI configuration offline and publish its exact commit to a review branch."""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = "mobile/ui-settings.json"
LATEST = "refs/odin-ui/latest"
PENDING = "refs/odin-ui/pending/"
ORIGINS = {"git@github.com:shawnfra2013/Oden2-.git", "https://github.com/shawnfra2013/Oden2-.git"}


def git(root, *args, data=None, env=None):
    result = subprocess.run(["git", *args], cwd=root, input=data, capture_output=True, text=True,
                            env=env, timeout=30)
    if result.returncode:
        raise RuntimeError("Git operation unavailable")
    return result.stdout.strip()


def validate(settings):
    if not isinstance(settings, dict) or set(settings) != {"accent", "size", "heading"}:
        raise ValueError("Choose a color, text size and chat heading")
    if settings["accent"] not in ("original", "teal", "gold") or settings["size"] not in ("standard", "large"):
        raise ValueError("Unknown appearance option")
    if not isinstance(settings["heading"], str) or not re.fullmatch(r"[\w .!?'-]{0,48}", settings["heading"]):
        raise ValueError("Use a heading of up to 48 letters, numbers or simple punctuation")
    return settings


def read_at(root, revision):
    return validate(json.loads(git(root, "show", revision + ":" + FILE)))


def current(root=ROOT):
    head = git(root, "rev-parse", "HEAD")
    latest = git(root, "for-each-ref", "--format=%(objectname)", LATEST)
    active = head
    if latest:
        base = git(root, "rev-parse", latest + "^")
        if git(root, "merge-base", latest, head) != latest and read_at(root, base) == read_at(root, head):
            active = latest
    pending = git(root, "for-each-ref", "--format=%(refname)", PENDING).splitlines()
    return {"settings": read_at(root, active), "version": head + "." + latest,
            "pending": len(pending), "latest": latest,
            "branch": ("odin-ui/edit-" + latest[:16]) if latest else ""}


def approve(settings, version, root=ROOT):
    validate(settings)
    before = current(root)
    if before["version"] != version:
        raise ValueError("Settings changed. Reload and review the edit again.")
    if before["settings"] == settings:
        return before
    head, old = version.split(".")
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        git(root, "read-tree", head, env=env)
        blob = git(root, "hash-object", "-w", "--stdin", data=json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
        git(root, "update-index", "--cacheinfo", "100644", blob, FILE, env=env)
        tree = git(root, "write-tree", env=env)
        commit = git(root, "-c", "user.name=Odin", "-c", "user.email=odin@localhost",
                     "commit-tree", tree, "-p", head, "-m", "Approved offline UI settings")
    git(root, "update-ref", "--stdin", data=(f"verify HEAD {head}\nupdate {LATEST} {commit} {old or '0'*40}\n"
                                             f"update {PENDING}{commit} {commit}\n"))
    return current(root)


def sync(root=ROOT, *, allowed=ORIGINS):
    pending = git(root, "for-each-ref", "--count=4", "--format=%(objectname)", PENDING).splitlines()
    if not pending:
        return
    if git(root, "remote", "get-url", "--push", "--all", "origin") not in allowed:
        raise ValueError("Unexpected UI draft destination")
    for commit in pending:
        if git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", commit) != FILE:
            raise ValueError("Unexpected UI edit scope")
        read_at(root, commit)
        branch = "refs/heads/odin-ui/edit-" + commit[:16]
        git(root, "push", "origin", f"{commit}:{branch}",
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if git(root, "ls-remote", "--exit-code", "origin", branch).split()[0] != commit:
            raise RuntimeError("Uploaded revision unconfirmed")
        git(root, "update-ref", "-d", PENDING + commit, commit)


if __name__ == "__main__":
    sync()
