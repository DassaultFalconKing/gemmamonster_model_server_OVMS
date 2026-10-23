# CIB2 / RC3B-postfix — конкретные кодовые работы и критерии выигрыша

Date: 2026-10-23. Status: IMPLEMENTATION PLAN, not runtime acceptance.

## Frozen dependency boundaries

- Release RC3B: annotated tag `qwm-semantic-refit-2026.4-rc3b` -> `b77b0f23fa7417e61778ef86ecb0ca739cc85f14`.
- Working RC3B-postfix: `freeze/rc3b-postfix-20261023-eb76a74f` -> `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`. The original `semantic-refit-2026.4` branch is NOT a writable CIB2 target.
- CIB2 implementation base: frozen working postfix tree plus CIB2 preflight docs/scripts/tests. Keep latest Qwen3Coder lossless arguments, Ornith tool-result template pin and Gemma EBNF whitespace fix.
- Exact binary lineage: RC3B tagged executable hashes are pinned, but **new working-postfix executable hashes are NOT yet pinned**. Never describe them as the same cohort.
- The actual serving SDK is `openvino_genai_windows_2026.4.0.0rc1_x86_64`, with stock GPU plugin. Upstream source tag `2026.4.0` is a *source reference*, not proof of byte-for-byte identity with that RC1 package.
- RC3B acceptance still explicitly awaits full `ovms_test` and owner signoff. A frozen source branch is not a frozen binary or a release acceptance.

## 1. Development packets (each yields one independently reviewable PR)

