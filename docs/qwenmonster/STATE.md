# Current checkpoint: packed MoE OTD bench recorded, then stop

- ACTIVE_STAGE: one packed serve at OFFLOAD_RATIO=75 measured with packs built at OFFLOAD_RATIO=40. Unpacked comparison, OFFLOAD_RATIO=40 serving and MTP K3 NOT RUN. ACCEPTED: NO.
- BASE_SHA / REVERT_POINT: `145f1531c` before this stop note. WORK_BRANCH: `integration/qwm01-otd-pack-20261022`.
- DEPENDENCY_LOCK: unchanged. Measured OVMS SHA-256 `1175bd25d6faf90e41c6591e23507cf6117895351462ff3b5648c8a6df08a760`. Measured GPU plugin SHA-256 `1093b69f6314898238ffec06fb46631759526e89c90e3e3fd2fd29c122e8058e`, cohort branch `47921924`. GenAI DLL unchanged `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`.
- LAST_GREEN_TESTS: pack build wrote 40 packs; reuse run reported 40 pack files. Packed graph reached AVAILABLE in require mode. Warmup plus 3 repeats, 384 completion tokens, finish_reason=length. Repeat TTFT 4.43 / 4.18 / 4.20 s; decode 5.75 / 5.94 / 5.97 tok/s. Warmup TTFT 13.85 s, decode 5.68 tok/s.
- CURRENT_FAILURE: unpacked ratio-75, both ratio-40 rows, MTP K3, `ovms_test` filter `*oeExpertsPack*`, and the process-exit OTD counters are NOT RUN. Available RAM at the packed start was 9824 MiB, below the 15463 MiB floor.
- ROOT_CAUSE: n/a. The exit summary was not captured; the trace ended mid-record.
- NEXT_ACTION: stop. Do not start another model until the operator asks. Next pack row is unpacked at OFFLOAD_RATIO=75 with the same token budget.
- EVIDENCE_PATH: [HANDOFF-MOE-OTD-PACK-20261022.md](HANDOFF-MOE-OTD-PACK-20261022.md). Raw logs stay private.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current checkpoint: operator compute pause and drafter handoff

- ACTIVE_STAGE: PAUSED BY OPERATOR, 2026-10-22. Status publication only; no new builds or inference. Operator compilations are active and untouched.
- BASE_SHA / REVERT_POINT: `8f88ca704`; WORK_BRANCH: `qwm01-request-schema`. CURRENT_HEAD: resolve after this documentation commit.
- DEPENDENCY_LOCK: unchanged. Drafter measurements used executable SHA-256 `3f4316ebc3c843c75215d120a2a542c5df685c1f2d4c3b12d9d1ccca67a3f527` and GenAI DLL `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`. This executable predates source fixes `3e3d38a8e` and `8f88ca704`.
- LAST_GREEN_TESTS: isolated MTP export/transform; short baseline/K1/K2/K3 HTTP/SSE and native smoke. Smoke is 27 input / 64 output tokens, not long-context acceptance. Exact 2048-token templated workload and private diagnostic prepared; final diagnostic validation NOT RUN.
- CURRENT_FAILURE: AEON startup lacks target hidden-state metadata (1/5 fallback outputs). Candidate metadata overlay exists but has not been runtime-tested. Ordinary EAGLE3 IR paged-attention transform fails. Full long-context matrix and drafter agentic gates NOT RUN. External worker reached its step limit and exited; no benchmark runner was launched.
- ROOT_CAUSE: see handoff for separate export, target metadata, transform and diagnostic API boundaries. Neither short token-rate measurements nor process exit prove operational acceptance.
- NEXT_ACTION: wait for operator release of compute. Then validate existing diagnostic, run baseline and MTP K3 with honest separate prefill/TTFT/decode metrics, review results, extend candidate matrix and useful tool-result loops. Do not restart repetitive 100/100 loops by default.
- EVIDENCE_PATH: [HANDOFF-DRAFTERS-20261022.md](HANDOFF-DRAFTERS-20261022.md); exact machine paths/raw evidence remain private. MASTER-PLAN.md has synchronized statuses.
- ACCEPTED: NO. No persistent OVMS or diagnostic process active at the pause snapshot; operator compiler left running.
- LINKED_TRACK: integration branch `integration/qwm01-otd-pack-20261022` = this checkpoint plus the MoE experts pack mode. The drafter executable above does not contain it. See [HANDOFF-MOE-OTD-PACK-20261022.md](HANDOFF-MOE-OTD-PACK-20261022.md).

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: mid-generation disconnect measured

