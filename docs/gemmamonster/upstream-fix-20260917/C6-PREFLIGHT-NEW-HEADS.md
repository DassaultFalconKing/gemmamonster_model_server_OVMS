# C6 PREFLIGHT — NEW-HEAD RECONSTRUCTION

Date: 2026-09-18  
Track: Gemma4 upstream landing  
Coordination branch at preflight write: `fix/gemma4-upstream-evidence-triage-20260917 @ 426a2eea`

## 1. Definition

C6 is a **new construction**, not another mutation of C5 and not a continuation of the empty-args investigation.

Its job is narrow:

- take the product fixes whose behavior was established by the C2→C5 Frankenstein sequence;
- transplant those fixes onto freshly resolved upstream heads;
- compile a new GenAI/XGrammar runtime and a new OVMS binary from those fresh bases;
- rerun the canonical acceptance gates against the new binary identity;
- produce the reviewer/upstream series from the resulting clean diffs.

C5 is the behavioral proof source. C6 must not inherit C5's old dependency wiring, build directories, runtime slots, temporary probes, or historical commit topology merely because they happened to be useful during investigation.

## 2. What C5 proved and C6 is allowed to carry

### Product behavior established by C5

1. **Bounded JSON whitespace fixes the Sept-16 streaming degeneration.**
   - Gemma4 tool JSON uses a finite whitespace bound.
   - C2 fixed the live failure without parser changes.
   - C3/C4/C5 repeated the same G5/G6 result after parser, GenAI, and XGrammar refreshes.
   - This is the primary repair carried into C6.

2. **The parser repair stack is independently valid and regression-tested.**
   - escaped delimited strings restored;
   - numeric lexemes preserved in the streaming test helper;
   - malformed/incomplete tool envelopes remain non-executable;
   - hard named-tool mismatch fails closed;
   - deferred post-call STOP flush is pinned as the expected streaming behavior.

3. **The repair survives dependency movement.**
   - C4 moved GenAI to the newer upstream base and remained GREEN.
   - C5 moved XGrammar to `f6043f4` and remained GREEN.
   - C5 canonical/live-like behavior did not regress.

### Explicitly not promoted as a C6 repair premise

- the historical `calculator{}` observation is **not a reproduced product defect**;
- F3 is evidence-only;
- F4 remains experimental and is not required to explain the confirmed whitespace fix;
- F1/F2/F5 may be upstreamed as independently justified generic hardening/API work, but C6 must not claim that they repair a reproducible empty-args bug.

This distinction is mandatory in code comments, commit messages, test names, and PR descriptions.

## 3. Fresh upstream heads

Snapshot at preflight write:

- OVMS upstream `main`: `3c2ac5f80d1547b36a887fc8f5084b140a2c4c41`
- OpenVINO GenAI upstream `master`: `3abf349be2c53f911d5de6edc2744e20c1780ba5`
- XGrammar upstream `main`: `1de42473b51ca176ab24aa0b5f434b293503e4a9`

These SHAs are **inputs for planning only**.

Immediately before C6 construction:

1. fetch all three upstreams;
2. re-resolve their branch heads;
3. record the resolved SHAs in the C6 identity manifest;
4. compare each new head against the snapshot above;
5. stop only for a concrete overlapping semantic conflict.

No "it was clean yesterday" assumptions.

## 4. Construction rule

C6 must be reconstructed from clean upstream bases.

Do not merge or replay the full C2→C5 branch history. Do not carry WORKSPACE runtime-slot commits into the reviewer series.

### GenAI reconstruction

Start from the freshly resolved GenAI upstream head.

Carry only the code required by the intended upstream series:

1. bounded JSON-schema whitespace API;
2. corrected contract tests:
   - unset = legacy/unbounded;
   - positive value = valid explicit bound;
   - equality/serialization include the bound;
   - **zero/negative are invalid**, matching current XGrammar semantics;
3. if generic hardening is included, rebuild it as independently reviewable commits:
   - fail-closed matcher advancement;
   - tokenizer-aware structural-tag parsing;
   - typed token structural API and language bindings.

Every intermediate commit in the reviewer series must compile. In particular, tokenizer-info plumbing must exist before commits that consume `m_tokenizer_info`.

### XGrammar reconstruction

Use the freshly resolved upstream XGrammar head.

Do not forward-port our old XGrammar snapshot as source patches unless a new incompatibility is demonstrated.

