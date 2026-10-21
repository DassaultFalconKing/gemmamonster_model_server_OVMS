# Whitespace and empty-argument defect taxonomy

Status: **HISTORICAL C5 VERDICT VERIFIED; PUBLIC XGRAMMAR STATUS VERIFIED; LOCAL PATCH BINARIES NOT VERIFIED**  
Checked: 2026-10-21  
Scope: Gemmamonster C5/C6 → Qwenmonster XML adaptation. Avoid diagnosis by substring ("whitespace", "empty args") alone.

## 1. Four distinct phenomena

| ID | Trigger | Layer / behavior | Evidence / fix | Verdict |
|---|---|---|---|---|
| G-JWS | Gemma tool JSON grammar emits unbounded whitespace | GenAI JSON Schema → constrained decoder | OVMS `205b59871336a0689f1951b34acfbdbdee008f16` and C6 transfer `08e9e8e9ed921c4ad4e12cc1a6b6821edac7a5cb`; current C6 Gemma builder uses `JSONSchema(schema, 2)` | **CONFIRMED FIXED** in historical C5 verdict; do not equate with XML |
| G-EA | Tool declares required arguments but output unexpectedly becomes `{}` | model/grammar/parser/sampling attribution | `24847c96805b28e4625fd85dbf98bece20ed2d3e` frozen report: 267 subsequent filled canonical calls; A/B/C exonerated, sampling unresolved, persistent defect not established | **NOT REPRODUCED**; not basis for unrelated product repair |
| Q-END | Qwen XML string argument end marker drifts to `</parameter1>` after excluded prefix `</parameter` | XGrammar `TagDispatch` excluded string path | [#650](https://github.com/mlc-ai/xgrammar/issues/650), fix [PR #651](https://github.com/mlc-ai/xgrammar/pull/651) | **OPEN / PR UNMERGED** as of 2026-10-21 |
| Q-ZERO | XML tool declares *no* parameters, `properties={}`; generated content can get stuck in whitespace-only loop | XGrammar `qwen_xml_parameter` empty-object grammar | [#802](https://github.com/mlc-ai/xgrammar/issues/802), [PR #803](https://github.com/mlc-ai/xgrammar/pull/803), [PR #837](https://github.com/mlc-ai/xgrammar/pull/837) | **OPEN / BOTH PRs UNMERGED** as of 2026-10-21 |

**G-EA and Q-ZERO are not synonymous.** G-EA describes an anomalous *missing required argument*; Q-ZERO describes a legitimate tool whose correct normalized arguments are `{}`, with a grammar that must generate a finite empty XML block.

## 2. Local patch provenance vs published upstream

Reported by the local C6 operator:

- Gemma bounded whitespace via `JSONSchema(..., 2)`: OVMS commit `205b59871`, C6 port `08e9e8e9e`; both resolved to public commits in the Gemmamonster fork.
- GenAI `max_whitespace_cnt` forwarding: local commit `bf3255153ee73faeee9c7da277853ab6aa9298e2`, `C:/gm/c6/genai/src/cpp/include/openvino/genai/generation_config.hpp:182`.
- XGrammar empty `ExcludeToken()` repair: local commit `f228574c0e7592f029407973092261a611f8ff61`; local report `C:/gm/c6/evidence/xgrammar-empty-exclude-findings.md`.
- Token bridge matcher checks: local `C:/gm/c6/evidence/genai-token-bridge-report.md`.

**Verification level:** two OVMS commits and the C5 verdict were verified through GitHub. The local GenAI/XGrammar commit IDs above were not resolvable under their *upstream* repositories at the earlier check; the XGrammar commit `f228574c...` is now public in `DassaultFalconKing/xgrammar`'s legacy branch, while the locked new public forks and SHA inventory have been verified. The local evidence files themselves were not fetched from this GitHub session. Do not claim their exact diff or runtime validation based solely on those paths. Audit them on the build host and record `git show` + library hash.

## 3. API compatibility trap

- Local C6 `src/llm/io_processing/gemma4/generation_config_builder.hpp` line 66 calls `JSONSchema(toolSchemaWrapper.stringRepr, 2)`.
- The earlier upstream GenAI snapshot `openvinotoolkit/openvino.genai@6a35b97bbab88120930a87d81c2ecccd12fc0ba9` declares only `JSONSchema(const std::string& schema)`, **but the newly published locked patched fork `DassaultFalconKing/openvino.genai@2decb9ec4bea827e01db47524352ad72d23b33ab` explicitly declares `JSONSchema(const std::string& schema, std::optional<int> whitespace_bound = std::nullopt)` and serializes `max_whitespace_cnt`. The patched source compatibility is now verified**.
- In that same public GenAI header, `QwenXMLParametersFormat(const std::string&)` serializes to `{"type":"qwen_xml_parameter","json_schema":...}` and **does not supply an equivalent `max_whitespace_cnt` argument**.

Conclusion: G-JWS's two-argument constructor depends on the now-public pinned GenAI fork. The locked XGrammar source also carries the empty `ExcludeToken()` semantics. **Neither G-JWS's JSON schema bound nor ExcludeToken hardening establishes that Q-END/Q-ZERO are fixed.** A local backport of PR #651 and a selected #803/#837 equivalent must be separately justified and tested for the actual XGrammar pin, not blanket-cherry-picked blindly.

## 4. Orthogonal acceptance and failure attribution

| Test | Schema | Native stimulus | Expected result | What it proves |
|---|---|---|---|---|
| T-G-JWS | Gemma tool JSON | strict `JSONSchema(schema, 2)` | bounded JSON whitespace under canonical profile | JSON fix only |
| T-G-EA | Gemma tool with mandatory `city` | 267 canonical filled calls historical evidence | remain **NOT REPRODUCED** unless new RED evidence | not an XML bug |
| T-Q-REQ | XML function requiring `city` | valid and invalid fields, unary/SSE | valid typed payload or explicit refusal; never silently emit `{}` as successful required call | schema/API correctness |
| T-Q-ZERO | XML function without parameters | actual guided decoding with `properties={}`, `required=[]` | complete finite XML, zero `<parameter>` children, JSON `{}`; no infinite whitespace | empty XML grammar termination |
| T-Q-END | XML string parameter | attempt `</parameter1>`; fragment `</parameter>` at every boundary | constrained mask blocks invalid close; parser rejects malformed native output | XML end marker stability |

Capture decoder token IDs, grammar mask/allowed tokens, complete native output, parser deltas, API JSON, model/tokenizer/schema/version and finish reason. A **parser-only** test rejecting `</parameter1>` does *not* show the grammar is fixed. A parser-only test reading `{}` does *not* show a generator can terminate Q-ZERO.

## 5. Engineering direction

1. **Do not modify Gemma known-good** or rewrite the historical G-EA verdict to justify new behavior.
2. Use the public source lock and offline preflight (`PUBLIC-COHORT-INTEGRATION.md`); independently pin actual compiled GenAI/XGrammar library identities, matcher and GPU evidence.
3. Run T-Q-ZERO and T-Q-END against the current deployed XGrammar first; save RED if reproduced.
4. Evaluate PR #651 and the overlapping alternative PRs #803/#837 against that pin. Select minimal semantic backport after differential tests; do not stack both zero-arg proposals without reviewing their overlap.
5. Keep Qwen parser safety checks for required schema fields, unknown names and malformed XML separate from generator grammar fixes.
6. Re-run Gemma baseline and full Qwen generation suite, actual GPU live tests; only then claim Qwen XML acceptance.

## References

- [Historical C5 verdict commit](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/commit/24847c96805b28e4625fd85dbf98bece20ed2d3e)
- [OVMS whitespace fix](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/commit/205b59871336a0689f1951b34acfbdbdee008f16)
- [C6 whitespace port](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/commit/08e9e8e9ed921c4ad4e12cc1a6b6821edac7a5cb)
- [XGrammar #650](https://github.com/mlc-ai/xgrammar/issues/650), [PR #651](https://github.com/mlc-ai/xgrammar/pull/651)
- [XGrammar #802](https://github.com/mlc-ai/xgrammar/issues/802), [PR #803](https://github.com/mlc-ai/xgrammar/pull/803), [PR #837](https://github.com/mlc-ai/xgrammar/pull/837)

## Update: public fork publication (2026-10-21)
- Source lock: `docs/qwenmonster/public-source-lock.json`, GitHub publication manifest in `DassaultFalconKing/openvino.genai` branch `docs/public-cohort-20261021`.
- Source-level availability **verified** for GenAI `2decb9ec...`, XGrammar `c77d5e0d...`, OpenVINO `b5bfb148...`, Minja `83eb074e...`.
- The actual patched GenAI `JSONSchema(schema, whitespace_bound)` is now **publicly confirmed**; the previous "unverifiable local patch" caveat applies only to actual local binary/runtime evidence, not available source.
- The XGrammar locked source includes empty `ExcludeToken()` support. The XML end-marker (#650/#651) and zero-parameter XML loop (#802/#803/#837) remain separate issues; no asserted fix.
