# Supported Git sync and safe source updates

Current operation: [runtime](ODIN_RUNTIME.md). This page is the minimal active update runbook. Earlier relay commands, staging plans, and dated acceptance claims are [archived](archive/ODIN_SAFE_UPDATES_AND_ROADMAP_before_2026-11-22.md).

The handheld's existing Git sync and opt-in CI-gated updater use GitHub `main`. They are not remote terminal access and do not silently approve device execution. A repository commit is not a device installation receipt.

On the actual Odin, after reviewing a passing **push** workflow on the exact intended SHA, run:

```bash
cd ~/odin-workspace || exit 1
git status --short --branch
python -B scripts/odin_auto_update.py --status
```

Review any local changes, origin mismatch, divergence, or failed CI before installation. Do not reset, force, erase untracked work, or expose keys. If approval and preflight succeed:

```bash
bash scripts/odin-safe-pull.sh
python -B scripts/odin_auto_update.py --status
git rev-parse HEAD
```

To opt in to later CI-gated pulls: `python -B scripts/odin_auto_update.py --enable`. To stop: `python -B scripts/odin_auto_update.py --disable`. Both change local updater settings; do not run them without the operator's approval.

Source updates do not reload already-running Python processes. Reboot persistence is not implied by runit. Use an explicitly approved service restart and verify a matching private mailbox receipt when needed. Consult [release gates](RELEASE_GATES.md) and [issue #71](https://github.com/shawnfra2013/Oden2-/issues/71) for device acceptance.
