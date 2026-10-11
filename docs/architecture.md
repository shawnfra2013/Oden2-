# Odin 2 Architecture

## Design rule

Odin 2 is maintained as a modular system.

No monolithic controller/bootstrap application.

Components have isolated responsibilities and communicate through documented configuration and interfaces.

## Major subsystems

- config — shared configuration
- controller — controller event processing
- controller/actions — replaceable Android actions
- services — supervision definitions
- boot — startup integration
- ai — AI/inference components
- scripts — administration and auditing
- tests — verification
- docs — architecture and hardware documentation

Runtime logs, state, credentials, API keys and SSH keys are not committed.

## Change policy

Before changing the device:

1. Measure current state.
2. Record the intended change.
3. Modify the smallest responsible component.
4. Test the change.
5. Record the result.
6. Preserve a rollback path.
