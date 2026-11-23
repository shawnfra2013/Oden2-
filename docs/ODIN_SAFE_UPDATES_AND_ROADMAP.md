# Odin source updates and device verification

## One-time activation, performed on Odin itself

After GitHub CI has passed on this exact release, run from Termux:

    cd ~/odin-workspace || exit 1
    bash scripts/odin-safe-pull.sh || exit 1
    python -B scripts/odin_auto_update.py --enable
    python -B scripts/odin_auto_update.py --status

This installs the reviewed update once and explicitly enables future
source updates. The control flag is in ignored state/, mode 0600. No
credentials are needed for the public GitHub Actions status API. The
GitHub repository remains the source authority, and existing private
SQLite databases, user files and tokens remain in ignored state/.

The existing git-sync process invokes the updater on each loop. It
fetches the remote main SHA, requires the completed successful **push**
Odin Checks workflow on precisely that SHA, rejects unclean tracked
trees and divergence, then uses scripts/odin-safe-pull.sh. The safe-pull
helper re-fetches and must still match the exact approved SHA. Failing
checks prevent installation.

The supervisor runs approximately every five minutes when Termux and
runit are active. Android can stop background processes. There is no
guarantee of restart after reboot; boot automation remains deferred.

## See status and disable updates

    python -B scripts/odin_auto_update.py --status
    python -B scripts/odin_auto_update.py --disable
    tail -n 25 logs/git-sync.log

Updates are classified as current, waiting, blocked, updated, or error.
The most recent outcome is stored privately in
state/auto-update-result.json. Logs record reason codes but do not
include private conversation content or credentials. The updater does
not delete or reset branches, install packages, or run model-written
commands.

When enabled, the updater reloads affected running services and records the
exact revision and reload outcome in `state/last-auto-rollout.json`. A later
no-op sync preserves that evidence. If you updated manually, see
`python -B scripts/odin_service_restart.py --local`. This uses the same
execution lock as the web app's confirmed restart control.

Check the revision and service state with the GitHub `odin_health` receipt.
Verify an actual local model reply on Odin and a second reply on the
iPhone over cellular. Follow the [phone runbook](ODIN_PHONE_ACCESS.md) for
individual cutover and reconnect checks.
