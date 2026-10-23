# CIB2 / RC3B OTD preflight state

**Date:** 2026-10-23
**Branch:** `feature/cib2-rc3b-otd-preflight-20261023`
**Immutable base:** `qwm-semantic-refit-2026.4-rc3b` -> `b77b0f23fa7417e61778ef86ecb0ca739cc85f14`
**Parent release:** `qwm-semantic-refit-2026.4-rc3` -> `b12a913ba492b951eb3384583e46541ffe467763`
**Status:** SOURCE_PREFLIGHT_RECORDED / HOST_GATES_OPEN; not accepted.
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

## Active (updated 2026-10-23)

- **ACTIVE_STAGE:** source preflight delivered; no GPU runtime code port attempted.
- **BASE_SHA:** `b77b0f23fa7417e61778ef86ecb0ca739cc85f14`, tag `qwm-semantic-refit-2026.4-rc3b`.
- **CURRENT_HEAD:** `cd12e2bcd11075cfa1c6616c343657633a35c923` (as of state update preparation; this state edit will create one subsequent docs-only SHA).
- **LAST_GREEN_TESTS:** GitHub tag resolution, direct RC3 parent verification, source manifests, published upstream 2026.4 OTD path, GitHub compare scope. No binary/runtime tests executed.
- **CURRENT_FAILURE:** exact 2026.4.0.0rc1 SDK source / active module provenance and operator Windows model host unavailable; full test suite and owner signoff unverified.
- **NOT_RUN:** Python preflight unit suite execution, full `ovms_test`, DLL file rehash, GPU OTD runtime performance, Windows source build, agentic soak.
- **NEXT_ACTION:** local operator runs `py -3 -m unittest discover -s tests/cib2 -p 'test_*.py' -v` and `py -3 scripts/cib2/preflight_rc3b.py --repo .`; then supplies actual pinned binaries and stock SDK DLLs for strict hash preflight. Capture true kernel/ABI profile before any OTD patch.
- **DOCUMENT:** `docs/cib2/PREFLIGHT-20261023.md` (verified static findings, gated commit map and operator steps).
- **ARTIFACTS:** `scripts/cib2/preflight_rc3b.py`, `tests/cib2/test_preflight_rc3b.py`.
- **REVERT_POINT:** `qwm-semantic-refit-2026.4-rc3b`.
- **EVIDENCE_PATH:** `docs/cib2/` only. No unsanitized host paths or private traces.
- **PROMOTION:** explicit `NOT_ACCEPTED`, source-preflight branch only.
