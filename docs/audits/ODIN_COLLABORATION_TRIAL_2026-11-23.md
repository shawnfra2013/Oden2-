# Odin live collaboration reliability trial — 2026-11-23

This is the sanitized, durable evidence ledger for the supervised ChatGPT ↔ GitHub ↔ Odin trials. GitHub Issues remain the authoritative task backlog. Private message bodies, credentials, model chats, and device addresses are intentionally not copied into the public project.

## Operating constraints

- Device: the existing Termux private mailbox polls approximately every **60 seconds** and processes **up to five request receipts** per cycle. It is asynchronous, not a direct remote shell.
- Reviewer: ChatGPT's currently installed scheduled receipt watcher operates **hourly**, not once per device message. A ChatGPT webhook subscription to private branch pushes was *not available* through this conversation's connected automation interface (event-source discovery returned an unavailable action). No instant reviewer wake-up is claimed.
- Development: GitHub source/CI and reviewed PRs are available through the authenticated connector. The chat does not currently have an attached interactive Codespaces terminal. A separate local sandbox could not resolve github.com, so direct terminal Git operations there were not used.
- Security: Do not add shell execution to untrusted mailbox messages, place private SSH keys in Codespaces, call paid models automatically, or install device changes without an approved release procedure.
- A complete local feedback-storage acknowledgment is **not** evidence the coding agent read the note, took an action, changed code, or passed CI.

## Evidence and incident ledger

| ID | Test or issue | Evidence / finding | Disposition |
| --- | --- | --- | --- |
| B-001 | Odin online source-test receipt | Exact private ID `8642f52105aa4508830d906c6cbc472d`, all seven source checks passed | PASS |
| B-002 | Odin offline store-and-forward | ID `f0935b4308f74c51a32a014bbec3390b` reached private outbox once after Wi-Fi restored | PASS |
| B-003 | Private reverse ping | Request `6bd037ac91e44aa09cb831f1d75e8f02` matched completion; device reported alive | PASS |
| B-004 | Read-only staging, local source and health | Staging hash, local source question and health matched private completion receipts | PASS |
| B-005 | Command-shaped / expired requests | `shell`, unknown `command` field, and expired requests were rejected or expired | PASS — security |
| B-006 | Feedback delivery | Private review note recorded/acknowledged; `action_executed=false` | PASS for storage; agent-read NOT demonstrated |
| B-007 | Coding expression check | Model returned a valid expression with inline backticks; old AST wrapper check marked mismatch | FIXED IN SOURCE PR #112; physical retest after rollout |
| B-008 | Device-only regression failure | Recovery integration test accidentally observed local device source receipts; source CI fixture had no such queue | FIXED IN SOURCE PR #110; physical retest after rollout |
| B-009 | Supervised coding module | Transactional local task leases: issue/branch/file conflicts, expiry, stale SHA, concurrency tests | SOURCE PR #111 merged; distributed coordinator/agent still future |
| B-010 | Live mailbox burst | Eight requests submitted together at 07:33:13 UTC on 2026-11-23. First five acknowledged 07:34:13–07:34:21, remaining three 07:35:25–07:35:29. **8/8 complete**; two polling cycles, no response loss observed | PASS; measured queue batching |
| B-011 | Continuous ChatGPT event notifications | No working direct event-trigger integration for this ChatGPT conversation; existing watcher is hourly | GAP: cannot truthfully promise instant ChatGPT wake-up |
| B-012 | Auditable failures | Existing text log recorded request IDs/status, but there was no bounded read-only correlator identifying missing, late, orphaned or inconsistent responses | MERGED [PR #114](https://github.com/shawnfra2013/Oden2-/pull/114): `scripts/odin_mailbox_audit.py` + regression tests |
| B-013 | Separate live Codespaces terminal | No active interactive Codespaces session attached to the conversation; cloud workspace not launched | GAP: GitHub source/API and Actions work; interactive shell requires a separately authorized session |
| B-014 | Viewer / private network acceptance | Direct iPhone cellular refresh through the approved private HTTPS route has not been run in this trial | OPERATOR-OWNED STEP; not a prerequisite for source CI |
| B-016 | Remote read-only audit request | The old private allowlist did not expose the mailbox correlator as an action. A fixed `mailbox_audit` request handler is being reviewed with strict schema, redacted response, snapshot persistence and no shell input. | SOURCE PR pending; physical test after approved install |
| B-015 | First auditor PR CI lint | Run [45132518927](https://github.com/shawnfra2013/Oden2-/actions/runs/45132518927) failed Ruff F401 for unused `tempfile` in the auditor and `timedelta` in its tests; Python and browser tests passed. Both unused imports were removed. All three exact reviewed-head checks subsequently passed. | FIXED and merged [PR #114](https://github.com/shawnfra2013/Oden2-/pull/114) |

## New diagnostic tool

From the current, safely installed Odin checkout:

```bash
cd "$HOME/odin-workspace" || exit 1
python -B scripts/odin_mailbox_audit.py --hours 1 --save
```

The tool uses **existing local Git objects only** in `state/github-bridge-private/outbox`. It neither fetches from GitHub nor executes a request. It compares private inbox/outbox metadata and writes one local private JSON snapshot under `state/mailbox-audits/` with permissions 0600. An exit code of 1 means incidents were found; 2 means the snapshot itself could not be evaluated. A successful audit does not certify an interactive shell, AI agent action, or current phone connectivity. No secret-bearing payload fields are printed. It is an **on-demand auditor**, not an unapproved new background daemon.

## One-hour supervised work acceptance criteria

- Evidence must distinguish **submitted → picked up → responded → stored → agent tool read → authorized code changed → exact source CI passed**. Missing stages remain explicit.
- Test 5+ request backlogs, stale/expired messages, malformed payloads, duplicate/replay behavior, interrupted network, feedback acknowledgment, source AI answer quality, and recovery after reviewed source rollout. Each finding has a stable ID, source revision, time, test, disposition and PR/issue when applicable.
- Preserve all original receipts and untracked owner files. At most two revision rounds for a failed source task; fail closed rather than execute mailbox text.
- Use existing [private mailbox runbook](../ODIN_GITHUB_BRIDGE.md), [handoff](../HANDOFF.md), and [single task board](../TASK_BOARD.md). This log is historical test evidence, not a second work queue.
- Continuous agent-to-agent work **requires a running authorized local/cloud agent and an enabled, event-compatible reviewer channel**. The present hourly reviewer is not a real-time conversational loop, and a one-hour background session cannot be asserted merely because this record exists.
