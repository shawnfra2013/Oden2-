# Current private GitHub mailbox runbook

Canonical operating details: [Odin runtime](ODIN_RUNTIME.md). Older public-mailbox commands and hosted-relay experiments are preserved in [the archived runbook](archive/ODIN_GITHUB_BRIDGE_before_2026-11-22.md).

The device bridge uses the **private** repository `shawnfra2013/Odin-private-bridge`. Odin polls `odin-bridge-inbox` and publishes bounded replies in `odin-bridge-outbox` using its existing authorized SSH configuration. The private workflow is [here](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml).

**Read-only live test:** submit one `ping` through the private workflow or authorized GitHub integration. Match the generated request ID to the exact outbox receipt; confirm `status=complete`, the `checked_at` timestamp, and the allowlisted `alive` result. To check the Odin Local Workstation, use `stage5_health` (compatibility action name) and inspect `reachable`. Neither test calls a model.

A successful request submission, previous receipt, or passing source-code tests cannot establish current connectivity. A `stage5_health` receipt proves the local HTTP service was reachable **at that receipt time**, not that a particular source revision or iPhone route was installed.

For a fresh rollout use [release gates](RELEASE_GATES.md). For encrypted phone-model messages use [offline chat](OFFLINE_CHAT.md). Do not publish private responses, secrets, pairing codes, SSH keys, or full private messages in a public issue. The legacy public diagnostic branches remain distinct from the **active private** device mailbox.
