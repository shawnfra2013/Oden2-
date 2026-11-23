# ODIN-HOUR immutable GitHub event evidence

**Purpose:** Preserve the **original GitHub pull request event's head SHA** without pretending that ChatGPT Work receives that SHA automatically. This solves the source-evidence gap discovered in the first [PR #119](https://github.com/shawnfra2013/Oden2-/pull/119) event-trigger test. GitHub Work notifications and GitHub Actions are separate systems.

## Workflow

The `.github/workflows/odin-hour-event-evidence.yml` job runs only for a same-repository pull request whose **title starts with `[ODIN-HOUR]`**, and for supported events `opened`, `synchronize`, `reopened`, `ready_for_review` and `review_requested`. It reads the exact original GitHub event payload, captures `pull_request.head.sha`, `pull_request.base.sha`, PR number, event action and Actions run ID, and uploads one immutable, sanitized 14-day Actions artifact. It does not copy the event body or comments, read private GitHub mail, contact the device, or post a review. The script runs from the **trusted current `main` checkout**, not unreviewed PR head code. This matters for long-lived draft PRs whose event `base.sha` predates the introduction of the script; the immutable PR event head and base SHAs are read from the original event payload, never inferred from the current checkout. The job has only `contents: read` permissions and a 3-minute deadline.

The artifact provides an independent reference for **the event SHA captured by GitHub Actions**, but not proof of the exact payload delivered to a separate ChatGPT Work task. A Work reviewer must still fetch the current PR head immediately before commenting and decline or rescope when the head changed. A Work review's marker is unique per `PR number + head SHA`, and reviewer-authored comments must never trigger another write to themselves.

## First live failure and reviewed correction

The first post-merge `synchronize` event on draft PR #119 (head `b15f9cfad3269a8016f94e13a88fec559b06a0b5`) reached the new GitHub Actions job, but [run 45147217823](https://github.com/shawnfra2013/Oden2-/actions/runs/45147217823) **failed**: the event's old `base.sha` checkout did not yet contain `scripts/odin_hour_event_receipt.py`. The correct response was FAIL, not a claimed event-evidence PASS. The reviewed fix checks out the trusted current `main` branch; a regression now prevents reintroducing the old base-ref checkout. A new event is required to prove the workflow actually creates the artifact.

## Evidence and progressive acceptance

1. Create a single harmless `[ODIN-HOUR]` pull request on a reviewed branch. Wait for an `ODIN-HOUR immutable PR event evidence` Actions run with the matching PR number, event action and original 40-character head SHA.
2. Check normal repository source CI separately (Odin Checks, browser acceptance and CodeQL) **against the reviewed head**. The event-capture job does not replace any of them.
3. Confirm that a real GitHub event produced a matching ChatGPT Work run and at most one technical review for the commit, if supported by the connected Work event trigger.
4. Send only relevant, approved review feedback through the existing private Odin mailbox. A stored acknowledgment is **not** a coding-agent tool read or source change. Verify each stage independently.
5. Escalate failures and stale head movements to [issue #99](https://github.com/shawnfra2013/Oden2-/issues/99), with the Actions run URL and actual PR SHA. Do not silently retry indefinitely.

## Event budget

The 30 Work event runs per hour figure is an upper bound, **not a throughput target**. Plan approximately **4–8 meaningful Work reviews** in a one-hour session: on new in-scope PR work, actual CI failure, actionable human review, or end-of-hour conclusion. Repeated comments/pings on the same commit are deduplicated. Source lint, unit tests, replay checks, and queue health should use local Odin or GitHub Actions without unnecessary Work activations.

An Actions artifact is not an automatically updating Git memory file. Meaningful sanitized conclusions should be linked into the dated project memory and issue #99 through reviewed documentation or issue comments. Private raw receipts and model chats stay out of public artifacts.

**Deployment scope:** This workflow is entirely GitHub-side. It does not require a physical Odin update, enable unlimited remote commands, or call a model. No evidence of an installed local coding agent is inferred from its success.
