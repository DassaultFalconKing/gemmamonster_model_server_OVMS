# Gemma4 whitespace regression 2026-09-16 — repair handoff

This file is the interruption-safe work ledger and final implementation handoff for the named-tool streaming whitespace regression.

## Status

```text
IMPLEMENTATION_COMMITTED
SOURCE_DIFF_VERIFIED
HOST_BUILD_NOT_RUN
LIVE_REPRO_NOT_RERUN
```

Do not describe this as a runtime-verified fix until the Windows/Arc live gate below passes. The code repair is committed; build and original-symptom verification require the OVMS host.

## Authority / starting point

- OVMS repair branch: `fix/gemma4-whitespace-regression-1609`
- Parent PR-prep branch: `upstream/gemma4-tool-calling`
- Parent head at start: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`
- Production fix commit: `a3a7004bdca0454fa905f38077299aa7a94a1c99`
- Current upstream OVMS GenAI pin: `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`
- Current XGrammar pin through that GenAI commit: `v0.1.31`
- GenAI companion branch: `DassaultFalconKing/openvino.genai:fix/schema-whitespace-bound-fe818c04-2026.5`
- GenAI RED contract commit: `d636c405e9b822a7008d4475a0d550a82d52a02f`
- GenAI companion HEAD: `e00eada6f4cce794ac3b3f6053cdb0c9dc569e68`
- XGrammar repair revision: `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`

## Evidence disposition

Cursor and Codex agree on the important boundary: the whitespace token ids exist before OVMS parser/SSE serialization. The stronger root-cause result is the grammar trap:

1. Gemma4 emits the native begin tag `<|tool_call>call:search_docs`.
2. JSONSchema then permits unlimited inter-element whitespace before `{`.
3. On the long named-tool prompt the greedy path can remain in `\n`/`\t` indefinitely.
4. Generation reaches `max_tokens`; parser never receives `{`, so no tool-call phase opens.
5. Unary on the exact same prompt happened to choose `{` and completed the call.

The observed `read()` vs `read_all()` split is therefore retained as a symptom boundary, not patched as the cause. No parser, streamer, SSE or CB read-loop workaround was added.

## Exact repair

### 1. GenAI companion capability

Branch `fix/schema-whitespace-bound-fe818c04-2026.5` starts at the exact OVMS pin `fe818c0467...` and adds:

- `StructuredOutputConfig::JSONSchema(schema, optional<int> max_whitespace_cnt)`;
- serialization of the optional bound into structural-tag JSON;
- equality/to-string semantics including the bound;
- XGrammar pin `9aa840b6...`, whose `JSONSchemaFormat` consumes per-tag `max_whitespace_cnt`;
- four C++ regression contracts: legacy serialization, bound=2, explicit zero, equality policy.

Diff audit `fe818c04...e00eada6`:

```text
src/cpp/CMakeLists.txt                                  1 + / 1 -
src/cpp/include/openvino/genai/generation_config.hpp   9 + / 4 -
tests/cpp/test_structured_output_json_schema.cpp       35 +
```

The pre-patch blobs of `generation_config.hpp` and `src/cpp/CMakeLists.txt` are byte-identical between the historical validated 2026.4 companion base and current `fe818c04`. The established patched blobs were therefore transplanted exactly rather than manually reconstructed.

### 2. OVMS regression contract

Added target:

```text
//src/test/llm/gemma4_generation:gemma4_whitespace_bound_test
```

For hard named `weather`, it inspects:

```text
Union -> TagsWithSeparator -> Tag -> JSONSchema
```

and requires:

```text
max_whitespace_cnt.has_value()
max_whitespace_cnt == 2
serialized structural JSON contains "max_whitespace_cnt": 2
```

This contract was authored before the production line change. With the companion GenAI API and old OVMS builder it is the intended RED assertion. No native RED/GREEN execution was possible from this connector environment.

### 3. OVMS production change

Only one production line changed in `Gemma4GenerationConfigBuilder::buildToolTag()`:

```cpp
JSONSchema(toolSchemaWrapper.stringRepr)
```

became:

```cpp
JSONSchema(toolSchemaWrapper.stringRepr, 2)
```

Because `buildToolTag()` is shared by auto/required/named tool grammars, every Gemma4 tool JSON schema gets the same bounded inter-element whitespace policy. JSON whitespace inside string values is unaffected.

## OVMS diff audit

Against `upstream/gemma4-tool-calling@d582668e...`, the repair branch contains only:

```text
docs/whitespace_regression_1609/HANDOFF.md             work ledger / handoff
src/llm/io_processing/generation_config_builder.hpp    1 + / 1 - production
src/test/llm/gemma4_generation/BUILD                   + regression target
src/test/llm/gemma4_generation/gemma4_whitespace_bound_test.cpp
```

The production commit `a3a7004...` itself is exactly one hunk and one changed line.

## Explicit non-fixes / untouched areas

- `Gemma4ToolParser`: untouched.
- `OVMSTextStreamer`: untouched.
- SSE response serialization: untouched.
- continuous-batching `read()` / `read_all()`: untouched.
- rendered-prompt adaptation: untouched.
- prompt wording: untouched.
- prefix-cache behavior: untouched.
- unrelated 2026.4 parser/builder code: not imported.

## Required Windows host gate

The OVMS branch intentionally does **not** pin an upstream PR to the user's GenAI fork. For local verification, override the `versions.mk` `?=` values through the environment; the Windows dependency script explicitly preserves environment overrides.

PowerShell before dependency/source build:

```powershell
$env:OV_USE_BINARY = "0"
$env:OV_GENAI_ORG = "DassaultFalconKing"
$env:OV_GENAI_BRANCH = "e00eada6f4cce794ac3b3f6053cdb0c9dc569e68"
```

Then use the normal source-dependency/build environment for this PR branch. `windows_install_build_dependencies.bat` will clone that exact GenAI commit and its frozen XGrammar revision when `OV_USE_BINARY=0`.

Minimum focused test gate after dependencies are rebuilt:

```text
bazel test //src/test/llm/gemma4_generation:gemma4_whitespace_bound_test \
  --config=win_mp_on_py_off --nocache_test_results --test_output=all
```

Then rerun the existing Gemma4 semantic suite on the same binary/dependency set. Do not reuse the earlier 64/64 result as evidence for this HEAD.

## Required live gate: original symptom

Use the original exact long-context request:

- `/v3/chat/completions`
- `temperature: 0.0`
- `max_tokens: 512`
- named `tool_choice=search_docs`
- same 5-sentence runbook paragraph repeated x60
- same tools/schema

Gate it as follows:

1. `stream=false` remains a valid `search_docs` tool call.
2. `stream=true` must emit a valid `search_docs` tool call instead of reaching `finish_reason=length` with `\n\t` residue.
3. Repeat streaming at least three times because the original trap was a legal greedy branch and one pass is weak evidence.
4. Capture raw ids / decode with specials visible if available; verify the tool begin tag is followed by bounded whitespace and `{`, not an unbounded whitespace run.
5. If failure persists after the grammar bound is confirmed in the effective structural JSON, only then reopen the CB `read()`/`read_all()` hypothesis.

## CI / verification state at handoff

- GitHub combined status for GenAI `e00eada6...`: no statuses reported.
- GitHub workflow runs for that commit: none reported.
- GitHub combined status for OVMS production commit `a3a7004...`: no statuses reported.
- Source-level compare/diff verification: completed.
- Native GenAI compile: not run here.
- Native OVMS Bazel test: not run here.
- Windows package build: not run here.
- Arc 140V live request: not run here.

## Work stages

- [x] S0 — resolve report branches and PR-prep branch.
- [x] S1 — read Cursor + Codex reports and original capture.
- [x] S2 — trace current OVMS builder, GenAI pin and XGrammar capability.
- [x] S3 — confirm historical repair shape and exact XGrammar support.
- [x] S4 — create companion GenAI branch from exact `fe818c04`; add regression contract first.
- [x] S5 — port typed whitespace-bound API + exact XGrammar repair revision; inspect diff.
- [x] S6 — add OVMS Gemma4 regression contract before production change.
- [x] S7 — apply only `max_whitespace_cnt=2` in Gemma4 `buildToolTag()`.
- [x] S8 — verify repository diffs, exact production hunk and GitHub status availability.
- [x] S9 — record exact SHAs and host verification protocol in this handoff.
- [x] S10 — implementation/ref handoff prepared.

## Resume point

**Resume on the Windows/Arc host at the Required Windows host gate above.** Do not make more parser/streamer changes before running that gate. If the focused test and live repro are green, the next repository task is dependency/upstream packaging: land or otherwise make the GenAI whitespace-bound capability available from an upstream-compatible pin, then re-run the full PR acceptance suite on the final OVMS HEAD.
