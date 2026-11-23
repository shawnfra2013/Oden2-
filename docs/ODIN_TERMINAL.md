# Odin Terminal — colorful read-only CLI

Issue [#148](https://github.com/shawnfra2013/Oden2-/issues/148). **Source-only until an approved physical checkout update.**

The terminal displays local source SHA, runit service state and PID, the *canonical mailbox launcher and process cwd* check, task queue counts, local metadata trace, public GitHub exact-main CI and recent public issue/PR activity. Public GitHub status does not prove installation or agent action. Private messages and credentials are never fetched or displayed.

After approved source installation into the canonical checkout:

```sh
cd ~/odin-workspace
python -B -m scripts.odin_terminal --issue 71
python -B -m scripts.odin_terminal --watch --issue 71
```

`--offline` avoids all network calls. `--theme neon`, `--theme ocean`, and `--theme ember` select colors; `--plain`, `--theme mono` and `NO_COLOR=1` disable them. `--json` outputs a script-friendly snapshot. Live watch refreshes local status every five seconds and public GitHub no more often than once every 300 seconds, and exits with Ctrl+C. This is not an always-connected ChatGPT terminal or a streaming transcript of ChatGPT tool calls.

Optional source-side `bin/odin` supports `status`, `watch`, `chat`, and `preflight`; it does not install itself or replace an existing `odin` or `ai` alias. Do not change Termux themes, local shell startup, or running services without reviewing existing configuration and obtaining operator approval.

**Acceptance:** exact-SHA CI, on-device Termux terminal rendering, canonical mailbox cwd and fresh private receipt, no leaking private content, offline transition, and measured overhead. Issue [#71](https://github.com/shawnfra2013/Oden2-/issues/71) retains the separate migration gate.
