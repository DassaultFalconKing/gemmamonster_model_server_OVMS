# CODE-DELTA-AUDIT: known-good 9a162626 vs RC2 908d6695

```
DIRECT CORE DELTA: NONE (all 27 suspect files blob-identical; git diff -- src/llm/ empty)
TRANSITIVE DELTA: NONE in source (only non-LLM initializer hardening + harness/docs/tests)
BEST CURRENT SUSPECT: runtime/test-condition differences (prefix_caching ON vs OFF,
  parallel_tool_calls default true vs false, temp 0 vs 1.0) + stateful/transient
  executor behavior; no proven code regression. Known-good never ran the 4-turn sweep.
374-vs-371 ATTRIBUTION: RESOLVED — ChatTemplateAdapter JSON-string→object conversion
  (funcArgsToObjectHistory + toolResponseJsonContentToObjectHistory); offline render
  bypassed the adapter. Same code both revisions. No tokenizer/metrics anomaly.
LENGTH_WITH_EMPTY_OUTPUT ATTRIBUTION: UNKNOWN (stateful, single-instance, not reproduced;
  no code delta explains it; GRAMMAR_THRASH explicitly withheld)
NEXT MINIMAL EXPERIMENT: 4-turn sweep on RC2 binary under known-good conditions
  (prefix_caching=false graph, parallel_tool_calls=false, temp=1.0/top_p=0.95/top_k=64),
  then flip one variable at a time, prefix_caching first. Config-only, one instance.
```

Read-only audit. No src/ changes, no fixes, no `<call:...>` recovery. Product commit
range is linear: merge-base(9a162626, 908d6695) = 9a162626.

## 1. Exact refs

- known-good: `9a1626260614f68a6282b6799842d5152f0dcdff` ("test(gemma4): prove single-tag
  grammar multiplicity", 2026-09-11; its own diff is comments-only in
  generation_config_builder.hpp + a contract test — still present in RC2)
- RC2: `908d669563f57535ab4eb747989e9ab33dfd5267`
- local evidence: `9195c9eee` / `308f0d488` (branch docs/rc2-acceptance-20260914,
  docs/probes only; src/ untouched; worktree `git status` clean at audit time)
- known-good frozen combo: docs/gemmamonster/KNOWN-GOOD-TOOL-CALLING-20260911.md
  (binary E7D8024F…, OVMS 2026.4.0.9a1626260, Heretic VLM_CB, gemma4/gemma4,
  temp=1.0/top_p=0.95/top_k=64/max_tokens=256, parallel_tool_calls=false,
  scope = ONE tool-result continuation loop, i.e. 2 steps — never a 4-turn sweep)

## 2. Phase A — suspect-file blob verdicts (all IDENTICAL_BLOB)

Verified via `git rev-parse <sha>:<path>` pairwise (27/27 equal), consistent with
empty `git diff 9a162626..908d669 -- src/llm/`:

input_processor.{cpp,hpp}, input_processors/chat_template_processor.{cpp,hpp},
input_processors/tokenization_processor.{cpp,hpp}, base_generation_config_builder.{cpp,hpp},
generation_config_builder.hpp, output_parser.{cpp,hpp}, base_output_parser.{cpp,hpp},
output_parsing_config.hpp, default_content_parser.{cpp,hpp}, delta.hpp,
gemma4/gemma4_tool_parser.{cpp,hpp}, gemma4/gemma4_reasoning_parser.{cpp,hpp},
apis/openai_api_handler.{cpp,hpp}, servable.{cpp,hpp}, servable_initializer.{cpp,hpp}.

Sample blob IDs (RC2 = known-good): gemma4_tool_parser.cpp `d7d766e0…`,
output_parser.cpp `4a8c0a29…`, servable.cpp `b15d409a…`.

`CORE_DIRECT_DELTA = NONE`. Per STOP CONDITION A, proceed to transitive layers.

## 3. Whole-range code delta (what DID change, 9a162626..908d6695, ~60 commits)

- `src/llm/`: NOTHING (empty diff).
- `src/audio|embeddings|rerank/*_node_initializer.cpp`: try/catch(ov::Exception)
  wrappers around servable construction (d7bc3496b, 88ac984e2, 7758aafec).
  Init-time, other-modality calculators only. → IRRELEVANT (HIGH).
- `.bazelrc`: XNNPACK gcc<12 defines commented out (Linux CPU path; our binary is
  Windows GPU-serving). → IRRELEVANT (HIGH).
