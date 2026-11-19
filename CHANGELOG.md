

<!-- odin-stage4-20261017 -->
## Stage 4 stabilization — October 17, 2026

Task-bound proposal provenance, confined atomic writes, collision-safe evidence, and structured command results. See [Stage 4 verification](docs/stage4-stabilization.md).
Verification: `python -B -m unittest discover -s tests -p test_stage4.py -v`.


<!-- ODIN_STAGE4_CHECKPOINT_2026-11-10 -->
## 2026-11-10 — Stage 4 verification checkpoint

- PASSED: 32/32 isolated Stage 4 tests.
- PASSED: Ruff validation.
- PASSED: Groq 120B live curl inference, HTTP 200.
- PASSED: GitHub remote-read main matches local 0c8d378.
- PENDING: live background-worker task receipt.
- PENDING: historical task-failure classification.
- PENDING: reviewed commit, push and GitHub Actions verification.
- Documented previous assistant discrepancies without assigning unproven causes.

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
## 2026-11-11 — Stage 4 stabilization verification

- Published stabilization commit 6d3423d to GitHub main.
- GitHub Actions Odin Checks run 43112942632 passed.
- Passed 38/38 Stage 4 regression tests, Ruff, and compilation checks.
- Verified live Groq inference and a harmless background-worker task.
- Hardened inference credential handling and interrupted-task recovery.
- Classified 23 historical JSON task records, including 8 failed tasks.
- Confirmed worker.lock is part of the worker locking implementation.
- Preserved previous verification checkpoints for historical traceability.
- Remaining: independently verify unattended reboot startup and AI provider-request provenance.

<!-- ODIN_STAGE4_PROVENANCE_2026_11_14 -->
## 2026-11-14 — Stage 4 inference provenance (isolated, unpublished)

- Added ai/agent/inference_receipt.py for task-scoped provider-response metadata.
- Integrated receipt capture, checkpoint persistence and interactive resume.
- Added five provenance and startup-order regression tests.
- Expanded CI discovery from test_stage4.py to test*.py.
- Verified 43/43 offline tests, Ruff and compilation.
- No live worker deployment, service restart, queue change or GitHub publication.
- Provider-request authenticity remains independently unverified.

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

## 2026-11-14 — Stage 5.5 browser integration

- Added modular Stage 5 browser frontend and localhost backend.
- Added bounded Groq inference adapter and request safeguards.
- Verified browser-to-AI response using a harmless marker.
- Passed 68 combined Stage 4 and Stage 5 regression tests.
- Preserved existing production services and task records.

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

## Unreleased

- Add browser menu links to existing Odin sections and document the
  fast-forward update and browser verification steps.

## 2026-11-19 — CI-gated updater and reliable device inbox

- Added a private opt-in CI-gated updater within existing Git-sync, pinned to
  the exact successful `main` workflow revision. Existing safe-pull checks
  protect the checkout, preserved untracked files and secrets.
- Changed Git-sync to avoid recurring false failures from harmless untracked
  files when local main is already current.
- Added exclusive relay polling, per-message failure isolation, bounded
  multi-message processing and locally persisted operational status.
- Added verified read-only `/status`, `/task git-status` and
  `/task queue-status` responses, plus explicit unknown-task rejection.
- Added iPhone task shortcuts and delayed-message status labels.
- Added offline regression tests and a focused 10-upgrade checklist and
  five-step follow-on roadmap in `docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md`.
- No automatic service restart, arbitrary shell, new daemon, boot persistence,
  or ChatGPT thread integration was introduced.
- The physical Odin will remain on its previous revision until a safe initial
  fast-forward is performed and the updater is enabled on-device.

## 2026-11-19 — Optional password unlock for Odin Control

- Added an owner-controlled local encrypted vault for the existing iPhone
  access token. New unlock password is used locally; the server still
  authenticates the original bearer token.
- Password is not sent to the server, stored in the app, or committed to
  GitHub. Token is encrypted with PBKDF2/AES-GCM before opting into
  browser storage. Existing no-save login remains available.
- Added unlock, forget saved access, and lock session UI. It protects
  against accidental exposure of plaintext saved credentials, but not
  against malicious code running in the browser.
- Added offline encryption, password rejection, tamper and browser-wiring
  tests. Does not change the physical Odin's device token, background
  services, or AI-provider configuration.

## 2026-11-19 — Crash-safe kernel Git-sync locking

- Replaced the existing Git-sync's abandoned-directory locking mechanism
  with an OS-managed, nonblocking Python `fcntl.flock`. It automatically
  releases after process termination and reuses the existing supervisor.
- Added offline coverage for overlapping sync attempts, crash recovery,
  unsafe symlink, original legacy-directory preservation and nonzero exit.
- No user data, service definitions, stored credentials, auto-update flag,
  source Git history or ignored untracked files are modified.
- Installing the updated source and independently observing a later
  scheduled sync on physical Odin are separate live acceptance checks.

## 2026-11-19 — Odin AI readiness and friendly task commands

- Recognize an exact allowlist of friendly read-only commands including
  "Task git-status" without routing them to model inference.
- Add /ai-status (no network or credential disclosure) and explicit
  /ai-test (actual bounded provider call).
- Preserve the separate local Odin conversation and hosted cloud API
  boundaries. AI responses remain unverified model text, not evidence
  of actions or shell execution.
- Add device-only AI environment readiness and a fixed failure-code
  protocol for private messages, validated by Vercel and shown in the
  existing iPhone interface. No secret contents appear in replies.
- Add Python and Node regression tests; a live reply from an AI model,
  unlike the already proven Git task, still requires separate verification.

## 2026-11-19 — On-demand verified private Odin service restart

- Added confirmation-gated System Restart all services button and
  exact typed /restart-services command using the same authenticated relay.
- Added detached, fixed-allowlist helper to restart existing
  Odin runit services, the private relay last; no device reboot,
  arbitrary shell, new package, or OS changes.
- Durable private result after services are checked as running.
  Interrupted operations fail explicitly; duplicate requests and
  rapid restart loops are blocked by local state and cooldown.
- Added offline tests for permission boundaries, message routing,
  idempotency, throttle, service order, failures and reconnect.
- Existing keys, private messages, Git history, user files and
  CI-gated source update policy are preserved. A one-time relay
  reload is required for the initial version activation.

## 2026-11-19 — Expanded device diagnostics

- Added the combined read-only Odin health receipt and its iPhone dashboard
  action. It distinguishes service supervision, updater state, and Stage 5
  HTTP reachability.
- Added private confirmation and result delivery for restarting a single
  managed Odin service. Existing all-service commands remain available.
- The updater's GitHub Actions query is pinned to the target SHA and bounded
  to prevent a long workflow history from blocking a release pull.

## Unreleased — Automatic rollout evidence

- Odin keeps the last automatic pull and reload outcome across no-op syncs.
- Odin health reports the saved revision, timestamp, and reload result.

- Odin health now reports worker heartbeat and private relay poll age,
  alongside pending and running task counts.
