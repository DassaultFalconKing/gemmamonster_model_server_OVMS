# Gemma4 P0 recovery checkpoint — 2026-09-15

Branch: `staging/gemma4-upstream-refit-clean-20260915`
Astra review commit: `e2bcbc9e3eadba9948c83e6fe2a0766c28ebdb2b`
Muse checkpoint before review publication: `81f9a133458601569ebcdfb606bbe9f29e039e30`
Status: `NOT MERGEABLE`

## Already GREEN after Astra REVIEW_HEAD

- `parallel_tool_calls`: RED `18de2c26c` -> GREEN `7be4b7aa4`.
- generation-side unsafe tool-name validation: RED `447718b8d` -> GREEN `547df8030`.
- raw phantom-publication RED: `fe894aad9`; local test reproduces malformed header/index leakage.

## P0 order

1. Transactional Gemma4 tool-call publication.
   - No public id/name/index before complete validated envelope commit.
   - Malformed then valid must produce only valid call at index 0.
   - Truncated STOP/LENGTH candidate must not commit.
   - Do not fix by unary post-filtering; streaming cannot retract an emitted header.

2. Preserve explicit hard HTTP intent.
   - Current `parseTools()` rewrites `required`/named to `none` when `tools` is omitted or null.
   - Add Chat/Responses RED for omitted/null/empty tools and return InvalidArgument.
   - Do not weaken existing hard structured-output validation.

3. Post-#4103 rendered prompt-state agreement.
   - Runtime Jinja and Minja converge on final `req.promptText`; reconcile there.
   - OPEN_THOUGHT after tool response must continue thought then require hard tool call without a second opener.
   - Fix implicit-reasoning detector: current rtrim(prompt) cannot match Gemma start tag ending in newline.
   - Test required, named, auto, closed thought, and tool-result -> second call.

4. Chunk invariance / final drain.
   - Semantic result must not depend on how identical decoded text is partitioned into parseChunk calls.
   - Test one/two calls coalesced vs split; reasoning opener/body/closer coalesced vs split.
   - Prefer Gemma-local progress/drain first; touch generic OutputParser/streamer only with a separate failing minimal test.

## P1 after P0

- object-compatible argument schema contract; no silent non-object roots;
- no-parameters tool policy;
- duplicate tool-name rejection;
- collision between named tools and policy keywords `none`/`auto`/`required`;
- canonical unknown-tool envelope must be rejected/swallowed, not leaked as visible content;
- reject one-envelope garbage + second bare `call:` unless real trace justifies it;
- bound malformed candidate bytes/depth.

## Ownership

Codex: transactional publication; prompt-state reconciliation; chunk/progress-drain changes.
Muse: HTTP hard-intent RED/GREEN; schema/API negatives; BUILD/hygiene; broad test execution.
ChatGPT: freeze SHA, adversarially review every GREEN, maintain recovery state.

Read with:
- `GEMMA4-UPSTREAM-REFIT-ADVERSARIAL-SEMANTIC-REVIEW.md`
- `GEMMA4-UPSTREAM-REFIT-PLAN.md`