- `windows_build.bat` (VS path), `windows_install_build_dependencies.bat`
  (OpenCV toolset v142→v143): build-machine/deps-build only. → IRRELEVANT (HIGH).
- `scripts/gemmamonster/launch-stable-candidate.ps1`, packaging/test-gate scripts
  (PYTHONHOME/OVMS_DIR env, 4-DLL provenance pins, ovms_test gates): harness only;
  diagnostic runs used setupvars.bat directly. → IRRELEVANT (HIGH).
- Everything else: docs/, agent-worklog/, src/test/, tests/. No functional LLM delta.

## 4. Phase B — boundary findings

### B.1 InputProcessor construction — equivalent given same graph options (HIGH)

isVLM/isOmni/useMinja/caps/chain-order code is blob-identical; per-request TRACE
proves the live values: VLM_CB graph, MINJA template from the model
chat_template.jinja file, adapter caps
`requiresObjectArguments=true (dry-run probe override false→true, probe.cpp:128),
parseToolResponseJsonContent=true`. No evidence of divergent config state between
revisions for the same graph file.

### B.2 GenerationConfig flow — same code; different REQUEST inputs (HIGH)

Builder logic identical. But known-good requests used `parallel_tool_calls=false`
→ `stop_after_first=true`; our probes/sweep used the default `true` →
`stop_after_first=false`. Same source, materially different TriggeredTags grammar
input. Classification: RUNTIME_ONLY (test-condition), relevance MEDIUM
(grammar-shape effect on multi-turn continuation untested cross-wise).
Sampling differs too (1.0/0.95/64 vs greedy 0): determinism only, relevance LOW.

### B.3 VLM_CB execution path — source identical; one RUNTIME config delta (HIGH)

Known-good CLI run used proto defaults: `max_num_seqs=256` (same as our graph),
`enable_prefix_caching=false` (proto default, llm_calculator.proto:106).
Our RC2 diagnostic graph sets `enable_prefix_caching: true, cache_size: 0`.
Prefix-cache ON vs OFF is the prime statefulness suspect for a transient
post-tool continuation failure (cache hit/miss + eviction dynamics differ).
Classification: RUNTIME_ONLY_DELTA, relevance MEDIUM (untested flip).

### B.4 Output visibility/streamer lifecycle — no delta found (MEDIUM)

Streamer/parser/delta-channel/loopback/finish code blob-identical. Failing turns
emitted zero parseChunk calls and zero SSE deltas with finish=length — i.e.
nothing reached the parser callback; consistent with generation-side budget burn,
not with parser suppression (a swallowed frame would still show parseChunk inputs
at TRACE). No lifecycle delta to blame.

### B.5 Prompt-token accounting — RESOLVED, no anomaly (HIGH)

`usage.prompt_tokens` = local `req.inputIds.get_size()` (servable.cpp:751), NOT
VLMPerfMetrics. Server TRACE logs both the rendered text (servable.cpp:753) and
the IDs (servable.cpp:752): for turn-04 the 437 logged IDs byte-match an
independent tokenization of the logged text, and 437 == usage. The 374-vs-371
gap was an artifact of the OFFLINE render bypassing `ChatTemplateAdapter`:
`funcArgsToObjectHistory` + `toolResponseJsonContentToObjectHistory`
(chat_template_adapter.cpp:52,73; active per-request, caps both true) parse
tool-call arguments and tool-result JSON strings into objects, taking the
template's `is mapping` branches (`{text:<|"|>…}` /
`response:echo{echoed:<|"|>…}`) instead of the verbatim-string branches
(`{{"text":…}}` / `{value:<|"|>{"echoed":…}<|"|>}`). +3 tokens per exchange,
exactly the observed slope. Offline MINJA==Jinja2 byte-equality still holds;
the adapter sits upstream of both. Classification: ACCOUNTING_ONLY (our
measurement setup, not the server). Same code both revisions → cannot explain
any behavioral delta.

### B.6 Dependencies/build/runtime — runtime DLLs IDENTICAL (HIGH)

