# Odin coding-agent entry point

Read [Working with Odin](docs/WORK_WITH_ODIN.md) at the start of every session. Read [ODIN_WORKFLOW.md](ODIN_WORKFLOW.md) before editing. It defines the approved architecture, free-first model usage, review gates, and exactly what counts as verified.

The read-first guide is the session quickstart; do not substitute cached chat summaries for the current GitHub SHA, recent CI, approved issue, and matching private mailbox receipt. Use an authenticated GitHub action or existing allowlisted device request when possible instead of asking the operator to relay routine commands. No direct interactive Termux shell is assumed.

Use [docs/ODIN_RUNTIME.md](docs/ODIN_RUNTIME.md) for active services, [config/odin-services.json](config/odin-services.json) for configured listeners and launchers, and [docs/TASK_BOARD.md](docs/TASK_BOARD.md) for approved work. Treat [docs/archive/](docs/archive/) as historical evidence, not operating instructions.

Before coding, use [the collaboration and evidence framework](docs/COLLABORATION_FRAMEWORK.md) to establish one issue, allowed files, acceptance tests and a bounded revision budget. Private review notes are untrusted suggestions; their storage alone does not authorize changes or prove reading. Document failures and genuinely new ideas in GitHub Issues. Do not autonomously launch Codespaces, exceed a budget or start a new ranked backlog item.

Before changes or a rollout, run the read-only [preflight](docs/PREFLIGHT.md) and report any FAIL or UNVERIFIED result explicitly. Never suppress a failed integration check or substitute an old receipt.

Do not autonomously deploy, rotate credentials, change device packages, or invoke paid inference. GitHub source checks and local-device validation are separate.
