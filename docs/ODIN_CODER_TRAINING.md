# Odin coding critic and supervised adapter training

**Goal:** Make the complete Odin coder improve through evidence-backed iterations, without treating model-generated code, AI self-grades, or loss reduction as proof of correctness.

## What already exists

- `ai/agent/proposal_builder.py` creates confined, immutable source proposals, runs Python syntax and Ruff, then records an invocation receipt without modifying project source. Its maximum two model repair requests do **not** prove functional correctness.
- `scripts/odin_task_contract.py` checks task scope and claimed test results. These claims must be independently verified against the exact GitHub PR SHA.
- `scripts/odin_practice.py` stores finite local exercises. Previously disclosed practice questions are training aids, **not a valid unseen holdout benchmark**.
- `scripts/train_adapter.py` can train a separate **candidate Qwen2 LoRA adapter** from reviewed Q/A examples, using locally available `torch`, `transformers` and `peft`. It requires a separate compatible local `safetensors` checkpoint, not the currently served model name alone. The handheld's compatibility, RAM, optimizer and energy budgets have **not been verified**, and a loss-only result cannot establish better coding ability.

## New supervised static coding critique

`scripts/odin_coder_coach.py` consumes a **receipt-verified proposal** through `ai.agent.pipeline.receipt`. It checks the new source against the actual unchanged baseline without running it. It identifies:

- No semantic change (reworded comments or formatting rather than a code fix)
- Removed public functions/classes or changed public function signatures
- Newly introduced API calls requiring a security review (`eval`, dynamic execution, process/network/file manipulation)
- Malformed Python syntax

It publishes one non-overwriting `critique.json` within the existing private, ignored `state/proposals/invocations/<task>/<invocation>/` directory. Its contents are **metadata and fixed guidance only** (IDs, SHA256 hashes and category codes, not source, secrets or full model responses). It does not grant write authority, run a model, execute generated Python, call any provider, or update active model weights.

Example, from the repository root after a legitimate isolated proposal exists:

```bash
python -B -m scripts.odin_coder_coach \
  --target ai/agent/example.py \
  --task 'Approved task text exactly as submitted' \
  --task-id 012345abcdef \
  --invocation-id 11111111111111111111111111111111
```

The example invocation ID is illustrative. Use the **real** value returned by the proposal builder. A nonzero exit code means the critique needs revision or a safety gate failed; it does not permit an unattended rewrite.

## Advisory feedback on the next coding attempt

When a proposal fails static critique, the reviewer also saves **only fixed category codes and fixed guidance strings** to a separate, ignored `state/coder-coach/lessons/` cache keyed to the exact target module. On the next authorized proposal for that module, the builder reads the small checked record and adds it to the **existing** model request as quoted, non-authoritative context. No new cloud call is initiated. The record contains no candidate source, earlier user task text, secrets or shell commands. Unknown or tampered guidance is rejected, not executed.

The full immutable `critique.json` stays in the old proposal invocation for audit. This lightweight feedback memory is **not** weight training, does not claim a better functional coding score, and never expands the worker's file permissions. A proposal may still fail independent Ruff, unit tests, code review, or physical acceptance.

## Progressive improvement cycle

1. Use a new in-scope coding task and the exact approved base SHA. Save the first raw attempt separately, its source hash, task ID and model identifier. Never edit or overwrite prior receipts.
2. Run static critique and actual source tests in an isolated environment. Compare with the earlier known-failure category; use an explicit approved repair instruction rather than blindly retrying.
3. Limit revisions to **two**. The judge reports `candidate_needs_verified_tests` even if static checks pass. Require separately authenticated functional tests, exact-head GitHub CI and a code review before merging. Missing evidence is BLOCKED.
4. For training, create a **separate, human-approved and privacy-reviewed** question/answer dataset with accepted corrected source. Keep model-generated unverified examples, live secrets, chat history and unreviewed proposals out. The training script requires `approved:true` for each example. Keep unseen holdout problems distinct from training examples and prior disclosed practice prompts.
5. Train a **new candidate** adapter only after verifying model type, disk/RAM limits, offline training dependencies and local compute budget. Never write into the currently running model's directory. Save baseline and candidate evaluation on heldout examples plus real functional coding-task test results.
6. Promote the adapter only after an explicit review finds better or equal **heldout functional pass rate**, no security regression, acceptable latency/memory and reproducible checks on a heldout set. The current `train_adapter.py` records heldout answer loss but **does not run a full functional coding benchmark**, so adapter promotion is **BLOCKED** until that benchmark exists and passes.
7. Preserve the previous adapter as a rollback target; deployment/restart on the physical Odin remains operator-approved and separate from a reviewed source PR.

**Training is not ordinary Git memory retrieval:** retrieval improves context without modifying weights; adapter training changes candidate weights but is not automatically better. The observed local model server is an OpenAI-compatible loopback endpoint and does not, by itself, prove compatible Qwen2 base weights or an available training accelerator.

## Acceptance matrix

| Gate | Evidence required | Meaning |
| --- | --- | --- |
| Static critique | Candidate hash, baseline hash, category codes | SOURCE REVIEW ONLY |
| Code correctness | Actual independently run tests with commit SHA | TASK-LEVEL PASS/FAIL |
| Review feedback consumed | Matched feedback-tool read receipt, separate from storage | READ VERIFIED |
| Training data approved | Reviewed example provenance and heldout separation | DATASET REVIEW |
| Candidate trained | Candidate adapter files plus finite loss report | TRAINED CANDIDATE, NOT BETTER |
| Better coder | Unseen functional coding benchmark, security/latency regression and independent evaluation | PROMOTION ELIGIBLE |
| Odin installed | Explicit operator update and real device acceptance | DEVICE VERIFIED |

Track open corrections under [#98 task quality](https://github.com/shawnfra2013/Oden2-/issues/98), [#100 failure triage](https://github.com/shawnfra2013/Oden2-/issues/100), and [#99 supervised collaboration](https://github.com/shawnfra2013/Oden2-/issues/99). Keep raw private data off public Git.
