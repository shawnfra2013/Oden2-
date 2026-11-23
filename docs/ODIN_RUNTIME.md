# Odin runtime and supported transports

| Task | Entry point | Dependency |
| --- | --- | --- |
| Open the workstation on Odin | `http://127.0.0.1:8765/` | Termux and the supervised `odin-stage5` service |
| Work without internet | Local chat in the workstation or `python -B scripts/odin_chat.py` | The enrolled model server and downloaded weights, usually on loopback port `18080` |
| Check Odin from iPhone | [Private GitHub Actions mailbox](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml) | GitHub sign-in, a running `odin-private-mailbox` service, and internet access on both devices |
| Use the full phone dashboard | Serve the `mobile/` app on an approved HTTPS origin | The [phone setup](../mobile/README.md) and optional credentials for enabled features |
| Update source | Existing runit Git sync and opt-in CI-gated updater | GitHub, exact-SHA CI, and the handset's updater configuration |

The historical name Stage 5 is retained in protocol names, service IDs, and the
`stage5/` directory. It refers to Odin's local browser workstation. The
workstation binds to loopback and its address opens on the handheld itself.
The model listener remains on loopback as well. The repository does not
configure a Tailscale service, route, or binding for either port.

The private mailbox polls its GitHub branches on a timer. Git sync also uses
a local timer. Both paths operate without this chat. In the private workflow,
`ping` verifies the mailbox and `stage5_health` checks the local HTTP server.
Those actions make zero model requests. A configured provider reported by
health still needs a successful reply to verify model execution.

The old hosted relay and wake routes are retired. A prior phone shortcut
still points to its original domain and needs a new shortcut. The private
workflow link above is usable with GitHub sign-in. The full dashboard
requires its own reachable HTTPS address and browser approval for that origin.

## Cutover verification

1. Confirm the reviewed source SHA passes GitHub Checks.
2. On Odin, confirm the running Git sync launcher uses the local timer and
   `odin-stage5` serves its loopback health endpoint. Existing copied runit
   scripts need the approved service update before their behavior changes.
3. Run private `ping` and `stage5_health` and open the matching receipts.
   A queued request establishes submission. The completed receipt establishes
   a device response at its recorded time.
4. Complete a browser or CLI turn with Wi-Fi disabled using
   [offline model setup](OFFLINE_CHAT.md).
5. Confirm the HTTPS route reaches the standalone mobile listener (default `127.0.0.1:8780` on its host). The workstation on `8765` is a different app. With Wi-Fi off and the private network connected, open the approved HTTPS origin from the iPhone Home Screen. Refresh, close, and reopen it. Confirm automatic sign-in or unlock the saved vault with its password. Send an encrypted device chat and verify the matching reply. Keep the previous shortcut until the replacement passes.
6. Record the deployed Git SHA, test time, device receipt ID, and which phone checks passed. CI tests the documented listener, capabilities response, and browser flow on a runner. Only the handset and iPhone can confirm the installed route.

Existing local relay records can be inspected with
`python -B scripts/odin_relay_client.py --status` or `--investigations`.
If an older runit installation has `odin-private-relay` enabled, stop it
with `sv down "$PREFIX/var/service/odin-private-relay"` during the approved
cutover. Keep the local journal for recovery.
