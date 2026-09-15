# RC1 forensic review and Candidate B parity recipe

Date: 2026-09-12

This document critically reviews `docs/gemmamonster/RC1-BUILD-PROVENANCE-FORENSIC.md` from commit `29ed19802aa095dc5277bac8f0dc8d2f785378ba` and converts only supported findings into the first RC2 causal experiment.

The forensic report is evidence-bearing input, not authority. Unsupported or internally inconsistent conclusions are downgraded here.

## 1. Critical provenance correction

The immutable RC1 package reports:

```text
OpenVINO Model Server 2026.4.0.82a8a4ec7
```

The full Git object for that prefix exists:

```text
82a8a4ec72928abad78f9180e67fbb91563e1c08
fix(gemmamonster): tolerate Bazel link before rebuild
```

The commit later recorded as the RC1 source identity is:

```text
a43f644f10e55d741d5388e43580146c5203c196
build: fix Windows build scripts for VS 2022 BuildTools at C:\BuildTools
```

`a43f644` is exactly one commit after `82a8a4ec7`. Its diff changes only:

- `.bazelrc`
- `windows_build.bat`
- `windows_install_build_dependencies.bat`

It contains no Gemma4 or other OVMS runtime-source change.

The binary mtime in the immutable operator record is `2026-09-12T03:55:57`; commit `a43f644` was created later. Therefore the strongest reconstruction is:

```text
BUILD-TIME GIT HEAD:
82a8a4ec72928abad78f9180e67fbb91563e1c08

BUILD-TIME WORKTREE PATCH:
the three build-infrastructure changes later committed as a43f644

POST-BUILD CLEAN CARRIER:
a43f644f10e55d741d5388e43580146c5203c196
```

Classification: **STRONGLY_INFERRED**, not exact shell-history proof.

This reconciles the embedded OVMS version with the later clean repository SHA without inventing a nonexistent relationship between two different Git hashes.

Do not rewrite the immutable historical RC1 branch. Record this as a provenance erratum in later worklogs and candidate reports.

## 2. What the forensic report establishes well

### High-confidence / repo-verifiable

- The RC1 dependency line is OpenVINO 2026.4 RC2:
  - OpenVINO `227c33757d1ef95d4da506d00686f923fdd2a535`
  - Tokenizers `a04accf6282d9b304214b492694b18c3979f667a`
  - GenAI `7ea2546852a382cd16bd22dea0cfad2db70ed744`
  - Windows GenAI package `2026.4.0.0rc2`
- Python is 3.12.10.
- MSVC is 14.44.35207 under `C:\BuildTools`.
- The installed Windows Bazel executable used by the official dependency/bootstrap path is 6.4.0 at `C:\opt\bazel.exe` according to the report and current upstream-style installer behavior.
- Packaging uses the official `windows_create_package.bat` model: copy the built executable, OpenVINO runtime DLLs, GenAI/tokenizers/OpenCV/curl/git2/TBB/eSpeak artifacts, embedded Python when requested, run `ovms.exe --version` and `--help`, then archive `ovms.zip`.
- `OV_USE_BINARY=1` is the intended/default dependency mode and the observed backend versions match the RC2 binary dependency line.

### Exact build-only patch later carried by `a43f644`

1. Comment the four global XNNPACK disable defines in `.bazelrc`.
2. Default `windows_build.bat` to `C:\BuildTools` when `BAZEL_VS` is absent.
3. Build OpenCV with MSVC toolset `v143` instead of `v142`.

These are build/infrastructure changes. They do not restore or alter Gemma4 parser/generator semantics.

## 3. What the forensic report does NOT prove

The report labels itself `COMPLETE`, but several claims remain reconstructed or incomplete:

- `ovms.zip` is explicitly listed as **not hashed**. Package identity is therefore not fully proven by that report.
- Only a SHA256 prefix is recorded for `ovms.exe` and selected DLLs in the report. Full hashes must be recorded for the new candidate.
- The command sequence is explicitly described as **reconstructed**, not copied from historical shell history.
- `OV_USE_BINARY=1` is strongly supported by defaults and runtime identity but is not shown as a direct historical environment capture in the report.
- The claimed external-cache path `C:/g54r2_new/...` is inconsistent with the reconstructed `windows_build.bat "" ...` command, whose first empty argument selects `C:\opt` as `--output_user_root`. Do not use the external-cache claim as build authority without the original `win_build.log`.
- The report's statement that `82a8a4ec7` is a fragment of `a43f644...` is false and is superseded by the provenance correction above.
- The report's XNNPACK performance discussion is speculative. The primary target path is VLM_CB on the Intel GPU; no evidence establishes XNNPACK flags as the source of RC1 decode speed.

