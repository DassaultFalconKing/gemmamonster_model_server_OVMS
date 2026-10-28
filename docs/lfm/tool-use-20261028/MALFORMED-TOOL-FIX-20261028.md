# LFM family malformed native calls: bounded correction

Hub/evidence: `C:\gm\lfm-2026.4\malformed-fix-20261028` (`tasks.json`).
Base: `27b41dd474737604352cd39076e59a52d88dfda5`.

## Cause and correction

The real OMP request failed with HTTP400, first at registry/schema validation,
then at literal parsing on replay. A diagnostic replay using the staged LFM2
template produced native `execute(..., shell=True, ...)`: no such tool was
registered. This diagnostic uses Jinja2 rendering and is not a token-identical
receipt of the original invalid byte86 output. The original pre-parser bytes
remain unavailable; do not claim that exact malformed literal was recovered.

The source-level defect is verified: LFM AUTO ignored enabled tool guidance.
Only required/named requests received grammar constraints. Also, the native
grammar could not compile real OMP schemas containing maxLength/minItems/anyOf,
despite their acceptance by publication validation.

Changes:

* With guidance enabled, AUTO lazily constrains native envelopes to registered
  names and schema-shaped arguments. Prose remains optional; pseudo-tools are
  not promoted. A separate think tag shields draft calls inside reasoning.
* Bound maxLength strings and minItems arrays and compile nested typed anyOf
  branches for the real OMP schema shapes. Unsupported combinations still fail.
* Reset installed lazy grammar between requests. Preserve explicit response_format
  precedence. Guidance disabled, no tools and tool_choice=none retain their paths.
* For LFM only, grammar validation errors return an error instead of silently
  removing the constraint. Other model-family fallback behavior is unchanged.
* Transactional parser/schema publication checks are unchanged.

## Tests and external harness

OpenCode2.2.0, executable
`C:\Users\testc\AppData\Roaming\npm\node_modules\@opencode\cli\bin\opencode.exe`,
explicit model `opencode/glm-5.3-flash-free`, session
`ses_e8037d675ffeOdRa0VqB774bdL`. Shell preflight succeeded. The first assignment
produced an independent mechanism/schema review; the resumed assignment executed
the focused test command and audited the diff. Reports, prompts, commands, PIDs,
stdout/stderr and status records are under the hub. Speculative exact-byte claims
in the initial worker report were rejected. Its confirmed fail-open finding was
corrected; preserving response_format precedence is an intentional boundary.

* RED: new guided-auto test failed before implementation; 48PASS/2SKIP/1FAIL.
* Intermediate GREEN: 50PASS/2SKIP through the external harness, including full
  real OMP schema projection compiled with both LFM tokenizers and reset checks.
* Final build: `final\build-py_off\COMPLETE.json` records binary hashes.
* Final independent regression: 219PASS/2 expected SKIP, 0FAIL, including LFM,
  Gemma4 and Qwen3Coder controls (`final-regression.xml`).
* Real failure-request replays: unary/SSE on LFM2 and LFM2.5, with per-run raw
  artifacts; initial candidate completed all four with HTTP200. Final binary
  reruns also completed all four with HTTP200 and native registered/schema-valid
  calls, separately under `final-lfm2` / `final-lfm25` (34.69/23.47s and
  33.83/33.78s unary/SSE respectively). Generated script contents remain poor.

The fixture retains all 12 OMP tool schemas and validation assertions; descriptive
annotations are removed. Private prompts/HTTP headers are not committed.

## Acceptance limits

Both models completed a sandbox read-code/read-requirements/write/read-back chain
using real OMP read/write schemas including required i. Both generated incorrect
PowerShell venv scripts: task-quality acceptance is FAIL, despite protocol success.
No generated script or installation command ran. Unknown tools, malformed native
literals and invalid schema arguments remain non-executable.

This fixes the tested malformed-call generation path; it does not guarantee
that AUTO selects a tool, generates correct programs or follows every instruction.
Only the OMP maxLength/minItems/anyOf forms here are verified. Parallel=false
restricts calls inside an envelope; multiple separately generated envelopes still
face the unchanged retainer check. Complete pre-parser token ordering, sustained
load and universal agent/release acceptance are NOT_VERIFIED.

Reproduce focused tests with `rtk proxy python C:/gm/lfm-2026.4/malformed-fix-20261028/run-tests.py final`.
Original model/build pins were not overwritten. Candidate tests use loopback18147;
the pinned LFM2 control on8137 is restored after tests rather than silently promoted.

## Explicit deployment after user request

The user subsequently requested the corrected server on8137. It is now running
LFM2-24B as PID10404 with EXE SHA256
`b3440410a08c1a62d4f8aa187dffe3c64177c9729fa1249290e866c48e58e481`.
The repository and installed OMP LFM2 launcher defaults now pin that EXE (KV auto).
Smoke returned OK; a live AUTO get_status call, host result, and final ready
answer passed. Deployment evidence: hub `live-8137/`. Prior task-quality limits
remain applicable.
