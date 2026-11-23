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

## Non-negotiable continuation policy — operator directive, 2026-11-23

This policy governs subsequent Odin supervised coding and review sessions. Read this document together with `README.md`, `AGENTS.md`, `ODIN_WORKFLOW.md`, `docs/ODIN_RUNTIME.md`, `docs/ODIN_CODER_TRAINING.md`, `docs/COLLABORATION_FRAMEWORK.md`, and `config/odin-services.json` before proposing infrastructure or coding changes. If any conflict appears, stop and request an explicit architecture decision; this document does not silently override security/release gates.

1. **Reuse the established transport.** Use only the existing private GitHub mailbox, its authenticated allowlisted actions, existing CI, and existing scheduled/event review tasks. No duplicate bridge, new public relay, alternate shell, new hosted service, or competing watcher without an issue documenting a verified missing capability and operator approval.
2. **Free-first inference is mandatory.** Prefer the configured on-device/offline model. An explicitly authorized free endpoint is allowed only within its actual rate/usage limits and security policy; never presume a free tier is unlimited. Do not invoke paid inference, silently fall back to a billable provider, start training on a paid service, or expose credentials. If no permitted inference is available, record BLOCKED.
3. **Use the existing mailbox efficiently, not recklessly.** Respect the approximately 60-second device poll and existing per-cycle bounded batch limits; reuse outstanding requests, deduplicate IDs, enforce expiry and backoff, and inspect receipts before sending new pings. Maximum useful coverage means bounded diagnostics and meaningful work, **not** flooding the inbox or increasing the polling rate without verified capacity and approval.
4. **Continue supervised self-improvement on existing scoped work.** Track issue #99 (one-hour trial), #100 (bounded coding critique/repair and benchmarks), #122 (local recall), and relevant existing PRs before creating new work. The cycle is immutable proposal → static critique → at most two review-directed revisions → independently executed functional tests → exact-head CI → human-reviewed PR → separate operator-approved device acceptance. Record FAIL/BLOCKED as such; never erase or relabel prior failed evidence.
5. **Distinguish improvement mechanisms.** Retrieval and saved critique lessons improve context; they do not update model weights. A candidate LoRA adapter is weight training only after an approved dataset, compatibility and compute checks, unseen functional benchmarks, explicit promotion and rollback approval. Do not claim autonomous weight improvement or successful agent action based on feedback storage, an AI self-grade, a green CI badge, or an unverified device response.
6. **Preserve safety and continuity.** Source edits remain scoped to reviewed branches/PRs; no force-push, merge, deploy, device restart, credential rotation, arbitrary remote commands, or unapproved paid usage. For every test record exact SHA, request/receipt ID, timestamp, outcome, CI link, and the distinction between GitHub source, actual handheld, and phone acceptance.

**Resume instruction:** Continue the existing PR/test/feedback work before inventing any new integration. Inspect the current open PRs and exact-head checks first; inspect the private outbox and watcher results next; prioritize independently verifiable defects and the next approved, bounded coding trial. This is a standing operational rule, not proof that a live device trial or self-training loop is currently running.
