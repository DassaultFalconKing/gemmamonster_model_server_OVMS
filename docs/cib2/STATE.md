# CIB2 / RC3B OTD preflight state

**Date:** 2026-10-23
**Branch:** `feature/cib2-rc3b-otd-preflight-20261023`
**Immutable base:** `qwm-semantic-refit-2026.4-rc3b` -> `b77b0f23fa7417e61778ef86ecb0ca739cc85f14`
**Parent release:** `qwm-semantic-refit-2026.4-rc3` -> `b12a913ba492b951eb3384583e46541ffe467763`
**Status:** SYNCED_WITH_FROZEN_WORKING_POSTFIX / STATIC_PREFLIGHT_OPEN; not accepted.
**Scope:** documentation, reproducible static gates, benchmark contracts. Do not mutate RC3B core, published tags or runtime DLLs.

## Verified so far
- Annotated release tag resolves to exact RC3B source commit, with direct RC3 parent.
- RC3B manifest: `docs/qwenmonster/RELEASE-CANDIDATE-20261023-RC3B-IDENTITY.json`.
- Release manifest specifies isolated OpenVINO GenAI Windows 2026.4.0.0rc1 SDK and stock GPU plugin; NOT custom `moe38545` (`21a2fd9f`).
- Release manifest reports live 6/6 passes for Gemma E4B, Gemma 26B and Ornith, plus targeted unit tests. Those are **reported evidence**, not independently re-executed here.
- Full `ovms_test` and owner signoff remain open.
- OpenVINO 2026.4 source already contains native OTD expert provider and LRU. Upstream provider checks oversize *inside* an acquisition loop, after earlier cache mutations; candidate safe preflight is transactional precheck.
- Baseline must be **actual SDK 2026.4.0.0rc1 binary provenance**. Do not confuse it with the released OpenVINO `2026.4.0` Git tag; source similarity alone proves neither ABI identity nor runtime behavior.

## Stage ladder
- P00 **SOURCE_BASE_VERIFIED**: tagged source ancestry and the manifest confirmed via GitHub.
- P01 **STATIC_SDK_GAP_AUDIT**: source comparison pending local exact SDK source/binaries; upstream 2026.4 provider risk confirmed.
- P02 **PINNED_RUNTIME_HASH**: recorded hashes in manifest; rehash on operator host NOT_RUN.
- P03 **CONTROL_TESTS**: reported RC3B targeted 11/11 Qwen generation policy and related parser tests; independently rerun NOT_RUN.
- P04 **FULL_SUITE**: NOT_RUN.
- P05 **GPU_OTD_LIVE_BASELINE**: NOT_RUN.
- P06 **OWNER_ACCEPTANCE**: NOT_DONE.

## Migration policy
1. First, add only passive tracing / offline replay / reproducible tests; no unexpected synchronization or allocator changes.
2. LRU transactional precheck and GPU lifetime fixes must first have baseline RED reproduction against **SDK RC1 source**, then minimal code patches and independent parity proof.
3. Expert pack is candidate-only, requires payload verification, same-handle reader pin and atomic publish; never silently activate on RC3B.
4. Keep no-OTD and stock-OTD outputs identical across instrumentation changes. OTD `OFFLOAD_RATIO=0` is negative control, not OTD coverage.
5. Performance reference is stock RC3B with pinned model/checkpoint/driver and memory profile; never infer its throughput from the closed 2026.5 fork.

## Active (updated 2026-10-23, post-freeze sync)

- **ACTIVE_STAGE:** detailed code-work planning, source preflight and host provenance checks. Runtime OTD patch **not started**.
- **IMMUTABLE_RELEASE:** `qwm-semantic-refit-2026.4-rc3b` -> `b77b0f23fa7417e61778ef86ecb0ca739cc85f14`; RC3 parent `b12a913ba492b951eb3384583e46541ffe467763`. Do not retag or substitute this release SHA.
- **FROZEN_WORKING_BASE:** `freeze/rc3b-postfix-20261023-eb76a74f` -> `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`, four additional postfix commits after RC3B. Preserve Qwen lossless parser, Ornith template pin and retainer architecture document.
- **CIB2_SYNC_MERGE:** `7351bb921e16382e4357bcc1311471b13964f64b`, two parents: prior CIB2 `d1f04532ed392ca134fc0a8158492861c555df16` + freeze `eb76a74f`. Merge tree is freeze + CIB2-only paths; working semantic-refit branch untouched.
- **LAST_GREEN_TESTS:** GitHub tag ancestry and tree compare; existing Qwen 81/81 XML at frozen commit is HISTORICAL operator evidence, not a new test execution.
- **CODEWORK:** `docs/cib2/CODE-WORK-PLAN-20261023.md`; CIB2-00 through CIB2-08, gated by exact 2026.4rc1 SDK and preserved protocol fixture baseline.
- **PREFLIGHT:** `scripts/cib2/preflight_rc3b.py` v2 distinguishes tag from freeze, refuses drift of protected Qwen/Ornith source blobs and committed diff outside CIB2 directories. `--binary-cohort tagged-rc3b` validates known release EXE hashes; `--binary-cohort frozen-postfix` (default) cannot mark EXEs verified without new build identity.
- **NOT_RUN:** Python unit test execution, new postfix executable SHA attestation, full `ovms_test`, Windows loaded DLL checks, GPU OTD performance and long agentic soak.
- **CURRENT_BLOCKER:** actual new working-postfix binary identities and exact isolated SDK 2026.4rc1 loaded-module evidence unavailable here. Archived tagged RC3B EXE hashes cannot substitute.
- **NEXT_ACTION:** local operator checks out CIB2 branch (with both tag and freeze fetched), runs `py -3 -m unittest discover -s tests/cib2 -p 'test_*.py' -v`, captures new postfix binaries and hardware-verified profile, tests `--strict`. Then open CIB2-00/01/03 PRs.
- **REVERT_POINTS:** immutable RC3B tag `b77b0f23` and working freeze `eb76a74f`; neither branch is modified by CIB2 work.
- **REVIEW_BOUNDARY:** modifications to `docs/cib2/`, `scripts/cib2/`, `tests/cib2/` only. No runtime/core GPU/plugin writes on this branch.
- **ACCEPTANCE:** explicit NOT_ACCEPTED pending full-suite and owner signoff.
