# C2 WHITESPACE-OLDBASE — candidate handoff

candidate_id: C2-whitespace-oldbase
status: BUILD_PASS / TEST_NOT_RUN / LIVE_NOT_RUN

repo: DassaultFalconKing/gemmamonster_model_server_OVMS
branch: test/gemma4-c2-whitespace-oldbase-20260917
worktree: C:\git\gemmamonster-C2

remote_head_before_work: 3ed4ad8dc (origin/fix/gemma4-whitespace-regression-1609 tip)
local_head_before_work: 3ed4ad8dc

ovms_head: eebda599f (O0 d582668 + whitespace stack a3a7004bd + WORKSPACE G1 wiring)
ovms_upstream_base: d582668e6405e5d4cffbf050e9ee7303f7b94ef0

ov_genai_head: e00eada6f4cce794ac3b3f6053cdb0c9dc569e68 (G1, verified on disk)
ov_genai_upstream_base: fe818c0467feb17b87c5adfb3f7e28dd70b76e99

xgrammar_sha_or_tag: 9aa840b6d16abf094f3e8e2ac9c10465b77656c9 (X1, from G1 CMakeLists)
xgrammar_upstream_base: v0.1.31 (stock GenAI pin superseded by G1)

openvino_pin: C:/o/openvino source-built 4977f92a (OpenVINO_DIR)
openvino_tokenizers_pin: b40486a0 (night build; tokenizers DLL untouched by G1 overlay)

build_state: PASS
build_command: bazel --output_user_root=C:/o build --config=win_mp_on_py_on --action_env OpenVINO_DIR=C:/o/openvino/runtime/cmake --jobs=4 //src:ovms //src:ovms_mediapipe_runtime_shared //third_party:espeak_ng //third_party:espeak_ng_data //src/python:libpython_calculators //src/python:libovmspython
build_exit_code: 0
build_attempts:
  - attempt1 FAIL 1840s: openai_api_handler.cpp cl Exit 2, no diagnostic (parallel-OOM suspected at jobs=8; evidence c2-build.err.log)
  - attempt2 FAIL 59s: same TU at jobs=4 -> not parallelism; root-caused as C2440 (old dev20260911 genai headers via windows_openvino /I shadowing). Evidence c2-build-retry.*, c2-build.log
  - attempt3 (g1 wiring) FAIL 234s: WORKSPACE windows_genai repoint alone insufficient; windows_openvino /I root listed first and shadowed. Evidence c2-build-g1.*
  - attempt4 (g1b, eebda599f) PASS: both windows_genai and windows_openvino -> C:\opt\openvino_g1\runtime slot. 157 actions. Evidence c2-build-g1b.*

wiring_history (one-axis purity kept):
  - 801752d89 llm_engine.bzl remote/commit -> fork (WRONG LEVER: OVMS headers come from windows_genai local repo, not llm_engine) — superseded
  - 933beb7f2 WORKSPACE windows_genai -> G1 slot; llm_engine.bzl reverted
  - eebda599f WORKSPACE windows_openvino -> G1 slot (header shadowing fix)

test_state: NOT_RUN (no C2 test gate required by matrix; G2/G3 proven on C1 line)
passed_gates: build
failed_gates: none outstanding
not_run_gates: G1 (GenAI 4/4 on G1 binaries), G2, G5, G6, G7

runtime_state: not started (no dist package yet)
host_state: GREEN (post-reboot; Available 16.3GB at C2 start; single lane held throughout)
reboot_state: rebooted 2026-09-17 before C2 construction
cache_state: C:/o shared output bases (uqyspfra=C1, 2ax5nbrk=C2); no cross-candidate runtime cache use (no runtime started)

artifact_root: C:\git\artifacts\gemma4-frankenstein-20260917\C2-whitespace-oldbase\
ovms_exe_sha256: C96E7819AFDCFE04CC3A2D423E17C94BBC2E5EAFCC28C8FE7FF4EE333C22740A
openvino_genai_dll_sha256: 92AB145C8CF238E1F37CF84C2F72F93D3D978E9B7F7CFC726208D3B9FCF35AED
openvino_genai_lib_sha256: 5AA71A0C49857C96E634783643DBAFD4EFC1D856E40F8701822C601260F0A77F
genai_slot: C:\opt\openvino_g1\runtime (headers+dll+lib overlaid on dev20260911 base; canonical move to C:\git\gemma4-runtimes\G1-X1\ pending C3 consumption)

changed_files (vs O2 tip 3ed4ad8dc): WORKSPACE (2 hunks, wiring only)
source_diff_summary: no production/test source change; build-wiring only

known_blockers:
  - dist package for live run not built yet (windows_create_package flow) — next heavy op
  - G1 GenAI C++ tests 4/4 NOT_RUN on G1 binaries (required before C2 live promotion per gate table)

next_exact_action:
  1. run GenAI StructuredOutputJSONSchema 4/4 against G1 build tree (G1 gate)
  2. package C2 dist (windows_create_package equivalent) into C2 artifact root
  3. reboot + clean candidate runtime caches, launch C2 on :18091, run G5/G6 exact long-context gates

resume_point: C2 binary GREEN and fingerprinted; continue at next_exact_action step 1.
