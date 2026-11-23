# Current private GitHub mailbox runbook

Canonical operating details: [Odin runtime](ODIN_RUNTIME.md). Older public-mailbox commands and hosted-relay experiments are preserved in [the archived runbook](archive/ODIN_GITHUB_BRIDGE_before_2026-11-22.md).

The device bridge uses the **private** repository `shawnfra2013/Odin-private-bridge`. Odin polls `odin-bridge-inbox` and publishes bounded replies in `odin-bridge-outbox` using its existing authorized SSH configuration. The private workflow is [here](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml).

**Read-only live test:** submit one `ping` through the private workflow or authorized GitHub integration. Match the generated request ID to the exact outbox receipt; confirm `status=complete`, the `checked_at` timestamp, and the allowlisted `alive` result. To check the Odin Local Workstation, use `stage5_health` (compatibility action name) and inspect `reachable`. Neither test calls a model.

A successful request submission, previous receipt, or passing source-code tests cannot establish current connectivity. A `stage5_health` receipt proves the local HTTP service was reachable **at that receipt time**, not that a particular source revision or iPhone route was installed.

**ChatGPT operating quickstart:** [Working with Odin](WORK_WITH_ODIN.md) specifies the route and receipt stages. Prefer the existing private dispatch workflow or an authorized GitHub write to a fresh `bridge/requests/<id>.json` in `odin-bridge-inbox`, then inspect the exact matching `bridge/responses/<id>.json` on `odin-bridge-outbox`. The request is version 1 with 32 lowercase hexadecimal ID, allowlisted action, UTC creation and positive expiry of at most an hour. A `ping` passes only when the corresponding `complete` response reports `result.alive=true`. Check near the normal minute polling interval with a deadline and avoid repeat pings. If no response is observed, report UNVERIFIED and use the launcher preflight below; do not send arbitrary shell requests or claim an always-on ChatGPT session.

**Independent source-only ping evaluation:** [PING_VERIFICATION.md](PING_VERIFICATION.md) documents the local `odin_ping_verifier.py` helper. It checks one copied request and matching receipt for identity, `alive=true` and freshness, but never contacts Odin or proves a running process. The existing GitHub workflow remains the request trigger.

## Canonical Termux launcher and state migration

**Latest verified state (2026-11-23, supersedes earlier mismatch):** the owner explicitly approved and executed the guarded local migration; `status=MIGRATED`, new `odin-private-mailbox` PID **9200**, source revision `1e3f309e6b7b3f84b1a9dc96524b9ace0b369dc2`, and original private state preserved with launcher backup. A fresh private ping `b710202611231656320000000000000a` completed **16:57:01Z**, PID 9200, `alive=true`; read-only `mailbox_migration_preview` `b710202611231657000000000000000b` completed **16:58:07Z** with `ALREADY_CANONICAL`, `canonical_checkout_confirmed=true`; post-migration `mailbox_audit` `b710202611231657130000000000000c` completed **16:58:15Z**, 6 matched/1 snapshot-pending, 0 malformed/stalled/rejected/incidents. Physical local preflight: 11 PASS, 0 FAIL, 5 UNVERIFIED. **Migration is complete; do not execute the operator-only apply command again.** Preserve backup, old state and old checkout. Earlier READY-only statements below are historical runbook explanations, not the current action queue. Remaining model, reboot, secure HTTPS/iPhone gates are independent and still UNVERIFIED.


A runit `odin-private-mailbox` process may be **running** while executing an obsolete temporary checkout. Check both the launcher `$PREFIX/var/service/odin-private-mailbox/run` and the running process's `/proc/<pid>/cwd` against `~/odin-workspace`. The device preflight now labels a mismatched launcher or live process **FAIL**, never PASS because `sv status` is green. A fresh `ping` reports the repository SHA seen by the running process but is not, alone, evidence of its filesystem location.

**Observed November 23 incident:** the supervised launcher pointed to `~/odin-pr45-test.iwGRYw`; the canonical checkout was current, but the live state, outbox Git clone and logs were stored under the temporary checkout. An initial read-only migration check found both source revisions equal, no tracked modifications, no pending receipt journals, zero unpushed outbox commits and a clean private outbox. Do **not** delete old checkouts or overwrite an existing canonical state directory.

**Approved migration sequence (operator action, not automatic):** First inspect source/destination private state and service launcher, preserve a copy of the launcher, gracefully stop only `odin-private-mailbox`, recheck pending receipt journals, outbox divergence and uncommitted changes, copy the private bridge state to the canonical checkout without replacing existing files, replace only the launcher `cd` target, start only that service, then verify live process cwd, a fresh matching private `ping` and `mailbox_audit` receipt. Keep the original private state and launcher backup available for rollback. If any path, state collision or pending/unpushed evidence differs, **stop and inspect** rather than resetting or deleting it. The private SSH key stays in Termux's existing `~/.ssh` location and is never copied into GitHub.

## Read-only migration preview through the existing private mailbox

