#!/data/data/com.termux/files/usr/bin/bash
# One-time, non-destructive Odin private relay pairing and runit activation.
# Run interactively using: bash scripts/odin-relay-activate.sh
set -euo pipefail

cd "${HOME}/odin-workspace" || exit 1
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
state="${PWD}/state/odin-relay"
service="${PREFIX}/var/service/odin-private-relay"

if [[ ! -f scripts/odin_relay_client.py ]]; then
  printf '%s\n' 'STOP: Odin relay code not installed.' >&2
  exit 1
fi
if ! command -v sv >/dev/null 2>&1; then
  printf '%s\n' 'STOP: Termux runit supervisor not available.' >&2
  exit 1
fi
umask 077
mkdir -p "$state"
chmod 700 "$state"

# Never silently replace an existing credential.
if [[ -e "$state/token" ]]; then
  printf '%s\n' 'Existing private relay token preserved. Reusing it.'
else
  printf '%s\n' 'Open your private Odin setup file and copy the DEVICE TOKEN.'
  read -r -s -p 'Paste device token (hidden), then press Return: ' relay_secret
  printf '\n'
  if [[ ! "$relay_secret" =~ ^[A-Za-z0-9._~-]{32,256}$ ]]; then
    printf '%s\n' 'STOP: Invalid device token format.' >&2
    unset relay_secret
    exit 1
  fi
  (set -C; printf '%s\n' "$relay_secret" > "$state/token")
  chmod 600 "$state/token"
  unset relay_secret
fi

printf '%s\n' '=== VERIFY PRIVATE SERVER CONNECTION ==='
python -B scripts/odin_relay_client.py --once

printf '%s\n' '=== START BACKGROUND PRIVATE RELAY ==='
if [[ -e "$service" && ! -d "$service" ]]; then
  printf '%s\n' 'STOP: A conflicting service path already exists.' >&2
  exit 1
fi
mkdir -p "$service"
if [[ ! -e "$service/run" ]]; then
  (set -C; cat > "$service/run" <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/odin-workspace"
exec python -u -B scripts/odin_relay_client.py --serve
RUN
  )
  chmod 700 "$service/run"
else
  printf '%s\n' 'Existing runit run script preserved.'
fi
sv up "$service"
sv status "$service"

printf '%s\n' '=== PAIRING SUMMARY ==='
printf '%s\n' 'Private relay paired and runit service requested.'
printf '%s\n' 'Test from iPhone: Chat > Odin Device Inbox > send /ping'
printf '%s\n' 'Expected reply: ODIN_RELAY_PONG (device transport, not AI inference).'
printf '%s\n' 'No GitHub commits, resets, deletes, or force pushes were performed.'
