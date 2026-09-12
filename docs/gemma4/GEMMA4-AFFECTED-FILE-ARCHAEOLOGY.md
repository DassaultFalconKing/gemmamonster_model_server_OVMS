# GEMMA4 AFFECTED FILE ARCHAEOLOGY

**Date:** 2026-09-12
**Session:** READ-ONLY Git archaeology
**Base worktree:** `integration/gemmamonster-2026.4-unified-20260911` @ `a43f644f10e55d741d5388e43580146c5203c196`
**Scope:** Gemma4 tool-calling / reasoning / generation-config / output-parsing / streaming surface

---

## 1. BERICHТ DISCOVERY

```
BERICHT_CANDIDATES:
  1. C:\git\gemmamonster-2026.4-build\docs\gemmamonster\Bericht-Provenance-Descendance-diff.md
  2. C:\git\gemmamonster-2026.4-dc668c\docs\gemmamonster\Bericht-Provenance-Descendance-diff.md
  3. C:\git\model_server-gemma4-2026.5-exact\docs\gemmamonster\Bericht-Provenance-Descendance-diff.md
  4. C:\git\model_server-gemma4-fast\docs\gemmamonster\Bericht-Provenance-Descendance-diff.md

SELECTED_BERICHT: All 4 — identical blob 19a1d2e5a6dba12d1252ab4a54961c50326223e7 (24245 bytes)
WHY: Single canonical Bericht propagated across 4 worktrees. Content covers provenance, affected file inventory, and semantic diff vs upstream.
TRACKED_OR_UNTRACKED: TRACKED in all 4 worktrees
REPORT_SHA/BLOB_IF_TRACKED: blob 19a1d2e5a6dba12d1252ab4a54961c50326223e7
```

---

## 2. AFFECTED FILE INVENTORY

### 2.1 Core Runtime Source (from Bericht §3)

| File | Role | Current existence | Rename lineage |
|------|------|-------------------|----------------|
| `src/BUILD` | Build targets | TRACKED | none |
| `src/llm/apis/openai_api_handler.hpp` | API handler header | TRACKED | none |
| `src/llm/apis/openai_completions.hpp` | Completions API | TRACKED | none |
| `src/llm/apis/openai_request.hpp` | Request parsing | TRACKED | none |
| `src/llm/apis/openai_responses.cpp` | Responses API impl | TRACKED | none |
| `src/llm/apis/openai_responses.hpp` | Responses API header | TRACKED | none |
| `src/llm/io_processing/base_generation_config_builder.hpp` | Base builder | TRACKED | none |
| `src/llm/io_processing/chat_template/analyzer.cpp` | Template analyzer | TRACKED | none |
| `src/llm/io_processing/chat_template/caps.hpp` | Template capabilities | TRACKED | none |
| `src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp` | **Gemma4 reasoning parser** | TRACKED | none |
| `src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp` | Reasoning parser header | TRACKED | none |
| `src/llm/io_processing/gemma4/gemma4_tool_parser.cpp` | **Gemma4 tool parser** | TRACKED | none |
| `src/llm/io_processing/gemma4/gemma4_tool_parser.hpp` | Tool parser header | TRACKED | none |
| `src/llm/io_processing/generation_config_builder.hpp` | **Generation config builder** | TRACKED | none |
| `src/llm/io_processing/input_processors/chat_template_adapter.cpp` | Template adapter | TRACKED | none |
| `src/llm/io_processing/input_processors/chat_template_adapter.hpp` | Adapter header | TRACKED | none |
| `src/llm/io_processing/input_processors/chat_template_processor.cpp` | Template processor | TRACKED | none |
| `src/llm/io_processing/input_processors/chat_template_processor.hpp` | Processor header | TRACKED | none |
| `src/llm/io_processing/output_parser.cpp` | **Output parser** | TRACKED | none |
| `src/llm/io_processing/output_parsing_config.hpp` | Parsing config | TRACKED | none |
| `src/llm/ovms_text_streamer.cpp` | **Text streamer** | TRACKED | none |
| `src/llm/servable.cpp` | **Servable** | TRACKED | none |
| `src/llm/servable.hpp` | Servable header | TRACKED | none |

