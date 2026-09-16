# Live Acceptance Tester Handoff — Gemma4 freeze candidate — 2026-09-16

## Mission

Run **Arc 140V live acceptance** against the Windows **build candidate** produced from the semantic-freeze branch.

This is **not** a semantic C++ implementation session and **not** a rebuild session unless the package is missing or provenance fails.

Do **not** declare:

- `KNOWN GOOD`
- `ACCEPTED`
- `production ready`
- `Gemma live PASS`

until the live matrix below is executed and recorded with immutable SHA + package hashes.

---

## Source authority (immutable)

| Field | Value |
|---|---|
| Repo | `DassaultFalconKing/gemmamonster_model_server_OVMS` |
| Branch | `staging/gemma4-upstream-refit-clean-20260915` |
| Build / branch tip | `b722aa440b5555041f24e6d6f7aea8bda100bdf7` |
| Behavioral freeze SHA | `66c66140113c4a6be8ce0b11b5aa23ccc774ac22` |
| Source tree | `2ac648ea1b352701336f35daab916e276980a6b1` |

`b722aa440` = behavioral freeze + freeze/docs commits only.

Prove before testing:

```powershell
git fetch --all --prune
git switch staging/gemma4-upstream-refit-clean-20260915
git rev-parse HEAD
# expect: b722aa440b5555041f24e6d6f7aea8bda100bdf7

git merge-base --is-ancestor 66c66140113c4a6be8ce0b11b5aa23ccc774ac22 HEAD
# must succeed
```

If remote HEAD moved past `b722aa440`: **STOP**. List new commits. Do not silently accept a newer tip.

---

## Package under test

Built on this host from the freeze tip. Prefer the packaged tree, not the Bazel build tree.

| Artifact | Path |
|---|---|
| Package dir | `C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms` |
| Zip | `C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms.zip` (~149 MB) |
| Binary | `...\dist\windows\ovms\ovms.exe` |

### Identity hashes (verify before live)

```text
ovms.exe SHA256:
3DFC2D11E614BD03924E6730AD8053DB00A6E5564F41E11F966A0929B44F65FE

openvino.dll SHA256:
F7797C7D89C78E67E2BC4779F8848A850B4C1C21C41EB6D3FB7D28A2450DAAC1
ProductVersion: 2026.5.0-23099-d015add94c1

openvino_genai.dll SHA256:
EF21DB9E15382916D3F800B2A1575F8B9240AC80BF28927888E5DF6AABBA3596
ProductVersion: 2026.5.0.0-3454-01f999504f8

openvino_tokenizers.dll SHA256:
224BD94976DCC1FF47CBBF4C9DBF1A2F959E40A9C4BBDDDD497A79BBD360E0A8
ProductVersion: 2026.5.0.0-741-b40486a0aac
```

Expected `--version`:

```text
OpenVINO Model Server 2026.5.0.b722aa440
OpenVINO backend 2026.5.0-23099-d015add94c1
OpenVINO GenAI backend 2026.5.0.0-3454-01f999504f8
Bazel build flags: --config=win_mp_on_py_on
```

Re-check:

```powershell
$pkg = 'C:\git\gemma4-upstream-refit-clean-20260915\dist\windows\ovms'
Get-FileHash "$pkg\ovms.exe" -Algorithm SHA256
& "$pkg\ovms.exe" --version
```

If SHA256 ≠ expected: **STOP** — wrong package.

---

## Dependency provenance (hard gate)

Build was retargeted off old RC2. Current root:

```text
C:\opt\openvino -> C:\opt\openvino_genai_windows_2026.5.0.0.dev20260911_x86_64
```

Matches `versions.mk` Windows GenAI pin (`2026.5.0.0.dev20260911`).

**Do not** launch using:

- `C:\g54r2\...`
- `C:\opt\openvino_genai_windows_2026.4.0.0rc2_x86_64`
- leftover `C:\Program Files\openvino_toolkit_windows_2026.2...` on machine PATH
- developer Bazel output trees as runtime (`C:\o\...`, `bazel-bin\...`)

Prefer:

1. copy/extract package to a clean directory, **or**
2. run from `dist\windows\ovms` with PATH = package dir + Windows system dirs only
3. call `setupvars.bat` / `setupvars.ps1` from **inside the package**

Confirm loaded DLLs resolve from the package (not old RC / g54r2).

XGrammar: no separate standalone version recorded; treat **GenAI 2026.5 package** as grammar runtime authority.

---

## What build session already proved

