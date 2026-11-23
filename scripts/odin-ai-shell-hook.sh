#!/usr/bin/env bash
# Opt-in Termux Bash hook. Never replace ~/.local/bin/ai or start a service.
if [ "${ODIN_AI_SHELL_HOOK_V1_LOADED:-}" = 1 ]; then
    return 0
fi
ODIN_AI_SHELL_HOOK_V1_LOADED=1

_odin_ai_legacy() {
    local executable="$HOME/.local/bin/ai"
    if [ ! -x "$executable" ]; then
        printf 'Original Odin AI executable missing: %s\n' "$executable" >&2
        return 2
    fi
    "$executable" "$@"
}

_odin_ai_dispatch() {
    local operation="${1:-}"
    operation="${operation,,}"
    case "$operation" in
        menu|help|status|watch|services|local|online)
            if [ ! -f "$HOME/odin-workspace/scripts/odin_cli_portal.py" ]; then
                printf 'Odin CLI portal source is unavailable; original ai preserved.\n' >&2
                return 2
            fi
            python -B "$HOME/odin-workspace/scripts/odin_cli_portal.py" "$@"
            ;;
        *)
            _odin_ai_legacy "$@"
            ;;
    esac
}

ai() { _odin_ai_dispatch "$@"; }
AI() { _odin_ai_dispatch "$@"; }
Ai() { _odin_ai_dispatch "$@"; }
aI() { _odin_ai_dispatch "$@"; }
