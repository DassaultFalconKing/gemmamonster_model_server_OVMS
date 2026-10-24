# CIB2-P0-RECEIPT — file-identity rehash receipt

- Date: 2026-10-24
- Scope: read-only. No compile, no model load, no Bazel, no OVMS start, no git operations, no edits under `C:\git`.
- Python: `C:\gm\minicpm-v47-eval\venv-pinned\Scripts\python.exe` (CPython 3.12.13), `hashlib.sha256`, streamed in 1 MiB chunks.
- Writes: this file only.
- Status of this receipt: **FILE-IDENTITY ONLY — NOT a PASS.**

## 1. SHA-256 rehash (6 paths)

| # | File | Computed SHA-256 | Expected SHA-256 | Result |
|---|------|------------------|------------------|--------|
| 1 | openvino.dll | `829c4642e287522f8a8e748a726d4ad3117a701e22ab46adc82771f98e5d2f7e` | `829c4642e287522f8a8e748a726d4ad3117a701e22ab46adc82771f98e5d2f7e` | MATCH |
| 2 | openvino_genai.dll | `5a2904f2564e4ce002db5ef5fe003a782e6f296f6377cd66df1b2db41d4c5e8d` | `5a2904f2564e4ce002db5ef5fe003a782e6f296f6377cd66df1b2db41d4c5e8d` | MATCH |
| 3 | openvino_intel_gpu_plugin.dll | `b90b57aecb9d8bbb7b0a1e945e45a088e94ea7baf61eaf5dd7d8fe5e06c9e55d` | `b90b57aecb9d8bbb7b0a1e945e45a088e94ea7baf61eaf5dd7d8fe5e06c9e55d` | MATCH |
| 4 | openvino_tokenizers.dll | `e96e02744f4cd9567e54065430aa609e97c48951299a21f30abc00fba6078d3c` | `e96e02744f4cd9567e54065430aa609e97c48951299a21f30abc00fba6078d3c` | MATCH |
| 5 | ovms.exe | `f472d619097b3d64c3899a4628f219381941e99bb388d9c9c8a1d84956475397` | `f472d619097b3d64c3899a4628f219381941e99bb388d9c9c8a1d84956475397` | MATCH |
| 6 | ovms_test.exe | `3ac79a92468f0de2582ae99133018c1d58eaa3f0584ef9184dabc13f93857df4` | `3ac79a92468f0de2582ae99133018c1d58eaa3f0584ef9184dabc13f93857df4` | MATCH |

Result counts: 6 MATCH, 0 MISMATCH, 0 NOT_FOUND. No hash was inferred, defaulted, or reconstructed; every value above was read from disk during this run.

### Paths and file metadata

| File | Full path | Size (bytes) | Last write (UTC) |
|------|-----------|--------------|------------------|
| openvino.dll | `C:\gm\qwenmonster\semantic-refit-2026.4-sdk\extracted\openvino_genai_windows_2026.4.0.0rc1_x86_64\runtime\bin\intel64\Release\openvino.dll` | 16,465,168 | 2026-08-27T19:50:32Z |
| openvino_genai.dll | `C:\gm\qwenmonster\semantic-refit-2026.4-sdk\extracted\openvino_genai_windows_2026.4.0.0rc1_x86_64\runtime\bin\intel64\Release\openvino_genai.dll` | 7,425,808 | 2026-08-27T19:50:28Z |
| openvino_intel_gpu_plugin.dll | `C:\gm\qwenmonster\semantic-refit-2026.4-sdk\extracted\openvino_genai_windows_2026.4.0.0rc1_x86_64\runtime\bin\intel64\Release\openvino_intel_gpu_plugin.dll` | 34,629,896 | 2026-08-27T19:50:32Z |
| openvino_tokenizers.dll | `C:\gm\qwenmonster\semantic-refit-2026.4-sdk\extracted\openvino_genai_windows_2026.4.0.0rc1_x86_64\runtime\bin\intel64\Release\openvino_tokenizers.dll` | 3,483,912 | 2026-08-27T19:50:32Z |
| ovms.exe | `C:\r20264\i6egknn4\execroot\ovms\bazel-out\x64_windows-opt\bin\src\ovms.exe` | 22,596,608 | 2026-10-23T11:30:59Z |
| ovms_test.exe | `C:\r20264\i6egknn4\execroot\ovms\bazel-out\x64_windows-opt\bin\src\ovms_test.exe` | 40,555,520 | 2026-10-23T11:30:13Z |

## 2. stable-status.txt lookup (bounded)

- Search root: `C:\gm\qwenmonster\semantic-refit-2026.4-src` (root exists: True)
- Method: filename-scoped enumeration, `-Filter 'stable-status.txt' -File -Recurse`, errors silent.
- Coverage of that root: 1,946 files / 351 directories enumerated.
- Result: **NOT_FOUND** — zero files named `stable-status.txt` exist anywhere under the specified root.
- No other directory or drive was searched. No model `.bin`/`.xml` file was opened.

Because the file does not exist, there is nothing to quote:

- `BUILD_EMBED_LABEL` (from stable-status.txt): **NOT AVAILABLE — file NOT_FOUND**, therefore neither empty nor non-empty can be asserted.
- Corroborating observation (same bounded tree): the literal token `BUILD_EMBED_LABEL` does not appear in any scanned text file under the src root, so no substitute definition was located either.

Consequence: the embedded build-label question is **unresolved**, not answered. Absence of the file is recorded as absence, not as an empty label.

## 3. source_build_association

**UNVERIFIED.**

- No file was found that contains both an expected SHA-256 from the list in §1 and the git SHA `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`.
- Bounded search performed: the literal `eb76a74f7aa39573d452d95443e189b1f5f4d9e8` was searched across the same `semantic-refit-2026.4-src` tree (1,946 files, files < 5 MB) → **zero hits**.
- A matching hash proves only that a file's bytes are the bytes expected. It does not connect those bytes to a specific commit, build invocation, or source tree.
- Therefore: the six MATCH results above **do not** associate the binaries with `eb76a74f…`, and this receipt makes no such claim.

## 4. Explicit non-claims / gate state

| Field | Value | Basis |
|-------|-------|-------|
| loaded_modules | **NOT_RUN** | No process was started; no DLL was loaded or enumerated in-process. |
| runtime_acceptance | **NO** | No inference, no device plugin load, no OVMS start, no smoke test performed. |
| source_build_association | **UNVERIFIED** | No file co-locates an expected SHA-256 with git SHA `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`. |
| Overall verdict | **NOT A PASS** | This is a file-identity receipt. 6/6 hash matches repeat byte identity only. |

Explicitly not claimed: compile success, Bazel target validity, OVMS functionality, GPU/co-access behavior, model load, tokenizer behavior, absence of tampering elsewhere, or reproducibility of the build.

Read-only confirmation: no compile, no model load, no Bazel invocation, no OVMS start, no `git` command, and no write under `C:\git` occurred during this task.
