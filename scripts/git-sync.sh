#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/odin-workspace"
LOCKDIR="${ROOT}/state/git-sync.lock"
LOG="${ROOT}/logs/git-sync.log"

mkdir -p "${ROOT}/logs" "${ROOT}/state"

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"
}

cleanup() {
    rmdir "$LOCKDIR" 2>/dev/null || true
}

if ! mkdir "$LOCKDIR" 2>/dev/null; then
    log "SKIP: another sync is already running"
    exit 0
fi

trap cleanup EXIT INT TERM

cd "$ROOT"

log "START"

if [[ -n "$(git diff --name-only --diff-filter=U)" ]]; then
    log "REFUSED: unresolved merge conflict"
    exit 1
fi

BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"

if [[ "$BRANCH" != "main" ]]; then
    log "REFUSED: expected branch main, found '${BRANCH:-detached HEAD}'"
    exit 1
fi

git fetch origin main >>"$LOG" 2>&1

read -r BEHIND AHEAD < <(
    git rev-list --left-right --count origin/main...HEAD
)

if (( BEHIND > 0 )); then
    log "REFUSED: local main is behind/diverged from origin/main (behind=$BEHIND ahead=$AHEAD)"
    exit 1
fi

if git grep -nEI \
'(gsk_[A-Za-z0-9_-]{20,}|csk-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|github_pat_[A-Za-z0-9_]+|ghp_[A-Za-z0-9]+|BEGIN (OPENSSH|RSA|EC|DSA) PRIVATE KEY)' \
-- . ':!*.md' >>"$LOG" 2>&1
then
    log "REFUSED: possible secret detected in tracked content"
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    log "INFO: repository contains local changes; automatic commits are intentionally disabled"
    exit 2
fi

if (( AHEAD == 0 )); then
    log "OK: already synchronized"
    exit 0
fi

git push origin main >>"$LOG" 2>&1
log "OK: pushed $AHEAD local commit(s)"
