#!/usr/bin/env bash
# Preserve existing Odin executable; never install a daemon on shell login.
set -eu
root="$HOME/odin-workspace"
legacy="$HOME/.local/bin/ai"
bashrc="$HOME/.bashrc"
hook="$root/scripts/odin-ai-shell-hook.sh"
marker="# ODIN_AI_SHELL_HOOK_V1"
mode="${1:---check}"

if [ "$mode" != "--check" ] && [ "$mode" != "--apply" ]; then
    printf 'Usage: bash scripts/odin-cli-install.sh [--check | --apply --confirm INSTALL-ODIN-AI-SHELL]\n' >&2
    exit 2
fi
if [ ! -x "$legacy" ] || [ ! -f "$hook" ]; then
    printf 'BLOCKED: current ~/.local/bin/ai or reviewed hook missing. No changes.\n' >&2
    exit 2
fi
if [ ! -f "$bashrc" ] || [ -L "$bashrc" ]; then
    printf 'BLOCKED: existing ~/.bashrc unavailable or unsafe; no changes.\n' >&2
    exit 2
fi
if grep -Eq '^[[:space:]]*(alias[[:space:]]+ai=|function[[:space:]]+ai[[:space:]]*\(|ai[[:space:]]*\(\))' "$bashrc"; then
    printf 'BLOCKED: ai is already assigned in ~/.bashrc; inspect manually.\n' >&2
    exit 2
fi
if grep -Fq "$marker" "$bashrc"; then
    printf 'ALREADY_INSTALLED: original ai remains unchanged.\n'
    exit 0
fi
if [ "$mode" = "--check" ]; then
    printf 'READY: preserved legacy ai at %s\n' "$legacy"
    printf 'New hook would enable ai, AI, Ai and aI in ~/.bashrc.\n'
    printf 'No shell, service or provider was changed.\n'
    exit 0
fi
if [ "${2:-}" != "--confirm" ] || [ "${3:-}" != "INSTALL-ODIN-AI-SHELL" ] || [ "$#" -ne 3 ]; then
    printf 'BLOCKED: explicit shell-install confirmation required.\n' >&2
    exit 2
fi

umask 077
backup_dir="$HOME/.odin-preservation"
if [ -L "$backup_dir" ]; then
    printf 'BLOCKED: unsafe backup path.\n' >&2
    exit 2
fi
mkdir -p "$backup_dir"
backup="$(mktemp "$backup_dir/bashrc-before-odin-ai.XXXXXXXX.bak")"
cp "$bashrc" "$backup"
chmod 600 "$backup"
printf '\n%s\n[ -r "$HOME/odin-workspace/scripts/odin-ai-shell-hook.sh" ] && . "$HOME/odin-workspace/scripts/odin-ai-shell-hook.sh"\n' "$marker" >> "$bashrc"
printf 'INSTALLED: new Bash hook enabled in future Termux shells.\n'
printf 'Backup: %s\n' "$backup"
printf 'Existing ~/.local/bin/ai was not changed. No services were started.\n'
