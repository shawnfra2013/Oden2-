# ChatGPT / Claude -> GitHub -> Odin workflow

Current device transport and November 20 verification are documented in [the private GitHub mailbox runbook](ODIN_GITHUB_BRIDGE.md). Use that mailbox for device checks.


For the November 20 on-device OpenAI result and fixed private mailbox inference diagnostic, see [the private probe runbook](ODIN_GITHUB_BRIDGE.md#private-inference-probe). The physical mailbox inference check passed on November 20.

## Purpose
Use GitHub as the canonical source tree. ChatGPT or Claude may propose changes, run checks where their tools allow, and write to GitHub only through an explicitly authorized integration. Odin 2 (Android 10/Termux) pulls accepted changes into its existing checkout. This is a source-code delivery workflow, **not** a live remote terminal or an always-on AI agent.

## Verified access at setup (2026-11-18, America/Chicago)
- The ChatGPT GitHub connection reported write/push rights to `shawnfra2013/Oden2-`.
- Main was `19a48e22869b2f5adbdc93932c8f6b14107f1cec` at inspection; later revisions must be checked live.
- Remote Desktop Commander listed **no connected device**. No claim of Odin remote execution is made.
- Existing GitHub Actions workflow: `.github/workflows/odin-checks.yml`.
- This document records a communication and delivery method; it does not establish Claude GitHub access or permission.

## Safe cycle
1. Read latest `main`, open pull requests, CI and relevant files before editing. Never assume an older chat snapshot is current.
2. Define a narrow change; use a separate branch/PR for code changes. Avoid force-push or overwriting unexpected work.
3. Test locally when possible and require passing GitHub Actions; record commit SHA and what was actually tested.
4. Merge reviewed work into `main`. Do not tell Odin to pull code still only on a feature branch.
5. On Odin, run `git status --short --branch` in `~/odin-workspace`. **Do not discard local edits**, untracked files, keys, or runtime state.
6. If clean on `main` and remote is correct, use `bash scripts/odin-safe-pull.sh` (or review then run `git pull --ff-only origin main`). Stop on conflicts/divergence.
7. Verify `git rev-parse HEAD` against the intended commit, run applicable tests, and restart services only when separately approved.
8. Keep a durable record of GitHub SHA, CI link, Odin verification results, and any unresolved limitations.

## How to collaborate with Claude
Connect Claude to the same repository using its supported GitHub workflow, if available. Give it the repository URL, this document, `README.md`, `docs/PROJECT_MEMORY.md` and the current PR/commit. Ask Claude to use a separate branch, test and open a PR. Never give either assistant long-lived tokens in the chat, repository, or scripts.

## Optional live-device bridge (future, NOT installed)
Remote Desktop Commander could expose an approved device terminal when its agent is installed and connected. Until it reports an online Odin device, do not claim that ChatGPT can run commands there. A separate command bridge would need per-device authentication, least-privilege commands, approvals for writes, auditable receipts, timeouts, replay protection, and no publicly exposed Termux HTTP shell. A GitHub webhook alone cannot grant secure interactive terminal access.

## Security and operation
- Never commit credentials, runtime databases, task queues, tokens or SSH private keys.
- Keep local Stage 4 supervised worker and Git sync functioning independently; do not silently restart them.
- Do not add unattended boot or launcher automation unless requested.
- Treat conversational AI output as unverified absent deterministic acceptance checks.
- Do not bypass review when source changes have not been tested.
