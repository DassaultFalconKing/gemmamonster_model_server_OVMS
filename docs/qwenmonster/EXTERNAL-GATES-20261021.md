# OVMS external-agent checkpoint

**ACCEPTED: NO.** No product source, installed runtime or published dependency
lock was changed. The existing Ornith process was verified by creation time,
executable hash, listener and configuration, then reused without restart.

Three actual external OpenCode sessions used CLI 1.19.3 and explicit model
opencode/glm-5.3-flash-free. One owned a bounded live probe; two reviewed isolated
source snapshots without inference or builds. Root independently checked the
runtime captures and substantive static findings. Process exit 0 alone was not
the acceptance criterion.

## Measured runtime result

- Invalid object-root schema: HTTP 400, expected diagnostic.
- Valid named weather/Paris immediately afterward: HTTP 200, exactly one validated
  weather call with city Paris and tool_calls finish.
- Exact assistant/tool_call_id replay and fresh post-dispatch receipt: HTTP 200,
  final stop response contains Paris and the receipt. External shell exit 0;
  original probe hash unchanged.

This closes the previously NOT RUN positive-after-errors control for the existing
runtime tuple. Hermes, actual LENGTH/cancellation,100-city and 1/2/4 workloads
remain separate NOT RUN gates. No #802 integration is implied.

## Resource boundary

Available RAM changed from 4776 MiB before the probe to 514 MiB afterward. OVMS RSS
changed from 7079 MiB to 12779 MiB; private bytes from 16400 MiB to 16451 MiB. At the
recorded later idle snapshot, available RAM was 2076 MiB. These measurements do
not establish a memory leak or an attributed root cause. No further inference
or competing native build was launched after observing pressure. Characterize
resident/private memory and system pressure before stress/concurrency work.

## Reviewed static findings

The visible CB streaming path retains GenerationOutput.finish_reason and passes
it to final API serialization; mapFinishReason maps LENGTH to length. The STOP
inside streamer.end() reaches parser cleanup and is not itself the client finish
reason. Do not implement an API finish-reason rewrite on that observation alone.
Parser terminal semantics and concrete legacy/executor cancellation still need
their own trace/runtime RED tests; those files were outside the bounded review.

The R1 runner needs an exact expected row-name set and bounded timeout cleanup.
The reviewer also flagged sources, paths and runtime DLLs absent from its reduced
snapshot; root checked the actual package: original-checks.cpp exists and is
sealed, original paths are materialized, and MSVC runtime DLLs are present.
Those snapshot limitations are not confirmed actual-package blockers. Native
build and matcher execution remain NOT RUN; do not promote the cohort.

Compact identities, outcomes and evidence hashes:
evidence/external-gates-20261021/RESULTS.json. Raw machine paths/logs/session IDs
remain private. Existing acceptance gates remain applicable.
