# Odin 2 — Safe self-update and useful device tasks

Date: 2026-11-19
Source authority: GitHub repository shawnfra2013/Oden2-, branch main.

## Existing architecture, not another agent

This release extends scripts/git-sync.sh, scripts/odin-safe-pull.sh, and
scripts/odin_relay_client.py. The existing runit supervisor remains the
five-minute update check. No new background service, cloud database, or
remote shell is created.

The local GitHub checkout can keep itself on the **latest CI-passing**
main revision only after one-time activation. It must not silently install
a failed commit, a diverged history, or a release that would collide with
the five preserved untracked files.

## One-time activation, performed on Odin itself

After GitHub CI has passed on this exact release, run from Termux:

    cd ~/odin-workspace || exit 1
    bash scripts/odin-safe-pull.sh || exit 1
    python -B scripts/odin_auto_update.py --enable
    python -B scripts/odin_auto_update.py --status

This installs the reviewed update once and explicitly enables future
source updates. The control flag is in ignored state/, mode 0600. No
credentials are needed for the public GitHub Actions status API. The
GitHub repository remains the source authority, and existing private
SQLite databases, user files and tokens remain in ignored state/.

The existing git-sync process invokes the updater on each loop. It
fetches the remote main SHA, requires the completed successful **push**
Odin Checks workflow on precisely that SHA, rejects unclean tracked
trees and divergence, then uses scripts/odin-safe-pull.sh. The safe-pull
helper re-fetches and must still match the exact approved SHA. Failing
checks prevent installation.

The supervisor runs approximately every five minutes when Termux and
runit are active. Android can stop background processes. There is no
guarantee of restart after reboot; boot automation remains deferred.

## See status and disable updates

    python -B scripts/odin_auto_update.py --status
    python -B scripts/odin_auto_update.py --disable
    tail -n 25 logs/git-sync.log

Updates are classified as current, waiting, blocked, updated, or error.
The most recent outcome is stored privately in
state/auto-update-result.json. Logs record reason codes but do not
include private conversation content or credentials. The updater does
not delete or reset branches, install packages, or run model-written
commands.

**Important:** updating source files does NOT reload an already-running
Python process. After a successful update, inspect and explicitly
restart affected runit services. Live-restart verification and rollback
will be a separate, consented stage.

## Verified, bounded Odin device commands

Messages to the existing private iPhone-to-Odin relay may contain:

- /ping — proof of the responding Odin transport process (no AI inference).
- /status — read-only abbreviated Git revision, tracked cleanliness,
  untracked file count.
- /task git-status — verified read-only Git task result, same safe facts.
- /task queue-status — read-only counts for pending, running and done.
- Other messages — sent to Odin's configured hosted AI provider.
- Unknown /task requests — rejected; never interpreted as shell commands.

The commands use fixed subprocess arguments, short timeouts, bounded
outputs, and no user-supplied shell syntax. The task commands do not
mutate the existing task-worker queue, and the output is explicitly
marked as a read-only verified result, not as an arbitrary completed
coding task.

The device relay uses one exclusive polling lock. An individual
message error is recorded while later messages can still be processed;
it never silently reclassifies failed delivery as success. Local
status is available via:

    python -B scripts/odin_relay_client.py --status

Use the existing iPhone app at https://odin-control.vercel.app/
under Chat > Messages & responses. Its shortcuts fill the message
field; the user still presses Send. It clearly distinguishes physical
Odin replies and independent cloud API replies.

## Ten release improvements and acceptance checks

1. CI-gated source updates, exact target SHA matched to successful push run.
2. Explicit opt-in and reversible control flag; default disabled.
3. Existing five-minute Git-sync integration; no duplicate daemon.
4. Fast-forward-only, expected-SHA pinned safe-pull protection.
5. Clean local state protected; untracked files preserved.
6. No false Git-sync alert when only unrelated untracked files remain.
7. Exclusive device relay polling prevents concurrent processing.
8. Independent message handling prevents one failed delivery from stopping
   later messages, and old replied messages cannot starve new requests.
9. Bounded read-only device status and task commands, with explicit rejection
   of arbitrary tasks.
10. Private diagnostic status, truthful iPhone waiting/error labels, tests
    and this durable checkpoint.

GitHub CI validates source syntax, Python regressions, Stage 4/5,
Node tests and secret-pattern gates. A successful CI run is not
evidence of a live iPhone round trip or a running device's loaded
revision. Those require separate real-world receipts.

## Next five logical features, in priority order

