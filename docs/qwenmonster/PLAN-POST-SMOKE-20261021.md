# Qwenmonster — revised plan after Ornith live smoke (2026-10-21)

Planning base: `feature/qwenmonster-qwm01-request-schema-20261021@5c777c174a80f0d72175985d963c8831da522761`.
XGrammar #802 candidate: `b288dca18ee25d2f35197fb3971334ca049c8554`.
**ACCEPTED: NO.** Original accepted C6 and staged runtime are read-only; public dependency lock is unchanged. Publish only placeholders, never private absolute paths or raw machine logs.

## Verified status and boundaries

- Post-merge OVMS full unit target build exit 0. Request QWM-01 2/2 (12 internal table cases), related tool controls 11/11, Qwen + Gemma parsers 148/148 (69 Qwen + 79 Gemma). The old three Gemma failure names are green. This includes two bounded production-routing/visibility repairs and **one corrected contradictory escaped-quote fixture**, not three production parser fixes. Full `//src:ovms` was also built.
- Ornith Qwen3.6-35B-A3B INT4 live smoke is **reported** successful for unary, SSE, zero-argument ping, required city argument and `tool_choice=none`. Raw traces are retained privately; this source review cannot independently replay them.
- Native XGrammar #802 candidate: 29/29 matcher checks; 31/31 GenAI controls. With pinned Qwen3-8B unit tokenizer, 422/425 whitespace tokens allowed on old grammar versus 0/425 on candidate; no equivalent Ornith tokenizer validation yet. R1 guard restricts root epsilon to `required.empty()` and `min_properties <= 0`.
- Live smoke uses a staged GenAI DLL **without** XGrammar #802. Thus zero-arg smoke is **not** runtime evidence that #802 is fixed. #650 malformed closing-tag mask remains open, as does the inherited undeclared-required property grammar mismatch.
- HTTP 400 transport, multi-round tool-result replay, 20 loops, 1/2/4 concurrency, isolated rebuilt dependency cohort and lock promotion are **NOT DONE**.
- Evidence sources: `docs/qwenmonster/STATUS-20261021.md`, `OVMS-TEST-HTTP-RESULTS.md`, `XGRAMMAR-802-COHORT-PROPOSAL.md`, `XGRAMMAR-650-NOTE.md`, `docs/gemma4-repairs/BOUNDED-REPAIRS.md`, `evidence/ovms-test-http-20261021/RESULTS.json`.

Each proposed change below follows six fields mandated by `AGENTS.md`. Test names are proposed gates, **not** test-pass claims.

## A. Real HTTP 400 contract (P0, immediate)

1. **Cause:** QWM-01 unit `InvalidArgument` is green, but status/error serialization over actual `/v3/chat/completions` was not exercised.
2. **Files:** New `scripts/qwenmonster/acceptance/http_contract.py`; `docs/qwenmonster/ACCEPTANCE.md`; sanitized JSON summary. Edit `src/llm/apis/openai_api_handler.cpp` or HTTP serializer only on a captured RED.
3. **Design:** Loopback request table: unsupported Draft4, invalid object root, duplicate schema/name, unavailable named tool, missing parameters, required with no tools; control valid none/auto/required/named. Verify response HTTP status, OpenAI error shape, inference-not-started and no unexpected downgrade to `none`. Redact tokens/path/user-agent/headers before public reporting.
4. **Expected:** Fail-fast invalid requests as actual HTTP400, without generation; valid requests preserve behavior.
5. **Test:** `HTTP-QWM01-INVALID-MATRIX`; positive Hermes/Gemma controls; actual request/response captures privately, public aggregate only.
6. **Provenance:** `OVMS-TEST-HTTP-RESULTS.md` request-unit green plus missing transport gate; independent HTTP harness design.

## B. Ornith tool-result loops and parallel slots (P0, immediate)