| Ticket | Work, exact seams | New behavior | Measurable gate / dependencies |
| --- | --- | --- | --- |
| **CIB2-00 SOURCE & BENCH LOCK** (P0) | Evolve `scripts/cib2/preflight_rc3b.py`; add versioned `manifest.schema.json`, verified load-path inventory and a reproducible baseline runner with output JSON. Pin SHA/size of *both* a tagged RC3B and the **new** working-postfix Windows executables separately, plus the SDK DLL set and GPU driver. | No accidental 2026.5 DLL mixing; no misleading perf comparisons; completely reproducible rollback. | Exact frozen source ancestry, SDK/active file-byte equality, individual artifact provenance, repeatable inputs, full suite status. Preserve `accepted=false` until owner approval. |
| **CIB2-01 PROTOCOL RETAINER GUARD** (P0) | Write cross-family regression harness under `tests/cib2/` and `scripts/cib2/`; use existing Qwen3Coder, Gemma4 and Ornith unit fixtures and actual tool-loop semantics. DO NOT rewrite parsers. Capture baseline Qwen string bytes, nested `1e3`, `1.10`, `9007199254740993`, quoted escape sequences, malformed typed args, tool-result replay and streaming fragments. | Guarantees that GPU/cache modifications cannot regress argument spelling, thinking/tool boundaries or publication of tool_calls. | Replay pinned saved Qwen focused 34/34 and full Qwen 81/81 where fixture provenance matches; Gemma EBNF whitespace `{0,2}`; live unary/SSE and C1/C2/C4 before promotion. Saved 81/81 XML is historical evidence only. |
| **CIB2-02 GRAPH & OTD ELIGIBILITY** (P0) | Read-only OVMS capability probe and model ledger. Source seams `src/llm/language_model/continuous_batching/servable_initializer.cpp` plus OpenVINO GPU `src/plugins/intel_gpu/src/plugin/ops/moe.cpp`. Log actual compiled `MOECompressed` / compatible graph, weights_path, model/export/key, `OFFLOAD_RATIO` and active GPU path. | Removes false claims that OTD is operating when the graph silently uses a different kernel; prevents nonsensical comparisons. | Per-checkpoint Qwen3.6/Ornith/Gemma4 capability proofs. `OFFLOAD_RATIO=0` control, 20/40/75 only where eligible; `100` is not “all on disk.” |
| **CIB2-03 OFFLINE REPLAY** (P0; no GPU dependency) | Adapt `86bab01e` simulator to `scripts/cib2/otd_sim/` with fixtures and deterministic test suite. Strict parser for layer/call/expert traces, incomplete-call invalidation; account cache hit/miss and physical vs logical bytes separately. | Repeatable cache-policy experiments without starting inference or mutating runtime. Enables rational optimization choices. | Reproduce exact LRU slot/hit/eviction sequence on valid traces; deny cache-policy promotion on truncated traces; synthetic C1/C2/C4 and lease overflow. |
| **CIB2-04 OTD LEASE SAFETY** (P1; isolated GPU fork) | Audit exact SDK RC1 source against 2026.4.0 native provider, then port **only** the non-mutating unique-expert capacity precheck from `7d905ba9` and required free-slot/eviction invariants. In source: `expert_weight_providers.cpp`, `lru_cache.cpp`; add GPU unit tests. Separately inspect V1 `124d0f44`, V2 `71efb7cb`, V3 `bdeed850`, V4 `591ab0b5` and `b5bfb148`, but port only proved defects. | Oversize simultaneous lease rejection no longer corrupts cache state or evicts useful experts. Reduces pathological reload thrashing and eliminates classes of stale slot/lifetime faults if reproduced. | Baseline RED before patch, GREEN after; exact LRU state unchanged on refusal; no wrong result on fallback; GPU in-flight reader, cancellation and multi-slot C1/C2/C4 tests. NO throughput improvement assumed. |
| **CIB2-05 OTD OBSERVABILITY** (P1; isolated GPU fork) | Minimal eventless/low-overhead adaptation of `4ff78eac`: `moe_otd_trace.{hpp,cpp}`, `moe_otd_runtime.*`, provider hooks; full counter snapshot/flush, trace integrity from `a973b006`. No extra `stream.finish()` or queue fence. | Separates read/transform/copy from MoE GEMV/dispatch latency; identifies reason for stalls, LRU hit rates and SSD traffic. | Flag-off outputs exactly match baseline, per-layer replay agrees with counters; compare decode/TTFT on/off (target overhead below noise, not a measured guarantee). Record process-global counters as such, not per-request telemetry. |
| **CIB2-06 PACKED EXPERT BACKEND** (P2; optional) | Port minimal `52f57df1` packed layout to compatible GPU source; one aligned contiguous 9-tensor record per expert; independent offline `build`, serving `off/use/require`; require integrity `2ed011fc`, pinned reader `359445cd`, atomic publish `65d4afca`. OVMS flag adapter only after native SDK parity. | Removes runtime scale/ZP transpose on cache misses and can replace ~9 positional reads per expert by 1. Faster warm/cold misses and reduced read syscall overhead **when I/O+transform are bottlenecks**. | 1-read/expert trace evidence, bit/quant/logits parity, missing/foreign/bit-flipped/truncated pack negative tests, concurrent builder/readers, complete A/B against unmodified CIB2 2026.4. Historically +10.5% r75 and +2.4% r40 on **slow 2026.5**, NOT prediction for RC3B. |
| **CIB2-07 UMA ADMISSION** (P2; OVMS/GenAI config) | Add read-only physical memory ledger first; later guarded admission for expert resident buffers + Windows cache + KV U4 + drafter + prefill workspaces and C1/C2/C4, keeping unsupported metrics explicitly `NOT_EXPOSED`. | Prevents swap storms/OOM when long context, multiple slots and OTD compete for the same 32GiB physical LPDDR; predictable fallback to plain/lower slots. | Unchanged tool-calling output, no hidden swap on stable workloads, measured allocations and resource consumption; refuse excess admission rather than silently changing quant/output. |
| **CIB2-08 SPECULATIVE-AWARE CACHE POLICY** (P3 research) | Only after real draft-vs-verify phase tracing with accepted/rejected token accounting, replay LRU/CLOCK/2Q, demand-first bounded prefetch and MTP K3 candidate. Xe2 `usm_host` separate feature-gated A/B. | Potential improvements in tail latency, SSD bytes per committed token and usable parallel slots; not inherently more tok/s. | Must improve a real RC3B workload vs native LRU without p95/p99 regression or increased NVMe amplification; agentic loops unchanged. |

## 2. No-go surfaces