### 2.2 Build / Package

| File | Role | Current existence |
|------|------|-------------------|
| `src/version.hpp` | Version info | TRACKED |
| `windows_build.bat` | Windows build | TRACKED |
| `windows_create_package.bat` | Package creation | TRACKED |
| `windows_install_build_dependencies.bat` | Deps install | TRACKED |

### 2.3 Test / Contract Files (from Bericht §4)

| File | Role | Current existence |
|------|------|-------------------|
| `src/test/llm/gemma4_fast/BUILD` | Test build | TRACKED |
| `src/test/llm/gemma4_fast/gemma4_parser_contract_test.cpp` | Parser contract | TRACKED |
| `src/test/llm/gemma4_fast/gemma4_reasoning_semantic_refit_test.cpp` | Reasoning test | TRACKED |
| `src/test/llm/gemma4_fast/gemma4_recovery_contract_test.cpp` | Recovery test | TRACKED |
| `src/test/llm/gemma4_overlay/BUILD` | Overlay build | TRACKED |
| `src/test/llm/gemma4_overlay/gemma4_chat_template_overlay_contract_test.cpp` | Overlay test | TRACKED |
| `src/test/llm/generation_config/BUILD` | Gen config build | TRACKED |
| `src/test/llm/generation_config/gemma4_generation_contract_test.cpp` | Gen contract | TRACKED |
| `src/test/llm/generation_config/gemma4_prompt_state_generation_contract_test.cpp` | Prompt state test | TRACKED |
| `src/test/llm/generation_config/openai_parallel_tool_calls_contract_test.cpp` | Parallel tools test | TRACKED |
| `tests/windows/gemma4_standalone_package_test.ps1` | Package test | TRACKED |

### 2.4 Historical Involvement-Only (Bericht §6)

| File | Role | Status |
|------|------|--------|
| `src/llm/apis/openai_api_handler.cpp` | API handler impl | TRACKED (different blob from KG) |
| `windows_build_fast.ps1` | Historical build helper | Not in current tree |

---

## 3. KEY REFERENCE POINTS

| Label | Ref | SHA | Date | Role |
|-------|-----|-----|------|------|
| **KG2026.4** | `freeze/gemmamonster-2026.4-known-good` | `c48366fee1f10cdf6b5fe3c181522ed0c58fc9fd` | 2026-09-09 | Frozen 2026.4 known-good |
| **E_MINJA** | `freeze/gemmamonster-working-e-minja-20260909` | `4907343476e5c57d7cff5a1209c8317358a847ea` | 2026-09-09 | Working E/MINJA runtime |
| **Accept2026.5** | `integration/ovms-2026.5-forward-port` | `2d17e36f39412f18df558c49c6bc4661b833f675` | 2026-09-09 | 2026.5 forward-port acceptance |
| **Hardening** | `integration/gemma4-protocol-hardening-2026.5` | `5d995cfafdb2ec90578678aa15714dedebc843b8` | 2026-09-09 | Protocol hardening branch |
| **HEAD** | `integration/gemmamonster-2026.4-unified-20260911` | `a43f644f10e55d741d5388e43580146c5203c196` | 2026-09-12 | Current unified 2026.4 |
| **RC2lean** | `release/gemmamonster-2026.4-rc2-lean` | `9a1626260614f68a6282b6799842d5152f0dcdff` | 2026-09-09 | RC2 lean release |
| **Main** | `origin/main` | `8a54214fe` | 2026-09-11 | Latest main |
| **Upstream** | `upstream/main` | `fadb3314a` | latest | OVMS upstream |

---

## 4. PER-FILE VERDICT

### 4.1 gemma4_tool_parser.cpp

