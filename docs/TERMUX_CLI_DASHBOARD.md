# Odin Termux CLI dashboard and AI portal

**Implementation:** Source-only [Issue #148](https://github.com/shawnfra2013/Oden2-/issues/148). Device rollout still belongs to [Issue #71](https://github.com/shawnfra2013/Oden2-/issues/71).

## Preserve the original AI launcher

The last actual Termux inventory (November 10) showed lowercase `ai` as an **executable** at `~/.local/bin/ai`, not a shell alias; it ran the Odin orchestrator. `AI` was not a persistent command at that check. Current Bash profile contents and reboot behavior are **not remotely verified**. The optional hook does not overwrite or repoint that file. It defines `ai`, `Ai`, `aI` and `AI` as Bash functions; with no arguments or unknown legacy arguments all four call the original executable unchanged.

| Command | Action |
| --- | --- |
| `ai` or any capitalization | Existing Odin orchestrator; no background service changes |
| `ai menu` | Read-only compact portal guide |
| `ai status` | Local SHA, queue, runit services, mailbox launcher and PID/cwd |
| `ai watch --github` | Refreshing colored dashboard; public source CI no faster than every 120 seconds |
| `ai local` | Explicit offline-model conversation using the existing chat CLI; no cloud fallback |
| `ai online --provider groq --confirm CLOUD-MAY-COST` | Explicit cloud mode; unavailable if the offline-only profile is active |
| `ai services` | Read-only runit statuses |
| `ai services up odin-task-worker --confirm START-ODIN-SERVICE` | One operator-initiated allowlisted, previously stopped service only |

The `services up` command is **not** automatic at login or when `ai` starts. The private mailbox refuses a start until its launcher **and** current PID working directory pass the canonical checkout preflight. Cloud mode may incur usage charges; confirmation is explicit but is **not** a quota accounting system. Do not enable paid inference without separately verified budget controls. Reboot/startup persistence requires independent Android/Termux:Boot acceptance.

## Physical installer — dry run first

Source code cannot read the live `~/.bashrc` or the actual `~/.local/bin/ai`. After an approved exact-SHA checkout on the handheld:

```sh
cd ~/odin-workspace || exit 1
command -v ai
ls -l ~/.local/bin/ai
bash scripts/odin-cli-install.sh --check
```

The installer blocks if the original executable, Bash profile or hook is missing, or if an obvious conflicting `ai` alias/function is already declared in `~/.bashrc`. It does not start services or models. After inspecting the dry-run and obtaining separate operator approval for the shell-profile change:

```sh
bash scripts/odin-cli-install.sh --apply --confirm INSTALL-ODIN-AI-SHELL
```

It backs up the existing Bash profile to a local 0600 file in `~/.odin-preservation/`, appends one guarded hook line and leaves the original `ai` executable untouched. Open a new shell; confirm `AI status`, `aI menu`, then `ai` still opens the original orchestrator. This is not a source-only operation and has not yet been performed.

## How it works

Local status checks use `git rev-parse HEAD`, `sv status`, queue directory counts, and the existing read-only preflight that compares the mailbox launcher with live `/proc/PID/cwd`. A green service state **cannot** hide a mismatched launcher directory. When selected, optional public GitHub Actions metadata is cached for 120 seconds and filtered against the exact local SHA. It never uses the private GitHub token or executes action contents. Status and watch are zero-model-call commands and are usable without the internet.

The interface automatically enables colors only on an interactive terminal, respects `NO_COLOR`, and does not create a daemon. Ctrl+C exits watch. GitHub source tests are distinct from device installation; the CLI does not show private ChatGPT internal execution. It displays only observable GitHub, queue and Termux evidence.

For #71, run `python -B scripts/odin_mailbox_migrate.py --expected-sha "$(git rev-parse HEAD)"` in the **physical Termux checkout** and inspect READY / BLOCKED / ALREADY_CANONICAL before any separate approved migration apply. Then verify a new matched private `ping`, `mailbox_audit` and live PID/cwd.
