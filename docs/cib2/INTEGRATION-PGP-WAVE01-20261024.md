# CIB2 / PGP Wave-01 Cursor integration receipt (2026-10-24)

**Status:** `HOST_READY` for offline CIB2 tooling integration only.  
**Not:** `GPU_READY`, `PACK_ACCEPTED`, or `PRODUCTION_READY`.  
**Runtime acceptance:** `NO`. Path A (`usm_device`) default; Path B (`usm_host`) OFF.

## 1. Exact input commits

| Role | Branch / PR | Source SHA |
|---|---|---|
| Coordinator base | `feature/cib2-offload-family-map-20261024` | `279f4097f9340cd9044c92ee43e67b0b24ab54d2` |
| PGP-02 prior hardening (already in base) | coordinator lineage | `a2ccb127c12712f05a429d383943c5f12b9f24e8` |
| PR #24 commit 1 | PGP-00 import | `bb0e23e7af01d43490e7bf2a26d09eb5e9d41bfb` |
| PR #24 commit 2 | PGP-00 Win32/WCHAR/extents | `550f72544e50c0aab071727a236c3d8f054b5728` |
| PR #24 commit 3 | PGP-02 numeric fail-closed | `17421f52c98f25bb1881bba691c16f187c282253` |
| PR #25 HEAD | PGP-05 benchmark screen | `df086dc8f8cfbfaf09aab2546f668a0a1555e127` |

No drift against pinned SHAs at fetch. Older worker `feature/cib2-pgp02-20261024` was **not** re-imported.

## 2. Final integration SHAs

| Item | Value |
|---|---|
| Integration branch | `feature/cib2-pgp-wave01-cursor-integration-20261024` |
| Worktree | `C:\Users\testc\cib2-pgp-integration` (isolated) |
| Cherry-pick equivalents | `f10030d8f`, `020a4a4b4`, `a8f405074`, `81f1cb58d` |
| Host fixture/privacy fix | `f1b056009` |
| Volume-root output-path fix | `85533a507` |
| File-sibling output protection | `7432937a3` |
| PGP-05 same-layout pack identity | `5783f3c57` |
| PGP-02 `strategy_effective` on fallback | `703ff6faf` |
| Final HEAD | confirm with `git rev-parse HEAD` on this branch after the docs commit |

## 3. Changed files (vs coordinator base)

Allowed boundary only:

- `docs/cib2/ORCHESTRATION-PGP-WAVE01-20261024.md`
- `docs/cib2/PACK-LAYOUT-USAGE-20261024.md`
- `docs/cib2/PGP05-BENCHMARK-SCREEN-20261024.md`
- `docs/cib2/README.md`
- `docs/cib2/STATE.md`
- `docs/cib2/STORAGE-GEOMETRY-USAGE-20261024.md`
- `docs/cib2/INTEGRATION-PGP-WAVE01-20261024.md` (this receipt)
- `scripts/cib2/benchmark_screen.py`
- `scripts/cib2/pack_layout.py`
- `scripts/cib2/storage_geometry.py`
- `tests/cib2/test_benchmark_screen.py`
- `tests/cib2/test_pack_layout.py`
- `tests/cib2/test_pack_layout_numeric_review.py`
- `tests/cib2/test_storage_geometry.py`
- `tests/cib2/test_storage_geometry_review.py`

`git diff --check` clean. No OVMS / runtime / GPU plugin / model / binary / hook changes.

## 4. Conflict resolution

Cherry-picks applied cleanly (`README.md` auto-merged). Separate pointers retained for PGP-00, coordinator-hardened PGP-02, and PGP-05. Coordinator PGP-02 protections from `a2ccb127` remain intact.

## 5. Findings A / B / C

Independent review-only agents plus host execution.

### Agent A — PGP-00 / Windows geometry

**Overall risk:** LOW–MEDIUM (after fixes: LOW for host diagnostic use).

Host suite initially failed four cases after PR #24 hardening landed on older fixtures:

1. `VOLUME_DISK_EXTENTS` fixture omitted the 4-byte pad (array at offset 8).
2. Device-descriptor fixture glued revision+serial by expanding a bytearray slice.
3. Access-alignment test treated Windows `Version==28` as invalid; foreign versions still fail closed.
4. Public-summary privacy check collided with the word “serials” in the operator note.

Additional audit HIGH: probing a **file** allowed sibling `.json` overwrite (documented tree protection gap) — fixed in `7432937a3`.

Volume-root probes previously could not write any same-volume `%TEMP%` output — fixed in `85533a507`.

Solid: WCHAR lengths, `GetVolumePathNameW`, zero-access handles, truncated extents fail-closed, non-additive memory ledgers, WDDM NOT_EXPOSED stub, stdout omits concrete serials.

### Agent B — PGP-02 / Pack V1 placement

