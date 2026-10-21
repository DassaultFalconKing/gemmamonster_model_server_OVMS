# W3 — LENGTH / CANCEL lifecycle (in progress)

Status: **PARTIAL MEASUREMENT. ACCEPTED: NO.**  
Master-plan card: W3. Tip after Cursor takeover includes this note.

## Source contract (already in tree)

- `OVMSTextStreamer::end()` always flushes `finishReason=STOP` into the parser so
  tool parsers can finalize held state. That is intentional and separate from the
  HTTP finish reason.
- `GenAiServable::preparePartialResponse` serializes the **backend**
  `generationOutput.finish_reason` on the final SSE/unary chunk after `end()`.

## Measured now

- Responses path already had
  `legacyServablePreparePartialResponseResponsesEndpointHasCorrectUsageOnLength`
  (`response.incomplete` for LENGTH).
- New focused chat-stream control:
  `CbChatStreamingPreservesBackendLengthFinishReason` — expects
  `"finish_reason":"length"` and no `"stop"` on the shared GenAI response path
  when the backend reports LENGTH (despite parser STOP flush).
- **Direct** `ovms_test.exe` run: **1/1 PASSED** (2026-10-21). Private XML
  `w3-length-gtest.xml`. A Bazel `--test_arg=--gtest_filter=...` launch via
  legacy CMD failed exit3 with empty test log (filter arg split on `=`); that is
  a launcher defect, not a product RED.

## Still NOT RUN / OPEN

- Live Ornith `max_tokens` truncation end-to-end
- Client disconnect / generation-handle cancel with resource reclamation proof
- After-cancel healthy request on a live server
- Mapping of CANCEL vs parser error at every owning CB calculator (partially covered by CB parser-failure suite)

Do not promote ACCEPTED from this note alone.
