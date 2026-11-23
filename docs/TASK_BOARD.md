# Odin GitHub task board

**GitHub Issues is the work queue.** Do not create a competing backlog in older stage documents. Each issue progresses **Planned → In progress → Tests passed → Device verified → Closed**, based on linked evidence. A completed GitHub test is not a physical Odin or iPhone verification.

## Integrated priority list — 20 improvements

**Single priority queue:** The fifteen originally approved feature items are all preserved in their existing relative order, with five new reliability/supervision safeguards from [parent proposal #96](https://github.com/shawnfra2013/Oden2-/issues/96) inserted where they reduce rework and risk. Ranking is by dependencies and practical usefulness, **not** by issue number. The five safeguards have their own issues #97–#101. No item below is authorized for unsupervised Codespaces startup, paid inference, live device modification or production deployment.

**Important scope:** Finish the current two-way feedback source bridge, free GitHub automation and separate physical acceptance before autonomously scheduling the ranked queue. GitHub Issues is the authoritative work queue. **AI/GitHub can prepare code, review receipts and source CI evidence within approved task scope; the operator controls account spending, credential/permission changes, physical Odin updates and actual iPhone cellular tests.** An operator-only acceptance task is not permission for an agent to perform it.

| Priority | GitHub issue / improvement | State | Implementation vs operator responsibility | Evidence to advance |
| ---: | --- | --- | --- | --- |
| 1 | [#97 — Exclusive task leases & conflict prevention](https://github.com/shawnfra2013/Oden2-/issues/97) | Planned | AI/GitHub; operator approves new scope | One owner/branch/base SHA per issue; concurrent and stale claims rejected |
| 2 | [#98 — Task quality & change-scope contract](https://github.com/shawnfra2013/Oden2-/issues/98) | Planned | AI/GitHub; operator approves expanded scope | Approved files, invariants and tests; catch removed tests and unrelated edits |
| 3 | [#86 — End-to-end request correlation](https://github.com/shawnfra2013/Oden2-/issues/86) | Planned | AI/GitHub; operator tests live route | Trace browser → mailbox → device → model with private IDs and timeout/replay cases |
| 4 | [#99 — Prove feedback received, read, acted on & verified](https://github.com/shawnfra2013/Oden2-/issues/99) | Planned; bridge source in #95 | AI/GitHub; operator verifies real device | Distinct receipt stages; exact task/SHA, fresh device and source evidence |
| 5 | [#80 — Authoritative service/port registry](https://github.com/shawnfra2013/Oden2-/issues/80) | Source merged in #73; device unverified | AI/GitHub; operator verifies live listeners | Detect missing launchers, duplicate ports and stale paths |
| 6 | [#81 — One read-only preflight](https://github.com/shawnfra2013/Oden2-/issues/81) | Source merged in #73; device unverified | AI/GitHub; operator authorizes device inspection | Dated PASS/FAIL/UNVERIFIED and strict unknown-state exit status |
| 7 | [#82 — Dependency, secrets & least privilege](https://github.com/shawnfra2013/Oden2-/issues/82) | Planned; automation in development | AI/GitHub; operator approves credentials/permissions | Detect vulnerable dependencies, exposed secrets, over-broad permission scopes |
| 8 | [#101 — Codespaces cost & stall watchdog](https://github.com/shawnfra2013/Oden2-/issues/101) | Planned | AI/GitHub; operator sets billing/spending caps | Detect missing heartbeat, over-budget risk, stale work; no auto-start |
| 9 | [#79 — Actual local inference readiness](https://github.com/shawnfra2013/Oden2-/issues/79) | Planned | AI builds checks; operator approves physical test | One bounded real model answer; HTTP listener alone insufficient |
| 10 | [#75 — One authoritative model route](https://github.com/shawnfra2013/Oden2-/issues/75) | Source merged in #85; device unverified | AI/GitHub; operator verifies installed behavior | Reject inconsistent or stale model/provider selection |
| 11 | [#87 — Fault injection & recovery tests](https://github.com/shawnfra2013/Oden2-/issues/87) | Planned | AI/GitHub | Offline, lost network, process crashes, malformed replies and replays produce actionable errors |
| 12 | [#100 — Bounded failure triage & repair proposals](https://github.com/shawnfra2013/Oden2-/issues/100) | Planned | GitHub diagnoses; authorized coding agent patches | Exact failing step, limited retries, tests; escalate after 2 revision rounds |
| 13 | [#88 — Verified backups & restore rehearsal](https://github.com/shawnfra2013/Oden2-/issues/88) | Planned | AI creates source tests; operator approves data handling | Checksums, retention, isolated restoration without private-data exposure |
| 14 | [#89 — Safe update verification & rollback](https://github.com/shawnfra2013/Oden2-/issues/89) | Planned | AI builds source; operator authorizes real install/recovery | Exact SHA, post-update checks, pause on failure, no force reset |
| 15 | [#90 — Hardware resource guardrails](https://github.com/shawnfra2013/Oden2-/issues/90) | Planned | AI builds source; operator checks actual device sensors | Bounded memory/storage/thermal/battery and UNVERIFIED missing data |
| 16 | [#84 — Performance & battery baseline](https://github.com/shawnfra2013/Oden2-/issues/84) | Planned | AI develops test harness; operator performs physical run | Reproducible latency, energy and memory measurements on Odin |
| 17 | [#83 — Offline work & reconciliation](https://github.com/shawnfra2013/Oden2-/issues/83) | Planned | AI/GitHub; operator approves live edits | Offline queue and UI edits, deterministic conflict/duplicate handling |
| 18 | [#77 — Explicit offline/online model choice](https://github.com/shawnfra2013/Oden2-/issues/77) | Planned | AI builds UI; operator approves any paid provider | Local free default, no silent paid fallback, explicit cost guard |
| 19 | [#76 — Private phone route + mailbox](https://github.com/shawnfra2013/Oden2-/issues/76) | Planned | AI builds code; operator approves network/security settings | Approved Tailscale HTTPS route and fresh matched private replies |
| 20 | [#78 — Encrypted iPhone auto-resume](https://github.com/shawnfra2013/Oden2-/issues/78) | Planned | AI builds code; operator performs cellular acceptance | Trusted reopen, refresh and pending-message recovery with encrypted response |

**Reporting rule:** a missing, stale, or unreachable source is **UNVERIFIED**; a demonstrated defect is **FAIL**. Neither counts as passing. Every item needs exact revision, relevant test, and an explicit device/phone acceptance record before closure.

## Supporting delivery and research work

| Issue | State | Completion evidence |
| --- | --- | --- |
| [#69 — iPhone over cellular](https://github.com/shawnfra2013/Oden2-/issues/69) | Planned | Wi-Fi disabled, Home Screen reopen and one matched encrypted reply |
| [#70 — Tailscale HTTPS](https://github.com/shawnfra2013/Oden2-/issues/70) | Planned | Private route verified from both devices |
| [#71 — Exact-revision rollout](https://github.com/shawnfra2013/Oden2-/issues/71) | Planned | Installed SHA, services and fresh mailbox receipt |
| [#72 — Documentation and release operations](https://github.com/shawnfra2013/Oden2-/issues/72) | In progress | Reviewed PR, exact-SHA CI, dated handoff |
| [#91 — Free GitHub automation](https://github.com/shawnfra2013/Oden2-/issues/91) | In progress | Dependabot, CodeQL, nightly evidence, optional Codespaces, manual source release |
| [#92 — Native Android 10 integration](https://github.com/shawnfra2013/Oden2-/issues/92) | Source merged in PR #93; device unverified | Read-only hooks inventory, permission matrix, then authorized companion/device tests |
| [#94 — Two-way private review feedback](https://github.com/shawnfra2013/Oden2-/issues/94) | Source merged in PR #95; physical round-trip unverified | Receive/store/acknowledge private feedback, then separately prove read/action with #99 |
| [#96 — Collaboration safeguards umbrella](https://github.com/shawnfra2013/Oden2-/issues/96) | Split into prioritized #97–#101 | Parent for the five additional safeguards; **not a 21st ranked task** |

## Working rules

Create new tasks using [the issue template](https://github.com/shawnfra2013/Oden2-/issues/new/choose), specify an owner, test and a blocker, and link relevant PRs. **Ordinary pushes and CI do not require repeated operator permission.** Installing or operating sensitive Android functionality, changing security settings, deleting data and destructive rollback require specific review. Do not close issues because code is pushed or CI passes.

Read [the current handoff](HANDOFF.md), [release gates](RELEASE_GATES.md) and [status](PROJECT_STATUS.md) before rollout. Public [open issues](https://github.com/shawnfra2013/Oden2-/issues?q=is%3Aissue+is%3Aopen) are authoritative for per-task status.