1. **End-to-end transport smoke gate**: use /ping to confirm a new
   iPhone -> private store -> Odin -> iPhone reply after each hosted
   relay release; surface stale acknowledgments accurately.
2. **Supervised worker task receipts**: queue only approved task types
   to the existing worker, display pending/running/verified outcome in
   the iPhone app, and require approval for changes or pushes.
3. **Private AI provider selection and fallback**: check available
   Groq/OpenAI credentials on Odin; keep keys device-side and model
   answers labeled unverified until independently accepted.
4. **Durable conversation and search**: preserve and recover private
   device conversation IDs, without merging the separate ChatGPT app
   thread or exposing prompts in public GitHub branches.
5. **Staged service reload and reboot recovery**: only after a tested
   update should a separately reviewed supervisor be allowed to restart
   an affected service and verify its health, with a rollback procedure.

These are *next tasks*, not claimed features of this release. Avoid
new infrastructure until a measurable need is demonstrated.

## Git-sync lock reliability — 2026-11-19

The previously used `state/git-sync.lock` **directory** could remain
after a terminated Termux process. It repeatedly logged
`SKIP: another sync is already running` even when no Git-sync child
existed. On-device recovery removed the confirmed empty abandoned
directory; the manually triggered sync then logged `START`,
`ODIN_UPDATE current already_up_to_date`, and
`OK: already synchronized (untracked files preserved)`.

The corrected existing `scripts/git-sync.sh` enters
`scripts/odin_git_sync_lock.py`, which holds a Python `fcntl.flock`
exclusive, non-blocking kernel lock on a private regular file named
`state/git-sync.flock` for the duration of the original sync.
Only a *real, concurrent process* can hold that lock; closing the
descriptor, Termux termination or killing the process releases it.
The lock file itself is deliberately **not deleted**. The original
`state/git-sync.lock` directory, if present, is ignored and preserved.
No new daemon, additional Termux package, boot hook or periodic task.

If two runs overlap, the second writes
`SKIP: active Git-sync process holds kernel lock` and does no work.
Unexpected lock errors are logged and return nonzero to the existing
runit wrapper; the original sync exit status is preserved. The
five-minute schedule, exact-CI-SHA gate, fast-forward checks, tracked
file protection and existing untracked files remain unchanged.

Validate on Odin after a CI-passing GitHub update using:
```bash
cd ~/odin-workspace
bash scripts/odin-safe-pull.sh
bash scripts/git-sync.sh
tail -n 12 logs/git-sync.log
sv status "$PREFIX/var/service/odin-git-sync"
```
A successful manual call proves the updated lock works; proof of
unattended periodic operation requires a *later* scheduled log entry.
Do not remove or reset any lock directory or user files as part of this
new procedure.

## Next milestone — device AI readiness and friendly commands

The authenticated iPhone relay has now returned a genuine
ODIN_TASK_COMPLETE verified=true task=git-status from physical Odin
at the expected Git commit. Transport and the fixed Git task are proven;
a normal *AI* conversation has not yet been proven.

The next code release adds:
- Fixed read-only alias matching for Task git-status, git status,
  check git status, and a small set of device/queue-status phrases.
  The alias matcher does not interpret arbitrary natural language,
  generate a shell command, or grant additional actions.
- /ai-status: returns only provider, AI-enabled, key-present,
  model-configured and ready flags plus a safe reason code from the
  running Odin relay's environment. Even ready=true is **not proof**
  that the provider accepted a request.
- /ai-test: an explicit bounded request through the existing
  on-device model and local SQLite conversation. Its output is
  model text, not a verified action and not this ChatGPT app thread.
- The iPhone displays allowlisted reasons for **failed** AI receipts
  instead of an unexplained failure. Raw provider errors, secret values,
  prompts and local files stay out of this diagnostic channel.

After a green release and a safe source update, restart only
odin-private-relay to load its new Python code. Then send /ai-status;
if it says disabled or a key is missing, configure the existing
device provider privately before attempting /ai-test. Do not ask
the user to paste a credential in ChatGPT, public GitHub branches or
the iPhone message field. Follow up with a normal question and confirm
an actual on-device model response before declaring this milestone done.

No device credential is automatically inferred from the hosted
Vercel cloud AI capability flag; those are independent providers.

## 2026-11-19 — On-demand verified supervised service restart

The user requested both a System UI Restart all services button and
a typed message command. Both use the private authenticated relay,
not the public GitHub diagnostic branch. The UI requires a confirmed
private session, device pairing and human confirmation; it never
passes arbitrary shell input or processes to the device.

