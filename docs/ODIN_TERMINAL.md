# Odin Terminal — colorful read-only CLI

Issue [#148](https://github.com/shawnfra2013/Oden2-/issues/148). **Physical read-only CLI snapshot accepted, Full Sweep source-only:** On November 23 the operator ran `python -B -m scripts.odin_terminal --offline --plain` from canonical checkout `fb5d219f96e693fb163ff9f62c384e8473881e64`. It showed supervised services running, canonical mailbox cwd PASS, and queue 0/0. Remote GitHub SHA and CI were deliberately UNKNOWN/OFFLINE because `--offline` was selected. The optional mixed-case `ai` shell hook remains uninstalled/unverified. The new `full_sweep` mailbox action requires a separately approved physical source rollout/reload.

The terminal displays local source SHA, runit service state and PID, the *canonical mailbox launcher and process cwd* check, task queue counts, local metadata trace, public GitHub exact-main CI and recent public issue/PR activity. Public GitHub status does not prove installation or agent action. Private messages and credentials are never fetched or displayed.

After approved source installation into the canonical checkout:

```sh
cd ~/odin-workspace
python -B -m scripts.odin_terminal --issue 71
python -B -m scripts.odin_terminal --watch --issue 71
```

`--offline` avoids all network calls. `--theme neon`, `--theme ocean`, and `--theme ember` select colors; `--plain`, `--theme mono` and `NO_COLOR=1` disable them. `--json` outputs a script-friendly snapshot. Live watch refreshes local status every five seconds and public GitHub no more often than once every 300 seconds, and exits with Ctrl+C. This is not an always-connected ChatGPT terminal or a streaming transcript of ChatGPT tool calls.

Optional source-side `bin/odin` supports `status`, `watch`, `chat`, and `preflight`; it does not install itself or replace an existing `odin` or `ai` alias. Do not change Termux themes, local shell startup, or running services without reviewing existing configuration and obtaining operator approval.

**Acceptance:** exact-SHA CI, on-device Termux terminal rendering, canonical mailbox cwd and fresh private receipt, no leaking private content, offline transition, and measured overhead. Issue [#71](https://github.com/shawnfra2013/Oden2-/issues/71) retains the separate migration gate.

## Existing `ai` orchestrator integration — opt-in, protected

The November 10 Termux inventory identified `~/.local/bin/ai` as an **executable** launching the Odin orchestrator, **not** an alias. Current device `~/.bashrc` and executable bytes must be inspected during the approved rollout. [Issue #148](https://github.com/shawnfra2013/Oden2-/issues/148) adds an opt-in Bash hook for `ai`, `AI`, `Ai` and `aI`. **No-argument and unknown legacy arguments still call the unchanged original executable.** The new portal dispatches `status` and `watch` to the merged `bin/odin` / `scripts/odin_terminal.py`, and `local` to the existing offline chat CLI. Examples:

```sh
ai status --offline
AI watch --issue 71 --theme ocean
Ai menu
ai services
ai local
```

`ai online --provider groq --confirm CLOUD-MAY-COST` explicitly selects an online provider and refuses to bypass an active offline-only lock. This consent is **not a cloud quota mechanism**. Status, watch and login make no AI calls. `ai services up SERVICE --confirm START-ODIN-SERVICE` is a **local, explicit, allowlisted** operator action on a confirmed-down service; the private mailbox cannot be started from this generic CLI route and stays under Issue #71's separately approved migration/restart process. Neither command grants unrestricted GitHub shell execution or establishes Android reboot persistence.

The physical installer first runs read-only as `bash scripts/odin-cli-install.sh --check` from an approved exact-SHA checkout. It refuses a missing original executable, missing Bash profile, or detected conflicting existing `ai` definition. Separate operator-approved `--apply --confirm INSTALL-ODIN-AI-SHELL` backs up `~/.bashrc` (0600) under `~/.odin-preservation` and appends one guarded source line; **it never writes `~/.local/bin/ai` or starts a daemon**. Test all capitalization variants and original no-argument behavior on the real handheld after approval. Source CI alone cannot install or verify the Bash hook.

## One-action private Full Sweep — source pending physical acceptance

A single **private** allowlisted mailbox request `action=full_sweep` uses the existing
`odin-bridge-inbox` → supervised Termux poller → `odin-bridge-outbox`
receipt path. One request/receipt pair binds the liveness response to a
single bounded collection of source SHA consistency, supervised service status,
canonical mailbox cwd, task queue depths, local workstation/provider readiness,
preflight PASS/FAIL/UNVERIFIED checks and private metadata audit counts.

The sweep **does not call a model**, configure Tailscale or contact the phone, fetch GitHub main,
run arbitrary command text, restart services, or modify configuration. The
model-inference, network-offline, exact-GitHub-main, phone and agent-action
gates remain explicitly `UNVERIFIED` in each sweep; the caller separately
matches reported revision to current GitHub main and its exact-SHA CI.
Missing probes remain UNVERIFIED, not PASS. A reply's top-level `complete`
means the bounded diagnostic ran; inspect `result.overall` and individual
checks for actual health. The private metadata audit can naturally see the
current request as pending before its own receipt is published.

**Deployment boundary:** This is initially reviewed GitHub *source only*.
An already-running, older Termux mailbox process cannot accept `full_sweep`
until a separately authorized device update and process reload. Do not submit
the new action against an older revision or mistake a saved request for
device execution. The existing `ping` and `mailbox_audit` actions remain
unchanged, including for rollback. Adding a browser workflow choice for
`full_sweep` is a separate private-repository integration gate once the
running device accepts the action.
