# UMA-02 PLAN — Acceptance matrix (tests first)

**Gate:** UMA-02 scratch prototype / harness acceptance  
**Depends on:** [DESIGN.md](./DESIGN.md) (path B) + UMA-00 evidence  
**Default mode:** specify cases first; implement only tiny host harness/docs already expected — **no** production allocator switch, **no** GPU soak without COMPUTE_GO  
**Linux:** `LINUX_DEFERRED_NO_MACHINE`

### SHA locks (copy into every UMA-02 evidence run)

| Artifact | SHA / ref |
|---|---|
| Wave-01 OpenVINO (integrity + fill) | `74003278a9c8925fcda7bc32ceb27320e59bbb1d` |
| Cohort baseline (alloc / copy_from) | `479219245f6f10b670367ad35af16513d72d2091` |
| UMA-00 evidence PR HEAD | `e320a59c6b44e64945d1797495383be3873f1b75` |
| This design pack | (commit on `docs/uma-01-design-20261022`) |

---

## 1. Goals

Prove that a path-B fill (CPU-visible residents + verify-then-scatter + fence + `set_filled`) is:

1. **Byte-identical** to path A (`usm_device` + `copy_from`) for successful fills.  
2. **Fail-closed** on corrupt records (no resident mutation before verify; no `set_filled`).  
3. **LRU-safe** (no false hit after failed verify).  
4. Runnable **host-only** wherever possible; GPU-live cases explicitly **COMPUTE_GO-gated**.

---

## 2. Environment classes

| Class | Meaning | When allowed |
|---|---|---|
| **HOST** | CPU + optional OpenCL USM alloc/query; no MoE GEMM; no model inference | Always on this Windows box |
| **GPU_LIVE** | Kernels read residents / full OTD miss path under load | Only with explicit **COMPUTE_GO** (currently **absent** — Wave-01 GPU PENDING_AUTHORIZATION) |
| **LINUX** | Same matrix on Linux UMA/iGPU | `LINUX_DEFERRED_NO_MACHINE` — do not FAIL Windows for absence |

Mark every case with `Env: HOST | GPU_LIVE`.

---

## 3. Acceptance matrix

### 3.1 Byte-parity vs path A

| ID | Case | Env | Setup | Steps | Pass criteria | Fail criteria |
|---|---|---|---|---|---|---|
| **U2-P01** | Single-expert slot parity | HOST | Tiny synthetic pack v1 (known payloads + checksums); allocate nine residents path A (`usm_device`) and path B (`usm_host`) with identical logical layouts / slot count | Fill expert E→slot S via path A; independently fill E→S via path B after verify; dump `slot*size … +size` for all nine tensors | All nine regions bitwise equal | Any byte differ; either path skipped verify |
| **U2-P02** | Multi-slot no crosstalk | HOST | Capacity ≥ 2; fill E0→S0 and E1→S1 on both paths | Compare each slot region | Parity per slot; S0 bytes unchanged by E1 fill | Crosstalk or mismatch |
| **U2-P03** | Evict-then-refill parity | HOST | Capacity 1; fill E0; fill E1 (evicts E0); refill E0 | Path A vs B dumps for final E0@slot | Final slot matches path A for E0 | Stale E1 bytes remain after B refill |
| **U2-P04** | Zero-size tensor skip | HOST | Pack with one tensor_bytes=0 (if representable) or null mem ptr | Fill; compare remaining tensors | Same skip behavior as path A; no crash | Touches zero-size buffer incorrectly |

**Oracle:** path A implementation at Wave-01 `fill_weights_from_pack` + `copy_from` (`74003278` / cohort `copy_from` semantics). Path B must not change pack bytes.

### 3.2 Corrupt-record negatives (before `set_filled`)

| ID | Case | Env | Setup | Steps | Pass criteria | Fail criteria |
|---|---|---|---|---|---|---|
| **U2-N01** | Checksum mismatch | HOST | Valid pack; flip ≥1 payload byte in staging after read **or** use pack with wrong stored checksum for expert E | Invoke path B fill for E | Throws `PackIntegrityError` (or provider-wrapped equivalent); **zero** bytes written to any of nine residents vs pre-fill snapshot; `set_filled` not called; `is_filled`/hit false | Any resident byte changed; hit true; silent accept |
| **U2-N02** | Verify-before-scatter ordering | HOST | Instrument or assert-order harness | On N01 path, assert scatter helper not entered | Scatter entry count = 0 on integrity fail | Scatter called before/without verify |
| **U2-N03** | Header/table reject (if exposed) | HOST | Truncated / bad header pack | Open/bind fails closed before miss fills | No residents published as filled | Partial bind with filled slots |
| **U2-N04** | Mid-scatter abort simulation | HOST | Inject throw after tensor t=3 of 9 | Catch; check filled bit; optional snapshot | `set_filled` false; subsequent successful fill restores full nine-tensor parity (U2-P01) | `set_filled` true; hit serves partial expert |

### 3.3 No false LRU hit after failed verify

