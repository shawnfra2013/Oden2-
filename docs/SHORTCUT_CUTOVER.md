# Odin iPhone shortcut cutover — current instructions

The supported architecture is described in [Odin runtime](ODIN_RUNTIME.md). **The app's current accessible HTTPS viewer address has not yet been verified.** Do not insert a guessed hostname, redirect a private token, or claim the old Home Screen icon has updated.

## Two different destinations

- **Working private device diagnostics:** [GitHub private mailbox workflow](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml). This opens with GitHub authentication. It can request and display matched Odin receipts but is **not** the full Odin iPhone dashboard.
- **Full iPhone viewer:** the separate `mobile/` app, served from an operator-approved HTTPS origin once the private route is configured and tested. The site uses its own browser approval and encrypted chat pairing.

## Replace persistent old links only after a verified new origin

1. Find any saved viewer text file, Safari bookmark, Home Screen web clip, and iOS Shortcut that opens the earlier dashboard. **Updating GitHub code, starting a new chat, or refreshing an old site does not edit these items on the iPhone.**
2. Until a new HTTPS origin passes [private-network verification](https://github.com/shawnfra2013/Oden2-/issues/70), do not label the old address as the current viewer. Use the private GitHub workflow above for device checks.
3. After the newly configured HTTPS origin is verified, replace the exact website URL in every saved text/Shortcut action. Create a fresh Home Screen shortcut from the new origin in Safari. Do not reuse an old origin's browser token, cookie, vault, or pairing as proof that access migrated.
4. With iPhone Wi-Fi **off** and cellular data **on**, verify loading, refresh, the installed release identifier, automatic browser approval or a deliberately saved unlock, and one real encrypted chat request with a matching device receipt.
5. Record the approved origin privately, the exact deployed Git SHA, test timestamp, and pass/fail evidence in [issue #69](https://github.com/shawnfra2013/Oden2-/issues/69). Never put passwords, tokens, pairing codes, private IPs, or private conversation content in an issue.

**Done means** the old shortcuts no longer open the obsolete destination and the new approved viewer passed the real cellular test. GitHub checks and local fixtures cannot establish this without the devices.
