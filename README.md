# Oden2-
Oden ADB OS edits/build


<!-- odin-stage4-20261017 -->
## Stage 4 stabilization — October 17, 2026

Task-bound proposal provenance, confined atomic writes, collision-safe evidence, and structured command results. See [Stage 4 verification](docs/stage4-stabilization.md).
Verification: `python -B -m unittest discover -s tests -p test_stage4.py -v`.


<!-- ODIN_STAGE4_CHECKPOINT_2026-11-10 -->
## Stage 4 — verified checkpoint (2026-11-10)

**Status: Stabilization in progress; not yet end-to-end accepted.**

- Platform: Odin_M2, Android 10, Termux.
- GitHub main: remote read and local HEAD matched 0c8d378; pushing remains untested.
- Code: Ruff passed; 32/32 Stage 4 tests passed in a disposable copy (1.801 seconds).
- Hosted inference: Groq openai/gpt-oss-120b via curl returned HTTP 200 and ODIN_STAGE4_OK.
- Python urllib returned HTTP 403 while curl succeeded. Root cause unknown.
- Task queue: 4 complete, 8 failed, 5 proposal_ready, 2 unverified, plus 20 non-JSON artifacts.
- Services were running at the last check, but live task processing remains unverified.
- Local Stage 4 modules have not yet been published to GitHub.

**Remaining:** verify one harmless task through the live worker, classify historical failures, review Git changes, commit and push approved files, and verify GitHub Actions.

See docs/PROJECT_MEMORY.md for historical discrepancies and safe continuation rules.

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

<!-- ODIN_STAGE4_VERIFIED_2026_11_11 -->
## Stage 4 stabilization — verified update (2026-11-11)

- GitHub: stabilization commit 6d3423d pushed to main.
- CI: Odin Checks run 43112942632 passed.
- Validation: 38/38 Stage 4 regression tests passed; Ruff and compilation checks passed.
- Hosted inference: live Groq 120B request succeeded.
- Worker: harmless live task completed with verified receipt.
- Historical queue: 23 JSON records classified (5 complete, 8 failed, 5 proposal_ready, 5 unverified).
- Historical failures: all 8 accounted for; causes include Groq requests, credentials, lint validation, and proposal validation.
- Queue artifacts: worker.lock confirmed as an intentional worker locking mechanism.
- Security: Groq credentials removed from curl command arguments; worker recovery and source checks hardened.

Remaining limitations:
- Historical failure classification does not establish that every failure mode is resolved.
- Individual AI provider-request provenance is not independently established.
- Unattended startup after reboot is not conclusively verified.

Stage 4 remains under stabilization; no new features are authorized.

<!-- ODIN_STAGE4_PROVENANCE_2026_11_14 -->
## Stage 4 inference provenance — isolated verification (2026-11-14)

- Implemented per-task inference receipt collection using ContextVar isolation.
- Checkpoints now persist provider-reported model, response ID and available token usage.
- Interactive resume restores saved inference receipts.
- Existing task outcome semantics remain unchanged; unverified is not promoted to complete.
- Offline acceptance: 43/43 regression tests passed; Ruff and Python compilation passed.
- GitHub Actions test discovery updated to include all test*.py files.
- Direct CLI startup ordering corrected and protected by a regression test.
- These changes remain in the isolated odin-stage4-lab; not yet published or activated.
- Provider-reported identifiers are not independently authenticated request provenance.
- Live worker behavior with this revision and GitHub CI on this revision remain unverified.

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

## Stage 5.5 — Browser AI checkpoint (2026-11-14)

- Isolated browser interface promoted to `stage5/`.
- Local-only HTTP server at `127.0.0.1:8765`.
- Groq inference disabled by default.
- Existing Stage 4 orchestrator reused without modification.
- Child-process inference adapter enforces a 45-second overall deadline.
- One concurrent model request permitted.
- Browser test returned `ODIN_STAGE55_LIVE_OK`.
- Stage 5 offline regression: 25/25 passed.
- Stage 4 offline regression: 43/43 passed.
- Responses remain unverified and are not persisted.
- Production worker and Git sync remain independent.
- Provider-request provenance not independently established.

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

## Updating Odin from GitHub

After the reviewed changes merge into `main` and CI passes, open the
existing `~/odin-workspace` checkout on Odin and check its status with
`git status --short --branch`. If it is on `main` with no local changes
or local-only commits, run `git pull --ff-only origin main` and confirm
`git rev-parse --short HEAD` matches the intended release. If the checkout
is dirty or has diverged, review the differences before updating.

Keep configuration, credentials, and runtime data on the device. Restart
the Stage 5 server if it was already running, then open its localhost
page and use the menu to reach AI Chat, Tasks, System, and Session.
Verify that System reports backend readiness and Tasks shows queue counts.

## 2026-11-19 — Safe autonomous source updates and device tasks

The existing Odin Git-sync service can now **optionally** keep the local
source checkout current with the latest CI-passing GitHub `main` revision.
It requires explicit one-time activation in Termux; it never resets files,
installs packages or restarts agents automatically. It keeps private data,
existing conversations and the five untracked files intact. The exact
reviewed CI SHA must match the fast-forward target. See
[`docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md`](docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md)
for activation, status, rollback boundaries and the next five priorities.

The existing private iPhone relay now supports multiple independent messages,
reports per-poll failures in a private status file, and accepts fixed read-only
`/status`, `/task git-status`, and `/task queue-status` requests. These
are bounded verifiable tasks, not arbitrary shell or unreviewed code execution.
The mobile interface offers shortcuts that fill the composer; the user still
presses Send. Cloud AI messages are separate from this ChatGPT conversation.

**Verification distinction:** GitHub green CI and a Vercel READY deployment do
not prove that Odin has installed/restarted the new revision or that a fresh
private iPhone message received a live reply. Those are separate acceptance
gates documented in the roadmap.
