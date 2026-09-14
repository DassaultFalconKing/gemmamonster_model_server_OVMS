# Whitespace-loop repair report — 2026-09-14

**OVERALL: BLOCKED / NOT ACCEPTED.** Only test contracts and this investigation
record were committed. No production repair was implemented because the required
TDD RED execution is blocked by the canonical Windows compiler configuration.
There is no new candidate binary or live acceptance result.

```text
SOURCE_HEAD: 5775cfe36506b8e7b75e86a4262f4241b95bcb41 (source before this documentation commit)
SOURCE_TREE: 18e2422bf1b3a88a0d6622779a789e886faf0d38
SOURCE_BASE: 908d669563f57535ab4eb747989e9ab33dfd5267
BRANCH: fix/gemma4-whitespace-loop-20260914 (local only)
WORKTREE: CLEAN at preflight before evidence/report creation
DEPENDENCY_HEADS:
  GenAI source: 7ea2546852a382cd16bd22dea0cfad2db70ed744 (verified, clean)
  Tokenizers submodule: a04accf6282d9b304214b492694b18c3979f667a (verified)
  OpenVINO source: UNKNOWN (configured pin 227c33757d1ef95d4da506d00686f923fdd2a535)
XGRAMMAR_HEAD: UNKNOWN (active candidate; no candidate built)
XGRAMMAR_REFERENCE_HEAD: bc09a30ec10ba30a6c1ab0c79eaeba3ca518d11f (verified, clean)
ENV_PREFLIGHT: PASS with temporary selection of C:\opt\bazel.exe = Bazel 6.1.1
UNIT_BUILD: FAIL (compiler bootstrap, not a product assertion)
BUILD: UNKNOWN (product build NOT RUN)
UNIT: UNKNOWN (0/6 executed; semantic RED NOT RUN)
LIVE_FRESH: UNKNOWN (NOT RUN)
LIVE_WARMED: UNKNOWN (NOT RUN)
PARALLEL_TRUE: UNKNOWN (repaired candidate NOT RUN)
PARALLEL_FALSE: UNKNOWN (repaired candidate NOT RUN)
WHITESPACE_BOUND: UNKNOWN (production propagation not implemented/proven)
INCOMPLETE_FRAME_DIAGNOSTIC: UNKNOWN (production repair not implemented/tested)
OVERALL: BLOCKED / NOT ACCEPTED
```

## Evidence authority

Fetched and re-resolved `origin/docs/rc2-acceptance-20260914` before work. Local
and remote-tracking HEAD both resolved to
`1497f814307ceeea8b8e2356d6081e429170a946`.
The primary evidence was read from `C:\git\rc2-908d6695-handoff-docs-20260914`.
The handoff and earlier verdict/deep-dive contain superseded classifications;
`WHITESPACE-LOOP-FINDING.md` and the K/F1 full decodes establish generated
whitespace before parsing. Renderer notes are actually located at
`deep-dive/renderer/RENDERER-NOTES.md`.

Pinned evidence:
[primary probe](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/tree/1497f814307ceeea8b8e2356d6081e429170a946/docs/probes/20260914-leakage-turn04).
Historical live results are reference evidence only and are not inherited as
repair acceptance.

## Atomic test commits

- `9b4a2a282d9bd2d0086e5612bdcf2e977e68c07b`: exercise the real
  `Gemma4GenerationConfigBuilder` and its structural JSON serialization for
  auto/required/named choices and both parallel modes. Require the bound at the
  serialized tool-schema boundary. This is not yet a matcher/soak proof.
- `5775cfe36506b8e7b75e86a4262f4241b95bcb41`: feed the canonical unfinished echo
  frame through `OVMSTextStreamer` and `OutputParser`; require no executable
  call, no content leakage, and a terminal diagnostic containing phase, LENGTH,
  pending state, buffered bytes, generated-token count and tool name. A test-only
  overload probe allows the STOP-only baseline to compile; a future reason-aware
  end overload must consume the actual LENGTH reason.

Both tests are **unexecuted**. Do not describe either as a proven reproduction
or GREEN. Existing normal-call and multiplicity tests are also unexecuted.

## Minimal integration traced; no fake OVMS field

At exact GenAI `7ea254...`,
`src/cpp/include/openvino/genai/generation_config.hpp:158-171` defines
`StructuredOutputConfig::JSONSchema` with only `value`; `to_json()` serializes
only `type` and `json_schema`. The installed RC2 header agrees.

The necessary dependency seam is a configurable optional whitespace bound in
this real GenAI type, serialized as a sibling `max_whitespace_cnt` property by
`to_json()`, with default-unbounded behavior retained for existing callers.
Equality and debug serialization must preserve the option too. The acceptance
dependency source must separately pin XGrammar in `src/cpp/CMakeLists.txt`;
the frozen known-good dependency profile must remain untouched.

GenAI's `src/cpp/src/sampling/structured_output/xgrammar_backend.cpp:38-49`
serializes the structural tag using `structural_tag_to_json()` and calls
`xgrammar::Grammar::FromStructuralTag()`. At exact XGrammar `bc09a30...`,
`cpp/structural_tag.cc:582-592` reads `max_whitespace_cnt`, and
`cpp/structural_tag.cc:1930-1947` passes it from the per-tag JSON schema node into
`JSONSchemaToGrammar`. This establishes the required integration surface,
**not** implemented propagation or runtime enforcement.

