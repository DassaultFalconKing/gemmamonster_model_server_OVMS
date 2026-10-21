# First iteration failure triage

## Initial Windows launch (environment)

COMMAND: local Bazel wrapper, four handoff targets.
SOURCE SHA: `8cd25d63085637d112f616d62913e345a93d2233`.
DEPENDENCY SHAs: `PUBLIC-COHORT-SOURCE-PINNED.json`; initial installed Minja
fixture-only drift recorded in build identity audit.
ERROR: `< was unexpected at this time`, before Bazel, at compiler setup.
ROOT CAUSE: shell/environment boundary; exact variable cause not discriminated.
SMALLEST CHANGE: isolated wrapper with Python 3.12 first in PATH; retry reached
Bazel and compiled all four targets. No product workaround.
NEGATIVE CONTROL: compiler errors are distinct; none in the initial source build.

## Zero-parameter test crash (fixture)

COMMAND: Qwen suite and isolated zero-parameter filter.
SOURCE SHA: `8cd25d6`.
DEPENDENCY SHAs: source lock plus build identity limitation above.
ERROR: Windows SEH `0xc0000005` in zero-argument test.
ROOT CAUSE: fixture passed a null rapidjsonRepr; constructor type-map helper
dereferences that pointer. This was not the XGrammar zero-parameter defect.
SMALLEST CHANGE: retain a parsed schema document for fixture lifetime.
NEGATIVE CONTROL: isolated test passed; other Qwen payloads retained.
FIX COMMIT: `bc609ea`.

## Rejected prefix steals next call (parser)

COMMAND: original disabled test explicitly run with
`--gtest_also_run_disabled_tests`, then active deferred-publication regression.
SOURCE SHA: `8cd25d6`, then `bc609ea` plus active test.
DEPENDENCY SHAs: unchanged source lock / installed triage tuple.
ERROR: valid cd arguments at index 0 without a new name after invalid numeric call.
ROOT CAUSE: unmatched speculative first delta retained across rejected calls.
SMALLEST CHANGE: allocate identity only after completed-call validation.
NEGATIVE CONTROL: valid multi-call, repeated-name, partition/reset and STOP/LENGTH
controls; full Qwen 66/66 after change.
FIX COMMIT: `ca78a4d`.

## Ready arguments held until end (streamer)

COMMAND: `*QwenmonsterStreamerPublishesCompletedArgumentsBeforeEnd`.
SOURCE SHA: `ca78a4d` plus active test.
DEPENDENCY SHAs: unchanged source lock / installed triage tuple.
ERROR: one callback before end instead of header + completed arguments.
ROOT CAUSE: drain executed only for final flush.
SMALLEST CHANGE: same generic one-delta lookahead on every flush.
NEGATIVE CONTROL: generic29/29 and same Gemma67/70 baseline failure set;
Qwen partition/SSE reconstruction and exactly-one-finish test pass.
FIX COMMIT: `3901c4e`.

## Malformed envelope borrows following parameter end (parser)

COMMAND: partition corpus with `</parameter1>` call followed by valid cd.
SOURCE SHA: `3901c4e` plus active corpus case.
DEPENDENCY SHAs: unchanged source lock / installed triage tuple.
ERROR: old string_tool name returned with later call bytes in its string argument.
ROOT CAUSE: parameter scanner searched across a completed outer envelope.
SMALLEST CHANGE: drop the malformed call when outer close precedes parameter close;
resume parsing after that transport boundary. The reserved outer close cannot be
embedded as literal parameter text under this safety rule.
NEGATIVE CONTROL: all split positions, valid nested XML text, repeated calls,
natural STOP bounded recovery and LENGTH truncation.
FIX COMMIT: `16c777e`.

## Schema constraints ignored (parser)