```
FILE: src/llm/io_processing/gemma4/gemma4_tool_parser.cpp
ROLE: Core Gemma4 native tool call parser — argument state machine, boundary ownership,
      bare-call recovery, numeric validation, parallel calls

LATEST (by date):
  commit: afb35de765e4a40759f2a159e4c7498e45476a54
  blob: a43443192058067f38029f16aba68c79b867e0b5
  author_date: 2026-09-11T16:32:14+02:00
  refs: upstream/releases/2026/4
  why_latest: Latest commit touching this file across all refs

NEWEST_CARRIER of latest blob:
  commit: afb35de765e4a40759f2a159e4c7498e45476a54
  refs: upstream/releases/2026/4
  same_blob_as_latest: YES

MOST_ADVANCED:
  commit: 8a54214fe (origin/main)
  blob: d7d766e032b47df0bb155140e6d26a8740af5217
  refs: origin/main, release/gemmamonster-2026.4-rc2-lean
  technical_reasons: |
    867 lines, 37812 bytes — largest version.
    Contains ALL features from hardening branch PLUS:
    - isValidJsonNumber() validation (lossless numeric lexemes)
    - Additional array parsing fixes (#4532, #4540)
    - Array-of-objects recursive parsing
    - Forward-ported from 2026.5 hardening + upstream array fixes
    Hardening branch (3c63559, 638 lines) LACKS numeric validation and array fixes.

LATEST_IS_MOST_ADVANCED: NO

IF_NO:
  what newer version lost/regressed: |
    upstream/releases/2026/4 (a434431, 363 lines) is a STRIPPED upstream-only version
    missing all Gemma4 native parser hardening. It's "newer" by date but contains
    only the upstream base without any of our custom work.
  what older/different version has: |
    origin/main (d7d766e, 867 lines) has the most complete implementation including
    native framing, recursive objects, recursive arrays, lossless numbers, registry-aware
    validation, bounded recovery, parallel calls, and array parsing fixes.

REQUIRED_COMPANIONS:
  - gemma4_tool_parser.hpp (same commit/branch)
  - output_parser.cpp (ownsToolCallBoundaries routing)
  - output_parsing_config.hpp (parser policy metadata)
  - generation_config_builder.hpp (grammar construction)
  - src/test/llm/gemma4_fast/gemma4_parser_contract_test.cpp

TEST_EVIDENCE:
  - gemma4_parser_contract_test.cpp: 276 lines on main (vs 153 on HEAD)
  - gemma4_recovery_contract_test.cpp: 143 lines on main (EMPTY on HEAD)

CONFIDENCE: HIGH — blob comparison is definitive, technical criteria well-matched
```

### 4.2 gemma4_reasoning_parser.cpp

```
FILE: src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp
ROLE: Gemma4 reasoning/thought-channel parser

LATEST:
  commit: 8a54214fe (origin/main)
  blob: c7e848098ca384fd960f4d7ae0f771fc5f0e14d3
  refs: origin/main, release/gemmamonster-2026.4-rc2-lean, integration/gemma4-protocol-hardening-2026.5
  why_latest: Same blob across main, rc2-lean, and hardening — all carried forward

NEWEST_CARRIER: Same as LATEST (shared blob across 3+ refs)

MOST_ADVANCED:
  commit: 8a54214fe (origin/main)
  blob: c7e848098ca384fd960f4d7ae0f771fc5f0e14d3
  refs: origin/main, rc2-lean, hardening
  technical_reasons: |
    53 lines — most complete version.
    Dedicated Gemma4 semantics with canonical <|channel|>thought<|channel|> handling.
    Earlier versions (KG2026.4: 32 lines, Accept2026.5: 30 lines) are simpler stubs.
    HEAD (39 lines) is an intermediate version missing some hardening.

LATEST_IS_MOST_ADVANCED: YES

REQUIRED_COMPANIONS:
  - gemma4_reasoning_parser.hpp (same blob)
  - gemma4_tool_parser.cpp (reasoning→tool handoff)
  - ovms_text_streamer.cpp (phase synchronization)
  - output_parser.cpp (parser ownership transitions)

CONFIDENCE: HIGH
```

### 4.3 generation_config_builder.hpp

