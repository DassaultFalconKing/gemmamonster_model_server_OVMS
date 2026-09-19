# C5fixed history-normalization handoff (2026-09-19)

SOURCE_HEAD=8c6f8b00912e8baa24fb1566a843b031584f1eaa
8c6f8b00912e8baa24fb1566a843b031584f1eaa

WORKTREE=C:\git\model_server-gemma4-clean (detached HEAD, clean; mid-thought branch
restored to 5fa8b4c4 after accidental move, remote never touched; agentic worktree
left alone with its uncommitted dirt archived to C5-frankenstein-newxgrammar/)
OUTPUT_USER_ROOT=C:/opt
OUTPUT_BASE=C:/opt/owi5bgwi (owner: model_server-gemma4-clean, verified via server cmdline)
CACHE_REUSED=YES (no clean, no new root, no dep rebuilds)
BUILD=PASS (//src:ovms = 1 no-op action: handler lives in shared lib, proven by aquery;
  //src:ovms_mediapipe_runtime_shared = 4 actions: recompile + relink)
BUILD_ELAPSED=102.233s (shared lib), Critical Path 30.71s
OVMS_SHA256=56AD64A0B09F8DC199BA07D073196E70BD5B5F78E25D345923FD88C39E1D9E9E (exe UNCHANGED)
NEW_DLL_SHA256=DD3B5D28F13147E53764F1BA5274A6EEBCE31CF8142AE4AB14963564052E4229
  (ovms_mediapipe_runtime_shared.dll, fix strings verified inside, staged to C:\llm\ovms-C5fixed)
OLD_DLL_SHA256=A9E466301BA398F20654F653E673B03EE9A6607241512E67BC110A3C45A364CD (replaced)
OPENVINO_DIR=c:/opt/openvino/runtime/cmake (verbatim from last working build)

2X2 (model gemma4, second-turn history replay, reasoning_content present):
ARGS_STRING_CONTENT_STRING=200 stop
ARGS_STRING_CONTENT_OBJECT=200 stop
ARGS_OBJECT_CONTENT_STRING=200 stop
ARGS_OBJECT_CONTENT_OBJECT=200 stop

PUBLIC_ARGUMENTS_REMAIN_STRING=YES (calculator{"expression":"17 * 23"} returned as string)

MID_THOUGHT_TOOL=PASS (T1 calculator tool_calls, empty content)
TOOL_A_RESULT_TOOL_B=PASS (T2 get_weather after replayed history, no 400)
LONG_AGENT_LOOP=PASS (T3 final summary factually correct, no leaks/duplicates/fabrication)

NEGATIVE_INVALID_JSON=PASS (all 4: HTTP400 INVALID_ARGUMENT with exact parse position;
  e.g. badjson -> "parse error at line 1, column 2 ... last read: '{b'")
MEDIAPIPE_TEMPLATE_ERRORS=0 (no template/mapping crashes post-fix)

Launch note: dist python embed lacks stdlib (no Lib/encodings) — server launched with
PYTHONHOME=C:\opt\Python312 (env-only, zero file mutation); template prepared via
libovmspython exactly like the proven 9780 launch.

VERDICT=C5FIXED_HISTORY_PASS
