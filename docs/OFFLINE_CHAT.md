# Offline development on Odin

The Odin web app and the Odin CLI can use a local OpenAI-compatible chat server. The local adapter connects exclusively to 127.0.0.1. It supports an explicitly named model, bounded history and a maximum of 700 generated tokens. It never reads a cloud API key. The model server and its weights must already be available on Odin for offline use.

Set ODIN_STAGE5_ENABLE_AI=1, ODIN_STAGE5_PROVIDER=local, ODIN_LOCAL_MODEL to the model ID served by the runtime, and ODIN_LOCAL_PORT to its port (default 8080) in the environment of each consumer. Open the web app on Odin at http://127.0.0.1:8765. It persists completed conversations in local SQLite. Programmer assistance generates text. Review edits and run project tests before applying them.

## One-time Termux installation

From the synchronized main checkout run `bash scripts/odin-install-offline.sh` on Wi-Fi. It installs the Termux llama-cpp package if needed, downloads the official Qwen 2.5 Coder 3B Instruct Q4_K_M file (2.10 GB), validates its SHA-256, and enrolls a local runit service on port 18080 with a 2,048-token context and one CPU inference slot. A successful expression-repair test activates the local-only profile for the web app and CLI, and blocks the private paid diagnostic.

After READY, open http://127.0.0.1:8765 on Odin. Turn Wi-Fi off and repeat `python -B scripts/odin-offline-check.py` to verify the device while disconnected. In the UI send a new question and check the on-device provider label. To stop inference use `sv down "$PREFIX/var/service/odin-local-model"`. Phone setup is in [Odin on iPhone](ODIN_PHONE_ACCESS.md).

## Verification

On-device acceptance uses a real coding question with Wi-Fi off. Phone acceptance uses the same local model, with the iPhone connected through Tailscale on cellular.

The private mailbox supports a fixed install_offline_model request carrying the exact reviewed source SHA. Both the running mailbox and canonical checkout must match that revision and have clean tracked files. The job runs the repository installer, records its result locally and returns a receipt. Re-reading a claimed request never starts the job again. During installation the private poller waits for completion. Public health checks remain available independently.

On the local web app Chat screen, open Project note to paste or import a small text or Markdown excerpt. Save keeps the note in that browser. Select Include to use it on a local request. Short reply caps output at 128 tokens. The elapsed time covers the model request. For upcoming work and its stop conditions, see [Local coding roadmap](LOCAL_CODING_ROADMAP.md).

Open **Look up Odin code** to find an exact Python function in the committed Stage 5, scripts or agent modules. Try `local_settings`. Selecting a result previews its path, line, revision and excerpt in the project note. Review it and send one question. Lookup alone runs no model and makes no edits. The private `stage5_source_check` action tests one fixed question through the local UI API and returns the source revision, match and elapsed time.

## Browser voice and references

In the web app, open **Voice and webpage excerpts**. Read reply aloud selects an installed voice reported as local. Dictate locally requires a browser with on-device recognition and an installed language pack. Review the draft and press Send. The browser reports when either feature is unavailable. Test actual microphone input and speaker output on each device.

**Clip for Odin** is a bookmark for the page you are reading. Activate it on a page to preview up to 1,200 characters of selected text or article text. Copy the excerpt into the chat draft. The bookmark reads on activation and sends no network request. Browsers that restrict bookmark scripts can use ordinary text selection. Only Send submits the reviewed text.

## Supervised coding and model adaptation

The private mailbox action `stage5_coding_review` asks the local model for one Python expression for counting UTF-8 bytes. It compares syntax against known expressions without executing the reply. The private receipt contains the proposed expression for review. A match records performance on this specific task. The action has no repository editing or push step.

Keep evaluated tasks separate from training examples. Collect owner-approved examples and corrections, reserve unseen tasks, then train a candidate LoRA adapter on compatible hardware using the matching upstream base. Compare the adapter with the installed baseline on the same unseen tasks before approving it for device use. No automatic training job is configured.

For isolated adapter training and held-out evaluation, see [Offline candidate adapter training](TRAINING.md).

## Offline UI edits and reconnect uploads

On the handheld open **Tasks → Edit the web UI offline**. Preview a chat heading, heading accent or chat text size. Suggest locally uses one bounded on-device chat request. You can type a heading directly without inference. The approval button explicitly queues these three public settings for the source repository. Approval creates a local Git commit with a separate index; it survives a service restart and a browser reload. A stale edit requires a fresh preview. Ordinary chat text and the model prompt are outside the uploaded file.

The existing sync service retries pending commits and confirms each remote SHA before clearing its queue entry. The review branch is named `odin-ui/edit-<commit prefix>`. The web app uses the approved local edit immediately. Once the review branch merges, other Odin checkouts can pick it up through source sync. Use **Reload saved edit and status** to check progress.

## Handheld controls

In the web app open **System → Device buttons**. Pick an action, choose Assign next press and press a keyboard key or a controller button. Bindings are stored in this browser on this device. Assign again to replace one or use Remove assignment. While the local UI is focused, shortcuts open chat, the notebook or the offline UI editor. A held gamepad button triggers once per press. Typing in a field keeps ordinary keys available for text entry. Android system keys, OS-wide remapping, and buttons intercepted by device firmware are outside this browser interface.
