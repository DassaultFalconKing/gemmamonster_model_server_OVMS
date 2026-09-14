# Current Windows RC2: source, binary, package and agent handoff

Snapshot date: 2026-09-14. This document describes the existing **908d6695**
product binary and its repaired package, not a newly compiled binary or a full
acceptance certificate. Runtime results below were observed on this host.

## Identity and ancestry

| Item | Value |
|---|---|
| Source commit | `908d669563f57535ab4eb747989e9ab33dfd5267` |
| Embedded version | `OpenVINO Model Server 2026.4.0.908d66956` |
| Remote | `https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS.git` |
| Source branch containing candidate at inspection | `integration/gemmamonster-rc2-clean-20260913` |
| OVMS executable SHA256 | `11d74fd958d1cd2570682fa13562c1bfcf0973dabbf79a0378a8d0cdc886a4fb` |
| Repacked ZIP SHA256 | `a2944b151f68c05140980d543c5067a0932047a7020fb9dccc13cdca65af23d4` |
| Repacked ZIP size | 140,027,849 bytes |

The source commit is a descendant of `9e34371da956b2bbb2579f20523dccac2d03ab74`
(product build separated from the test executable). Its immediate parent is
`ae4ddfd79d156604b1803031972f0b596540d789`, a test default-device correction.
Checkpoint `3e7664c263cca42545e35fe1f1cb3fecbd18408b` was used as a reference
for Windows stabilization history, not as the build source. It is not an ancestor
of this candidate: their merge-base is `9e34371da956b2bbb2579f20523dccac2d03ab74`.

Do not infer ancestry from directory names: the original source worktree is
named `gemmamonster-2026.4-unified-20260911`, but the current SHA is not a
descendant of the older semantic base `202d5e898d86af6dffd5e53fdc4e875f9de4ebed`.
Their verified merge-base is `e894bac71dc02616a68b669af7445a0f8fdb3361`.
There are 149 reachable candidate-side commits after that shared base.
See [ancestry.json](ancestry.json) and [ancestry-log.txt](ancestry-log.txt) for
machine-generated relationships and full commit IDs. Commit dates are not a
substitute for `merge-base --is-ancestor`.

Relevant source milestones include isolated RC2 dependency-root correction
`cadfcfae`, parser/grammar repairs `e8c12202`, grammar multiplicity test
`9a162626`, Windows skip lifecycle repairs `19f432ef`, graph availability
precondition `215eb1b3`, string CPU fixture correction `b264c0a0`, resource
exception-to-Status repairs for embeddings/rerank/STT (`7758aafe`, `88ac984e`,
`d7bc3496`), FP32 streaming fixture `06980ea7`, assisted decoding device alignment
`ccb145e8`, and product-only build guidance `9e34371d`.

## Runtime composition and dependency authority

| Dependency | Exact source pin / observed binary version |
|---|---|
| OpenVINO | `227c33757d1ef95d4da506d00686f923fdd2a535`; `2026.4.0-22955-227c33757d1-releases/2026/4` |
| GenAI | `7ea2546852a382cd16bd22dea0cfad2db70ed744`; `2026.4.0.0-3407-7ea2546852a` |
| Tokenizers | `a04accf6282d9b304214b492694b18c3979f667a`; `2026.4.0.0-736-a04accf6282` |
| Python | Embedded Python 3.12.10 |
| OpenCV | `opencv_world4140.dll`, source setting 4.14.0 |
| Curl | Source setting `8.21.0_7`, `libcurl-x64.dll` |
| Other runtime files | TBB, git2, eSpeak-ng DLL/data, pyovms binding, Python packages, setup scripts, licenses |

Runtime profile: `maintainer-rc2`. Package source URL:
`https://storage.openvinotoolkit.org/repositories/openvino_genai/packages/pre-release/2026.4.0.0rc2/openvino_genai_windows_2026.4.0.0rc2_x86_64.zip`.
Source authority is `versions.mk` and `scripts/gemmamonster/stable-runtime-profiles.ps1`
at the literal source SHA. Binary file identity is recorded in
[runtime-inventory.json](runtime-inventory.json) and [SHA256SUMS.txt](SHA256SUMS.txt).
The inventory covers 2949 files. Models and weights are external to the package.

The source supports lean runtime packaging and opt-in Optimum tooling. Exporter
settings in versions.mk (Optimum 2.3.0, optimum-intel 2.1.0, exporter OpenVINO
2026.3.1 / tokenizers 2026.3.1.0) are not the versions of the shipped RC2 DLLs.
Do not replace runtime DLLs with exporter-environment packages.

## Build and packaging history

The original candidate is at:
`C:\gemmamonster-artifacts\candidates\2026.4\908d6695-maintainer-rc2-rc2-product-20260913T223554Z`.
Its log confirms Python enabled, tests disabled, integrity config disabled,
MSVC under `C:\BuildTools`, dependency root `C:\g54r2`, and
`--config=win_mp_on_py_on`. The log records successful linking of `src/ovms.exe`,
2294.952 seconds elapsed, 8321 total actions (3115 internal, 5206 local).
See [evidence/original-build.log](evidence/original-build.log).

The original packaging copied the runtime, passed `--version` and `--help`,
then ended with `tar.exe: Write error`. Its original ZIP is not a valid release
artifact. The donor has no completed candidate provenance manifest; the fresh
inventory here does not retroactively certify the original builder's clean-tree
and loaded-module provenance gates. Source linkage is supported by the embedded
stamp, source checkout and logs, not by a completed original manifest.