- No cherry-pick of the 2026.5 GPU plugin binary, driver, `openvino.dll` or whole graph scheduler. Previous attempt mixed 2026.4/2026.5 DLLs and produced Windows error 127.
- No changes to pinned Gemma4 EBNF grammar, Qwen lossless numeric/string preservation, Ornith tool-result template, canonical CIB2 model snapshots or XGrammar unless explicitly new protocol work with independent RED evidence.
- No assumption that the old `2026.5` throughput measurements predict `2026.4`; historical 2026.5 throughput cratered ~32 -> 8 tok/s, and whether V1 specifically caused it is unproven.
- No new SSD pager, gratuitous cache policy replacement, `usm_host` default or CPU expert offload before workload data.

## 3. Expected outcome by user-visible behavior

| Improvement | Before / risk | After, if candidate passes |
| --- | --- | --- |
| Agent tool calls | GPU/OTD changes can accidentally disturb Qwen/Gemma structured outputs | Hard gate keeps exact Qwen argument string bytes and numbers, correct Gemma bounded JSON, Ornith memory boundary and streaming tool IDs. |
| Long agentic loops | Concurrent contexts risk LRU churn, resource pressure and silent abort | Bounded admission and transactional lease handling reduce avoidable restarts and unstable tail latency. |
| Large MoE on 32GiB Arc 140V | Native OTD may have many separate expert tensor reads and transform overhead | Packed path can eliminate transform and reduce read count; conditional gain at high miss rate, not a throughput guarantee. |
| Debugging | Native exit counters are opaque and can be missing on abnormal stop | Per-run/trace snapshots and offline replay identify slow phases and invalidate incomplete evidence. |
| Stable performance | 2026.5 regression could recur through indiscriminate backports | Pure 2026.4 RC1 plugin baseline remains oracle; every candidate has on/off A/B, binary hashes and rollback. |

## 4. Sequencing / responsibility

1. **Cloud code work (safe immediately):** CIB2-00 (manifest/harness), CIB2-01 (protocol no-change tests), CIB2-03 (simulator + synthetic fixtures), CIB2-02 static model/IR capability registry. Each in separate docs/scripts/tests path and independent PR.
2. **Local SDK audit and GPU work:** establish exact Windows RC1 SDK source/build, run RED for CIB2-04. Work in a separate compatible `DassaultFalconKing/openvino` worktree; do not install candidate DLL in RC3B runtime. Then P2 tracing.
3. **Experimental opt-in path:** only after verified 2026.4 binary/perf baseline, code packed OTD with hardening and cancellation tests. Promote individually or leave disabled.
4. **Admission + advanced scheduling:** later, driven by measured C1/C2/C4 and speculative acceptance traces.

Each coding PR is reviewed independently, commits preserve a working `STATE.md`, and no GPU test is labeled executed by cloud execution.

## 5. Numerical gates (targets; not reported measurements)

- Exact numerical/route parity: no regression relative to the same 2026.4 kernel/model.
- Source+unit+protocol: full suite green before release; pinned Qwen 81/81 historical suite is an input, not a blanket product acceptance.
- Cold/warm TTFT, decode tok/s, TPOT p50/p95/p99 and physical NVMe bytes per committed token: paired A/B with same model/IR/driver/seed/input tokens, >=1 warmup +3 measured repeats, C1/C2/C4.
- Candidate must not significantly reduce no-OTD speed or increase p95/p99 under representative workloads. Any proposed numeric threshold is a project gate, not a measured finding.
- RC3B tagged binary SHA applies **only** to the tag. Working postfix has new code and needs a new signed or checksum-pinned artifact identity before claiming deployment reproducibility.
- Acceptance stays NOT_ACCEPTED until owner signoff and the full native suite plus live agentic validation.

## 6. First author assignments

- **A / test and provenance:** implement full working-postfix build identity lock, collect sample runtime module map, make preflight `--strict` truly status-bearing, add negative-provenance tests.
- **B / replay tools:** port upstream experimental Python replay `otd_sim.py` with trace-v1 strictness; no Intel GPU source changes.
- **C / capability audit:** produce per-model checkpoint matrix from actual IR op eligibility, explicit `NOT_ELIGIBLE` vs `NOT_EXPOSED`, and no fabricated routes.
- **D / local GPU:** reproduce oversize cache mutation and build smallest possible fix against exact 2026.4 RC1, with separate line-specific patches for V1–V4 only if bug shown.

Release owner merges only independently passing gated candidates, not a large combined OTD port.
