# CIB2 / PGP / UMA execution wave 01

Authoritative design input: `d7014062d406f7242d67e9960d051f1431d6de1a`, [programme index](README.md). This execution follows CIB2 P0–P9, PGP-00–05 and UMA-PGP-00–06. Historical host evidence remains attached to its original source/model tuple.

## Ownership and dispatch

| Task | Owner | Isolated output | Review gate |
|---|---|---|---|
| PGP-00 + UMA-PGP-00 | OpenCode / GLM 5.3 Flash | `storage_geometry.py`, tests and diagnostic usage | Actual volume geometry, denied/unknown probes preserved, single physical memory ledger |
| PGP-02 foundation | OpenCode / DeepSeek V4.1 Flash | `pack_layout.py`, fixtures, tests and usage | Deterministic complete permutations, provenance isolation, malformed profile refusal, synthetic-only designation |
| P0/P1/P2/P3 readiness audit | Cursor Agent / Grok 4.7 High | Read-only report | Source/build/load evidence separated; next native gate has a concrete input and owner |
| Integration and independent QA | Coordinator | This feature branch and sanitized evidence | Inspect worker diffs, rerun tests, review failures before accepting any output |

Workers started from the same exact design commit in separate feature worktrees. They cannot change production source, native GPU/runtime files, weights, other workers' outputs or the shared registry. No worker may build/load a model, start listeners, repack weights or change system configuration. Provider sessions and exact commands are retained in the private canonical registry; process completion alone means NEEDS_REVIEW.

## Ordered programme

1. PGP-00 / UMA-PGP-00 and synthetic PGP-02 tooling can progress now. No real trace is invented from static expert maps.
2. CIB2-P0 establishes reproducible executable/source/build/module identity and unchanged Gemma/Qwen/Ornith protocol controls. CIB2-P1 records compiled expert kind, weights path and nine-tensor spec for each available full model.
3. CIB2-P2 reproduces native lease RED on exact RC1 before the smallest safety patch. P3 ports native Pack V1 safety; P4 integrates fail-closed/no-listeners CLI; P5 verifies actual native packs independently.
4. P6 validates model/kernel/tool parity and measured C1/C2/C4 on one isolated 2026.4 tuple. PGP-01 supplies actual complete traces and overhead control. Only then can optimized placement feed real A0/A1 packs and paired measurements.
5. Path A is the reference: verified staging, nine device copies, `usm_device`, safe slot publication. Path B remains OFF. UMA-PGP-03 must independently establish pre-write reader ownership and post-write GPU visibility on a compatible RC1 candidate before B0/B1.
6. Grouped I/O, prefetch, V2, typed per-slot A/B allocation and dense/non-GEMM3 placement stay separately gated. No automatic B/hybrid or hot/cold switch.

## PGP-00 / PGP-02 independent integration review (2026-10-24)

- Integration QA branch: `feature/cib2-pgp-wave01-integration-qa-20261024`, based on `279f4097`; original worker branches remain untouched. PGP-00 imported exactly from worker `6b843045` then hardened independently.
- PGP-02 is **already present and hardened** in coordinator lineage (follow-up commit `a2ccb127`, preceding this wave's `279f4097`). Do **not** cherry-pick the original `038d5591` onto it: that would revert the source-profile output protection and structural validation. Source worker remains an immutable reference.
- PGP-00 corrections: `GetVolumeInformationW` receives TCHAR counts, mounted-folder roots are resolved via `GetVolumePathNameW`, physical disk device mapping refuses mounted-folder aliases, and oversized/partial extents fail closed. Separate mock-only regression tests cover these exact hazards.
- Probe remains *diagnostic only*. No real Arc 140V Windows process, GPU, NVMe, WDDM ledger, model weights or pack runtime was exercised by cloud QA. Output and acceptance stay `NO`. Full native Pack V1 P3/P5 and source-build identity gates are still separate.
- Verification gate: `python -m unittest discover -s tests/cib2 -p 'test_*.py' -v` on operator host, then captured Windows drive-root/mount-point/ACL-denied snapshots. No synthetic report can be promoted to real PGP-00 acceptance.

## Baseline observation in this wave

The coordinator reran the existing 67 host tests at the design commit: PASS. A fresh physical-file rehash found all six previously recorded EXE/DLL identities unchanged and the source checkout still at frozen `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`.

[P0 diagnostic](evidence/pgp-wave01-20261024/p0-diagnostic.json) remains **UNVERIFIED** for source/build association and **NOT_RUN** for loaded modules. The inspected Bazel log ends in a successful/up-to-date target but does not bind the executable to all build inputs; `stable-status.txt` has an empty `BUILD_EMBED_LABEL`. No OVMS/native GPU job was observed at dispatch and no such process was launched here. Old semantic-refit/wave01 registry RUNNING labels do not establish live ownership and were not overwritten.

`fsutil fsinfo sectorinfo` and `ntfsinfo` returned Access denied. PGP-00 must preserve probe failures and independently use safe API information where available. WDDM free and system available are overlapping constraints, never additive capacity. Physical NVMe bytes and NAND geometry are NOT_EXPOSED unless directly measured.

Current runtime/production acceptance: **NOT_GRANTED**. See the private canonical register for current per-task process/review state and immutable request/handoff records.
