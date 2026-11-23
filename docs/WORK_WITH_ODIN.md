# Read first · Working with Odin 2

At the start of every Odin session, read this file. Identify the active issue, current GitHub main revision and most recent matching private receipt before making a claim about the handheld. Use the existing connection yourself when available. Shawn should only need to step in for a physical observation, a permission decision or a real blocker.

## Who does what

| Owner | Work | Evidence |
| --- | --- | --- |
| ChatGPT or Codex | Inspect current source and private receipts, submit approved bounded checks, diagnose failures, make scoped repairs on a branch and run tests. | Exact request ID, observed time, result, PR head SHA and check links. |
| GitHub | Store reviewed source, run CI, carry private requests and replies, retain offline source-check receipts. | Source commit, exact-head workflow result, private outbox object. |
| Odin in Termux | Poll the private inbox, validate requests, run supported device actions, publish replies, and replay queued source receipts after reconnection. Run local models and the supervised worker when configured. | A newly matched result for the specific action, with revision and process information where supplied. |
| Shawn | Set priorities and spending choices, approve sensitive changes, perform physical operations and real iPhone acceptance when needed. | Device preflight, observed service working directory, or phone result tied to the test. |

## Talk to Odin as live as the bridge allows

1. Use the authenticated private repository `shawnfra2013/Odin-private-bridge`. Prefer its private mailbox workflow. With an authorized GitHub connection, the same bounded request can be written directly to branch `odin-bridge-inbox` at `bridge/requests/<id>.json`. The source repository is `shawnfra2013/Oden2-`. Check the target repository and branch before every write.
2. For liveness use `ping`. Generate the ID with `uuid.uuid4().hex`. Require exactly 32 lowercase hexadecimal characters and use the same ID in the filename and payload. The base fields are `version` (integer 1), `id`, `action`, `created_at` and `expires_at`. Use current UTC, a short positive expiry of at most one hour, and validate against the checked-out bridge before sending. Additional fields depend on the action. A 31-character filename is skipped before execution.
3. Save the submission SHA, ID, action and expiry. The service normally polls about once per minute while connected. Follow **the same ID** on branch `odin-bridge-outbox` at `bridge/responses/<id>.json`. Use a bounded wait and check near expected completion. Avoid duplicate requests. An absent file means no matching response was visible at that check.
4. Verify ID, action, status, checked time and the action-specific result. A passing ping requires `complete` and `result.alive == true`. Record the reported revision and PID when available. For local coding, inspect `stage5_coding_review`, HTTP status and `match`. A healthy listener proves less than a correct model answer. For phone chat, require successful decryption in the paired browser.
5. On delay, inspect private inbox acceptance, expiry and outbox activity. Use `mailbox_audit` when reachable. If the service cannot reply, use the on-device read-only preflight and check the live PID's working directory. A previously observed launcher ran from a temporary checkout. The guarded migration runbook preserves state and requires a fresh operator preview. A GitHub push alone cannot move a running process. [Mailbox runbook](ODIN_GITHUB_BRIDGE.md)

### Which action to use

| Need | Private actions on the audited source |
| --- | --- |
| Reachability, workstation, and transport | `ping`, `stage5_health`, `staging_probe`, `mailbox_audit`. The staging probe performs a bounded write/readback. |
| Local model evidence | `stage5_note_check`, `stage5_source_check`, `stage5_coding_review`. Finite practice uses `practice_next` and `practice_followup` and records outcomes. |
| Private user conversation | `encrypted_chat` with a paired browser and a sealed payload. Ordinary diagnostic requests cannot stand in for this conversation. |
| Review and diagnosis | `review_feedback` stores a bounded note. `regression_details` runs defined diagnostics. Verify what the running revision actually supports. |
| Separate authorization | `install_offline_model` is an installation tied to an exact SHA. `inference_probe` is a separately configured hosted diagnostic that can incur cost. Use the local checks for ordinary verification. |

A **ping** checks liveness. A **receipt** records one outcome. A **pairing code** is entered once in a trusted browser for encrypted chat. A **saved unlock password** unlocks the browser's local credential vault. Keep both secrets out of chats, Git and screenshots. A **pinned excerpt** is Shawn's separate request to preserve selected chat text in the sidebar. Treat its delivery as open until demonstrated. An **exact SHA** identifies the source revision being evaluated.

## What has been demonstrated and what remains

| Capability | Evidence available | Acceptance still due |
| --- | --- | --- |
| Two-way private transport | Eight requests completed in a burst. A ninth ping arrived after 756 seconds. Online and offline source receipts were matched after reconnection. | A fresh matching reply for today's request, canonical live process location and private trace after reload. |
| Local inference and conversations | A bounded source-aware question historically returned HTTP 200 with the expected answer. The workstation and CLI support local chat, bounded history and persistent conversations. | Current model identity and result, Wi-Fi-off device check, current latency and resource baseline. |
| Coding proposals and memory | Worker creates isolated proposals. Independent syntax/Ruff checks, AST critique and same-target lesson reuse have source tests. Local SQLite FTS5 retrieves curated project notes. | Three source-backed answers on the handheld and one unseen task with saved first attempt, feedback-driven revision and independent functional tests. |
| Collaboration | A review note was stored. A PR event triggered Work activity. GitHub can retain event-SHA evidence. | Correlate authenticated agent read, proposed action, changed files, exact revision, independent CI and review. A note stored or displayed establishes only that stage. |
| Updates, services and recovery | Source supports CI-gated updates, supervised services, offline queues, recovery and scoped restart checks. | Installed SHA, running SHA, post-restart health and restore rehearsal. Boot automation was deferred by Shawn. |
| Phone, browser and Android | Source includes encrypted phone chat, reconnect/refresh, browser credential storage, local notes, snippets, offline edits to three UI settings, focused controller bindings, and browser-dependent voice controls. | Real iPhone Home Screen reopen and refresh on cellular, private HTTPS, one decrypted reply, offline edit reconciliation, and device-specific input/voice checks. |
| Model training | A candidate-adapter trainer exists for approved data and a compatible model. | Approved examples, compatible compute, separate held-out functional benchmark, baseline comparison and a promotion decision. No verified weight update. |

## Best next steps

First restore a dependable feedback path. Establish the canonical live checkout, obtain one fresh ping and mailbox audit, then one bounded local inference receipt. Next verify local recall and run one unseen coding task end to end. Preserve the first attempt, critique, revised attempt, tests and independent review. Then prove the phone route on cellular. Keep the existing ranked queue and the operating limits in the [task board](TASK_BOARD.md) and [workflow](../ODIN_WORKFLOW.md). The [verified checkpoint](audits/ODIN_VERIFIED_MEMORY_2026-11-23.md) contains the historical evidence.

## Close each work session

Record UTC time, source branch and SHA, installed or reported device SHA if observed, issue/PR, exact tests, receipt IDs, missing evidence and the next safe action. Keep private details in the private handoff. Update the dated checkpoint when evidence changes. Preserve old failures and their fixes. Give Shawn a short answer covering what worked, what is still blocked, and any physical step he alone can perform.
