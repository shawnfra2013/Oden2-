# Odin 2 system architecture

| Component | Runtime |
| --- | --- |
| Odin web app | Termux runit service `odin-stage5`, serving `127.0.0.1:8765` and the enrolled iPhone through Tailscale on port `8766` |
| Model | Termux `odin-local-model` on loopback port `18080` |
| Conversation store | SQLite on Odin. The browser keeps its active conversation ID for the current tab. |
| Controller bindings | Browser-local settings on the handheld |
| GitHub mailbox | Bounded private diagnostic actions and receipts. Public receipts contain sanitized status. |
| Git sync | Five-minute timer, with optional CI-gated source updates after explicit enrollment |

Odin serves the page, status, chat, and confirmed service restart controls from the same origin on each device. The phone listener uses a configured Tailscale address and an exact iPhone peer address. Both listeners share the same model request lock and conversation store. The phone does not need a token entered at refresh. The web app uses the local model and stops chat when it is unavailable.

The task worker remains independent of the web app. Odin keeps conversations and credentials on the device. Approved appearance changes go to a GitHub review branch through the existing sync mechanism. The appearance JSON still uses its original tracked path so previously queued edits can upload.

GitHub `main` is the source authority. CI validates a source revision. A separate device receipt confirms the checked-out SHA and service state. An actual iPhone request over cellular establishes private phone access. Android process supervision and unattended reboot are separate acceptance checks.

See [phone enrollment and cutover](ODIN_PHONE_ACCESS.md), [offline model setup](OFFLINE_CHAT.md), [GitHub diagnostics](ODIN_GITHUB_BRIDGE.md), and [source updates](ODIN_SAFE_UPDATES_AND_ROADMAP.md).
