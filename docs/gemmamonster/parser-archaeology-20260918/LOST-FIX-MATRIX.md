# Gemma4 parser lost-fix matrix — 2026-09-18 (docs-only, static verification)

Branch: `fix/gemma4-mid-thought-toolcall-c5-20260918`
BASE (C5 behavioral baseline): `a671ddf9f10f31a8afda849b44400291c35148ea`
HEAD at time of writing: `a671ddf9` (no production/test changes in this session)
Method: static only — `git show` / `git diff` / `git log -S|-G` / file reads.
No build, no test runs, no production or test code changes.
Status vocabulary: `RETAINED` / `REIMPLEMENTED` / `WEAKENED` / `LOST` /
`TEST_LOST` / `OBSOLETE_BY_DESIGN` / `UNRESOLVED` / `FALSE_POSITIVE`.

## 1. Lineage map (chain of custody, verified by merge-base)

- `fd0c86c7` (PR3, `fix/gemma4-parser-generation-candidate`) — streaming/holdback
  hardening + `gemma4_streaming_hardening_test.cpp`. Parallel line: shares only
  upstream base `6f3df706b` (#4386) with the PR4 line. **Not an ancestor of C5.**
  Its hardening file **never entered the C5 lineage**
  (`git log --oneline a671ddf9 -- <hardening-test>` is empty).
- `0a537f089` (Sep 5, `fix: let tool start terminate open reasoning phase`) —
  introduced the generic REASONING-phase tool-start transition in
  `OutputParser::parseChunk`. **Not an ancestor of PR3** (parallel lines).
- `62a3d71de` (Sep 5, test predecessor) — created
  `src/test/llm/output_parsers/gemma4_reviewed_contract_test.cpp` with
  `StreamerTransitionsFromOpenGemmaReasoningToTools` and 7 sibling tests.
  Ancestor of PR4 (`b4b183d6`): True.
- `7b5b73be` (Sep 5, `wip(gemma4): scope reasoning routing and isolate builder`) —
  scoped the generic transition behind `OutputParsingConfig::toolStartTerminatesReasoning=false`
  and opted `Gemma4ReasoningParser` in (`=true`).
- `b4b183d6` (PR4, `fix/gemma4-rc1-reviewed-contracts` tip) — reviewed-contract line.
  **Not an ancestor of C5. Not an ancestor of `dd7ac8de8`.**
- `dd7ac8de8` (Sep 15, `feat(gemma4): transfer RC tool-calling stack for 2026.4
  upstream review`) — tree **still contains** `toolStartTerminatesReasoning`
  (verified in `output_parsing_config.hpp` at that ref) and the refined handoff
  (`52aee8bfe`). Parallel line to the accepted staging refit.
- `43bc254e` (`staging/gemma4-upstream-refit-clean-20260915`, accepted RC) —
  ancestry **never contained** `toolStartTerminatesReasoning`
  (`git log --oneline 43bc254e -S'toolStartTerminatesReasoning' -- src/llm` is empty)
  and never contained `gemma4_reviewed_contract_test.cpp`. No revert commit exists;
  the hunk was never carried across the lineage fork.
- `7c072087f` (Sep 16, transplant accepted-RC delta onto upstream main) → C5
  `a671ddf9` — faithfully inherited the already-weakened state.

Loss mechanism for everything below marked LOST/TEST_LOST: **lineage fork +
incomplete refit/transplant, not a revert.** `--diff-filter=D` on the reviewed
contract test path returns nothing: the file was never deleted, it was never
transplanted.

## 2. Calibration case (confirmed LOST): reasoning -> tool implicit transition

Historical contract (canonical form at `52aee8bfe`, Sep 9):

- `OutputParser::parseChunk`, REASONING phase: explicit `endTag` (`<channel|>`)
  wins when it precedes the tool opener; otherwise a complete tool start tag
  (`<|tool_call>`, incl. registry-mode per-tool variants) terminates reasoning:
  bytes before the opener are flushed as reasoning, tool bytes stay buffered,
  phase moves to `TOOL_CALLS_PROCESSING_TOOL`, incomplete opener is held
  (`nullopt`) until more bytes arrive.
- Gated by `OutputParsingConfig::toolStartTerminatesReasoning` (default false);
  only `Gemma4ReasoningParser` opts in. Design note `52c6b534d`: canonical
  protocol closes `<channel|>` first; the flag is a tolerance/recovery seam.
- Regression tests: `StreamerTransitionsFromOpenGemmaReasoningToTools`
  (`62a3d71de`, input `<|channel>thought\nNeed a file.<|tool_call>...` with NO
  `<channel|>`, expects `reasoning="Need a file."`, empty content, 1 parsed call)
  and `ReasoningImplicitlyEndsOnSplitToolStartWithoutChannelEnd`
  (PR3 hardening suite, split-opener variant with Russian prose + Windows path).

Current C5 evidence of loss:

- `src/llm/io_processing/output_parsing_config.hpp` (43 lines): no
  `toolStartTerminatesReasoning` field (`grep` clean).
- `src/llm/io_processing/output_parser.cpp:413-420` (REASONING branch): checks
  only `reasoningParser endTag`; no tool-start lookup; falls through to
  `parseReasoningChunk(tokens, finishReason)` which keeps phase REASONING, so
  tool bytes are consumed as reasoning and the call is never parsed.
- `src/llm/io_processing/gemma4/gemma4_reasoning_parser.hpp:43-49`: no opt-in.
- Both regression tests absent: reviewed-contract file deleted from lineage;
  hardening suite never transplanted; zero name matches in `src/test/llm`.
- No equivalent: every C5 test that pairs reasoning with a tool call uses an
  explicit `<channel|>` — verified bodies:
  `ParseToolCallOutputWithSingleToolCallAndReasoning` (`gemma4_output_parser_test.cpp:147-163`),
  `RecoversBareKnownCallAtReasoningPhaseBoundary` (`gemma4_upstream_refit_contract_test.cpp:112-119`,
  bare `call:..` syntax, explicit end),
  `DetectsAdjacentToolMarkerWithDefaultDecodeMode` (`gemma4_special_token_handoff_test.cpp:39-57`).
  A bare-`call:` recovery path is not a substitute for a full `<|tool_call>`
  opener arriving mid-thought: different trigger syntax, different phase logic.

Status: **LOST** (implementation) + **TEST_LOST** (both probes).
Recovery pointer: port `52aee8bfe` hunk onto C5 `parseChunk` REASONING branch +
`7b5b73be` config field + opt-in; regression tests `StreamerTransitions…`
(coalesced) and `ReasoningImplicitlyEndsOnSplit…` (split) from the cited commits.

## 3. Matrix

| # | Contract (§5 order) | First known | Historical test | Historical impl | C5 equivalent | C5 test | Status |
|---|---|---|---|---|---|---|---|
| 1 | reasoning -> tool implicit transition (no `<channel|>`) | `0a537f089` (generic), gated `7b5b73be`, refined `52aee8bfe` | `StreamerTransitionsFromOpenGemmaReasoningToTools` (`62a3d71de`); `ReasoningImplicitlyEndsOnSplitToolStartWithoutChannelEnd` (PR3 `fd0c86c7`) | `output_parser.cpp` REASONING branch + `toolStartTerminatesReasoning` (`output_parsing_config.hpp`, Gemma4 opt-in) | none — C5 `output_parser.cpp:413-420` checks only `endTag` | none (all C5 reasoning+tool tests use explicit `<channel|>`; bodies verified §2) | **LOST** + **TEST_LOST** |
| 2 | tool-start as reasoning terminator (same as #1, flag side) | `7b5b73be` | same as #1 | `OutputParsingConfig::toolStartTerminatesReasoning`, `gemma4_reasoning_parser.hpp:48` | field absent at C5 (43-line config) | none | **LOST** |
| 3 | explicit `<channel|>` reasoning termination | pre-PR4 (`b44c4eafc` port) | `ParseToolCallOutputWithSingleToolCallAndReasoning`, `ParseReasoningWithoutToolCall` (in 39 retained) | `parseReasoningChunk(..., UNKNOWN)` + remainder preserve | identical (`output_parser.cpp:415-416`, `parseReasoningChunk` ownership unchanged) | same tests retained (`gemma4_output_parser_test.cpp:147-178`) | **RETAINED** |
| 4 | implicit reasoning start from rendered prompt | PR4 `output_parser.cpp:354-363` (`detectAndSetImplicitReasoningStart`, rtrim+endsWith) | generation-contract tests (superseded set) | `detectAndSetImplicitReasoningStart` | `classifyRenderedPromptState(...)==OPEN_THOUGHT` (`output_parser.cpp:359-366` + `rendered_prompt_state.cpp:80-95`), centralized superset | `gemma4_generation/rendered_prompt_state_test.cpp` | **REIMPLEMENTED** |
| 5 | coalesced reasoning start/body/end/content in one flush | C5 `output_parser.cpp:389-393` (coalesced-close to UNKNOWN) | PR4 reasoning-parser override (`b4b183d6:.../gemma4_reasoning_parser.cpp:34-42`) returned `nullopt` on any chunk containing start/end tag — dropped coalesced bodies | buggy (data loss) | Qwen3 inheritance (strip tags, emit body) + UNKNOWN-branch coalesced-close | `ParseToolCallOutputWithSingleToolCallAndReasoning` (coalesced full envelope via streamer) | **REIMPLEMENTED** (old impl buggy, C5 strictly better) |
| 6 | special-token decode mode transitions | pre-PR4 | `DetectsAdjacentToolMarkerWithDefaultDecodeMode` (C5-era, same semantics) | `needSpecialTokensForCurrentDecode` per-phase predicates | identical predicates (`output_parser.cpp:324-332`); streamer moved decode reconcile before token-ID injection (`ovms_text_streamer.cpp`, handoff fix) | `DetectsAdjacentToolMarkerWithDefaultDecodeMode` | **RETAINED** (+fix) |
| 7 | token-ID structural phase detection | pre-PR4 | `DetectsAdjacentToolMarkerWithDefaultDecodeMode` | `getPhaseStartTagForToken` (tool-first, phase guards) | identical guards (`output_parser.cpp:334-348`) | same | **RETAINED** |
| 8 | split `<\|tool_call>` start marker | PR3 `77305a67b`/`1a92c54b7` | `SplitToolCallStartTagDoesNotLeakIntoContent`, `PartialPrefixIsHeld…` (param matrix) | `StreamOutputCache::lookupTags` INCOMPLETE holdback | same holdback semantics (`output_parser.cpp:62-89`) | `stream_output_cache_test.cpp` (LookupTag/LookupTags unit); `StreamingWithBiggerChunks` | **RETAINED** (impl) / **TEST_LOST** (named end-to-end probes) |
| 9 | split `<tool_call\|>` end marker | PR3 (same series) | `SplitToolCallEndTagDoesNotLeakIntoContent`, `FinishAfterPartialEndTagDoesNotEmitEmptyToolCalls` | same holdback | same | same cache tests; `StreamingWithMissingEndTagBeforeStop` (fail-closed variant) | **RETAINED** / **TEST_LOST** (exact probes) |
| 10 | structural-marker holdback (no leak into content/reasoning) | PR3 `721e13d12` | `PartialPrefixIsHeldAndBytesAreNeitherLostNorDuplicated` | holdback helper (later `lookupTagsAtBoundary` lineage) | `lookupTags`/`lookupTagsAtBoundary` + `preambleBoundaryAtBufferStart` (`output_parser.cpp:49-59,91-149`) | cache unit tests; `DoesNotPromoteCrossChunkBareCallMidSentence` (bare-syntax variant) | **REIMPLEMENTED** (superset: boundary-gated) |
| 11 | first tool call after reasoning (explicit end) | pre-PR4 | `ParseToolCallOutputWithSingleToolCallAndReasoning` | REASONING→UNKNOWN→TOOL routing | identical routing | retained (`gemma4_output_parser_test.cpp:147`) + `ParseToolCallWithThoughtPreamble:359` | **RETAINED** |
| 12 | second/parallel tool call after first | pre-PR4 | `ParseTwoToolCallsAtOnce`, `ParseToolCallOutputWithThreeToolCalls(WithContentInBetween)`, `StreamingWithWhitespacesBetweenToolCalls` | WAITING_FOR_TOOL re-entry | equivalent refactor (`output_parser.cpp:444-458`) | all retained | **RETAINED** |
| 13 | tool call followed by normal content | pre-PR4 | `ParseToolCallOutputWithContentAndSingleToolCall`, `ThreeToolCallsWithContentInBetween` | WAITING→CONTENT on content start tags/STOP | identical | retained | **RETAINED** |
| 14 | tool call followed by STOP (atomic flush, no dup) | PR4 `de65d7b70`/`b27cc5397` + `CompleteBufferedGuidedJsonEmitsWholeToolCallOnFinalFlush` | `CompleteBuffered…FinalFlush`, `TruncationDoesNotExposeExecutableToolCall` | buffered finalize/withhold | STOP drains `pending`, commits only validated envelopes (`gemma4_tool_parser.cpp:598-657`); `parseToolCallChunk` stays | `phantom:CanonicalValidCallPublishesOneAtomicDelta`, `RepeatedFinalizationDoesNotDuplicateCommittedCall` | **REIMPLEMENTED** (moved into tool parser) |
| 15 | incomplete tool call at EOF / truncated args never fabricate | PR3 `FinishAfter…` trio; reviewed `TruncationNeverFabricatesArguments` | `FinishAfterPartialToolStart/OpenArgsObject…`, `GuidedJsonTruncationNeverFabricatesArguments` | withhold-until-complete | same fail-closed shape in native parser | `phantom:StopBeforeEnvelopeClosePublishesNothing`, `LengthBeforeEnvelopeClose…`, `StreamingSplitMalformed…`, `StreamingWithMissingEndTagBeforeStop` | **REIMPLEMENTED** |
| 16 | malformed tool names / unknown registered tool fail closed | accepted-RC era `e001de937` | (new in C5 lineage) | registry `allowedToolNames` + `discardRejectedCandidate` | same (`gemma4_tool_parser.hpp:135-144`, `rejectCandidateEnvelope`) | `RejectsUnknownRegisteredTool` | **RETAINED** (C5-lineage contract, intact) |
| 17 | invalid (guided) JSON cannot coerce/fallback | `62a3d71de` `InvalidGuidedJsonCannotFallBackToNativeCoercion` (`{"s":}` throws) | exact `{"s":}`-throws probe | `tryParseGuidedJsonArguments` strict path | guided-scanner mechanism removed (see #26); strictness re-expressed in native number/container validation | `RejectsInvalidNumberLikeBareScalars`, `MalformedCallIsBounded…`, `f7:MalformedOrUnclosedArrayCommitsNoCall`, `policy:InvalidRequiredGrammar…` | **REIMPLEMENTED** (shifted layer; exact probe **TEST_LOST**) |
| 18 | recursive object/array arguments | PR3 `NestedObjectPreservesTypes`; reviewed `GuidedJsonEveryByteSplit…` nested payload | nested native sweep | `parseSingleArgument` recursion / guided scanner | `findMatchingContainerEnd` + depth cap 64, dual `{`/`(` syntax | `ParsesNestedNativeArgumentsRecursively`, `ArrayOfObjects…`, `NestedArrayOfArrays…` | **REIMPLEMENTED** (superset) |
| 19 | escaped quotes/backslashes in args | pre-PR4 (39-set) | `…ContainingEscapedQuotes/Apostrophes/Backslashes/…Quotes` | delimited-string semantics (`4a316e615` restore) | same | all retained (`gemma4_output_parser_test.cpp:846-911`) + `PreservesValidNumberLexemesLosslessly` | **RETAINED** |
| 20 | Windows paths in args | PR3 `WindowsPathsRemainJsonArrayNotStringifiedJson`, `FinishInsideUnclosedQuotedWindowsPath…`; reviewed `C:\\temp\\` payload + `C:\\llm\\README.md` probe | array-form + unclosed-quote probes | guided/native string handling | native string handling; one `C:\Users\test\file.txt` probe retained (`gemma4_output_parser_test.cpp:876`) | `…ContainingBackslashes` (retained) | **RETAINED** (basic) / **TEST_LOST** (array-form + unclosed-quote exact probes) |
| 21 | numeric lexeme preservation | `32b3b1fb6` | `PreservesValidNumberLexemesLosslessly` via helper test | `NumberPreservingWriter::RawNumber` + `kParseNumbersAsStringsFlag` | identical (`normalizeJsonLosslessly`, test helper `compactJsonLosslessly`) | `PreservesValidNumberLexemesLosslessly` + `partial_json_builder_test`/`number…` helper | **RETAINED** |
| 22 | bare/native call recovery (`call:name{…}` without `<\|tool_call>`) | accepted-RC `e001de937` | (new in C5 lineage) | `findBarePreamble` + `isLogicalBoundary` + boundary-gated preamble | same | `RecoversBareKnownCallAtReasoningPhaseBoundary`, `AtCrossChunkLineBoundary`, `DoesNotPromote…MidSentence` | **RETAINED** — complement of #1, not a substitute (bare syntax + explicit end only) |
| 23 | prose resembling a tool marker must not parse (non-Gemma) | `62a3d71de` `StreamerKeepsNonGemmaToolExamplesInReasoning` (hermes3+qwen3 `<think>` example) | exact cross-parser probe | gated flag (qwen3=false) — `7b5b73be` scoping | holds trivially (no transition exists); qwen3/hermes3 wiring intact (`output_parser.cpp` ctor sets unchanged) | none — nearest is bare-syntax gemma4-only `DoesNotPromote…` | **TEST_LOST** (behavior holds, guard gone; must be re-added with any #1 fix) |
| 24 | parser registry enforcement (unknown names throw) | pre-PR4 | `parser_config_validation_test.cpp` | ctor `throw Unsupported … parser` | identical throws (`output_parser.cpp:251,267`) | `parser_config_validation_test.cpp` retained | **RETAINED** |
| 25 | unknown named tool fail-closed at runtime | `e001de937` lineage | `RejectsUnknownRegisteredTool` | registry enforcement in tool parser | identical | retained (`gemma4_upstream_refit_contract_test.cpp:107`) | **RETAINED** |
| 26 | preamble recovery only at logical boundaries | C5 lineage (`preambleStartTagsRequireBoundary`, `lookupTagsAtBoundary`) | (new in C5 lineage) | `isLogicalBoundary` + `preambleBoundaryAtBufferStart` surviving clears | same | `DoesNotPromoteCrossChunkBareCallMidSentence`, `RecoversBareKnownCallAtCrossChunkLineBoundary` | **RETAINED** (C5-lineage contract, intact) |
| 27 | content/reasoning/tool remainder ownership across phases | pre-PR4 (`parse*Chunk` remainder preserve) | `MalformedCallIsBoundedAndLaterValidCallSurvives`, `TwoConsecutiveToolCallsKeepIndices` | endTag-remainder split + re-add; `AfterToolCall` single-envelope drain | identical ownership (`output_parser.cpp:152-218`); `AfterToolCall` break-for-reentry + 64-step drain + 4096B compaction | `MalformedCallIsBounded…`, `TwoCanonicalCallsIndependentOfPartition` | **REIMPLEMENTED** (old `ownsToolCallBoundaries` delegation folded into AfterToolCall protocol; runtime equivalence static-only, see UNRESOLVED-1) |
| 28 | tool-response / turn tokens at generation end | pre-PR4 | `…WithToolResponseTokenAtTheEndOfGeneration`, `StreamingContentWithTurnTokenAtTheEndOfGeneration` | contentParser startTags for gemma4 (`<turn|>`, `<|tool_response>`, …) | identical wiring (`output_parser.cpp:279-280`) | both retained (`gemma4_output_parser_test.cpp:725,757`) | **RETAINED** |
| 29 | guided-JSON byte-split escape matrix (11 payloads × every cut) | `62a3d71de` `GuidedJsonEveryByteSplitPreservesStringsAndTypes` | full matrix incl. `C:\\temp\\`, `\"`, `\\`, `\n\u0000`, nesting | guided streaming scanner (`findGuidedJsonEnd`, `maskStringValues`) | mechanism removed; partition-invariance kept for canonical/native payloads | `chunk_invariance:Single/TwoCanonicalCalls…`, `ReasoningContentIndependentOfPartition`, `ParsesNestedNativeArgumentsRecursively` | **WEAKENED** (narrowed to native/canonical subset) |
| 30 | tool parser owns quoted end markers / no router split at raw endTag | `f4dc17d6f`/`77abdb520` `ownsToolCallBoundaries` (+`871cd4702`, `d2edab5e7`/`b949d0837` CONTENT routing) | (implicit in PR4-era suites) | `parseToolCallChunk` full-buffer delegation when flag set | flag absent (`grep` clean); superseded by AfterToolCall single-envelope protocol + remainder split (see #27) | `MalformedCallIsBoundedAndLaterValidCallSurvives`, canonical-call partition tests | **REIMPLEMENTED** (redesign; static-only, see UNRESOLVED-1) |

## 4. Refuted FALSE_POSITIVE candidates

- Claim: `RecoversBareKnownCallAtReasoningPhaseBoundary` /
  `ParseToolCallOutputWithSingleToolCallAndReasoning` /
  `DetectsAdjacentToolMarkerWithDefaultDecodeMode` cover the implicit transition.
  Refuted: all three bodies use an explicit `<channel|>` immediately before the
  tool opener (cited lines in §2). Bare-`call:` recovery additionally uses a
  different trigger syntax. None exercises tool-start-terminates-reasoning.
- Claim: PR3 `fd0c86c7` is a "runtime-proven" ancestor of the transition.
  Refuted: `fd0c86c7` predates `0a537f089` on a parallel line (merge-base only
  at upstream `6f3df706b`); PR3 proves holdback/streaming contracts, not #1.
  (PR3 does contain its own later-added implicit-transition probe
  `ReasoningImplicitlyEndsOnSplitToolStartWithoutChannelEnd`, also lost.)

## 5. Handshake evaluation (§9 of the session brief)

Historical lineage already converged on the proposed shape, minus one side:

- Reasoning side (exists historically, lost): `toolStartTerminatesReasoning`
  — "tool start may terminate this reasoning phase", Gemma4 opts in, default false.
- Tool side (exists in C5, different form): registry enforcement
  (`allowedToolNames`, unknown names rejected) + AfterToolCall single-envelope
  ownership ("tool parser accepts handoff; router must not split/replay").
  The historical explicit tool-side flag `ownsToolCallBoundaries` was folded
  into this protocol rather than retained as a gate.
- Orchestration (both eras): `OutputParser` owns phase transitions; sub-parsers
  never switch `processingPhase` (verified C5 `output_parser.hpp:48-76`,
  `gemma4_tool_parser` 659-line body contains no phase writes).

Recommendation for the future repair (not implemented in this docs-only session):
restore the PR4-faithful single reasoning-side flag in its `52aee8bfe` form
(tool-start checked with explicit-end-wins ordering + incomplete holdback) rather
than inventing a new tool-side gate — the tool side already constrains via
registry + envelope validation, and `52c6b534d` records the tolerance/recovery
intent. Re-add `StreamerKeepsNonGemmaToolExamplesInReasoning` in the same commit
as the non-Gemma guard (§10 requirement).

## 6. UNRESOLVED (need runtime proof; deferred — no build in this session)

- U1: observable equivalence of C5 AfterToolCall remainder protocol vs historical
  `ownsToolCallBoundaries` delegation under adversarial chunkings (static
  reasoning says equivalent; matrix rows #27/#30 rest on code reading only).
- U2: §10 scenario checklist against C5 (token-ID-driven tool start from
  REASONING, implicit-start + tool, STOP-after-tool, post-tool content,
  multi-call after reasoning, prose-with-marker for gemma4 full tag): expected
  RED only for the implicit-transition family; the rest need executed
  confirmation.
- U3: exact-payload divergences inside WEAKENED row #29 (which of the 11 guided
  escape payloads still round-trip through the native parser + token grammar).
- U4: `e001de937` bare-call boundary edge cases vs old preamble handling
  (e.g. tab/CR-only gaps, `preambleBoundaryAtBufferStart` after STOP flush).

## 7. Verification-target status (session §14)

- Historical accepted parser contracts inventoried: yes — 30 rows above
  covering all §5 items plus lineage extras.
- Each with a C5 status: yes.
- HIGH-confidence lost contracts identified: **#1/#2** (single contract family).
- Reasoning→tool regression restored: **not in this session (docs-only)** —
  recovery pointers in §2/§5.
- Regression tests exist: **no** (to be ported from `62a3d71de` + PR3 suite).
- Shared parser/router/streamer behavior intact: **unchanged** (no code touched).
- UNRESOLVED documented: §6.
- BASE `a671ddf9`, HEAD `a671ddf9`, branch
  `fix/gemma4-mid-thought-toolcall-c5-20260918` recorded above.
- Incremental C5 build readiness: **not buildable in this session** — no
  compilation or test execution performed; readiness unverified.