| Gate | Result |
|---|---|
| Six `//src/test/llm/gemma4_generation:*` targets on HEAD | PASS |
| `git diff --check` | PASS |
| Product build `--config=win_mp_on_py_on` exit 0 | PASS |
| Package create `--with_python` | PASS |
| Packaged `ovms.exe --version` / `--help` | PASS |
| Semantic C++ changes during build | NONE |

Build log: `win_build_freeze_20260915-232545.log`  
Build used short Bazel root `C:\o` (long `output_user_root` hit MSVC `D8022` path-length failures — env only, no source fix commits).

OpenCV env note: `C:\opt\opencv_4.14.0\x64\vc16` is a junction → `vc17` (BUILD expects `vc16`).

---

## Read before live

- `docs/gemmamonster/GEMMA4-SEMANTIC-FREEZE-20260915.md`
- `docs/gemmamonster/GEMMA4-UPSTREAM-REFIT-PLAN.md`
- `docs/gemmamonster/POST-ASTRA-P0-CHECKPOINT.md` (if present / relevant to Arc)
- This handoff

**STOP SEMANTIC FEATURE WORK.** Parser / grammar / template-state / API-policy bugs → report, do not “fix along the way.”

---

## Live matrix (Arc 140V)

Record for every case: request, response, raw model/tool traces if available, binary SHA, model id/path, server flags, timestamp.

### 1. Model load

- Load Arc 140V Gemma4 target used for this program
- Confirm server stays up; no mixed-runtime DLL faults

### 2. Unary Chat Completions / Responses

For tools present:

| tool_choice | Expect |
|---|---|
| `auto` | guided or optional path per freeze contract; no phantom executable calls |
| `required` | hard structured intent preserved; no silent downgrade to none |
| named tool | named intent preserved; invalid names rejected |

Also: omitted / null / empty `tools` with hard `tool_choice` must fail closed (P0-B).

### 3. Streaming

Same matrix as unary (`auto` / `required` / named).

Watch for:

- chunk-partition dependence (P0-D must hold)
- phantom tool headers before envelope commit (P0-A)
- terminal drain / incomplete envelope handling

### 4. Parallel tool calls

- `parallel_tool_calls=false`
- `parallel_tool_calls=true`

One-envelope garbage / adjacent multicall must fail closed (F9), not publish partial phantoms.

### 5. Multi-turn

- tool response → second model call
- prior tool history / rendered thought continuation (P0-C / H1–H2 / H4–H5)
- **H3** (reordered parallel tool responses / `tool_call_id`) is **backlog** — do not treat failure as freeze regression unless it blocks dogfood; record separately

### 6. Dogfood

- NovaClaw-style agent loop
- OpenCode-style agent loop

Long enough to exercise multi-turn tools, not a single hello-world.

---

## Pass / fail discipline

**PASS candidate toward acceptance** only if:

1. Package SHA matches this handoff
2. Provenance is 2026.5 package DLLs
3. Load + unary + streaming + parallel + multi-turn + dogfood complete with evidence

**FAIL / STOP** if:

- wrong SHA / RC2 or g54r2 DLLs loaded
- hard tool intent erased
- phantom executable tool calls
- streaming depends on chunk boundaries
- unbounded malformed tool growth / crash
- cross-family OpenAI tool regressions (F7 lives in generic `OpenAIApiHandler::parseTools()`)

On FAIL: first meaningful error + request/response + loaded DLL paths + SHA. Do not weaken contracts.

---

## Explicit non-goals for this tester session

- No new Gemma4 semantic C++ features
- No freeze-scope reopen (P0/F6/F7/F9/F10 already frozen)
- No “quick rebuild against whatever is in C:\opt”
- No declaring production ready from `--version` alone

---

## Suggested return format

```text
TESTED_PACKAGE_SHA256:
TESTED_HEAD:
LOADED_OPENVINO:
LOADED_GENAI:
LOADED_TOKENIZERS:
MIXED_OLD_RUNTIME: YES/NO

MODEL:
LOAD: PASS/FAIL
UNARY_AUTO:
UNARY_REQUIRED:
UNARY_NAMED:
STREAM_AUTO:
STREAM_REQUIRED:
STREAM_NAMED:
PARALLEL_FALSE:
PARALLEL_TRUE:
MULTI_TURN:
NOVACLAW:
OPENCODE:

VERDICT:
  LIVE_ACCEPTANCE_PASS
  or LIVE_ACCEPTANCE_FAIL

BLOCKERS:
- ...
EVIDENCE_PATHS:
- ...
```

---

## Handoff verdict from build session

```text
VERDICT: READY_FOR_LIVE_ACCEPTANCE
BUILD_CANDIDATE: PRODUCED
SEMANTIC_FREEZE: INTACT (no source mutation for build)
```
