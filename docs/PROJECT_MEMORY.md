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
