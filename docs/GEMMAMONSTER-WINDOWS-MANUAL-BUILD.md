# Gemmamonster Windows manual build runbook

This document is the canonical manual-build procedure for the Gemmamonster OVMS fork on Windows.

It is intentionally fail-closed. The build environment is part of the build provenance. Do not start dependency installation, compilation, packaging, tests, or runtime acceptance until the environment pre-flight reports `ENV_PREFLIGHT = PASS`.

## 1. Build profiles: do not mix them

Two different profiles exist and must remain distinct.

### Frozen known-good reference

Use this only to reproduce the accepted reference candidate exactly:

- Gemmamonster source: `9a1626260614f68a6282b6799842d5152f0dcdff`
- OpenVINO: `227c33757d1ef95d4da506d00686f923fdd2a535`
- OpenVINO GenAI: `7ea2546852a382cd16bd22dea0cfad2db70ed744`
- OpenVINO Tokenizers: `a04accf6282d9b304214b492694b18c3979f667a`
- XGrammar: `v0.1.31` as pinned by GenAI `7ea254...`
- runtime profile: `maintainer-rc2`
- pipeline: `VLM_CB`
- known-good binary SHA256: `E7D8024F4F385B8DA5051C343DA3ACE0FBEF65813767EFB74C7FCCFFEE80CB0A`

Do not replace XGrammar 0.1.31 with 0.2.6 when reproducing the frozen reference.

### Current acceptance profile

Use this for the active local acceptance worktree:

- local worktree: `C:\git\gemmamonster-2026.4-unified-20260911`
- exact source SHA: always capture with `git rev-parse HEAD`; the last reported local prefix was `82a8a4ec7...`
- OpenVINO: `227c33757d1ef95d4da506d00686f923fdd2a535`
- OpenVINO GenAI base: `7ea2546852a382cd16bd22dea0cfad2db70ed744`
- OpenVINO Tokenizers: `a04accf6282d9b304214b492694b18c3979f667a`
- XGrammar acceptance pin: `v0.2.6`, commit `bc09a30ec10ba30a6c1ab0c79eaeba3ca518d11f`
- expected whitespace cap: `max_whitespace_cnt=2`
- runtime profile: `maintainer-rc2`
- pipeline: `VLM_CB`

The current unified branch is local-only until it is pushed. Do not describe a local-only SHA as remotely reproducible.

## 2. Open one PowerShell session and keep it

Use a Developer PowerShell for Visual Studio 2022 or an equivalent shell with the required MSVC installation available.

All commands below must run in the same PowerShell process. Do not initialize the environment in a temporary child `powershell.exe -File ...` process and then build in another shell.

```powershell
$repo = 'C:\git\gemmamonster-2026.4-unified-20260911'
Set-Location $repo
```

## 3. Mandatory environment sanitation and initialization

Run the canonical pre-flight before doing anything else:

```powershell
.\scripts\gemmamonster\Enter-GemmamonsterEnv.ps1
```

The pre-flight deliberately performs these phases in order:

1. `SANITIZE`: remove stale process-scope OpenVINO, GenAI, Gemmamonster, Bazel, Python, Conda/venv, CMake and runtime selectors.
2. clean stale OpenVINO, packaged OVMS, candidate, old `C:\g54*`, Python and MSYS entries from inherited `PATH` while preserving unrelated system/tool paths.
3. assert that stale selectors are actually gone.
4. `INITIALIZE`: set the exact `maintainer-rc2` toolchain and dependency pins.
5. `VERIFY`: prove active Bazel/Python versions, source identity, `versions.mk` authority and canonical paths.

Proceed only when the script reports:

```text
ENV_PREFLIGHT = PASS
```

For build/test/package work after the dependency root already exists, use the stronger gate:

```powershell
.\scripts\gemmamonster\Enter-GemmamonsterEnv.ps1 -RequireRuntimeRoot
```

Do not use `-AllowDirty` for a candidate that may later be promoted.

Canonical pre-flight authority:

