# Seal Fast reader compatibility and future Resident Pack contract

Date 2026-10-24. Source: TZ-SEAL-FAST-20261024 §0–14. Candidate only; `runtime_acceptance=NO`.

## What is already ready

The **routed-expert** reader is implemented in the Intel GPU plugin: OTDPACK1 is read via `OffloadExpertWeightProvider::configure_pack()` and `fill_weights_from_pack()`, with native `PackLayout` + verified expert records at demand time. The existing OVMS branch routes immutable sealed generations via `--moe_experts_pack_dir`. These consumers require no change in file format for this seal optimization.

## What is NOT ready

The **static by-design Resident Pack** draft in PR #32 has an offline inventoried pack and digest tooling only. It has no accepted native compiled-GPU-graph binding, no data-owner lifetime proof and no GPU residency-loader contract. Do not graft its payloads into OTDPACK1 or set `runtime_acceptance=YES`.

## Gate sequence

- R0: Keep old Python CLI shape and V2 generation digest and strict inventory stable. New seal/verify are opt-in experimental branch, not merged into active long-running build.
- R1: Verify native OTDPACK1 read from a sealed generation using the attributed OpenVINO/OVMS binaries; preserve patch-free kernel and exact logits.
- R2: Run same-cohort `stock r20`, `CIB2 unpacked r20`, `CIB2 packed r20` tests with free host. Instrument `SynchronousExecutionGate`, `onednn.wait`, `stream.finish` and checksum; report speed versus 27.61 decode tok/s and 32.65 r0.
- R3: Resident Pack requires actual compiled-graph static constant manifest, verified source-offset and quant layout, single-load ownership and no duplicated USM allocations, then model startup TTFT and GPU memory A/B. Reader design and integration performed in another native GPU plugin candidate. No forced coupling of native OTD seal and static pack.
- R4: Only with accepted R3 create **new** dual-generation envelope (new schema/feature gate), with independent attestation of immutable static vs dynamic pieces. Existing `cib2.pack_generation.v2` must not silently accept extra files.

## Unresolved conflicts in original TZ

A 'fast structural + SHA-on-copy' pass cannot reject arbitrary *preexisting* payload corruption while avoiding native record-FNV verification. `full` is mandatory before release. Hardlink mode also cannot prove immutability from file write bits alone (ACLs/admin/other hardlinks). Both are explicitly surfaced as mode-specific guarantees in the new metrics and MANUAL.

Native model feature/reader readiness is not inferred from passing Python pack tests; it requires GPU unit and same-hardware serve tests. Do not merge candidate PR until local agent verifies OS-specific semantics and real speeds.
