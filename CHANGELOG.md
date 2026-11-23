# Current changes

For the complete earlier changelog, see [the archived changelog](docs/archive/CHANGELOG_before_2026-11-22.md). Entries there are historical observations, not current instructions.

## November 22, 2026 — operating-system and documentation reset## November 23, 2026 — terminal-only source loop and offline source receipts

- Source CLI and local tests added for Termux and manually opened GitHub Codespaces (PR #104), with local JSON source-only receipts.
- Private mailbox source-receipt synchronizer delivered in [PR #109](https://github.com/shawnfra2013/Oden2-/pull/109): bounded validation, durable journal, idempotent private outbox uploads, offline retry, security tests and operator acceptance steps.
- Live device installation and new receipt correlation will be recorded separately; no hosting change, editor dependency, arbitrary command bridge, or phone endpoint was introduced.



- Establish [the canonical runtime guide](docs/ODIN_RUNTIME.md), [decisions](docs/DECISIONS.md), [issue-based task board](docs/TASK_BOARD.md), [release gates](docs/RELEASE_GATES.md), [time-stamped status](docs/PROJECT_STATUS.md), and [handoff](docs/HANDOFF.md).
- Archive previous stages, old hosted-service notes, and dated progress snapshots without deleting audit evidence.
- Add automated active-document consistency checks and a GitHub Actions status/handoff artifact workflow.
- Retain the physical bridge and local service identifiers for compatibility. User-facing name: **Odin Local Workstation**.
- **Not claimed:** new cellular access, a verified Tailscale route, physical installation of this revision, or live device-side acceptance.

The canonical runtime and rollout instructions are in [the current runtime guide](docs/ODIN_RUNTIME.md).
