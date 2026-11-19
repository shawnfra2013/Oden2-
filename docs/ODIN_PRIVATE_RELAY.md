# Odin private message relay — phone ↔ device

The protected Odin Control iPhone app now includes a private device inbox
that can show message content, receipts and replies. This is **not** the public
GitHub diagnostic mailbox, and it is **not a direct connection to the current
ChatGPT app thread**. Messages from this thread cannot arrive automatically
without an additional ChatGPT integration.

## Architecture and security

- The existing Vercel project `odin-control` hosts `/api/relay`.
- Conversation content is stored in **private Vercel Blob storage**, never
  in public `odin-bridge-inbox` or `odin-bridge-outbox`.
- The private server-side store was provisioned for the existing project.
  Its environment configuration stays in Vercel, not GitHub.
- The phone needs the existing `ODIN_CONTROL_ACCESS_TOKEN` through the
  authenticated UI. The device uses a separate
  `ODIN_DEVICE_RELAY_TOKEN` configured in Vercel and installed privately
  in Termux at `state/odin-relay/token` (mode 0600).
- No token value belongs in source code, GitHub issues, this ChatGPT thread,
  screenshots, browser URL parameters, or a public log.
- Device-to-phone messages, device acknowledgments and phone read receipts
  use HTTPS with distinct authentication, and the server keeps a bounded
  private conversation journal. Messages are held in the store until
  displaced by newer events; old messages are not a durable backup.
- The phone polls approximately every 15 seconds while the app is open.
  The Odin client polls approximately every 45 seconds while running.
  Neither iOS push notifications nor wake-ups of an inactive ChatGPT thread
  are implemented.

## One-time pairing prerequisites

1. In Vercel, open **odin-control → Settings → Environment Variables**.
   Use a fresh unique 32+ character random value for
   `ODIN_DEVICE_RELAY_TOKEN` with target Production. Don't share it publicly.
2. Retrieve the same value securely and enter it on the Odin's Termux
   terminal without shell history. After updating the Odin checkout,
   execute:

```bash
cd ~/odin-workspace || exit 1
mkdir -p state/odin-relay
chmod 700 state/odin-relay
umask 077
read -rsp 'Private relay token: ' ODIN_RELAY_DEVICE_SECRET; echo
printf '%s\n' "$ODIN_RELAY_DEVICE_SECRET" > state/odin-relay/token
chmod 600 state/odin-relay/token
unset ODIN_RELAY_DEVICE_SECRET
python -B scripts/odin_relay_client.py --once
```

3. Enable the model provider in the local service environment. The relay
   calls `scripts/odin_chat.py`, which uses the existing local SQLite
   history and selected cloud model API. It **does not** execute returned
   code, run arbitrary shell commands, or perform unattended deployments.
4. Start `python -B scripts/odin_relay_client.py --serve` under a suitable
   existing process supervisor once one-shot pairing and inference work.
   Android battery/process management may stop background processes.

### Delivery status meanings

- `queued`: message saved in private relay; no device receipt yet.
- `delivered`: Odin poller received it.
- `read`: Odin began processing it, or the iPhone displayed a device reply.
- `replied`: a response to that message is stored.
- `failed`: Odin reported an inability to produce a model answer.

A receipt is evidence of software processing, not that a human read a
message or that a suggested command actually ran.

### Current limitation

ChatGPT can **currently** send GitHub diagnostic requests and inspect
their receipts during an active chat. It cannot autonomously subscribe
to `/api/relay`, wake a paused conversation, or become the exact same
OpenAI API session that runs in the app. The iPhone cloud AI route is a
separate OpenAI API conversation and should not be labeled as replies
from this ChatGPT app thread.
