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