- ACTIVE_STAGE: a streaming request on the installed candidate DLL was closed after content tokens had started. Memory did not return while that process stayed alive. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `af3b0099dc7e140a9805ae31e7a1faf204abba04`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. Loaded module SHA-256 `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`.
- LAST_GREEN_TESTS: three content SSE events arrived (`NUMBER 1`), then the socket was closed. The executor log reached `All requests: 0` 0.27 s after the disconnect error. The follow-up returned `finish_reason=stop` and content `OK`. The server was then stopped, and the listening port was closed.
- CURRENT_FAILURE: cancel is NOT_PROVEN. Private bytes were 15965.5 MiB before the request and 16121.3 MiB at both 5 s and 15 s after the close (+155.8 MiB). Working set rose from 2764.0 MiB to 16113.2 MiB and stayed there; that is residency of memory already committed, not a release. No generation-handle stop line. The disconnect also failed the executor with `generation_stream.hpp:136`: perf metrics are not available until generation has completed. The process survived that error. Undeclared-required empty XML remains.
- ROOT_CAUSE: n/a for the memory samples. The perf-metrics assertion fires because stop/disconnect reads metrics before generation has completed.
- NEXT_ACTION: the perf-metrics assertion is the concrete disconnect RED. Do not treat process exit as resource reclamation. Do not edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: W3-LENGTH-CANCEL.md. Raw JSON stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: installed candidate DLL live-reviewed

- ACTIVE_STAGE: the installed candidate GenAI DLL was loaded by the server and reviewed on unary, SSE, disconnect-follow-up, and one required city tool call. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `cb17e2867646d233d0317523f2d576d957148670`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. Loaded module SHA-256 `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d`.
- LAST_GREEN_TESTS: the listening process loaded that hash. Unary `max_tokens=16` returned `finish_reason=length`, 16 completion tokens, content `NUMBER 1 2 3 4 5 6 7 `. SSE ended with `length` and `[DONE]`. After a client socket close, the follow-up returned `finish_reason=stop` and content `OK`. One non-streaming tool call returned `finish_reason=tool_calls` and `get_weather` with `city` `Paris`. The executor log returned to 0 requests. The server was stopped.
- CURRENT_FAILURE: cancel is NOT_PROVEN. Working set stayed about 1.5 MiB above the pre-request sample, and the log has no generation-handle stop line. Executor drain to 0 also happens on normal completion. Undeclared-required empty XML remains. 100/100 required, named, and autonomous loops are not this run.
- ROOT_CAUSE: n/a. The loaded module is the installed candidate, so this run is not the earlier side-by-side process.
- NEXT_ACTION: cancel/resource measurement remains open. Do not edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: XGRAMMAR-650-NOTE.md. Raw JSON stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: candidate GenAI DLL installed

- ACTIVE_STAGE: the isolated candidate replaced both the staged runtime GenAI DLL and the copy beside the server executable. Originals were kept privately. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `7858ea024ce75d96142d7dbee71ae1103f695902`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. Installed DLL SHA-256 `442452056e06c3a7e05d71ca082e9f30fd0034c8f6dcf5b2e56f04f140599e4d` (9031680 bytes), built from XGrammar `5b0b7084a65a2059b44c03fbc6320ad7fcc41f33` and GenAI `8f305a1c1bc11e348c8ad0cc37269a91ba21cc74`. Previous DLL SHA-256 `7892465a3bca67e103e26b198f47fb1d5c0a98fc2cc7cb4616ba0e8d5ad054da` (8745472 bytes).
- LAST_GREEN_TESTS: the earlier side-by-side live unary/SSE still stands for that process. These installed files have not been retested yet.
- CURRENT_FAILURE: cancel is unproven. Undeclared-required empty XML remains. The installed copy's own live runs are delegated and not reviewed.
- ROOT_CAUSE: n/a. Windows loads `openvino_genai.dll` from the executable directory before PATH, so both that copy and the staged runtime copy were replaced.
- NEXT_ACTION: review the delegated load, length, disconnect, and one required-city runs. Do not edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: XGRAMMAR-650-NOTE.md. Paths of the backups stay in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: candidate DLL live unary and SSE

