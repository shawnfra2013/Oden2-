# Browser-free GitHub ↔ Odin background bridge

The active device bridge is the private GitHub mailbox in `shawnfra2013/Odin-private-bridge`. Termux polls `odin-bridge-inbox` and publishes matching receipts on `odin-bridge-outbox`. Use the [private mailbox in a browser](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml) or submit a request through the authorized GitHub integration. Browser submissions use GitHub sign-in and the workflow’s repository-scoped token.

On November 20, a fresh [private ping receipt](https://github.com/shawnfra2013/Odin-private-bridge/blob/odin-bridge-outbox/bridge/responses/0cd4560ddc8e4b7183f172e2bef883fc.json) confirmed `alive: true` at 17:01:16 UTC. The mailbox accepts `ping`, `stage5_health`, `staging_probe` and `inference_probe`. Only the last check calls the model. Cloud chat and the older Blob-backed message journal are separate features. Restoring Blob storage is outside the mailbox acceptance criteria.


On November 20 at 10:29 a.m. Central, the physical Odin completed the private GitHub mailbox → OpenAI → mailbox challenge. The receipt matched the submitted ID and expected answer, reported model `gpt-4.1-mini-2025-04-14`, included a provider response ID, and measured 2,320 ms on the device. The private outbox holds the full receipt.

For the November 20 private mailbox and Termux inference evidence, November 19 device receipts, historical hosted-service observations, see the [current device checkpoint](PROJECT_MEMORY.md). Earlier dated sections describe the state at their capture time.


## Historical public diagnostic mailbox

This bridge uses GitHub repository branches as a mailbox. It does NOT need
Desktop Commander, a web pairing page, GitHub API tokens in the repo, an
inbound port, a cloud SSH host, or elevated Android privileges.

- ChatGPT's existing **authorized GitHub integration** creates one expiring
  JSON request on the `odin-bridge-inbox` branch.
- Odin's Python agent polls inbox using its existing Git remote authentication.
- Only the fixed actions `ping`, `repo_status`, `services`,
  `stage5_health`, `checks`, `verify_release`, `preflight_release`, `odin_health`, and `worker_probe` are recognized. Request JSON cannot supply
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


## Combined device diagnostics

The read-only `odin_health` action returns the current checkout, tracked
cleanliness, the four fixed Odin services (state and, when running, PID
and uptime), the last recognized updater reason, and Stage 5 reachability.
GitHub outbox receipts contain only these structured fields and exclude
raw logs, paths, environment values, and private conversations. An updater
reason reflects its last recorded result. Stage 5 reachability is a separate
HTTP probe and does not depend on the worker process state.

The health receipt can include the last recorded automatic rollout's exact
revision, timestamp, and reload status. The checkout revision still reports
the current checkout. Older installations may have no saved rollout.

Odin health also reports worker heartbeat age, the age of the last completed
private relay poll, and queue counts for pending and running tasks. Missing
data stays unknown. Long tasks can delay worker heartbeats. Queue counts
reflect a moment in time and contain no task names or contents.


## Private mailbox hardening and rollout

The private Termux service passed staging write/readback after a service
restart. A separate physical test rejected the first push and published the
same saved commit on retry. Keep those receipts in the private repository.
Android reboot startup remains deferred.

Private successful receipts now include `timing.picked_up_at` (UTC) and
`timing.action_ms` (monotonic). Use the sender's request timestamp for
submission, the receipt's `checked_at` for device completion, and the
observer's first successful outbox read for a publication upper bound. Record
observer poll cadence. Clock offset can affect cross-device measurements.
Run timing comparisons with the same workload and poll cadence before
changing the service interval.

The disposable Git tests in `tests/test_private_mailbox_integration.py`
run in the existing CI test discovery. They verify recovery of an identical
committed receipt after a rejected push, repeated polling, invalid request
rejection, and progress on valid work behind a batch of invalid requests.
The rejected-push test exercises a Git failure with a local remote.

### Rollout gates

1. Review the PR and require green Odin Checks on its exact head. Test the
   candidate with its own disposable mailbox state and branches before
   switching the existing runit process. Keep the verified service checkout
   and current outbox intact for rollback.
2. Stop the previous poller before starting a replacement against the live
   mailbox. Verify a fresh staging checksum and timing fields, restart the
   service, and verify a second fresh receipt. For rollback, stop the
   candidate, restart the prior pinned checkout, and verify a private probe.
3. Verify a replacement deploy key against the private mailbox before
   switching the service. Keep the old key during the rollback window.
   Confirm with the owner before revocation and verify the replacement again.
4. Capture an idle and queued latency baseline before tuning polling. Check
   Stage 5 provider and model configuration with credentials redacted.
   Benchmark fixed inference requests and recovery after a timeout only
   after the intended backend is enabled. Keep inference time separate from
   mailbox pickup and publication time.
5. Verify per-check names, timings and failure categories for Ruff and
   regression checks on an exact revision before any expanded rollout.

## Private inference probe

Send the standard private request fields with action `inference_probe`.
The physical device constructs the challenge from its validated request ID,
uses the OpenAI Responses adapter with a fixed model and a 96-token output
limit, and compares the complete reply. The public mailbox excludes this action.
Service opt-in uses a device-owned mode-0600 file,
`~/.config/odin-private-inference/key`, inside a mode-0700 directory.
Move the key outside this directory to disable new calls. Keep the SQLite
attempt journal there across checkouts and restarts. It reserves at most two
paid attempts per UTC day, including timeouts and failed calls. A repeat
with the same ID returns saved evidence or an unknown prior outcome.

Run the pinned rollout script from a clean candidate checkout in Termux.
It runs disposable tests, verifies the published old outbox, then switches
the detached pilot checkout while its service is down. Startup failures
restore the old revision. Only the private mailbox receives this capability.

Live acceptance requires a newly submitted request ID, action
`inference_probe`, status `complete`, provider `openai`, provider response
ID, returned model, exact answer match and device timing. Retain the actual
receipt in the private repository. Public documentation records the outcome
only. A request from the handheld to this ChatGPT conversation remains a
separate capability. Expansion waits for combined-path acceptance.

### Hosted device inference check

Use **Chat → Odin Device Inbox → Verify Odin GPT** in a paired session. The UI sends the fixed `/ai-proof` request over the private relay and refreshes the inbox for the matching device reply. This requires the upgraded relay client, working private storage and the on-device private probe credential. Both device entry points share one attempt journal and budget.