| Component | Required value |
|---|---|
| Bazel | `6.4.0` |
| Python | `3.12.10` |
| VS Build Tools | `C:\BuildTools` |
| MSVC toolset | `14.44.35207` |
| MSYS bash | `C:\opt\msys64\usr\bin\bash.exe` |
| short/runtime root | `C:\g54r2` |
| OpenVINO | `227c33757d1ef95d4da506d00686f923fdd2a535` |
| GenAI | `7ea2546852a382cd16bd22dea0cfad2db70ed744` |
| Tokenizers | `a04accf6282d9b304214b492694b18c3979f667a` |
| binary runtime line | `2026.4.0.0rc2` |
| OpenCV | `4.14.0` |

## 4. Capture source identity before the build

```powershell
$HEAD   = (git rev-parse HEAD).Trim()
$TREE   = (git rev-parse "$HEAD^{tree}").Trim()
$BRANCH = (git branch --show-current).Trim()
$STATUS = @(git status --porcelain)

"BRANCH=$BRANCH"
"HEAD=$HEAD"
"TREE=$TREE"

if ($STATUS.Count -ne 0) {
    throw "Dirty worktree before build:`n$($STATUS -join "`n")"
}
```

Also confirm the actual tool executables, not merely version strings:

```powershell
Get-Command git
Get-Command bazel
Get-Command cmake
Get-Command python

bazel --version
C:\opt\Python312\python.exe --version
```

Expected Bazel is `6.4.0`; expected Python is `3.12.10`.

Current acceptance uses Bazel 6.4.0 because 6.1.1 misidentifies the modern VC
layout when `C:\BuildTools\VC` also contains `vcpkg`. Use the unmodified official
6.4.0 executable; do not move vcpkg or patch Bazel's embedded tools. Historical
reference build records remain historical; dependency pins are unchanged.

## 5. Bootstrap the canonical RC2 dependency root

Back up tracked files that the upstream Windows dependency installer may rewrite:

```powershell
$workspaceBackup = [IO.File]::ReadAllBytes((Join-Path $repo 'WORKSPACE'))
```

Install dependencies into the canonical short root:

```powershell
cmd.exe /d /c "windows_install_build_dependencies.bat g54r2 1 0"
if ($LASTEXITCODE -ne 0) { throw "dependency install failed: $LASTEXITCODE" }
```

Verify the root:

```powershell
Get-Item C:\g54r2\openvino -Force | Format-List FullName,LinkType,Target
```

The target must resolve to the `2026.4.0.0rc2` runtime line.

## 6. Verify WORKSPACE local repositories

For a manual short-root build, both Windows OpenVINO repositories must resolve to:

```text
C:\g54r2\openvino\runtime
```

Check:

```powershell
Select-String .\WORKSPACE -Pattern 'windows_openvino|windows_genai|openvino\\runtime'
```

The relevant `windows_openvino` and `windows_genai` paths must not point to the old global `C:\opt\openvino\runtime` tree during the build.

A mixed tree is a provenance failure even if compilation succeeds.

## 7. Current acceptance only: bleeding-edge XGrammar

Frozen known-good `9a162626` keeps stock GenAI and XGrammar `v0.1.31`. Current repair uses GenAI base `7ea2546852a382cd16bd22dea0cfad2db70ed744` plus the tracked schema API patch, and XGrammar `9aa840b6d16abf094f3e8e2ac9c10465b77656c9` with recursively pinned submodules.

Use the existing checkout at `C:\g54r2\openvino_genai_src`. The script creates or verifies XGrammar under `openvino_genai_build\_deps\xgrammar-src`, checks both SHA values, synchronizes recursive dependencies, applies the versioned patches, builds the C++ runtime and installs matching headers and DLLs into `C:\g54r2\openvino`.

```powershell
.\scripts\gemmamonster\build-whitespace-genai.ps1
```

Python bindings are disabled for this C++ product. TVM-FFI is therefore outside the active dependency graph. The XGrammar patch corrects header installation when used as a CMake subproject.

The actual JSONSchema node carries `max_whitespace_cnt=2` only for Gemma4 tool arguments. Default JSONSchema callers remain unbounded. Verify serialization and C++ matcher acceptance before promoting a candidate.

## 8. Stop stale Bazel state

```powershell
bazel --output_user_root=C:/g54r2 shutdown
```

If Bazel reports that `repository_rule.remotable` requires `--experimental_repo_remote_exec`, do not edit production code. First prove that the active Bazel is 6.4.0 and that this repository's `.bazelrc` is being read. For `sync` or `query`, pass `--experimental_repo_remote_exec` explicitly; the existing build flag does not apply to those commands.

## 9. Set the OVMS version metadata

```powershell
C:\opt\Python312\python.exe `
    .\windows_set_ovms_version.py `
    "--config=win_mp_on_py_on" `
    C:\g54r2

if ($LASTEXITCODE -ne 0) { throw "windows_set_ovms_version.py failed: $LASTEXITCODE" }
```

