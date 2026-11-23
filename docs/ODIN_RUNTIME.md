# Odin 2 — CURRENT runtime truth

**Authority:** This document describes the supported architecture as of November 22, 2026. Verify actual reachability from a new receipt before claiming an installed or running device is current. [Earlier observations are archived](archive/README.md). The repository and CI are separate from the physical handheld.

## What Odin uses

| Purpose | Supported path | Verification boundary |
| --- | --- | --- |
| Source of truth | [GitHub `shawnfra2013/Oden2-`, main](https://github.com/shawnfra2013/Oden2-) | Exact commit SHA and exact-SHA CI |
| Device communication | [Private GitHub mailbox](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml) | Matched request ID, completed receipt, and timestamp |
| Offline terminal source results | Canonical `~/odin-workspace/state/codespace-receipts/` → private mailbox `bridge/local-source-receipts/` | Receipt ID + exact SHA + UTC upload marker; source-only, not device acceptance |
| Handheld workstation | `http://127.0.0.1:8765/` on Odin | Local Termux HTTP health and real user turn |
| Local chat | On-device model server, usually `127.0.0.1:18080`, if installed and enabled | Real local reply with network disconnected |
| Supervised services | Termux runit, including `odin-private-mailbox`, `odin-git-sync`, and task worker as configured | Read-only service and process checks on Odin |
| Code updates | Existing CI-gated opt-in updater and Git sync | Git SHA installed + service reload evidence; no implied restart |
| Optional iPhone control | Standalone `mobile/` Node viewer on `127.0.0.1:8780` behind an approved private HTTPS origin | Installed app release, secure browser access, and real cellular test |

The internal directory `stage5/`, service `odin-stage5`, environment keys prefixed `ODIN_STAGE5_`, and mailbox action `stage5_health` remain **compatibility identifiers**. They refer to the **Odin Local Workstation**, *not* an unfinished development stage. Do not rename them without a tested device migration.

The agreed work process is defined in [ODIN_WORKFLOW.md](../ODIN_WORKFLOW.md). Tracked and device-generated services plus default port numbers are inventoried in the [service registry](SERVICE_REGISTRY.md); it is source metadata, not proof a process is running.

## Source, device, and phone are three distinct states

1. **Source verified:** GitHub commit exists and required checks pass on that exact SHA.
2. **Device verified:** A newly submitted private request has a matching completed receipt, device SHA where the action provides it, and a recorded UTC time. A previous health reply does not prove a new release was installed.
3. **Phone verified:** The approved HTTPS viewer loads the intended code, retains browser authorization, refreshes, and delivers a paired encrypted reply over the iPhone's cellular connection with Wi-Fi disabled.

The private mailbox works asynchronously through GitHub. The phone does **not** have a direct secure remote terminal by virtue of having GitHub access. Browser login, device mailbox pairing, and encrypted-chat pairing are separate credentials and must never be conflated.

**Private networking:** Tailscale access is a planned verification target in [issue #70](https://github.com/shawnfra2013/Oden2-/issues/70), not a proved active route. Keep loopback ports bound locally and do not expose them to the public internet. An approved HTTPS origin must be verified before adding a new Home Screen shortcut.

## Offline receipt continuity

The handheld's existing private GitHub mailbox service also carries validated source-test receipts, without a new provider. Termux stores them durably while offline; when connectivity returns, the service replays them to its private outbox branch and retries interrupted pushes. The original local files remain available. GitHub Actions and ChatGPT's scheduled receipt watcher can review source-check outcomes after upload; neither is a continuously connected terminal or a substitute for separate matched device-action receipts. Codespaces runs cloud source tests and does not receive the handheld mailbox SSH key. See [the terminal guide](CODESPACES_WORKFLOW.md) and [the private mailbox runbook](ODIN_GITHUB_BRIDGE.md).

## How to operate safely

- **Check Odin:** open the private GitHub workflow, run `ping` or `stage5_health`, and inspect the *matching* response in the private outbox. These checks make no model request. Never treat successful submission alone as a device response.
- **Use locally:** open the workstation at `127.0.0.1:8765` on the handheld. For offline inference, follow [offline chat](OFFLINE_CHAT.md) and verify an actual answer with internet disabled.
- **Update source:** use [the reviewed updater instructions](ODIN_SAFE_UPDATES_AND_ROADMAP.md), preserving local state and rejecting unsafe Git histories. Do not silently restart services.
- **Use the iPhone:** follow [mobile setup](../mobile/README.md) and [shortcut cutover](SHORTCUT_CUTOVER.md); do not reuse an old host or browser credential. Cellular end-to-end acceptance remains tracked in [issue #69](https://github.com/shawnfra2013/Oden2-/issues/69).
- **Verify release:** follow [release gates](RELEASE_GATES.md). A CI success never certifies the actual phone or handheld.
- **Continue work:** read [status](PROJECT_STATUS.md), [issues](TASK_BOARD.md), [decisions](DECISIONS.md), and [handoff](HANDOFF.md).

The old hosted message service and wake routes are not supported deployment paths. Historical command examples belong exclusively in the archive. Preserve device journals for recovery but do not reactivate them as operating instructions.
