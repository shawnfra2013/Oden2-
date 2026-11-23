# GitHub event delivery test

Request ID `ODIN-HOUR-SMOKE-20261123-A` identifies this documentation-only draft PR. The acceptance evidence is a GitHub PR event and a ChatGPT task run that identifies the same PR, request ID, and full head SHA. The supervised device trial requires separate authorization and preflight under issue #99.

## Second event class: new commit on the existing draft PR

Request ID `ODIN-HOUR-SYNC-20261123-B` is a harmless `synchronize` event test, distinct from PR opening. On a GitHub update, the reviewer should (1) verify the current full head SHA and the matching PR, (2) check the three workflows for this new SHA, (3) post at most one redacted review marker for this SHA, and (4) record whether the originating event includes its immutable event-time SHA. Do not confuse the previous PR-open comment with an acknowledgment of this new commit.

This text changes documentation only. It does not authorize device updates, executable shell access, cloud costs, or an automated agent trial.
