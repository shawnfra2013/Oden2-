# Odin portable development shell (online Codespaces / offline Termux)

**Current scope:** Run source code and tests in a terminal. The same Python entrypoint runs in GitHub Codespaces when online or on Odin in Termux while offline, provided its tools and dependencies are already installed. This is not a remote Termux shell, device deployment, model endpoint, or private receipt bridge.

## Use now (no editor installation)
**Delegation boundary:** [Working with Odin](WORK_WITH_ODIN.md) assigns GitHub Actions routine deterministic CI; ChatGPT coordinates approved issues and reviews. A separately authorized, **actually running and attached** coding agent in Codespaces can implement and test scoped changes, then publish a source PR. A GitHub API connection or CI check cannot conjure a Codespaces shell or make that cloud workspace execute Termux device commands. The cost and idle-time controls below still apply. The physical device has its own private mailbox and local agent acceptance gates.


- Online: open the GitHub repository in a **manually started GitHub Codespace**, open its terminal, and run the commands below. A Codespace uses cloud compute and **does not run offline**. GitHub account usage, storage, and idle-time charges/limits remain the owner's controls.
- Offline: open **Termux on Odin** in the checked-out `~/odin-workspace` repository. Run the same commands. Editing and tests can continue without internet, and Git pushes wait until connectivity returns.
- A standalone editor integration is deliberately **deferred**. This workflow does not require adding an editor to the handheld.

```sh
cd ~/odin-workspace       # On Odin; Codespaces terminal is already in the repository
python -B scripts/odin_codespace.py status
python -B scripts/odin_codespace.py test
```

**Requirements:** Python 3.13+ recommended; Node.js 22 for mobile tests; Ruff available as `ruff` or `.venv/bin/ruff`; and project dependencies already installed (`npm ci --prefix mobile --no-audit --no-fund --ignore-scripts` once when online). The Codespaces dev container automatically prepares a local Python virtual environment with Ruff 0.14.5 and installs the mobile dependencies **after you manually start the Codespace**. This does not start any model or device service. For a Termux checkout, install the tools yourself while connected before offline work. An offline run with a missing tool fails explicitly rather than pretending the test passed.

The source test loop runs active-doc checks, source structure checks, Python tests, local workstation tests, mobile Node tests, Ruff, and source preflight. Its JSON receipt is written under `state/codespace-receipts/`, ignored by the **public** Git repository. It includes the local source SHA, test results, timing, and a unique ID; **it is not proof of device operation or phone connectivity**.

**Offline-to-private receipt sync on Odin:** When this revision is installed and the existing `odin-private-mailbox` service is restarted with owner approval, that service reads receipts from the canonical `~/odin-workspace/state/codespace-receipts/` queue. Once internet returns it submits validated summaries to the **private** GitHub repository's `odin-bridge-outbox` branch under `bridge/local-source-receipts/<id>.json`. It preserves local originals, ignores malformed or symlinked files, caps uploads at three per poll, retries interrupted commits/pushes, and rejects conflicting IDs. A private `ping` may report `last_source_receipt_push` with the latest successful upload time. This is not a device-health receipt and is separate from private request/response IDs.

**Codespaces:** Cloud-generated receipts stay local to the Codespace; its GitHub Actions source checks provide durable cloud evidence. No Codespace is granted access to the handheld's private mailbox key or allowed to impersonate Odin. Running the source CLI does not automatically push source changes to GitHub. Approved source changes still require Git commits, PR review and CI.

## Existing receipt and release process

The separate [private mailbox](ODIN_GITHUB_BRIDGE.md) remains the approved asynchronous path to the handheld. Do not copy local terminal output or credentials into public source receipts. A GitHub source PR and CI report are verified against the exact head SHA. Only approved device operations go through the existing authenticated private workflow; a comment or source receipt must never be interpreted as authorization for arbitrary shell execution.

For a reviewed source change: local tests → scoped PR → GitHub CI → review → merge → exact-main-SHA release gate → operator-approved install on Odin → new matching private device receipt → phone acceptance test as applicable. An offline local commit stays local until network access returns.

**No automatic cloud workspace starts, free-tier assumptions, paid inference, host changes, Tailscale changes, service restarts, or physical deployments are part of this source runner.** See [runtime truth](ODIN_RUNTIME.md) and [release gates](RELEASE_GATES.md).
