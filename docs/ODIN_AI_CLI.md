# Talk to Odin AI from Termux and Stage 5

## What this actually connects

`python -B scripts/odin_chat.py` opens a conversational AI assistant
**inside the Odin Termux CLI**. Stage 5's existing browser interface uses
the same provider selection and local conversation store.

This is an **independent model/API conversation**, not the live ChatGPT app
thread. The current ChatGPT conversation cannot receive messages from this
CLI without a separately authorized application integration. ChatGPT may
still poll and read **sanitized diagnostic receipts** through the proven
GitHub mailbox bridge, but that public mailbox must not carry private chat.

## Current default: Groq

Odin's existing Groq backend remains the default. Once
`GROQ_API_KEY` is available in your local Termux environment, enable the
model for this invocation (do not paste keys into GitHub or chat):

```bash
cd ~/odin-workspace || exit 1
ODIN_STAGE5_ENABLE_AI=1 ODIN_STAGE5_PROVIDER=groq python -B scripts/odin_chat.py
```

This path uses the existing bounded Groq orchestrator; it does not
install a new provider or change running services. Groq network access,
a valid key, and the chosen model's availability are required.

## Optional: ChatGPT-style model using the OpenAI API

The OpenAI backend uses the documented **Responses API** at
`https://api.openai.com/v1/responses`. It is opt-in and **disabled by
default**. It is not covered automatically by a ChatGPT app subscription;
API usage can incur separate charges. Select and verify an API model name
you have access to. No model name or credential is hardcoded.

1. Create an OpenAI Platform API key through the authorized key-setup
   interface. Never paste the key into a conversation, code repository,
   screen recording, or command history.
2. Put the key in your local environment, using a secure secrets workflow.
   The app requires `OPENAI_API_KEY`, `ODIN_OPENAI_MODEL`, and
   `ODIN_STAGE5_ENABLE_AI=1`. Set `ODIN_STAGE5_PROVIDER=openai` to
   select it. **No bridge request can change these variables.**
3. From Termux, with the local environment already configured:

```bash
cd ~/odin-workspace || exit 1
ODIN_STAGE5_ENABLE_AI=1 ODIN_STAGE5_PROVIDER=openai python -B scripts/odin_chat.py
```

The provider sends at most 12 recent messages with bounded contents and
one new user request to OpenAI's HTTPS endpoint, with `store: false`.
Responses are capped in size, a 40-second request timeout is enforced,
and API keys are never included in GitHub receipt data. Local SQLite
contains the completed conversation history and remains under ignored
`state/`. Network/provider error details are deliberately not echoed.

For either provider, type a question after `You:` and see the model
reply at `Odin:`. Available CLI commands are `:new`, `:status`,
and `:quit`. The last conversation ID is preserved locally in
`state/odin-chat-cli/conversation_id`; SQLite retains older turns.

For a single interaction (not background mode):

```bash
ODIN_STAGE5_ENABLE_AI=1 python -B scripts/odin_chat.py --once "Summarize our Odin project status"
```

## Development and safety boundaries

- Neither chat provider can execute shell commands or approve deployments.
- Live GitHub-bridge diagnostics remain separate from conversation storage.
- A model's suggested terminal commands are unverified advice, not receipts.
- Stage 4 background worker, existing Git sync and Stage 5 server are not
  restarted or reconfigured by this change.
- API execution is not offline inference: Odin must have network access to
  the selected model provider.
- For the closest possible workflow, use the live ChatGPT conversation for
  approved GitHub writes and the Odin CLI for local conversations. Project
  source of truth is GitHub, not model memory or an unsynced transcript.
