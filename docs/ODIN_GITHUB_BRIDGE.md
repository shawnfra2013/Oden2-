# Browser-free GitHub ↔ Odin background bridge

## Overview

This bridge uses GitHub repository branches as a mailbox. It does NOT need
Desktop Commander, a web pairing page, GitHub API tokens in the repo, an
inbound port, a cloud SSH host, or elevated Android privileges.

- ChatGPT's existing **authorized GitHub integration** creates one expiring
  JSON request on the `odin-bridge-inbox` branch.
- Odin's Python agent polls inbox using its existing Git remote authentication.
- Only the fixed actions `ping`, `repo_status`, `services`,
  `stage5_health`, `checks`, and `verify_release` are recognized. Request JSON cannot supply
  a shell command, executable, filename to read, argument list, or URL.
- Odin pushes a small JSON receipt to `odin-bridge-outbox`.
- ChatGPT can read that receipt through the GitHub connection.
- The working `main` tree is never automatically updated, modified, or
  restarted by the bridge. The existing worker and Git sync stay independent.

**Security limitation:** this is a **PUBLIC repository**. Anyone can read
request/response branches; therefore responses contain only bounded status
fields, sanitized booleans and counts, and no raw command output, file names,
environment variables, secrets, conversations, or task-queue content. A writer
with access to the inbox branch can trigger those limited diagnostics, including
local regression tests. For sensitive results, move the mailbox to a dedicated
private repository before extending it.

This is not arbitrary interactive SSH. Direct SSH from the ChatGPT conversation
requires an actual connected transport; a Tailscale-only SSH server is useful
for your own devices but does not by itself give ChatGPT an SSH client.

## Configuration

Branches `odin-bridge-inbox` and `odin-bridge-outbox` must exist remotely.
The Odin checkout's Git origin must be exactly one of:

- `git@github.com:shawnfra2013/Oden2-.git`
- `https://github.com/shawnfra2013/Oden2-.git`

The outgoing clone is created under ignored
`~/odin-workspace/state/github-bridge/outbox`. It has its own isolated
Git checkout and does not touch local main or the five preserved untracked files.

The bridge requires ordinary Git authentication for **push** from Odin.
`git ls-remote` proves read access but not write access; the first test
response confirms whether write access actually works.

## Local first-run (after merge to main and local safe pull)

From Termux:

```bash
cd ~/odin-workspace || exit 1
python -B -m unittest discover -s tests -p 'test*.py' -q || exit 1
python -B scripts/odin_github_bridge.py --once
```

With no requests, success prints `Processed requests: 0`. Errors are reported,
and a brief local-only log is kept at
`state/github-bridge/agent.log`. No services are restarted.

## Opt-in background service (not installed automatically)

Only after the one-time run succeeds:

```bash
cd ~/odin-workspace || exit 1
ln -s "$HOME/odin-workspace/services/odin-github-bridge" \
  "$PREFIX/var/service/odin-github-bridge"
sv up "$PREFIX/var/service/odin-github-bridge"
sv status "$PREFIX/var/service/odin-github-bridge"
```

The runit service checks GitHub every 60 seconds. To stop it without deleting
files: `sv down "$PREFIX/var/service/odin-github-bridge"`.

Termux background execution remains subject to Android battery/process
limits; runit alone does **not** guarantee reboot persistence.

## Request format

Under the inbox branch, create a NEW
`bridge/requests/<32_lowercase_hex_id>.json` file:

```json
{
  "version": 1,
  "id": "0123456789abcdef0123456789abcdef",
  "action": "ping",
  "created_at": "2026-11-18T22:00:00Z",
  "expires_at": "2026-11-18T22:30:00Z"
}
```

Requests expire at most one hour after creation. Use current UTC timestamps
when submitting a real request, not the example time. IDs must be unique.
Responses appear at `bridge/responses/<id>.json` on the outbox branch.

The bridge checks at most five requests per cycle. It does not delete
requests; existing receipt IDs prevent duplicate execution. If Git push fails,
the outgoing clone retains the local commit and retries the push at the next
cycle, without repeating the action.

## Revision-aware, read-only verification (v2)

The optional `verify_release` request accepts one additional field:
`"expected_sha": "<40 lowercase hexadecimal characters>"`. Use the exact
reviewed commit from GitHub's `main` branch (not a branch name or abbreviated
SHA). It checks that Odin is on `main`, its working tree has no tracked edits,
and its local `HEAD` equals `expected_sha`. If any check fails, it reports
`"verified": false` and **does not run the test suite**.

When the SHA matches, Odin runs the same existing allowlisted Stage 4, Stage 5,
and Ruff checks. The receipt includes their booleans and a final `HEAD`
check. If the revision changes while tests execute, verification is false.

This is evidence for *checks run against an Odin checkout at a particular
revision*, **not** proof that all long-running processes have loaded that
revision, nor proof of live AI behavior or correct user-facing responses.
`verify_release` **does not pull, merge, deploy, restart, edit, or run
an arbitrary command**.

Example request (replace dates, ID and SHA with real fresh values):

```json
{
  "version": 1,
  "id": "0123456789abcdef0123456789abcdef",
  "action": "verify_release",
  "expected_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "created_at": "2026-11-18T22:00:00Z",
  "expires_at": "2026-11-18T22:30:00Z"
}
```

## Hardened background bridge and safe updates (v3)

The hardened agent uses an exclusive local lock for each poll, rejects request blobs
larger than 4096 bytes before reading them, and adds `preflight_release`:
a **read-only update assessment** for an exact, reviewed 40-character main
commit SHA. It fetches remote Git metadata (without merging or restarting
anything) and reports the branch, tracked-clean flag, main ancestry,
expected remote target, untracked-file count, and possible file collisions.

Use the same request structure as `verify_release` but set
`"action": "preflight_release"`. A response of
`"safe_to_attempt_pull": true` is **not an automatic deployment**.
It is only one required check; a fresh local update must still pass Git's
built-in protections and the device operator's approval.

`scripts/odin-safe-pull.sh` now permits unrelated, preserved untracked
files and checks both exact-path and path-prefix collisions using NUL-delimited
Git filenames. It rejects tracked edits, a non-main checkout, an unexpected
origin or divergence. It never deletes, resets, stashes, or force-pushes.

The runit-generated `services/*/supervise/` directory is now ignored by Git.
This does not delete the existing supervisor data or alter how runit works.

## Chat from inside Odin: separate from public telemetry

This bridge is **not a ChatGPT conversation transport**. The user can interact
with the existing local Stage 5 AI Chat, which stores conversations in local
SQLite and uses its configured inference provider when enabled. The model
running through that backend is a separate conversational session, not this
ChatGPT app thread.

Never publish chat histories, private prompts, agent context or API credentials
to the public `odin-bridge-inbox` or `odin-bridge-outbox` branches.
Building actual conversational synchronisation requires a private, authorized
channel and a clear identity/session mapping. GitHub status receipts are
not suitable for it. OpenAI API access on Odin would also require separately
configured, securely stored API credentials and API billing; a ChatGPT
subscription does not automatically provide API credits.

## Operational limits and review gates

- Never use this mechanism to execute arbitrary commands, run downloaded
  scripts, restart services, install packages, modify protected files or
  deploy to production.
- PR review and GitHub CI are still required before merging code to main.
- A passing test receipt is not proof of model response correctness or live
  inference provenance.
- No on-device change happens merely by pushing this bridge code; the user
  must separately pull and opt in to service activation.
- Stop the bridge if the source branch or origin is unexpected, or if the
  isolated outbox checkout is not clean.
