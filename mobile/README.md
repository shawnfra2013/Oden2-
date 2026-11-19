# Odin Control — Hosted iPhone UI

Source of truth: `shawnfra2013/Oden2-`, directory `mobile/`.
Production: https://odin-control.vercel.app/

## Existing public monitoring

The Overview, Activity, and System tabs read sanitized public bridge receipts,
GitHub commits, and CI runs. They do not require credentials. These are
last-known reports, not proof that the Odin remains online.

## Optional private controls (server-side credentials required)

On the **existing** Vercel project `odin-control`, configure these project
Environment Variables for Production, then redeploy:

| Key | Storage | Purpose |
| --- | --- | --- |
| `ODIN_CONTROL_ACCESS_TOKEN` | Sensitive | A unique, randomly generated bearer token (32+ chars) shared privately with the owner for access to protected endpoints. |
| `ODIN_OPENAI_MODEL` | Plain | API model name, e.g. `gpt-5-mini`. |
| `OPENAI_API_KEY` | Sensitive | A fresh OpenAI Platform API key. Do not use a previously exposed or revoked key. |
| `ODIN_GITHUB_TOKEN` | Sensitive | Fine-grained GitHub token limited to **this repository**, Contents read/write; only needed for device diagnostics. |

The server never ships the OpenAI API key or GitHub token to the browser.
The app access token is entered in the **Chat** tab (Private controls).
It is held only in this open browser tab's JavaScript memory. Closing or
reloading the tab requires entering it again. Never share it in GitHub,
screenshots, or AI conversation messages.

Cloud AI chat uses OpenAI's HTTPS Responses API with `store: false`
and a bounded per-tab history. It is a **separate API conversation**:
it does not synchronize the current ChatGPT app thread or private local
Odin SQLite conversations. Users should not enter confidential secrets
in prompts. The UI labels cloud model replies separately from device receipts.

Diagnostics use a fixed allowlist of `ping`, `repo_status`, `services`,
`stage5_health`, `checks`, `verify_release`, and `preflight_release`.
The private Vercel endpoint writes fresh expiring requests into the public
GitHub `odin-bridge-inbox` branch. Odin polls it and writes sanitized
results to `odin-bridge-outbox`. Read receipts remain visible in the
Activity tab. **No user-supplied arbitrary commands, remote shell,
service restarts, dependency installs, or deployments** are supported.

The **separate authenticated private relay** at `/api/relay` carries iPhone ↔
Odin messages in the project's private Blob store. It requires the distinct
`ODIN_DEVICE_RELAY_TOKEN` on the device. This is a basic shared-secret personal
relay, **not** end-to-end encryption or a connection to this ChatGPT thread.
Do not send conversations through the public GitHub inbox. See
[`docs/ODIN_PRIVATE_RELAY.md`](../docs/ODIN_PRIVATE_RELAY.md).

## Security design

- All private routes require an exact production Origin and a fixed
  bearer token, stored in sensitive server-side environment variables.
- No credentials are hardcoded, exposed through `/api/capabilities`,
  included in GitHub, or returned in browser responses.
- The UI does not persist the access token in localStorage, cookies or
  GitHub branches. Changing environment variables requires a deployment
  for running instances to use new values.
- This small personal gateway uses one shared secret, **not multi-user
  sign-in**. Rate limiting, revocation, per-device session identities,
  encrypted private relay, and audit logs will be necessary before
  allowing broader file or shell actions.
- The hosted UI's monitoring endpoints remain public, because the
  underlying GitHub repository and mailbox are public.

## iPhone installation

Open https://odin-control.vercel.app/ in Safari; Share → Add to Home Screen.
No new native app and no destructive migration are required.

## Build and deploy notes

The Vercel project currently uses a source-file deployment because the
team's GitHub integration is not installed. Automatic Git-to-Vercel sync
is **not** enabled. New deployments must use the reviewed `mobile/`
files from the canonical GitHub `main` commit and be verified separately.

GitHub CI runs Node syntax and security tests plus the original Stage 4,
Stage 5 and Ruff regression suites.

## Stabilization and operational verification (2026-11-19)

- The shared access module must export `validOrigin` used by `/api/relay`. A previous missing export caused 500 errors. The full authenticated iPhone → Odin → reply handler flow is now covered by regression tests.
- `/api/relay` returns HTTP 503 and a nonsensitive failing stage if the private store fails. No messages or tokens appear in server logs. The browser keeps an error visible instead of overwriting it during render.
- A successful `/api/session` means app access succeeded; it does **not** prove the device is online. A `queued` message is not considered delivered until an actual device receipt arrives.
- `odin-git-sync` is already runit-supervised and logs to `logs/git-sync.log`. The optional `odin_auto_update.py` extension can apply a CI-passing exact GitHub SHA with `odin-safe-pull.sh` after one-time activation; it is **off until enabled on the device**. It never silently force-resets the checkout or restarts running processes. See `docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md`.
- `odin-private-relay` is a separate, existing device poller. Its runtime may be stopped by Android battery management or after reboot; a supervisor PID alone does not prove an end-to-end reply.
- Public GitHub monitoring and private message delivery are different systems; an old public GitHub receipt must not be reported as live private relay health.
- Vercel deployment is manual (source-file deployment). CI green is necessary but cannot prove a deployed function or Odin service is operating until a live route and `/ping` are checked.

## Safe read-only task shortcuts

The private device composer offers Ping, Device status, Git task and Queue task shortcuts. These fill predefined `/ping`, `/status`, `/task git-status` and `/task queue-status` messages; the user still taps Send. Responses require a running, paired Odin relay. Failed or delayed acknowledgments are labeled instead of reported as healthy. Unrecognized tasks cannot execute arbitrary shell commands.
