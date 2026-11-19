#!/usr/bin/env bash
# Safely fast-forward a clean Odin checkout to the reviewed GitHub main.
set -euo pipefail

repo="${ODIN_REPO_DIR:-$HOME/odin-workspace}"
if [[ ! -d "$repo/.git" ]]; then
  printf 'ERROR: Git checkout not found: %s\n' "$repo" >&2
  exit 1
fi
cd "$repo"
if [[ "$(git branch --show-current)" != main ]]; then
  printf 'ERROR: Checkout is not on main. No pull attempted.\n' >&2
  exit 1
fi
if [[ -n "$(git status --porcelain --untracked-files=normal)" ]]; then
  printf 'ERROR: Local changes/untracked files present. No pull attempted.\n' >&2
  git status --short
  exit 1
fi
origin="$(git remote get-url origin)"
if [[ "$origin" != "https://github.com/shawnfra2013/Oden2-.git" && "$origin" != "git@github.com:shawnfra2013/Oden2-.git" ]]; then
  printf 'ERROR: Unexpected origin URL. No pull attempted.\n' >&2
  exit 1
fi
printf 'Current commit: '; git rev-parse --short HEAD
git fetch origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
  printf 'ERROR: Local main has diverged. No pull attempted.\n' >&2
  exit 1
fi
git merge --ff-only origin/main
printf 'Updated commit: '; git rev-parse --short HEAD
printf 'Working tree status:\n'; git status --short --branch
