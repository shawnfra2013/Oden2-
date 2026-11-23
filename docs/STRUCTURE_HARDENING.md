# Odin structure hardening · November 20, 2026

## Operating record

| Component | Supported use | Verification |
|---|---|---|
| Private GitHub mailbox | The supervised device polls the private inbox and publishes one receipt per ID. GitHub sign-in grants browser access to the private workflow. | [Browser dispatch 44798925193](https://github.com/shawnfra2013/Odin-private-bridge/actions/runs/44798925193) completed in 34 seconds. The [matching physical receipt](https://github.com/shawnfra2013/Odin-private-bridge/blob/odin-bridge-outbox/bridge/responses/1b109785813db31dd2139e1a16bec004.json) reported alive at 19:06:16 UTC. |
| Staging verification | A disposable device file contains a deterministic payload derived from the request ID. | [Physical receipt](https://github.com/shawnfra2013/Odin-private-bridge/blob/odin-bridge-outbox/bridge/responses/a1ca0fbe8a80409b8e1582d4a6bb25da.json) returned 52 bytes. Independent SHA-256 calculation matched. |
| Fixed model challenge | The device holds its credential and charges at most two attempted challenges per UTC day. Interrupted attempts reuse the local journal. | The November 20 device model receipt predates this repair. Browser and staging checks in this pass used no model calls. |
| Public telemetry | Sanitized device reports and GitHub source/CI status. | A historical receipt proves the state at its recorded time. |

## Disposition of the 21 audit findings

| Audit items | Source changes and operating contract |
|---|---|
| 1 · Receipt recovery | A local write-ahead receipt outside the Git checkout records the intended bytes. Under the service lock, recovery publishes that specific path and resumes any outstanding push. Conflicting content stops for inspection. Tests interrupt staging, commit and remote publication. Unrelated local edits survive. A dirty checkout left by an older release without an intent record still requires inspection. |
| 2, 7 · Reload reporting | Record target before pull, persist each reload attempt and return failure on restart or evidence errors. Retry up to three times for the same revision. Updated services require a changed PID in the source checkout and an unchanged target revision before verified status. Zero eligible services fails verification. A separate functional device receipt establishes application-level acceptance. |
| 3, 6 · Private service | Private mode uses its polling timer. Public service health now includes the private mailbox. The private mailbox stays under its own rollout procedure. A new private ping adds the source revision and running PID after installation. |
| 4 · Browser results | The private workflow checks reachability and readiness for Stage 5 and the exact byte count and SHA-256 for staging. Envelope completion alone cannot satisfy either check. |
| 5 · Secret checks | CI and sync check tracked Markdown and source using quiet matching, handle scanner failure and never print a matching line. The detector uses known patterns; coverage depends on credential format. |
| 8, 13 · Rollout and provenance | The installer discovers the detached, clean service checkout, checks its source origin and ancestry, reuses its protected key, and recognizes an installed target. Keep separate records for source SHA, CI, web deployment and running device SHA. GitHub private workflow updates take effect independently of the Termux launcher. |
| 12 · Polling cost | A fully reconciled private inbox/outbox revision pair skips the tree scan on unchanged polls. A new head triggers reconciliation. Large changing backlogs still require tree scans. |
| 14–15 · Update controls | Stage 5 installation and updates use the same explicit private opt-in validation. Safe pull and diagnostic preflight include ignored untracked paths and rename destinations; Git also refuses overwriting ignored files on merge. |
| 18–19 · Editors and workspace roots | Legacy editors display full changes. The direct editor lints and checks the patch before replacing the file atomically. Repair validates and applies the same in-memory patch. Source-relative agents follow their checkout. The longstanding worker queue remains under the canonical home workspace to preserve existing jobs and callers. |
| 20–21 · Reproducibility and documentation | CI uses a committed npm lockfile, pinned Ruff and syntax checks for runit launchers. This table supersedes earlier operating-status statements. Keep dated historical evidence for comparison. |

## Release acceptance

The live checks above exercised the previously running Termux service. On an enrolled Odin, the existing opt-in source updater calls the isolated mailbox installer after main passes its release checks. It only advances an existing running service and reuses saved credentials. An intentionally stopped service stays stopped. A device without auto-update needs an authorized local rollout. The four supported mailbox checks cannot install software. After cutover, send a private ping and compare the reported revision against the reviewed SHA, then verify a second receipt after restart. The direct phone route must be observed from the physical iPhone. See [phone enrollment](ODIN_PHONE_ACCESS.md). Use these checks before marking the release deployed.
