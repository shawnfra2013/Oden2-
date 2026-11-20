# Odin 2 / Termux system architecture

Current device transport and November 20 verification are documented in [the private GitHub mailbox runbook](ODIN_GITHUB_BRIDGE.md). Use that mailbox for device checks.


For the November 20 on-device OpenAI result and fixed private mailbox inference diagnostic, see [the private probe runbook](ODIN_GITHUB_BRIDGE.md#private-inference-probe). The physical mailbox inference check passed on November 20.

Updated: 2026-11-19. This describes the files **actually present** in the
GitHub source tree. Dated checkpoints are kept in `docs/PROJECT_MEMORY.md`.
GitHub CI passing does not mean an Odin device has updated, restarted, or
completed a real messaging round-trip.

## Source-of-truth and modules

| Module | Responsibilities | Entrypoints |
| --- | --- | --- |
| `ai/agent/` | Stage 4 bounded hosted inference, proposals, acceptance and evidence | `orchestrator.py`, `pipeline.py`, `proposal_builder.py` |
| `scripts/odin_worker.py` | Local supervised worker and task queue | Existing `odin-task-worker` runit service |
| `stage5/` | Localhost HTTP browser AI, provider selection, SQLite conversation store | `server.py`, `chat_provider.py`, `conversation_store.py` |
| `scripts/odin_chat.py` | Termux interactive CLI with persistent local conversations | `python -B scripts/odin_chat.py` |
| `scripts/odin_github_bridge.py` | Public **sanitized** diagnostic requests/receipts on dedicated GitHub inbox/outbox branches | Existing runit `odin-github-bridge` (when enabled) |
| `scripts/odin_relay_client.py` | Private phone ↔ Odin message polling, local-model reply and acknowledgment | Existing `odin-private-relay` runit service (when enabled) |
| `mobile/` | iPhone web UI, Vercel API routes, private authentication, status timeline | `index.html`, `app.js`, `api/`, `lib/` |
| `mobile/lib/relay.js` | Bounded read view over immutable private Blob events, retaining legacy journal read-only | `mobile/api/relay.js` |
| `scripts/git-sync.sh` | Existing supervised Git fetch/push loop with optional CI-gated safe source pull | `services/git-sync/run` and device's `odin-git-sync` service |
| `scripts/odin-safe-pull.sh` | Guarded fast-forward-only update protecting tracked and untracked files and optional exact SHA pin | Manual use or opt-in updater |
| `scripts/odin_auto_update.py` | Exact-GitHub-CI-gated source update, private status/enable flag, no automatic restarts | Invoked by existing Git-sync loop when opted in |
| `.github/workflows/odin-checks.yml` | Python, shell, Node, secret-pattern and regression CI gates | GitHub Actions |
| `tests/`, `mobile/tests/`, `stage5/test_*.py` | Offline regression tests; production routes still require live verification | CI and local runs |

## Communication boundaries

1. **iPhone monitoring** reads public, bounded and sanitized GitHub telemetry.
2. **iPhone private device messaging** authenticates via `ODIN_CONTROL_ACCESS_TOKEN`;
   Vercel `/api/relay` stores messages in a *private* Blob store.
3. The Termux relay polls with a different `ODIN_DEVICE_RELAY_TOKEN`;
   `queued`, `delivered`, `read`, and `replied` mean distinct observed events.
   Configured tokens do **not** establish continuous device availability.
4. The cloud AI chat API is a separate OpenAI API conversation, not this
   ChatGPT app's exact thread. It requires a separately provided server-side
   `OPENAI_API_KEY`. No private prompts are sent through the public mailbox.
5. GitHub diagnostic writes require a separate fine-grained server token;
   actions are allowlisted. No arbitrary command execution is enabled.
6. Android Termux process lifetimes and startup after reboot are not
   guaranteed by runit; boot automation was explicitly deferred.

## Release and update policy

- GitHub `main` is the **source** authority. A GitHub green CI run is
  a code check, not proof of live device state.
- Deploy `mobile/` to the **existing** Vercel project `odin-control`.
  The team has no GitHub integration attached to that project; manual
  source-file deployment remains necessary and must be verified.
- The existing `git-sync` may now invoke `scripts/odin_auto_update.py`
  **only after** the device owner enables its private state flag. It checks
  successful GitHub push CI on the exact main SHA, then uses
  `scripts/odin-safe-pull.sh` pinned to that SHA. The default is off and
  unsafe updates stop; no resets or unreviewed merges. See
  `docs/ODIN_SAFE_UPDATES_AND_ROADMAP.md`.
- Source changes do not automatically restart already-running Python
  services. Verify the running revision and separately approve restart.
- Do not check in `state/`, service secrets, private conversation text,
  local SQLite databases or API keys.
- On failures: surface the stage in the UI, record only sanitized failure
  metadata in Vercel logs, and keep existing state intact. See
  `docs/ODIN_PRIVATE_RELAY.md` for the live `/ping` check.

## Remaining acceptance gaps (as of this update)

A corrected relay API handler was tested in CI and redeployed, but a fresh
authenticated iPhone → Odin → iPhone `/ping` receipt has not yet been
independently observed on that deployed revision. Opt-in CI-gated
source updates have code support but require device activation; automatic
service restarts, full ChatGPT thread synchronization, robust iOS push
notifications, and reboot persistence remain **unimplemented**.
