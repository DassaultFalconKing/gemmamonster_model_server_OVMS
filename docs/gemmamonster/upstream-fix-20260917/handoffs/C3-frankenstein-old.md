# C3 FRANKENSTEIN-OLD — candidate handoff

candidate_id: C3-frankenstein-old
status: BUILD_PASS / G3 228-229 / G4 64-64 / LIVE_NOT_RUN (reboot boundary)

repo: DassaultFalconKing/gemmamonster_model_server_OVMS
branch: test/gemma4-frankenstein-oldbase-20260917
worktree: C:\git\gemmamonster-C3

remote_head_before_work: d582668e6405e5d4cffbf050e9ee7303f7b94ef0
ovms_head: 526099c5771c04b4dcc001320611d9d87b19fb2c
ovms_upstream_base: d582668e6405e5d4cffbf050e9ee7303f7b94ef0
construction: cherry-pick -x C1-net (d7e26e7d,2dc4e54c,dd3845f,d554273a5,2ec9530df;
  audit pair 2489e342/b9f65b96 EXCLUDED; HANDOFF.md not carried) + whitespace
  (c481b7f84,7e44f5355,a3a7004bd) + WORKSPACE G1 wiring. C1 test files byte-identical
  to main line (hash-verified).

ov_genai_head: G1 e00eada6 (SAME BITS as C2, dll SHA 92AB145C re-verified in C3 dist; NO rebuild)
xgrammar_sha_or_tag: X1 9aa840b6 (same bits)
openvino_pin: C:/o/openvino source-built 4977f92a

build_state: PASS (2976s first; G3/G4 increments after)
build_exit_code: 0
disk_note: C3 fetch first failed on disk-full (139MB); cleared 6.6GB Temp, deleted orphan
  output base owi5bgwi (10GB, model_server-gemma4-clean cache, nothing in program references it).
  Evidence logs: c3-build.err.log (fetch fail), c3-build2.* (PASS).

passed_gates:
  - G3 focused 228/229 (only OutputParserInitializationDependsOnParserNames environmental opt-125m; evidence c3-g3.log, test-228.log)
  - G4 semantic 6/6 64/64 PASS (evidence c3-g4.log)
failed_gates: none
not_run_gates: G2-strict (see below), prefix-turn probes (no recorded expected outputs)
G2_dogfood: STRICT-REPLAY NOT_RUN — CAUSE: archived requests (list_dir/read_file inspector flow)
  and archived expected outputs (get_weather/calculator calls, 221-token prompts) are from
  different fixture generations and cannot be compared field-wise. Behavior spot-check on C3
  GREEN: turn1 list_dir{"."}, turn2 read_file{binary-provenance.txt}, turn4 stop + factually
  correct 3-sentence summary (version 2026.5.0.b722aa440, MIXED_OLD_RUNTIME=NO). Raw: g2-turn{1,2,4}.json.
G5 unary: finish=tool_calls, search_docs{"query":"dead-letter prefix handling"}, 23 completion, prompt 5232
G6 streams 3/3: tool_calls, ws_only=0, 22-23 out — same fixture as C2, same GREEN
G7 audit: PASS — production diff vs d582668 is exactly gemma4_tool_parser.cpp (escaped strings)
  + generation_config_builder.hpp (whitespace call-site); rest is tests + WORKSPACE wiring

dist_package: C:\git\gemmamonster-C3\dist\windows\ovms.zip (149MB)
dist_verified: ovms.exe 07F3B9FE… (differs from C2 C96E7819 as expected: parser+whitespace) +
  openvino_genai.dll 92AB145C… (IDENTICAL to C2: GenAI reuse proven) +
  --version OpenVINO 2026.5.0-23084-4977f92a234 + GenAI 2026.5.0.0-3447-e00eada6f4c

runtime_state: not started (reboot required first: new OVMS binary identity)
host_state: GREEN (lane free; disk 10.7GB after build)
reboot_state: reboot REQUIRED before C3 live (matrix step 2)
cache_state: C3 needs own isolated runtime cache (not yet created)

artifact_root: C:\git\artifacts\gemma4-frankenstein-20260917\C3-frankenstein-old\
ovms_exe_sha256: 07F3B9FE0EE4BA65FDD7220F167ADBB1912AF8B6ED6588478469B25B38F01A90
openvino_genai_dll_sha256: 92AB145C8CF238E1F37CF84C2F72F93D3D978E9B7F7CFC726208D3B9FCF35AED

known_blockers: none for construction/gates; live pending reboot
next_exact_action:
  1. reboot
  2. clean C3 runtime cache, launch C3 dist :18091, G5/G6 via g5g6-gate.ps1 (same 5232-token fixture)
  3. G2 dogfood replay + G7 audit, then C3 promotion verdict

resume_point: C3 dist GREEN and fingerprinted; continue at next_exact_action step 1.
