# LFM Design C: adversarial review / semantic refit, 2026-10-27

Source lock: [PR #4697](https://github.com/openvinotoolkit/model_server/pull/4697), HEAD 990174b4bfc21e0d623c4917ea860246e929bc06.
Status: **partial code / BLOCK production wiring**. This review branch must not overwrite RC4, the candidate-final EXE, or active services.

## Findings

**C1 HIGH: wrong integration owner.** OutputParser::parseChunk routes plain non-envelope text through parseContentChunk -> contentParser (DefaultContentParser). Lfm2ToolParser::parseRetainedChunk receives tool-phase spans, not the prose-only pseudo-plans motivating Design C. Consequently, integrating demotion only at Lfm2ToolParser content emission does not solve the reported problem. Semantic refit must operate in the CONTENT-phase owner, with exactly-once segment buffering/flush at native-tool and generation-end boundaries. Prove prose-only routing first.

**C2 HIGH: false positives and API semantics.** A legitimate JSON response with a top-level plan/steps field, or documentation containing pseudo-tool markers, is indistinguishable from the proposed demotion heuristic without request context. Classifying it as reasoning_content may hide an answer that the user explicitly requested. reasoning_content is API-visible, not a security boundary. Parser-name gating determines family, not output intent. Design requires a fresh product decision on opt-in/request context before runtime wiring.

**C3 HIGH: streaming lifecycle.** Buffering all non-envelope content until termination removes token streaming for normal no-tool replies; the observed tool_choice=none prose hang would now also yield no visible partial answer. OutputParser::drainPendingDelta does not automatically flush an arbitrary private Lfm2ToolParser content buffer in CONTENT phase. Prove unary/SSE parity, START/STOP/LENGTH, partial markers, cancellation/reset, content-before-tool, trailing prose, and exactly-once flush. Cap combined retained bytes at 1 MiB.

**C4 MEDIUM: D2 ambiguity.** The specification alternately permits one pseudo-tool line in a paragraph or only all-pseudo-tool lines. The first formulation hides ordinary explanatory prose. Experimental classifier in this branch deliberately requires *all* nonempty lines to start with a pseudo-tool marker.

**C5 MEDIUM: classifier is not execution policy.** Nothing except a complete native Liquid envelope may publish executable tool calls. Leave required/named EBNF intact, auto unconstrained, and explicit parallel_tool_calls=false fail-closed. Do not import heuristic recovery of malformed Python or synthetic tag closures.

## Peer research and documentation

- The [vLLM LFM2 parser](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/lfm2_tool_parser.py) recognizes Liquid native tool sentinels. It also repairs malformed AST literals; those permissive semantics must NOT be adopted by our strict retainer.
- [OVMS PR #4411](https://github.com/openvinotoolkit/model_server/pull/4411) improves LFM2 tool history templates and reports BFCL gains. Compare history semantics rather than wholesale cherry-picking.
- [OVMS PR #4636](https://github.com/openvinotoolkit/model_server/pull/4636) refactors output parsing; compare phase ownership, but no upstream-wide merge into pinned 2026.4.
- [OVMS PR #4493](https://github.com/openvinotoolkit/model_server/pull/4493) prefers forgiving incomplete output structures; this conflicts with transactional fail-closed LFM publication.
- [vLLM issue #63309](https://github.com/vllm-project/vllm/issues/63309) and [issue #59218](https://github.com/vllm-project/vllm/issues/59218) illustrate real prose/truncated-tag loss and unary-vs-streaming divergence. Test both byte-for-byte.
- OpenVINO 2026.4 documentation and the actual pinned runtime must both be consulted before wiring the u4 launch setting; do not confuse a GraphConfig property with a server CLI flag.

## Measured speed: independently verified vs claimed

The 2026-10-27 handoff reports r0 about 55 decode tok/s, r20 31.53, r30 23.96, r0+u4 58.54 and r20+u4 32.41 on Arc 140V. The detailed MEMORY-PRESSURE-REPORT and raw runs live outside GitHub. This review cannot recompute sample statistics, confidence intervals, GPU residency, or cause of cliff. Therefore these are **machine-reported measurements**, not independent reviewer reproduction.

Treat offload as a capacity trade-off, not an acceleration. u4 helps the r0 cohort but does not recover r20. Source of cliff needs device traces and transfer counters. For offload greater than zero, the handoff requires WEIGHTS_PATH pointing to openvino_model.bin and a persistent CACHE_DIR. Do not generalize a short benchmark to long context.

u4 should be an LFM2.5-specific, measured profile with a clear rollback, not a global default on Qwen/Gemma/LFM2-24B. The start-lfm25.ps1 source still has not been modified in this branch.

## Diagnose the tool_choice=none prose hang

Capture (1) raw SSE bytes and terminal DONE, (2) finish_reason/usage, (3) last token timestamp versus client read timeout/EOF, (4) rendered final prompt and generation config, (5) raw generated tokens versus output-parser deltas. Separate model generation hang, streamer termination, parser flush and client read-loop bugs. Harness skip-final-prose is not a product fix.

## Code delivered in this review branch

- src/llm/io_processing/lfm2/thought_demotion.hpp: standalone C++17 pure predicate, no tool promotion or tokenizer dependence.
- src/test/llm/output_parsers/lfm_thought_demotion_review_test.cpp: focused positive/negative gtest.
- src/llm/BUILD: declaration of the new header.
- Host g++ -std=c++17 -Wall -Wextra -Werror -pedantic standalone sanity: 12 assertions PASS in review environment.

NOT_RUN: OVMS Bazel/gtest, Windows MSVC build, live GPU, u4 launch A/B, and peer-server differential. No OutputParser production wiring has been added.

## Required next gate

1. Fix the Design C architecture to demote at CONTENT ownership, not inside the tool-only phase. Prove prose-only pseudo-plan routing.
2. Decide false-positive policy: preserve legitimate JSON plan and Markdown documentation unless explicitly allowed to classify them.
3. Add RED OutputParser tests for prose-only D1/D2, native tool following pseudo-plan, text after tool, malformed/truncated spans, repeated turns, cancellation, and unary/SSE reconstructed parity. Use actual LFM2.5 tokenizer.
4. Build and refit the minimum safe content segment hold/flush implementation. Do not break native retainer, LFM2-24B tool-only, Gemma or Qwen. Run regression and owned Arc 140V smoke.
5. Diagnose the prose hang independently. Wire u4 only through the confirmed successful configuration route, then record paired r0 A/B metrics.

Do not modify Pack/CIB2, GenAI/Minja binary cohort, release binaries or port 8137 control process for this review.
