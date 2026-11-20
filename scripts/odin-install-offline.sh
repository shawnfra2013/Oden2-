#!/usr/bin/env bash
# Interactive Termux enrollment. Re-running resumes an interrupted download.
set -euo pipefail
umask 077
: "${PREFIX:?Run inside Termux on Odin}"
cd "$HOME/odin-workspace"
[[ -f stage5/offline_profile.py && "$(uname -m)" == aarch64 ]]
config="$HOME/.config/odin-offline"
mkdir -p "$config"
exec 9>"$config/install.lock"
flock -n 9 || { echo "Another installation is running"; exit 1; }
command -v llama-server >/dev/null || pkg install -y llama-cpp
command -v llama-server >/dev/null
file=qwen2.5-coder-3b-instruct-q4_k_m.gguf
hash=724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7
weights="$config/$file"
valid() { printf '%s  %s\n' "$hash" "$1" | sha256sum --check --status; }
if [[ -f "$weights" ]]; then
  valid "$weights" || { echo "Existing model checksum differs"; exit 1; }
else
  url="https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/$file"
  curl --fail --location --retry 3 --continue-at - --output "$weights.part" "$url"
  if ! valid "$weights.part"; then
    mv "$weights.part" "$weights.invalid.$(date +%s)"
    echo "Download checksum differs. Rerun for a fresh download."
    exit 1
  fi
  mv "$weights.part" "$weights"
fi
service="$PREFIX/var/service/odin-local-model"
tmp=$(mktemp -d "$PREFIX/var/odin-local-setup.XXXXXX")
trap 'rm -rf -- "$tmp"' EXIT
{
  printf '#!%s/bin/bash\n' "$PREFIX"
  printf 'exec %q -m %q --alias qwen2.5-coder-3b --host 127.0.0.1 --port 18080 -c 2048 -np 1 -t 4 -ngl 0\n' "$(command -v llama-server)" "$weights"
} > "$tmp/run"
chmod 700 "$tmp/run"
if [[ -e "$service" ]]; then
  cmp -s "$tmp/run" "$service/run" || { echo "A different model launcher exists. Stopped."; exit 1; }
else
  mv -T "$tmp" "$service"
fi
for ((i=0;i<30;i++)); do [[ -e "$service/supervise/ok" ]] && break; sleep 1; done
sv -w 20 up "$service"
ready=0
for ((i=0;i<120;i++)); do
  if curl -fsS --max-time 2 http://127.0.0.1:18080/health >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[[ "$ready" == 1 ]] || { echo "Model failed its readiness check"; exit 1; }
# Verify the listener belongs to the supervised model we just launched.
pid=$(sv status "$service" | sed -n 's/^run:.*(pid \([0-9]*\)).*/\1/p')
[[ -n "$pid" && "$(readlink -f "/proc/$pid/exe")" == "$(readlink -f "$(command -v llama-server)")" ]]
python -B scripts/odin-offline-check.py
touch "$config/enabled"
sv -w 20 restart "$PREFIX/var/service/odin-stage5"
for ((i=0;i<30;i++)); do
  if curl -fsS --max-time 2 http://127.0.0.1:8765/api/health 2>/dev/null |
      python -c 'import json,sys; d=json.load(sys.stdin);sys.exit(0 if d.get("provider")=="local" and d.get("ai_enabled") is True else 1)' 2>/dev/null; then
    echo "READY: Open http://127.0.0.1:8765 on Odin"
    exit 0
  fi
  sleep 1
done
echo "Model answered. Stage 5 local provider still unverified."
exit 1