| ID | Case | Env | Setup | Steps | Pass criteria | Fail criteria |
|---|---|---|---|---|---|---|
| **U2-L01** | Remap without hit | HOST | Capacity ≥ 1; corrupt E | `acquire_slot(E)` → integrity fail; then `lookup(E)` / `acquire_slot(E)` again with **fixed** pack still corrupt | First and second attempts: `hit == false`; filled bit false | `hit == true` after failure |
| **U2-L02** | Recover then hit | HOST | After U2-L01, repair pack or switch to good record for E | Successful fill; lookup again | First success: miss→fill; second: `hit == true` only after success | Hit before success; or never hits after success |
| **U2-L03** | Unrelated expert isolation | HOST | Corrupt E0; good E1 | Fail E0; succeed E1 | E1 may hit after fill; E0 still unfilled / non-hit | E0 appears hit; E1 blocked |

### 3.4 Allocator / visibility (host-capable)

| ID | Case | Env | Setup | Steps | Pass criteria | Fail criteria |
|---|---|---|---|---|---|---|
| **U2-A01** | Resident type under flag | HOST | Build/run with path B flag on | Query `get_allocation_type()` on nine OTD residents | All are `usm_host` (or documented lockable host USM) | Still `usm_device` while flag on |
| **U2-A02** | Default flag off | HOST | Production-shaped config / flag unset | Same query | Residents remain `usm_device` (path A) | Accidental host alloc without flag |
| **U2-A03** | Fence before publish | HOST | Hook/order assert around `set_filled` | Successful path B fill | Fence API invoked after last scatter, before `set_filled` | `set_filled` without fence |

### 3.5 GPU-live (COMPUTE_GO gated) — specify now, run later

| ID | Case | Env | Pass criteria (when authorized) | Status now |
|---|---|---|---|---|
| **U2-G01** | Kernel reads path-B slot match path-A reference output for fixed MoE op | GPU_LIVE | Numerics within existing OTD tolerance vs path A on same weights | **BLOCKED** — no COMPUTE_GO |
| **U2-G02** | Miss latency / copy-byte counters under one cold miss | GPU_LIVE | Counters recorded; no claim of win required for UMA-02 PASS | **BLOCKED** |
| **U2-G03** | Concurrent miss + eviction under stream | GPU_LIVE | No false hit; no use-after-evict under Wave-01 lease rules | **BLOCKED** |

UMA-02 **overall** may be marked `HOST_PASS` without G01–G03. Do **not** mark `COMPUTE_GO` or `UMA-03 READY` from host-only results.

---

## 4. Suggested harness shape (tiny, optional)

Prefer a **host-only** executable or gtest adjacent to MoE OTD pack tests:

```text
uma02_parity_harness
  --pack <path> --expert <id> --slot <n>
  --mode a|b|compare
  --dump-dir <out>
```

| Piece | Notes |
|---|---|
| Pack | Reuse Wave-01 pack builder / tiny fixture (nine small tensors) |
| Path A | Existing `fill_weights_from_pack` + device USM |
| Path B | Same fill with host USM + scatter helper (scratch only) |
| Compare | `memcmp` dumps; exit non-zero on diff |
| Negatives | Mutate payload or checksum table; expect throw + unchanged dump |

**Do not** wire into OVMS production binaries. **Do not** land in golden C6.

If coding is not yet authorized: leave this section as the spec; implement harness in a later UMA-02 coding session.

---

## 5. Evidence to collect per run

For each executed case ID:

1. Command line + cwd + UTC timestamp  
2. OpenVINO SHA + flag values  
3. PASS/FAIL/NOT_RUN/BLOCKED_COMPUTE_GO  
4. For parity: checksums (e.g. FNV or SHA-256) of nine dumps path A vs B  
5. For negatives: exception type/message; before/after resident digests  
6. Explicit statement: `COMPUTE_GO=false` unless operator flips it  

Suggested local mirror: `C:\gm\orchestration\uma-02-windows-YYYYMMDD\evidence\` (create when running, not required for this design publish).

---

## 6. Exit criteria

| Label | Meaning |
|---|---|
| **UMA-02 HOST_PASS** | U2-P01–P03, U2-N01–N02, U2-L01–L02, U2-A01–A03 PASS on this Windows host |
| **UMA-02 HOST_FAIL** | Any required HOST case FAIL |
| **UMA-02 GPU_BLOCKED** | Expected today — G01–G03 NOT_RUN |
| **UMA-03 eligible** | Only after HOST_PASS **and** COMPUTE_GO for GPU_LIVE cases / perf |

**Non-exit:** merge to production, Wave-01 enablement, driver changes, Linux PASS.

---

## 7. Mapping back to DESIGN invariants

| Design invariant | Covered by |
|---|---|
| Pack v1 unchanged | Fixture uses v1; parity oracle |
| Nine-tensor layout | P01–P03 dumps all nine |
| Fail-closed integrity | N01–N04, L01 |
| Fence before publish | A03 (+ G01 when live) |
| Default production path unchanged | A02 |
