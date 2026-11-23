# Odin on iPhone

Open the same web app from either device. Odin serves it on `http://127.0.0.1:8765/`. The iPhone connects through Tailscale to Odin's private address on port `8766`. Termux runs the app and the on-device model. GitHub handles reviewed source updates and separate diagnostic receipts.

## Connect the iPhone

1. Connect both devices to your private Tailscale network. Find each device's IPv4 address in the Tailscale app. Keep access to Odin's port `8766` limited to your iPhone in the tailnet policy. Odin also checks the connecting IP against the iPhone address you enroll.
2. On the reviewed release, run the following on Odin. The command shows the exact URL to open. If Tailscale assigns a new address, repeat enrollment with both current addresses.

   ```bash
   (
     set -e
     cd "$HOME/odin-workspace"
     read -r -p "Odin Tailscale IPv4 address > " odin_ip
     read -r -p "iPhone Tailscale IPv4 address > " iphone_ip
     python -B stage5/phone_access.py "$odin_ip" "$iphone_ip"
     sv -w 20 restart "$PREFIX/var/service/odin-stage5"
     curl -fsS --max-time 5 http://127.0.0.1:8765/api/health
   )
   ```

3. On iPhone, open the printed URL in Safari with Tailscale connected. Turn Wi-Fi off to verify over cellular. Check that System shows the on-device provider and send a short chat prompt. In Safari, use **Share → Add to Home Screen**. Replace the old Home Screen icon after the new one reopens successfully.
4. Use **Refresh app** to reload current app files from Odin and refresh task counts and backend status. **Check connection** refreshes just those live checks and renews the browser session. Chat returns a reply only while Odin and its model are online. Reopen the Home Screen app after locking the iPhone, then repeat with Odin's screen off. Test recovery after a service restart separately from Android reboot.

The enrollment file `~/.config/odin-web/phone-peer` stays on Odin. The phone listener binds only to the configured private address, verifies the TCP peer address, and checks the requested host and write origin. App cookies are automatic. Tailscale encrypts the private connection between devices. Safari loads this private URL as HTTP, so browser features that require an HTTPS secure context can be unavailable. Odin's own loopback page remains available when the phone listener is waiting for Tailscale.

## Retire the older setup

While the previous release is still installed, stop its old phone relay so it cannot relaunch after the source is removed. This preserves the launcher, archive, and credentials for recovery. Use the reviewed Git update process before enrolling the phone.

```bash
legacy="$PREFIX/var/service/odin-private-relay"
if [ -f "$legacy/run" ]; then
  touch "$legacy/down" && sv -w 20 down "$legacy"
fi
```

If the Git-sync supervisor still runs its old launcher, reload it once the updated launcher is installed. Home Screen icons keep their original addresses. Replace the old icon and any old Viewer bookmarks when the direct route passes. Retire the old hosting project separately after deciding whether its stored messages need export. Source cleanup alone does not change that account.

## Verify model readiness

Use the [offline model guide](OFFLINE_CHAT.md) to install or verify the model. The safe readiness checks are a local health request to `127.0.0.1:8765/api/health`, a local model health request to `127.0.0.1:18080/health`, and a real reply in the phone UI. If model enrollment is missing, the web app can still show its system and task panels and chat stays disabled.
