# Odin 2 Architecture

## Design Principle

Odin 2 is built as a **modular system** – there is no monolithic controller or bootstrap application.
Each component has a single, well‑defined responsibility and interacts with other parts only through **documented configuration** and **explicit interfaces**.

## Core Subsystems

| Subsystem | Purpose |
|-----------|---------|
| **config** | Centralised, shared configuration data |
| **controller** | Core event‑processing engine |
| **controller/actions** | Pluggable Android actions that can be swapped out |
| **services** | Definitions for supervising background services |
| **boot** | Integration logic that runs at startup |
| **ai** | Components for AI inference and related processing |
| **scripts** | Administrative and audit scripts |
| **tests** | Automated verification and regression tests |
| **docs** | Architecture, hardware specifications, and other documentation |

> **Note:** Runtime logs, state files, credentials, API keys and SSH keys are **never** committed to the repository.

## Change Management Policy

When a change to a device is required, follow these steps:

1. **Measure** – Capture the current state of the system.
2. **Record** – Document the intended modification and its rationale.
3. **Isolate** – Apply the change to the smallest possible component that owns the behaviour.
4. **Test** – Verify the change with the appropriate test suite.
5. **Log** – Record the observed results and any side effects.
6. **Rollback** – Ensure a clear path to revert the change if needed.
