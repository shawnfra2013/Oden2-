#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/odin-workspace"
LOG="${ROOT}/logs/git-sync.log"

mkdir -p "${ROOT}/logs" "${ROOT}/state"

# Runit continues calling this same script. A Python fcntl.flock wrapper
# holds a kernel lock for the ENTIRE sync, automatically releasing on crash.
# The old state/git-sync.lock directory is ignored and never modified.
if [[ "${1:-}" != "--under-odin-sync-lock" || "$#" -ne 1 ]]; then
    exec python -B "${ROOT}/scripts/odin_git_sync_lock.py"
fi

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"
}

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

# Reuse the existing five-minute supervisor. Updates are disabled unless the
# owner deliberately enables the 0600 state/auto-update.enabled flag.
# Any failed gated update stays visible in logs and status JSON.
if [[ -f "${ROOT}/state/auto-update.enabled" ]]; then
    if ! python -B "${ROOT}/scripts/odin_auto_update.py" --once >>"$LOG" 2>&1; then
        log "ALERT: CI-gated auto-update failed; refusing further sync"
        exit 1
    fi
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

if ! git diff --quiet || ! git diff --cached --quiet; then
    log "REFUSED: tracked changes exist; automatic commits disabled"
    exit 2
fi

if (( AHEAD == 0 )); then
    # Preserve harmless user-owned untracked files without producing
    # a false sync failure every five minutes.
    log "OK: already synchronized (untracked files preserved)"
    exit 0
fi

if [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
    log "REFUSED: local untracked files present before push; no automatic commits"
    exit 2
fi

git push origin main >>"$LOG" 2>&1
log "OK: pushed $AHEAD local commit(s)"
