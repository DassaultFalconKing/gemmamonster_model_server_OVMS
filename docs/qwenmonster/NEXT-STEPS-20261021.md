> Implementation checkpoint: R1 result/cleanup hardening implemented with18/18 offline tests; executing-source hashes and absolute external paths bound to a new sealed preparation. Native R1 execution remains NOT RUN. Concrete legacy success gating traced statically; parser/CB terminal and cancellation changes still require actual RED. See R1-RUNNER-HARDENING.md.

> External checkpoint: existing-server negative -> positive -> receipt continuation PASS with captured shell exit0. See EXTERNAL-GATES-20261021.md. Low available RAM now precedes stress/build work. Static review confirms visible API paths retain the actual finish reason; proposal A remains a parser/legacy investigation, not an established API mapping defect. R1 native execution remains NOT RUN; harden exact-row and timeout checks first.

# OVMS / Qwenmonster: measured status and proposed next work

Updated 2026-10-21. **ACCEPTED: NO.**
Scope is OVMS and the GenAI/XGrammar/tokenizer cohort needed by its Qwen path.
Unrelated agent-platform troubleshooting is outside this plan.
This is a status update and engineering proposal; no new product implementation,
native build or inference run is implied.

## Measured checkpoint

Evidence documentation commit: `f803da18b0802cf16223fc032039bafb3ce6534f`.
Continuation/transport tested source: `5c777c174a80f0d72175985d963c8831da522761`.
See STATUS-20261021.md and FOLLOWUP-20261021.md for the exact evidence scopes.

| Area | Current result | Remaining boundary |
|---|---|---|
| OVMS product and full diagnostic target | Built; request QWM 2/2, tool controls 11/11, Qwen/Gemma parsers 148/148 PASS | No full-suite or release acceptance claim |
| QWM-01 | Shared restricted schema validation implemented; unit and negative HTTP gates measured | Positive-after-errors and broader live policy matrix incomplete |
| Ornith smoke | Unary, SSE, zero-arg, required city and none PASS | Does not establish all schemas, prompt modes or decoder masks |
| Tool-result continuation | 20/20 PASS, 10 unary + 10 SSE | Controlled two-turn stub replay; autonomous/subagent and concurrent workloads NOT RUN |
| HTTP400 | 17/17 negative cases PASS, including 2 streaming requests | Positive-after-errors and Hermes transport NOT RUN |
| XGrammar R1 candidate | Source/native evidence reviewed; 28-row immutable matrix prepared | Matrix build/run NOT RUN; prior R1 binary/run linkage incomplete |
| Dependency cohort | Published lock unchanged | Candidate #802 absent from installed GenAI; isolated rebuild NOT RUN |
| XML #650 / inherited required-key gap | OPEN | Decoder-mask correctness remains independent of parser rejection |
| QWM-02 schema reuse | PROPOSED, not implemented/measured | Compile-cost baseline first |

The continuation wrapper exited 1 after producing all 20 results; Python exit was
not captured. Offline review checked the actual semantic artifacts and hashes.
Do not turn this into a clean exit0 claim. Available RAM declined to about 2.5 GiB
on that run; its cause is UNKNOWN, not an established OVMS memory leak.

## Recommended order

1. Establish repeatable execution and resource evidence. Correct the harness exit
   capture, run the missing positive-after-error control when resources permit,
   and record available RAM, OVMS private bytes/working set, request counts and
   latency at baseline, after each loop and after idle. Separate system pressure
   from retained per-request state before changing memory or concurrency settings.
2. Verify actual terminal reasons through the backend/streamer boundary. Prioritize
   LENGTH and cancellation because synthetic STOP can confuse completion handling.
   Retain fail-closed behavior for incomplete calls and verify the next request
   remains healthy after cancellation or disconnect.
3. Complete the prepared R1 native matrix in a separate CPU build slot. Preserve
   all four inherited defects as OPEN; compare the locked baseline and candidate
   with the same cases. Reproduce #650 independently. No parser workaround should
   stand in for a decoder-mask repair.