```
FILE: src/llm/io_processing/generation_config_builder.hpp
ROLE: Builds OpenVINO GenAI generation config with Gemma4-aware grammar

LATEST:
  commit: 8a54214fe (origin/main)
  blob: 32fd42590c3904be9cb98493792a6cd542a3e652
  refs: origin/main, rc2-lean

MOST_ADVANCED:
  commit: 8a54214fe
  blob: 32fd42590c3904be9cb98493792a6cd542a3e652
  technical_reasons: |
    222 lines — most complete.
    Contains: none/auto/required/named tool_choice, lazy/TriggeredTags auto,
    hard-choice mandatory path, parallel_tool_calls, stop_after_first,
    prompt-state aware grammar, exact JSON Schema delegation.
    Hardening (c27b3f9, 219 lines) is 3 lines smaller — missing clarifying comments
    about fde0762 superseded workaround and unique alternatives.
    HEAD (eb14cec, 142 lines) is severely stripped.

LATEST_IS_MOST_ADVANCED: YES

REQUIRED_COMPANIONS:
  - base_generation_config_builder.hpp
  - chat_template_processor.cpp (rendered prompt reconciliation)
  - chat_template_adapter.cpp (Gemma-specific state)
  - gemma4_tool_parser.cpp (tool tag definitions)

CONFIDENCE: HIGH
```

### 4.4 output_parser.cpp

```
FILE: src/llm/io_processing/output_parser.cpp
ROLE: Orchestrates reasoning/tool parser transitions, streaming state

LATEST:
  commit: 8a54214fe (origin/main)
  blob: 4a8c0a299b348d117d75f957a72c03c3e21101c5
  refs: origin/main, rc2-lean

MOST_ADVANCED:
  commit: 8a54214fe
  blob: 4a8c0a299b348d117d75f957a72c03c3e21101c5
  technical_reasons: |
    491 lines — most complete.
    Contains bareRecovery handling, pendingDelta management,
    resetStreamingState with pendingDelta.reset(), and all
    ownsToolCallBoundaries routing. Hardening (26d346f, 473 lines)
    LACKS bareRecovery and pendingDelta features.

LATEST_IS_MOST_ADVANCED: YES

REQUIRED_COMPANIONS:
  - output_parsing_config.hpp
  - gemma4_tool_parser.cpp (ownsToolCallBoundaries)
  - gemma4_reasoning_parser.cpp (phase transitions)
  - ovms_text_streamer.cpp (token streaming)

CONFIDENCE: HIGH
```

### 4.5 ovms_text_streamer.cpp

```
FILE: src/llm/ovms_text_streamer.cpp
ROLE: Token streaming with special-token phase synchronization

LATEST:
  commit: 8a54214fe (origin/main)
  blob: 7378bc05c6bb39d33c25f399111939a8d3766682
  refs: origin/main, rc2-lean, hardening

MOST_ADVANCED:
  commit: 8a54214fe
  blob: 7378bc05c6bb39d33c25f399111939a8d3766682
  technical_reasons: |
    285 lines — most complete.
    Contains thought-close → tool-open phase sync, skip_special_tokens
    correctness, token-ID vs decoded-string ordering fixes.
    HEAD/KG2026.4/Accept2026.5 all share older blob (5764c6e, 277 lines)
    which LACKS the phase handoff fix (commit 45ea4a8).

LATEST_IS_MOST_ADVANCED: YES

REQUIRED_COMPANIONS:
  - gemma4_reasoning_parser.cpp (phase transitions)
  - gemma4_tool_parser.cpp (tool open detection)
  - output_parser.cpp (processing phase coordination)

CONFIDENCE: HIGH
```

### 4.6 servable.cpp

