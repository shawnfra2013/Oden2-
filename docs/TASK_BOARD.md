# Odin GitHub task board

**GitHub Issues is the task tracker**; do not maintain a competing backlog in old stage documents. Each issue has one **Workflow state**: Planned → In progress → Tests passed → Device verified → Closed. State changes require a link to evidence. For phone-specific work, Device verified also requires the cellular acceptance evidence.

| Issue | Current state | Completion gate |
| --- | --- | --- |
| [#69 — iPhone viewer on cellular](https://github.com/shawnfra2013/Oden2-/issues/69) | Planned | iPhone Home Screen reopen, refresh, and real encrypted round-trip |
| [#70 — Private network/Tailscale](https://github.com/shawnfra2013/Oden2-/issues/70) | Planned | Approved actual device connection and HTTPS origin |
| [#71 — Exact-revision device rollout](https://github.com/shawnfra2013/Oden2-/issues/71) | Planned | On-device SHA/service receipt and stale-status test |
| [#72 — Documentation and release operations](https://github.com/shawnfra2013/Oden2-/issues/72) | In progress | Reviewed PR, CI evidence, status and handoff artifacts |
| [#75–#79 — five approved fixes](https://github.com/shawnfra2013/Oden2-/issues/75) | In progress (#75); others Planned | Model routing, private phone path, explicit modes, encrypted resume, and live readiness |
| [#80–#84 — five additional improvements](https://github.com/shawnfra2013/Oden2-/issues/80) | #81 In progress; others Planned | Service registry, preflight, dependencies, offline queue, performance/battery baseline |

Create a new task with [the issue template](https://github.com/shawnfra2013/Oden2-/issues/new/choose), identify the owner, exact acceptance test, evidence link, and any blocker. Never close an issue solely because code was pushed or CI passed. If device access is missing, leave it at Tests passed and record that limitation.

To review the work, use the [repository's open issues](https://github.com/shawnfra2013/Oden2-/issues?q=is%3Aissue+is%3Aopen). For a new session read [handoff](HANDOFF.md) and [status](PROJECT_STATUS.md) first.