For experiment design, treat XNNPACK parity as a build-variable control, not a proven performance optimization.

## 4. Why Candidate B must be split into B-PARITY and B-CLEAN

A single new build cannot simultaneously answer both of these questions cleanly:

1. Did advanced Gemma4 source semantics change behavior/performance relative to fast RC1?
2. Can the result be reproduced using an isolated, provenance-clean dependency root?

Therefore use two stages.

### B-PARITY

Purpose: maximize causal comparability with immutable RC1.

Keep constant as far as evidence permits:

- host / Intel Arc 140V / driver
- exact model bytes
- OpenVINO 2026.4 RC2 dependency set
- Bazel 6.4.0
- Python 3.12.10
- MSVC 14.44.35207
- shared `C:\opt` build/dependency root
- the exact three-file RC1 build-infrastructure patch
- official `windows_build.bat` and `windows_create_package.bat` path
- `--with_python --with_tests`
- VLM_CB / GPU / Gemma4 parsers
- benchmark and NovaClaw workload

Change intentionally:

- source semantics: existing refit source carried by the active RC2 branch (`8a54214` lineage, semantic core `9a162626`).

### B-CLEAN

Only after B-PARITY functional/performance results are known.

Purpose: prove that the same source remains correct when built from a fresh isolated dependency root with complete provenance and hashes.

B-CLEAN is not allowed to replace B-PARITY in the causal comparison because changing source and dependency-root mechanics simultaneously would confound the result.

## 5. Preflight conflict that must be resolved before B-PARITY

Current `scripts/gemmamonster/Enter-GemmamonsterEnv.ps1` is a maintainer-RC2 profile that asserts:

```text
BAZEL_VERSION = 6.1.1
GEMMAMONSTER_ROOT = C:\g54r2
OpenVINO_DIR = C:\g54r2\openvino\runtime\cmake
```

RC1 parity requires:

```text
BAZEL_VERSION = 6.4.0
GEMMAMONSTER_ROOT / build output root = C:\opt
OpenVINO_DIR = C:\opt\openvino\runtime\cmake
```

Therefore do **not** bypass or weaken the preflight. Add an explicit second profile instead.

Required interface:

```powershell
.\scripts\gemmamonster\Enter-GemmamonsterEnv.ps1 `
  -ToolchainProfile rc1-parity
```

Default behavior must remain the existing isolated maintainer-RC2 profile.

`rc1-parity` must still execute the same mandatory sequence:

```text
SANITIZE old process environment
-> assert stale selectors removed
-> INITIALIZE exact parity values
-> VERIFY actual paths and versions
-> return PASS only if everything matches
```

Never silently accept 6.1.1 or 6.4.0 depending on whichever `bazel.exe` happens to resolve first.

## 6. RC1 build-infrastructure parity patch

On the active RC2 branch, port only commit `a43f644` as a three-file build patch. The preferred local operation is:

```powershell
git cherry-pick a43f644f10e55d741d5388e43580146c5203c196
```

Before committing/pushing, verify the resulting diff contains **only** the three intended hunks and preserves any newer unrelated build-script fixes already present on the RC2 carrier.

Required verification:

```powershell
git diff HEAD^ -- .bazelrc windows_build.bat windows_install_build_dependencies.bat
git diff --check HEAD^
```

If the cherry-pick conflicts or modifies additional behavior, abort it and re-apply only the three exact hunks manually. Do not replace whole files with RC1-era blobs.

## 7. B-PARITY build recipe

This recipe is the **target recipe** after the `rc1-parity` preflight profile and three-hunk build patch are committed and verified.

Use one PowerShell process for preflight and every subsequent command.

```powershell
Set-Location <RC2_WORKTREE>

# Exact source identity first
git rev-parse HEAD
git status --short

# Mandatory fail-closed parity preflight
.\scripts\gemmamonster\Enter-GemmamonsterEnv.ps1 `
  -ToolchainProfile rc1-parity `
  -RequireRuntimeRoot

