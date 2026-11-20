# Offline development on Odin

The Stage 5 browser and the Odin CLI can use a local OpenAI-compatible chat server. The local adapter connects exclusively to 127.0.0.1. It supports an explicitly named model, bounded history and a maximum of 700 generated tokens. It never reads a cloud API key. The model server and its weights must already be available on Odin for offline use.

Set ODIN_STAGE5_ENABLE_AI=1, ODIN_STAGE5_PROVIDER=local, ODIN_LOCAL_MODEL to the model ID served by the runtime, and ODIN_LOCAL_PORT to its port (default 8080) in the environment of each consumer. Open Stage 5 on Odin at http://127.0.0.1:8765. It persists completed conversations in local SQLite. Programmer assistance generates text. Review edits and run project tests before applying them.

## Encrypted phone mailbox

When online, the mobile Chat tab can submit a single question to the same local model. This panel requires a trusted HTTPS UI host, existing private authentication, ODIN_CONTROL_ORIGIN set to that exact origin and a server-side ODIN_PRIVATE_MAILBOX_TOKEN scoped to repository contents in the private bridge. Account sign-in on github.com does not authenticate this separate UI host.

On Odin, the mailbox process needs Python cryptography, the local model settings above and a reachable local model server. Run python scripts/odin_encrypted_chat.py pair in a trusted Odin terminal. Enter its code once in the browser pairing field. Each paired browser holds a nonextractable AES key in IndexedDB. Clearing site data removes the browser pairing. Keep the pairing code out of Git, messages and screenshots. All browsers paired with this device key can decrypt messages from its history if they have the ciphertext. To revoke the shared key, replace it on Odin and re-pair trusted browsers. The host serving the browser code must be trusted.

The browser encrypts the question and Odin encrypts its answer, binding both to the request ID and direction. GitHub stores ciphertext and routing metadata. The browser saves pending ciphertext for retries. Dismissing a pending receipt only clears the local pointer and cannot cancel a submitted request. GitHub delivery needs internet. Offline operation uses the browser or CLI on Odin itself.

## Verification

The browser acceptance workflow runs Chromium with the real UI, WebCrypto, device decryption and local HTTP adapter. Model output and mailbox HTTP transport use deterministic fixtures. The Node tests exercise the authenticated API handler with a simulated GitHub service including retries and pending receipts. On-device acceptance requires measured memory and disk, installed model weights, and a real coding task with Wi-Fi off. Hosted acceptance also requires pairing and a decrypted reply on the chosen UI deployment.
