# Current implementation checkpoint: R1 runner hardening

- ACTIVE_STAGE: first implementation unit complete: versioned runner/gate and18 offline regressions.
- BASE_SHA / REVERT_POINT: 8ad9410de45a2f16e8fe7bc9e560f0c11387d7aa; CURRENT_HEAD: resolve after commit.
- WORK_BRANCH: qwm01-request-schema.
- DEPENDENCY_LOCK: unchanged; accepted C6 install and running OVMS unchanged.
- LAST_GREEN_TESTS:18/18 offline runner tests; sealed preparation preflight; exact28-row native-source contract checked statically.
- CURRENT_FAILURE: native build/matcher and actual backend cancellation/terminal RED NOT RUN; four inherited grammar defects remain OPEN.
- ROOT_CAUSE: count-only result selection, loose companion success matching, unbounded cleanup and incomplete execution identity checks in old runner.
- NEXT_ACTION: resource-separated R1 native execution; reproduce actual parser/CB terminal and cancellation behavior before product changes.
- EVIDENCE_PATH: R1-RUNNER-HARDENING.md; evidence/r1-runner-hardening-20261021/RESULTS.json; raw logs private.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current external-agent checkpoint

- ACTIVE_STAGE: existing runtime reuse verified; bounded negative/positive/continuation PASS; two external static reviews checked.
- BASE_SHA / CURRENT_DOCUMENTATION_SNAPSHOT / REVERT_POINT: 346b333ea8cd3c1ed8ca5f1ff4d802a473162327; CURRENT_HEAD: resolve after this evidence-only update.
- WORK_BRANCH: qwm01-request-schema.
- DEPENDENCY_LOCK: unchanged; running executable unchanged; #802 still not integrated.
- LAST_GREEN_TESTS: external shell exit0; HTTP400 then valid named Paris tool call then nonce-bearing continuation. Prior20/20 and17/17 scopes retained.
- CURRENT_FAILURE: no measured API gate failure; available RAM reached514MiB during probe; reason unknown. Native R1, Hermes, LENGTH/cancel,100-city,1/2/4 remain NOT RUN.
- ROOT_CAUSE: memory pressure not attributed. Streamer STOP is distinct from actual API finish reason in visible CB path.
- NEXT_ACTION: resource characterization; complete parser/legacy trace; harden R1 exact rows and bounded cleanup before resource-separated native build.
- EVIDENCE_PATH: EXTERNAL-GATES-20261021.md; evidence/external-gates-20261021/RESULTS.json; raw logs private.
- ACCEPTED: NO.

Historical checkpoints below keep their measured scopes.

# Current follow-up: tool continuations and HTTP400 measured

- ACTIVE_STAGE: 20 controlled tool-result continuations and 17 negative HTTP400 transport cases completed.
- BASE_SHA / TESTED_SOURCE / REVERT_POINT: `5c777c174a80f0d72175985d963c8831da522761`; CURRENT_HEAD: resolve git HEAD after this evidence-only change.
- WORK_BRANCH: `qwm01-request-schema`; remote feature/qwenmonster-qwm01-request-schema-20261021.
- DEPENDENCY_LOCK: unchanged; candidate #802 not in installed GenAI/runtime.
- LAST_GREEN_TESTS: 20/20 continuations (10 unary + 10 SSE); 17/17 real HTTP400 + diagnostic matches.
- CURRENT_FAILURE: #650/inherited required gap OPEN; positive-after-error, Hermes, 100-city, 1/2/4 workloads NOT RUN. Wrapper exit1/Python exit not captured; semantic artifacts independently verified.
- ROOT_CAUSE: runtime grammar/cohort work remains separate; low available RAM deferred extra generation/build.
- NEXT_ACTION: resource/run receipts and positive-after-errors; trace actual STOP/LENGTH/CANCEL; run R1 matrix and separate #650 controls, then isolated cohort and runtime acceptance. See NEXT-STEPS-20261021.md.
- EVIDENCE_PATH: FOLLOWUP-20261021.md; evidence/followup-20261021/RESULTS.json; raw logs private.
- ACCEPTED: NO.

Historical checkpoints below retain their original scope and are superseded only by the measured gates above.

# OVMS test current measured checkpoint

