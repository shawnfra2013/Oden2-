# Odin Control for iPhone

The source of truth for supported transports is [current Odin runtime](../docs/ODIN_RUNTIME.md). The public dashboard status is **not** a private-device heartbeat. The iPhone over-cellular test remains open in [issue #69](https://github.com/shawnfra2013/Oden2-/issues/69); verify the private network and HTTPS route before considering a Home Screen shortcut complete.

The dashboard shows sanitized GitHub status and keeps optional device chat and
online chat in separate routes. For device checks without setting up a dashboard,
open the [private GitHub mailbox](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml) in Safari and sign in to GitHub.

## Serve the dashboard

Run `npm ci --prefix mobile` and `npm start --prefix mobile` with Node 22 or
newer. The Node process listens on `127.0.0.1:8780` by default. Set
`ODIN_MOBILE_PORT` to override the port. Serve that listener behind the
operator's authenticated network or HTTPS reverse proxy. Use the actual
HTTPS address with no trailing slash for `ODIN_CONTROL_ORIGIN`.

Open the HTTPS address in Safari, then use Share → Add to Home Screen.
Open the installed shortcut and select **Remember this browser** there to obtain its browser ID. Approve it
on the host using `ODIN_TRUSTED_BROWSER_ID` to reuse the browser's session
across visits. Alternatively, unlock private access with the configured
`ODIN_CONTROL_ACCESS_TOKEN`, which has an encrypted browser vault option.
On reopen, the viewer tries its approved browser cookie automatically. If that fails and a vault was previously saved at this origin, enter its local unlock password. Clearing website data removes both. Repeat browser approval on the same HTTPS address if needed. Never paste the token into chat.

An approval belongs to its origin. Set up the new origin once when moving
from the old dashboard.

| Feature | Host configuration |
| --- | --- |
| Private access | `ODIN_CONTROL_ORIGIN`, plus `ODIN_TRUSTED_BROWSER_ID` or `ODIN_CONTROL_ACCESS_TOKEN` |
| Encrypted on-device model chat | `ODIN_PRIVATE_MAILBOX_TOKEN`, and the [Odin model and key setup](../docs/OFFLINE_CHAT.md) |
| Optional public diagnostic mailbox submission | `ODIN_GITHUB_TOKEN`, and an explicitly enrolled public diagnostic service |
| Optional paid online chat | `OPENAI_API_KEY`, `ODIN_OPENAI_MODEL`, positive `ODIN_CLOUD_CHAT_DAILY_LIMIT`, and a durable TLS Redis ledger configured as `ODIN_CHAT_REDIS_URL` |

Phone refresh reads dashboard and GitHub data. Open the private workflow to
request a new device receipt. The legacy message composer, service restart
buttons and wake endpoint are retired. A mobile host is optional for Odin
local chat, private GitHub checks, and normal updates.