Known-good packaged DLLs vs RC2 repacked SHA256SUMS: openvino.dll `def53dd3…`,
openvino_genai.dll `9d1639af…`, openvino_tokenizers.dll `ef29a1d5…`,
tbb12.dll `60e4501c…` — all four byte-identical; dep SHAs match
(OpenVINO 227c33757d, GenAI 7ea25468). Only `ovms.exe` differs
(E7D8024F… vs 11d74fd9…), expected from rebuild (version stamp
2026.4.0.9a1626260→2026.4.0.908d66956 + non-LLM initializer code).
No dependency-regression claim possible. `ovms.exe`-internal LLM .obj
equivalence not byte-proven without a rebuild → stated as residual, LOW.
Model export: the ENTIRE Heretic dir was rewritten 2026-09-12 (between the
09-11 known-good runs and the 09-14 diagnostic) — tokenizer, detokenizer,
language model, embeddings, chat_template.jinja, configs. No 09-11 copy exists
to diff → content equivalence UNKNOWN. Classification: RUNTIME_ONLY_DELTA,
confidence MEDIUM as a candidate layer, LOW for either specific symptom
(current export renders/parses canonically in all clean probes).

## 5. Phase C — archaeology notes

Range is ~60 commits: B-parity/toolchain/preflight recipe work, Windows stress
gates/skip contracts, C-API/death-test hardening, worklog/docs, plus the three
non-LLM initializer hardening commits above. No commit touches src/llm/,
VLM_CB execution, token accounting, or the model export (export is outside git).
`9a162626` itself only added comments + a single-tag multiplicity contract test.
There is no commit to bisect for src/llm behavior — the tree is flat there.

## 6. Phase D — working-vs-broken table

| Layer | Known-good 9a162626 | RC2 908d669 | Delta? | Relevance |
|---|---|---|---|---|
| Gemma4 tool parser (`d7d766e0…`) | blob | same blob | no | — |
| Gemma4 reasoning parser | blob | same blob | no | — (never engages in this path per TRACE) |
| Generation config builder | blob (+comments) | same blob | no | grammar INPUT differed via parallel_tool_calls (request-level) |
| Chat template processor/adapter | blob | same blob | no | adapter explains 374-vs-371 (ACCOUNTING_ONLY) |
| Input processor chain | blob | same blob | no | — |
| VLM_CB execution/streamer | blob | same blob | no | prefix_caching runtime flag differs (graph vs CLI default) |
| prompt token accounting | inputIds (code) | inputIds (code) | no | 437==437 proven; no anomaly |
| runtime DLLs (OV/GenAI/Tok/TBB) | def53…/9d16…/ef29…/60e4… | identical hashes | no | dependency regression excluded |
| ovms.exe binary | E7D8024F… | 11d74fd9… | yes (rebuild+stamp+non-LLM init) | LOW |
| model export (Heretic dir) | 09-11 vintage | rewritten 09-12 | yes, content cmp UNKNOWN | MEDIUM layer / LOW symptom link |
| request conditions | ptc=false,temp 1.0 | ptc default true,temp 0 | yes (test setup) | MEDIUM (untested cross) |
| multi-turn test coverage | 2-step loop only | 4-turn sweep (1 transient fail) | coverage gap | HIGH epistemic: no proven regression |

## 7. Classification of findings

- 27 suspect files IDENTICAL_BLOB → no DIRECT_DELTA (HIGH).
- Non-LLM initializer hardening, .bazelrc, build bats, launcher/gate scripts →
  IRRELEVANT (HIGH).
- prefix_caching ON-vs-OFF, parallel_tool_calls default-vs-false, temp 0-vs-1.0 →
  RUNTIME_ONLY_DELTA (HIGH confidence they differ; MEDIUM that one matters).
- ovms.exe rebuild difference → RUNTIME_ONLY_DELTA (HIGH differs / LOW relevance).
- 09-12 model re-export → RUNTIME_ONLY_DELTA (HIGH differs / LOW symptom link).
- 374-vs-371 → ACCOUNTING_ONLY, RESOLVED via ChatTemplateAdapter (HIGH).
- LENGTH_WITH_EMPTY_OUTPUT mechanism → UNKNOWN (HIGH confidence it is unproven;
  stateful/transient; withheld GRAMMAR_THRASH per evidence rule).
- `<call:...>` on clean RC2 → NOT_REPRODUCED (unchanged).

## 8. Boundary of knowledge (what would prove more)

1. Rerun the 4-turn sweep on the RC2 binary with known-good conditions
   (prefix_caching=false graph; parallel_tool_calls=false; temp=1.0/top_p=0.95/
   top_k=64), flipping one variable at a time. Decides the two RUNTIME_ONLY
   suspects without touching code.
2. Long mixed-load soak to re-trigger LENGTH_WITH_EMPTY_OUTPUT; capture its TRACE
   parseChunk/Pipeline-input-text the way turn-04's success was captured.
3. Recover or rebuild the 09-11 model export (check backups/optimum cache) for an
   export A/B — only if (1) is clean.