```
FILE: src/llm/servable.cpp
ROLE: Main servable entry point, session management

LATEST:
  commit: 8a54214fe (origin/main)
  blob: b15d409a7f98a26e58827c3331d74dfbe1b0e571
  refs: origin/main, rc2-lean, KG2026.4, Accept2026.5, Hardening

MOST_ADVANCED:
  Same blob across all branches EXCEPT current HEAD (8e0f35a, 500 lines).
  HEAD has a REDUCED version (500 lines vs 944 lines everywhere else).
  technical_reasons: |
    944 lines — full session continuity, runtime state management.
    HEAD's 500-line version is a stripped 2026.4 subset.

LATEST_IS_MOST_ADVANCED: YES (same blob as KG2026.4 — stable)

IF_NO: N/A — HEAD is the regression, not an advancement

REQUIRED_COMPANIONS:
  - servable.hpp
  - openai_api_handler.hpp
  - output_parser.cpp
  - All parser files

CONFIDENCE: HIGH
```

### 4.7 Test Files

```
=== gemma4_parser_contract_test.cpp ===
  LATEST: origin/main, blob 47a2edad, 276 lines
  HEAD: blob c6774352, 153 lines — REDUCED, DIFFERENT blob
  Main is MORE COMPLETE.

=== gemma4_reasoning_semantic_refit_test.cpp ===
  LATEST: origin/main, blob 8a8dd7bc, 152 lines
  HEAD: 1 line — ESSENTIALLY EMPTY
  Main has full test; HEAD has placeholder.

=== gemma4_recovery_contract_test.cpp ===
  LATEST: origin/main, blob 5df92bb, 143 lines
  HEAD: 1 line — ESSENTIALLY EMPTY
  Main has full test; HEAD has placeholder.

=== gemma4_generation_contract_test.cpp ===
  LATEST: origin/main, blob cb84eb6, 400 lines
  HEAD: blob 9ddb55b, 143 lines — REDUCED
  Main is 2.8x MORE COMPLETE.

=== gemma4_prompt_state_generation_contract_test.cpp ===
  LATEST: origin/main, blob b754ebf, 67 lines
  HEAD: 1 line — ESSENTIALLY EMPTY

=== openai_parallel_tool_calls_contract_test.cpp ===
  LATEST: origin/main, blob 89a8fea, 160 lines
  HEAD: 1 line — ESSENTIALLY EMPTY

VERDICT: Current HEAD has STUB test files. origin/main has full test coverage.
```

---

## 5. GLOBAL MATRIX

| File | KG2026.4 | Accept2026.5 | Hardening | HEAD (current) | RC2lean | Main | Latest winner | Most advanced winner | Same? |
|------|----------|-------------|-----------|----------------|---------|------|---------------|---------------------|-------|
| gemma4_tool_parser.cpp | 3c63559 (638) | 3c63559 (638) | 3c63559 (638) | 2c2448e (564) | d7d766e (867) | d7d766e (867) | upstream rel (a434431, 363) | **Main (d7d766e, 867)** | NO |
| gemma4_reasoning_parser.cpp | a274e6d (32) | 85fed76 (30) | c7e8480 (53) | 303423f (39) | c7e8480 (53) | c7e8480 (53) | Main (c7e8480, 53) | **Main (c7e8480, 53)** | YES |
| generation_config_builder.hpp | ea9adb1 (213) | ea9adb1 (213) | c27b3f9 (219) | eb14cec (142) | 32fd425 (222) | 32fd425 (222) | Main (32fd425, 222) | **Main (32fd425, 222)** | YES |
| output_parser.cpp | f08426e (421) | f08426e (421) | 26d346f (473) | abe1ea9 (413) | 4a8c0a2 (491) | 4a8c0a2 (491) | Main (4a8c0a2, 491) | **Main (4a8c0a2, 491)** | YES |
| ovms_text_streamer.cpp | 5764c6e (277) | 5764c6e (277) | 7378bc0 (285) | 5764c6e (277) | 7378bc0 (285) | 7378bc0 (285) | Main (7378bc0, 285) | **Main (7378bc0, 285)** | YES |
| servable.cpp | b15d409 (944) | b15d409 (944) | b15d409 (944) | 8e0f35a (500) | b15d409 (944) | b15d409 (944) | Main (b15d409, 944) | **Main (b15d409, 944)** | YES |
| openai_api_handler.hpp | a600135 (215) | 2539277 (244) | 2539277 (244) | 0f3c0b3 (205) | 2539277 (244) | 2539277 (244) | Main (2539277, 244) | **Main (2539277, 244)** | YES |
| parser_contract_test | f5c3d78 (258) | f5c3d78 (258) | f5c3d78 (258) | c677435 (153) | 47a2edad (276) | 47a2edad (276) | Main (47a2edad, 276) | **Main** | YES |
| reasoning_refit_test | MISSING | MISSING | 8a8dd7bc (152) | 1 line | 8a8dd7bc (152) | 8a8dd7bc (152) | Main (8a8dd7bc, 152) | **Main** | YES |
| recovery_contract_test | MISSING | MISSING | d33d00cf (125) | 1 line | 5df92bb (143) | 5df92bb (143) | Main (5df92bb, 143) | **Main** | YES |
| generation_contract_test | 95bfa71 (288) | 95bfa71 (288) | 95bfa71 (288) | 9ddb55b (143) | cb84eb6 (400) | cb84eb6 (400) | Main (cb84eb6, 400) | **Main** | YES |
| prompt_state_test | MISSING | MISSING | b754ebf (67) | 1 line | b754ebf (67) | b754ebf (67) | Main (b754ebf, 67) | **Main** | YES |
| parallel_tools_test | 9691cbc (108) | 9691cbc (108) | 9691cbc (108) | 1 line | 89a8fea (160) | 89a8fea (160) | Main (89a8fea, 160) | **Main** | YES |

