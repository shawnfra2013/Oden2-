<!-- ODIN_STAGE4_CHECKPOINT_2026-11-10 -->
# Odin — Technical Project Memory

Checkpoint: November 10, 2026.
This is technical project memory, not personal ChatGPT memory.

## Identity
Device: AYN Odin_M2, Android 10, Termux.
Workspace: ~/odin-workspace
Repository: shawnfra2013/Oden2-
Branch: main
Last verified local and remote HEAD: 0c8d378

## Verified implementation
- Orchestrator, pipeline, development controller, health check, proposal builder, worker and Stage 4 tests are present locally.
- 32/32 regression tests passed in a disposable filesystem copy.
- Ruff linting passed.
- Groq openai/gpt-oss-120b live inference passed via curl.
- GitHub remote-read main matched local HEAD.
- The newer Stage 4 files remain unpublished.
- Worker and sync services were running at last check; active task processing remains unverified.

## Queue snapshot
- 4 complete
- 8 failed
- 5 proposal_ready
- 2 unverified
- 20 non-JSON artifacts

These labels do not independently prove successful live jobs.
Historical failures require inspection before assigning causes.

## Historical Claude and assistant discrepancies

1. DEVICE MISIDENTIFICATION:
Earlier Claude-related guidance used an Odin 2 Mini profile or discussed rooting without confirming the original Odin_M2 device.
Do not infer Mini hardware, firmware or root compatibility.

2. EXECUTION CLAIMS:
Earlier assistants sometimes treated proposed, truncated or unexecuted scripts as completed operations.
Require actual command output and confirmed backups before declaring success.

3. HISTORICAL STAGE 4 FAILURE:
An October 17 candidate reportedly had 22 errors across 29 tests, including an os.link problem in pipeline.py around line 112.
The newer local snapshot passed 32 tests.
This does not prove which revision is loaded in the live worker.

4. ANDROID RESTORATION:
Prior debloat instructions risked treating restoration of installed packages as a full app-data backup.
Package restoration is not equivalent to restoring application data.
Android modifications are outside current Stage 4 scope.

5. PROVIDER ERROR ATTRIBUTION:
Historical Anthropic authentication/billing errors are different from the Groq urllib 403 and later successful curl 200 requests.
Do not claim Claude caused current errors without direct evidence.

6. COMMAND DELIVERY:
Malformed command prefixes such as nbash or incomplete heredocs are paste/execution errors, not proof of worker defects.

7. GITHUB SAFETY:
Existing Git sync intentionally protects dirty repositories.
Do not disable safeguards merely to force a push.

## Operating rules
- Stabilize existing components only; do not introduce new features.
- Preserve uncommitted changes, queues, credentials and service definitions.
- No git reset --hard, git clean, force-push or blind pull.
- Do not commit runtime state, logs, secrets or API keys.
- Use verified output rather than assistant assertions.
- Keep Termux commands complete and copyable.
- Distinguish local tests from live worker behavior.
- Inspect the existing README and GitHub workflow edits before changing them.

## Stage 4 completion gates
1. Classify historical failures safely.
2. Run one harmless task through the live worker and verify its receipt.
3. Confirm GitHub Actions runs Stage 4 tests.
4. Review intended files and secrets before commit.
5. Push approved changes and verify Actions on the new commit.

Stage 4 is not complete until those gates pass.

<!-- ODIN_STAGE4_LIVE_WORKER_2026_11_10 -->

## Live background-worker verification — 2026-11-10

- PASS: Live worker accepted task 3825285bfacc.
- PASS: Task finished with status complete.
- PASS: Git-status verification returned code 0.
- PASS: Task output SHA-256 checksum matched its receipt.
- PASS: Existing Stage 4 regression suite, 32/32 tests.
- PASS: Separate live Groq 120B curl inference.
- NOT YET VERIFIED: AI orchestration through the live worker.
- NOT YET VERIFIED: GitHub Actions on the unpublished Stage 4 code.
- Historical failed task records still require classification.
- No source-code commit, push or worker restart was performed.

<!-- ODIN_STAGE4_AI_WORKER_2026_11_10 -->

## Live AI-worker functional checkpoint — 2026-11-10

- Task ID: 3daf406c1df6.
- Submitted question: 19 multiplied by 17.
- Original task log contained a standalone answer of 323.
- Task ID and checkpoint ownership matched.
- Checkpoint status remained unverified by design.
- Orchestrator respond() calls the ask() model-request path.
- Saved checkpoint did not include assistant final text or a provider request ID.
- Assessment: live AI-worker behavior observed; individual provider-request provenance not independently established.
- No automatic deployment or code modification was authorized by this task.
- Release and GitHub Actions verification remain pending.

