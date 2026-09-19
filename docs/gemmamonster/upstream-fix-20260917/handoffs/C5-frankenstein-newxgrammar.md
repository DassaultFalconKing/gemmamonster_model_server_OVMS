# C5 FRANKENSTEIN-NEWXGRAMMAR — candidate handoff

candidate_id: C5-frankenstein-newxgrammar
status: BUILD_PASS / G3 228-229 / G4 64-64 / LIVE_NOT_RUN (reboot boundary)

repo: DassaultFalconKing/gemmamonster_model_server_OVMS
branch: test/gemma4-frankenstein-newxgrammar-20260917
worktree: C:\git\gemmamonster-C5

ovms_head: a671ddf9f10f31a8afda849b44400291c35148ea (C4 source + WORKSPACE G2-X2 wiring)
ovms_upstream_base: d582668e6405e5d4cffbf050e9ee7303f7b94ef0

ov_genai_head: 15e8f897c19154294c6d00a518a2bb28d99905df (fork branch c5-newxgrammar-20260917, pushed;
  G2 source + XGrammar pin f6043f4 only)
ov_genai_upstream_base: 3abf349be2c53f911d5de6edc2744e20c1780ba5 (unchanged from C4)

xgrammar_sha_or_tag: X2 f6043f4daafd0d018f77c3ec07bcfcd70b7e0532 (verified rev-parse in _deps after targeted invalidation)
xgrammar_upstream_base: v0.1.31 tag (upstream moved 4 commits past X1; HEAD 38b97c0 held for C6 per decision)

openvino_pin: C:/o/openvino source-built 4977f92a

build_state: PASS (403s, 5433 disk-cache hits, 5 local — relink-only prediction CONFIRMED)
build_exit_code: 0
ovms_exe_note: D1F2B8AB differs from C4 1D384B88 despite identical public headers/import-lib hash;
  attributed to link embedding (timestamps/paths). Behavior gates decide; recorded, not hidden.

passed_gates:
  - GenAI StructuredOutputJSONSchema 4/4 PASS on X2 binaries (evidence C5/x2-4of4.log)
  - G3 focused 228/229 (only environmental opt-125m; evidence C5/c5-g3.log, test-228.log)
  - G4 semantic 6/6 64/64 PASS (evidence C5/c5-g4.log)
failed_gates: none
not_run_gates: none remaining (G2 closed by pack, see below)

G2 canonical pack: GREEN 2026-09-18 (dogfood session 03 on live C5 + verified verdict
`C6-g2pack/VERIFIED-G2-VERDICT.md` — agent's results.csv rejected as misparsed).
Turns 1-3 tool_calls, turn4 stop+correct summary, g6 search_docs @5232, prefix 1-3
stop+coherent @~16K. Response-level evidence (not transition contracts, see
TRANSITION-VERDICT-20260919.md for the 7 named gaps).
  Evidence C:\git\artifacts\gemma4-frankenstein-20260917\C6-g2pack\:
  turns 1-4 unary tool_calls (perfect inspector chain), g6 SSE search_docs 5232,
  prefix 1-3 SSE text stop (~16K prompts, coherent). All sane, no spam/length/hallucination.
C5_VERDICT: PROMOTED and PINNED as the working candidate. C5 supersedes C4.

live_G5_G6: GREEN 2026-09-18 on C5 PID 12504 (same 5232-token fixture:
  unary tool_calls 23tok; streams 3/3 tool_calls ws_only=0). Fourth candidate identical.
live_like_suite: byte-for-byte same verdicts as C4 in all 6 cases (parallel, required,
  nocall-text, emptyparams stop-empty pre-existing, unicode 2-call, unknown fail-closed
  INVALID_ARGUMENT with identical message). Zero XGrammar-move regressions. Evidence C5/livelike/.
G7-refresh: PASS (C4->C5 delta is WORKSPACE wiring only).
C5_VERDICT: PROMOTED (with G2-strict open, same documented cause). C5 supersedes C4.

dist_package: C:\git\gemmamonster-C5\dist\windows\ovms.zip (149MB)
dist_verified: ovms.exe D1F2B8AB… + openvino_genai.dll 8C7F1F0C… (X2) +
  --version OpenVINO 2026.5.0-23084-4977f92a234 + GenAI 2026.5.0.0-3469-15e8f897c19-c5-newxgrammar-20260917

slot: C:\git\gemma4-runtimes\G2-X2\ (immutable, manifest inside)

runtime_state: not started (reboot required: new XGrammar identity)
host_state: GREEN (lane free; disk 32GB)
reboot_state: reboot REQUIRED before C5 live (matrix)
cache_state: C5 needs own isolated runtime cache (not yet created)

artifact_root: C:\git\artifacts\gemma4-frankenstein-20260917\C5-frankenstein-newxgrammar\
ovms_exe_sha256: D1F2B8ABA2C8DD76C9ED1C6E0BDFFA680A26CD20F7802B12D6F501EC2AD0AB6C
openvino_genai_dll_sha256: 8C7F1F0CD4061EDD10CF30258EFEACDFA594A0A3A172947F9BBAEF29818C4115

known_blockers: none for construction/gates; live pending reboot
next_exact_action:
  1. reboot
  2. clean C5 runtime cache, launch C5 dist :18091, G5/G6 same fixture + live-like suite
  3. G2/G7 refresh, C5 promotion verdict, then C6-PREFLIGHT refresh decision

resume_point: C5 dist GREEN and fingerprinted; continue at next_exact_action step 1.