OVMS currently constructs the tool JSONSchema at
`src/llm/io_processing/generation_config_builder.hpp:79`. A future fix must set
the real GenAI option there, then verify the resulting grammar rejects three
insignificant whitespace characters while allowing zero/two, whitespace inside
string values, and legitimate complete multiple calls. Tests/docs containing
`max_whitespace_cnt` do not satisfy the production propagation gate.

## VLM_CB termination seam traced

`src/llm/servable.cpp:787` and `:807` finalize unary streamers despite having
`output.finish_reason` available; `:811` retains that real reason for API
serialization. Streaming obtains the actual reason at `:843` and finalizes at
`:854`. These are the VLM_CB call sites for a minimal explicit reason-aware
streamer finalization path.

`src/llm/ovms_text_streamer.cpp:201-254` drains buffered tokens and then sends
STOP unconditionally. Keep the legacy virtual `end()` contract compatible;
pass the actual terminal reason explicitly at the VLM_CB seams. Do not infer
LENGTH from a token-budget equality or globally alter legacy end behavior.
The Gemma4 parser owns incomplete frame state in
`src/llm/io_processing/gemma4/gemma4_tool_parser.cpp:834-943`.
Diagnostics must observe that state and must never manufacture a call or JSON.

## Canonical build blocker and attempted recovery

The operation used `Enter-GemmamonsterEnv.ps1 -RequireRuntimeRoot`, then the
repository's `test-stable-source.ps1` with `maintainer-rc2` and the Heretic
tokenizer path. It did not hand-assemble a compiler or substitute another
runtime profile. See [preflight](repair-evidence/preflight.log) and
[unit bootstrap log](repair-evidence/unit-bootstrap-failure.log) for the exact
executed command, pins and failure.

Observed recovery steps (these subsequent tool outputs are summarized here,
not reconstructed as raw logs):

1. Global `C:\opt\bazel.exe` was 6.4.0. The existing 6.1.1 executable was selected
   temporarily for each operation; the original file was restored in `finally`.
2. Canonical MSYS bash was missing. The existing
   `C:\opt\msys2-x86_64-20240727.exe` installer was launched hidden with the
   repository-prescribed arguments. It exited 0; bash reports 5.2.26. This new
   MSYS installation remains on disk.
3. Test analysis completed, but compiler actions failed with `msvc_not_found`.
   `vcvarsall.bat`, cl/link/lib/ml64 and MSVC 14.44.35207 all exist.
4. Exact Bazel 6.1.1 `windows_cc_configure.bzl:257-267` recognizes the modern
   layout only if the VC directory has exactly Auxiliary, Redist and Tools.
   `C:\BuildTools\VC` also has vcpkg. It consequently searches the old layout,
   producing the misleading missing-tool diagnostic.
5. An initial configure-only sync lacked `--experimental_repo_remote_exec`;
   its failed request was cancelled by stopping only this task's Bazel server.
   A later sync supplied that flag and hermetic Python 3.12 explicitly.
6. Windows ACL denied a temporary move of vcpkg outside VC. No backup directory
   was created; vcpkg remains at its original path. No ACL/ownership change or
   elevated command was attempted.
7. A temporary subset-based layout check in the embedded Bazel script was
   rejected by Bazel's installation integrity check (`corrupt installation`).
   The original script was restored. No integrity bypass was attempted.

The canonical compiler layout must be repaired through an authorized toolchain
setup before semantic TDD can continue. A newer Bazel or alternate VC/runtime
profile would require a separate change to the canonical build authority; none
was substituted here.

[Restoration hashes](repair-evidence/restored-tool-hashes.json) prove byte-exact
restoration of global bazel.exe and the embedded detection script.
[VC layout](repair-evidence/vc-layout.json) records the blocking fourth directory.
The preflight PASS is operation-specific: global bazel.exe was restored to 6.4.0
afterward, and preflight alone does not establish compiler readiness.

`git diff --check` on the evidence commit reports trailing whitespace/blank EOF
in the captured raw logs. Those logs are retained without editorial cleanup.
The added C++ tests, report and JSON records have no whitespace errors.

## Unfinished work / continuation gates

After the compiler blocker is resolved, execute both new contracts to genuine
semantic RED, implement/rebuild the real GenAI/XGrammar integration, apply the
Gemma4 per-tag bound, and preserve VLM_CB terminal diagnostics. Add matcher
boundary tests and run normal/parallel regressions before the product build.
Then freeze source/dependency identity, build and package with the canonical
procedure, hash candidate modules, prove loaded-module provenance, and execute
the entire fresh/warmed live matrix, retaining raw requests, responses,
token IDs, full decodes and the first failing turn.

No candidate executable/DLL hashes, effective repaired grammar, repaired
GenerationConfig or new server TRACE window exist because no candidate was
built or launched. No OVMS process was restarted and no inference request was
sent by this repair attempt. No merge to main or remote push was performed.