- ACTIVE_STAGE: end-of-day status published; Ornith live unary/SSE/tool smoke PASS; agent/HTTP400 still open.
- BASE_SHA: `e0772d161a81ed3420082af2bf68ab46d342e904`. CURRENT_HEAD / REVERT_POINT: resolve with `git rev-parse HEAD`.
- WORK_BRANCH: `qwm01-request-schema`; remote feature/qwenmonster-qwm01-request-schema-20261021.
- DEPENDENCY_LOCK: unchanged. XGrammar #802 candidate `b288dca18ee25d2f35197fb3971334ca049c8554` proposal-only.
- LAST_GREEN_TESTS: tip `//src:ovms`; LIVE-UNARY `OK.`; LIVE-SSE `Hi`; LIVE-TOOL-ZERO-ARG; LIVE-TOOL-REQUIRED-CITY; LIVE-TOOL-CHOICE-NONE.
- CURRENT_FAILURE: agent loops / HTTP400 transport NOT RUN; XML #650 OPEN; #802 not in staged GenAI DLL.
- ROOT_CAUSE: n/a for smoke; acceptance incomplete. Pin `C:/llm/models/ornith-35b-ov`. Qwen3.8 deferred.
- NEXT_ACTION: agent loops; HTTP400; optional Qwen3.8; explicit lock only after runtime cohort. Keep ACCEPTED NO.
- EVIDENCE_PATH: STATUS-20261021.md; private hub `C:/gm/qwenmonster/live-ornith-20261021`.
- ACCEPTED: NO.

Historical snapshots follow and are superseded by the measured checkpoint above.

# OVMS tip: Gemma bounded repairs merged, rebuild in progress

- ACTIVE_STAGE: repair/gemma4-bounded merged into qwm01 tip; focused units and ovms_test rebuild pending.
- BASE_SHA / REVERT_POINT: `e0772d161a81ed3420082af2bf68ab46d342e904`.
- WORK_BRANCH: `qwm01-request-schema` / remote `feature/qwenmonster-qwm01-request-schema-20261021`.
- CURRENT_HEAD: resolve with `git rev-parse HEAD` (merge `564d3e2a6`, docs checkpoint on tip).
- DEPENDENCY_LOCK: unchanged published core lock.
- LAST_GREEN_TESTS: prior HTTP request-unit on pre-merge tip; repair-branch units Gemma79/79, core29/29, Qwen69/69, policy9/9.
- CURRENT_FAILURE: unknown until post-merge rebuild; previous tip retained three Gemma baseline fails in full ovms_test.
- ROOT_CAUSE: n/a for merge; repairs address content visibility, bare preamble, native-string fixtures.
- NEXT_ACTION: rebuild focused parser units then full ovms_test; replay HTTP request-unit gates; update evidence.
- EVIDENCE_PATH: private hub C:/gm/qwenmonster/gemma4-bounded-20261021; docs/gemma4-repairs/BOUNDED-REPAIRS.md.
- ACCEPTED: NO.

Historical snapshots follow and are superseded by the measured checkpoint above.

# OVMS test current measured checkpoint

- ACTIVE_STAGE: full target and QWM request unit gate completed; transport/live gates remain open.
- BASE_SHA / CURRENT_HEAD / REVERT_POINT: `e0772d161a81ed3420082af2bf68ab46d342e904` (tested product code, later documentation-only tip resolved with git rev-parse HEAD).
- WORK_BRANCH: `qwm01-request-schema`; remote feature/qwenmonster-qwm01-request-schema-20261021.
- DEPENDENCY_LOCK: unchanged published core lock; auxiliary restoration identities recorded separately.
- LAST_GREEN_TESTS: full ovms_test build exit0, QWM2/2, related tool controls11/11, Qwen69/69; actual loaded core module hashes match staged inputs.
- CURRENT_FAILURE: Gemma67/70, same three failures; HTTP400 transport, LIVE, AGENTIC NOT RUN; XML #650 and remaining grammar/profile issues still open.
- ROOT_CAUSE: absent auxiliary inputs, Python dev/runtime mismatch, and generated-header file junction; repaired without product source changes.
- NEXT_ACTION: verify real HTTP400 transport separately; complete explicit cohort integration and canonical model/live gates.
- EVIDENCE_PATH: OVMS-TEST-HTTP-RESULTS.md and evidence/ovms-test-http-20261021/RESULTS.json; raw logs retained privately.
- ACCEPTED: NO.

