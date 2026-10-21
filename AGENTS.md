# AGENTS.md — Gemmamonster / Qwenmonster engineering contract

This file applies to automated agents working in this repository. It is an
engineering workflow policy, **not** evidence that the current candidate is
accepted. Preserve the accepted Gemma4 baseline and the published C6 dependency
source lock. Project-specific technical contracts live under `docs/qwenmonster/`.

## 1. Identity before edits

- Record repository, working branch, exact base/HEAD/tree SHA, clean/dirty status,
  dependency source **and actual build-library** revisions, active runtime profile,
  and a revert point. Prefer an isolated worktree to editing the known-good C6.
- Read `docs/qwenmonster/{STATE.md,ACCEPTANCE.md,public-source-lock.json,
  PUBLIC-COHORT-INTEGRATION.md,STREAMING-LIFECYCLE-DECISION.md,
  SCHEMA-VALIDATION-PROFILE.md}` where relevant; verify they describe the
  *actual* checked-out revision. Never silently advance pinned GenAI, XGrammar,
  OpenVINO, Minja, Tokenizers, tokenizer/template or model revisions.
- Locate the bug's owning boundary before patching:
  `tokenizer / model-native format / XGrammar / GenAI generator / OVMS parser /
  streamer / OpenAI API / harness`. Do not repair a grammar mask defect by
  adding an undocumented parser workaround or a family-specific SSE transport.

## 2. Reproduce → diagnose → smallest patch → controls

1. **RED:** Execute a minimal deterministic reproducer against the unmodified
   candidate; capture the command, exact source/dependency SHAs, real failure,
   input, expected and actual behavior. If it cannot be reproduced, label
   `UNREPRODUCED`, never invent a failing log.
2. **ROOT CAUSE:** Identify the state transition or API contract violated;
   distinguish an implementation defect from fixture/test harness or environment
   failures. State assumptions and unsupported cases explicitly.
3. **PATCH:** Change the smallest responsible component, in an atomic,
   reviewable commit. Prefer existing OVMS/GenAI/XGrammar interfaces and
   narrow, named helpers to speculative cross-layer rewrites.
4. **GREEN:** Re-run the *same* RED, then adversarial and positive controls:
   malformed → valid call, repeated/parallel calls, missing/duplicate
   arguments, STOP/LENGTH/CANCEL, reset, partial XML marker boundaries,
   SSE index/ID/finish reason, and tool-result continuation as applicable.
5. **REGRESSION:** Run focused Qwen, generic OutputParser and Gemma
   controls. Record pre-existing failures by test name and compare before/after;
   do not quietly modify the Gemma known-good to make a Qwen-only patch green.
6. **EVIDENCE:** Preserve concise reproducible evidence and explicit status for
   unrun stages. Build success does not imply native matcher masks, model
   inference, API compatibility or agentic acceptance.

## 3. Non-negotiable parser and streamer invariants

- An executable tool identity is published only **after** completed envelope,
  registered function name and executable argument schema validation. OpenAI
  SSE has no identity retraction: rejected calls publish neither ID/name nor
  executable arguments, and consume no public call index.
- A published function/header is followed only by arguments for that same
  function/index; IDs are unique per request; accepted indices are monotonic
  in accepted call order. Reset isolates requests and clears pending queues.
- Chunk partition must not change semantic tool calls, typed arguments, order
  or SSE reconstruction; exercise single/multiple splits at every XML delimiter
  and repeated functions. Completed queued deltas must be delivered promptly.
- Treat native XML transport markers as reserved boundaries. Malformed
  envelopes must not consume the next call. Any recovery is bounded, explicitly
  justified and regression-tested. A truncated argument must not become
  executable merely because generation ended.
- Unsupported or malformed schemas and arguments **fail closed**, with a
  documented supported JSON Schema profile. Do not silently weaken `required`,
  enums, unions or unknown restrictions, or substitute default arguments.
  Prefer request-level validation for client usability where appropriate.
- Keep **grammar mask** correctness separate from **parser tolerance**:
  Gemma's bounded JSON whitespace and empty `ExcludeToken()` fixes do not
  establish Qwen XML #650 end-marker or #802 zero-parameter correctness.

## 4. Required change proposal format

Before substantial new code, write six explicit fields for **each** proposed
change, in `docs/qwenmonster/` or the change's own design note:

1. **Cause:** observed failure or measured deficiency, evidence, severity.
2. **Files:** exact paths (including tests, fixtures and docs).
3. **Implementation:** owning function(s), algorithm, limits, error semantics.
4. **Expected effect:** precise postconditions and compatibility tradeoffs.
5. **Test:** a RED/GREEN test or clearly labelled new unexecuted gate, plus
   relevant positive/Gemma/generic controls and acceptance stage.