1. **Cause:** Unary/SSE one-shot tool delivery does not establish agent continuation or auto-delegation.
2. **Files:** New `scripts/qwenmonster/acceptance/run_agent_loop_matrix.py`, versioned sanitized fixtures and aggregate reports; production files only after exact failure ownership established.
3. **Design:** Pin model/tokenizer/Jinja/backend/DLL hashes. Execute deterministic non-destructive tools with `tool_call_id` result replay. Matrix: unary/SSE; none/auto/required/named; thinking ON/OFF; 1/2/N tools; typed/zero-argument; 20 complete tool-result → next-assistant cycles; concurrency 1/2/4 when hardware permits. For each turn log separately model *chooses* call → parser/API *delivers* → harness *executes* → model *continues*. Validate SSE IDs, indices, JSON reconstruction and server health.
4. **Expected:** Complete agentic loops with no orphaned calls; distinguish model decision, grammar, parser, API, harness and GPU failures.
5. **Test:** `ORNITH-AGENT-20-LOOPS`, `ORNITH-SSE-ID-INVARIANTS`, `ORNITH-CONCURRENT-1-2-4`; negative harness fixtures for dropped/reordered deltas; actual 20 completed loops required to close this gate.
6. **Provenance:** Ornith smoke status, Gemma/Qwen streaming contracts and local acceptance protocol; independent harness design.

## C. XGrammar #650 closing-marker mask (P0, separate dependency branch)

