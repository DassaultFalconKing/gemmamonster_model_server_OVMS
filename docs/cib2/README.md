## Active CIB2 Pack V2 Full execution (2026-10-24)

- [Master plan: new OVMS 2026.4 / Pack V2 / UMA](MASTER-PLAN-NATIVE-PACKV2-20261024.md)
- [Orchestrator: execute N1 → N4, native build + live Arc140V](ORCHESTRATOR-EXEC-N1-N4-20261024.md)
- [Previous Cursor source-build handoff](CURSOR-HANDOFF-PACKV2-BUILD-20261024.md)
- OVMS code: [Draft PR #29](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/29); OpenVINO 2026.4 target N2/N3/N4 code: [Draft PR #10](https://github.com/DassaultFalconKing/openvino/pull/10); 2026.5-derived native source DONOR: [PR #9](https://github.com/DassaultFalconKing/openvino/pull/9).
- N1 runtime port / Windows compilation / GPU tests **NOT_RUN**. N2/N3/N4 helper code **WRITTEN, NOT WIRED to hardware events or OS/WDDM**. Prefetch OFF until lease+admission gates are green; Path B OFF.

# CIB2 layer/expert offload — current programme and evidence index

**2026-10-24. PROGRAMME CURRENT; GPU/production acceptance NOT_GRANTED.**

This is the current entry point for semantic-refit 2026.4 RC3B-postfix family-map / packed-expert and memory design. Do not treat new documentation as runtime or GPU acceptance.

## Current normative implementation/design

1. [LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md](LAYER-EXPERT-PACK-IMPLEMENTATION-20261024.md) — master plan P0–P9 for OpenVINO 2026.4 RC1 native Pack V1, exact compiled eligibility, fail-closed CLI, source/module identity, live C1/C2/C4 and regression gates.
2. [PROFILE-GUIDED-EXPERT-PACKING-20261024.md](PROFILE-GUIDED-EXPERT-PACKING-20261024.md) — PGP-00…05 profile-first per-layer physical placement, Windows sector/NTFS geometry, real traces, grouped read/prefetch only after A/B.
3. **[PGP UMA Path A (default) / B (opt-in), section 11](PROFILE-GUIDED-EXPERT-PACKING-20261024.md#11-uma-path-a--optional-path-b-placement-controller-integrated-with-pgp-2026-10-24)** — memory-controller datapaths, ownership/visibility/leases, UMA admission, A0/A1/B0/B1 controls, staged tickets UMA-PGP-00…06.
4. [Editable A/B memory and pack flow](PGP-UMA-PATH-AB-20261024.mermaid) — solid Path A, dotted experimental Path B, single physical LPDDR ledger.
5. [STATE.md](STATE.md) — tracked baseline, missing hardware gates, current operator handoff.

## PGP wave-01 integration QA

- [Cursor Wave-01 integration receipt](INTEGRATION-PGP-WAVE01-20261024.md) aggregates PR #24 + PR #25 on `feature/cib2-pgp-wave01-cursor-integration-20261024` (**HOST_READY** offline tooling; 174/174 host tests).
- [Wave-01 dispatch + independent review](ORCHESTRATION-PGP-WAVE01-20261024.md) records the three branches and acceptance limitations.
- [PGP-00 storage/UMA geometry diagnostics](STORAGE-GEOMETRY-USAGE-20261024.md) with standalone `storage_geometry.py` and independent mocked Windows safety tests.
- [PGP-02 offline Pack V1 placement](PACK-LAYOUT-USAGE-20261024.md) was already part of coordinator lineage and independently hardened; no re-import of the older worker version.
- [PGP-05 offline benchmark evidence screen](PGP05-BENCHMARK-SCREEN-20261024.md) — A0/A1/B0/B1 same-cohort reviewer; never auto-promotes runtime.
- **Status:** offline tooling `HOST_READY`; not native Pack V1 or 2026.4 GPU acceptance.

## Current measured/static evidence (DO NOT archive)

- [RESULTS-20261024.md](RESULTS-20261024.md): current host wave, 67/67 tests, source/binary limitations, no 2026.4 GPU inference in this wave.
- [FAMILY-MAP-20261024.md](FAMILY-MAP-20261024.md): seven exported model inventories, compiler eligibility still unknown.
- [GEMMA-QWEN-TESTS-20261024.md](GEMMA-QWEN-TESTS-20261024.md): real XML/BIN boundary samples, not a packer or live OTD proof.
- [EXECUTION-20261024.md](EXECUTION-20261024.md): immutable worker delegation and evidence provenance.
- [evidence/](evidence/) and source-only `scripts/cib2` / `tests/cib2` remain in their original locations.

## Archived superseded documents

- [archive/20261023/README.md](archive/20261023/README.md) indexes byte-identical snapshots of historical 2026-10-23 coding/preflight notes. Old file links from this branch are redirected. No historical test evidence has been reinterpreted or overwritten.

## Separate branches that are **not** silently incorporated

- [ADR-UMA-01, including measured A/B addendum](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/docs/adr-uma-arc140v-shared-memory-20261022/docs/qwenmonster/ADR-UMA-ARC140V-MEMORY-MODEL-20261022.md).
- [OpenVINO GPU Pack Wave01 PR #7](https://github.com/DassaultFalconKing/openvino/pull/7), [UMA Path B scratch PR #8](https://github.com/DassaultFalconKing/openvino/pull/8).
- Old routed-expert research [docs/moe-nvme-experts-research-20261021](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/tree/docs/moe-nvme-experts-research-20261021/docs/research/routed-experts-nvme-20261021): original work preserved in its **own branch**, not moved/deleted in this working tree.

**Policy:** Pack V1 and `usm_device` Path A are the baseline. `usm_host` Path B remains experimental/off until exact RC1 same-cohort resource, safety, model, agentic and performance gates are passed. The pack file layout and memory resident mode are independent optimization axes.

## Independent PGP-05 evidence screening (candidate)

- [PGP-05 read-only A0/A1/B0/B1 screen](PGP05-BENCHMARK-SCREEN-20261024.md):
  strict same-cohort validation, source/pack/gate flags, paired sample metrics,
  physical-device-counter separation and synthetic negative tests.
  This offline reviewer cannot authorize runtime/pack/GPU acceptance; Path B stays OFF.
