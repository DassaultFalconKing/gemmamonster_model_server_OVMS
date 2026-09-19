# C5fixed recipe (pinned working state, 2026-09-19)

Pinned copy: `C:\llm\ovms-C5fixed-pinned-20260919\` (robocopy mirror of the live
dist minus logs/live-tests; hashes verified equal).
Live dist (mutable): `C:\llm\ovms-C5fixed\`.

## Binary identity

```text
56AD64A0B09F8DC1  ovms.exe (stock link; handler lives in shared lib)
DD3B5D28F13147E5  ovms_mediapipe_runtime_shared.dll (rebuilt @8c6f8b00, fix inside)
8C7F1F0CD4061EDD  openvino_genai.dll (= G2-X2 slot bits, XGrammar f6043f4)
```

Source: detached HEAD `8c6f8b00912e8baa24fb1566a843b031584f1eaa`
(`openai_api_handler.cpp` +57 only vs `5fa8b4c4e`) in
`C:\git\model_server-gemma4-clean` (mid-thought branch restored to `5fa8b4c4e`).

## Build (cached incremental, no clean)

Worktree with cache: `C:\git\model_server-gemma4-clean`, root `C:/opt`,
base `C:/opt/owi5bgwi`. Proof that `//src:ovms` alone is NOT enough:
`deps(//src:ovms)` lacks the handler — build `//src:ovms_mediapipe_runtime_shared`.

```powershell
$env:BAZEL_VS="C:\BuildTools"; $env:BAZEL_SH="C:/opt/msys64/usr/bin/bash.exe"
$env:PYTHONHOME="C:\opt\Python312"
$env:PATH="C:\opt;C:\opt\Python312;C:\opt\Python312\Scripts;C:\opt\msys64\usr\bin;"+$env:PATH
C:\opt\bazel.exe --output_user_root=C:/opt build --config=win_mp_on_py_on `
  --override_repository=boringssl=C:\opt\boringSSL-SwiftPM `
  --action_env OpenVINO_DIR=c:/opt/openvino/runtime/cmake `
  --action_env OpenCV_DIR=c:/opt/opencv_4.14.0 `
  --repo_env=HERMETIC_PYTHON_VERSION=3.12 --jobs=8 `
  //src:ovms_mediapipe_runtime_shared
```

Result 102s / 4 actions (recompile + relink). Stage the new DLL over the dist.

## Launch (proven profile)

```powershell
$env:PYTHONHOME="C:\opt\Python312"   # dist embed lacks stdlib; env-only, no file change
$env:PYTHONPATH="C:\opt\owi5bgwi\execroot\ovms\bazel-out\x64_windows-opt\bin\src\python\binding"
C:\llm\ovms-C5fixed\ovms.exe --rest_port 18091 --rest_bind_address 127.0.0.1 `
  --port 9000 --grpc_bind_address 127.0.0.1 --config_path C:\live_accept\config.json
```

Model `gemma4` = `C:/llm/models/runtime/gemma4-26-heretic-google-current`
(see `C:\live_accept\config.json`).

## Live gates on this binary (all GREEN)

2x2 second-turn replay 4/4 (pre-fix: 2x400) | public arguments-as-STRING |
agent loop T1/T2/T3 | negatives 4/4 HTTP400 with parse position |
MEDIAPIPE_TEMPLATE_ERRORS=0.