- ACTIVE_STAGE: Ornith answered unary and SSE through the isolated candidate GenAI DLL. The staged runtime file was not replaced. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `e5491389d8f95f921991d4c8c5970ace326b9437`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged.
- LAST_GREEN_TESTS: process module list showed the candidate `openvino_genai.dll`, not the staged copy. Unary `max_tokens=16` returned `finish_reason=length` and 16 completion tokens. SSE ended with `length` and `[DONE]`. After a client socket close, a follow-up unary returned `finish_reason=stop` and content `OK`. The executor log returned to 0 requests. Server stopped afterwards.
- CURRENT_FAILURE: client close still does not prove generation-handle cancel or resource reclamation. Undeclared-required empty XML remains. 100/100 required, named, and autonomous loops are not this run.
- ROOT_CAUSE: n/a for the live slice. Windows loads a DLL beside `ovms.exe` before `PATH`, so the first start loaded the copy next to the Bazel output. The measured process was started from a copy of the executable placed beside the candidate DLL.
- NEXT_ACTION: cancel/resource measurement, then the acceptance workloads that are still open. Do not edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: XGRAMMAR-650-NOTE.md. Raw JSON stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: Qwen tokenizer end-marker mask

- ACTIVE_STAGE: the #650 divergence mask is measured on the Qwen3-8B unit tokenizer against the candidate XGrammar library. The staged runtime was not replaced. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `7e462812d8eaab195140575d982b802b9c24ceed`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. Candidate sources remain XGrammar `5b0b7084a65a2059b44c03fbc6320ad7fcc41f33` and GenAI `8f305a1c1bc11e348c8ad0cc37269a91ba21cc74`.
- LAST_GREEN_TESTS: native matcher 71/71 PASS, `SUMMARY failures=0`. On vocab 151669 / eos 151645, the good and bad strings diverge at token 9. The bad next tokens are rejected and the good next token is allowed: id 16 byte `31` (`1`), id 55 byte `58` (`X`), id 9174 bytes `5f 66 75 6e 63 74 69 6f 6e` (`_function`), id 9685 bytes `2f 3e` (`/>`), good id 29 byte `3e` (`>`). The good token sequence completes. The bad sequences are rejected. Hard/lazy whitespace remains 425 tokens, 0 allowed.
- CURRENT_FAILURE: the candidate DLL has not been loaded by a live server. Cancel and resource reclamation remain NOT_RUN. Undeclared-required empty XML still accepts empty.
- ROOT_CAUSE: n/a. The rejected ids are the tokenizer pieces that continue a started `</parameter`.
- NEXT_ACTION: one live unary/SSE on the candidate DLL only, then the cancel measurement. Do not swap the staged runtime or edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: XGRAMMAR-650-NOTE.md. The raw checker log stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: isolated #650 candidate matcher

