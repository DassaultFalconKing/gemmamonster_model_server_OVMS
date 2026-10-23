# CIB2 / RC3B OTD preflight: verified evidence and port gates

**Date:** 2026-10-23. **Status:** SOURCE-PREFLIGHT ONLY, NOT ACCEPTED. No GPU tests were executed here.

## Pinned provenance

- Immutable base annotated tag: qwm-semantic-refit-2026.4-rc3b -> b77b0f23fa7417e61778ef86ecb0ca739cc85f14 (tag object 0ff886df7b9b706d1d72174cfa0d729e94ede09e).
- Direct parent: qwm-semantic-refit-2026.4-rc3 -> b12a913ba492b951eb3384583e46541ffe467763; verified parent of RC3B commit.
- Manifest: docs/qwenmonster/RELEASE-CANDIDATE-20261023-RC3B-IDENTITY.json, verified at the tagged commit.
- Build reported by manifest: win_mp_on_py_off, isolated openvino_genai_windows_2026.4.0.0rc1_x86_64, stock GPU SDK plugin, **not** custom moe38545 / 21a2fd9f.
- ovms.exe: 22589440 bytes, SHA256 2beed15ee7f6af9a2c45854005caff24886562c8da5586f052bd2133e3d671c2.
- ovms_test.exe: 40527872 bytes, SHA256 aacd1f136a0142ade962f24543a8f3c4fb69b111689b353be3e2b397bc122f2c.
- RC3B is accepted=false. Manifest reports 6/6 live Gemma E4B, Gemma26 and Ornith runs, QwenmonsterGenerationPolicy 11/11 and targeted parser tests PASS; **not independently rerun**. Full ovms_test and owner signoff remain open.
- Both release tags are annotated but unsigned; GitHub reference identity is not a signature verification.

## Preflight results

| Gate | Status | Evidence / blocker |
| --- | --- | --- |
| F00 RC3B tag and direct RC3 parent | SOURCE_VERIFIED | GitHub tag and commit objects |
| F01 New branch isolation | SOURCE_VERIFIED | Branch created at exact RC3B SHA |
| F02 Native OTD in 2026.4 | UPSTREAM_SOURCE_VERIFIED | ExpertWeightProvider, native LRU, performance counters |
| F03 Exact SDK 2026.4rc1 OTD/ABI | NOT_RUN | 2026.4.0 source tag is **not** a binary-identity substitute for the installed RC1 SDK |
| F04 Oversize expert lease LRU side effects | SOURCE_DEFECT_PRESENT_UPSTREAM | Cache can mutate before capacity refusal in upstream 2026.4.0 |
| F05 RC3B executable SHA rehash | NOT_RUN | Operator Windows binaries not available in this environment |
| F06 Stock SDK vs active GPU plugin hash | NOT_RUN | Actual DLLs and loader provenance not available |
| F07 Static preflight unit suite | CODE_COMMITTED / NOT_EXECUTED | Python standard-library tests checked into branch |
| F08 Full ovms_test | NOT_RUN | Release candidate acceptance still open |
| F09 GPU performance and agentic soak | NOT_RUN | No host or authorized inference job in this execution |
| F10 Owner signoff | NOT_DONE | Not provided |

### F04 confirmed source-level issue

Upstream OpenVINO 2026.4.0 OffloadExpertWeightProvider::try_acquire_simultaneous performs LRU slot acquisition while iterating distinct experts, and only checks capacity **after previous experts have already been processed**. On a request larger than capacity, the path can return no simultaneous lease **after** cache side effects. The closed-program fix 7d905ba prevalidates the distinct expert count before mutating the cache. This requires an exact RC1 source comparison and baseline RED test before any port.

- https://github.com/openvinotoolkit/openvino/blob/2026.4.0/src/plugins/intel_gpu/src/graph/impls/ocl_v2/moe/expert_weight_providers.cpp
- https://github.com/DassaultFalconKing/openvino/commit/7d905ba91d2dd48eb9df1a1ebaa83db0ff1fd0ce

## Ordered port map

