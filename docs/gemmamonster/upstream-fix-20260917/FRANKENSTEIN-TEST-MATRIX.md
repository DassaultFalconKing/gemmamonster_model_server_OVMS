# Gemma4 Frankenstein Candidate Build / Test Matrix

Status: `TEST_AUTHORITY / EXECUTION_PENDING`
Date: 2026-09-17

## 1. Goal

Validate the Gemma4 stack as a sequence of deliberately mixed candidates. Each candidate changes only one major dependency/source axis at a time so a RED result remains attributable.

The final promotion target is `SUPER-UPSTREAM`: fresh OVMS upstream + clean Gemma4 series + fresh OpenVINO GenAI upstream + fresh compatible XGrammar upstream + bounded JSON-schema whitespace.

This document is the authority for candidate identity, build composition, gates, promotion, and evidence layout.

## 2. Three independent axes

### OVMS axis

- `O0` upstream Gemma4 PR baseline: `d582668e6405e5d4cffbf050e9ee7303f7b94ef0`.
- Its upstream base at matrix creation: `openvinotoolkit/model_server:main` `204d3bf3ba6f8e2aeb489c5eeb7ab46c79fde482`.
- `O1` parser/evidence repair: `fix/gemma4-upstream-evidence-triage-20260917`, matrix-time HEAD `405c3887aa893076489a7ae1a48926d9f186478e`, final HEAD to be pinned after the last HTTP expectation repair.
- `O2` OVMS whitespace call-site repair: production commit `a3a7004bdca0454fa905f38077299aa7a94a1c99` plus focused whitespace test/build registration from `fix/gemma4-whitespace-regression-1609` (`3ed4ad8...` handoff HEAD).
- `O3` clean reviewer-facing Gemma4 series regenerated on the freshly re-resolved OVMS upstream head immediately before PR.

At matrix creation, `d582668` is 5 commits ahead and 0 behind `204d3bf`, so OVMS is already on the current upstream base. Re-resolve again before `SUPER-UPSTREAM`.

### OpenVINO GenAI axis

- `G0` stock old base: `fe818c0467feb17b87c5adfb3f7e28dd70b76e99`.
- `G1` old-base whitespace repair: `e00eada6f4cce794ac3b3f6053cdb0c9dc569e68`, test pin `d636c405e9b822a7008d4475a0d550a82d52a02f`.
- `G2` upstream master at matrix creation: `438e06189a07fe464fe39c544ac7997b73ca973d` + clean replay of the two whitespace commits.
- `G3` freshly re-resolved GenAI master immediately before PR + clean whitespace series.

`fe818c04..438e061` is 20 upstream commits. `src/cpp/include/openvino/genai/generation_config.hpp` and `src/cpp/CMakeLists.txt` are byte-identical across those two upstream heads, so there is no direct file-level conflict with our whitespace API/pin patch. Runtime interaction still requires testing because the 20 commits include Continuous Batching changes.

### XGrammar axis

- `X0` stock GenAI pin: `v0.1.31`.
- `X1` validated bounded-whitespace pin: `9aa840b6d16abf094f3e8e2ac9c10465b77656c9`.
- `X2` XGrammar upstream `main` at matrix creation: `f6043f4daafd0d018f77c3ec07bcfcd70b7e0532`.
- `X3` freshly re-resolved XGrammar upstream head immediately before PR.

`X2` is 7 commits ahead and 0 behind `X1`. Current upstream still exposes `max_whitespace_cnt` in structural-tag / JSON-schema paths. Its HEAD commit explicitly reports differential validation against `9aa840b6`, including whitespace-limit cases. We still treat `X1 -> X2` as a separate experiment rather than trusting upstream test prose as a substitute for our Gemma4 runtime gate.

## 3. Known control behavior

### Semantic control

On `d582668`:

- 6 / 6 Bazel targets passed.
- 64 / 64 cases passed.
- exit code 0.

Targets:

1. `//src/test/llm/gemma4_generation:gemma4_generation_policy_test` — 27.
2. `//src/test/llm/gemma4_generation:gemma4_phantom_tool_call_test` — 12.
3. `//src/test/llm/gemma4_generation:gemma4_chunk_invariance_test` — 4.
4. `//src/test/llm/gemma4_generation:gemma4_rendered_prompt_state_test` — 11.
5. `//src/test/llm/gemma4_generation:gemma4_f7_contract_test` — 5.
6. `//src/test/llm/gemma4_generation:gemma4_f10_guard_test` — 5.