4. Build an isolated explicit GenAI/XGrammar candidate cohort with build/link/DLL
   receipts and canonical tokenizer masks. Keep the accepted install and published
   lock intact. Propose a new lock only after the measured candidate gates.
5. On each explicitly named runtime tuple, measure 100 required-city calls and
   zero-argument/none/auto/required/named cases, thinking OFF/ON, tool-result prompt
   histories, repeated functions and SSE reconstruction. Then exercise 1/2/4 client
   sessions. State queueing vs true concurrent execution under the chosen
   max_num_seqs; do not raise that setting just to label a test concurrent.
6. Profile schema compilation; implement QWM-02 only if measured cost warrants it.
   Keep correctness and performance changes in separate atomic commits.

Live acceptance on the existing runtime and on the new candidate runtime are
different result sets. Neither may inherit the other's tuple-specific PASS.
Qwen3.8 hydration and MoE/OTD remain deferred separate tracks.

## Concrete proposed refinements

### A. Preserve terminal-reason semantics

1. Cause: source inspection shows OVMSTextStreamer::end() flushes STOP. Existing
   direct parser LENGTH tests do not prove the actual backend terminal path.
   End-to-end impact is UNREPRODUCED, not an already measured product failure.
2. Files: src/llm/ovms_text_streamer.{hpp,cpp}, its actual owning executor and
   completion-response path after tracing, relevant streamer/parser/API tests.
3. Implementation: trace ownership first; preserve the real terminal outcome
   through final drain and API finish mapping using the existing supported
   GenAI interfaces. Avoid guessing a reason from partial text or publishing
   incomplete calls. Choose the smallest API change after a measured RED.
4. Expected effect: STOP, token-limit termination and cancellation keep their
   distinct completion/recovery behavior; no fabricated executable arguments.
5. Test: actual max_tokens truncation, client disconnect/cancel at call boundaries,
   normal completed tool calls, subsequent healthy request, Qwen/Gemma/generic
   controls. All new backend tests are NOT RUN.
6. Provenance: current end() source, ACCEPTANCE.md criterion 11 and the existing
   STREAMING-LIFECYCLE-DECISION.md contract; proposed design is independent.

### B. Request-scoped compiled-schema reuse (QWM-02)

1. Cause: verifyQwenXmlToolProfile() constructs a RapidJSON SchemaDocument for
   intake and each argument-validation invocation. Source-confirmed repetition;
   latency/CPU impact has not been measured.
2. Files: src/llm/io_processing/qwen3coder/tool_schema_profile.{hpp,cpp},
   qwen3coder_tool_parser.cpp and the owning request/context integration after
   tracing, focused schema/parser tests and a reproducible benchmark.
3. Implementation: profile first. If useful, own an immutable compiled schema
   per registered tool within the request/parser lifetime; use a fresh mutable
   validator for each call and preserve allocator/schema lifetime, reset and
   fail-closed profile checks. Start without a global cache or relaxed validation.
4. Expected effect: fewer repeated compilations without changing accepted schemas,
   argument semantics or cross-request isolation. No performance target is claimed.
5. Test: identical rejection/acceptance corpus, repeated calls, changed schemas
   across requests, reset, parallel request isolation, compile counts and CPU/
   latency measurements with identical source/runtime inputs. NOT RUN.
6. Provenance: current tool_schema_profile.cpp implementation and the explicitly
   deferred QWM-02 note in QWM01-IMPLEMENTATION-HANDOFF.md; independent design.

## Alternatives and decision

- Recommended: correctness/resource characterization, grammar/cohort evidence,
  full runtime matrix, then measured schema optimization. This keeps regressions
  attributable to one mechanism and avoids benchmarking an unidentified runtime.
- Acceptance-first: run the whole existing-runtime stress matrix immediately.
  This can expose product symptoms sooner but needs stable resource headroom and
  still cannot close the candidate-cohort grammar gates.
- Performance-first: implement caching now. It could reduce compile overhead,
  but that benefit is currently unmeasured and would expand lifetime/concurrency
  changes while terminal and grammar semantics are still open.

No dependency promotion or product feature is implemented by this document.
