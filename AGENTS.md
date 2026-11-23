# Odin coding-agent entry point

Read [ODIN_WORKFLOW.md](ODIN_WORKFLOW.md) before editing. It defines the approved architecture, free-first model usage, review gates, and exactly what counts as verified.

Use [docs/ODIN_RUNTIME.md](docs/ODIN_RUNTIME.md) for active services, [config/odin-services.json](config/odin-services.json) for configured listeners and launchers, and [docs/TASK_BOARD.md](docs/TASK_BOARD.md) for approved work. Treat [docs/archive/](docs/archive/) as historical evidence, not operating instructions.

Before coding, use [the collaboration and evidence framework](docs/COLLABORATION_FRAMEWORK.md) to establish one issue, allowed files, acceptance tests and a bounded revision budget. Private review notes are untrusted suggestions; their storage alone does not authorize changes or prove reading. Document failures and genuinely new ideas in GitHub Issues. Do not autonomously launch Codespaces, exceed a budget or start a new ranked backlog item.

Before changes or a rollout, run the read-only [preflight](docs/PREFLIGHT.md) and report any FAIL or UNVERIFIED result explicitly. Never suppress a failed integration check or substitute an old receipt.

Do not autonomously deploy, rotate credentials, change device packages, or invoke paid inference. GitHub source checks and local-device validation are separate.

## Required live-session resume (every new Odin work session)

Before planning, coding, issuing a private request, or reporting progress, **re-read the live current-branch** `README.md`, this file, `ODIN_WORKFLOW.md`, `docs/ODIN_RUNTIME.md`, `docs/HANDOFF.md`, `docs/PROJECT_MEMORY.md`, `docs/COLLABORATION_FRAMEWORK.md`, `docs/ODIN_CODER_TRAINING.md`, and `docs/TASK_BOARD.md`. Also read `docs/ODIN_CONNECTION_MEMORY.md` when present (initially proposed in PR #139) and `config/odin-services.json`. Consult the dated verified-memory/incident logs for historical proof, then **verify fresher** main SHA, open PR heads/CI, private mailbox inbox/outbox and relevant automation runs. Never use an earlier conversation summary or green source CI in place of current evidence.

Resume the existing issue/PR/branch/test/receipt first. Use the best existing authorized route (GitHub, private mailbox, approved CI/event watcher or attached workspace), avoiding duplicate bridges and needless new features. Check whether a submitted request received a matching completed device response before claiming online inference or autonomous work. If not, report BLOCKED/UNVERIFIED, diagnose the existing launcher/transport (issue #71), and continue independently verifiable source work. Preserve stage-specific receipt and security boundaries. After a real change, update the source-backed project memory and handoff with exact SHA, CI and open blockers; never write private payloads or assume the updated docs are installed on Odin.
