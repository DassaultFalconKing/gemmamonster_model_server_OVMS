# M1 protocol matrix

| Scenario | Code/test evidence | Candidate status |
| --- | --- | --- |
| one completed call in one chunk | `QwenmonsterCompletedCallsInSingleChunk` | test added, unrun |
| two completed calls in one chunk | `QwenmonsterMultipleCompletedCallsInSingleChunk` | test added, unrun |
| complete call followed by partial next | `QwenmonsterCompletedCallFollowedByPartialName` | test added, unrun |
| STOP inside an open value | `QwenmonsterStopDoesNotPublishOpenParameter` + changed legacy fixture | test added, unrun |
| LENGTH inside an open value | `QwenmonsterLengthDoesNotPublishIncompleteArguments` | unit test added; streamer end semantics pending |
| STOP after complete `</function>` | legacy `ToolCallRecoveredWhenStoppedAfterInnerCloseTag` | test retained, unrun |
| quoted attributes, nested JSON, zero arguments | existing Qwen suite | unrun |
| SSE response ownership and tool_call indexes | end-to-end live probe required | unverified |
| multiple parallel sessions | live acceptance required | unverified |
| Gemma 4 parser isolation | no Gemma source diff; tests still needed | unverified |

## Evidence grading
- **STATIC:** source reviewed and branch diff created.
- **RED:** only once actual pre-fix test output is saved.
- **UNIT GREEN:** only when focused Bazel test output exists.
- **LIVE GREEN:** only when real OVMS/Qwen/SSE/harness traces exist.
