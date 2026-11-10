# Stage 4 stabilization

The worker and builder now bind each proposal to a task ID, worker-issued invocation ID,
target and task text, baseline source hash, and candidate-byte hash. Proposals live at
`state/proposals/invocations/<task-id-or-interactive>/<invocation-id>/`.
Each invocation owns `candidate.py` and `metadata.json`. Older shared proposal files
remain historical evidence. The worker independently validates the actual bytes and
metadata, parses Python, runs Ruff, and checks the baseline again after lint.

The filesystem helper opens directories without following symlinks and publishes
new evidence atomically without overwriting existing destinations. A colliding job
is quarantined with its source record for manual review. Interrupted work is preserved
without automatic replay. Expected schema, syntax and process errors become task-level
failure records; subsequent valid tasks can continue.

Command results carry typed return codes, command arguments, task IDs and sequence
numbers in their checkpoint. Command output is never interpreted as a process exit
status. General model conversations remain `unverified`, including successful command
execution: arbitrary natural-language requests do not yet have deterministic acceptance
contracts. Exact supported Git-status requests can complete with direct process evidence;
validated proposals can reach `proposal_ready`. Neither state applies generated code.

## Verification

```bash
python -B -m unittest discover -s tests -p test_stage4.py -v
```

The 29 regression cases use temporary roots and simulated model/process responses.
They exercise proposal binding and tampering, timestamp independence, safe publication,
symlink rejection, evidence collisions, timeout/recovery and queue continuation,
structured execution results, model schema errors, health status, and controller imports.
No live model requests occur in this suite.

The guarded installer additionally runs actual Ruff against each candidate using the
project configuration, checks installed identities, repeats the regression suite and lint
after replacement, restarts the worker under its existing service, runs one real Git-status
queue probe, checks stable service identity, and verifies that previous done records/logs
retain their hashes. It records a private manifest with exact before/after hashes and a
restore proof. If a post-change gate fails it attempts verified rollback and restores the
worker service state. Rollback failure is an error requiring inspection, never success.

Use the installer with `--rollback <printed-backup-directory>` to restore that revision
while the queue is empty. Rollback refuses later source changes. Preserve the installer
and the printed private backup path.

GitHub's workflow includes this suite, but hosted CI does not run until these changes
are committed and pushed. The existing Git-sync script deliberately refuses dirty trees
and does not automatically commit these changes. Publication remains a subsequent step.

Actual cloud inference, Android sleep/reboot persistence, full security isolation, and
generic autonomous-task acceptance are outside these verification claims.


<!-- ODIN_STAGE4_CHECKPOINT_2026-11-10 -->
## November 10 verification

Verified:
- 32/32 tests passed in disposable copy.
- Ruff passed.
- Groq 120B inference passed via curl.
- GitHub main remote-read matched local HEAD 0c8d378.

Unverified:
- New task completed by the currently running worker.
- Root causes of eight historical failed records.
- Push permission and success from Termux.
- GitHub Actions on the unpublished Stage 4 implementation.

Next: validate the live worker, review the existing CI changes, then publish approved work.

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
