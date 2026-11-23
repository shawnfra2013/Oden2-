# Odin 2 — canonical working agreement

**Status:** Current operating policy; this file controls how the repository is reviewed. It is not an authorization to make unreviewed device changes. GitHub CI validates this document and the machine-readable service registry without calling an AI model.

## What is used
- GitHub `shawnfra2013/Oden2-` main is the reviewed source of code, not evidence of installation on Odin.
- The **private GitHub mailbox** is the asynchronous request/response path for bounded diagnostic actions. Match request IDs and timestamps. Never confuse inbox branches with chat inboxes or live device access.
- The **offline source receipt queue** is written only under `~/odin-workspace/state/codespace-receipts/` on the handheld. The existing private mailbox uploader forwards validated source-only results when connected; it does not execute scripts from receipt content or make a cloud shell live.
- **Tailscale** is the selected private device-to-phone network. The HTTPS route and real iPhone cellular test are **not yet verified**; do not pretend a draft listener or saved shortcut is live.
- The **Odin Local Workstation** runs in the historical `stage5/` implementation directory; the internal service name is a compatibility identifier.
- On-device inference is the free-first default. A paid/online provider is used only when explicitly chosen, configured, and covered by a known cost guard. No silent fallback or startup model calls.
- For active ports and service launchers, use [the registry](config/odin-services.json) and [its guide](docs/SERVICE_REGISTRY.md), not old plans. It distinguishes tracked launchers from device-generated ones.

**Supervised coding and review:** Use [the collaboration framework](docs/COLLABORATION_FRAMEWORK.md) for bounded task acceptance, review receipts, failure investigation, two revision rounds maximum, and verified handoff. The [integrated 20-item GitHub task board](docs/TASK_BOARD.md) is priority order; do not silently start future items or treat a received note as executed work.

## Standard change workflow
**Start-of-session entry:** [Working with Odin](docs/WORK_WITH_ODIN.md) supplies the quick read, live GitHub/receipt checks, tool/agent roles, and persistence boundaries. It must be read before choosing a task, but it does not override the controls in this file, [release gates](docs/RELEASE_GATES.md), or [collaboration proof](docs/COLLABORATION_FRAMEWORK.md).

1. Start with the [read-first guide](docs/WORK_WITH_ODIN.md), [README](README.md), [runtime truth](docs/ODIN_RUNTIME.md), [current handoff](docs/HANDOFF.md), and [open GitHub issues](docs/TASK_BOARD.md). Validate current GitHub SHA and matched private receipts; archive records are historical only.
2. Before editing, identify the relevant issue and current main SHA. Record acceptance criteria; do not reopen completed milestones because of old folder names.
3. Make the smallest reviewable branch/PR, preserving credentials and device state. Do not add hosting or services without a reviewed architecture change.
4. Run **source checks**: unit tests, syntax, lint, tracked file/path integrity, listener collision detection, active-document guard, and secret checks. Never describe a passing source check as a physical-device test.
5. **Only with operator approval**, install the exact reviewed SHA on Odin, verify local service/process/port states, and obtain a fresh matching private mailbox receipt. A source push does not restart or update running Python processes by itself.
6. Prove phone usability on the real iPhone using Tailscale, approved HTTPS, Wi-Fi disabled/cellular enabled, app reopen, refresh, and encrypted request/reply. Without that, leave phone acceptance open.
7. Record evidence and remaining blockers on the GitHub issue, update docs/DECISIONS.md for architecture changes, and refresh docs/HANDOFF.md for the next session.

## Cost and safety rules
- Use the authorized GitHub connection and pre-existing allowlisted private device mailbox rather than copying commands when supported. A GitHub Action, a mailbox acknowledgment, a Codespaces shell, and an Odin agent execution are different capabilities; never conflate them.
- Use an attached, operator-authorized Codespaces shell for bounded source work only when available; GitHub Actions handles deterministic tests without an interactive workspace. Neither service is an implicit permanent free shell or a direct device terminal.
- No automatic cloud model requests for reading this policy, validating files, CI, startup, or status checks.
- Do not publish tokens, pairing secrets, private user messages, SSH keys, or personal addresses.
- Never use force-push, hard reset, remove live services, expose a public port, or auto-restart the device without explicit review.
- Preserve earlier evidence in docs/archive/, but do not use archived commands to configure the active system.

**Source validation:** `python -B scripts/odin_preflight.py --mode source` produces PASS/FAIL/UNVERIFIED evidence; GitHub retains its JSON report. **Device inspection:** `python -B scripts/odin_preflight.py --mode device --strict` is read-only and fails closed when required evidence is unknown. Neither mode calls a model or approves deployment. See [preflight guide](docs/PREFLIGHT.md).
