# Realign main onto accepted upstream-2026.5 Gemmamonster Gemma4 RC

Main and accepted staging diverged by 89 main-only and 63 staging-only commits. A conventional merge could retain superseded main-only Gemma implementations. This promotion deliberately makes the accepted RC tree authoritative while preserving both histories in a two-parent merge based on `8f970d4236738ae800b01786af7ad5ad843a62c8`.

This is a main-line realignment onto the accepted upstream-2026.5 Gemmamonster refit, not a conventional feature merge. Of the staging-only commits, 14 belong to upstream lineage; 49 are Gemmamonster-specific, including 13 documentation/evidence commits. See [commit inventory](COMMITS.md).

Production/runtime/build content is identical to accepted RC `43bc254e8996f17b929afef79f310d0b0b0cc139`. No main-only files are preserved. The only additions are the three promotion documents listed in [report](REPORT.md). No parser, runtime, generation semantics, dependency pins or operating parameters are changed by promotion.

Accepted live provenance is reused: build source `b722aa440b5555041f24e6d6f7aea8bda100bdf7`, evidence HEAD `43bc254e8996f17b929afef79f310d0b0b0cc139`, packaged binary SHA256 `3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE`. This is source-equivalence reuse, not a claim of a new promotion binary build.

Fresh verification must be attached from the actual promotion HEAD before opening this candidate: all six accepted semantic cc_test targets with cached test results disabled, whole-tree RC allowlist comparison, both-parent ancestry, and `git diff --check`. This draft does not assert tests that have not run yet.

Known non-blocking limitation: local Gemma/OpenCode planning/delegation loops remain a separate agent-loop termination / progress watchdog / plan-ledger policy track. A delegated parent-turn CANCELLED is expected when the same PID/executor continues, no GPU fatal/resource/quarantine event occurs, and the next request succeeds; it has not been demonstrated to be an OVMS failure. Full caveat and unchanged VLM_CB/GPU/u4 operating profile are in [report](REPORT.md).

Candidate text only: the branch is for independent review. No PR is opened or merged by this promotion task.
