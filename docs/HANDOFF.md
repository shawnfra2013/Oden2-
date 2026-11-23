# Odin — current session handoff

**Updated:** November 23, 2026 (Central). This is the current human-reviewed checkpoint. Use [the timestamped snapshot workflow](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml) and the actual GitHub main SHA for subsequent sessions. Historical material is not a deployment guide.

## November 23 Termux ai traceback and issue #71 preflight evidence

**Operator-reported physical Termux observation:** `~/odin-workspace` had HEAD `312a075fab3a931af3d68d39c6b708bd7c300f28`; `type -a ai AI Ai aI` reported only the original lower-case executable at `~/.local/bin/ai`; the protected Bash-hook installer returned **READY (dry-run only)** and made no shell changes. The read-only `odin_mailbox_migrate.py --expected-sha 9bf0d34a169df05ffb94a939010f00cb828ba13a` check returned **BLOCKED: Canonical checkout is not the approved source SHA**. This is an expected safety gate for a stale checkout versus the requested target, **not** proof of a corrupt mailbox, dirty Git tree, or wrong active process directory.

**Observed failure:** A real interactive `ai` turn reached `ai/agent/orchestrator.py::_respond_impl` but raised `ModuleNotFoundError: No module named 'scripts'` at `from scripts.odin_project_memory import context_for` (line 399 before repair). Direct Python script invocation starts with `ai/agent` on its import path, while the earlier memory unit test imported the orchestrator as a repository package. Source PR #156 adds the canonical repository root to the direct-script import path and an independent no-model subprocess regression; validate its exact PR SHA and separately verify the physical `ai` command after approved source rollout. A source merge does not modify the existing executable or service.

**Latest private boundary at this checkpoint:** ping request `b7102026112315245800000000000005` returned `action=none`, `status=expired`, at `2026-11-23T16:21:49Z`. Do **not** call that liveness PASS or infer current PID/cwd. The last *successful* earlier matched audit remains the post-fix `b7102026112315194000000000000004` at 15:20:36 UTC, which does not prove the newest installed revision. Next safe action is exact-SHA source CI for PR #156, then **read-only** local `git status`, update policy inspection, and `odin_mailbox_migrate.py` dry-run using the local HEAD. Obtain explicit operator approval for any Git update, shell hook apply, mailbox migration or process restart.




## November 23 current #71 and protected AI CLI continuation (source vs device)