### Compatibility control

Filtered `//src:ovms_test` on `d582668`:

- 229 ran;
- 213 passed;
- 16 failed.

Full triage classification:

- 1 environmental missing `opt-125m` fixture;
- 1 stale HTTP hard-named-tool expectation;
- 1 test-helper lossless-number defect;
- 1 real escaped-delimited-string parser regression;
- 12 stale parser expectations against accepted atomic / fail-closed semantics.

### Live whitespace control

Exact long-context named request:

- `POST /v3/chat/completions`;
- `temperature: 0.0`;
- `max_tokens: 512`;
- named `tool_choice=search_docs`;
- same tools/schema;
- same 5-sentence runbook paragraph repeated x60;
- model `gemma4-26-heretic`;
- GPU / `VLM_CB` / Gemma4 parser + reasoning parser / guided generation / u4 KV / prefix cache / `max_num_batched_tokens=4096`.

Control result:

- unary: valid `search_docs` in 23 completion tokens;
- streaming: newline/tab degeneration to `finish_reason=length`, no tool call.

## 4. Frankenstein candidate matrix

| ID | Candidate | OVMS | GenAI | XGrammar | Changes isolated | Promotion signal |
|---|---|---|---|---|---|---|
| C0 | `BASE-CONTROL` | `O0` | `G0` | `X0` | none | reproduce known controls: 64/64; archived 213/229; long unary PASS / long stream degenerates |
| C1 | `PARSER-ONLY` | final `O1` | `G0` | `X0` | OVMS parser + stale-test reconciliation only | 229/229 with fixtures + 64/64; whitespace live failure may remain |
| C2 | `WHITESPACE-OLDBASE` | `O0 + O2` | `G1` | `X1` | grammar-level whitespace repair only | GenAI whitespace tests + OVMS whitespace test + live stream >=3/3 |
| C3 | `FRANKENSTEIN-OLD` | `O1 + O2` | `G1` | `X1` | full OVMS repair stack, old GenAI base | 229/229 + 64/64 + live stream >=3/3 + dogfood replay |
| C4 | `FRANKENSTEIN-NEWGENAI` | byte-identical to C3 | `G2` | `X1` | GenAI 20-commit upstream delta only | behavior must match C3; new RED => GenAI delta/interaction suspect |
| C5 | `FRANKENSTEIN-NEWXGRAMMAR` | byte-identical to C3/C4 | byte-identical GenAI whitespace code to C4 except pin | `X2` | XGrammar 7-commit upstream delta only | behavior must match C4; new RED => XGrammar delta/interaction suspect |
| C6 | `SUPER-UPSTREAM` | `O3` | `G3` | `X3` | all freshly re-resolved upstreams, clean histories | every gate GREEN + clean-build reproducibility + reviewer-ready diffs |

## 5. Construction rules

### C1 `PARSER-ONLY`

Must contain only the net repair outcomes:

- lossless-number test-helper fix;
- escaped-delimited-string production parser fix;
- legacy parser expectations reconciled to atomic envelope semantics;
- unknown hard-named HTTP tool choice expects `INVALID_ARGUMENT`;
- no GenAI/XGrammar/whitespace dependency change.

The missing `facebook/opt-125m` fixture must be provided before declaring 229/229.

### C2 `WHITESPACE-OLDBASE`

Exact dependency pair:

- OVMS whitespace branch derived from `d582668`, production call site `JSONSchema(schema, 2)`;
- GenAI `e00eada6`;
- XGrammar `9aa840b6`.

C2 answers one question: does the bounded grammar fix the original live degeneration without parser repairs?

### C3 `FRANKENSTEIN-OLD`

Planned branch:

`test/gemma4-frankenstein-oldbase-20260917`

Base: `d582668`.

Carry only net source/test changes from C1 and O2. Exclude repair-session audit/revert/checkpoint debris from the executable history. GenAI stays exactly `e00eada6`; XGrammar stays exactly `9aa840b6`.

### C4 `FRANKENSTEIN-NEWGENAI`

Planned GenAI branch:

`fix/schema-whitespace-bound-master-20260917`

Base: `438e061`.

Replay logically:

1. `d636c40` whitespace API contract test;
2. `e00eada6` implementation.

Expected touched surface remains:

- `src/cpp/include/openvino/genai/generation_config.hpp`;
- `src/cpp/CMakeLists.txt`;
- `tests/cpp/test_structured_output_json_schema.cpp`.