- ACTIVE_STAGE: the XML end-marker lock is compiled into an isolated GenAI candidate. The staged runtime was not replaced. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `c4ae73f9254eca81a44f22fe8435b940dee87dbc`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. Candidate sources, not the public lock: XGrammar `5b0b7084a65a2059b44c03fbc6320ad7fcc41f33` (`fix/qwenmonster-xml-end-marker-lock-20261022`), GenAI `8f305a1c1bc11e348c8ad0cc37269a91ba21cc74` (`codex/qwenmonster-xgrammar-802-20261022`).
- LAST_GREEN_TESTS: native matcher linked to the candidate XGrammar static library, 43/43 PASS, `SUMMARY failures=0`. #802 empty-object epsilon, declared-required rejection of empty, and the Qwen3-8B unit-tokenizer hard/lazy whitespace mask (425 tokens, 0 allowed) still pass. #650 accepts a real `</parameter>`, `<div>`, `</p>`, and a comparison expression, and rejects `</parameter1>`, `</parameter_function>`, `</parameterX>`, and `</parameter/>`. On the synthetic byte vocabulary, after the prefix `</parameter`, bytes `1`, `X`, and `_` are masked off. The candidate DLL contains `lock_excluded_prefixes`; the staged DLL does not.
- CURRENT_FAILURE: the #650 mask was not measured on the Qwen3-8B tokenizer. Undeclared-required `{type:object, required:[a]}` still accepts empty XML. Cancel and resource reclamation remain NOT_RUN. The candidate DLL was not loaded for inference.
- ROOT_CAUSE: n/a for this matcher slice. The string result is the locked TagDispatch prefix, not a parser rejection.
- NEXT_ACTION: measure the end-marker mask on the unit tokenizer, then a live probe that loads only the candidate DLL. Do not swap the staged runtime or edit the public lock. Keep ACCEPTED NO.
- EVIDENCE_PATH: XGRAMMAR-650-NOTE.md. The raw checker log stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: W3 live max_tokens

- ACTIVE_STAGE: Ornith live max_tokens measured on the existing tip binary. ACCEPTED stays NO.
- BASE_SHA / REVERT_POINT: `5f4453a41b598b3cd2143a9c07177e0ccfe9bb81`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. C6 and staged GenAI DLL untouched.
- LAST_GREEN_TESTS: live unary and SSE `max_tokens=16` both returned `finish_reason=length` (completion_tokens 16 on unary). A following unary after client socket close returned `finish_reason=stop` and content `OK`.
- CURRENT_FAILURE: client disconnect did not prove generation-handle cancel or resource reclamation. W4 #650 still OPEN; no local XGrammar checkout.
- ROOT_CAUSE: n/a for the length slice. Backend finish reason reached the HTTP chunk on a real model, matching the unit.
- NEXT_ACTION: separate XGrammar fork for #650. Do not treat this live slice as cancel proof. Keep ACCEPTED NO.
- EVIDENCE_PATH: W3-LENGTH-CANCEL.md. Raw JSON stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: W3 chat LENGTH unit measured

- ACTIVE_STAGE: focused chat-stream LENGTH unit PASS on the existing GenAI response path. No product C++ change.
- BASE_SHA / REVERT_POINT: `3c5c84a241b1dd11dfc4618c7a7ffa9f27fa6f30`. CURRENT_HEAD: resolve with `git rev-parse HEAD` after this commit.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. #802 candidate still proposal-only. C6 and staged GenAI DLL untouched.
- LAST_GREEN_TESTS: `HttpOpenAIHandlerParsingTest.CbChatStreamingPreservesBackendLengthFinishReason` 1/1 PASS in 74 ms via direct `ovms_test.exe` with the active runtime on PATH. Final SSE chunk carried `"finish_reason":"length"` and `[DONE]`.
- CURRENT_FAILURE: `bazel test` under `test:windows` PATH `C:/opt/openvino/runtime/...` exited `-1073741515` (DLL not found) before gtest. Live Ornith max_tokens, disconnect, and after-cancel healthy request still NOT RUN.
- ROOT_CAUSE: streamer `end()` still feeds STOP into the parser; HTTP serialization kept the backend LENGTH. The bazel miss is the checked-in Windows test PATH, not a finish-reason regression.
- NEXT_ACTION: live max_tokens / client disconnect / healthy follow-up on the existing Ornith profile. Then W4 #650 on a separate XGrammar fork. Keep ACCEPTED NO.
- EVIDENCE_PATH: W3-LENGTH-CANCEL.md. Raw gtest log stays in the private hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: Cursor takeover after Codex handoff