Required verification:

- token-aware structural-tag API used by GenAI exists;
- bounded JSON whitespace behavior exists;
- the GenAI focused matcher/structural-tag tests compile and pass against the resolved XGrammar head.

### OVMS reconstruction

Start from the freshly resolved OVMS upstream `main`.

Reapply the C5-proven product changes semantically:

1. escaped delimited string semantics;
2. numeric-lexeme-safe test helper;
3. Gemma4 tool JSON whitespace bound at the call site;
4. bounded-whitespace + required-field tests;
5. stale hard-named tool expectation -> `INVALID_ARGUMENT`;
6. deferred STOP-flush streaming expectations.

Do not transplant:

- C2/C3/C4/C5 WORKSPACE slot wiring;
- F3 experiment;
- debug traces;
- net-zero audit pair `2489e342/b9f65b96`;
- research harnesses;
- local artifact paths.

## 5. Build sequence

C6 gets new build identities.

### Stage A — GenAI/XGrammar

1. clean C6 GenAI worktree from fresh GenAI upstream;
2. bind the freshly resolved XGrammar head;
3. configure a new C6 build root;
4. compile GenAI with tests enabled;
5. run focused structured-output/XGrammar tests;
6. install/package into a new immutable runtime slot, e.g. `C6-GENAI`;
7. record DLL/LIB/header hashes and exact dependency SHAs.

Do not reuse `G2-X1`, `G2-X2`, or `TOKEN-REPAIR-ACTIVE`.

### Stage B — OVMS

1. clean C6 OVMS worktree from fresh OVMS upstream;
2. apply the C5-proven OVMS patch set;
3. wire OVMS only to the immutable C6 GenAI runtime;
4. build/package a new OVMS distribution;
5. record executable/DLL hashes and `--version` output.

A successful incremental relink of an old candidate is not a C6 build. C6 needs a new reproducible identity from the new bases.

## 6. Required gates

### Static / unit

- GenAI bounded-whitespace contract: PASS;
- GenAI/XGrammar focused compatibility: PASS;
- OVMS Gemma4 focused parser/generation tests: PASS;
- semantic Gemma4 suite: PASS;
- no new failures hidden as "environmental"; any unavailable fixture is named explicitly.

### Canonical behavior

Reuse the canonical C5 G2 pack as the behavioral oracle, not old mismatched dogfood fixtures.

Required:

- canonical unary turns produce expected `tool_calls`;
- long `search_docs` streaming path remains correct;
- prefix/text STOP behavior remains correct;
- no whitespace-only degeneration.

### Live regression

Run the same calibrated long-context G5/G6 fixture used across C2→C5:

- unary: valid tool call;
- streaming: repeated tool call success;
- whitespace-only chunks: zero;
- no server/executor failure.

Run the C5 live-like protocol checks needed to show no parser/tool-policy regression:

- auto text/no-call;
- named;
- required;
- parallel tool calls;
- Unicode/multi-call;
- unknown hard-named tool fails closed.

Empty-args stress data may be retained as observation-only. It is not a C6 acceptance premise unless a reproducible defect is re-established.

## 7. Diff and provenance gate

Before C6 can be called promotable:

- diff OVMS C6 against the freshly resolved OVMS upstream base;
- diff GenAI C6 against the freshly resolved GenAI upstream base;
- classify every changed production file;
- prove candidate-specific runtime wiring is absent from the upstream series;
- bind all test evidence to the exact binary hashes and source SHAs;
- verify local branch head == pushed remote head.

Expected product diff should remain small and explainable. If C6 suddenly needs a large unrelated patch surface, stop and re-triage rather than blessing the blob because the tests happen to be green.

## 8. C6 success condition

C6 is complete only when all of the following are true:

- fresh upstream heads recorded;
- fixes reconstructed rather than history-dumped;
- GenAI/XGrammar builds on the fresh dependency head;
- OVMS builds against that fresh GenAI runtime;
- canonical C5 behavior is reproduced;
- long-context whitespace degeneration remains absent;
- parser/tool-policy gates remain green;
- exact source/runtime identities are frozen;
- atomic upstream commit/PR series can be generated from the clean C6 diffs.

The intended conclusion is:

> C5 established the behavior. C6 demonstrates that the same narrowly scoped fixes survive reconstruction on current upstream heads and produce a clean, compilable, reviewable upstream candidate.