**Live verified transport:** fresh request `b7102026112314520000000000000001` completed with `alive=true` at 14:53:18 UTC, PID 31499, device-reported SHA `0a9538a0a02576a70faaf4c4691c276ab1d338ad`. Follow-up ping `b7102026112315181600000000000003` completed at 15:19:22 UTC, PID 16369, device SHA `15e0c09c3a0e74e2169d59e83520bae4b6a68eb0`. The PID/revision changed, but the reason and current `/proc/PID/cwd` are **not** proven. Audit `b7102026112315194000000000000004` completed at 15:20:36 UTC against source `15e0c09c...`, showing **5 matched, 1 pending, 0 malformed/stalled/incidents**. The earlier one-incident audit was a verified safe-action-list defect; [PR #152](https://github.com/shawnfra2013/Oden2-/pull/152) fixed it and the new physical audit demonstrates that source is now running.

**Source delivery:** [PR #149](https://github.com/shawnfra2013/Oden2-/pull/149) is the one canonical colorful read-only Odin Terminal; [PR #153](https://github.com/shawnfra2013/Oden2-/pull/153) integrates mixed-case `ai`/`Ai`/`aI`/`AI` through a **separate opt-in Bash hook**, preserving the original `~/.local/bin/ai` executable. Main portal merge `312a075fab3a931af3d68d39c6b708bd7c300f28` passed exact-main four source checks. [PR #154](https://github.com/shawnfra2013/Oden2-/pull/154) merged a fixed **read-only** private `mailbox_migration_preview` action to eliminate future copy/paste when its code is actually loaded on the device. Source main at this handoff preparation was `2d6a0e9e733b18e80b5fb8db22310b881d52cf63`; verify its own exact-main CI before acceptance. A subsequent ping request `b7102026112315245800000000000005` has been submitted; **do not claim a new runtime revision until its matching response is checked**.

**Unresolved:** Physical Termux canonical mailbox launcher/PID cwd and private outbox/collision preview, actual live source update to the newest SHA, shell startup profile contents, protected mixed-case `ai` installation, service restart/reboot persistence and iPhone acceptance remain **UNVERIFIED**. The existing private bridge must report the new action as loaded before using it; an unknown-action rejection is not a shell access failure. Never install, restart, copy private state, auto-start cloud inference or change the original `ai` launcher without the distinct owner approval gates in [#71](https://github.com/shawnfra2013/Oden2-/issues/71). Preserve earlier observations and do not repeat the expired-ping investigation.

## November 23 issue #71 verified transport and CLI review candidate

**Transport:** private request `b7102026112314520000000000000001` (ping) received `status=complete`, `action=ping`, `result.alive=true` at 14:53:18 UTC; it reported device-side PID 31499, source `0a9538a0a02576a70faaf4c4691c276ab1d338ad`. Private request `b7112026112314552400000000000001` (mailbox_audit) received `status=complete` at 14:56:39 UTC and reported 1 matched, 1 pending, 0 stalled, 0 audit incidents in its scope, and the same source revision. The earlier ping `3c63d6ac4953bba8df7c5f66aa18bda0` returned expired at 14:48:25 UTC. **A fresh bidirectional device response has now been observed**; the running Termux service launcher path and /proc/PID/cwd have NOT been independently inspected from this chat and still need physical issue #71 preflight. The old temporary checkout remains preserved. Do not automatically migrate, restart, discard journals or install code.

**Terminal:** [issue #148](https://github.com/shawnfra2013/Oden2-/issues/148) / **merged** [PR #149](https://github.com/shawnfra2013/Oden2-/pull/149) added optional read-only colored snapshot/watch based on local runit/queue/cwd and polled PUBLIC GitHub main/CI/issues, with no cloud model, phone stream, device command or alias install. Merged source SHA `a692b5fe9a63da045a104ade9dcc56920d440777` passed its exact-main Odin Checks, browser acceptance, and CodeQL Python/JavaScript. **Post-merge:** new private `ping` request `b7122026112315074400000000000001` completed at **15:08:39 UTC** (`alive=true`, PID 31499), but the running mailbox still reported **older source** `0a9538a0a02576a70faaf4c4691c276ab1d338ad`. Thus the new CLI and its command wrapper are **NOT VERIFIED INSTALLED** on Odin. Run the read-only migration/checkout preview, inspect canonical/private state and obtain specific owner approval before any source update, service restart or launcher migration. Watch mode cannot display ChatGPT's internal tool-call stream.

## November 23 five-upgrade source delivery — not a device release

The user approved five free-first improvements; the reviewed GitHub source now contains the following **bounded foundations**, each with exact-head passing PR tests: (1) private request-bound ping verifier [#143](https://github.com/shawnfra2013/Oden2-/pull/143) plus existing manual private workflow; (2) scoped Codespaces/local coding-agent task handoff [#144](https://github.com/shawnfra2013/Oden2-/pull/144), which does not start or authenticate a workspace; (3) event-to-review correlation [#135](https://github.com/shawnfra2013/Oden2-/pull/135), freshness-gated supervision [#138](https://github.com/shawnfra2013/Oden2-/pull/138), and claimed-stage timeline [#146](https://github.com/shawnfra2013/Oden2-/pull/146); (4) two-round repair gate [#136](https://github.com/shawnfra2013/Oden2-/pull/136), held-out comparison [#137](https://github.com/shawnfra2013/Oden2-/pull/137), and the same source-only dashboard; (5) pending encrypted phone message reconnection and fixed rejected/expired response states [#145](https://github.com/shawnfra2013/Oden2-/pull/145).

The source merges also include the mandatory session guide [#142](https://github.com/shawnfra2013/Oden2-/pull/142). The last functional main source merge observed before this documentation update was `9304fa0d37023c4316d5330bc413738868fd36a2`. Verify the **final docs merge SHA and push CI separately** before an approved device update. The private outbox still showed `65e71811898b9a97656ece80ece4d655cea9ce10`, and the recent request `3c63d6ac4953bba8df7c5f66aa18bda0` had **no matching response visible** at the latest source-side read. This is an UNVERIFIED live device connection; do not claim an installed revision, functioning shell, agent training, active Codespaces or iPhone cellular success.

**Release order:** first inspect the canonical `odin-private-mailbox` process and dry-run [#71](https://github.com/shawnfra2013/Oden2-/issues/71) state-preserving migration, obtaining operator approval before a service change. Then prove fresh ping and mailbox audit; then a real authenticated agent task PR/revision functional test, source-backed on-device recall and unseen held-out model benchmark. The paired iPhone over-cellular test is independently required. No unattended deployment or extra paid cloud service was activated.

## Continuity update — GitHub-only observation, November 23, 2026

Read [Working with Odin](WORK_WITH_ODIN.md) at session start. This review extends the read-first guide and reconciles prior parallel documentation PRs #139 and #142 into one review branch. At the review cutoff public `main` was `6585082b09acde9dedac2bdb3f375f372abe58f1` with successful exact-SHA GitHub source checks. A new bounded private `ping` request ID `3c63d6ac4953bba8df7c5f66aa18bda0` was submitted to the private inbox at 13:37:09 UTC; the matching response was **not yet visible at the last read**, and the private outbox head was `65e71811898b9a97656ece80ece4d655cea9ce10` (08:23:08 UTC). This is **UNVERIFIED** device connectivity, not a failed or successful live device execution. Refresh the private response/outbox before drawing a new conclusion; expiry alone does not establish cause. No remote shell, Codespaces session or model training was activated by this documentation work.

The previously observed private mailbox launcher/process working-directory mismatch remains a separate physical [#71](https://github.com/shawnfra2013/Oden2-/issues/71) acceptance gate. Source documentation, CI and PR events do not move that running service. First obtain a fresh read-only preview and operator decision, then a matched new `ping` and `mailbox_audit`; afterward validate a supervised issue #99 coding cycle and issue #122 local recall. The [private mailbox runbook](ODIN_GITHUB_BRIDGE.md) controls safe request shape and migration.

## Verified Git project memory (not automatic model recall)

The current sanitized, source-backed memory checkpoint is [November 23 verified collaboration memory](audits/ODIN_VERIFIED_MEMORY_2026-11-23.md); the read-first index and retention rules are in [project memory](PROJECT_MEMORY.md). These documents preserve decisions, the newest relevant GitHub PR/receipt IDs, observed errors, tested fixes, and remaining physical gates. They do **not** mean the device model automatically loads them, that its ignored local state is backed up to public Git, or that a reviewer comment triggered an agent action. Confirm a fresh SHA/receipt before treating a saved checkpoint as live.

## Source-backed local recall (operator rollout pending)

[Memory issue #122](https://github.com/shawnfra2013/Oden2-/issues/122) tracks a source-only SQLite FTS5 index of curated Git project notes. The existing orchestrator can add up to two excerpts as untrusted **data** on a new user question, without starting a separate model request. This is a reviewed-source capability only until the exact code is installed and the Android/Termux Python SQLite build and a real recall answer are verified. It does not retrain the model or import private mailbox content. See [project memory](PROJECT_MEMORY.md).

## Canonical architecture

- [Current runtime truth](ODIN_RUNTIME.md) and [source/workflow rules](../ODIN_WORKFLOW.md) control the supported stack.
- Development: Termux terminal on Odin (offline-capable), GitHub Actions for source CI, optional manually started GitHub Codespaces terminal (online only); no separate editor installation.
- Communications: current [private GitHub mailbox](ODIN_GITHUB_BRIDGE.md), using separate request/response branches. Queued offline source-test receipts are sent through the **same** authenticated private outbox. It is not an arbitrary command channel.
- Local browser: **Odin Local Workstation**. Historical source/service identifiers remain compatibility names only.
- Tailscale is the selected private network; approved HTTPS viewer access from the iPhone remains an operator-owned live acceptance step. The saved iPhone shortcut may still point to a historical origin; follow [shortcut cutover](SHORTCUT_CUTOVER.md).

## Physical Odin integration results — November 23, 2026

The handheld's last explicitly reported source SHA during live bridge testing was `89e758ec78099486abbab7c57af5c8fe26e58cc8`. The newer functional source fixes are merged to GitHub main but are **not thereby proven installed or loaded by its running Python services**.

| Exercise | Observed result |
| --- | --- |
| Online terminal source-test receipt `8642f52105aa4508830d906c6cbc472d` | All seven checks PASS; matched the private GitHub outbox |
| Offline-created receipt `f0935b4308f74c51a32a014bbec3390b` | PASS; same ID uploaded once after reconnect |
| Fresh private ping `6bd037ac91e44aa09cb831f1d75e8f02` | Matching complete receipt, reported alive, device SHA, last source upload |
| Private staging write/readback | PASS; 52-byte payload/hash matched |
| Local workstation health | PASS; ready, local model selected |
| Bounded source-aware local question | PASS; model matched answer, HTTP 200 |
| Bounded coding expression | Model returned correct expression with inline backticks; older checker marked mismatch — fix in PR #112 |
| Device regression details | Python suite had one failure: disposable mailbox test read the real local offline source queue — fix in PR #110; workstation suite and Ruff passed |
| Invalid shell action, unexpected request field, expired request | Correctly rejected or expired; no arbitrary command execution |
| Private review note | Device stored and acknowledged request; `action_executed=false`; **agent read and implementation not established** |
| Local practice request | Nine-case notebook already finished; six reviewed passes, three misses, not a new exercise |

This table records observations at the cited private receipt times. Do not copy private response payloads into public issues or release artifacts.

## Merged source work and current boundary

- [PR #104](https://github.com/shawnfra2013/Oden2-/pull/104): portable terminal source checks.
- [PR #109](https://github.com/shawnfra2013/Oden2-/pull/109): durable offline-to-private source receipt synchronization.
- [PR #110](https://github.com/shawnfra2013/Oden2-/pull/110): isolated recovery regression fixture. Source validation passed; physical retest after install pending.
- [PR #112](https://github.com/shawnfra2013/Oden2-/pull/112): coding-review inline-code normalization. Source validation passed; physical retest pending.
- [PR #111](https://github.com/shawnfra2013/Oden2-/pull/111): first coding-coordination module (local exclusive task leases). Source validation passed; this is not distributed locking or self-directed coding. The functional main merge was `88303d7875c898cbebe2a1f6aa87d6700c81cbce` before this documentation update.

The bridge **does not yet provide** an authenticated general remote shell or automatically start a Codespace. A received feedback note is not proof of local agent read, generated change, or independently reviewed PR. Priorities and issue states remain in [the single task board](TASK_BOARD.md).

## Collaboration and incident audit continuation

The November 23 stress-test observations, including the eight-message backlog (8/8 replies over two polling cycles), branch limits, rejected command injection, source fixes, exact receipts and missing ChatGPT push wake-up are in [the dated collaboration trial ledger](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md). An offline-capable, on-demand private mailbox auditor merged in [PR #114](https://github.com/shawnfra2013/Oden2-/pull/114). Run it only from an approved checkout with `python -B scripts/odin_mailbox_audit.py --hours 1 --save`. Its local snapshots do **not** establish live ChatGPT wake-up or autonomous Odin coding.

## Merged bridge diagnostics awaiting physical update

A scoped `mailbox_audit` private action lets ChatGPT request a read-only, redacted, last-hour inbox/outbox correlation through the existing private GitHub mailbox. It cannot run arbitrary CLI commands and is not an instant ChatGPT wake-up. The audited source implementation merged in [PR #115](https://github.com/shawnfra2013/Oden2-/pull/115). The current release must be installed and the service reloaded under the normal release gate before live testing the action. Source tests are not device installation evidence.

## Pending local feedback presentation acceptance

The review-feedback CLI gained a merged [PR #116](https://github.com/shawnfra2013/Oden2-/pull/116) `--inspect ID` path that creates an immutable, **non-executing** tool-presentation record, and the private mailbox can asynchronously forward its metadata. The reviewed source checks passed. Real tool presentation remains a separate event after owner-approved checkout/reload, with a fresh private outbox receipt. The acknowledgment does not certify an AI identity or action. The next test should use a new bounded review note and independently verify both the original storage response and the separate tool-presentation receipt.

## Current device delivery delay

A fresh read-only ping (`c0ad2026000000000000000000000009`) sent after the new source merges had **no matching private outbox response after at least 150 seconds**, while the outbox's last observed commit remained at 07:35:29 UTC. Record this as a delivery stall, not proof of a device shutdown or a failed installation. Before live rollout, collect a new read-only Termux service/status observation or a later matching response. See incident B-018 in [the trial ledger](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md).

## Latest physical bridge launcher discovery

At 2026-11-23 08:20–08:23 UTC, a read-only Termux check confirmed that the active `odin-private-mailbox` runit launcher and process cwd were in `~/odin-pr45-test.iwGRYw` rather than the canonical `~/odin-workspace`. The previous missing `agent.log` was a lookup under the wrong state directory. Both checkouts had Git SHA `d12f965128bc3ef479c00e1fdc85546371a46d93`. The private staging outbox was clean, with zero unpushed commits and neither pending receipt journal; canonical outbox was absent. A fresh matching ping completed at 08:21:59 UTC, and the allowlisted remote mailbox audit completed at 08:23:08 UTC (12 considered, 11 matched, one pending, zero stalls; longest reply 756s). The cause of the earlier delay remains unknown.

**Next operator gate:** preserve private outbox/history and launcher backup, migrate only the private mailbox state/launcher to the canonical checkout, and restart only the private mailbox runit service after a final collision check. Never remove staging logs, reset branches or overwrite canonical private state. The device preflight now reports FAIL when either the launcher or running process uses a noncanonical checkout. See [private mailbox runbook](ODIN_GITHUB_BRIDGE.md).

## November 23 progressive upgrade checkpoint — source versus device

The newest source features are all through reviewed, green PR-head checks: [#123 local searchable project memory](https://github.com/shawnfra2013/Oden2-/pull/123), [#124 GitHub PR event head-SHA receipts](https://github.com/shawnfra2013/Oden2-/pull/124), [#125 long-lived PR base checkout repair](https://github.com/shawnfra2013/Oden2-/pull/125), and [#126 metadata-only private bridge trace](https://github.com/shawnfra2013/Oden2-/pull/126). The latest functional GitHub main merge before this documentation update is `c548d3e5c8c1368093ea6df080e0037f908323e6`. A real [GitHub event run 45148206068](https://github.com/shawnfra2013/Oden2-/actions/runs/45148206068) stored an artifact for draft PR #119's exact event head SHA. The prior failed run 45147217823 is retained as a test defect, not erased.

**Physical installation remains distinct:** the last operator-confirmed canonical checkout was `0abab1045650cd6cb8968c61ced4b027974f42b2`, and the private mailbox service last proved running from temporary `odin-pr45-test.iwGRYw`. Do not automatically update, migrate, restart or claim memory ingestion/trace records from GitHub source alone. First follow the [state-preserving launcher migration runbook](ODIN_GITHUB_BRIDGE.md), keeping private outbox history and untracked files. A newly observed matching ping, exact source SHA, running PID/cwd, local memory recall and trace summary are required afterward. Work technical comments on #119/#120 beyond the original PR-open review are not yet independently evidenced.

## Guarded private mailbox launcher migration utility (source only)

A source-reviewed helper now exists at `scripts/odin_mailbox_migrate.py`. Preview mode (`--expected-sha SHA`, without `--apply`) verifies the live launcher and PID/cwd, canonical source SHA, tracked file cleanliness, pending private receipts, private outbox Git branch/remote and unpushed commits, stale copy directories and destination collisions. The **separate operator-owned** `--apply --confirm MIGRATE-ODIN-MAILBOX` is designed to back up the old launcher, stop **only** `odin-private-mailbox`, repeat receipt checks, copy (never delete) private state, atomically repoint the launcher and restart with rollback on failure. Unit tests use entirely fake filesystem and runit interfaces. Until an actual approved device preview and application are observed, the launcher remains **UNVERIFIED / not migrated**. See [private mailbox runbook](ODIN_GITHUB_BRIDGE.md) and [issue #71](https://github.com/shawnfra2013/Oden2-/issues/71).

## Next controlled acceptance sequence

1. Review exact GitHub main SHA and associated Actions checks after the final docs merge; preserve untracked owner files.
2. With operator approval, safely update the canonical Odin checkout and reload only the existing private mailbox service if its code changed; do not infer a process reload from `git pull`.
3. Request a fresh `regression_details` and bounded coding-review receipt; compare each with the earlier failure and the exact installed source SHA.
4. Prove source-task coordination locally through the reviewed lease tests; cross-device/shared lease ownership is future work, not a claim of the current module.
5. For feedback, obtain a separate agent-tool-read acknowledgment and an actual in-scope agent-generated PR with exact-SHA CI. Do not promote the recorded-only private receipt to those stages.
6. Complete private routing and iPhone cellular viewer acceptance as a separate owner-driven test.

**Safety invariant:** No force-push, silent device reset, secret exposure, paid inference, unrestricted remote shell or unreviewed automatic deployment.
