# Odin verified collaboration memory — 2026-11-23

**Type:** Source-backed project handoff. **Verification status:** Public GitHub evidence plus explicitly identified operator-provided device observations. This file is **not** an automatically ingested model-memory database, a running-device heartbeat, or permission for a new task. GitHub issues and pull requests remain authoritative; this is a concise checkpoint with provenance.

## Durable storage boundaries

| Record | Where it belongs | What it does not prove |
| --- | --- | --- |
| Reviewed source and regression tests | Public `main` and reviewed PR commit SHA | Installed Android code, model learning |
| Sanitized decisions, defects and progress | Public [issues](https://github.com/shawnfra2013/Oden2-/issues), [task board](../TASK_BOARD.md), dated `docs/audits/` | Continuous execution or automatically updated local memory |
| Verified device request/reply receipts | Authenticated private `Odin-private-bridge` inbox/outbox | That an AI agent read or acted on the reply |
| Task queue, model conversations, diagnostics and journals | Device-local ignored `state/` directories | Publicly accessible Git backup or semantic retrieval |
| Current resume instructions | [Handoff](../HANDOFF.md), [runtime](../ODIN_RUNTIME.md), this dated memory checkpoint | Always-fresh runtime state without a new request |

**Privacy:** Never publish full private feedback, device paths containing secrets, token values, plaintext chat history, keys, or arbitrary logs. Commit only bounded, sanitized summaries and links to public evidence. The raw device journals remain private and should be backed up separately by an explicitly approved procedure.

## Verified milestones

- Source-only checks passed on both online and offline Odin receipts `8642f52105aa4508830d906c6cbc472d` and `f0935b4308f74c51a32a014bbec3390b`; the offline receipt was pushed to the private outbox after reconnection.
- Private mailbox two-way `ping`, health, staging probe and feedback storage were observed; a feedback storage receipt explicitly indicated `action_executed=false`.
- A burst of eight private requests completed over two polling cycles. A ninth request `c0ad2026000000000000000000000009` eventually completed after a 756-second delay. Its exact root cause is not established.
- Real GitHub event-triggered ChatGPT Work activity was observed when [draft PR #119](https://github.com/shawnfra2013/Oden2-/pull/119) opened: the separate Work task wrote [comment 7095797592](https://github.com/shawnfra2013/Oden2-/pull/119#issuecomment-7095797592). A duplicate delivery `218fc738-e71a-11f1-85f4-797094405109` did not write a second review. The original delivered event did not include an immutable event-time head SHA, so full event-SHA correlation remains unverified.
- Operator read-only inspection established that the active private mailbox runit launcher and Python process executed from a temporary checkout `odin-pr45-test.iwGRYw`, not the canonical `~/odin-workspace`. The missing canonical log was explained by this path mismatch. The old private outbox was clean with no pending journals or unpushed commits at inspection time.
- Physical canonical `~/odin-workspace` was successfully fast-forwarded to `0abab1045650cd6cb8968c61ced4b027974f42b2`, preserving reported untracked files. PR #118 added a CI-tested **read-only** device-preflight guard; updating the canonical Git checkout does not itself migrate the private mailbox launcher.
- Source fixes for private mailbox fixture isolation (#110), coding-answer backtick handling (#112), local task leases (#111), private mailbox audit (#114/#115), feedback presentation metadata (#116), and live evidence/docs (#117/#118) were merged to GitHub. Physical acceptance remains independent.

## Active progressive trial (snapshot, not live status)

- [Issue #99](https://github.com/shawnfra2013/Oden2-/issues/99) is the canonical 60-minute work/trial packet, including stop conditions and staged proof `submitted → device_received → agent_tool_read → action_proposed → code_changed → source_verified`.
- [Draft PR #119](https://github.com/shawnfra2013/Oden2-/pull/119): PR-open Work event proved on `a1fcb78262807e28133df131f6196a544b29990c`. Second **synchronize** source head `b6ba18ca86c1a8b5de2941a5b11aa0f55782f991`, request `ODIN-HOUR-SYNC-20261123-B`, passed three GitHub checks; a distinct Work review of that head was **not observed** at snapshot time.
- [Draft PR #120](https://github.com/shawnfra2013/Oden2-/pull/120): source head `a85301b1714d0eca98e190eb4b84dc3b9b9db32a`, request `ODIN-HOUR-CODE-20261123-C`; exact-head CI passed 3/3. Source fixes two task-contract quality gaps: unchanged `head_sha` and duplicate `changed_paths`. A separate event-triggered Work code review and physical Odin agent action were **not observed** at snapshot time.
- Limits: at most one technical review per PR head SHA; maximum two scoped revision rounds; stop on permission/security violations, missing evidence, out-of-scope paths or unapproved device changes. Batch routine results to avoid consuming unnecessary Work activations.

## Progressive upgrades verified later on 2026-11-23 (source/Actions only)

- **Local search-backed recall:** [PR #123](https://github.com/shawnfra2013/Oden2-/pull/123) merged at `afd3c4b294119742ddf0b85a875a1c855c6c2ffc`. It adds an allowlisted, private SQLite FTS5 index of canonical Git notes and inserts up to two bounded, untrusted excerpts into the **existing** orchestrator question request. It has source tests and requires no additional model call. **Physical Android FTS5 availability and an actual model recall remain UNVERIFIED.**
- **GitHub PR-event provenance:** [PR #124](https://github.com/shawnfra2013/Oden2-/pull/124) adds a read-only artifact workflow for marked `ODIN-HOUR` PR events. First live `synchronize` test on #119 failed in [run 45147217823](https://github.com/shawnfra2013/Oden2-/actions/runs/45147217823) because checkout of an older PR base SHA lacked the capture script. Corrected by [PR #125](https://github.com/shawnfra2013/Oden2-/pull/125), merge `ef5466016a4a03daf5469e940849bc9a5daf1b89`. New **actual event** [run 45148206068](https://github.com/shawnfra2013/Oden2-/actions/runs/45148206068) succeeded: its step log recorded head `825e5a1fb9edd88ef1ff1f1af6d56c74b71d7b2b`, PR #119, and run ID. GitHub confirmed a non-expired 492-byte artifact `odin-hour-event-119-45148206068-1` (ID `14804847590`). This proves an event-payload GitHub Actions SHA capture and artifact publication, **not** that separate ChatGPT Work delivery contained the SHA.
- **Private response observability:** [PR #126](https://github.com/shawnfra2013/Oden2-/pull/126), source merge `c548d3e5c8c1368093ea6df080e0037f908323e6`, adds a bounded, append-only 0600 private trace record after a mailbox response is published. It stores status, UTC, request ID, action, local SHA and action timing without payload content. Failures never turn a completed delivery into a failure. **Actual live-device trace creation remains UNVERIFIED until canonical launcher migration and approved source reload.**
- **Event-sourced coding agent remains unproved:** draft [PR #120](https://github.com/shawnfra2013/Oden2-/pull/120) passed 3/3 GitHub source tests but no authenticated Work reviewer-to-Odin coding-agent action receipt was observed at this checkpoint. Work activations are reserved for meaningful changes, not routine pings.

These milestones do not replace previous errors with retrospective PASS. The GitHub source of truth must be pulled and verified on the physical device separately.

## Immediate next acceptance steps

1. Complete the [issue #71](https://github.com/shawnfra2013/Oden2-/issues/71) private-mailbox runtime migration with operator approval only **after** rechecking pending state, preserving outbox and log history, and backing up the launcher. Confirm both new launcher and live process cwd match canonical, then perform a new private ping and mailbox audit.
2. Confirm an actual event-triggered Work review on the **new SHA** of PR #119, not the original opened-event comment or passing CI alone. Assess technical review feedback on PR #120; do not treat a source check as code-review completion.
3. Deliver bounded review feedback to the private mailbox, obtain a distinct matching stored acknowledgment, and separately prove the local coding agent's authenticated tool read and new reviewed source result. Never infer those stages from one another.
4. When the time-bounded supervised trial actually starts, record its **real start UTC**, absolute end UTC, source SHA and results. Review its hour-long packet in issue #99 and update the dated audit record with PASS/FAIL/BLOCKED. Don't mark it complete from a scheduled reminder alone.
5. After a reviewed source update, verify **real device recall** from the newly added #123 local FTS5 index against three source-backed facts. Do not treat merged retrieval source or unit tests as installed inference; retrieved text stays untrusted data, not instructions.

## Memory hygiene

Do not overwrite old dated checkpoints. Add a new dated summary or amend the latest through an exact-SHA reviewed PR when facts change. Preserve original Git commits and private receipts. Always mark **observed**, **source-only**, **device-unverified**, or **blocked**, along with a timestamp, issue/PR, and immutable evidence identifier. Never transform a missing or stale observation into a PASS.
