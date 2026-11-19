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
