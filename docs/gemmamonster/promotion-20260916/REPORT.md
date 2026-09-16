# Gemma4 RC main promotion

This is a main-line realignment onto the accepted upstream-2026.5 Gemmamonster refit, not a conventional feature merge.

## Frozen refs

```text
MAIN_SHA=8f970d4236738ae800b01786af7ad5ad843a62c8
STAGING_SHA=43bc254e8996f17b929afef79f310d0b0b0cc139
MERGE_BASE=9eb93f15fecb848d399f17c7a6a6626e5a1498d7
BEHAVIORAL_FREEZE=66c66140113c4a6be8ce0b11b5aa23ccc774ac22
BUILD_SOURCE=b722aa440b5555041f24e6d6f7aea8bda100bdf7
UPSTREAM_OBSERVED=405263f311484ce58db6ce8c46751c03c3af0a30
UPSTREAM_LINEAGE_TIP=a5136cb285482aaef5410a053b5ecd04ff9324ec
```

Both origin refs were fetched and checked against GitHub before construction. Main-only commits: 89; staging-only commits: 63; upstream lineage introduced: 14; Gemmamonster-specific commits: 49 (including 13 documentation/evidence commits and 36 implementation/test commits).

## Deliberate tree realignment

The branch starts at exact main. A two-parent merge records main as first parent and accepted staging as second parent. `git merge --strategy=ours --no-commit --no-ff <RC>` establishes the parent relationship, then `git read-tree --reset -u <RC>` replaces the entire index/worktree with the accepted RC tree before commit. The intermediate ours tree is never committed.

No main-only content is preserved. Main history remains reachable through the first parent. All tracked RC files are retained, including upstream build/dependency configuration and acceptance evidence. This prevents obsolete main-only Gemma runtime code and RC2 pins from surviving an ordinary conflict-free merge.

The only intentional differences from RC are these new documentation files:

- `docs/gemmamonster/promotion-20260916/REPORT.md`: provenance, operating profile, review scope.
- `docs/gemmamonster/promotion-20260916/COMMITS.md`: full commit inventories and ancestry-based classification.
- `docs/gemmamonster/promotion-20260916/PR-CANDIDATE.md`: text for independent review before opening a PR.

The whole-tree RC comparison must match that allowlist exactly. This covers `src/`, `third_party/`, `versions.mk`, `MODULE.bazel`, `WORKSPACE*`, `BUILD*`, `windows_build*`, and every other runtime/build path, including deletions. Git blob identities prove byte equality of tracked content, not merely equivalent behavior.

## Runtime and live acceptance provenance

```text
RUNTIME_DIFF_FROM_RC: NONE
BUILD_SOURCE: b722aa440b5555041f24e6d6f7aea8bda100bdf7
EVIDENCE_HEAD: 43bc254e8996f17b929afef79f310d0b0b0cc139
BINARY_SHA256: 3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE
```

No runtime changes are introduced by promotion. Build source to RC differs only in documentation and recorded acceptance material. Existing accepted packaged-binary live evidence is reused by source equivalence; the package is not claimed to have been built from the new promotion commit. The whole live acceptance is not rerun. Runtime/build differences would invalidate reuse and require a stop, rebuild and retest.

## Fresh verification procedure

Run all six `//src/test/llm/gemma4_generation` cc_test targets on the actual committed promotion HEAD, with cached test results disabled: generation_policy, phantom_tool_call, chunk_invariance, rendered_prompt_state, f7_contract, f10_guard. Preserve commands, output, tested SHA, exit codes and XML outside the committed tree to avoid changing HEAD after testing. Run `git diff --check` plus the promotion documentation diff check. No fresh test PASS is asserted in this pre-execution report; the delivery result and external logs carry fresh outcomes. The broader `//src:ovms_test` is a large combined executable, not a cheap standalone Gemma4 target.

## Known non-blocking dogfood caveat

The local Gemma/OpenCode agent can enter repetitive planning/delegation loops. This has not been demonstrated to be an OVMS protocol/parser/runtime failure.

Observed delegation behavior: parent request generates/thinks -> agent decides to delegate -> client cancels parent turn -> OVMS logs CalculatorGraph/LLMExecutor CANCELLED -> request count returns to zero -> new subagent request arrives -> same OVMS executor continues normally.

Treat this as expected parent-turn cancellation when delegation actually occurred, the same OVMS PID remains alive, no GPU_CONTEXT_FATAL, CL_OUT_OF_RESOURCES or executor quarantine occurs, and the subsequent request succeeds. CANCELLED alone is not evidence of a server crash.

Agent looping belongs to the separate follow-up track `agent-loop termination / progress watchdog / plan-ledger policy`. It is outside this promotion unless evidence proves the server causes the loop.

## RC operating profile (unchanged)

```text
pipeline_type=VLM_CB
target_device=GPU
KV_CACHE_PRECISION=u4
enable_prefix_caching=true
max_num_batched_tokens=4096
max_num_seqs=4
cache_size=0
reasoning_parser=gemma4
tool_parser=gemma4
enable_tool_guided_generation=true
dynamic_split_fuse=true
```

## Review boundary

Push only `integration/gemma4-rc-main-promotion-20260916`. Do not open a direct staging-to-main PR, open the promotion PR, merge, move staging, rewrite main, or tune runtime. The user independently reviews the promotion branch before a PR is opened or merged.