COMMAND: `*QwenmonsterSchemaValidationBeforePublication`.
SOURCE SHA: `16c777e` plus active schema regression.
DEPENDENCY SHAs: unchanged source lock / installed triage tuple.
ERROR: enum, extra-property, integer/number, union/nested and malformed schema
cases published executable identities.
ROOT CAUSE: only shallow lexical typing and required presence were checked.
SMALLEST CHANGE: existing RapidJSON validator plus embedded, restricted Draft 4
meta-schema; reject duplicate XML names. See SCHEMA-VALIDATION-PROFILE.md.
COMPILER FAILURES: C2220 from C5232 and C6313 on third-party templates; retain
`SCHEMA-GREEN.txt` and `SCHEMA-GREEN-retry.txt` locally. Narrow include suppressions
permit compilation; no dependency patch or global flag change.
NEGATIVE CONTROL: positive enum/integer/nullable/nested/local-ref and zero-parameter
controls; final Qwen69/69, policy9/9, generic29/29, same Gemma67/70 failures.

## Review-driven parser/schema edge regressions

All XML FSM states now stop at a reserved outer transport boundary, including
missing function/name/parameter/outer closes and a fresh envelope following an
unclosed call. Actual RED evidence: ALL-STATES-ENVELOPE-RED.txt and
RESERVED-BOUNDARY-RED.txt; fix `7ac3c7b`.

Schema review reproduced references into unchecked annotations, unsafe recursive
compiler maps, NUL regex truncation, required/default shortcuts and duplicate
JSON member injection. Fail closed with validated simple definition references,
safe compiler input, schema-aware default stripping, and duplicate/NUL rejection
for schemas and typed arguments. Restricted profile: SCHEMA-VALIDATION-PROFILE.md.
Actual RED evidence: SCHEMA-ENGINE-EDGE-RED.txt,
SCHEMA-REFERENCE-ANNOTATION-RED.txt, DUPLICATE-SCHEMA-RED.txt. Fixes `60b0d9f`
and `f6f2a29`. Negative controls include valid references, nullable/nested types,
a property named default and zero-parameter tools; 36 schema cases pass.

Independent read-only review closed all reported scoped findings after these
corrections. Full final unit counts and remaining baseline failures are retained
in UNIT-RESULTS.json. No live/release acceptance was inferred from review.

## Open native matcher risks (no dependency patch)

COMMAND: standalone native XML probe; raw grammar and every ASCII token mask
retained locally in `NATIVE-XML-MATCHER.txt`.
SOURCE SHA: public GenAI/XGrammar lock; existing compiled matcher library hashed
in the native probe receipt. Synthetic ASCII vocabulary, no inference model.
ERROR: mask permits `1` after `</parameter`; malformed candidate is accepted as
a prefix but is not a completed call. Zero-parameter branch accepts 1024 spaces
and can then close. This demonstrates an unbounded whitespace path, not an actual
infinite model-generation run.
ROOT CAUSE: native XML matcher behavior; parser safety cannot repair its masks.
SMALLEST PROPOSED CHANGE: separately reproduce and evaluate compatible upstream
backports before proposing a new cohort. No dependency source was patched here.
NEGATIVE CONTROL: correct hard/lazy single-tool examples complete; existing
bounded JSON/ExcludeToken native suite31/31 passes.

## Gemma baseline remains red

COMMAND: initial and final `//src:gemma4_output_parser_test`.
SOURCE SHA: initial `8cd25d6` and current candidate.
DEPENDENCY SHAs: same installed tuple and tokenizer hashes for both runs.
ERROR: three identical failed test names recorded in UNIT-GEMMA-initial.txt and
UNIT-GEMMA.txt (duplicated reasoning end tag, no-tools content, escaped quotes).
ROOT CAUSE: not investigated in this Qwen-only iteration; source/tests match C6.
SMALLEST PROPOSED CHANGE: investigate in a separate Gemma baseline workstream;
do not silently modify accepted Gemma behavior in a Qwen patch.
NEGATIVE CONTROL: no new failing Gemma test after generic prompt drain.

Live/model/agent/differential runner tests: NOT RUN. The acceptance gates are
not green; neither Qwenmonster nor a new dependency cohort is promoted.