Keep XGrammar pinned to `9aa840b6`. The OVMS tree must be byte-identical to C3.

### C5 `FRANKENSTEIN-NEWXGRAMMAR`

Planned GenAI experiment branch:

`test/schema-whitespace-bound-master-xgrammar-main-20260917`

Base: exact C4 GenAI HEAD.

Change exactly one behavioral dependency:

```cmake
XGRAMMAR_VERSION 9aa840b6d16abf094f3e8e2ac9c10465b77656c9
```

to:

```cmake
XGRAMMAR_VERSION f6043f4daafd0d018f77c3ec07bcfcd70b7e0532
```

No OVMS change. No GenAI API/logic change. This makes C4 -> C5 a clean XGrammar A/B.

Before executing, audit `9aa840b6..f6043f4` and record the seven commits. Because upstream touches JSON-schema converter internals, source-level clean application is insufficient; live Gemma4 whitespace tests remain mandatory.

### C6 `SUPER-UPSTREAM`

Immediately before construction:

1. re-resolve `openvinotoolkit/model_server:main`;
2. re-resolve `openvinotoolkit/openvino.genai:master`;
3. re-resolve `mlc-ai/xgrammar:main`;
4. record all three exact SHAs;
5. compare each with C3/C4/C5 bases;
6. regenerate clean reviewer-facing OVMS and GenAI histories;
7. pin the exact XGrammar SHA demonstrated GREEN by the fresh candidate.

Planned branches:

- OVMS: `upstream/gemma4-tool-calling-super-20260917`;
- GenAI: `upstream/schema-whitespace-bound-super-20260917`.

C6 must not contain evidence/checkpoint commits, accidental broad test edits, audit/revert pairs, or machine-local paths/logs.

## 6. Gate matrix

Legend: `REQ` required to promote; `OBS` useful observation; `CTRL` expected control behavior.

| Gate | C0 | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| G0 identity manifest | REQ | REQ | REQ | REQ | REQ | REQ | REQ |
| G1 GenAI `StructuredOutputJSONSchema.*` | CTRL | CTRL | REQ | REQ | REQ | REQ | REQ |
| G2 OVMS whitespace-bound focused test | n/a | n/a | REQ | REQ | REQ | REQ | REQ |
| G3 filtered 229-case `ovms_test` | CTRL | REQ | OBS | REQ | REQ | REQ | REQ |
| G4 6-target / 64-case semantic gate | REQ | REQ | REQ | REQ | REQ | REQ | REQ |
| G5 exact long named unary | REQ | REQ | REQ | REQ | REQ | REQ | REQ |
| G6 exact long named stream | CTRL fail | OBS | REQ >=3/3 | REQ >=3/3 | REQ >=3/3 | REQ >=3/3 | REQ >=3/3 |
| G7 existing dogfood replay | OBS | REQ | REQ | REQ | REQ | REQ | REQ |
| G8 intended-file/source-diff audit | REQ | REQ | REQ | REQ | REQ | REQ | REQ |
| G9 clean build/output root | OBS | OBS | OBS | OBS | OBS | OBS | REQ |
| G10 dependency-axis A/B equivalence | n/a | n/a | n/a | baseline | C4 == C3 | C5 == C4 | C6 >= C5 |

## 7. Exact automated gates

### G1 GenAI whitespace API

Run `StructuredOutputJSONSchema.*` from GenAI C++ tests.

Required 4/4:

- `LegacySerializationDoesNotSetWhitespaceBound`;
- `BoundIsSerializedAtSchemaFormatLevel`;
- `ZeroBoundIsNotTreatedAsUnset`;
- `EqualityIncludesWhitespacePolicy`.

### G2 OVMS whitespace call-site

```powershell
bazel test //src/test/llm/gemma4_generation:gemma4_whitespace_bound_test `
  --config=win_mp_on_py_off `
  --nocache_test_results `
  --test_output=all
```

Expected: effective `max_whitespace_cnt == 2` in the Gemma4 structural JSON schema.

### G3 229-case compatibility

Use the evidence environment:

- Windows;
- MSVC `C:\BuildTools` 14.44.35207;
- MSYS bash first in `PATH`;
- `BAZEL_SH=C:/opt/msys64/usr/bin/bash.exe`;
- Python 3.12.10;
- `--output_user_root=C:/o`;
- `win_mp_on_py_on`.

```text
bazel test --config=win_mp_on_py_on --nocache_test_results --test_output=all \
  --test_env=PYTHONPATH=<workspace>/bazel-out/x64_windows-opt/bin/src/python/binding;C:/opt/openvino/python \
  --test_filter=Gemma4OutputParserTest.*:Gemma4UpstreamRefitContractTest.*:Gemma4SpecialTokenHandoffTest.*:HttpOpenAIHandlerParsingTest.* \
  //src:ovms_test