- ACTIVE_STAGE: fetched origin; merged canonical MASTER-PLAN/PLAN-MAP onto tip with local R1 native + CB parser-failure commits; pushed `b2e2daae3`.
- BASE_SHA / REVERT_POINT: `d7e793ed3` (R1 native) / CB fix `15076a147`; CURRENT_HEAD: resolve with `git rev-parse HEAD`.
- WORK_BRANCH: `qwm01-request-schema` → `origin/feature/qwenmonster-qwm01-request-schema-20261021`.
- DEPENDENCY_LOCK: unchanged. #802 candidate still proposal-only.
- LAST_GREEN_TESTS: as prior tip — R1 native 24 PASS + 4 OPEN; CB parser-failure 6/6 + 171 controls; Ornith live smoke historically PASS (server now down).
- CURRENT_FAILURE: W3 LENGTH/CANCEL/disconnect backend lifecycle still NOT measured as a dedicated gate; Ornith process gone; OpenCode idle (last `cb-parser-red`).
- ROOT_CAUSE: n/a for takeover. Codex left tip ahead of origin with R1/CB; origin had master-plan only — now merged.
- NEXT_ACTION: MASTER W3 — actual LENGTH/CANCEL/disconnect through streamer/API (proposal A in NEXT-STEPS); then W4 #650 / W5 candidate cohort. Keep ACCEPTED NO.
- EVIDENCE_PATH: MASTER-PLAN.md, PLAN-MAP.md, CB-PARSER-FAILURE.md, R1-NATIVE-20261021.md; private followup hub.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: CB parser failure containment

- ACTIVE_STAGE: implemented and reviewed; product/full diagnostic builds and 177 selected native tests PASS.
- BASE_SHA / REVERT_POINT: d7e793e; CURRENT_HEAD: resolve after commit.
- WORK_BRANCH: qwm01-request-schema.
- DEPENDENCY_LOCK: unchanged; accepted C6 untouched; owned idle server stopped with verified identity and remains stopped.
- LAST_GREEN_TESTS: 6 new native tests, 10 common/legacy, 2 QWM, 11 tool controls, 148 Qwen/Gemma; 28 offline Python tests. R1 native matrix: 24 PASS, 4 known OPEN, 0 unexpected; companion checks PASS.
- CURRENT_FAILURE: original CB failure reproduced by 2/2 RED tests, now GREEN. Four inherited grammar defects remain OPEN; patched live runtime NOT RUN.
- ROOT_CAUSE: shared response path ignored streamer CANCEL/parser error and serialized successful completion; LM/VLM owners now stop failed handles.
- NEXT_ACTION: measure actual handle cancellation/resource reclamation and STOP/LENGTH lifecycle; isolate candidate GenAI/XGrammar cohort rebuild.
- EVIDENCE_PATH: CB-PARSER-FAILURE.md; evidence/cb-parser-failure-20261021/RESULTS.json; R1-NATIVE-20261021.md.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

# Current implementation checkpoint: passive resource observer

- ACTIVE_STAGE: resource collector implemented; 10 focused tests, 28 combined regressions and 3 passive idle samples completed.
- BASE_SHA / REVERT_POINT: 86d1f26078466c18b517ca53833acbb28fc648f7; CURRENT_HEAD: resolve after commit.
- WORK_BRANCH: qwm01-request-schema.
- DEPENDENCY_LOCK: unchanged; running OVMS not restarted or reconfigured.
- LAST_GREEN_TESTS: 10/10 resource tests; 28/28 combined runner/resource tests; 3/3 passive samples with exact PID/creation identity.
- CURRENT_FAILURE: no failing current offline test. Load characterization, actual backend RED and native R1 still NOT RUN.
- ROOT_CAUSE: past memory pressure not attributed; idle counters alone do not establish a leak.
- NEXT_ACTION: correlate before/during/after resource observations with a bounded controlled run when resources permit; reproduce parser/CB cancellation behavior before product changes.
- EVIDENCE_PATH: RESOURCE-PROBE.md; evidence/resource-probe-20261021/RESULTS.json; raw JSONL private.
- ACCEPTED: NO.

Historical checkpoints below retain their measured scopes.

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

