# Odin preflight — explicit PASS / FAIL / UNVERIFIED

This preflight is **read-only**. It never invokes an AI model, installs an update, restarts a daemon, writes GitHub data, or contacts the iPhone. It checks source assumptions separately from observations on Odin.

## Source CI (runs on every pull request and main push)

```bash
python -B scripts/odin_preflight.py --mode source --json-path /tmp/odin-preflight.json
```

GitHub Actions uploads the dated, redacted JSON report as the `odin-source-preflight` artifact. The report checks the Git revision, the active documentation guard, service/port registry and tracked entrypoints, and the private mailbox branch-name/source wiring. A source check that fails stops the CI job. Live device status, private HTTPS, and the iPhone remain **UNVERIFIED** even when source checks pass.

## Device check after a reviewed installation

On the actual Odin in Termux, inspect **without changing services**:

```bash
cd ~/odin-workspace || exit 1
python -B scripts/odin_preflight.py --mode device
```

The optional `--strict` flag returns nonzero if any required item lacks a PASS. It is deliberately **not** an unattended deployment or approval button: exact GitHub main SHA, model inference and iPhone cellular cannot be proven from this command alone.

The device mode checks available runit status for required private mailbox and Git sync, reports optional task/workstation services, probes the local workstation health endpoint, probes only the TCP port of an already enabled on-device model, and inspects Tailscale CLI state if the CLI exists. Neither a TCP connection nor HTTP health proves a model completed inference. The Android Tailscale app may exist without a CLI. A failed or missing check is never silently upgraded.

## Release decision and rollback

1. Review source CI for **the exact intended SHA**.
2. If any source gate fails, do not merge or install; fix it in a review branch and rerun.
3. After a passing reviewed release, the configured safe updater may pull the matching revision. The enabled/disabled auto-update preference is an Odin device setting; GitHub does not grant device access automatically.
4. Confirm installed SHA, supervisor states, fresh request-bound mailbox evidence, local inference and actual iPhone Tailscale HTTPS acceptance.
5. If a rollout fails, stop further rollout and preserve private state. Report the failed evidence and the **last verified source commit**. Revert a GitHub change through a new reviewed revert commit—never force-push or discard history. A physical device rollback is separately reviewed; don't run reset/delete/restart operations automatically.

**Completion policy:** an issue remains in progress or unverified until the required source tests and real device/phone receipts exist. See [release gates](RELEASE_GATES.md) and [workflow](../ODIN_WORKFLOW.md).