## 10. Build OVMS manually

```powershell
bazel --output_user_root=C:/g54r2 build `
    --config=win_mp_on_py_on `
    --action_env=OpenVINO_DIR=C:/g54r2/openvino/runtime/cmake `
    --jobs=$env:NUMBER_OF_PROCESSORS `
    --verbose_failures `
    //src:ovms `
    //third_party:espeak_ng `
    //third_party:espeak_ng_data

if ($LASTEXITCODE -ne 0) { throw "OVMS build failed: $LASTEXITCODE" }
```

Expected primary outputs include:

```text
bazel-bin\src\ovms.exe
bazel-out\x64_windows-opt\bin\src\openvino_genai.dll
bazel-out\x64_windows-opt\bin\src\openvino_tokenizers.dll
```

A successful compilation is not acceptance. It proves only `BUILD = PASS`.

## 11. Record pre-package provenance

At minimum hash the runtime components that can materially alter GPU/GenAI behavior:

```powershell
$prePackage = @(
    'C:\g54r2\openvino\runtime\bin\intel64\Release\openvino.dll',
    'C:\g54r2\openvino\runtime\bin\intel64\Release\openvino_intel_gpu_plugin.dll',
    'C:\g54r2\openvino\runtime\3rdparty\tbb\bin\tbb12.dll',
    (Join-Path $repo 'bazel-out\x64_windows-opt\bin\src\openvino_genai.dll'),
    (Join-Path $repo 'bazel-out\x64_windows-opt\bin\src\openvino_tokenizers.dll')
)

$prePackage | ForEach-Object { Get-FileHash $_ -Algorithm SHA256 }
```

Treat a GPU plugin loaded from an unexpected global path as a provenance failure, not as a harmless Windows detail.

## 12. Create a lean isolated package

```powershell
$short = $HEAD.Substring(0,8)
$pkg = "C:\gemmamonster-artifacts\manual\$short-maintainer-rc2"
New-Item -ItemType Directory -Force -Path $pkg | Out-Null

cmd.exe /d /c "windows_create_package.bat g54r2 --with_python `"$pkg`""
if ($LASTEXITCODE -ne 0) { throw "package creation failed: $LASTEXITCODE" }
```

Do not add the Optimum bundle to a runtime-only acceptance candidate unless that tooling is explicitly required.

## 13. Verify packaged hashes

```powershell
$ovms = Join-Path $pkg 'ovms'

$names = @(
    'ovms.exe',
    'openvino.dll',
    'openvino_genai.dll',
    'openvino_tokenizers.dll',
    'openvino_intel_gpu_plugin.dll',
    'tbb12.dll'
)

$names | ForEach-Object {
    Get-FileHash (Join-Path $ovms $_) -Algorithm SHA256
}
```

Prove at least the GPU plugin matches the canonical source tree:

```powershell
$sourceGpu = (Get-FileHash 'C:\g54r2\openvino\runtime\bin\intel64\Release\openvino_intel_gpu_plugin.dll' -Algorithm SHA256).Hash
$packageGpu = (Get-FileHash (Join-Path $ovms 'openvino_intel_gpu_plugin.dll') -Algorithm SHA256).Hash

if ($sourceGpu -ne $packageGpu) {
    throw 'Packaged GPU plugin does not match the canonical runtime root'
}
```

Generate a recursive package manifest for later A/B work:

```powershell
Get-ChildItem $ovms -Recurse -File |
    Sort-Object FullName |
    ForEach-Object {
        $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $rel = [IO.Path]::GetRelativePath($pkg, $_.FullName).Replace('\','/')
        "$h  $rel"
    } | Set-Content (Join-Path $pkg 'SHA256SUMS.txt') -Encoding ASCII
```

## 14. Restore tracked build inputs