```

Required fixtures:

- Gemma4 E4B junction/fixture;
- `facebook/opt-125m` fixture.

Promotion expectation for C1/C3/C4/C5/C6: 229/229.

### G4 semantic suite

Run the six targets in section 3 with:

```text
--config=win_mp_on_py_off --nocache_test_results --test_output=all
```

Promotion expectation: 6/6 targets, 64/64 cases, exit 0. Historical 64/64 cannot be reused for a new candidate HEAD.

## 8. Live gates

### G5/G6 exact long-context named pair

For every promoted whitespace-enabled candidate:

1. exact request with `stream=false`;
2. exact same request with `stream=true` three times;
3. preserve raw unary JSON and each SSE stream;
4. record prompt/completion tokens and finish reason;
5. verify valid `search_docs` call;
6. reject newline/tab-only `finish_reason=length`.

Required: unary GREEN and streaming 3/3 GREEN.

Interpretation boundary:

- C3 GREEN, C4 RED => GenAI upstream delta/interaction primary suspect.
- C4 GREEN, C5 RED => XGrammar upstream delta/interaction primary suspect.
- C5 GREEN => fresh XGrammar is a viable input to `SUPER-UPSTREAM`.

### G7 dogfood replay

Replay:

- long-context `auto`;
- `required`;
- named unary;
- named streaming;
- Responses API parallel calls;
- long reasoning + two parallel calls.

No parser leakage, malformed executable call, whitespace degeneration, or protocol break.

## 9. Build isolation and evidence

Recommended artifact root:

```text
C:\git\artifacts\gemma4-frankenstein-20260917\
  C0-base-control\
  C1-parser-only\
  C2-whitespace-oldbase\
  C3-frankenstein-old\
  C4-frankenstein-newgenai\
  C5-frankenstein-newxgrammar\
  C6-super-upstream\
```

C1-C5 may use incremental compilation, but each candidate must have a distinct artifact/output identity. C6 requires a clean build/output root; cached downloads are allowed, stale compiled objects from another candidate are not final evidence.

Each candidate must contain an identity manifest with at least:

```text
candidate_id
ovms_branch
ovms_head
ovms_dirty
ovms_upstream_base
ov_genai_branch
ov_genai_head
ov_genai_upstream_base
xgrammar_sha_or_tag
xgrammar_upstream_base
openvino_pin
openvino_tokenizers_pin
build_config
python_enabled
model_path
runtime_profile
ovms_exe_sha256
openvino_genai_dll_sha256
started_at
```

Also preserve build command/log, test command/exit code, test logs, live payloads, raw HTTP/SSE, and server log.

No candidate is promoted from memory, screenshots, or an artifact directory whose binary/dependency identity is unknown.

## 10. Promotion order

1. Finish C1 parser repair and record its exact HEAD.
2. Finish currently-running C2 old-base GenAI/whitespace build and tests.
3. Construct C3 only from the proven net changes of C1 + C2.
4. Require C3 GREEN before changing dependency bases.
5. Build C4 by changing only GenAI upstream base, keeping XGrammar at `9aa840b6`.
6. Require C4 GREEN.
7. Build C5 by changing only XGrammar `9aa840b6 -> f6043f4`.
8. Require C5 GREEN.
9. Re-resolve all three upstream heads.
10. Construct C6 `SUPER-UPSTREAM` from clean histories and exact fresh heads.
11. Run full C6 gate from a clean build root.
12. Only C6 is eligible to become the source of the upstream PR(s).

## 11. Final PR gate

Before opening upstream PR(s), `SUPER-UPSTREAM` requires all of:

- exact OVMS / GenAI / XGrammar SHAs recorded;
- clean build succeeds;
- GenAI whitespace tests 4/4;
- OVMS whitespace-bound test GREEN;
- compatibility gate 229/229;
- semantic gate 64/64;
- exact long named unary GREEN;
- exact long named streaming >=3/3 GREEN;
- dogfood replay GREEN;
- final diff contains only intended files;
- reviewer-facing history excludes evidence/checkpoint/revert debris.

A clean merge/rebase is not a runtime acceptance signal. Every dependency-axis promotion is evidence-driven.