Historical snapshots follow and are superseded by the measured checkpoint above.

# QWM-01 current measured checkpoint

- ACTIVE_STAGE: focused unit and native companion builds complete; HTTP build blocked in dependency analysis.
- BASE_SHA / CURRENT_HEAD / REVERT_POINT: `7037ee528d62981dafc93c9d5507addceb8f3341` (exact tested product code; later evidence-only tip is resolved with git rev-parse HEAD).
- WORK_BRANCH: `qwm01-request-schema`; remote `feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged public-source-lock.json. Candidate XGrammar `3303659ec09c62c1d024a7d4eed1b0bc18b30cc3` is separate, not deployed.
- LAST_GREEN_TESTS: source6/6; Qwen69/69, policy9/9, generic29/29; native #802 assertions29/29 and GenAI controls31/31. Unit tokenizer hard/lazy whitespace masks: 422 allowed before, 0 after.
- CURRENT_FAILURE: Gemma67/70 same baseline failures; ovms_test dependency analysis cannot find configured BoringSSL. HTTP intake and HTTP400 NOT RUN. XML #650 and inherited undeclared-required conversion gap remain open.
- ROOT_CAUSE: environment dependency absence blocks HTTP compile/link; native #802 epsilon change removes the zero-argument whitespace path. See QWM01-BUILD-REPORT.md.
- NEXT_ACTION: restore exact full-server Windows dependencies; build/run Qwen HTTP tests, then integrate proposed explicit cohort and complete target model/live gates.
- EVIDENCE_PATH: evidence/qwm01-build-20261021/RESULTS.json and QWM01-BUILD-REPORT.md; raw machine logs retained privately.
- ACCEPTED: NO; RUNTIME UNVERIFIED.

The sections below are historical checkpoints, superseded by this measured entry.

# QWENMONSTER local execution checkpoint

Date: 2026-10-21. ACCEPTED: **NO**.

- ACTIVE_STAGE: first source/build/unit iteration completed; native XML risks reproduced; live gates blocked.
- BASE_SHA: `ba6ec792c3121850fea167fa7d7e190b25fcdc76` (accepted C6 left untouched).
- WORK_BRANCH: `feature/qwenmonster-parser-invariants-20261021`.
- CURRENT_HEAD: `a299bb9f3612e8d7a98da60e2d5ef834ab526660` (implementation/probe checkpoint before this documentation-only commit; resolve final branch tip with `git rev-parse HEAD`).
- TESTED_PARSER_SHA: `f6f2a296d0574cf611cd2be6e31e3916c5858dbb`; final four-target run tested these exact code changes before their commit, plus evidence-only edits.
- DEPENDENCY_LOCK: `public-source-lock.json`, unchanged. GenAI `2decb9ec4bea827e01db47524352ad72d23b33ab`; XGrammar `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba`; OpenVINO `b5bfb14860320ae2a44d0fc55d78caa9a9d789b9`; Minja `83eb074e42140b0d1194d1dd61f29c31e4515ee9`; Tokenizers `d73028e255ddc279483fbc6e8ea90dc802e820f5`.
- LAST_GREEN_TESTS: six-component source preflight; Qwen69/69 (no disabled tests), policy9/9 (unchanged cached result in final run), generic29/29; 14 partition cases / 2340 runs; existing native JSON/ExcludeToken controls31/31.
- CURRENT_FAILURE: Gemma67/70, same three initial failures; XML matcher permits malformed close continuation and unbounded zero-argument whitespace path. Full server build, fresh locked dependency rebuild, canonical prompt and live/agent acceptance NOT RUN.
- ROOT_CAUSE: rejected speculative identity contaminated the next call; generic streamer held ready arguments until end; malformed envelopes crossed transport boundaries; shallow validation and RapidJSON edge cases allowed invalid arguments. Implemented fail-closed fixes and active regressions. Native matcher masks require a separate compatible dependency fix.
- NEXT_ACTION: investigate Gemma baseline separately; review/reproduce compatible XML matcher backports on dedicated dependency branches; propose explicit cohort revision if needed. Rebuild exact cohort and server, then pin actual model/tokenizer/template and run prompt/API/live/20-loop gates before promotion.
- REVERT_POINT: execution entry `8cd25d63085637d112f616d62913e345a93d2233`; original C6 above.
- EVIDENCE_PATH: `docs/qwenmonster/evidence/`; full local logs `C:/gm/qwenmonster/evidence/`.
- ACCEPTED: **NO**. RUNTIME UNVERIFIED.

## Measured scope and compatibility

All four requested test executables compiled. The combined final Bazel command
exited 1 because of the three unchanged Gemma failures; this is not a green full
build. No candidate OVMS server executable was built or launched.

Tool ID/name/index publication now waits for completed-call validation. The
generic streamer drains ready output each flush with its existing final-delta
lookahead. Outer tool transport markers are reserved in every XML parser state;
they cannot be literal parameter data. See STREAMING-LIFECYCLE-DECISION.md and
SCHEMA-VALIDATION-PROFILE.md for the supported restricted Draft 4 profile and
compatibility limits. Guided auto default remains OFF.

The exact source lock passes. Unit binaries reused the existing staged runtime;
its Minja checkout differs only by one test fixture and its production headers
match the lock. This is not a fresh locked-cohort binary rebuild. The synthetic
native probe records loaded GenAI/OpenVINO module paths; no inference model or
tokenizer was loaded. Do not transfer this result to actual model token masks.

Independent read-only review found no remaining actionable important issue in
the scoped parser/schema/drain changes after RED/GREEN corrections. This review
does not establish live, model, dependency or release acceptance.

## Evidence index

- `evidence/BUILD-FINAL.txt`, `UNIT-RESULTS.json`, `UNIT-*.txt`: real compiler/test outcomes.
- `evidence/PUBLIC-COHORT-SOURCE-FINAL.json`, `PUBLIC-COHORT-BUILD-IDENTITY.md`: source and binary provenance boundaries.
- `evidence/GRAMMAR-COMPILE.json`: synthetic hard/lazy XML compile, masks and whitespace traces.
- `evidence/FAILURE-TRIAGE.md`: observed failures, smallest fixes and controls.
- `evidence/NOT-RUN.json`: all unexecuted acceptance gates.
- `evidence/*RED*.txt`: retained actual failing regressions, not inferred failures.
- `evidence/EXECUTION-CHECKPOINT.md`: historical entry checkpoint; superseded by this file.

## QWM-01 HTTP-intake follow-on (2026-10-21)

- WORK_BRANCH: `feature/qwenmonster-qwm01-request-schema-20261021` (isolated follow-on, original Qwenmonster branch unchanged).
- BASE_SHA / REVERT_POINT: `8aba34ad4e422d470d91afdf88aa3dd9696cb143`.
- QWM01_PATCH_SHA: `e0c6966c9f03eec8236548e8bcf5fd164141395b`;
  tests `f6489410...`, code `df01cfec...`, RapidJSON include `e0c6966c...`.
- ACTIVE_STAGE: SOURCE PATCHED, BUILD/UNIT/HTTP/LIVE NOT RUN for follow-on.
- LAST_GREEN_TESTS: prior branch Qwen69/69, policy9/9, generic29/29;
  *none have been rerun against this change*. Gemma historical 67/70.
- CURRENT_FAILURE: unknown until real compiler/HTTP unit execution;
  XGrammar #650 and #802 masks still fail on published lock.
- ROOT_CAUSE: request intake had Gemma-only strict checks, while Qwen
  runtime used a separate restricted Draft4 schema compiler. The code now
  shares that parser profile with the HTTP layer.
- DEPENDENCY_LOCK: unchanged `docs/qwenmonster/public-source-lock.json`.
- COMPANION_XGRAMMAR_CANDIDATE: isolated branch
  `DassaultFalconKing/xgrammar:fix/qwenmonster-xml-empty-object-20261021`
  at `3303659ec09c62c1d024a7d4eed1b0bc18b30cc3`. NOT LOCKED OR BUILT.
- NEXT_ACTION: compile new Bazel schema-profile library and execute Qwen
  HTTP RED/GREEN, parser/generic/Gemma negative controls; separately compile
  #802 candidate and run real matcher masks. See
  `docs/qwenmonster/QWM01-IMPLEMENTATION-HANDOFF.md`.
- EVIDENCE_PATH: current source commits; no new runtime logs.
- ACCEPTED: NO.
