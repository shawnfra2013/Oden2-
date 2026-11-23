# Current private GitHub mailbox runbook

Canonical operating details: [Odin runtime](ODIN_RUNTIME.md). Older public-mailbox commands and hosted-relay experiments are preserved in [the archived runbook](archive/ODIN_GITHUB_BRIDGE_before_2026-11-22.md).

The device bridge uses the **private** repository `shawnfra2013/Odin-private-bridge`. Odin polls `odin-bridge-inbox` and publishes bounded replies in `odin-bridge-outbox` using its existing authorized SSH configuration. The private workflow is [here](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml).

**Read-only live test:** submit one `ping` through the private workflow or authorized GitHub integration. Match the generated request ID to the exact outbox receipt; confirm `status=complete`, the `checked_at` timestamp, and the allowlisted `alive` result. To check the Odin Local Workstation, use `stage5_health` (compatibility action name) and inspect `reachable`. Neither test calls a model.

A successful request submission, previous receipt, or passing source-code tests cannot establish current connectivity. A `stage5_health` receipt proves the local HTTP service was reachable **at that receipt time**, not that a particular source revision or iPhone route was installed.

## Offline development source receipts

A portable test run (`python -B scripts/odin_codespace.py test`) saves a source-only receipt under the canonical Odin checkout at `~/odin-workspace/state/codespace-receipts/<id>.json`. The **existing** supervised private mailbox polls about once per minute when connected and, on this version of the bridge, uploads up to three valid receipts per cycle to the **private** `odin-bridge-outbox` branch at `bridge/local-source-receipts/<id>.json`. No tokens, code, chat transcripts, terminal stdout/stderr, or passwords are copied into the receipts. Uploading is part of the already-authorized private transport; it neither executes a command nor edits source.

A disconnected handheld preserves its local receipts. On reconnect, the private bridge first finishes any interrupted local Git commit or retries an ahead-of-remote push, then publishes newly queued source receipts. Original receipts remain on Odin; replayed IDs must have identical content, and conflicting IDs halt that upload instead of overwriting evidence. Missing/invalid test receipts are skipped safely, not interpreted as successes. A private `ping` can include the latest `last_source_receipt_push` marker; that marker means a receipt upload completed at its recorded time, **not** that an AI model responded or a device test passed.

When reviewing receipts from ChatGPT or scheduled GitHub checks, distinguish **(a)** requested device action replies in `bridge/responses/`, **(b)** unprompted local source-test receipts in `bridge/local-source-receipts/`, and **(c)** GitHub Actions results tied to the exact source SHA. Use IDs, status, SHA and UTC timestamps to avoid duplicate/stale findings. ChatGPT monitoring is scheduled rather than continuously connected; mailbox polling does not wake a Codespace or an interactive ChatGPT turn.

**Operator live test (after approved installation/reload):** In Odin Termux, run the source test command; observe its locally saved ID; confirm the matching private branch receipt arrives; repeat the bridge poll or restart the connection to prove no duplicate; and confirm a new private `ping` returns a matching last-upload ID. To test a genuinely offline period, run a second source test with connectivity disabled, reconnect, and check that exact ID appears once. If offline dependencies are missing, the recorded test outcome is FAIL, not a successful test.

## Private mailbox audit (read-only)

After an approved checkout update, a Termux operator or authorized local agent can run `python -B scripts/odin_mailbox_audit.py --hours 1 --save`. It reads the **local** private inbox ref and outbox Git objects only: no GitHub fetch, credentials, model call or command execution. For each recent request it checks a corresponding response ID/action, timestamp, outcome, unexpected command completion, and overdue or orphaned replies. Reports are stored as immutable private snapshots under `state/mailbox-audits/`. Exit code **0** means no incidents in the requested window; **1** means findings, and **2** means the audit itself could not run. Reports redact message payloads and cannot attest to agent understanding or live ChatGPT notification.

**Remote bounded audit request:** The private bridge additionally accepts the exact action `mailbox_audit` with only the standard ID and UTC expiry fields. When installed and loaded on Odin it runs the fixed local read-only auditor for the last hour, saves a local audit snapshot, and returns only bounded counts, status codes, IDs, response latency and source SHA. This does **not** give ChatGPT arbitrary terminal access. The action is not accepted by the public bridge; extra fields like `command` are rejected. A response to this new action requires a refreshed physical Odin release and cannot be claimed from a source test alone.

GitHub receives device receipts as they are pushed. ChatGPT's existing receipt watcher is **hourly**, not event-pushed. Do not claim that GitHub immediately wakes this ChatGPT conversation. See [the dated collaboration trial](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md) for measured eight-message queue behavior and outstanding wake-up limitations.

## Feedback tool presentation receipts

A review note already stored by the private `review_feedback` action remains **untrusted data**. To have an authorized local tool explicitly present one saved message, use the Termux terminal or a properly attached coding agent:

```bash
cd ~/odin-workspace || exit 1
python -B scripts/odin_review_feedback.py --list
python -B scripts/odin_review_feedback.py --inspect EXACT_32_CHARACTER_FEEDBACK_ID
```

The explicit `--inspect` operation prints the stored note to the *local tool only* and atomically saves a **metadata-only** receipt in `state/github-bridge-private/feedback-tool-observed/`. The existing private mailbox service then sends these receipts to `odin-bridge-outbox:bridge/feedback-tool-receipts/<id>.json` when connected, preserving local originals, rejecting mismatched IDs and recovering interrupted commits. Receipt fields include only the message ID, reviewed head SHA, issue/PR, note digest, UTC presentation time and `action_executed=false`, `agent_identity_verified=false`. No original note, terminal output or command is published.

**Evidence boundary:** this proves a specific local tool invocation displayed the note and the private mailbox delivered its metadata. A human could have invoked the tool; therefore it does **not** prove model cognition, genuine autonomous agent identity, an implemented correction, or source CI. Those need separate task/PR/test receipts under [the collaboration proof contract](COLLABORATION_FRAMEWORK.md).

For a fresh rollout use [release gates](RELEASE_GATES.md). For encrypted phone-model messages use [offline chat](OFFLINE_CHAT.md). Do not publish private responses, secrets, pairing codes, SSH keys, or full private messages in a public issue. The legacy public diagnostic branches remain distinct from the **active private** device mailbox.
