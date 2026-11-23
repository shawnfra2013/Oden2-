# Odin — current session handoff

**Prepared:** November 22, 2026 (Central). This is a human-maintained checkpoint; generate a fresh UTC status and handoff artifact using [the snapshot workflow](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml) at the start of the next session.

## Current source and architecture

- Canonical supported stack: [runtime](ODIN_RUNTIME.md). User-facing local browser name: **Odin Local Workstation**.
- Private bridge: [GitHub mailbox](ODIN_GITHUB_BRIDGE.md), independent of the optional standalone phone viewer.
- The last observed matching private `stage5_health` receipt in the November 22 live test was completed at **2026-11-23 04:22:23 UTC**, showing the local workstation reachable *at that time*. This is historical evidence, not a live guarantee or proof of a new installed SHA.
- Tailscale routing and the iPhone cellular viewer have not passed end-to-end acceptance.

## Active issues

[#69](https://github.com/shawnfra2013/Oden2-/issues/69) phone; [#70](https://github.com/shawnfra2013/Oden2-/issues/70) private routing; [#71](https://github.com/shawnfra2013/Oden2-/issues/71) exact-SHA device rollout; [#72](https://github.com/shawnfra2013/Oden2-/issues/72) documentation/release operations.

## Saved viewer link and historical hosting

The uploaded `Odin Viewer.txt` still contains only an older external dashboard URL. The original hosted viewer was introduced by [PR #9](https://github.com/shawnfra2013/Oden2-/pull/9), and its message journal was expanded in [PR #11](https://github.com/shawnfra2013/Oden2-/pull/11). Both are **historical** implementations. A GitHub source cleanup or a new chat does not rewrite the actual iPhone Shortcut or Home Screen bookmark. The supported replacement HTTPS viewer origin is **not yet verified**; follow [the shortcut cutover procedure](SHORTCUT_CUTOVER.md) instead of guessing a destination.

## Canonical workflow and source structure checks

- [ODIN_WORKFLOW.md](../ODIN_WORKFLOW.md) defines the agreed working approach without paid model calls; [AGENTS.md](../AGENTS.md) points repo-aware assistants at it.
- [config/odin-services.json](../config/odin-services.json) records tracked vs device-generated launchers and current loopback defaults; [service guide](SERVICE_REGISTRY.md) explains limitations.
- `scripts/check_odin_structure.py` and regression tests are part of the GitHub CI gate, not a claim that sockets or daemons are alive on the handheld.
- Approved fixes are in [issues #75–#79](https://github.com/shawnfra2013/Oden2-/issues/75); additional planned improvements are [#80–#84](https://github.com/shawnfra2013/Oden2-/issues/80). All require separate acceptance evidence before marking complete.

## Session continuation

1. Check `main` and the latest [source CI](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-checks.yml) for the exact merge SHA; do not reuse the old screenshot revision.
2. Download a new [project snapshot artifact](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml), which timestamps public status without exposing private receipts.
3. Use the private mailbox for a *new* matching device request/response before claiming current physical health.
4. Resume [task board](TASK_BOARD.md) issues in order; record actual acceptance evidence and blockers, including the iPhone cellular round trip.
5. At session end, update this handoff with the last verified commit, tests, receipts, remaining gaps, and next concrete action.

**Never equate** an old hosted viewer page, a GitHub CI green badge, and a newly verified Odin or iPhone connection.