After the reviewed device code is **actually installed and loaded**, a new fixed private action `mailbox_migration_preview` can run `odin_mailbox_migrate.check` remotely **without granting a shell**. This action is deliberately read-only: it performs the same canonical checkout/source SHA, private journal, clean-outbox, service launcher and process cwd checks as the local dry-run. The private request must contain only standard version/ID/created/expiry fields plus `action=mailbox_migration_preview` and an exact 40-character `expected_sha`. It is rejected on the public mailbox, on unknown fields, or on invalid/mismatched revisions. Result fields are strictly bounded status/reason categories, reported SHA and PID; no private paths, keys, logs or receipt bodies are returned. `READY` is a **candidate** for separate owner review, not an authorized apply; `ALREADY_CANONICAL` is a runtime observation. `BLOCKED` retains state unchanged.

The historical running bridge may not recognize this action until source rollout and service reload: a GitHub merge alone cannot make the current Termux interpreter accept new actions. Never bypass a missing response by posting shell text, and never invoke `--apply` without a current safe preview and explicit physical operator approval. No state is copied and no service is restarted by this diagnostic.

## Guarded one-service migration utility (operator-controlled)

After reviewing [the verified launcher mismatch](https://github.com/shawnfra2013/Oden2-/issues/71), Odin now provides a dedicated, fail-closed, **dry-run-first** migration helper. It does not install code or run automatically.

From an exact, approved canonical checkout, preview the move before touching any service:

```bash
python -B scripts/odin_mailbox_migrate.py --expected-sha "$(git rev-parse HEAD)"
```

The preview confirms the current `odin-private-mailbox` runit launcher, its live `/proc/PID/cwd`, canonical `main` SHA, no tracked code changes, the exact private outbox remote and branch, no pending source/feedback/response journals, no unpushed private commits, and no conflicting canonical private state. The tool does **not** fetch, push, restart or modify state in preview mode. A prior clean check is only a snapshot: it is repeated after the service is stopped in apply mode.

**Apply is a separate operator authorization.** Run it only after preview reports `READY` and after reviewing the intended state-copy operation:

```bash
python -B scripts/odin_mailbox_migrate.py \
  --expected-sha "$(git rev-parse HEAD)" \
  --apply --confirm MIGRATE-ODIN-MAILBOX
```

When approved, the helper backs up the original launcher under `~/.odin-preservation/`, stops **only** `odin-private-mailbox`, rechecks all three pending journals and private Git state, copies the private outbox and logs into previously absent canonical `state/github-bridge-private` (never moves or deletes the original), restricts copied file permissions, atomically changes only the launcher's `cd` directory, restarts only the mailbox, and verifies the new live cwd. A failed restart attempts to restore the original launcher and service; copied state and the old checkout are preserved for forensic review. No force push, reset, private key export, change to `odin-git-sync`, or arbitrary shell execution over the bridge.

**Stop conditions:** Unexpected launcher contents, mismatched live PID/cwd, existing canonical private state, unsafe path or symlink, outbox divergence, journal, source SHA mismatch, oversized state, or failed service transition all block further migration. If a staging directory remains after an interrupted copy, preserve it for inspection—do not delete it automatically.

**Post-migration verification:** Run `python -B scripts/odin_preflight.py --mode device`, `sv status "$PREFIX/var/service/odin-private-mailbox"`, and request a **new** matching allowlisted private `ping` plus `mailbox_audit` receipt. A successful launcher migration does not establish phone connectivity or an AI's source-editing capability.

## Offline development source receipts

A portable test run (`python -B scripts/odin_codespace.py test`) saves a source-only receipt under the canonical Odin checkout at `~/odin-workspace/state/codespace-receipts/<id>.json`. The **existing** supervised private mailbox polls about once per minute when connected and, on this version of the bridge, uploads up to three valid receipts per cycle to the **private** `odin-bridge-outbox` branch at `bridge/local-source-receipts/<id>.json`. No tokens, code, chat transcripts, terminal stdout/stderr, or passwords are copied into the receipts. Uploading is part of the already-authorized private transport; it neither executes a command nor edits source.

A disconnected handheld preserves its local receipts. On reconnect, the private bridge first finishes any interrupted local Git commit or retries an ahead-of-remote push, then publishes newly queued source receipts. Original receipts remain on Odin; replayed IDs must have identical content, and conflicting IDs halt that upload instead of overwriting evidence. Missing/invalid test receipts are skipped safely, not interpreted as successes. A private `ping` can include the latest `last_source_receipt_push` marker; that marker means a receipt upload completed at its recorded time, **not** that an AI model responded or a device test passed.

When reviewing receipts from ChatGPT or scheduled GitHub checks, distinguish **(a)** requested device action replies in `bridge/responses/`, **(b)** unprompted local source-test receipts in `bridge/local-source-receipts/`, and **(c)** GitHub Actions results tied to the exact source SHA. Use IDs, status, SHA and UTC timestamps to avoid duplicate/stale findings. ChatGPT monitoring is scheduled rather than continuously connected; mailbox polling does not wake a Codespace or an interactive ChatGPT turn.

**Operator live test (after approved installation/reload):** In Odin Termux, run the source test command; observe its locally saved ID; confirm the matching private branch receipt arrives; repeat the bridge poll or restart the connection to prove no duplicate; and confirm a new private `ping` returns a matching last-upload ID. To test a genuinely offline period, run a second source test with connectivity disabled, reconnect, and check that exact ID appears once. If offline dependencies are missing, the recorded test outcome is FAIL, not a successful test.

## Structured local private response trace (source-only until updated)

The existing private bridge now makes a **best-effort, append-only structured trace** after publishing a request's private response. It stores only the 32-character request ID, allowlisted action name, receipt status and UTC timestamp, local source SHA and bounded action duration when available. It deliberately excludes request bodies, private Git message contents, model conversations, network tokens and terminal output.

It writes to ignored `state/odin-traces/events.jsonl` with 0600 file permissions and a 2 MiB maximum. Repeated IDs with identical evidence are ignored; conflicting replays are rejected and recorded in the existing bridge log. A logging error never converts an already-published response into a failed action, retries it, or changes the existing delivery mechanism. It does **not** certify a coding-agent read, physical device/phone access, or browser round trip.

After an approved exact-SHA update and verified canonical launcher/cwd migration, inspect the last hour using:

```bash
python -B scripts/odin_trace_log.py --hours 1
```

A missing local journal shows `events=0` as **no observed trace records**, not proof no work occurred. At the 2 MiB cap, append is blocked rather than silently deleting history; preserve/archive state through a separately approved process. The existing [mailbox auditor](#private-mailbox-audit-read-only) independently checks GitHub-side request/response correlation and can detect events that never reached local journaling.

## Private mailbox audit (read-only)

After an approved checkout update, a Termux operator or authorized local agent can run `python -B scripts/odin_mailbox_audit.py --hours 1 --save`. It reads the **local** private inbox ref and outbox Git objects only: no GitHub fetch, credentials, model call or command execution. For each recent request it checks a corresponding response ID/action, timestamp, outcome, unexpected command completion, and overdue or orphaned replies. Reports are stored as immutable private snapshots under `state/mailbox-audits/`. Exit code **0** means no incidents in the requested window; **1** means findings, and **2** means the audit itself could not run. Reports redact message payloads and cannot attest to agent understanding or live ChatGPT notification.

**Remote bounded audit request:** The private bridge additionally accepts the exact action `mailbox_audit` with only the standard ID and UTC expiry fields. When installed and loaded on Odin it runs the fixed local read-only auditor for the last hour, saves a local audit snapshot, and returns only bounded counts, status codes, IDs, response latency and source SHA. This does **not** give ChatGPT arbitrary terminal access. The action is not accepted by the public bridge; extra fields like `command` are rejected. A response to this new action requires a refreshed physical Odin release and cannot be claimed from a source test alone.

GitHub receives device receipts as they are pushed. ChatGPT's existing receipt watcher is **hourly**, not event-pushed. Do not claim that GitHub immediately wakes this ChatGPT conversation. See [the dated collaboration trial](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md) for measured eight-message queue behavior and outstanding wake-up limitations.

## Feedback tool presentation receipts

A review note already stored by the private `review_feedback` action remains **untrusted data**. To have an authorized local tool explicitly present one saved message, use the Termux terminal or a properly attached coding agent:

```bash
cd ~/odin-workspace || exit 1
python -B scripts/odin_review_feedback.py --list
python -B scripts/odin_review_feedback.py --inspect EXACT_32_CHARACTER_FEEDBACK_ID
```

The explicit `--inspect` operation prints the stored note to the *local tool only* and atomically saves a **metadata-only** receipt in `state/github-bridge-private/feedback-tool-observed/`. The existing private mailbox service then sends these receipts to `odin-bridge-outbox:bridge/feedback-tool-receipts/<id>.json` when connected, preserving local originals, rejecting mismatched IDs and recovering interrupted commits. Receipt fields include only the message ID, reviewed head SHA, issue/PR, note digest, UTC presentation time and `action_executed=false`, `agent_identity_verified=false`. No original note, terminal output or command is published.

**Evidence boundary:** this proves a specific local tool invocation displayed the note and the private mailbox delivered its metadata. A human could have invoked the tool; therefore it does **not** prove model cognition, genuine autonomous agent identity, an implemented correction, or source CI. Those need separate task/PR/test receipts under [the collaboration proof contract](COLLABORATION_FRAMEWORK.md).

For a fresh rollout use [release gates](RELEASE_GATES.md). For encrypted phone-model messages use [offline chat](OFFLINE_CHAT.md). Do not publish private responses, secrets, pairing codes, SSH keys, or full private messages in a public issue. The legacy public diagnostic branches remain distinct from the **active private** device mailbox.