On 2026-09-14 the donor runtime directory was copied byte-for-byte to:
`C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms`.
No DLLs, executable or Python contents were replaced. Python zipfile created a
new ZIP, verified every entry's CRC, extracted it, and compared SHA256 of every
file against the donor. This is a **repack**, not a rebuild. Test reports and
archive identity are in [package-test-results.json](package-test-results.json).
Repack and test drivers are included under [evidence/](evidence/).

A separate clean checkout attempt at `9e34371` failed before compilation while
unpacking TensorFlow because C: ran out of space. It did not produce the binary
documented here. Free-space measurements later improved; they are transient.
The Windows guide budgets up to 13 GB for compilation and 40 GB for the full
setup/build workflow.

## Fresh runtime checks and limits

Tests used the supplied setupvars.bat, with inherited PYTHONHOME/PYTHONPATH
removed and PATH restricted to Windows directories before setup. The initial
smoke and E4B tests ran from an extracted ZIP; Wondernutts ran from the equivalent
staged package folder. Requests, responses, configs and logs are included.

| Check | Result and scope |
|---|---|
| ZIP CRC / 2949-file SHA256 roundtrip | PASS |
| Packaged `--version` / `--help` | PASS, exit 0 |
| CPU dummy model / KFS v2 inference | PASS: ten ones in, ten twos out |
| Local Gemma4 E4B CPU VLM_CB | FAIL: no SDPA operation for SDPAToPagedAttention transformation |
| Local Gemma4 E4B CPU explicit VLM | PASS: one 2+2 request returned 4, finish_reason stop |
| Wondernutts Gemma4 26B A4B GPU VLM_CB | PASS: model AVAILABLE, one 2+2 request returned 4, HTTP 200, finish_reason stop |
| Streaming, repeated/parallel tool calls, continuation, restart/session persistence, image inputs, long runs | NOT RUN on this repacked binary |
| Full regression suite / overall RC2 acceptance | NOT ESTABLISHED |

Wondernutts model path:
`C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov`.
Its supplied graph selected GPU, VLM_CB, max_num_seqs 256, prefix caching true,
cache_size 0. A copied graph replaced models_path `./` with an absolute path;
the model files were not changed. API model ID was **gemma4**. Tests used REST
18086 / gRPC 18087 and stopped only their owned process trees afterward.
The prior E4B CB log was overwritten by a later runner launch; its error is
transcribed here from the session output, not presented as preserved raw evidence.
Early config quoting and /v1-vs-/v2 runner mistakes were corrected; final reports
are smoke results, not full-suite results.

## Commands for another coding agent

Freeze source and binary independently. Do not substitute `9e34371`, current
remote HEAD, an older RC2 binary or an ovms_test binary for this candidate.
The documentation branch adds documents to the source SHA and is not its binary
build stamp. Use official scripts instead of assembling DLL/PATH state by hand.

Build in a fresh checkout, using PowerShell 7 (`pwsh`):

```powershell
git checkout --detach 908d669563f57535ab4eb747989e9ab33dfd5267
Import-Module Microsoft.PowerShell.Utility
.\scripts\gemmamonster\audit-stable-refit.ps1 -RepoRoot $PWD
.\scripts\gemmamonster\build-stable-candidate.ps1 `
  -RepoRoot $PWD -RuntimeProfile maintainer-rc2 -ShortRoot g54r2 `
  -WithoutTests -Label rc2-product
```

Use `-SkipDependencies` only after checking the existing dependency root and
exact RC2 profile. The builder transiently rewrites WORKSPACE's OpenVINO/GenAI
pins to the short root and restores tracked files. On this host:
BAZEL_VS `C:\BuildTools`, BAZEL_VC `C:\BuildTools\VC`, MSVC 14.44.35207,
BAZEL_SH `C:\opt\msys64\usr\bin\bash.exe`. Bazel must use hermetic Python 3.12.
The installer names Bazel 6.4.0 while .bazelversion says 6.1.1: record the actually
invoked executable/version when rebuilding; do not infer it from either file.
`ovms_test.exe` is test-only and not required for the product package.

Launch this package from cmd.exe:

```bat
cd /d C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\ovms
call setupvars.bat
ovms.exe --version
ovms.exe --config_path C:\git\artifacts\ovms-908d6695-rc2-repacked-20260914\wondernutts-test\gemma4-config.json --rest_port 18086 --port 18087
```

Check ports first; bind to loopback for a local-only test if needed. REST base:
`http://127.0.0.1:18086`; chat route `/v3/chat/completions`, model `gemma4`.
The machine-specific config paths must be adapted on another host. The model's
full tensor hashes and exporter provenance were not independently frozen here.

For a tool-calling campaign, capture every request/response, finish_reason,
call count/name/arguments, grounded schema values and tool-result continuation.
Keep readiness, transport, payload semantics and overall acceptance separate.
After GPU execution failure or executor quarantine, reload/recreate before any
retry; /v3/models HTTP 200 alone is not generation readiness. Reject RC2/2026.4
version drift. Do not import historical test PASS as evidence for this binary.

Historical stabilization details are source records in
`agent-worklog/sessions/2026-09-13-windows-autonomous-stabilization.md`; their
test binary hashes and partial suite outcomes belong to those earlier runs.
