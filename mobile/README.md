# Odin AI Control — iPhone hosted dashboard

iPhone-first installable web dashboard backed by **sanitized public** Odin GitHub telemetry. It uses no credentials and has no write controls or unrestricted CLI route.

## Live data

- `/api/status`: read-only Vercel function that retrieves the last 12 request and response records from the public `odin-bridge-inbox` / `odin-bridge-outbox` branches. Status values are schema-filtered and cannot include arbitrary logs or private messages.
- The main GitHub revision and recent Actions results are retrieved live.
- Workflow steps clearly distinguish GitHub submission, Odin receipts, exact revision verification, and remaining private conversation pairing.
- Device state is a *last-reported observation*, not an assertion about continuous background availability. UI refreshes once per minute while visible.
- ChatGPT in-app conversation is **not connected**: this dashboard never impersonates a ChatGPT session, and does not publish chat, API credentials, private keys or prompts into GitHub.

## Source and deployment

The Vercel Git project should use the existing public GitHub repository `shawnfra2013/Oden2-` with **Root Directory: `mobile`**. The repository's `main` is the canonical source of truth, not this app's deployment. The Vercel endpoint exposes public status data only. Do not add OPENAI_API_KEY or Github write tokens to this dashboard.

From iPhone Safari, open the deployed URL and choose Share → Add to Home Screen to install as a standalone icon.

## Future private conversation and approved CLI controls

Not yet enabled. Future work requires a private authenticated transport; the public GitHub mailbox is unsuitable for chat content. Device actions must require scoped allowlists, explicit approval for mutations, tamper-evident receipts, and rollback checks. Until then UI presents request/response visibility and waiting states only.
