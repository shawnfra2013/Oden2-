# GitHub event delivery test

Request ID `ODIN-HOUR-SMOKE-20261123-A` identifies this documentation-only draft PR. The acceptance evidence is a GitHub PR event and a ChatGPT task run that identifies the same PR, request ID, and full head SHA. The supervised device trial requires separate authorization and preflight under issue #99.

## Second event class: new commit on the existing draft PR

Request ID `ODIN-HOUR-SYNC-20261123-B` is a harmless `synchronize` event test, distinct from PR opening. On a GitHub update, the reviewer should (1) verify the current full head SHA and the matching PR, (2) check the three workflows for this new SHA, (3) post at most one redacted review marker for this SHA, and (4) record whether the originating event includes its immutable event-time SHA. Do not confuse the previous PR-open comment with an acknowledgment of this new commit.

This text changes documentation only. It does not authorize device updates, executable shell access, cloud costs, or an automated agent trial.

## Third event class: independently captured GitHub event SHA

Request ID `ODIN-HOUR-EVIDENCE-20261123-D` requests one additional harmless `synchronize` event after the trusted GitHub-side evidence workflow merged. Its acceptance is a GitHub Actions artifact recording the **original** `pull_request.head.sha` for this exact commit, independently of a later-fetched mutable PR head. Verify the artifact's run ID and SHA. Review notifications, if any, must remain deduplicated and must not be mistaken for a device action.

This remains documentation-only. It does not authorize device commands, deployment, new Work automation, or paid inference.