6. **Provenance:** upstream file/issue/commit, existing project pattern or
   explicitly `INDEPENDENT DESIGN`. Distinguish verified from inferred ideas.

If a proposed fix cannot yet pass a native build or actual model test,
state that limitation. Do not silently promote it.

## 5. Evidence and promotion ladder

`SOURCE → BUILD → UNIT → MATCHER → API → LIVE → AGENTIC`.

Each stage requires its *own* measured artifacts with exact source/binary/model
identities. `NOT RUN`, `FAILED`, `CACHED`, `SOURCE ONLY` and `UNVERIFIED`
are first-class statuses. Synthetic tokenizer/matcher evidence is not a live
model run; a comparator is not a peer-engine capture; an accepted parser call
is not a successful tool execution or completed agent continuation.

Track separately: model-native tool decision → parser/API delivery → harness
execution → successful next assistant turn. Do not declare a known-good
candidate until all requested acceptance gates are measured and pass.

## 6. Commit, environment and checkpoint discipline

- Update `docs/qwenmonster/STATE.md` before risky work and after every
  meaningful milestone with `ACTIVE_STAGE, BASE_SHA, WORK_BRANCH, CURRENT_HEAD,
  DEPENDENCY_LOCK, LAST_GREEN_TESTS, CURRENT_FAILURE, ROOT_CAUSE, NEXT_ACTION,
  REVERT_POINT, EVIDENCE_PATH, ACCEPTED`. Preserve links or hashes for large
  external logs; never fabricate an artifact.
- Make atomic commits by mechanism (build compatibility, parser lifecycle,
  streamer delivery, schema enforcement, native grammar, evidence). Confirm the
  remote fast-forward and publish handoff SHAs. Keep dependency fork changes
  on separate branches with a proposed **new** cohort revision; do not edit
  the existing published lock by stealth.
- Detect the active shell: use PowerShell syntax on Windows, Bash on Bash
  hosts, fish-compatible syntax on fish hosts. If RTK is configured for the
  repository, follow that wrapper without mangling structured build/test output.
- Never commit secrets, credentials, model weights, personal machine artifacts
  or enormous build outputs. Do not claim an unexecuted action succeeded.

## 7. Reviewer-facing outcome

Every completed change reports: branch/HEAD, exact dependency and runtime
identities, RED reproduction, root cause, patch, tests (pass/fail/cached/not run),
unchanged baseline failures, evidence paths, commit/push status, next gate,
and `ACCEPTED: YES/NO`. Label peer comparisons `VERIFIED / INFERENCE /
UNKNOWN` and decisions `KEEP / REFINE / PORT SEMANTICS / TOLERANCE ONLY /
DROP / UNKNOWN`. Prefer compact, information-dense lists to narrative claims.

## 8. Windows `ovms_test` build and execution

- `//src:ovms_test` is the full diagnostic/test executable, separate from
  `//src:ovms` and the small parser test targets. A successful focused parser
  build does not prove the full dependency graph or HTTP handler compiles.
  Build it only when the requested diagnostic scope needs it; do not launch
  the complete test suite or prepare every model as an incidental build step.
  A GTest filter limits execution, not compilation: building the full target
  still compiles its registered tests and server dependencies. Preserve the
  isolated incremental output/cache for subsequent filtered runs; do not clean
  it merely because a later runtime fixture or filter failed.
- Before building, record checkout/HEAD, MSVC/Bazel versions, exact dependency
  sources and library hashes. Use the checkout's `versions.mk`,
  `windows_install_build_dependencies.bat`, and `public-source-lock.json` as
  separate inputs. In this QWM baseline the auxiliary recipe selects BoringSSL
  `firebase/boringSSL-SwiftPM` tag `0.32.1` at
  `38b03401110f03bde32bc7e86ff4f815238ed2d3`, curl Windows build `8.22.0_2`,
  OpenCV `4.14.0`, and Python `3.12.10`.
  Recheck these values on another revision. Restore missing auxiliary inputs
  explicitly; never run the blanket installer with cleanup/expunge against
  an accepted install, fetch moving dependency heads, or replace the core cohort.
- Inspect repository overrides and junction targets. A present wrapper directory
  may point to missing headers/DLLs. Verify files after staging: extractor exit0
  can mean "No files to process". Check official archive hashes, architecture,
  headers, import libraries, DLLs and layout. A `vc17` alias to a verified `vc16`
  package is a layout adaptation, not proof of historical binary equivalence.
  Record a newly restored binary's exact identity instead of inheriting acceptance.
  Record URLs and the authoritative digest source: e.g. official GitHub release
  asset digest, curl's published checksum, or NuGet catalog package SHA512.
