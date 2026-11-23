# Odin status — evidence, not assumptions

**This is a guide to obtaining a status snapshot, not a live value.** The dated, automatically generated snapshot is available as an artifact from the [Odin Project Snapshot workflow](https://github.com/shawnfra2013/Oden2-/actions/workflows/odin-project-snapshot.yml) once that workflow has run.

A snapshot reports:
- GitHub `main` SHA, observation time (UTC), and **exact-SHA** source-check outcome;
- the open GitHub issue count and tracked work;
- the private-device status as **not checked** in public CI artifacts, since private responses must not be copied into public build logs;
- phone acceptance as **not verified by CI** until an actual device/phone test is recorded in [issue #69](https://github.com/shawnfra2013/Oden2-/issues/69).

Run the read-only local report without credentials: `python -B scripts/odin_project_snapshot.py --output-dir /tmp/odin-project-status`. The generated `status.md` and `handoff.md` contain timestamps; rerunning them is necessary for new information. The workflow runs on a daily schedule and manually; it publishes artifacts without committing changing timestamps to `main`.

A public source-status artifact **must never** report an unobserved handset heartbeat or call a private GitHub response "live". To inspect the device, use [the private mailbox runbook](ODIN_GITHUB_BRIDGE.md) and match a newly submitted request to a receipt.
