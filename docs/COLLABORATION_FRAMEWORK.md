# Odin supervised collaboration and proof contract

**Status:** Source-level framework; NOT a claim that Odin can yet independently operate in Codespaces or that this version is installed on the handheld.

**Startup and tool routing:** Read [Working with Odin](WORK_WITH_ODIN.md). Prefer the connected GitHub source API and fixed CI workflows for non-device tasks; use the existing authenticated private mailbox for allowlisted physical queries; delegate to an explicitly attached, authorized Codespaces/local coding agent only when one is actually available. No tool connection itself proves agent code execution, and a scheduled event check is not a continuous chat terminal.

## Responsibilities

- **GitHub:** issues, PRs, source CI, read-only diagnostics, security scan, immutable receipts and exact-SHA evidence. Actions can detect a failure but do not reason or repair by themselves.
- **Odin coding agent:** under an approved task and session, inspect, branch, propose scoped changes, test, and publish a receipt. No self-started Codespaces, paid models, arbitrary shell, permissions escalation, secret exposure, merge or device deployment.
- **ChatGPT reviewer:** on demand, an enabled hourly check, or a separately configured supported **GitHub PR event-triggered Work task**, review evidence with exact issue, PR, current head SHA and prior receipt ID. A real PR-open event did trigger a Work review on #119, but that did not wake this existing chat; its original delivered payload omitted event-time SHA. The event evidence workflow records the GitHub payload SHA in a separate artifact. Do not claim agent read/action from feedback storage.
- **Operator:** approves task scope, paid/cloud spending settings, security-sensitive work, source merges as gated, physical installation and real phone testing. Routine safe source tests and in-scope revisions need no repeated approval.

## First coding module — exclusive source-task leases (issue #97)

The portable, offline-safe `scripts/odin_task_lease.py` module is a **local source coordination primitive**, not a running coding agent. It serializes claims through SQLite `BEGIN IMMEDIATE` under `state/task-leases/`. It records a permanent unique lease ID, owner, Git branch, issue, expected base SHA, exact allowed paths and a bounded UTC expiry (60–3600 seconds). Claims for the same issue, same branch, or overlapping file paths are rejected. Expired and released records remain for audit; stale base-SHA claims fail before creating state.

The caller must independently authenticate the observed GitHub SHA, approved task scope, and identity. A lease does not itself grant shell or network privileges, prove the requester is authorized, or automatically create a PR. No Codespace or Android service is started. This is source-only groundwork toward a supervised coding agent. Run the offline test suite for concurrency, replay, expiry, owner mismatch and path traversal cases. To inspect local counts without changing any lease, use `python -B scripts/odin_task_lease.py status`. Real cross-machine lease enforcement still requires an authorized shared coordinator with conditional writes, which is not introduced here.

## Build → review → revise → verify

1. **Assign:** name one GitHub issue, expected base SHA, owner, allowed paths, required tests, acceptance criteria and maximum two review-driven revision rounds. The structured validator is scripts/odin_task_contract.py. It validates submitted facts, not their independent authenticity.
2. **Build:** an authorized agent creates a small branch/PR, records issue, PR, exact head SHA, changed files, tests and timestamp. GitHub runs source CI for the exact SHA.
3. **Inspect:** reviewer checks current PR head, evidence, failed steps and scope. Decision is hold, revise or review_ready. Missing, stale or contradictory evidence yields FAIL or UNVERIFIED, never implicit success.
4. **Feedback:** authorized private feedback can be sent through the private manual GitHub workflow. The receiver stores the bounded note and sends a matching receipt with recorded=true. That does NOT prove the coding agent read, understood, or applied it.
5. **Improve:** if still within approved scope and budget, agent proposes a targeted revision, new SHA and fresh CI results; new ideas outside scope become a separate proposed GitHub issue. The independent stage validator scripts/odin_feedback_progress.py enforces order submitted → device_received → agent_tool_read → action_proposed → code_changed → source_verified. Its checks do not authenticate external evidence.
6. **Stop:** two review-driven revision rounds maximum; block on wrong task/SHA/receipt, scope drift, no progress, unavailable tests, exhausted budget or missing approvals. Do not loop or silently expand the task.
7. **Release:** reviewed source merges and manual exact-main-SHA checks precede any physical installation. Device and iPhone testing are separate, explicit approval gates.

## Feedback tool observation stage

The local review-feedback CLI supports an explicit `--inspect ID` action, separate from the no-side-effect `--list` query. A successful inspection saves a metadata-only receipt for asynchronous private GitHub outbox delivery. It records exactly `local_feedback_tool_presented`, not an authenticated AI identity, a source update, or model comprehension. In the proof sequence, this event is only evidence that a local tool presented the note; it must **not** automatically be promoted to `agent_tool_read` or `action_proposed`. Actual agent identity, an independently observable tool read and a new scoped PR require later independent proof.

## Source-only progress timeline and benchmark dashboard

`python -B -m scripts.odin_progress_dashboard --metadata /private/approved-metadata.json --format markdown` renders a bounded task-stage timeline and held-out benchmark counts using the existing feedback-stage validator and benchmark comparator. Input must be an operator-approved local metadata record; do not upload private receipts or chat to public Git. Every displayed stage is explicitly **claimed**, not independently authenticated: a green CI check, stored note or self-reported grade never establishes Odin agent action, physical installation or improved weights. This is a source-level presentation adapter, not a live phone view, persistent subscription, remote shell or automatic model promotion.

## Timing, availability and cost

GitHub checks respond on pushes without a running Codespace. Odin's private mailbox checks approximately once per minute ONLY if the device service is running. The regular ChatGPT receipt watch checks hourly; a separate configured **Work PR event task** has demonstrated an actual PR-open run but is not a general push-to-chat webhook. [ODIN-HOUR event evidence](ODIN_HOUR_EVENT_EVIDENCE.md) captures immutable PR-event head SHA using GitHub Actions and recommends 4–8 meaningful reviewer activations per hour, not the maximum 30. No unattended model-to-model loop is yet verified.

Prefer no Codespace for GitHub-only work. For authorized coding sessions use a manually started two-core workspace when needed, a target idle timeout of 15 minutes, at most one workspace and up to 60 minutes per session. A 30 two-core-hour monthly planning target is NOT a billing cap; verify GitHub account limits directly before consuming resources. Never silently enable paid APIs.

## Proof and quality gates

For each task keep the approved scope, request ID, issue, PR, head SHA, timestamp, exact test run and outcome, reviewer decision, revision round, and an evidence link. Keep private messages, SSH keys, tokens and personal data out of public GitHub.

The private receiver and manual submission workflow (PR #95) have now demonstrated a **real private review note stored and acknowledged by Odin** (November 23, 2026). The device receipt explicitly reported `action_executed=false`. The separate local-agent tool read, authorized code correction and subsequent independently reviewed agent-generated PR have **not** occurred in this test. Pure offline tests validate contracts but cannot establish those physical steps. See the [current handoff](HANDOFF.md) for the actual test results.

Check source with: python -B -m unittest discover -s tests -p 'test*.py' -v; python -B scripts/odin_preflight.py --mode source. Passing GitHub checks never proves live handheld or iPhone acceptance.