1. **Cause:** Both accepted and #802 candidate native matchers allow invalid continuation after `</parameter`; parser rejection cannot prevent decoder emission.
2. **Files:** Dedicated XGrammar branch; pinned TagDispatch FSM/structural-tag converter; matcher tests; `scripts/qwenmonster/native_matcher/probe.cpp`; no changes to accepted checkout or dependency lock.
3. **Design:** Semantically port opt-in longest-excluded-prefix restriction from [upstream PR #651](https://github.com/mlc-ai/xgrammar/pull/651); isolate behavior to XML parameter-string grammar and preserve normal text/HTML. Keep #650 independent of #802 for RED/GREEN and bisect.
4. **Expected:** Token mask disallows malformed close suffixes, including `</parameter1>`, before decoding them.
5. **Test:** `XGRAMMAR-Q-END-PREFIX-MASK` at every byte boundary and with actual target Qwen tokenizer, hard/lazy modes, nested/Unicode text; negative controls #802 and Gemma bounded JSON/ExcludeToken.
6. **Provenance:** [XGrammar #650](https://github.com/mlc-ai/xgrammar/issues/650) and PR #651; application to fork is a new backport, not inherited upstream proof.

## D. #802 integrated runtime candidate and proposed new lock (P0)

1. **Cause:** Static native candidate is green, installed GenAI DLL still links old grammar; live `ping` cannot verify installed #802.
2. **Files:** Isolated GenAI/XGrammar build configuration (explicit `FETCHCONTENT_SOURCE_DIR_XGRAMMAR`), distinct candidate runtime packaging, new candidate hash manifest; public lock **not** edited during validation.
3. **Design:** First build #802-only GenAI candidate, verify DLL SHA and loaded module; run actual loaded-native masks. Then compile combined #802 + independently proven #650 branch, compare both against original stage. Keep existing runtime read-only; publish sanitized hashes, not paths. Lock revision requires separate reviewed proposal.
4. **Expected:** Runtime decoder truly uses corrected Q-ZERO and, when ready, Q-END grammar without disturbing accepted C6.
5. **Test:** `COHORT-LOADED-DLL-SHA`, Q-ZERO/Q-END masks using candidate modules, Gemma JSON controls, Ornith live unary/SSE/zero-arg/20 loops and original-vs-candidate A/B.
6. **Provenance:** XGrammar #802 R1 `b288dca18`, 29 native tests/31 GenAI controls, and `XGRAMMAR-802-COHORT-PROPOSAL.md`.

## E. Undeclared required-property schema (P1, bounded compatibility)

1. **Cause:** Both XGrammar versions may generate empty XML for object with `required:["a"]` and no `properties.a` declaration; runtime rejects missing values. This is inherited. JSON Schema can allow such a key via `additionalProperties`, so blanket rejection is wrong.
2. **Files:** Qwen shared schema profile and HTTP tests, potentially a separate XGrammar converter patch, `docs/qwenmonster/SCHEMA-VALIDATION-PROFILE.md`.
3. **Design:** Compare `additionalProperties` true/false/typed, `required` absent from `properties`, `minProperties` and nested schemas. Explicitly 400 for unsatisfiable or unsupported guided forms; otherwise generate the required key faithfully. Never silently weaken `required`.
4. **Expected:** HTTP-accepted schemas are representable by the constrained XML grammar and executable validator.
5. **Test:** `QWM-UNDECLARED-REQUIRED` HTTP-unit + real HTTP400 + native grammar masks, Q-ZERO R1, positive open-schema and Gemma/Hermes controls.
6. **Provenance:** XGrammar R1 review finding and source profile; semantic policy is independent design.

## F. Gemma repair regression control (P1, do not modify accepted C6)

1. **Cause:** Gemma improved from 67/70 to 79/79 in candidate, but original C6 executable comparison and live Gemma compatibility are not yet evidenced.
2. **Files:** Existing Gemma/generic parser tests and `docs/gemma4-repairs/BOUNDED-REPAIRS.md`; no accepted C6 changes.
3. **Design:** Run original C6 in **separate diagnostic worktree/output** and candidate with fixed tokenizer/core DLL identity. Compare special-token visibility, duplicated-end channel routing, native string **decoded** semantics, resets, SSE and cancellation. Keep updated legacy fixture expectation explicit.
4. **Expected:** Confirm bounded fixes preserve Gemma tool execution and do not hide newly broken behavior.
5. **Test:** Candidate Gemma79/79, Qwen69/69, generic29/29; original-C6 three-failure classification plus actual live Gemma smoke where possible.
6. **Provenance:** `docs/gemma4-repairs/BOUNDED-REPAIRS.md` and post-merge measured results.

## G. Reasoning, MTP, schema cache and XML buffer performance (P2 after evidence)

1. **Cause:** Current smoke lacks measurements for thinking→tool transitions, agent auto-delegation, repeated schema compilation, long XML buffer retention, MTP/draft and MoE expert-cache behavior. No demonstrated blocker yet.
2. **Files:** Qwen generation-policy builder, reasoning parser and focused tests only if required; schema-profile and XML FSM perf benchmarks; isolated MTP/model runtime track.
3. **Design:** Pin canonical Qwen3.6/Ornith prompt bytes and tool-call phases, measure real delegation rates and concurrency. On a significant RED, reuse immutable compiled `SchemaDocument` per request or compact completed XML envelopes preserving unary offsets. MTP/cache A/B only with matched conditions.
4. **Expected:** Measured performance/autonomy improvement without lost call IDs, parser state or Gemma regressions.
5. **Test:** `QWM-REASONING-TOOL`, `QWM-AUTO-DELEGATION`, `QWM-SCHEMA-1000`, `QWM-BUFFER-10000`, MTP A/B with 2340 partition controls.
6. **Provenance:** Existing project Qwenmonster refit + local Ornith/MTP direction; specific optimization mechanisms are independent hypotheses.

## H. Public artifact privacy gate (immediate)

1. **Cause:** Certain earlier published project Markdown files contain machine-absolute filesystem locations. A new commit that removes text will not erase it from repository history or historical GitHub diffs.
2. **Files:** Future status/evidence publishers and a new private-only leakage inventory; do not include the leaked strings in a public report.
3. **Design:** Scan new added artifacts for absolute paths, credentials, model mount points, and request headers; output only pass/fail counts publicly. Discuss any history-rewrite remediation separately; do not force-push or modify accepted branches without approval.
4. **Expected:** No additional disclosure of private machine map in later public reporting.
5. **Test:** Pre-push sanitizer RED/GREEN with invented fake paths and secrets; manual review of generated diff.
6. **Provenance:** `AGENTS.md` confidentiality rules and observed public Markdown violations.

## Execution order and gates

1. **Now, parallel:** A HTTP400 real transport, B 20-loop/1-2-4-slot agentic matrix, with existing isolated tip. Preserve evidence privately.
2. **Independent grammar work:** C #650 backport and E undeclared-required schema parity; keep #802 R1 pinned as candidate.
3. **Candidate runtime:** D isolated GenAI rebuild, actual loaded DLL + token masks, rerun A/B and Gemma F; propose new lock **only** after review.
4. **Later:** G after a measured trigger. H applies to *every* publication step.
5. Never write into the accepted C6 checkout, staged runtime or source-lock until explicit approval. Never promote one-shot smoke to full acceptance.
