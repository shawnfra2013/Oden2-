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

This is **not a secure end-to-end private conversation relay to Odin**.
The public GitHub inbox must never transport private messages. Natural
language conversations with Odin's local agent will need a separate
private, authenticated, consented pairing channel.

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
