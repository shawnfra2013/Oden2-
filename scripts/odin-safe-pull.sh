#!/usr/bin/env bash
# Fast-forward only after checking the exact origin, tracked edits and collisions.
# Unrelated untracked device files are preserved, not removed.
set -euo pipefail

repo="${ODIN_REPO_DIR:-$HOME/odin-workspace}"
if [[ ! -d "$repo/.git" ]]; then
  printf 'ERROR: Git checkout not found: %s\n' "$repo" >&2
  exit 1
fi
cd "$repo"

if [[ "$(git symbolic-ref --quiet --short HEAD || true)" != "main" ]]; then
  printf 'STOP: Checkout is not on main.\n' >&2
  exit 1
fi

origin="$(git remote get-url origin)"
if [[ "$origin" != "https://github.com/shawnfra2013/Oden2-.git" && "$origin" != "git@github.com:shawnfra2013/Oden2-.git" ]]; then
  printf 'STOP: Unexpected origin URL.\n' >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  printf 'STOP: Tracked local changes need review.\n' >&2
  git status --short
  exit 1
fi

printf 'Starting commit: '
git rev-parse HEAD
git fetch origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
  printf 'STOP: Local main has diverged from GitHub.\n' >&2
  exit 1
fi

# Compare NUL-delimited paths to preserve odd untracked filenames.
# Also protect file/directory prefix collisions; Git will perform its own
# final safety checks during the fast-forward.
python - <<'PY'
import subprocess
import sys

def names(*argv):
    output = subprocess.check_output(["git", *argv])
    return [p for p in output.split(b"\0") if p]

incoming = names("diff", "--diff-filter=A", "--name-only", "-z", "HEAD", "origin/main")
untracked = names("ls-files", "--others", "--exclude-standard", "-z")
collisions = [
    (new, old) for new in incoming for old in untracked
    if new == old or new.startswith(old + b"/") or old.startswith(new + b"/")
]
if collisions:
    print(f"STOP: {len(collisions)} untracked-path collision(s); no merge attempted.", file=sys.stderr)
    sys.exit(1)
print(f"Preflight: {len(untracked)} untracked file(s) preserved.")
PY

git merge --ff-only origin/main

printf 'Updated commit: '
git rev-parse HEAD
git status --short --branch
