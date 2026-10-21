Current follow-up: full ovms_test and QWM request unit gate are measured in OVMS-TEST-HTTP-RESULTS.md. The historical BoringSSL/HTTP-unit blocker below is superseded. Real HTTP400 transport and live acceptance remain NOT RUN.

# QWM-01 build report — 2026-10-21

**ACCEPTED: NO. RUNTIME UNVERIFIED.**

Tested OVMS code `7037ee528d62981dafc93c9d5507addceb8f3341` on local branch `qwm01-request-schema`;
publication branch `feature/qwenmonster-qwm01-request-schema-20261021`.
Separate XGrammar candidate `3303659ec09c62c1d024a7d4eed1b0bc18b30cc3`. Published source lock unchanged.
Machine paths and raw logs remain private in the local orchestration hub.

| Stage | Measured result |
|---|---|
| Locked source preflight | All six components SOURCE PASS |
| Four requested test binaries | All compiled; all four tests actually executed |
| Qwen parser | 69/69 PASS, zero disabled; 14 cases / 2340 partitions |
| Generation policy | 9/9 PASS |
| Generic parser | 29/29 PASS |
| Gemma parser | 67/70; exactly the same three initial baseline failures |
| Combined focused Bazel invocation | Exit 3: test failures, not compilation failure |
| ovms_test | BUILD FAILED in dependency analysis; configured boringssl directory absent |
| QWM HTTP intake / HTTP400 | NOT RUN; the handler's new API translation unit was not compiled |
| Candidate native XGrammar/GenAI validation binaries | Fresh Release build PASS |
| #802 native assertions | 29/29 PASS; same program on baseline has 14 failures |
| GenAI JSON/token-bridge/ExcludeToken controls with candidate | 31/31 PASS |
| Actual Qwen3-8B tokenizer masks, hard and lazy | 425 whitespace-only tokens: baseline permits 422; candidate permits 0; immediate close passes |
| Synthetic zero-argument whitespace path | Baseline accepts 1024 spaces; candidate accepts 0; both can close |
| Python #802 tests | NOT RUN: torch/TVM-FFI/XGrammar bindings unavailable; native equivalents executed |
| Full server / actual target model / live API / agentic | NOT RUN |

The existing staged GenAI DLL was not rebuilt with #802. Candidate XGrammar is
statically linked into isolated native validation executables only. This is a
validated candidate mechanism, not an accepted replacement runtime cohort.
Actual-vocabulary evidence uses the pinned Qwen3-8B unit tokenizer, not a loaded
Qwen3.6 inference model. DLL and tokenizer hashes are retained in RESULTS.json.
The inherited Minja fixture-only source drift in the staged runtime is unchanged;
production headers match the lock, but no fresh locked full dependency build ran.

No product source was modified. An initial local native harness build encountered
Windows min/max macro collisions; target-local NOMINMAX/WIN32_LEAN_AND_MEAN fixed
that harness compile. The first HTTP test command exposed legacy CMD argument
splitting; a separate ovms_test build then established the real dependency blocker.
Neither event is attributed to the QWM product patch. All attempts are retained.

## Remaining gates

1. Restore/identify exact Windows full-server dependencies, starting with BoringSSL;
   rerun ovms_test with the QwenXml HTTP filters and verify HTTP400 mapping.
2. XML #650 remains reproducible: malformed end-marker is allowed as an incomplete
   prefix. #802 does not fix it.
3. Both converter libraries accept empty XML for a required key not declared in
   properties. This inherited grammar/profile gap needs a separate bounded fix;
   parser executable-argument validation remains fail closed.
4. Propose a new cohort explicitly only after dependency/runtime integration and
   remaining matcher controls. Then build server, pin canonical target model and
   prompt, and run unary/SSE/tool replay/20 loops/concurrency acceptance.

Evidence: `evidence/qwm01-build-20261021/RESULTS.json`, compact native RED/GREEN
logs and `REVIEW.md`. Full logs, command lines, UTC run IDs, worker PIDs and
provider sessions are retained privately; no local path map is published.
