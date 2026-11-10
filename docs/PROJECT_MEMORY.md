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
