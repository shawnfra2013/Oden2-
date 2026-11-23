# Odin Control for iPhone

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
In the dashboard, Request Browser Approval shows a browser ID. Approve it
on the host using `ODIN_TRUSTED_BROWSER_ID` to reuse the browser's session
across visits. Alternatively, unlock private access with the configured
`ODIN_CONTROL_ACCESS_TOKEN`, which has an encrypted browser vault option.
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
