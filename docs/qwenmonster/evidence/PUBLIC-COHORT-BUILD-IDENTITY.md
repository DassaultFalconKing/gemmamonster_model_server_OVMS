# Build identity audit, 2026-10-21

Status: focused build/unit triage completed; runtime acceptance NOT ESTABLISHED.
All four requested test executables compiled. Final combined test exit 1:
Qwen69/69, policy9/9 (unchanged cached in final run), generic29/29, Gemma67/70
with the same initial three failures. Full server and fresh dependency rebuild
NOT RUN. Exact tested parser commit: `f6f2a296d0574cf611cd2be6e31e3916c5858dbb`.
See BUILD-FINAL.txt and UNIT-RESULTS.json.

## Source identity

Execution base: `8cd25d63085637d112f616d62913e345a93d2233`, branch
`feature/qwenmonster-parser-invariants-20261021`. Remote matched at start.
Comparative-refit `b267d9a0dc54bd029265ba73ee4756981eda0df5` is an ancestor,
0 commits behind / 7 ahead. Original C6 `ba6ec792` is retained unchanged.

All five companion checkouts are clean at the exact public lock after selecting
a separate Minja worktree: see `PUBLIC-COHORT-SOURCE-PINNED.json`.
`PUBLIC-COHORT-SOURCE.json` retains the original Minja mismatch.

## Actual initial build inputs

- Separate OVMS checkout: `C:/git/qwenmonster-parser`.
- Bazel: 7.4.1, explicit executable from the existing build tools inventory.
- Separate output root: `C:/gb/qwm`; separate disk cache:
  `C:/gm/cache/qwm-actions`. Shared repository download cache only.
- MSVC: `14.44.35207`, `C:/BuildTools`, x64, C++20 for OVMS.
- Configuration: `win_mp_on_py_off`, bzlmod disabled, two jobs.
- Explicit `windows_openvino`, `windows_genai`, `windows_opencv`,
  `windows_opencl`, `windows_opencl2` repository overrides select the staged
  `C:/gm/c6-head-20261019/deps/bazel-repos` wrappers.
- OpenVINO/GenAI includes and import libraries resolve through those wrappers
  to `C:/gm/c6-head-20261019/deps/runtime`; no upstream binary substitution.
- Installed `generation_config.hpp` SHA256 equals the locked GenAI source.
- Existing GenAI CMake cache: Release; compiler
  `C:/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/cl.exe`;
  OpenVINO_DIR is the matching staged `runtime/cmake`.
- Existing GenAI CMake overrides select the new C6 XGrammar and Minja trees.
  `build.ninja` confirms both include paths. XGrammar is compiled into GenAI;
  it is not a separate runtime DLL.

## Minja limitation

The existing Minja checkout is `1bdb178afd6f527354e17a1db1b3a22b59189f21`.
The lock requires `83eb074e42140b0d1194d1dd61f29c31e4515ee9`.
Its only diff is `tests/gemmamonster/fixtures/gemma4-26-heretic-chat_template.jinja`.
The complete `include/` tree is identical; no production Minja header changed.
A separate checkout at the lock is `C:/gm/qwenmonster/minja`. This establishes
source equivalence of included headers, not a fresh locked-cohort rebuild.
The initial test build deliberately uses the existing installed DLLs for
compiler/parser triage; a fresh dependency build must use
`FETCHCONTENT_SOURCE_DIR_MINJA=C:/gm/qwenmonster/minja` and
`FETCHCONTENT_SOURCE_DIR_XGRAMMAR=C:/gm/c6-head-20261019/xgrammar`.
No existing accepted install or source tree is modified.

## Runtime/device boundary

Available device: Intel Arc 140V (16GB), driver `32.0.101.9150`.
No inference device has been selected for this candidate; no candidate model
has been loaded. VLM_CB/LM_CB, model/tokenizer/template identity, TTFT, throughput and GPU faults
are RUNTIME UNVERIFIED. The separate synthetic native matcher probe records
actual loaded GenAI/OpenVINO DLL paths and hashes in GRAMMAR-COMPILE.json;
tokenizers was NOT_LOADED. This does not establish inference runtime identity.
Unit tokenizer provenance is separate from live model acceptance.

## Retained machine evidence

Local raw logs and detailed SHA256 inventory:

- `C:/gm/qwenmonster/evidence/BUILD-initial.txt`
- `C:/gm/qwenmonster/evidence/BUILD-initial-trace.txt`
- `C:/gm/qwenmonster/evidence/BUILD-initial-retry.txt`
- `C:/gm/qwenmonster/evidence/BUILD-INPUT-AUDIT.json`
- `C:/gm/qwenmonster/evidence/UNIT-TOKENIZERS.json`

Initial wrapper attempts failed before Bazel (`< was unexpected at this time`).
The trace locates that failure at compiler environment setup. A later retry
with Python 3.12 prepended to PATH started Bazel; the exact cause of the shell
failure has not been discriminated. It is not a C++ compiler failure.
