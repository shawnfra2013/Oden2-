# Odin 2 / Termux system architecture

Read the [runtime guide](ODIN_RUNTIME.md) for supported addresses, dependencies,
and cutover checks. Dated verification is kept in [project history](PROJECT_MEMORY.md).

| Module | Responsibilities | Entry point |
| --- | --- | --- |
| `stage5/` (compatibility path) | Odin Local Workstation: loopback browser with provider selection and SQLite conversation storage | `services/stage5/run` |
| `ai/agent/` | Bounded inference, proposals and evidence | `orchestrator.py`, `pipeline.py` |
| `scripts/odin_worker.py` | Supervised task queue | `odin-task-worker` |
| `scripts/odin_chat.py` | Termux model conversation | `python -B scripts/odin_chat.py` |
| `scripts/odin_github_bridge.py` | Private GitHub mailbox and optional sanitized public diagnostics | `odin-private-mailbox` and optional `odin-github-bridge` |
| `mobile/` | Optional phone dashboard, public telemetry and authenticated chat | `npm start --prefix mobile` |
| `scripts/git-sync.sh` | Periodic Git sync and opt-in CI-gated source update | `services/git-sync/run` |
| `.github/workflows/` | Source and browser verification | GitHub Actions |

GitHub main is the source authority. Device activation and functional receipt
verification are separate. The optional updater fast-forwards only after exact
main-SHA checks and local preflight. Source updates preserve private device
state. Termux reboot startup remains deferred.
