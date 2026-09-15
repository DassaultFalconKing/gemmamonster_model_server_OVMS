# RC2 B-PARITY build runbook — 2026-09-12

## Purpose

Build one causal-comparison candidate from the existing 2026.4 semantic-refit source while preserving the RC1 Windows build mechanics as closely as evidence supports. This runbook builds and packages only. Runtime tuning is deliberately deferred to acceptance.

## Pinned source

Branch: `integration/gemmamonster-rc2-semantic-refit-20260912`

Historical source identities carried by this branch:
- operational carrier: `8a54214fed2a0cb01ad17159364996f8787a92fa`
- semantic `src/llm/**` identity: `9a1626260614f68a6282b6799842d5152f0dcdff`

The build agent MUST fetch the branch and record the exact current HEAD before changing anything. It MUST NOT edit `src/llm/**` or other Gemma4 protocol implementation files.

## RC1 provenance correction

The immutable RC1 binary reports OVMS source fragment `82a8a4ec7`, matching commit `82a8a4ec72928abad78f9180e67fbb91563e1c08`. The later commit `a43f644f10e55d741d5388e43580146c5203c196` contains only three build-file changes and was created after the binary timestamp. The strongest reconstruction is therefore:

`82a8a4ec... + uncommitted three-file build patch -> RC1 binary -> a43f644... clean post-build carrier`.

This is strongly inferred, not shell-history proof.

## Exact dependency/toolchain parity target

- Windows 11 host
- VS 2022 BuildTools at `C:\BuildTools`
- MSVC `14.44.35207`
- Bazel executable: `C:\opt\bazel.exe`
- active Bazel version: `6.4.0`
- repository `.bazelversion`: leave at `6.1.1`; do not rewrite it merely to match the active Windows installer-provided Bazel
- Python: `C:\opt\Python312\python.exe`, version `3.12.10`
- MSYS bash: `C:\opt\msys64\usr\bin\bash.exe`
- `OV_USE_BINARY=1`
- OpenVINO: `227c33757d1ef95d4da506d00686f923fdd2a535`
- Tokenizers: `a04accf6282d9b304214b492694b18c3979f667a`
- GenAI: `7ea2546852a382cd16bd22dea0cfad2db70ed744`
- GenAI Windows package: `openvino_genai_windows_2026.4.0.0rc2_x86_64.zip`
- OpenCV: `4.14.0`
- CURL: `8.21.0_7`

## Test-first preflight profile gate

The branch already contains `tests/windows/gemmamonster_env_preflight_profile_contract_test.ps1`, specifying a second preflight profile named `rc1-parity` while preserving `maintainer-rc2` as the default.

On the Windows build host:

1. Run the profile contract before implementation and record the result. It is expected to fail while `rc1-parity` is not implemented. Do not claim RED unless the command was actually executed and failed for the expected missing-profile reason.
2. Make the smallest change to `scripts/gemmamonster/Enter-GemmamonsterEnv.ps1` needed to support `-ToolchainProfile rc1-parity`.
3. Keep `maintainer-rc2` behavior unchanged.
4. `rc1-parity` must sanitize process-scope build/runtime selectors first, assert stale state is gone, then initialize and verify the parity environment.
5. Under `rc1-parity`, verify active Bazel 6.4.0 from `C:\opt`; do not require `.bazelversion` to equal the active Bazel version.
6. Re-run the contract test and require PASS before any dependency install/build.

## Exact three-file build parity patch

Port only the content delta of `a43f644f10e55d741d5388e43580146c5203c196`, not its divergent history:

1. `.bazelrc`: comment the four global XNNPACK disable definitions:
   - `xnn_enable_avxvnniint8=false`
   - `xnn_enable_avx512fp16=false`
   - `xnn_enable_avx512amx=false`
   - `xnn_enable_avxvnni=false`
2. `windows_build.bat`: default VS BuildTools path to `C:\BuildTools`.
3. `windows_install_build_dependencies.bat`: build OpenCV with CMake toolset `v143` rather than `v142`.

After the patch, prove the diff scope. No production Gemma4 code may be changed in the build session.

These three changes are retained for parity and build hygiene. This runbook does NOT claim they caused RC1 decode speed.

## Build sequence

Use one PowerShell process for preflight and all consequential commands.

1. Fetch and verify exact branch/HEAD/tree/status.
2. Read `agent-worklog/CURRENT.md`, this runbook, and the latest relevant Worklog sessions.
3. Run the preflight contract RED/implementation/GREEN sequence above.
4. Apply and commit the three-file parity patch, with diff-scope verification.
5. Run `Enter-GemmamonsterEnv.ps1 -ToolchainProfile rc1-parity` in the same shell. Do not proceed unless actual output is PASS and shows the expected tools/paths/pins.
6. Bootstrap official dependencies:
   `cmd.exe /d /s /c "windows_install_build_dependencies.bat opt 0 0"`
7. Re-run `rc1-parity` preflight with the runtime root required.
8. Build official Windows targets with Python and tests:
   `cmd.exe /d /s /c "windows_build.bat \"\" --with_python --with_tests"`
9. Run the produced `bazel-bin\src\ovms_test.exe`. Record exit code and complete test summary. Do not infer PASS from successful linking.
10. Package via the official script:
   `cmd.exe /d /s /c "windows_create_package.bat opt --with_python"`
11. Run packaged `setupvars.bat`, `ovms.exe --version`, and `ovms.exe --help`.
12. Hash the package and provenance-critical files with full SHA256.

If Windows quoting makes a literal command form invalid, use the semantically identical invocation accepted by `cmd.exe`, and record the exact executed command. Never silently substitute a different build profile.

## Required artifact hashes

At minimum record full SHA256 for:
- `dist\windows\ovms.zip`
- packaged `ovms.exe`
- `openvino.dll`
- `openvino_genai.dll`
- `openvino_tokenizers.dll`
- `openvino_intel_gpu_plugin.dll`
- `tbb12.dll`
- `opencv_world4140.dll`

Also record file sizes and timestamps.

## Build-session stop conditions

STOP, do not improvise, if any of these occurs:
- preflight profile contract cannot be made GREEN without altering the established `maintainer-rc2` contract;
- active Bazel is not exactly 6.4.0 for parity;
- dependency pins differ;
- build requires editing `src/llm/**` or Gemma4 protocol source;
- `ovms_test.exe` fails;
- official packaging/self-test fails;
- package loads DLLs from an uncontrolled external runtime during self-test.

Do not change GPU driver, model, model files, parser/generator source, runtime scheduler options, KV precision, prefix caching, or launch tuning in this build session.

## Handoff

Update Worklog with:
- start and final HEAD/tree;
- exact commits created;
- exact commands and exit codes;
- preflight RED and GREEN evidence;
- build/test/package verdicts;
- package path and hashes;
- `ovms.exe --version` output;
- unresolved deviations from RC1 parity.

Push the active RC2 branch only after recording the evidence. The test agent must receive one immutable package identity, not a directory that can be rebuilt underneath it.