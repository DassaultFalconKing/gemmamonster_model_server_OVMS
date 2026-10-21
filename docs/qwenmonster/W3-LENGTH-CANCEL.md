# W3 — LENGTH / CANCEL lifecycle (unit measured)

Status: **CHAT STREAM UNIT PASS. LIVE max_tokens PASS. CANCEL NOT PROVEN. ACCEPTED: NO.**  
Master-plan card: W3.

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
- `CbChatStreamingPreservesBackendLengthFinishReason` **PASS** (1/1, 74 ms)
  when `ovms_test.exe` is launched with the active OpenVINO runtime on `PATH`.
  The serialized SSE chunk was `"finish_reason":"length"` followed by `[DONE]`.
  The assertion also rejects `"finish_reason":"stop"`.
- `bazel test //src:ovms_test` with the repo `test:windows` path
  `C:/opt/openvino/runtime/...` exited `-1073741515` (`STATUS_DLL_NOT_FOUND`)
  in 2s and produced no gtest body. That is a harness DLL lookup miss on this
  machine, not evidence that the API dropped LENGTH.
- **Direct** `ovms_test.exe` run: **1/1 PASSED** (2026-10-21). Private XML
  `w3-length-gtest.xml`. A Bazel `--test_arg=--gtest_filter=...` launch via
  legacy CMD failed exit3 with empty test log (filter arg split on `=`); that is
  a launcher defect, not a product RED.

## Live Ornith slice

Same tip binary, existing GPU profile (`OFFLOAD_RATIO` 20, `max_num_seqs` 1), model `ornith-35b-ov`.

- Unary `max_tokens=16`: HTTP 200, `finish_reason=length`, `completion_tokens=16`.
- SSE `max_tokens=16`: HTTP 200, final `finish_reason=length`, `[DONE]` present, no `stop`.
- Client closed the socket after the first SSE event (379 bytes). Executor samples then showed 0 scheduled requests. That does **not** prove generation-handle cancel or resource reclamation.
- Next unary (`Reply with exactly OK.`): HTTP 200, `finish_reason=stop`, content `OK`.

## Still NOT RUN / OPEN

- Generation-handle cancel with resource reclamation proof
- Mapping of CANCEL vs parser error at every owning CB calculator (partially covered by CB parser-failure suite)

Do not promote ACCEPTED from this note alone.
