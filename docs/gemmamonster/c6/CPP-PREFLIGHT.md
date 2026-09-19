# C++ compile preflight ladder (binding for C6 and forward)

Changed Gemma4 parser code must pass narrow targets BEFORE any full build.
A full 6000+ action build must never be the first compiler of a parser edit.

## Ladder (same output root/cache/toolchain/slot as the pending full build)

```text
STEP 1  //src/llm:io_processing_gemma4_tool_parser
STEP 2  //src/llm:output_parsers
STEP 3  //src:ovms_mediapipe_runtime_shared
STEP 4  full build (//src:ovms + packaging deps)
```

## Trigger rule

```text
changed Gemma4 parser              -> STEP 1 mandatory
changed OutputParser/routing       -> STEP 1 + STEP 2
changed runtime-bound API/parser   -> STEP 1/2 as applicable + STEP 3
full build allowed only after relevant preflight gates are green
```

## Reference flags (this host)

```powershell
C:\opt\bazel.exe --output_user_root=C:/o build --config=win_mp_on_py_on `
  --override_repository=boringssl=C:\opt\boringSSL-SwiftPM `
  --action_env OpenVINO_DIR=c:/o/openvino/runtime/cmake `
  --action_env OpenCV_DIR=c:/opt/opencv_4.14.0 `
  --repo_env=HERMETIC_PYTHON_VERSION=3.12 --jobs=8 <target>
```

Plus in every launching shell: `BAZEL_VS=C:\BuildTools`,
`BAZEL_SH=C:/opt/msys64/usr/bin/bash.exe`, `PYTHONHOME=C:\opt\Python312`,
`PATH=C:\opt;C:\opt\Python312;...` first. Never `bazel clean` for a preflight retry.

## Proven on pre-c6-20260919

STEP 1 PASS (3 actions) -> STEP 2 PASS (6 actions) -> STEP 3 PASS (520 actions).
Caught without full build: interleaved-method corruption, missing `using JsonWriter`,
protected-member shadowing, stale `requiresValidStructuredOutput`/`parallelToolCalls`
vs new base API (adapted, documented in handoff).