- Set up the selected x64 MSVC environment, pinned core runtime and auxiliary
  runtime paths. Check both `python` and `python3`: repository rules can select
  `python3` independently. Embedded Python alone may lack `Include/Python.h`,
  `libs/python312.lib` and `Lib/site-packages`; full-target analysis can need the
  development distribution even with `win_mp_on_py_off`. Keep `PYTHONHOME`,
  `PYTHON_BIN_PATH`, `PYTHON_LIB_PATH`, `--python_path`, repository environment,
  action environment and actual executables consistent. Do not dump the complete
  environment into logs; it may contain credentials.
  Probe `sys.executable`, `sys.version`, `sysconfig.get_path('include')` and the
  required files with both interpreter entry points; retain only these selected
  nonsecret fields privately and compare their versions to the chosen recipe.
- Use an isolated short Bazel output root and bounded jobs (initially 2 on the
  validated host). Serialize heavy builds and check active owned processes before
  retrying. Retain UTC run identity, exact argument array, PID, stdout/stderr and
  final exit status outside the source tree. Never delete accepted caches or kill
  unrelated processes to make a diagnostic run fit.
- Build and execute as separate stages. Pass arguments as a native argument
  array; avoid CMD loops using `%1`/`shift` to reconstruct nested
  `--test_arg=--gtest_filter=...`. Such forwarding split the filter in the measured
  Windows run and caused a Bazel37 path error before compilation. Prefer direct
  `bazel build //src:ovms_test`, then direct `ovms_test.exe` execution. A shell or
  dependency-analysis failure is not a C++ failure and means tests are NOT RUN.
- Run from the tested worktree root with the exact staged runtime/auxiliary DLL
  paths and `OPENVINO_TOKENIZERS_PATH_GENAI` set. Windows fixture path helpers use
  the current directory; an executable copied elsewhere does not carry its test
  fixtures. Pin only the fixture assets needed by the selected filter. Preserve
  tokenizer/model/template provenance and never substitute an unrelated tokenizer
  merely to satisfy a directory name. Keep model weights and generated assets out
  of Git. Do not rewrite all Windows test configs for a request-parser-only gate.
  The tokenizer extension must be an existing file from the exact chosen runtime;
  record its hash and fail preflight on a missing/empty path or fallback.
- First run `--gtest_list_tests` with the intended filter and verify expected
  enabled test names are present. For QWM-01 require both
  `HttpOpenAIHandlerParsingTest.QwenXmlRequestSchemaProfileIntake` and
  `HttpOpenAIHandlerParsingTest.QwenXmlSchemaProfileIsNotAppliedToHermesByAccident`.
  For `HttpOpenAIHandlerParsingTest.QwenXml*`, require exactly these two enabled
  tests and no extras. If a filter is lost, a listing of the entire suite is a
  failure, even though it contains both required names. Other filters require an
  explicitly reviewed selected set before execution, including parameterized cases.
  Then run that same filter with a new per-run `--gtest_output=xml:...` path.
  Reject zero selected/executed tests, missing/stale XML, skipped required cases,
  nonzero failures/errors, or process failure even if another log contains PASS.
  XML must be outside source, created after this run's recorded start, and hashed
  with the logs. Parse its executed testcase names/statuses and root counts;
  require the exact selected set and count, with required cases actually run and
  completed. The fresh XML plus process exit code is authoritative, not a console
  PASS line or an older result file. Do not count disabled or skipped required tests.
- Keep handler status validation, HTTP400 transport mapping, model generation and
  live agent continuation as separate gates. The two QWM request-parser tests do
  not by themselves prove the HTTP response code or real model behavior. Run the
  relevant generic/Gemma controls after changes and compare baseline failures by
  exact name; never edit accepted Gemma tests to turn a Qwen gate green.
  Unless separate named transport/model/agent tests or probes were actually
  executed and retained, report HTTP400/API, LIVE and AGENTIC as NOT RUN.
- Publish compact results and hashes with explicit BUILD/UNIT/API/LIVE status;
  retain raw machine logs privately and use placeholders in public commands.
  Document exact local commands in the private handoff, never the private path map
  in commits. These rules are workflow policy, not a claim that a run has passed.
- On this Windows/Bazel 7.4.1 path, verify file-symlink support and start Bazel
  with `--windows_enable_symlinks` before `build`. With the default false,
  a generated Protobuf header's `_virtual_includes/.../*.pb.h` became a directory
  junction to a file, causing C1083/WinError267 despite the generated header
  existing under `_virtual_imports`. Inspect the reparse-point type and target;
  do not fabricate/copy a header into the include tree or edit generated code.
  If stale invalid junctions need removal, first stop the owned build and verify
  each absolute link and target stays inside its isolated output root. Remove
  only the junction nonrecursively, then let Bazel regenerate it with the correct
  startup flag. Never change system symlink policy or clean a baseline tree.
