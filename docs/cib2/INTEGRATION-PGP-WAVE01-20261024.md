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

No drift was observed against the pinned SHAs at fetch time. Older worker branch `feature/cib2-pgp02-20261024` was **not** re-imported.

## 2. Final integration SHAs

| Item | Value |
|---|---|
| Integration branch | `feature/cib2-pgp-wave01-cursor-integration-20261024` |
| Worktree | `C:\Users\testc\cib2-pgp-integration` (isolated) |
| Cherry-pick equivalents | `f10030d8f`, `020a4a4b4`, `a8f405074`, `81f1cb58d` |
| Host fixture/privacy fix | `f1b0560099207f9fba892f986628a9a475acc37f` |
| Volume-root output-path fix | `85533a507` (allow private snapshot outside a probed drive-letter volume root) |
| Final HEAD at documentation time | recorded in the docs commit that adds this receipt; confirm with `git rev-parse HEAD` |

## 3. Changed files (vs coordinator base)

All paths remain inside the allowed boundary:

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
- `tests/cib2/test_pack_layout_numeric_review.py`
- `tests/cib2/test_storage_geometry.py`
- `tests/cib2/test_storage_geometry_review.py`

`git diff --check` against base: clean. No OVMS/runtime/GPU/plugin/model/binary/hook changes.

## 4. Conflict resolution

Cherry-picks applied without unresolved conflict markers. `docs/cib2/README.md` retains separate pointers to PGP-00, PGP-02 (coordinator-hardened), and PGP-05. PGP-02 coordinator protections from `a2ccb127` remain intact; worker PGP-02 was not re-applied.

## 5. Findings A / B / C

### Agent A — PGP-00 / Windows geometry

Host execution exposed four failures after integrating PR #24 hardening onto the original unit fixtures:

1. **High / test fixture:** `VOLUME_DISK_EXTENTS` helper omitted the 4-byte pad before the extent array (offset 8). Hardened parser correctly refused a mis-packed 2-extent buffer.
2. **High / test fixture:** `STORAGE_DEVICE_DESCRIPTOR` fixture wrote `ASXA01\x00` into a 6-byte slice, dropping the NUL and gluing revision to serial.
3. **Medium / test vs Windows shape:** access-alignment test treated `Version==28` as invalid; Windows commonly returns `Version==Size==28`, which the hardened parser accepts. Foreign versions (e.g. 99) still fail closed.
4. **Medium / public summary:** stdout privacy assertion collided with the word “serials” in the operator note. Note reworded to “device identity strings”; tests assert absence of `serial_number` fields and concrete serial values.

Code behaviour for WCHAR counts, `GetVolumePathNameW`, truncated extents, drive-root-only device mapping, NOT_EXPOSED preservation, and non-additive memory ledgers matches the review suite.

### Agent B — PGP-02 / Pack V1 placement

Targeted suite **44/44 PASS**. Coordinator numeric fail-closed from PR #24 commit 3 is present. No native Pack V1 changes. Latent-review notes (if any beyond PASS) do not block `HOST_READY`.

### Agent C — PGP-05 / Benchmark screening

Targeted suite **15/15 PASS**. Screen emits `OFFLINE_REVIEW_ONLY` or `BLOCKED`, always `runtime_acceptance=NO`, `promotion_authorized=false`. Physical device-counter bytes stay separate from logical reads.

## 6. Defects fixed on the integration branch

Commit `f1b056009`:

- Align extent/descriptor fixtures with Win32 layouts used by hardening.
- Accept documented access-alignment Version 28 while still rejecting foreign versions.
- Keep public stdout free of concrete serial values / `serial_number` fields.

Commit `85533a507`:

- Drive-letter volume-root probes (`C:\`) no longer treat the entire volume as the probed source tree for output containment, which previously blocked every same-volume `%TEMP%` snapshot. Exact probed-path overwrite and in-tree outputs remain refused.

Post-audit hardenings (separate integration commits):

- **PGP-00:** refuse JSON output beside a probed *file* (sibling overwrite protection).
- **PGP-02:** when offline fallback retains identity placement, set `strategy_effective` to `identity` (not the requested frequency/coaccess label).
- **PGP-05:** require A0/B0 and A1/B1 pairs to share `pack_manifest_sha` so resident-mode contrasts are not confounded by different packs.

## 7. Targeted test results

Interpreter: **Python 3.14.6** (`py -3`).

| Suite | Result |
|---|---|
| `py_compile` storage/pack/benchmark | PASS |
| `test_storage_geometry*.py` | **41/41 PASS** (includes volume-root + sibling-file output guards) |
| `test_pack_layout*.py` | **44/44 PASS** |
| `test_benchmark_screen.py` | **16/16 PASS** (includes same-layout pack identity) |

## 8. Full host suite

```text
py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v
Ran 168 tests in ~0.5s
OK
```

Do **not** treat historical “67/67” receipts as this run’s count. Actual integration receipt: **168 PASS / 0 FAIL / 0 SKIP**.

## 9. Windows hardware status

Read-only PGP-00 probe executed on this Windows host against a temp directory (private snapshot kept under `%TEMP%`, not committed):

| Probe | Status | Note |
|---|---|---|
| volume.filesystem_information | EXPOSED | |
| volume.allocation_geometry | EXPOSED | |
| volume.sector_sizes_fsutil | NOT_EXPOSED | Access denied (Error 5) — preserved, not defaulted |
| memory.physical / commit | EXPOSED | |
| memory.video_wddm_always_separate_ledger | NOT_EXPOSED | DXGI probe disabled by coordinator (ABI caution) |
| device.identity / disk0 | EXPOSED | private file only; stdout sanitized |
| runtime_acceptance | NO | |

Mounted-folder live case: **NOT_RUN** (no dedicated mount fixture on this host). Probing `C:\` with output under `%TEMP%` correctly fail-closed (output inside probed tree). No native inference / OTD / GPU session was started.

## 10. Native Pack V1 and GPU acceptance

| Gate | Status |
|---|---|
| Native Pack V1 P3/P5 | NOT_RUN / NOT_GRANTED |
| 2026.4 GPU live inference | NOT_RUN / NOT_GRANTED |
| Source/build/module identity (P0) | UNVERIFIED / open |
| Compiled eligibility (P1) | open |
| Runtime / production acceptance | **NO** |

## 11. Residual blockers (P0/P1/P2/P3/P5)

- **P0:** bind working-postfix EXE/DLL hashes to exact build inputs; loaded-module evidence on operator host.
- **P1:** compiled expert-kind / nine-tensor eligibility per full model export.
- **P2:** native lease RED reproduction on exact RC1 before safety patch.
- **P3:** native Pack V1 port with fail-closed CLI — offline `pack_layout.py` is not a substitute.
- **P5:** independent native pack verification + same-cohort A0/A1 (and later B0/B1 only if Path B gates pass). PGP-05 JSON screen cannot authorize these.

## 12. Next hardware-agent action

On an idle Arc 140V operator slot (no concurrent inference):

1. Checkout this integration branch at the published HEAD.
2. Re-run `py -3 -m unittest discover -s tests/cib2 -p "test_*.py" -v` and attach the receipt.
3. Capture sanitized PGP-00 snapshots for: NTFS drive root, one mounted folder if present, denied `fsutil`, denied IOCTL, and WDDM NOT_EXPOSED without substitution. Keep serials/private paths out of git.
4. Only then schedule P0 binary/module identity and native Pack V1 gates — do not promote Path B or runtime acceptance from this host tooling merge.
