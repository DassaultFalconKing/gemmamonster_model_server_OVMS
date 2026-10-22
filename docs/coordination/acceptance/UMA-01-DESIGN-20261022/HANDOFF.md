# UMA-01 HANDOFF — Path B design complete; coding not started

**Date:** 2026-10-22  
**Decision carried forward:** `UMA_B_PROTOTYPE_READY_FOR_DESIGN` → **design published**  
**This pack:** `docs/coordination/acceptance/UMA-01-DESIGN-20261022/`  
**Prior pack:** `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/`  
**Docs branch:** `docs/uma-01-design-20261022` (docs-only; **do not merge** without operator approval)

---

## 1. Paths (canonical in OVMS docs tree)

| Deliverable | Path |
|---|---|
| Design | `docs/coordination/acceptance/UMA-01-DESIGN-20261022/DESIGN.md` |
| UMA-02 plan | `docs/coordination/acceptance/UMA-01-DESIGN-20261022/UMA-02-PLAN.md` |
| Handoff (this file) | `docs/coordination/acceptance/UMA-01-DESIGN-20261022/HANDOFF.md` |
| Index | `docs/coordination/acceptance/UMA-01-DESIGN-20261022/README.md` |
| UMA-00 verdict | `docs/coordination/acceptance/UMA-00-WINDOWS-20261022/VERDICT.md` |
| Local UMA-00 evidence | `C:\gm\orchestration\uma-00-windows-20261022\` |

Optional local mirror of this design: `C:\gm\orchestration\uma-01-design-20261022\` (docs copy only).

---

## 2. SHA index

| Artifact | SHA / URL |
|---|---|
| Wave-01 OpenVINO (wt-integration tip inspected) | `74003278a9c8925fcda7bc32ceb27320e59bbb1d` |
| OpenVINO Draft PR #7 | https://github.com/DassaultFalconKing/openvino/pull/7 @ `74003278…` — host PASS; GPU **PENDING_AUTHORIZATION** |
| Cohort baseline | `479219245f6f10b670367ad35af16513d72d2091` |
| UMA-00 evidence PR #21 HEAD | `e320a59c6b44e64945d1797495383be3873f1b75` — https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/21 |
| ADR parent | `8e03f6ae285b381a2abfb46c6c11d46be5079b27` / Draft PR #20 |
| Golden C6 | `ba6ec792c3121850fea167fa7d7e190b25fcdc76` — **READ ONLY / untouched** |

---

## 3. One-paragraph design summary

Path B keeps pack v1, nine resident tensors, and Wave-01 fail-closed verify: on a miss, read the expert record into CPU staging, checksum it, then **CPU-scatter** verified slices into nine **`usm_host`** slot regions (instead of `usm_device` + `enqueue_memcpy`), issue an explicit stream fence because `CacheCoherentUMA=false`, and only then `set_filled`. Production default and Wave-01/C6/OVMS stay on path A until a separate enablement gate; UMA-02 proves host byte-parity and corrupt/LRU negatives without assuming COMPUTE_GO.

---

## 4. Open questions / risks that block coding

1. **Fence primitive on Arc 140V NEO** for host-written `usm_host` → GPU kernel visibility (finish vs marker vs mandatory tiny memcpy) — must be chosen and proven before claiming prototype correctness beyond CPU dumps.  
2. **No COMPUTE_GO** — cannot validate kernel reads, miss latency, or eviction-under-fire; do not run GPU inference/soak.  
3. **`usm_host` GEMM bandwidth** unknown vs `usm_device` on this driver — UMA-03 only; could erase miss-path wins.  
4. **Mid-scatter partial mutation** policy (overwrite-on-retry vs scrub) needs a conscious pick before implementing the scatter helper.  
5. **Operator authorization** for a non-shippable OpenVINO scratch branch — without it, stay at docs/harness-spec only.  
6. **Windows memory pressure** — host USM still competes in the same LPDDR/WDDM pool; pin-limit changes remain out of scope.

None of these reopen the UMA-00 topology verdict; they gate **implementation**, not this design publish.

---

## 5. Explicit governance statements

| Statement | Value |
|---|---|
| Merge this docs PR? | **NO** without operator approval |
| COMPUTE_GO assumed? | **NO** |
| Production allocator switch? | **NO** |
| Wave-01 / golden C6 / production OVMS edits? | **NO** |
| Driver / BIOS / pin limit? | **NO** |
| Linux | `LINUX_DEFERRED_NO_MACHINE` |
| Independent of enabling OTD in production? | **YES** |

---

## 6. Recommended single next action

**Wait for operator approval, then implement a host-only UMA-02 parity + corrupt/LRU harness on an isolated OpenVINO scratch branch (flag default off) — do not start GPU_LIVE or production enablement.**

If the operator prefers sequencing: complete Wave-01 GPU authorization / COMPUTE_GO first only if G01 is required before any scratch coding; otherwise HOST cases U2-P/N/L/A can proceed without it.

---

## 7. Parent return checklist

- [x] DESIGN / UMA-02 plan / HANDOFF paths  
- [x] One-paragraph design summary (§3)  
- [x] Open questions / risks that block coding (§4)  
- [ ] Draft PR URL (filled when opened)  
- [x] Recommended next action (§6)  
- [x] Explicit: no merge, no COMPUTE_GO assumed  

**Draft PR URL:** _(pending push)_
