# Verified one-request ping result

The existing private GitHub [mailbox workflow](https://github.com/shawnfra2013/Odin-private-bridge/actions/workflows/odin-private-mailbox.yml) already supplies a single manual `ping`. ChatGPT can also submit an allowlisted request through its authenticated GitHub connection. Neither method grants a shell.

`scripts/odin_ping_verifier.py` independently evaluates a **local copy** of one private request and its matching reply; it never fetches GitHub data or calls Odin. Save private JSON only in authorized private storage and do not upload it to the public repository. Example:

```sh
python -B scripts/odin_ping_verifier.py --request /private/request.json --receipt /private/response.json
```

For a missing response, omit `--receipt`; it reports UNVERIFIED. A PASS requires matching IDs/actions, `complete`, `alive=true`, coherent UTC times and a response within five minutes of the observation. A result does **not** prove which code is installed. To diagnose an absent private receipt, use [the canonical mailbox runbook](ODIN_GITHUB_BRIDGE.md) and issue #71; never resubmit flooded pings or migrate services without operator approval.
