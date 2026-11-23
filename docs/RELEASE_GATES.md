# Odin release gates

**Definition of done:** Source tests are distinct from installed-device verification and the iPhone cellular test. All gates must report evidence and time.

1. **Document/architecture check (automated):** active Markdown passes `python -B scripts/check_active_docs.py`; outdated host guidance cannot reappear.
2. **Code and security (automated):** Python and Node tests, syntax, lint, secret scan, and protected-source checks pass on the proposed PR SHA.
3. **Source release (automated):** merge only reviewed code; require a completed successful GitHub `push` check on the exact merge SHA before updating Odin.
4. **Physical installation (separate evidence):** on Odin verify checkout SHA, local service state, safe update result, and a *newly requested*, matching private mailbox receipt with UTC timestamp. A prior `stage5_health` response is not release proof.
5. **Private network and phone (separate evidence):** verify an approved HTTPS origin, browser approval, iPhone on cellular with Wi-Fi off, fresh refresh, Home Screen reopening, and one paired encrypted response whose ID matches the request. Do not infer this from CI browser fixtures.
6. **Close issue / handoff:** link the source SHA, checks, device receipt, phone result, and unresolved limitations in [GitHub Issues](TASK_BOARD.md), [decision log](DECISIONS.md) if architecture changed, and [handoff](HANDOFF.md).

Any failed, missing, unavailable, or stale gate remains **unverified** rather than being promoted to success. Never expose secrets or private device addresses to document a pass.

Automated project snapshots are published as CI artifacts, *not* deployed code. See [status](PROJECT_STATUS.md).
