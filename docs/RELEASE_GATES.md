# Odin release gates

**Definition of done:** Source tests are distinct from installed-device verification and the iPhone cellular test. All gates must report evidence and time.

1. **Document/architecture check (automated):** active Markdown passes `python -B scripts/check_active_docs.py`, and `python -B scripts/check_odin_structure.py` validates the agreed workflow, tracked services, default ports, JSON, relative links and active entrypoints. Neither check can verify actual device listeners.
2. **Read-only preflight (automated):** `python -B scripts/odin_preflight.py --mode source` must pass on the candidate SHA and publish a dated JSON artifact. The report distinguishes PASS, FAIL and UNVERIFIED. Never treat missing live device/phone evidence as success.
3. **Code and security (automated):** Python and Node tests, syntax, lint, secret scan, and protected-source checks pass on the proposed PR SHA.
4. **Source release (automated):** merge only reviewed code; require a completed successful GitHub `push` check on the exact merge SHA before updating Odin.
5. **Physical installation (separate evidence):** on Odin verify checkout SHA, local service state, safe update result, and a *newly requested*, matching private mailbox receipt with UTC timestamp. A prior `stage5_health` response is not release proof.
6. **Private network and phone (separate evidence):** verify an approved HTTPS origin, browser approval, iPhone on cellular with Wi-Fi off, fresh refresh, Home Screen reopening, and one paired encrypted response whose ID matches the request. Do not infer this from CI browser fixtures.
7. **Close issue / handoff:** link the source SHA, checks, device receipt, phone result, and unresolved limitations in [GitHub Issues](TASK_BOARD.md), [decision log](DECISIONS.md) if architecture changed, and [handoff](HANDOFF.md).

On the physical Odin, after installing an approved revision, use `python -B scripts/odin_preflight.py --mode device` for an explicitly reported read-only check. `--strict` exits nonzero if any required check lacks evidence; it cannot itself approve release because iPhone acceptance requires a real test. See [preflight guide](PREFLIGHT.md).

Any failed, missing, unavailable, or stale gate remains **unverified** rather than being promoted to success. Never expose secrets or private device addresses to document a pass.

Automated project snapshots are published as CI artifacts, *not* deployed code. See [status](PROJECT_STATUS.md).
