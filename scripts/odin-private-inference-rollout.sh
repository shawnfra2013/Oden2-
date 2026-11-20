#!/usr/bin/env bash
# Run from a disposable checkout of the exact reviewed upgrade.
set -euo pipefail
umask 077
target=$(git rev-parse HEAD)

service="${PREFIX:?}/var/service/odin-private-mailbox"
pid_of_service() {
  sv status "$service" | sed -n 's/^run:.*(pid \([0-9]*\)).*/\1/p'
}
before=$(pid_of_service)
active=$(readlink -e "/proc/${before:?service down}/cwd")
old=$(git -C "$active" rev-parse HEAD)
case "$(git -C "$active" remote get-url origin)" in
  https://github.com/shawnfra2013/Oden2-.git|git@github.com:shawnfra2013/Oden2-.git) ;;
  *) echo 'Unexpected active source repository.' >&2; exit 1 ;;
esac
[[ "$active" == "$HOME/"* && "$active" != "$HOME/odin-workspace" ]] ||
  { echo 'Expected an isolated service checkout.' >&2; exit 1; }
if git -C "$active" symbolic-ref -q HEAD >/dev/null; then exit 1; fi
[ -z "$(git -C "$active" status --porcelain)" ]
python -B -m unittest discover -s tests -p 'test_private*.py' -v
python -B -m unittest discover -s stage5 -p test_openai_adapter.py -v
git -C "$active" fetch -q "$PWD" "$target"
git -C "$active" merge-base --is-ancestor "$old" "$target" || { echo "Target must advance the active revision."; exit 1; }
config="$HOME/.config/odin-private-inference"
mkdir -p -m 700 "$config"
[ ! -L "$config" ] && [ "$(stat -c %a "$config")" = 700 ] || exit 1
if [ ! -e "$config/key" ]; then
  python -B - <<'PY'
import fcntl
import getpass
import os
import tempfile
from pathlib import Path
folder = Path.home() / ".config/odin-private-inference"
key = getpass.getpass("OpenAI key for private probes (hidden): ").strip()
if not key or len(key) > 1024 or not key.isascii() or any(c.isspace() for c in key):
    raise SystemExit("Invalid key input")
fd, temp = tempfile.mkstemp(dir=folder)
try:
    with os.fdopen(fd, "w") as handle:
        handle.write(key)
        handle.flush()
        os.fsync(handle.fileno())
    with (folder / ".install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not os.path.lexists(folder / "key"):
            os.replace(temp, folder / "key")
finally:
    Path(temp).unlink(missing_ok=True)
PY
fi
python -B -c 'from scripts.odin_inference_probe import load_key; load_key()'
if [[ "$old" == "$target" ]]; then echo "Already running target $target"; exit 0; fi
rollback() {
  rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ]; then
    echo "Restoring pre-upgrade revision $old"
    sv -w 20 down "$service" && git -C "$active" checkout -q --detach "$old" &&
      sv -w 20 up "$service" && sv status "$service"
  fi
  exit "$rc"
}
trap rollback EXIT
trap 'exit 130' INT TERM
sv -w 20 down "$service"
outbox="$active/state/github-bridge-private/outbox"
[ -z "$(git -C "$outbox" status --porcelain)" ]
export GIT_SSH_COMMAND="ssh -i '$HOME/.ssh/odin_private_bridge_ed25519' -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10"
remote=$(git ls-remote --exit-code git@github.com:shawnfra2013/Odin-private-bridge.git refs/heads/odin-bridge-outbox)
[ "$(git -C "$outbox" rev-parse HEAD)" = "${remote%%[[:space:]]*}" ]
git -C "$active" checkout -q --detach "$target"
sv -w 20 up "$service"
sleep 2
after=$(pid_of_service)
[ -n "$after" ] && [ "$before" != "$after" ] || exit 1
[ "$(readlink -e "/proc/$after/cwd")" = "$active" ]
printf 'READY for private inference probe: %s PID %s\n' "$target" "$after"
