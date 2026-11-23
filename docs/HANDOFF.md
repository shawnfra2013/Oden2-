# Odin — current session handoff

**Prepared:** November 22, 2026 (Central). This is a human-maintained checkpoint; generate a fresh UTC status and handoff artifact using [the snapshot workflow](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml) at the start of the next session.

## Current source and architecture

- Canonical supported stack: [runtime](ODIN_RUNTIME.md). User-facing local browser name: **Odin Local Workstation**.
- Private bridge: [GitHub mailbox](ODIN_GITHUB_BRIDGE.md), independent of the optional standalone phone viewer.
- The last observed matching private `stage5_health` receipt in the November 22 live test was completed at **2026-11-23 04:22:23 UTC**, showing the local workstation reachable *at that time*. This is historical evidence, not a live guarantee or proof of a new installed SHA.
- Tailscale routing and the iPhone cellular viewer have not passed end-to-end acceptance.

## Active issues

[#69](https://github.com/shawnfra2013/Oden2-/issues/69) phone; [#70](https://github.com/shawnfra2013/Oden2-/issues/70) private routing; [#71](https://github.com/shawnfra2013/Oden2-/issues/71) exact-SHA device rollout; [#72](https://github.com/shawnfra2013/Oden2-/issues/72) documentation/release operations.

## Session continuation

1. Check `main` and the latest [source CI](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-checks.yml) for the exact merge SHA; do not reuse the old screenshot revision.
2. Download a new [project snapshot artifact](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml), which timestamps public status without exposing private receipts.
3. Use the private mailbox for a *new* matching device request/response before claiming current physical health.
4. Resume [task board](TASK_BOARD.md) issues in order; record actual acceptance evidence and blockers, including the iPhone cellular round trip.
5. At session end, update this handoff with the last verified commit, tests, receipts, remaining gaps, and next concrete action.

**Never equate** an old hosted viewer page, a GitHub CI green badge, and a newly verified Odin or iPhone connection.
