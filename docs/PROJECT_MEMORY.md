# Odin project memory — source-backed index

**Source of truth:** GitHub repository `shawnfra2013/Oden2-`, with exact revision, task/PR and evidence links. This document is an entry point for **human or agent retrieval**; its presence in Git does **not** mean the local Odin model automatically ingests or remembers it.

## Read this first for an Odin work session

1. [Latest verified collaboration checkpoint — 2026-11-23](audits/ODIN_VERIFIED_MEMORY_2026-11-23.md): what passed, what failed, unresolved conditions, exact source/receipt references, and safe next steps.
2. [Current handoff](HANDOFF.md): approved resume plan and physical-device blockers.
3. [Single prioritized task board](TASK_BOARD.md): task owners, acceptance and dependencies; do not create a competing backlog here.
4. [Dated incident and trial log](audits/ODIN_COLLABORATION_TRIAL_2026-11-23.md): test history, failures, remedies and proof limitations.
5. [Current runtime](ODIN_RUNTIME.md): supported environment and boundary between GitHub source, physical Odin and phone.

## What is and is not retained

**Retained in Git:** reviewed code commits; sanitized decisions, change history, issue comments, test/result links, dated memory checkpoints. Git stores versions for retrieval, not autonomous semantic learning.

**Retained privately:** the physical device's ignored `state/` files, local queue/model records, audit snapshots, and authenticated private mailbox receipts. They are **not** part of the public Git commit history and do not constitute a Git backup.

**New source implementation (device unverified):** `scripts/odin_project_memory.py` builds a local, ignored SQLite FTS5 index using only the allowlisted current Git documents (including the optional canonical connection handoff after PR #139 is merged). The orchestrator now automatically adds at most two bounded, read-only matching excerpts to a **new** question as untrusted background data; this makes no additional model call. It does not retrieve private mail, run commands from documents, train the underlying model, or independently verify the current device state. The physical Termux FTS5 build and actual offline recall must still be tested after an approved source update.

Try locally (from an approved checkout):

```bash
python -B scripts/odin_project_memory.py --rebuild
python -B scripts/odin_project_memory.py --query 'delayed mailbox receipt'
```

The index is confined to ignored `state/project-memory/index.sqlite3`; it can be rebuilt if the Git documents or checkout SHA change. The source repair in [PR #140](https://github.com/shawnfra2013/Oden2-/pull/140) additionally compares the cached snippet rows with the approved documents, checks SQLite integrity, and rejects symlinked cache directories before reading. It rebuilds only the generated index on a mismatch. These are **proposed, source-tested changes**, not evidence of a physical Odin rollout; inspect PR head SHA and exact-head CI before claiming them accepted. Results carry a local source SHA and `verified_externally=false`. The next separate test is a real model recall of a prior defect, current approved task and outstanding blocker, with source references. This is retrieval, not model retraining.

## Coding improvement is separate from memory retrieval

Odin now has a source-only supervised coding critique module, described in [coding and adapter training gates](ODIN_CODER_TRAINING.md). It reviews immutable isolated proposals and saves bounded, metadata-only static feedback for a human or authorized reviewer. Existing `scripts/train_adapter.py` can build a **candidate** Qwen2 LoRA adapter from explicitly approved examples, but neither this critique nor the Git memory index updates live model weights. The current handheld's model-training compatibility and measured unseen coding accuracy remain **UNVERIFIED**. Do not call repeated critique rounds 'self-training' until an approved dataset, separate candidate checkpoint, heldout functional coding benchmark and controlled device activation are evidenced.

**Connection continuity integration (PR #140):** The allowlist now includes `docs/ODIN_CONNECTION_MEMORY.md` when present. It is introduced in [PR #139](https://github.com/shawnfra2013/Oden2-/pull/139), and is absent from `main` until merged. The retrieval system treats its content as untrusted **background data**; the startup obligation to read it comes from the canonical agent/workflow documents, not from following instructions found inside retrieved text. No device installation is implied.

## Memory update rules

- Add new facts once, in a dated checkpoint or the existing canonical issue/PR; link rather than duplicating whole conversation transcripts.
- Every claim should include its provenance: UTC observation time, request/receipt ID, Git SHA, CI link, issue/PR, and PASS/FAIL/BLOCKED/UNVERIFIED status.
- Keep **code merged**, **device installed**, **message stored**, **agent read**, **agent acted**, and **source verified** as different states.
- Never commit raw private messages, credentials, personal chat, device paths with secrets, or unrestricted device logs.
- Do not erase historical failures after fixing them. Record the fix, tests, and remaining physical verification separately.

## Historical project memory

Earlier dated milestones and raw historical state records remain intact in the [historical project memory archive](archive/PROJECT_MEMORY_before_2026-11-22.md). Historical files are **not** current setup instructions or proof of today's running device.
