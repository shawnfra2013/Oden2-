# Local coding roadmap

The owner observed an offline reply on the handheld. The [installer receipt](https://github.com/shawnfra2013/Odin-private-bridge/blob/odin-bridge-outbox/bridge/responses/3020503f4deb26f6fbf26e75d68efd47.json) records a successful coding check. The list below is a backlog. No service consumes it or starts the next item.

## This release

- [x] Enter or import one small UTF-8 project excerpt on Odin.
- [x] Save and forget that note in the browser. Including it in model input is an explicit selection.
- [x] Reject local-only options when the server selects a cloud provider.
- [x] Offer a 128-output-token cap for quick replies and preserve the regular limit.
- [x] Show elapsed inference time for a completed request.
- [x] Add one private Stage 5 acceptance action with a fixed prompt, local provider check and exact-answer receipt.

## Next reliability and capability tests

1. Measure cold and warm replies to the same short coding question on the actual handheld.
2. Record first-token latency separately from total response time before changing threads or context size.
3. Check the context limit with long code, Unicode, and several turns. Provide a clear prompt to trim input.
4. Test short and regular modes against the same three small coding fixes, recording correctness and time.
5. Shipped a read-only Python function lookup with file, line and revision. Extend to other languages only when needed.
6. Offer project-note search if manually selecting one excerpt becomes a bottleneck.
7. Present a proposed diff and the files it affects before any write.
8. Apply one approved diff in an isolated worktree; stop on a stale base commit.
9. Run one named project test suite there. Record its exit status, duration and revision.
10. Display queued, running, failed, interrupted and completed states for one job ID in the local UI.
11. Support cancellation of a running job and confirm that its child process exited.
12. Verify interrupt and replay behavior, including loss of Wi-Fi after local execution.
13. Deliver terminal-state notifications from existing receipts; avoid model calls for status.
14. Verify a real on-device answer through Tailscale after reopening the iPhone web app.
15. Evaluate an optional Claude provider on the same tasks, only with explicit cloud selection and a budget.
16. Prototype one user-selected hardware button that opens local chat; verify ordinary controls still work.

A checked tool result needs a deterministic assertion. Model suggestions stay advisory. Each new device operation has a named action, bounded inputs, an expected result and a stop condition.