**Overall risk:** LOW. No CRITICAL/HIGH after integration fix.

Solid: determinism, permutation/inverse parity, numeric fail-closed (`a8f405074`), scoped provenance, CLI SHA binding, acceptance flags locked `NO`, synthetic warnings.

MEDIUM addressed on branch: `strategy_effective` now becomes `identity` whenever fallback is used (`703ff6faf`). Residual notes (library SHA footgun, post-hoc synthetic strip, docs example `placement==order`) remain documentation/API hygiene, not host blockers.

Native Pack V1 untouched.

### Agent C — PGP-05 / Benchmark screening

**Overall risk:** LOW for promotion misuse; was MODERATE for matched-pair integrity until pack identity fix.

Solid: never `PASS`; `promotion_authorized=false`; `runtime_acceptance=NO`; cohort/scenario lock; device_counter-only physical bytes; NaN/overflow fail-closed; synthetic BLOCKED.

HIGH fixed: A0≡B0 and A1≡B1 must share `pack_manifest_sha` (`5783f3c57`). Residual MEDIUM (offload ratio enum, warmup authenticity, extra negatives) do not block `HOST_READY`.

## 6. Defects fixed on the integration branch

| Commit | Defect |
|---|---|
| `f1b056009` | Align PGP-00 fixtures with Win32 extent/descriptor layout; Version 28 acceptance; stdout serial-field privacy |
| `85533a507` | Allow volume-root probe to write elsewhere on same volume |
| `7432937a3` | Refuse sibling writes beside a probed file |
| `5783f3c57` | Enforce same-layout `pack_manifest_sha` in PGP-05 |
| `703ff6faf` | Record `strategy_effective=identity` on layout fallback |

## 7. Targeted test results

Interpreter: **Python 3.14.6** (`py -3`).

| Suite | Result |
|---|---|
| `py_compile` storage/pack/benchmark | PASS |
| `test_storage_geometry*.py` | **41/41 PASS** |
| `test_pack_layout*.py` | **44/44 PASS** |
| `test_benchmark_screen.py` | **16/16 PASS** |

## 8. Full host suite

```text
py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v
Ran 168 tests in ~0.5s
OK
```

Do **not** treat historical “67/67” as this run. Actual: **168 PASS / 0 FAIL / 0 SKIP**.

## 9. Windows hardware status

Read-only PGP-00 executed on this Windows host. Private snapshots under `%TEMP%\cib2-pgp00-private\` (not committed).

| Case | Status | Note |
|---|---|---|
| Ordinary NTFS path / worktree | RUN | volume root `C:\`, allocation EXPOSED |
| Drive root `C:\` → TEMP output | RUN | after `85533a507` |
| `fsutil fsinfo sectorinfo/ntfsinfo` | NOT_EXPOSED | Error 5 Access denied — preserved |
| Device identity / alignment IOCTL | EXPOSED | private file; stdout sanitized |
| WDDM ledger | NOT_EXPOSED | DXGI disabled by coordinator; not substituted |
| Mounted-folder live path | **NOT_RUN** | no dedicated mount fixture on this host |
| Native inference / OTD | **NOT_RUN** | no hardware benchmark slot claimed |

`runtime_acceptance` remains `NO` in every probe.

## 10. Native Pack V1 and GPU acceptance

| Gate | Status |
|---|---|
| Native Pack V1 P3/P5 | NOT_RUN / NOT_GRANTED |
| 2026.4 GPU live inference | NOT_RUN / NOT_GRANTED |
| Source/build/module identity (P0) | UNVERIFIED / open |
| Compiled eligibility (P1) | open |
| Runtime / production acceptance | **NO** |

## 11. Residual blockers (P0/P1/P2/P3/P5)

- **P0:** bind working-postfix EXE/DLL hashes to exact build inputs; loaded-module evidence.
- **P1:** compiled expert-kind / nine-tensor eligibility per full model export.
- **P2:** native lease RED reproduction on exact RC1 before safety patch.
- **P3:** native Pack V1 port with fail-closed CLI — offline `pack_layout.py` is not a substitute.
- **P5:** independent native pack verification + same-cohort live A0/A1 (B0/B1 only after Path B gates). PGP-05 JSON screen cannot authorize these.

## 12. Next hardware-agent action

On an idle Arc 140V operator slot (no concurrent inference):

1. Checkout this integration branch at the published HEAD.
2. Re-run `py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v` and attach the receipt.
3. Capture sanitized PGP-00 snapshots for: NTFS drive root, one mounted folder if present, denied `fsutil`, denied IOCTL, and WDDM NOT_EXPOSED without substitution. Keep serials/private paths out of git.
4. Only then schedule P0 binary/module identity and native Pack V1 gates — do not promote Path B or runtime acceptance from this host tooling merge.