---

## 6. COMPATIBILITY CLUSTERS

### CLUSTER-A: origin/main complete code surface
```
files:
  src/llm/io_processing/gemma4/gemma4_tool_parser.cpp     (blob d7d766e)
  src/llm/io_processing/gemma4/gemma4_tool_parser.hpp     (same branch)
  src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp (blob c7e8480)
  src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp (same branch)
  src/llm/io_processing/generation_config_builder.hpp     (blob 32fd425)
  src/llm/io_processing/output_parser.cpp                 (blob 4a8c0a2)
  src/llm/io_processing/output_parsing_config.hpp         (same branch)
  src/llm/ovms_text_streamer.cpp                          (blob 7378bc0)
  src/llm/servable.cpp                                    (blob b15d409)
  src/llm/servable.hpp                                    (same branch)
  src/llm/apis/openai_api_handler.hpp                     (blob 2539277)
exact commits/blobs: All on origin/main @ 8a54214fe
shared contract: Gemma4 native tool framing + reasoning boundaries + rendered-prompt grammar
can transplant atomically: YES — all files coexist on same branch head
```

### CLUSTER-B: origin/main test surface
```
files:
  src/test/llm/gemma4_fast/gemma4_parser_contract_test.cpp          (blob 47a2edad)
  src/test/llm/gemma4_fast/gemma4_reasoning_semantic_refit_test.cpp (blob 8a8dd7bc)
  src/test/llm/gemma4_fast/gemma4_recovery_contract_test.cpp        (blob 5df92bb)
  src/test/llm/generation_config/gemma4_generation_contract_test.cpp (blob cb84eb6)
  src/test/llm/generation_config/gemma4_prompt_state_generation_contract_test.cpp (blob b754ebf)
  src/test/llm/generation_config/openai_parallel_tool_calls_contract_test.cpp (blob 89a8fea)
exact commits/blobs: All on origin/main @ 8a54214fe
shared contract: Test contracts for Cluster-A code
can transplant atomically: YES — but requires Cluster-A code to compile
```

### CLUSTER-C: hardening-branch code (SUBSET of main)
```
files:
  src/llm/io_processing/gemma4/gemma4_tool_parser.cpp     (blob 3c63559, 638 lines)
  src/llm/io_processing/gemma4/gemma4_reasoning_parser.cpp (blob c7e8480, 53 lines)
  src/llm/io_processing/generation_config_builder.hpp     (blob c27b3f9, 219 lines)
  src/llm/io_processing/output_parser.cpp                 (blob 26d346f, 473 lines)
exact commits/blobs: integration/gemma4-protocol-hardening-2026.5 @ 5d995cf
shared contract: Earlier hardening without array fixes and bareRecovery
can transplant atomically: YES — but INFERIOR to Cluster-A
```

