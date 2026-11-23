# Odin verification coverage gate (source-only candidate)

Issues: [#86](https://github.com/shawnfra2013/Oden2-/issues/86), [#99](https://github.com/shawnfra2013/Oden2-/issues/99), and physical memory acceptance [#122](https://github.com/shawnfra2013/Oden2-/issues/122).

This is a **local, offline, non-executing metadata evaluator**, not a new daemon, GitHub API client, authenticated receipt reader, agent identity provider, or physical test runner. It never sends a device command. The caller must independently retrieve, authenticate and redact each receipt before constructing input. A forged input with `verified=true` can falsely report PASS; the gate does not cryptographically validate that assertion. Therefore output PASS means **metadata-consistent**, not externally authenticated or device accepted.

Run: `python -B scripts/odin_verification_coverage.py redacted-metadata.json` (nonzero exit for incomplete coverage). Test: `python -m unittest discover -s tests -p 'test_odin_verification_coverage.py'`.

Input shape:

```json
{
  "expected_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "evidence": [
    {
      "stage": "source",
      "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "timestamp": "2026-11-23T19:59:00Z",
      "status": "PASS",
      "proof_kind": "source",
      "verified": true
    }
  ]
}
```

Allowed stages: `source`, `device`, `agent`, `memory`, `phone`. Missing stages are UNVERIFIED; duplicate stages or replayed 32-hex request IDs FAIL. Stale/future timestamps and mismatched SHA are UNVERIFIED. A claimed PASS needs a stage-matched proof kind and explicit verified flag; non-source stages also need a request ID. Agent PASS additionally requires all three independent booleans `agent_identity_verified`, `action_executed`, and `source_revision_verified` to be true. Do not infer these flags from a feedback note or tool-presentation receipt.

**Next verification capability:** attach authenticated adapters to the existing private GitHub mailbox and exact-head Actions, supply provenance of those attestations, and add a physical acceptance runner for Android memory and cellular phone checks only after operator approval. Keep private payloads out of public CI, issue comments and JSON reports. Missing connector permission must remain UNVERIFIED, not be treated as missing device activity.

This initial gate intentionally does not parse or emit arbitrary evidence fields. No deployment is approved by a PASS label.
