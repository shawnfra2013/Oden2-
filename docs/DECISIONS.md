# Odin architecture decision log

This is the **current decision register**, not a historical status report. Record a new decision and evidence before reversing any of these rules. Latest proposed change: November 23, 2026 (this PR, not effective on main until reviewed merge).

| ID | Decision | Reason and consequence |
| --- | --- | --- |
| D-001 | GitHub `main` remains the source repository, with reviewed PRs and exact-SHA CI | Prevents unverified edits and accidental rollout |
| D-002 | The **private GitHub mailbox** is the source-to-device request/receipt transport | Provides bounded asynchronous diagnostics with no publicly exposed shell |
| D-003 | User-facing name is **Odin Local Workstation** | The `stage5/`, `odin-stage5`, `stage5_health` names remain internal compatibility identifiers, not active project phases |
| D-004 | The phone viewer is a **separate** optional Node app behind approved private HTTPS | Loopback-only services are not directly reachable from a cellular iPhone |
| D-005 | No private network provider is claimed active without a verified connection | Tailscale needs a real operator/device test; track in [#70](https://github.com/shawnfra2013/Oden2-/issues/70) |
| D-006 | CI, physical Odin, and iPhone cellular acceptance are three different release states | Prevents misleading "fixed" or "online" claims |
| D-007 | Historical records go in `docs/archive/` and active instructions have one source of truth | Avoids reactivating removed infrastructure |
| D-008 | No secrets, private chat, pairing codes, or direct terminal endpoints in public issues or CI artifacts | Keeps private mailbox and device access safe |
| D-009 | [ODIN_WORKFLOW.md](../ODIN_WORKFLOW.md) is the single machine-readable-compatible workflow policy, backed by deterministic GitHub CI | Reading and validating it never calls a paid AI model |
| D-010 | [Service registry](../config/odin-services.json) declares source defaults, with device-generated services identified separately | Source checks catch missing paths and duplicate ports; only live on-device inspection proves bound sockets |
| D-011 | [Preflight](PREFLIGHT.md) reports PASS/FAIL/UNVERIFIED; missing required evidence never silently passes | Static CI and actual device/phone acceptance remain distinct; no startup paid inference or unreviewed actions |
| D-012 | [Working with Odin](WORK_WITH_ODIN.md) is the single read-first session guide; the existing workflow/runtime/release documents remain authoritative for their respective gates | Prevents duplicate communication handoffs, requires source-and-receipt checks before status claims and keeps archived reports historical |
| D-013 | Use existing GitHub tools, deterministic CI and the private allowlisted mailbox for free-first two-way collaboration; use Codespaces only as a separately authorized source workspace | No public relay, unrestricted shell, unapproved automated startup, paid inference or claimed continuous ChatGPT wake-up |

**Changing a decision:** create a GitHub issue stating the proposed replacement and a migration/test plan, then a reviewed PR updating this log, [runtime](ODIN_RUNTIME.md) and [release gates](RELEASE_GATES.md). Do not edit unrelated service configurations implicitly.
