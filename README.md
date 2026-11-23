# Odin 2 — current operating guide

**Every session: [Working with Odin — 60-second quickstart](docs/WORK_WITH_ODIN.md).** For supported environment and real device/phone acceptance boundaries, consult [Current Odin runtime](docs/ODIN_RUNTIME.md). Operational policy remains [ODIN_WORKFLOW.md](ODIN_WORKFLOW.md); a dated checkpoint is not current runtime proof.

Odin's local browser is the **Odin Local Workstation** (historical implementation path `stage5/`). The working communication path is the **private GitHub mailbox**; the optional iPhone viewer needs its own approved HTTPS origin and has not yet passed the cellular acceptance test.

| Need | Current document |
| --- | --- |
| Session start, roles, receipts, agentic coding and memory | [Working with Odin](docs/WORK_WITH_ODIN.md) |
| Read-only colorful Termux status and existing `ai` integration | [Termux CLI dashboard](docs/TERMUX_CLI_DASHBOARD.md) |
| What is actually in use | [Runtime](docs/ODIN_RUNTIME.md) |
| Working agreement read by GitHub and Odin | [Odin Workflow](ODIN_WORKFLOW.md) |
| Services and listener defaults | [Service registry](docs/SERVICE_REGISTRY.md) |
| Source-to-device messaging | [Private mailbox runbook](docs/ODIN_GITHUB_BRIDGE.md) |
| Offline test receipts and private replay | [Terminal source loop](docs/CODESPACES_WORKFLOW.md) and [mailbox](docs/ODIN_GITHUB_BRIDGE.md) |
| Local model and encrypted mobile chat | [Offline chat](docs/OFFLINE_CHAT.md) |
| Source updates and acceptance checks | [Release gates](docs/RELEASE_GATES.md) |
| Online cloud / offline handheld terminal development | [Terminal development loop](docs/CODESPACES_WORKFLOW.md) |
| Read-only preflight and explicit failures | [Preflight guide](docs/PREFLIGHT.md) |
| Open work | [Task board](docs/TASK_BOARD.md) |
| Evidence-aware status | [Status guide](docs/PROJECT_STATUS.md) |
| Architecture decisions | [Decision log](docs/DECISIONS.md) |
| Session continuation | [Handoff](docs/HANDOFF.md) |
| Replace old iPhone saved links | [Shortcut cutover](docs/SHORTCUT_CUTOVER.md) |
| Previous stages, providers, and observations | [Historical archive](docs/archive/README.md) |

**Status rule:** A GitHub merge or passing CI is not proof that the handheld installed it. A website refresh is not proof of a device heartbeat. Only a matched, time-stamped device receipt supports a device claim, and only an actual iPhone cellular test establishes phone acceptance.

Changes must use an issue, a reviewed PR, CI, and recorded evidence. Do not paste credentials, pairing codes, or private IPs in issues or screenshots.
