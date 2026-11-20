# Offline development on Odin

The Stage 5 browser and the Odin CLI can use a local OpenAI-compatible chat server. The local adapter connects exclusively to 127.0.0.1. It supports an explicitly named model, bounded history and a maximum of 700 generated tokens. It never reads a cloud API key. The model server and its weights must already be available on Odin for offline use.

Set ODIN_STAGE5_ENABLE_AI=1, ODIN_STAGE5_PROVIDER=local, ODIN_LOCAL_MODEL to the model ID served by the runtime, and ODIN_LOCAL_PORT to its port (default 8080) in the environment of each consumer. Open Stage 5 on Odin at http://127.0.0.1:8765. It persists completed conversations in local SQLite. Programmer assistance generates text. Review edits and run project tests before applying them.

## One-time Termux installation

From the synchronized main checkout run `bash scripts/odin-install-offline.sh` on Wi-Fi. It installs the Termux llama-cpp package if needed, downloads the official Qwen 2.5 Coder 3B Instruct Q4_K_M file (2.10 GB), validates its SHA-256, and enrolls a local runit service on port 18080 with a 2,048-token context and one CPU inference slot. A successful expression-repair test activates the local-only profile for Stage 5, its CLI and encrypted chat, and blocks the private paid diagnostic. The hosted cloud route requires an explicitly positive ODIN_CLOUD_CHAT_DAILY_LIMIT on the host. For zero paid turns, set that value to 0 if previously configured.

After READY, open http://127.0.0.1:8765 on Odin. Turn Wi-Fi off and repeat `python -B scripts/odin-offline-check.py` to verify the device while disconnected. In the UI send a new question and check the on-device provider label. To stop inference use `sv down "$PREFIX/var/service/odin-local-model"`. Keeping the offline profile selected prevents cloud fallback.

## Encrypted phone mailbox

When online, the mobile Chat tab can submit a single question to the same local model. This panel requires a trusted HTTPS UI host, existing private authentication, ODIN_CONTROL_ORIGIN set to that exact origin and a server-side ODIN_PRIVATE_MAILBOX_TOKEN scoped to repository contents in the private bridge. Account sign-in on github.com does not authenticate this separate UI host.

On Odin, the mailbox process needs Python cryptography, the local model settings above and a reachable local model server. Run python scripts/odin_encrypted_chat.py pair in a trusted Odin terminal. Enter its code once in the browser pairing field. Each paired browser holds a nonextractable AES key in IndexedDB. Clearing site data removes the browser pairing. Keep the pairing code out of Git, messages and screenshots. All browsers paired with this device key can decrypt messages from its history if they have the ciphertext. To revoke the shared key, replace it on Odin and re-pair trusted browsers. The host serving the browser code must be trusted.

The browser encrypts the question and Odin encrypts its answer, binding both to the request ID and direction. GitHub stores ciphertext and routing metadata. The browser saves pending ciphertext for retries. Dismissing a pending receipt only clears the local pointer and cannot cancel a submitted request. GitHub delivery needs internet. Offline operation uses the browser or CLI on Odin itself.

## Verification

The browser acceptance workflow runs Chromium with the real UI, WebCrypto, device decryption and local HTTP adapter. Model output and mailbox HTTP transport use deterministic fixtures. The Node tests exercise the authenticated API handler with a simulated GitHub service including retries and pending receipts. On-device acceptance requires measured memory and disk, installed model weights, and a real coding task with Wi-Fi off. Hosted acceptance also requires pairing and a decrypted reply on the chosen UI deployment.

The private mailbox supports a fixed install_offline_model request carrying the exact reviewed source SHA. Both the running mailbox and canonical checkout must match that revision and have clean tracked files. The job runs the repository installer, records its result locally and returns a receipt. Re-reading a claimed request never starts the job again. During installation the private poller waits for completion. Public health checks remain available independently.

On the local Stage 5 Chat screen, open Project note to paste or import a small text or Markdown excerpt. Save keeps the note in that browser. Select Include to use it on a local request. Short reply caps output at 128 tokens. The elapsed time covers the model request. For upcoming work and its stop conditions, see [Local coding roadmap](LOCAL_CODING_ROADMAP.md).

Open **Look up Odin code** to find an exact Python function in the committed Stage 5, scripts or agent modules. Try `local_settings`. Selecting a result previews its path, line, revision and excerpt in the project note. Review it and send one question. Lookup alone runs no model and makes no edits. The private `stage5_source_check` action tests one fixed question through the local UI API and returns the source revision, match and elapsed time.

## Browser voice and references

In local Stage 5 or the hosted encrypted chat, open **Voice and webpage excerpts**. Read reply aloud selects an installed voice reported as local. Dictate locally requires a browser with on-device recognition and an installed language pack. Review the draft and press Send. The browser reports when either feature is unavailable. Test actual microphone input and speaker output on each device.

**Clip for Odin** is a bookmark for the page you are reading. Activate it on a page to preview up to 1,200 characters of selected text or article text. Copy the excerpt into the chat draft. The bookmark reads on activation and sends no network request. Browsers that restrict bookmark scripts can use ordinary text selection. The hosted encrypted panel also accepts one selected UTF-8 text file of up to 1,600 bytes into the draft. Only Send submits the reviewed text.

## Supervised coding and model adaptation

The private mailbox action `stage5_coding_review` asks the local model for one Python expression for counting UTF-8 bytes. It compares syntax against known expressions without executing the reply. The private receipt contains the proposed expression for review. A match records performance on this specific task. The action has no repository editing or push step.

Keep evaluated tasks separate from training examples. Collect owner-approved examples and corrections, reserve unseen tasks, then train a candidate LoRA adapter on compatible hardware using the matching upstream base. Compare the adapter with the installed baseline on the same unseen tasks before approving it for device use. No automatic training job is configured.
