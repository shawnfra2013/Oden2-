# Current changes

For historical changes, see [the archived changelog](docs/archive/CHANGELOG_before_2026-11-22.md). Historical records are not current deployment instructions.

## November 23, 2026 — live device-to-GitHub testing and supervised source fixes

- [PR #104](https://github.com/shawnfra2013/Oden2-/pull/104): terminal-only source test runner for Termux and optional GitHub Codespaces; local structured source receipts, no editor dependency.
- [PR #109](https://github.com/shawnfra2013/Oden2-/pull/109): offline-to-private GitHub receipt synchronization with durable local preservation, idempotent replay and bounded validation. **Real Odin acceptance:** source receipts `8642f52105aa4508830d906c6cbc472d` and `f0935b4308f74c51a32a014bbec3390b` arrived in the private outbox, one after an offline interval.
- The physical private bridge also accepted a newly issued read-only `ping` and returned a matching response (request `6bd037ac91e44aa09cb831f1d75e8f02`). These observations prove bounded messaging at their receipt times, not an interactive remote terminal.
- [PR #110](https://github.com/shawnfra2013/Oden2-/pull/110): fix disposable mailbox integration tests that accidentally inherited the live offline receipt directory. The physical `regression_details` request identified one failing recovery assertion, while source CI had passed with an empty queue.
- [PR #112](https://github.com/shawnfra2013/Oden2-/pull/112): accept a single paired Markdown backtick wrapper around a valid local coding expression; Odin had returned the correct expression with HTTP 200 but the older parser classified it as a mismatch.
- [PR #111](https://github.com/shawnfra2013/Oden2-/pull/111): first coordination module, exclusive local source task leases with SQLite transactions, stale SHA detection, path and branch conflicts, and concurrency tests. Cross-machine coordination and agent-authenticated work remain separate.
- Added an explicit local feedback-tool presentation receipt and private mailbox metadata uploader, preserving immutable IDs, offline retry, and a strict separation between tool display, model reading and code execution.
- Added a private-only fixed `mailbox_audit` bridge action, allowing a redacted read-only diagnostics request without exposing an arbitrary terminal. Its source implementation requires reviewed CI and later device rollout before live acceptance.
- Added a bounded read-only private mailbox incident auditor and local append-only snapshots; it detects stale, orphaned, mismatched, malformed, unexpected-completion and future-timestamp cases without printing private content.
- Recorded the eight-request stress test (8/8 completed over two 60-second polling cycles) in the [collaboration trial ledger](docs/audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md). The current ChatGPT review watch is hourly; no instant wake-on-push is claimed.
- Live private `staging_probe` and workstation health passed. Local-source query matched. A bounded `shell` action was rejected. Private review feedback was **stored and acknowledged, not executed**. The nine-case practice set reported finished, not a new coding session.
- **Open:** install the reviewed fixes on the actual handheld with the operator's approval; rerun the device regression and coding challenge; prove feedback read by the local coding agent and subsequent agent-produced PR; separately validate remote shell permissions and iPhone cellular connectivity.

## November 22, 2026 — operating-system and documentation reset

- Established [the canonical runtime guide](docs/ODIN_RUNTIME.md), [decisions](docs/DECISIONS.md), [issue-based task board](docs/TASK_BOARD.md), [release gates](docs/RELEASE_GATES.md), [status](docs/PROJECT_STATUS.md), and [handoff](docs/HANDOFF.md).
- Archived previous milestones and dated progress snapshots without deleting audit evidence.
- Added active-document consistency checks and a GitHub Actions status/handoff artifact workflow.
- Retained internal compatibility identifiers. User-facing name: **Odin Local Workstation**.
- A reviewed GitHub commit does not itself verify handheld installation or the iPhone viewer.

The canonical runtime and rollout instructions are in [the current runtime guide](docs/ODIN_RUNTIME.md).
