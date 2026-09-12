# Gemmamonster RC2 semantic-refit execution plan — 2026-09-12

## Objective

Build a successful RC2 on the proven 2026.4 runtime/dependency line while retaining the advanced Gemma4 protocol semantics already implemented in the historical refit lineage. RC1 is a performance/build-method control, not the source base.

## Candidate identities

### Control A — immutable RC1

- source: `a43f644f10e55d741d5388e43580146c5203c196`
- role: fast runtime control, build/package-method evidence, negative semantic reference
- existing measured behavior: excellent VLM_CB decode performance and runtime endurance, but reduced Gemma4 source semantics and unstable `required`/named forced tool policy

### Candidate B — existing semantic refit

- operational carrier: `8a54214fed2a0cb01ad17159364996f8787a92fa`
- semantic core: `9a1626260614f68a6282b6799842d5152f0dcdff`
- source substrate: latest maintainer 2026.4 pre-2026.5-switch lineage rooted at `9eb93f15fecb848d399f17c7a6a6626e5a1498d7`
- runtime dependency line: 2026.4 RC2 pins already recorded in `versions.mk`

Git evidence shows the 15 commits from `9a162626` to `8a54214` do not modify `src/llm/**`. Therefore keep two identities: semantic source identity and operational carrier identity.

## Execution order

1. Keep RC1 immutable. No repair commits on `a43f644` lineage.
2. Use `integration/gemmamonster-rc2-semantic-refit-20260912` from `8a54214` for RC2 work.
3. Install/use the repo-local Worklog before consequential work.
4. Wait for the RC1 build-provenance forensic report.
5. Validate that report against historical scripts, logs, artifacts and exact dependency identities. Unsupported reconstruction remains `UNKNOWN`.
6. Derive one exact B build recipe that preserves RC1 build mechanics wherever proven while compiling B source.
7. Run mandatory sanitized environment preflight in the same shell as build/test/package.
8. Build and package B with official OVMS Windows scripts/method, not ad-hoc DLL collection.
9. Verify source contracts, package manifest/hashes, and loaded runtime modules.
10. Run functional/streaming/NovaClaw/endurance/performance acceptance.
11. Freeze B only if the exact package passes; source-contract success alone is not acceptance.

## Primary causal experiment

A and B should match, as far as evidence allows, on:

- host/GPU/driver
- model bytes
- VLM_CB
- launch flags
- dependency/runtime profile
- build/package method
- benchmark harness

The intended major changed variable is source semantics.

## If B fails

Do NOT immediately edit parser/generator code. First locate the first failing layer with raw request → raw OVMS response/SSE → NovaClaw interpretation traces.

Then use the existing refit history as a bisect ladder:

`9eb93f15` → `16df6acd` → later hardening → `e8c12202` → `9a162626`.

Only if historical bisect proves an implementation defect should P/R/S/G/T be modified individually:

- P: tool parser / boundary ownership
- R: reasoning / phase coordination
- S: special-token streamer handoff
- G: generation/tool policy
- T: rendered prompt/template-state adaptation

Session continuity remains a separate optional/high-risk variable.

## Promotion gates

Required for RC2 promotion:

- exact source/package/dependency provenance
- contracts green
- official package green
- auto/none/streaming/complex-schema/parallel/multi-turn green
- NovaClaw long-loop replay green
- no promise-without-call regression
- at least 150 realistic requests with no GPU fatal/quarantine/restart
- TTFT and pure-decode comparison against immutable RC1

`required`/named forced policy remains a secondary gate unless the target deployment explicitly depends on it.