If the dependency installer rewrote `WORKSPACE`, restore the original bytes after the build/package operation:

```powershell
[IO.File]::WriteAllBytes((Join-Path $repo 'WORKSPACE'), $workspaceBackup)
```

Then prove the worktree is back to its intended state:

```powershell
$statusAfter = @(git status --porcelain | Where-Object { $_ -notmatch '^\?\? bazel-[^/]*/$' })
if ($statusAfter.Count -ne 0) {
    throw "Unexpected source mutations after build:`n$($statusAfter -join "`n")"
}
```

## 15. Runtime acceptance must use the package, not `bazel-bin`

The candidate runtime must be launched from the isolated package directory. Do not use `bazel-bin\src\ovms.exe` as acceptance evidence.

The preferred launcher is:

```powershell
.\scripts\gemmamonster\launch-stable-candidate.ps1 `
    -CandidateRoot $pkg `
    -ModelPath 'C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov' `
    -ModelName 'gemma4-26-heretic' `
    -RestPort 8000
```

If launching manually, prepend only the candidate runtime and candidate Python to `PATH` for that process:

```powershell
$oldPath = $env:PATH
$env:OVMS_DIR = $ovms
$env:PYTHONHOME = Join-Path $ovms 'python'
$env:PATH = "$ovms;$env:PYTHONHOME;$env:PYTHONHOME\Scripts;$oldPath"

Set-Location $ovms
.\ovms.exe --version
```

Then launch with Gemma4 parsers:

```powershell
.\ovms.exe `
    --rest_port 8000 `
    --model_path 'C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov' `
    --model_name gemma4-26-heretic `
    --task text_generation `
    --tool_parser gemma4 `
    --reasoning_parser gemma4
```

The canonical accepted architecture remains `VLM_CB`. Do not switch the acceptance baseline to `LM_CB` merely to avoid a GPU failure.

## 16. Prove loaded runtime modules

After startup, identify the listening process and inspect the modules actually loaded by Windows:

```powershell
$pid = (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
$p = Get-Process -Id $pid

$p.Modules |
    Where-Object { $_.ModuleName -match 'openvino|genai|tokenizer|tbb' } |
    Select-Object ModuleName,FileName
```

The package-sensitive modules must resolve from the candidate package, especially:

```text
openvino.dll
openvino_genai.dll
openvino_tokenizers.dll
openvino_intel_gpu_plugin.dll
tbb12.dll
```

DriverStore shims may be system-owned and must be classified separately. Do not use a broad `openvino* must all be inside package` rule for system driver shims.

## 17. Acceptance order

Only after package and loaded-module provenance are proven:

1. `VLM_CB` startup.
2. tiny generation without tools.
3. forced single tool call with valid JSON arguments.
4. tool-result continuation.
5. streaming probe.
6. parallel/repeated tool-call matrix.
7. longer multi-turn agent loop.

After a `GPU_CONTEXT_FATAL` / `CL_OUT_OF_RESOURCES` quarantine, do not continue issuing inference requests to that executor. Restart/reload and preserve the fault evidence first.

## 18. Required build record

Every candidate worth comparing later must record at least:

```text
SOURCE_HEAD:
SOURCE_TREE:
BRANCH:
WORKTREE:

ENV_PREFLIGHT:
BAZEL:
PYTHON:
MSVC:

OPENVINO_SHA:
GENAI_SHA:
TOKENIZERS_SHA:
XGRAMMAR_SHA:
XGRAMMAR_VERSION:
MAX_WHITESPACE_CNT:

RUNTIME_ROOT:
PIPELINE:
RUNTIME_PROFILE:

OVMS_SHA256:
OPENVINO_SHA256:
GPU_PLUGIN_SHA256:
GENAI_DLL_SHA256:
TOKENIZERS_DLL_SHA256:
TBB_SHA256:

BUILD:
PACKAGE:
PACKAGE_PROVENANCE:
LOADED_MODULE_PROVENANCE:
TINY_GENERATION:
TOOL_CALL:
CONTINUATION:
STREAMING:
OVERALL:
```

Do not promote a candidate based on `ovms.exe --version`, `/v3/models = 200`, or a successful Bazel build alone. Those are useful facts, not acceptance.