The fixed service allowlist: odin-git-sync, odin-task-worker,
odin-github-bridge if installed, and odin-private-relay LAST.
The independent Stage 5 localhost server isn't a runit service and
is excluded. This does not reboot Android or affect SSH or bootloader.

A detached subprocess starts after the private message was marked
read. It records durable private request and result data under
state/odin-relay/restarts. Bounded sv restart calls and sv status
checks determine success/failure. The relay itself restarts last;
its next poll sends the actual outcome to the originating message.
An interrupted operation yields an explicit failure after five minutes.
Requests are deduplicated and locally rate-limited to 10 minutes.

GitHub CI tests input allowlisting, idempotency, throttle, ordering,
missing/failing services, detached execution and timeout recovery.
CI alone does not verify physical runit or actual iPhone receipt.
One initial relay restart after the new code is installed is required
because the already-running old Python process cannot reload itself
using an action it does not yet know. Later authorized requests
require no manual Termux input while the relay remains alive.

### Automatic reload after a CI-gated pull

When source auto-update is enabled, a successful verified fast-forward
reloads running Odin worker, GitHub bridge, and private relay services.
The sync supervisor keeps its lock and uses the new sync script on its
next cycle. Inactive services stay down. Source update and reload outcomes
are recorded separately in `logs/git-sync.log`.

The older updater records a source-only pull on the first transition.
The new updater uses that exact-HEAD record on its next cycle to perform
the initial reload. For a manual pull, use
`python -B scripts/odin_service_restart.py --local` in the Odin checkout.
The local command and authenticated relay share a single execution lock.

## Bridge expansion sequence

1. **Close live acceptance.** After an unattended pull, record the
   before/after revisions and reload result from the device. Request
   `odin_health` and `verify_release` for the exact release. In the paired
   app, test `/ai-status`, a real model reply, and one single-service restart
   with its verified receipt. Stage 5 test success and a running Stage 5
   HTTP listener are separate checks.
2. **Preserve deployment evidence.** Persist the last successful update and
   reload independently of the latest no-op sync. Expose the revision,
   timestamp, reload outcome, and fixed reason codes in health receipts.
   Show receipt age and the distinction between GitHub CI and device tests.
3. **Diagnose common failures with structured actions.** Add worker and
   relay heartbeat age, queue depth, and bounded failure categories. For
   each action, verify permissions, retries, timeouts, and that credentials
   and raw logs stay out of GitHub. Use private diagnostics for sensitive
   detail.
4. **Add private interactive access for deeper debugging.** Use a reachable
   private network path and a revocable, dedicated Termux SSH identity.
   Acceptance requires an authenticated read-only shell probe from the
   intended session and confirmation that removing the key revokes access.

### Durable automatic rollout evidence

The updater writes `state/last-auto-rollout.json` when an automatic pull
reaches the service reload step. It records the exact revision, pull
timestamp, and reload status (`pending`, `verified`, or `unverified`).
Later no-op or failed syncs preserve that record. The first automatic
pull performed by the new updater supplies the first record. Confirm it
from an Odin health receipt after at least one subsequent no-op sync.

After the heartbeat release, request Odin health with the worker and private
relay active. Confirm both ages and both queue counts. The worker records
its heartbeat before starting a queue cycle, so age can increase while a
task runs. Use service state and running count alongside heartbeat age.

### November 19 connection and acceptance audit

The managed task worker already executes local queue items. Stage 5 has
its own loopback-only runit service so a browser-server failure can be
recovered independently. On an opted-in Termux checkout, an idle,
synchronized git-sync cycle installs the new service only when the
service path and local port are both free. A separate existing listener
is preserved. Verify both service status and HTTP reachability in a
fresh device health receipt. Boot automation and launcher changes remain
deferred.

The Stage 5 tab retains the selected SQLite conversation ID across
refresh and offers New chat. It checks health on returning to a tab
or coming online, and retries a failed health check without resending
a chat message. The hosted dashboard uses the newest applicable health
receipt for the Stage 5 indicator.

Before hardening, collect evidence for the signed production wake path
(including wake versus timer provenance and a reconnect), iPhone private
model reply, both bulk restart entry points and a single-service restart,
and a proposal created and tested on Odin. Record rollout evidence after
a later idle sync. The historical 5.6/5.7 lab command transcript remains
incomplete. Private SSH and the operator-deferred boot flow are separate
milestones. The Friday read-only report is already scheduled.