## 2026-11-14 — Canonical Odin checkpoint
- GitHub and local main verified at 6d3423d.
- Both Odin services verified running on November 14.
- Earlier Stage 4 checks: 38/38 tests and CI run 43112942632 passed.
- Live Groq inference and a harmless worker task were previously verified.
- Historical queue: 23 JSON records classified, including 8 failures.
- AI provider-request provenance remains unverified.
- Current queue, recovery state, and loaded worker revision still require verification.
- User explicitly deferred bootloader and automatic startup work; these are not development blockers.
- Separate ChatGPT-to-Odin bridge removed from the roadmap by user decision.
- Priority: finish documentation and CI verification, then continue hardening native Odin capabilities.
- Preserve historical records, credentials, services, and recovery evidence.
- Use read-only inspection, isolated tests, and verified results before changes.

<!-- ODIN_STAGE4_PROVENANCE_2026_11_14 -->
## 2026-11-14 — Stage 4 provenance development checkpoint

- Development location: ~/odin-stage4-lab, isolated from the live workspace.
- Latest observed live HEAD: df8bb37; historical checkpoint 6d3423d retained.
- Live Git status contained untracked file e; preserve it.
- Implemented inference receipt collection and checkpoint persistence.
- Interactive resume retains prior receipts; task outcome remains unverified.
- Added five regression tests; complete suite passed 43/43.
- Ruff and compilation passed in isolation.
- CI workflow locally updated to discover test*.py.
- Direct CLI startup ordering corrected; --help launches the interactive CLI rather than displaying help.
- Changes have not been published to GitHub or loaded by the running worker.
- Provider metadata is provider-reported, not independently verified.
- Next gates: controlled source review, approved publication, GitHub Actions verification and live revision verification.
- No bootloader work, boot changes, queue mutation or separate execution bridge.

<!-- ODIN_STAGE4_LIVE_VERIFIED_2026_11_14 -->

## Stage 4 live verification — 2026-11-14

- Published commit: `777c3ec65690167bd7d5075ea427e91f72b1f39c`.
- GitHub Actions: Odin Checks run `43640303358` completed successfully.
- Local validation: 43/43 regression tests passed.
- Runtime activation: `odin-task-worker` restarted successfully,
  PID `13622` to `15603`.
- Git sync remained running under PID `13625`.
- Live verification task: `ed1619c049ea`.
- Task outcome: `unverified`, as required for conversational
  tasks without deterministic acceptance contracts.
- Checkpoint contains an inference receipt for Groq
  `openai/gpt-oss-120b`, including provider-reported response
  ID and token usage (262 prompt, 62 completion, 324 total).
- `provider_request_traceable` is true;
  `independently_verified` remains false.
- Queue after the test: zero pending and zero running tasks.
- No bootloader changes or new feature activation.

## Stage 5.5 verified checkpoint — 2026-11-14

- Stage 5 source location: `stage5/`.
- Previous isolated development: `~/odin-stage5-lab/stage55`.
- Browser backend: Python standard-library HTTP server.
- Security scope: localhost prototype, not remote authentication.
- Groq model: `openai/gpt-oss-120b` through Stage 4 orchestrator.
- AI disabled unless `ODIN_STAGE5_ENABLE_AI=1`.
- Child-process deadline: 45 seconds.
- Live browser marker: `ODIN_STAGE55_LIVE_OK`.
- Offline tests: Stage 5 25/25; Stage 4 43/43.
- Provider receipt not independently verified for browser request.
- No task persistence, remote bridge, or bootloader changes.
- Next release gates: complete CI, review scoped diff, commit, push, verify GitHub Actions.

<!-- ODIN_CANONICAL_2026_11_15 -->
## Current verified baseline — 2026-11-15

- Device: AYN Odin_M2, Android 10, Termux.
- Repository: shawnfra2013/Oden2-, branch main.
- Audited commit: 07cf2b6d7190ce488adf4066cccfdc301ef1099b.
- Local HEAD, origin/main and GitHub main matched.
- GitHub Actions Odin Checks: run 43663313265 passed.
- Stage 4 regression tests: 43/43 passed.
- Stage 5 regression tests: 25/25 passed.
- Ruff: passed.
- Git sync and task worker were running at the service check.
- Worker PID 7531 was running scripts/odin_worker.py
  from the expected workspace.
- Exact source revision loaded in worker memory was not
  independently established.
- Queue: zero pending and zero running JSON tasks.
- Historical done-directory JSON records: 25 total;
  6 complete, 8 failed, 5 proposal_ready, 6 unverified.
