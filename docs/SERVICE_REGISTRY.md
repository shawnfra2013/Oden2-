# Odin service and port registry

The machine-readable source is [config/odin-services.json](../config/odin-services.json). The source validator checks its entries against tracked files, source port defaults, and current documentation. **Presence in GitHub does not imply a live Termux process**. To check live listeners, inspect the handheld's services and ports independently.

| Tracked or configured component | Default listener | Source status |
| --- | --- | --- |
| Odin Local Workstation, internal `odin-stage5` | `127.0.0.1:8765` | Tracked Termux launcher |
| Standalone Node phone viewer | `127.0.0.1:8780` | Optional loopback service; HTTPS route not verified |
| Optional local model runtime | `127.0.0.1:18080` | Configured default, external process not guaranteed installed |
| Git sync | None | Tracked runit launcher |
| Private GitHub mailbox | None | Device-generated runit launcher, script tracked in repo |
| Task worker | None | Device-generated runit launcher, script tracked in repo |
| Optional legacy public diagnostics | None | Tracked launcher, **not** the active private mailbox |

**Tailscale phone access:** draft PR #68 proposed `8766` over a Tailscale IPv4 HTTP listener. That is **not** an active main-branch listener or verified HTTPS setup. The required phone path is approved Tailscale HTTPS with a real cellular acceptance test. Don't introduce a dead port into the live registry.

**Legacy code:** Some historical relay modules remain tracked for compatibility tests or migration investigation. They are not evidence of an active hosted service and must not be started automatically. Historical provider names may remain in archived documents or regression fixtures, never in active setup instructions.

## Validation

- `python -B scripts/check_odin_structure.py` checks required files and service script references; JSON validity; duplicate listener port and service IDs; source-port agreement; Markdown relative links outside the archive; and absence of retired-host references in active boot/UI entry points.
- `python -B scripts/check_active_docs.py` additionally checks all current documentation against retired-host and obsolete-stage terms.
- GitHub Actions runs these tests automatically on PRs and pushes to main.
- Device operators separately verify `sv status`, bound sockets, model HTTP readiness, and a fresh matching private mailbox receipt. Missing runtime proof is **unverified**, not **passing**.

See [ODIN_WORKFLOW.md](../ODIN_WORKFLOW.md), [current runtime](ODIN_RUNTIME.md), and [release gates](RELEASE_GATES.md).
