# Odin communication — persistent handoff (2026-11-23)

## Read first: how ChatGPT communicates with Odin

The working, authorized route is **ChatGPT GitHub connector + scheduled/event-triggered ChatGPT tasks + the existing private GitHub mailbox**, not Desktop Commander and not an interactive shell.

- Source of truth: `shawnfra2013/Oden2-`. Read current commit, PR head SHA, exact-head GitHub Actions, review comments and source documentation.
- Private transport: `shawnfra2013/Odin-private-bridge`, inbox branch `odin-bridge-inbox`, outbox branch `odin-bridge-outbox`. The Termux runit `odin-private-mailbox` service polls approximately every 60 seconds while connected.
- Authorized GitHub connection and the scheduled **Odin receipt watch** can read the private outbox and report new bounded device receipts. The **Review ODIN-HOUR pull requests** event task reviews supported GitHub PR events. They do not give this conversation an always-on terminal or guarantee an immediate wake-up for every event.
- A request submission is **not** a completed response. A completed private response is **not** proof an agent read feedback. A tool-presentation receipt is **not** proof an agent acted. A green CI run is **not** proof the new code is installed on the handheld.
- Never put private mailbox payloads, tokens, SSH keys, credentials, or personal conversations in the public repo. Never enable arbitrary shell execution from a GitHub request.

## Exact continuity procedure

1. Inspect the latest `Odin receipt watch` automation run, including its run ID, UTC completion time, and receipt summary. Inspect the `Review ODIN-HOUR pull requests` event automation run separately.
2. Through the authorized GitHub connection, inspect the private outbox's latest commit and compare newly uploaded request/response IDs, source-test receipt IDs, tool-feedback receipts, UTC timestamps and source SHAs with the previous checkpoint. Do not treat an unchanged outbox as a fresh device ping.
3. Inspect the public repo's exact PR head SHA and required CI. Distinguish PR source verification, physical device action, installed revision, model reply and ChatGPT event-to-run correlation.
4. To prove live physical connectivity, send a **fresh** allowlisted private `ping` through the existing authorized private workflow and match its request ID with a newly uploaded `complete` receipt. For workstation HTTP health use the existing `stage5_health` action. If workflow dispatch is unavailable through the connected GitHub tools, say so; do not fabricate a ping.
5. Before any physical update, confirm the running mailbox process and runit launcher point at canonical `~/odin-workspace`. A prior observed launcher pointed at `~/odin-pr45-test.iwGRYw`. Use `scripts/odin_mailbox_migrate.py` in read-only preview mode, then the guarded operator-approved migration if safe. Preserve existing private outbox and journals; never force, reset or delete.
6. After a real migration, obtain a new matching `ping` and `mailbox_audit` receipt and confirm the live process cwd and installed SHA. Do not infer installation from source CI.

## Evidence checkpoint at 2026-11-23

The hourly watcher last completed at 10:48:42 UTC and accessed the authorized private outbox. The last observed private outbox commit was `65e71811898b9a97656ece80ece4d655cea9ce10` at 08:23:08 UTC; no new device response or agent-read/action proof was observed in that run. The event reviewer had received two PR synchronization events around 10:05 UTC, but event-delivery IDs were not correlated to a ChatGPT run ID. This is a **historical snapshot**, not current connectivity proof.

See [current runtime](ODIN_RUNTIME.md), [private mailbox runbook](ODIN_GITHUB_BRIDGE.md), [collaboration trial](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md), [handoff](HANDOFF.md), and [release gates](RELEASE_GATES.md). If this handoff conflicts with fresher authenticated receipts, use the fresh evidence and update this document.