- Historical statuses do not establish that all task
  outcomes were independently verified.
- Stage 5.5 browser interface and backend passed offline
  tests and a previous live browser verification.
- Stage 5 HTTP server was offline at the latest check;
  it is not established as a persistent service.
- Stage 5 browser responses are not persisted and
  provider-request provenance is not independently verified.
- Four identical untracked files of 17,499 bytes remain
  unidentified and preserved. A fifth untracked file,
  main, is empty.
- state/bridge-reporter is a separate nested Git repository
  excluded by the parent repository's state/ ignore rule.
- Automate launcher work is deferred.
- Termux:Boot installation and unattended reboot
  verification are deferred.
- Bootloader work is deferred.
- No production code changes or service restarts were
  performed for this audit.
- Earlier dated checkpoints remain historical records;
  this section supersedes their pending-status claims
  for the checks explicitly verified above.

Remaining limitations:
- Identify and safely handle the untracked files.
- Loaded worker revision has not been independently proven.
- Persistent Stage 5 startup is not configured or verified.
- Generic AI task acceptance, independent provider-request
  authentication, and persistent browser conversations
  are not established.

## Stage 5.6 and 5.7 lab recovery — 2026-11-15

- GitHub's published browser implementation is Stage 5.5. Stage 5.6 and
  5.7 were exercised in the separate Android 10 / Termux lab
  (`~/odin-stage56-lab`). Their implementation is pending recovery or
  reconstruction on GitHub.
- Stage 5.6 added a SQLite conversation store and API. Recovered references
  identify `conversation_store.py`, `conversation_api.py`, the
  `conversations` and `messages` tables, and `/api/conversations` and
  `/api/conversations/<id>`. The lab notes record SQLite readback of a
  user message and its reply.
- Stage 5.7 fed saved history from the selected conversation into the
  inference adapter. Recovered limits were 12 messages, 4,000 characters
  per message, and 12,000 characters total. History excluded system roles.
- Reviewed screenshots `Screenshot_20261115-052603.png` and
  `Screenshot_20261115-052649.png` show recall of test value 47 in the
  original conversation and no disclosure when a different conversation
  asked for it. Earlier lab notes report 53 Stage 5 and 43 Stage 4 tests
  passing. These results apply to the lab.
- The full schema, route handlers, and original regression files are
  still missing. Before publishing the functionality, review those
  boundaries and verify persistence, bounded history, and per-conversation
  isolation against the exact GitHub revision being reviewed.

## Hosted iPhone relay stabilization — 2026-11-19 (latest checkpoint)

- Repository: `shawnfra2013/Oden2-`. Relay repair PR #13 merged to
  `main` as `1e8f73f10958cc66159861c05a9d9e4ee80ce77b`.
- GitHub Actions PR validation `44478622727` passed, including Python,
  Stage 5, Node module syntax and authenticated relay handler tests.
- Vercel existing project: `odin-control`, domain
  `https://odin-control.vercel.app/`. Production deploy
  `dpl_Ana2JCHZFYEimuv2ztbQ9u2wgjtS` reported READY.
  Verified public `/`, `/api/capabilities`, and `/api/status` returned
  HTTP 200. Unauthenticated `/api/relay` returned HTTP 403 as expected.
  A **new authenticated end-to-end phone ↔ Odin `/ping` round-trip remains
  unverified**; never substitute offline tests for that proof.
- Root cause of observed private inbox failure: `mobile/api/relay.js`
  called `validOrigin`, but `mobile/lib/access.js` did not export it.
  Vercel runtime errors showed five `TypeError: validOrigin is not a
  function` failures. Export fixed; CI now tests the full protected
  handler and refusal paths. Sanitized storage failure stages added.
- Existing production Vercel environment configuration checked:
  `ODIN_CONTROL_ACCESS_TOKEN`, `ODIN_DEVICE_RELAY_TOKEN`,
  `BLOB_READ_WRITE_TOKEN`, and `ODIN_OPENAI_MODEL` exist.
  `OPENAI_API_KEY` and `ODIN_GITHUB_TOKEN` do not exist; therefore
  hosted cloud AI chat and app-originated GitHub diagnostic writes remain
  disabled. Do not publish any token values. Private Blob store connected.
- Vercel project feature flags: no active flags and no Flags settings
  configured; no new feature flag platform or monitoring service created.
- User's last on-device Termux output showed `main` at `12e861d`,
  `odin-private-relay` runit PID 4646 and successful zero-message
  private poll at that time. This does **not** verify the later live
  iPhone-to-Odin test or continued background uptime.
- Device checkout had five preserved untracked files; no reset, deletion,
  or forced update approved or performed.
