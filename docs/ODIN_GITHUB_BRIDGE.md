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

For a fresh rollout use [release gates](RELEASE_GATES.md). For encrypted phone-model messages use [offline chat](OFFLINE_CHAT.md). Do not publish private responses, secrets, pairing codes, SSH keys, or full private messages in a public issue. The legacy public diagnostic branches remain distinct from the **active private** device mailbox.