### CLUSTER-D: current HEAD (MINIMAL SUBSET)
```
files:
  All same paths but DIFFERENT, REDUCED blobs
exact commits/blobs: integration/gemmamonster-2026.4-unified-20260911 @ a43f644
shared contract: Minimal 2026.4 subset, many test stubs
can transplant atomically: YES — but this is the WEAKEST version
```

---

## 7. FINAL SYNTHESIS

```
FILES_WHERE_LATEST_IS_BEST:
  gemma4_reasoning_parser.cpp (main = latest = most advanced)
  generation_config_builder.hpp (main = latest = most advanced)
  output_parser.cpp (main = latest = most advanced)
  ovms_text_streamer.cpp (main = latest = most advanced)
  servable.cpp (main = latest = most advanced, HEAD is regressed)
  All test files (main = latest = most advanced, HEAD has stubs)

FILES_WHERE_OLDER_IS_MORE_ADVANCED:
  gemma4_tool_parser.cpp — origin/main (867 lines) is MORE ADVANCED than
    upstream/releases/2026/4 (363 lines) which is "newer" by date but
    contains only upstream base without Gemma4 hardening.
    LATEST ≠ MOST_ADVANCED here.

FILES_WITH_MULTIPLE_COMPETING_ADVANCED_VERSIONS:
  gemma4_tool_parser.cpp:
    - origin/main (d7d766e, 867 lines) — full hardening + array fixes + numeric validation
    - latest-refit (9e6071d, 827 lines) — gate12 repair, close but lacks array parsing fixes
    - content-owns-boundaries (c9e6f98, 780 lines) — specialized routing variant
    Winner: origin/main

FILES_REQUIRING_ATOMIC_CLUSTER:
  ALL runtime files (Cluster-A) must move together.
  Tests (Cluster-B) require Cluster-A to compile.
  DO NOT move gemma4_tool_parser.cpp alone without output_parser.cpp and
  generation_config_builder.hpp.

FILES_WITH_UNRESOLVED_LINEAGE:
  src/llm/apis/openai_api_handler.cpp — historical involvement file.
  HEAD blob differs from KG2026.4. Needs separate analysis for which
  version has the fail-closed tool_choice validation.

BEST_COHERENT_SOURCE_SNAPSHOT:
  origin/main @ 8a54214fe (15 commits ahead of rc2-lean, all docs/build/launcher)

BEST_COHERENT_DONOR_CLUSTER:
  Cluster-A + Cluster-B from origin/main @ 8a54214fe
  All 6 core runtime files + 6 test files, same branch head

DO_NOT_COMBINE:
  current HEAD (a43f644) runtime files WITH main test files — version mismatch
  upstream/releases/2026/4 tool_parser (a434431) WITH any Gemma4 hardening — incompatible
  hardening branch (5d995cf) tool_parser WITH main output_parser — missing bareRecovery

OVERALL_CONFIDENCE: HIGH
  Blob SHA comparison is definitive.
  origin/main is the clear MOST_ADVANCED for all key files.
  current HEAD is a MINIMAL 2026.4 subset — significantly weaker.
  LATEST_IS_MOST_ADVANCED = YES for all files except gemma4_tool_parser.cpp
  where upstream "newer" is actually stripped.
```

---

## 8. CRITICAL OBSERVATION

**current HEAD (`a43f644f1`) is NOT the most advanced version of any file.**

It is a deliberately minimal 2026.4 integration branch with:
- Reduced tool parser (564 lines vs 867 on main)
- Stripped reasoning parser (39 lines vs 53)
- Stripped generation config (142 lines vs 222)
- Missing streaming fixes (277 lines vs 285)
- Stub test files (1 line vs 127-400 lines)

This is consistent with the branch being an early 2026.4 integration point, NOT the latest development state.

**origin/main (`8a54214fe`) is the single best source for all Gemma4 affected files.**
