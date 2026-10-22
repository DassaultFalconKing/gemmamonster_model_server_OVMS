# 12 — Review P0–P6 before heterogeneous agent execution

**2026-10-22. Status: REVIEW / NOT AN IMPLEMENTATION.**

## Provenance

Reviewed incoming 303-line attachment GEMMAMONSTER: исполняемый план задач для кодящих агентов P0–P6 (user-uploaded deep-research-report(4).md, NOT in GitHub). Its citation markers are **not resolvable inside a fresh agent worktree**; replace with pinned URLs/SHAs or mark SOURCE_UNVERIFIED. Compared with [09-ARCHITECTURE-PLAN-V2.md](09-ARCHITECTURE-PLAN-V2.md), [06-IMPLEMENTATION-ROADMAP.md](06-IMPLEMENTATION-ROADMAP.md), [07-MODEL-AND-DRAFTER-BASELINES.md](07-MODEL-AND-DRAFTER-BASELINES.md), the [frozen measured checkpoint](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/4215aa39da160eb742ecd7f0fa2ace5c90d64efa/docs/qwenmonster/CHECKPOINT-OTD-PACK-QWM01-20261022.md), and current integration `746dc833dc3bcccf64fabdb469feda9260582bae` with newly added [HOT_COLD_EXPERTS_ARCHITECTURE.md](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/746dc833dc3bcccf64fabdb469feda9260582bae/docs/qwenmonster/HOT_COLD_EXPERTS_ARCHITECTURE.md).

## Verdict: adopt only after corrections

The incoming plan is strong on native OTD ownership, capability before optimization, U4 KV and single physical 32-GiB UMA, P2→P3→P5 evidence dependency, and one-worktree-per-task. But **it predates deployed integration work and must not be executed literally**.

| Priority | Gap | Correction |
|---|---|---|
| **BLOCKER** | **A4 / PR-OTD-PACK** proposes writing a new packer and transform elimination | These exist already: pack build/require, 4KiB expert-major files, one read/miss, 40 packs, 4 packed/unpacked r40/r75 bench cells. Change A4 into pack payload integrity, negative tests, existing OVMS/GPU unit filters and packaging review. |
| **BLOCKER** | **A2** assumes telemetry is still only exit counters | GPU fork already has `MOE_OTD_TRACE`, release counter fix, offline summaries, 43 standalone GPU tests. Audit gaps: graceful flush, phase/request identity, OS physical reads and timing attribution; do not rebuild working infrastructure. |
| **BLOCKER** | **A3S** proposes new native LRU simulator | 31,306-event C++ vs Python LRU parity already gave zero differences. Extend to real traces with draft/verify/commit, C1/C2/C4, not rewrite. |
| **BLOCKER** | Model targets skip **AEON Ornith** | Treat Ornith as separate Qwen3.6 derivative, checkpoint, tokenizer/template and expert profile, with its own MTP/DFlash feasibility gate. |
| **BLOCKER** | Only C6 and 2026-10-21 research counted | Add accepted C6, QWM01 measured `85c37fcfb`, current integration `746dc833`, measured OpenVINO GPU fork `479219245`, plus new hot/cold research. |
| **BLOCKER** | No explicit pack payload-integrity issue | In measured code serving `require` uses `PackLayout::open` without full `verify_pack` for data records. Source identity is sampled non-cryptographic hash. Design and test bitflip/wrong-model/truncation handling without claiming full startup verification exists. |
| **HIGH** | A1D MTP/DFlash sounds enabled | Short K1/K2/K3 MTP smoke was **unpacked**; MTP K3+packs NOT RUN; AEON DFlash startup failed missing target hidden-state metadata. OpenVINO compatible IR and loaded runtime strategy are required. |
| **HIGH** | Trace for all three models assumed | If a model graph does not lower to eligible OTD, mark NOT_ELIGIBLE with evidence. Do not silently substitute legacy Qwen3-30B as product proof. |
| **HIGH** | Logical expert read counters equated to physical NVMe bytes | File reads/OS page cache and physical device reads differ. Async disk, copy and compute timings can overlap, so additive TPOT cost allocation is not generally valid. Distinguish metric provenance. |
| **HIGH** | Fixed six-week calendar, automatic bench | Agent-days/Gantt are estimates; **operator compute pause remains in force**. Static work, offline harness and lightweight tests are allowed; no unapproved inference servers or benchmark jobs. |
| **HIGH** | Rigid “≥5% throughput or ≤10% bytes” gate | Those are proposed project thresholds, not accepted measurements; use paired workloads, correctness, tail latency, confidence, memory pressure and actual bytes/committed token. |
| **HIGH** | New model-specific memory and precision hypotheses | Current hot/cold architecture correctly separates **residency hotness** and **precision hotness**. Proposed Qwen3.8 PLE placement, full-resident Gemma4/Qwen3.6, mixed-quant and traffic values require exact IR/layout/hardware validation. |
| **HIGH** | Coordinator delegates within inherited model/session | Require independent fresh child sessions, explicitly selected available model/provider, isolated permissions and worktrees; independent review in a different family when possible. No claim of heterogeneous delegation without evidence of model IDs. |

