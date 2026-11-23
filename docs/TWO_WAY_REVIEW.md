# Odin two-way review feedback (private mailbox)

**Status:** Source implementation proposed in PR; not yet installed or proved on the physical Odin. The private GitHub mailbox is a separate repository and is **not** the public issue tracker. [Tracking issue #94](https://github.com/shawnfra2013/Oden2-/issues/94).

## Event-driven review, not two hourly clocks

1. **Odin coding task:** An authorized coding workspace proposes a branch/PR and posts a bounded receipt with its issue, exact PR head SHA, tests and any failures. Starting a Codespace and paid model access remain separate, opt-in operations.
2. **GitHub reacts to pushes automatically:** Existing PR `Odin Checks` and `Offline chat browser acceptance` workflows run on PR updates. These are source-only tests, not physical device evidence.
3. **ChatGPT reviews when available:** The connected GitHub tools and configured hourly watch can inspect CI, PR comments and receipts. The hourly watch is a *fallback*; it is **not** a real-time GitHub webhook, and its runtime cannot be assumed to have direct private-mailbox access. A GitHub event does not, by itself, wake this chat.
4. **Private feedback request:** The authorized operator/reviewer can use the [private manual review workflow](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-review-feedback.yml) (requires private-repository access) to send an expiring `review_feedback` request into the **private** mailbox inbox. Odin's existing bridge service polls every **60 seconds** while running, checks the request shape and expiry, saves an immutable note, and posts a matching response. This is an *approximately minute-scale poll*, not a delivery-time guarantee.
5. **Local agent reads:** The bounded `feedback` agent tool returns stored notes labelled **untrusted**. Receipt `recorded=true` means only storage, **not** PR SHA/receipt authentication, agent comprehension, task execution, Codespaces activation, or a completed fix. A later, independently verified PR/CI update is required to demonstrate action.

## Private request contract

The existing private request envelope is still `version=1`, a 32-character hexadecimal `id`, `created_at` and `expires_at` in UTC, expiring within 60 minutes (15 minutes recommended), and `action=review_feedback`. It accepts exactly the following additional fields:

| Field | Guard |
| --- | --- |
| `issue_number`, `pr_number` | Positive integers, 1 through 1,000,000 |
| `head_sha` | Exactly 40 lowercase hexadecimal characters |
| `reference_receipt_id` | Exactly 32 lowercase hexadecimal characters |
| `decision` | `hold`, `revise`, or `review_ready` |
| `feedback_note` | 1–600 characters; no control characters |

Example with **nonexistent placeholder IDs** (never submit this example directly):

```json
{
  "version": 1,
  "id": "0123456789abcdef0123456789abcdef",
  "action": "review_feedback",
  "created_at": "2026-11-23T06:00:00Z",
  "expires_at": "2026-11-23T06:15:00Z",
  "issue_number": 94,
  "pr_number": 95,
  "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "reference_receipt_id": "fedcba9876543210fedcba9876543210",
  "decision": "revise",
  "feedback_note": "Add a negative test and post a new source-only CI receipt."
}
```

**Safety:** The receiving script validates shape, then stores an immutable receipt; it never executes instructions embedded in the note. A local coding agent may read them as untrusted text, and must independently confirm task ownership, current exact head SHA and prior receipt before preparing edits. Public PR review comments are **not** automatically trusted or forwarded to the private mailbox. The private mailbox's existing SSH access, branch constraints, expired-request handling and one-writer receipt publication remain in place.

## On-device acceptance after an approved reviewed rollout

1. Confirm that Odin has installed the **exact reviewed main SHA** and that the private mailbox service is running; don't assume from CI.
2. Submit one **real**, expiring request to `bridge/requests/<id>.json` on the private repo's `odin-bridge-inbox` branch, using approved GitHub access and a valid issue, PR, exact head SHA and prior receipt ID.
3. Verify a matching `bridge/responses/<id>.json` on the private `odin-bridge-outbox` branch with `action=review_feedback`, `status=complete` and `result.recorded=true`.
4. Run `python -B scripts/odin_review_feedback.py --list` *on Odin* to verify the note is visible as `trusted=false` with `action_executed=false`.
5. If an authorized coding worker subsequently uses the note, verify its independent follow-up receipt, PR SHA and CI. This last step is **not implemented as automatic self-editing**.

The loop may be idle while you're at work and resume on the next meaningful GitHub event. GitHub Actions and the existing on-device poll require no running Codespace. No paid inference, public listener, auto-merge or live Android control is introduced.
