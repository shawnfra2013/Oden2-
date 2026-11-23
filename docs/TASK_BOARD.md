# Odin GitHub task board

**GitHub Issues is the work queue.** Do not create a competing backlog in older stage documents. Each issue progresses **Planned → In progress → Tests passed → Device verified → Closed**, based on linked evidence. A completed GitHub test is not a physical Odin or iPhone verification.

## Ordered list of 15 improvements

The sequence below is **priority and dependency order**, not the GitHub issue number. Work that provides diagnostics, safety and a trustworthy release foundation comes before polish. Separate small PRs can run in parallel where they do not conflict.

| Rank | Issue | State | Why it comes here / deterministic acceptance |
| --- | --- | --- | --- |
| 1 | [#86 — End-to-end request correlation](https://github.com/shawnfra2013/Oden2-/issues/86) | Planned | Trace browser → mailbox → device → model with privacy-safe IDs, timeouts, duplicate and missing-receipt tests |
| 2 | [#80 — Authoritative service/port registry](https://github.com/shawnfra2013/Oden2-/issues/80) | Tests passed in PR #73; device unverified | Detect missing launchers, duplicate ports and stale paths; verify actual listeners on the handheld separately |
| 3 | [#81 — One read-only preflight](https://github.com/shawnfra2013/Oden2-/issues/81) | Tests passed in PR #73; device unverified | Dated PASS/FAIL/UNVERIFIED on source and real device, explicit exit status, no paid model calls |
| 4 | [#82 — Dependency/secrets and least privilege](https://github.com/shawnfra2013/Oden2-/issues/82) | Planned | Inventory dependencies and permission scopes; CI rejects secrets and uncovered vulnerabilities |
| 5 | [#79 — Actual local inference readiness](https://github.com/shawnfra2013/Oden2-/issues/79) | Planned | Test a genuine bounded model answer on Odin; a TCP/HTTP listener alone is insufficient |
| 6 | [#75 — One authoritative model route](https://github.com/shawnfra2013/Oden2-/issues/75) | Tests passed in PR #85; device unverified | Mismatched or stale model selection fails clearly, not by silently switching providers |
| 7 | [#87 — Fault injection/recovery test suite](https://github.com/shawnfra2013/Oden2-/issues/87) | Planned | Offline and mocked lost-network, process, malformed-response and replay scenarios produce actionable errors |
| 8 | [#88 — Verified backups and restore rehearsal](https://github.com/shawnfra2013/Oden2-/issues/88) | Planned | Checksum-backed backups, retention and isolated restore proof without revealing private data |
| 9 | [#89 — Safe update verification and rollback](https://github.com/shawnfra2013/Oden2-/issues/89) | Planned | Exact SHA, post-update checks, rollout pause and recoverable revision; never force reset |
| 10 | [#90 — Hardware resource guardrails](https://github.com/shawnfra2013/Oden2-/issues/90) | Planned | Bounded memory/storage/thermal/battery decisions with missing sensor data UNVERIFIED |
| 11 | [#84 — Performance and battery baseline](https://github.com/shawnfra2013/Oden2-/issues/84) | Planned | Reproducible latency, power and memory baseline measured on real Odin |
| 12 | [#83 — Offline work and reconciliation](https://github.com/shawnfra2013/Oden2-/issues/83) | Planned | Queue offline work and UI edits; deterministic conflict resolution and duplicate protection |
| 13 | [#77 — Explicit offline/online model choice](https://github.com/shawnfra2013/Oden2-/issues/77) | Planned | Free local default; no silent paid fallback; deliberate mode and cost guard |
| 14 | [#76 — Private phone route + mailbox](https://github.com/shawnfra2013/Oden2-/issues/76) | Planned | Real approved Tailscale HTTPS path and separate matched private diagnostic receipts |
| 15 | [#78 — Encrypted iPhone auto-resume](https://github.com/shawnfra2013/Oden2-/issues/78) | Planned | Trusted-device reopening, refresh, pending-message recovery and actual cellular encrypted response |

**Reporting rule:** a missing, stale, or unreachable source is **UNVERIFIED**; a demonstrated defect is **FAIL**. Neither counts as passing. Every item needs exact revision, relevant test, and an explicit device/phone acceptance record before closure.

## Supporting delivery and research work

| Issue | State | Completion evidence |
| --- | --- | --- |
| [#69 — iPhone over cellular](https://github.com/shawnfra2013/Oden2-/issues/69) | Planned | Wi-Fi disabled, Home Screen reopen and one matched encrypted reply |
| [#70 — Tailscale HTTPS](https://github.com/shawnfra2013/Oden2-/issues/70) | Planned | Private route verified from both devices |
| [#71 — Exact-revision rollout](https://github.com/shawnfra2013/Oden2-/issues/71) | Planned | Installed SHA, services and fresh mailbox receipt |
| [#72 — Documentation and release operations](https://github.com/shawnfra2013/Oden2-/issues/72) | In progress | Reviewed PR, exact-SHA CI, dated handoff |
| [#91 — Free GitHub automation](https://github.com/shawnfra2013/Oden2-/issues/91) | In progress | Dependabot, CodeQL, nightly evidence, optional Codespaces, manual source release |
| [#92 — Native Android 10 integration](https://github.com/shawnfra2013/Oden2-/issues/92) | Tests passed in PR #93; device unverified | Read-only hooks inventory, permission matrix, then authorized companion/device tests |

## Working rules

Create new tasks using [the issue template](https://github.com/shawnfra2013/Oden2-/issues/new/choose), specify an owner, test and a blocker, and link relevant PRs. **Ordinary pushes and CI do not require repeated operator permission.** Installing or operating sensitive Android functionality, changing security settings, deleting data and destructive rollback require specific review. Do not close issues because code is pushed or CI passes.

Read [the current handoff](HANDOFF.md), [release gates](RELEASE_GATES.md) and [status](PROJECT_STATUS.md) before rollout. Public [open issues](https://github.com/shawnfra2013/Oden2-/issues?q=is%3Aissue+is%3Aopen) are authoritative for per-task status.