# Make binary dependency mode explicit rather than relying on a default.
$env:OV_USE_BINARY = '1'

# Historical shared-root mechanics. No expunge during the causal A/B run.
cmd /c windows_install_build_dependencies.bat opt 0 0
if ($LASTEXITCODE -ne 0) { throw "dependency bootstrap failed: $LASTEXITCODE" }

# RC1-style official build: C:\opt output root, Python, tests.
cmd /c windows_build.bat "" --with_python --with_tests
if ($LASTEXITCODE -ne 0) { throw "build failed: $LASTEXITCODE" }

# Run the built native suite before packaging.
& .\bazel-bin\src\ovms_test.exe
if ($LASTEXITCODE -ne 0) { throw "ovms_test failed: $LASTEXITCODE" }

# Official package assembly, embedded Python, lean package (no Optimum bundle).
cmd /c windows_create_package.bat opt --with_python
if ($LASTEXITCODE -ne 0) { throw "package failed: $LASTEXITCODE" }
```

Do not call any step PASS unless its command was executed and its exit/output proves it.

## 8. Mandatory provenance immediately after package creation

Record full hashes, not prefixes:

```powershell
$pkg = Join-Path (Get-Location) 'dist\windows\ovms'
$zip = Join-Path (Get-Location) 'dist\windows\ovms.zip'

Get-FileHash -Algorithm SHA256 "$pkg\ovms.exe"
Get-FileHash -Algorithm SHA256 $zip
Get-FileHash -Algorithm SHA256 "$pkg\openvino.dll"
Get-FileHash -Algorithm SHA256 "$pkg\openvino_genai.dll"
Get-FileHash -Algorithm SHA256 "$pkg\openvino_tokenizers.dll"
Get-FileHash -Algorithm SHA256 "$pkg\openvino_intel_gpu_plugin.dll"
Get-FileHash -Algorithm SHA256 "$pkg\tbb12.dll"

& "$pkg\ovms.exe" --version
```

Also record:

```text
SOURCE_HEAD
SOURCE_TREE
BRANCH
WORKTREE_STATUS
Bazel executable path/version
Python executable path/version
MSVC version
OV_USE_BINARY
OpenVINO/GenAI/Tokenizers pins
package DLL list
model identity
launch command
```

The embedded OVMS version must match the actual build-time HEAD, not a later documentation/freeze commit.

## 9. B-PARITY runtime gates

Use the exact immutable RC1 model and launch shape:

```text
pipeline_type = VLM_CB
target_device = GPU
tool_parser = gemma4
reasoning_parser = gemma4
```

Run in this order:

1. unary sanity
2. tool auto
3. streaming tool call
4. multi-turn tool-result continuation
5. complex schema
6. distinct parallel tools
7. NovaClaw recorded PASS/FAIL replay with raw request / raw OVMS SSE / harness interpretation
8. performance benchmark with TTFT and pure decode separated
9. endurance >= 150 realistic requests

`required` and named forced remain secondary gates for this candidate unless the target deployment explicitly depends on them.

## 10. Decision table

```text
B-PARITY fails build/preflight
    -> build/toolchain problem; do not edit Gemma4 semantics

B-PARITY builds but standalone auto/tool tests fail
    -> source semantic regression; use historical refit bisect

Standalone passes, NovaClaw fails, raw OVMS has no native tool frame
    -> generator/template/history path

Raw model/native marker exists, OpenAI tool_calls missing
    -> parser/streamer/finalization path

OVMS returns tool_calls correctly, NovaClaw stops
    -> harness/client path

B-PARITY functional PASS but much slower than RC1
    -> investigate build/runtime/performance deltas before semantic edits

B-PARITY functional + speed PASS
    -> proceed to B-CLEAN reproducibility build
```

## 11. B-CLEAN promotion rule

B-CLEAN may use the isolated maintainer-RC2 dependency root and the existing provenance-oriented builder, but must compile the **same semantic source** proven by B-PARITY.

Only promote RC2 when:

- B-PARITY establishes behavior/performance parity or improvement;
- B-CLEAN reproduces functional behavior on an isolated dependency root;
- full source/dependency/package hashes are recorded;
- loaded runtime modules are proven to resolve inside the packaged candidate;
- NovaClaw long-loop acceptance and endurance are green.

Until those gates run, this document is a build/experiment recipe, not a PASS record.