- Existing `odin-git-sync` fetches and conditionally pushes; it **does not**
  automatically pull/restart latest code. Existing read-only log is
  `logs/git-sync.log`; wrapper now emits nonzero exit status rather than
  `|| true`. Safe reviewed manual update remains
  `scripts/odin-safe-pull.sh`.
- Odin-side source and any running Python service do not update solely
  because GitHub `main` was merged. Autopull with CI gates and boot
  persistence remain separate work, deferred to avoid unsafe hot updates.
- Current architecture source-of-truth: `docs/architecture.md`;
  private pairing and test instructions: `docs/ODIN_PRIVATE_RELAY.md`.

## Odin 10-point stabilization and safe update release — 2026-11-19

**Canonical reviewed code release:** `b6fedfc70b027ca66afe48853b668fdd3f2d9121`
(merged PR #17). GitHub Actions `Odin Checks` main push run
`44486431089` concluded **success**; checks included 94 Stage 4/bridge
Python tests, 32 Stage 5 Python tests, 29 Node tests, Ruff, Python
compilation, Bash syntax, secret scanning, and repository sanity.

**Existing iPhone deployment:** `odin-control` production deployment
`dpl_AgEhBdNf9DpYHv59agr3N91sLvba` was **READY** at
`https://odin-control.vercel.app/`.
Live unauthenticated checks:
- `/` HTTP 200; device task shortcuts and private message view present.
- `/api/status` HTTP 200 and reported reviewed GitHub commit
  `b6fedfc70b027ca66afe48853b668fdd3f2d9121` and CI success.
- `/api/capabilities` HTTP 200; access/pairing/private relay configured,
  hosted cloud API model **not** configured.
- Unauthenticated `/api/relay` HTTP 403 (expected protection).
- Latest sampled Vercel `/api/relay` runtime error query returned no
  errors in the selected 15-minute window. This does **not** establish
  authenticated message acceptance or device-origin replies.

**Device execution state:** The last user-provided Termux update proved
the Odin checkout had fast-forwarded to `523f7769ea15d311dbf0b9320a5d28e64b428b40`
and preserved five untracked files. A previous live GitHub status receipt
also showed the older `12e861d` revision, prior to that manual update.
No direct remote terminal has been connected. The source release
`b6fedfc` has **not** been proven installed on the physical device.
A new local fast-forward and one-time explicit safe-updater enablement
are required. Running `odin-private-relay` Python code does not reload
itself merely because files change. The local device's safe update flag
and background services have not been confirmed after this release.

**Diagnostics:** Four recent read-only GitHub bridge requests were
submitted for `ping`, `repo_status`, `services`, and `checks`.
At the latest check no matching new outbox receipts had appeared.
Do not treat these as passed until an actual receipt exists.
A fresh authenticated iPhone-to-Odin `/ping`, two independent messages,
and one verified device task are also **not independently proven live**.
The 3-message/1-task success in CI used mocked transport and was
an offline regression test, not a production result.

**Change scope:** `scripts/odin_auto_update.py` is an opt-in,
CI-gated source updater called by the existing `git-sync.sh` service.
It approves only a successful GitHub push workflow for the exact
current `main` SHA and uses the existing pinned fast-forward-only safe
pull. No data deletion, force reset, new daemon, package installs,
boot automation, or unsupervised service restart was added. Default
auto-update state is **disabled** until explicitly enabled on Odin.
The relay client now uses an exclusive poll lock, per-message failure
isolation, bounded receipt/status persistence, and fixed read-only
`/status`, `/task git-status`, `/task queue-status` actions.
The iPhone composer provides shortcuts, status labels, and separated
cloud API/device sources.

**Authoritative instructions and five-feature plan:**
`docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md`. Earlier checkpoints remain
historical; the release above supersedes earlier source-head claims only
for checks explicitly verified here.

## Bridge expansion checkpoint — 2026-11-19

The physical Odin was manually verified at
`539ca3e7a791c5ff54106827f32b17432789c93d`. Termux preserved all five
untracked files and confirmed all four runit services after a local restart.
Odin subsequently returned an exact-revision receipt with Stage 4, Stage 5,
and Ruff passing. The hosted dashboard displayed that receipt.

The expanded bridge shipped in PRs #25 and #26. Main commit
`206ccdd142ff6b177611a068cfd079dcb739d40f` passed GitHub Actions run
`44544616441`. The combined diagnostics action reads the actual runit
process state and updater result. The authenticated inbox can request a
fixed named service restart, with the existing cooldown and durable result.
A direct Codex-to-Termux SSH session has not been established. See the
release roadmap for live acceptance and the next expansion.