| Sequence | Closed-program source | Disposition |
| --- | --- | --- |
| CIB2-00 offline exact LRU replay | 86bab01e | Portable independently, no runtime changes |
| CIB2-01 OTD trace and read/transpose/copy telemetry | 4ff78eac | Optional 2026.4 plugin backport, no new synchronous waits |
| CIB2-02 transactional oversize-lease refusal | 7d905ba9 | Safety fix AFTER exact RC1 RED reproduction |
| CIB2-03 packed expert-major device layout | 52f57df1 | Candidate ONLY; default off, strict tensor/parity checks |
| CIB2-04 payload integrity and same-handle reader identity | 2ed011fc, 359445cd | Mandatory for packed mode |
| CIB2-05 atomic publish, trace reconciliation | 65d4afca, a973b006, ebb7c805 | Mandatory with pack/trace feature |
| CIB2-06 V1–V4 lifetime, router, clone, weights path | 124d0f44, 71efb7cb, bdeed850, 591ab0b5 | Differential bugs-only audit, never blind cherry-pick |
| Deferred: USM_HOST default, expert prefetch, alternative cache policy, CPU lanes | Separate experiments | Not part of CIB2 baseline |

**Do not copy 2026.5 Intel GPU or OpenVINO DLLs into the 2026.4 RC3B runtime.** Previous mixed-ABI experiment failed with Windows error 127. Only source backports rebuilt against exact compatible SDK cohort are admissible.

Wave01 host pack publication tests reported 200 repeats passing, but GPU acceptance and performance were NOT_RUN; held-reader replace and stale temp risks remain. Source:
https://github.com/DassaultFalconKing/openvino/tree/integration/otd-wave01-win-acceptance-20261022/docs/coordination/acceptance/WIN-OTD-WAVE01-20261022

## Read-only Windows host commands

Use an isolated checkout, never alter the live RC3B installation. The commands below do not launch an inference server.

~~~powershell
git fetch origin tag qwm-semantic-refit-2026.4-rc3 tag qwm-semantic-refit-2026.4-rc3b
git fetch origin feature/cib2-rc3b-otd-preflight-20261023
git switch feature/cib2-rc3b-otd-preflight-20261023
py -3 -m unittest discover -s tests/cib2 -p 'test_*.py' -v
py -3 scripts/cib2/preflight_rc3b.py --repo .
~~~

For a strict local identity gate, additionally supply actual files using --ovms-exe, --ovms-test-exe, --sdk-gpu-plugin and --active-gpu-plugin, then --strict. Determine the actual loaded GPU DLL and the untouched SDK copy; equality to a user-specified file by itself does not establish the SDK file's authenticity.

Verifier exit 2 means FAIL; exit 3 means strict mandatory evidence missing. Missing binary inputs produce NOT_RUN, never PASS. This static verifier **cannot grant product acceptance**, even if mandatory checks pass.

## Host test gates before any GPU code port

1. Rehash exact RC3B installed binaries, GPU plugin, GenAI/runtime DLLs; record stock 2026.4rc1 SDK provenance, source tree SHA, loaded-module paths, driver, model/checkpoint, quant/IR and tokenizer identity.
2. Run targeted Gemma and Qwen/Ornith parser/grammar and real tool-call suites; then complete ovms_test and ensure no protocol regression.
3. Freeze stock RC3B performance oracle with exact input token IDs, same model and driver, KV U4, C1/C2/C4, OFFLOAD_RATIO 0 (negative control) and 20/40/75 (when graph eligible); compare TTFT, decode, p95, memory, actual disk bytes, warm/cold. Each cell warmup plus >=3 repeats.
4. Prove an oversized simultaneous expert set can be refused without cache side effects. Capture RED on exact SDK, patch minimal source, repeat GREEN, numerical parity and cancellation/in-flight reader tests.
5. Bring in offline P3 replay first, then passive P2 tracing. Incomplete traces and speculative accepted-token metrics not actually exposed must never be fabricated.
6. Packed candidate requires checksum/payload, model-identity, atomic publication, reader handle pin, fault/race and C1/C2/C4 performance gates. Default remains native OTD.
7. Owner signoff after full suite and representative agentic soak. No work here marks the underlying RC3B accepted.

## Source modification boundary

Preflight branch allows only docs/cib2/, scripts/cib2/ and tests/cib2/. No edits to Gemma/Qwen parsers, XGrammar, build dependency locks, driver configuration or RC3B tags. Separate 2026.4 GPU source candidate branch is required for future functional patches.

Active state: docs/cib2/STATE.md. Revert point: qwm-semantic-refit-2026.4-rc3b. No private prompts, host path secrets, model binaries or unsanitized traces in GitHub.
