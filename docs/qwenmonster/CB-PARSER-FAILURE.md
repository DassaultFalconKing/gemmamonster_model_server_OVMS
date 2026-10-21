# CB parser failure containment

Status: implemented; native RED reproduced (2/2 failing tests), final GREEN
6/6 and 171 existing controls PASS. Product and full diagnostic builds PASS.
ACCEPTED: NO.

1. Cause: `GenAiServable::preparePartialResponse` ignores the streamer's
   `StreamingStatus` and never checks `OVMSTextStreamer::hadParserError()`.
   A parser exception can therefore enqueue a finish delta while the consumer
   continues normal serialization and loopback. This is source-confirmed;
   executable impact must be reproduced before changing production code.
2. Files: `src/llm/servable.cpp`,
   `src/llm/language_model/continuous_batching/servable.cpp`,
   `src/llm/visual_language_model/continuous_batching/servable.cpp`,
   `src/test/http_openai_handler_test.cpp`, this note and `STATE.md`.
3. Implementation: inspect write status before serialization and inspect parser
   error after the terminal drain. On parser error return the same generic
   InvalidArgument status as the legacy path; clear unpublished deltas and
   disable loopback. A callback cancellation must remain cancellation rather
   than parser failure. The CB owner stops its generation handle on failure,
   because a disconnection callback may retain the handle beyond calculator
   teardown. Do not change API finish-reason mapping or parser grammar tolerance.
   VLM invokes the base serializer directly and needs the same explicit stop.
4. Expected effect: failed parser output cannot become a successful completed
   response, and the failed request stops consuming generation resources.
   Already delivered stream bytes cannot be retracted. This does not establish
   decoder-mask correctness or model acceptance.
5. Test: deterministic malformed Mistral argument-before-name input through the
   real streamer and base CB response path, including failure during write and
   end drain; callback cancellation and fresh healthy context controls. Execute
   RED first, then identical GREEN and Qwen/Gemma/request controls. New tests
   were NOT RUN at proposal time. The initial two tests subsequently reproduced
   successful serialization after parser failure, and passed after the patch;
   final controls and generation-handle runtime cancellation remain separate.
6. Provenance: independent design following existing legacy parser exception
   handling and existing `legacyServableParserExceptionCancelsGenerationAndReportsFailure`
   test. No upstream issue or dependency revision is claimed as its origin.

Final verification: all 177 selected native tests passed with exact listings,
fresh XML and successful process exit. This includes six parser-failure,
cancellation and healthy-context checks across Responses and Chat Completions,
10 common/legacy controls, two QWM intake tests, 11 tool controls and 148
Qwen/Gemma parser tests. The two original RED tests genuinely observed a parser
error followed by an OK backend status and normal terminal completion.

OpenCode supplied three Chat Completions tests in an isolated snapshot; the
coordinator reviewed them, adapted their names and executed them in the native
suite. Independent review found the VLM cleanup omission and the need to prove
the end-only failure boundary; both were addressed before final verification.
Compact source/binary/DLL/XML identities and build receipts are recorded in
`evidence/cb-parser-failure-20261021/RESULTS.json`. Raw logs remain private.

The native tests exercise actual tokenizer/streamer/parser/response preparation,
but they do not own a running generation pipeline. Actual handle stop, retained
callback cleanup, GPU resource reclamation, disconnect and live model acceptance
on the patched product remain NOT RUN. The server was stopped for these builds
and remains stopped. Parser STOP/LENGTH recovery and dependency cohort promotion
remain separate tasks.
