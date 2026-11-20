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
By default, the token is held only in the open tab's JavaScript memory.
On this device, the owner can explicitly opt in to **Save encrypted access**:
choose a new local unlock password of at least 12 characters. The browser
encrypts the existing bearer token with Web Crypto PBKDF2-SHA-256 (310,000
iterations) and AES-256-GCM, using a random salt and nonce per save. Only the
encrypted vault is saved to this browser's local storage. The unlock password
is never saved, logged, or sent to Vercel; after unlock the original token
still authenticates the HTTPS API. The server credentials and Odin pairing
are not changed.

The next time the app opens **in the same browser/storage context**, enter
the shorter password instead of copying the long token. "Use access token
instead" remains available if the browser loses the saved vault. "Forget
saved access" removes the encrypted local copy. "Lock private session" clears
the in-memory token but leaves the optional encrypted copy for future
unlocks. Safari and an iPhone Home Screen web app may use different storage;
a different device or cleared website data requires the original token.

Choose a strong, unique multi-word password: a short PIN is not supported.
Encryption helps protect a saved token at rest but does not make an
untrusted or compromised browser safe. Never share the token or unlock
password in GitHub, screenshots, or AI messages.

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
- By default the browser stores no token. The optional password vault
  stores **encrypted ciphertext only** under a namespaced localStorage key;
  no plaintext token, unlock password, or session cookie is stored. GitHub
  never receives any credential. Changing the server token invalidates an
  old saved vault until reconnected with the new token and re-saved.
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

## AI readiness in the private Odin inbox

The **AI status** shortcut fills /ai-status; Odin replies with
credential-safe information from the environment of its *running relay
process*. ready=true only indicates configuration, not a confirmed
network/model response. **Test AI** fills /ai-test, which invokes the
existing on-device model adapter when sent; it does not send a ChatGPT
app message or execute a shell command.

A normal message is routed to Odin's selected device AI provider and
its existing local SQLite conversation. Failures are stored as bounded
codes such as ai_disabled, credential_missing, model_missing,
provider_timeout, and provider_unavailable; the iPhone shows a
nonsecret explanation. Credentials remain on the device. The
separate **Cloud AI** section still needs a server-side key and is
not automatically enabled by Odin's device provider. This release
does not configure API credentials or verify a live provider call.

## Restart all supervised Odin services from iPhone

Once the updated physical Odin private relay is running, unlock
Odin Control and open System → Service controls → Restart all services.
A confirmation dialog warns that active work may be interrupted.
The Chat → Messages & responses composer accepts the exact
/restart-services command (also "restart all services" and
"restart odin services"). The shortcut pre-fills this command;
the owner still sends it and confirms.

This uses the authenticated private message API, not public GitHub
diagnostics. The action cannot execute arbitrary shell commands,
change credentials, reset Git, install packages, or reboot Android.

The detached on-device helper restarts only configured runit
services: odin-git-sync, odin-task-worker, odin-github-bridge (if
configured), then odin-private-relay last. The standalone Stage 5
HTTP server, sshd, ssh-agent and unrelated services are excluded.
Requests are rate-limited to once every 10 minutes.

The phone first shows delivery/read confirmation, not success.
The helper checks post-restart running status. Only after the
relay reconnects does it deliver a private
ODIN_SERVICES_RESTART_RESULT verified=true|false response.
An interrupted helper yields verified=false after five minutes.

First installation limitation: the auto-updater may pull new
source without reloading the old running Python relay. Until
the new odin-private-relay process is activated once, this
new command cannot work. After a CI-passing fast-forward,
one initial Termux service restart is needed; subsequent
restarts can be initiated from the authenticated UI.

To restart only one service, send `/restart-service odin-task-worker` in
the authenticated inbox and confirm the named target. The target must be
one of the four supervised Odin services listed above. Single-service and
all-service requests share the existing cooldown and durable result path.

### Request-driven device wake-up

Set a private TLS Redis connection in the Vercel environment as
`ODIN_WAKE_REDIS_URL`. The Redis account needs LPUSH, LTRIM, EXPIRE, MULTI,
EXEC and BLPOP on `odin:wake:v1:*`. Both the publisher and waiting endpoint
use the same database. For requests written directly to the GitHub mailbox
and completed release checks, configure the repository webhook for Push and
Workflow runs, JSON delivery to `https://odin-control.vercel.app/api/wake`,
and a matching random secret (32 characters or more) in
`ODIN_WAKE_WEBHOOK_SECRET`. Redeploy after setting environment variables.
The updated Git sync run script must also be active for release wake-ups.

The signal contains only a lane name and a constant marker. The bridge still
validates each queued request and sends its usual matching device receipt.
One connected listener per lane uses a blocking Redis connection for up to
20 seconds per HTTP request. Check the hosting and Redis usage allowance
before enabling. If the transport or network is unavailable the ordinary
relay, diagnostic and sync checks continue. Android must allow Termux to run.
To accept the rollout, send one private ping and one GitHub mailbox ping,
compare each new ID and device receipt timestamp, then repeat after reconnect.

### Hosted device inference check

Use **Chat → Odin Device Inbox → Verify Odin GPT** in a paired session. The UI sends the fixed `/ai-proof` request over the private relay and refreshes the inbox for the matching device reply. This requires the upgraded relay client, working private storage and the on-device private probe credential. Both device entry points share one attempt journal and budget.