## Corrected DAG

~~~mermaid
flowchart TD
  B["Bootstrap / source + model/provider registry"]
  A0["A0 pinned model/IR capability"]
  A0R["A0R references / source provenance"]
  A4["A4 pack integrity hardening"]
  A1["A1 protocol / baseline harness"]
  A1D["A1D drafter compatibility"]
  A2["A2 telemetry gaps"]
  A3T["A3T real speculative routing traces"]
  A3S["A3S replay / candidate simulation"]
  A5["A5 optional cache/I/O policy"]
  A6["A6C/A6X optional compute studies"]
  A7["A7 separate integration acceptance"]
  B --> A0 & A0R & A4
  A0 --> A1 & A1D & A2 & A6
  A1 --> A3T
  A1D --> A3T
  A2 --> A3T
  A3T --> A3S --> A5
  A1 --> A7
  A4 --> A7
  A5 --> A7
~~~

A4 offline pack-negative tests can proceed **in parallel with static P0**; it does not need a new P2 to rediscover the packer. A3S must match native LRU before testing CLOCK/2Q, and A5 is forbidden before A3S evidence. A6C and A6X are optional, not blockers.

## Unambiguous evidence hierarchy

`SOURCE_CONFIRMED` ≠ `BUILD_PASS` ≠ `UNIT_PASS` ≠ `OFFLINE_REPLAY_PASS` ≠ `HTTP_PASS` ≠ `LIVE_PASS` ≠ `AGENTIC_PASS` ≠ `ACCEPTED`. Use explicit `NOT_RUN`, `NOT_ELIGIBLE`, `BLOCKED`, `FAIL`, `SOURCE_UNVERIFIED`. Accepted status is the **operator's release decision**, never autonomously assigned.

Frozen source evidence: 4 short packed/unpacked runs, 43 standalone GPU unit PASS; Qwen parser 69/69, generation policy 9/9, controlled HTTP and tool continuations. **Not accepted:** MTP K3 + packs, complete pack test filters, 100/100 tool calls, true multi-slot agent loops, cancellation resource reclamation, corruption on serve-path require, complete per-request NVMe instrumentation.

## Scheduling and security

Coordinator may organize **real independently addressable models** from Anthropic, OpenAI/Codex, Google/Gemini, local OVMS/OpenCode or other available providers, after capability discovery, without presuming access to them. Do not assign more than one active author to a mutable code path. Author and reviewer must not share the same context or worktree. Do not expose secrets, raw prompts, private paths or private test traces. No automatic merging, no C6/lock mutation, no force pushing, no operator-unapproved GPU jobs.

**Implementation command:** [13-HETEROGENEOUS-COORDINATOR-PROMPT-20261022.md](13-HETEROGENEOUS-COORDINATOR-PROMPT-20261022.md). It supersedes only the Anthropic-only agent assignment policy of [11](11-MODEL-EXECUTION-LEDGER-20261022.md), not the target-model or U4 memory ledgers.
