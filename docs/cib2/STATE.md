## PGP wave-01 Cursor integration checkpoint (2026-10-24)

- **INTEGRATION_BRANCH:** `feature/cib2-pgp-wave01-cursor-integration-20261024` on coordinator base `279f4097`, aggregating PR #24 and PR #25. Receipt: [INTEGRATION-PGP-WAVE01-20261024.md](INTEGRATION-PGP-WAVE01-20261024.md).
- **INCLUDED:** PGP-00 (import + Win32/WCHAR/extents hardening), PGP-02 numeric fail-closed (coordinator `a2ccb127` retained; worker PGP-02 not re-imported), PGP-05 offline A0/A1/B0/B1 screen.
- **HOST TESTS:** Python 3.14.6; targeted geometry/pack/benchmark PASS; full `tests/cib2` **168/168 PASS**. Host fixes include fixtures/privacy, volume-root snapshot path, sibling-file output guard, `strategy_effective` fallback identity, and A0/B0–A1/B1 pack identity.
- **WINDOWS PGP-00:** read-only probe RUN (temp path); `fsutil` ACL-denied and WDDM ledger preserved as NOT_EXPOSED; `runtime_acceptance=NO`. Mounted-folder live case NOT_RUN. Private snapshot outside repo.
- **ACCEPTANCE:** `HOST_READY` for offline tooling only. Native Pack V1 / GPU / production **NOT_GRANTED**. Path A default, Path B OFF.
- **NEXT:** hardware agent re-runs full suite on Arc 140V slot, captures sanitized drive-root/mount/ACL snapshots, then P0/P1/P2/P3/P5 native gates.

## PGP wave-01 integration QA checkpoint (2026-10-24) — superseded by Cursor integration above

- **QA_BRANCH:** `feature/cib2-pgp-wave01-integration-qa-20261024`, based on the coordinator's `279f4097` without touching frozen source or either worker branch.
- **PGP-02:** already integrated and independently hardened in the coordinator lineage at `a2ccb127`. No backport from the older PGP-02 worker snapshot. Additional QA closes huge-integer numeric overflow / float-boundary rounding with a separate regression suite.
- **PGP-00:** worker source/tests/docs imported by exact Git blobs; Win32 WCHAR lengths, actual NTFS mounted-volume root and incomplete disk extents hardened with additional mock tests.
- **QA STATUS:** cloud session was review/offline only; host execution and integration receipt now live on the Cursor integration branch.
- **NEXT:** keep PR #24/#25 open until the integration PR is accepted and contents confirmed included.

# CIB2 current execution state


## Documentation consolidation (2026-10-24; docs-only)

- **Branch:** `docs/cib2-layer-expert-pack-implementation-20261024` (branch source is executed family-map wave `ab7412c85a...`); only docs/diagram/archival moves here. Frozen `eb76a74f7aa...` untouched.
- **ACTIVE DOCUMENTATION:** [README](README.md) → [CIB2 P0–P9](LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md) → [PGP+UMA A/B](PROFILE-GUIDED-EXPERT-PACKING-20261024.md) → [inline Mermaid and editable source](PGP-UMA-PATH-AB-20261024.mermaid).
- **PATH A:** default `usm_device` resident and queue-ordered GPU copies; **PATH B:** optional scratch `usm_host`, pre-write GPU-reader drain + CPU scatter + post-write visibility; never silently enabled. B prior short model tests not production/2026.4 acceptance.
- **ARCHIVE:** byte-identical 2026-10-23 codework and preflight notes moved under [archive/20261023](archive/20261023/README.md); execution evidence, 67/67 host suite reports, mapper/replay scripts, and active state retained.
- **CURRENT_STAGE:** architecture and implementation plan documented; no new 2026.4 native GPU or OVMS tests executed by this docs branch.
- **NEXT_ACTION:** local agents start read-only PGP-00 Windows geometry/UMA ledger and synthetic PGP-02 optimizer; do not launch optional B or pack promotion until P0/P1 compiled eligibility and native 2026.4 Pack V1/A gates PASS. Preserve MFP-1 negative regressions.
- **ACCEPTANCE:** `NOT_ACCEPTED`; no runtime source, binaries or pack data modified.


## Current checkpoint: 2026-10-24

**Current normative design documents:** [LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md](LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md) and [PROFILE-GUIDED-EXPERT-PACKING-20261024.md](PROFILE-GUIDED-EXPERT-PACKING-20261024.md), including explicit UMA Path A default and gated B, with [flowchart](PGP-UMA-PATH-AB-20261024.mermaid). Previous 2026-10-23 work plan/preflight writeups are preserved in [archive/20261023/](archive/20261023/README.md) without altering source evidence. **Archive is not an acceptance gate**: full GPU runtime/2026.4 source-build evidence remains open.

Branch `feature/cib2-offload-family-map-20261024`. HOST_WAVE_REVIEWED, runtime acceptance NO. 67/67 host tests PASS, seven static export maps. Working-postfix EXE/DLL hashes now collected; build association and loaded evidence remain open. [Results and next gates](RESULTS-20261024.md). Earlier state below is historical.

---

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
- **HISTORICAL CODEWORK:** `docs/cib2/archive/20261023/CODE-WORK-PLAN-20261023.md`; its old CIB2-00 through CIB2-08 gates were elaborated by `docs/cib2/LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md` and `docs/cib2/PROFILE-GUIDED-EXPERT-PACKING-20261024.md`. Exact 2026.4rc1 SDK and protected protocol fixtures remain mandatory.
- **PREFLIGHT:** `scripts/cib2/preflight_rc3b.py` v2 distinguishes tag from freeze, refuses drift of protected Qwen/Ornith source blobs and committed diff outside CIB2 directories. `--binary-cohort tagged-rc3b` validates known release EXE hashes; `--binary-cohort frozen-postfix` (default) cannot mark EXEs verified without new build identity.
- **NOT_RUN:** Python unit test execution, new postfix executable SHA attestation, full `ovms_test`, Windows loaded DLL checks, GPU OTD performance and long agentic soak.
- **CURRENT_BLOCKER:** actual new working-postfix binary identities and exact isolated SDK 2026.4rc1 loaded-module evidence unavailable here. Archived tagged RC3B EXE hashes cannot substitute.
- **NEXT_ACTION:** local operator checks out CIB2 branch (with both tag and freeze fetched), runs `py -3 -m unittest discover -s tests/cib2 -p 'test_*.py' -v`, captures new postfix binaries and hardware-verified profile, tests `--strict`. Then open CIB2-00/01/03 PRs.
- **REVERT_POINTS:** immutable RC3B tag `b77b0f23` and working freeze `eb76a74f`; neither branch is modified by CIB2 work.
- **REVIEW_BOUNDARY:** modifications to `docs/cib2/`, `scripts/cib2/`, `tests/cib2/` only. No runtime/core GPU/plugin writes on this branch.
- **ACCEPTANCE:** explicit NOT_ACCEPTED pending full-suite and owner signoff.
