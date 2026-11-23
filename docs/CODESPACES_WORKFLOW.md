# Odin portable development shell (online Codespaces / offline Termux)

**Current scope:** Run source code and tests in a terminal. The same Python entrypoint runs in GitHub Codespaces when online or on Odin in Termux while offline, provided its tools and dependencies are already installed. This is not a remote Termux shell, device deployment, model endpoint, or private receipt bridge.

## Use now (no editor installation)

- Online: open the GitHub repository in a **manually started GitHub Codespace**, open its terminal, and run the commands below. A Codespace uses cloud compute and **does not run offline**. GitHub account usage, storage, and idle-time charges/limits remain the owner's controls.
- Offline: open **Termux on Odin** in the checked-out `~/odin-workspace` repository. Run the same commands. Editing and tests can continue without internet, and Git pushes wait until connectivity returns.
- A standalone editor integration is deliberately **deferred**. This workflow does not require adding an editor to the handheld.

```sh
cd ~/odin-workspace       # On Odin; Codespaces terminal is already in the repository
python -B scripts/odin_codespace.py status
python -B scripts/odin_codespace.py test
```

**Requirements:** Python 3.13+ recommended; Node.js 22 for mobile tests; Ruff available as `ruff` or `.venv/bin/ruff`; and project dependencies already installed (`npm ci --prefix mobile --no-audit --no-fund --ignore-scripts` once when online). The Codespaces dev container automatically prepares a local Python virtual environment with Ruff 0.14.5 and installs the mobile dependencies **after you manually start the Codespace**. This does not start any model or device service. For a Termux checkout, install the tools yourself while connected before offline work. An offline run with a missing tool fails explicitly rather than pretending the test passed.

The source test loop runs active-doc checks, source structure checks, Python tests, local workstation tests, mobile Node tests, Ruff, and source preflight. Its JSON receipt is written under `state/codespace-receipts/`, ignored by Git and never automatically uploaded. It includes the local source SHA, test results, timing, and a unique ID; **it is not a device receipt**.

## Existing receipt and release process

The separate [private mailbox](ODIN_GITHUB_BRIDGE.md) remains the approved asynchronous path to the handheld. Do not copy local terminal output or credentials into public source receipts. A GitHub source PR and CI report are verified against the exact head SHA. Only approved device operations go through the existing authenticated private workflow; a comment or source receipt must never be interpreted as authorization for arbitrary shell execution.

For a reviewed source change: local tests → scoped PR → GitHub CI → review → merge → exact-main-SHA release gate → operator-approved install on Odin → new matching private device receipt → phone acceptance test as applicable. An offline local commit stays local until network access returns.

**No automatic cloud workspace starts, free-tier assumptions, paid inference, host changes, Tailscale changes, service restarts, or physical deployments are part of this source runner.** See [runtime truth](ODIN_RUNTIME.md) and [release gates](RELEASE_GATES.md).
