# LFM agent continuation: bounded follow-up, 2026-10-27

Source: `055b5814431b15e65880520c56f9b34d99912113`, branch
`review/lfm25-design-c-semantic-refit-20261027`.
Evidence: `C:\gm\lfm-2026.4\agent-followup-20261027`.
Validation was performed locally before publication. Existing `/wd6313`, command
receipts and handoff documents were already dirty and are preserved in the
separate cleanup-state commit.

## State fixed for review

| Component | Verified behavior / boundary |
|---|---|
| LFM executable | Cleanup pin `d7ec623dbd82dae2f5e80f66c4446a7b650e086f3c7cc6da4806fa5aa68a4c3d`; no rebuild |
| Test executable | `52ecc4e41a4356d5364965b5245125c9480f593a602f331b10d8fa724c6e2ba0` |
| Parser | Native envelopes only; validates registry/schema; preserves argument spelling; prose pseudo-tools remain non-executable |
| `auto` | Unconstrained generation, including with guidance enabled; can produce prose instead of tools |
| `required` / named | Whole native-envelope grammar; hard validation; named restricts tool selection |
| Final response | Release tool constraint with `none` once known mandatory actions have completed |
| Model | LFM2.5-8B-A1B INT4, existing port18147 staging, GPU LM, OFFLOAD_RATIO=0, KV auto, prefix cache off |
| Isolation | Owned server on loopback 18147 only; historical pin, model staging, port8137 and CIB2 untouched |

Fresh parser/policy gate: **48 PASS / 2 expected SKIP / 0 FAIL** (50 scheduled).
See `parser-policy-baseline.xml` and `.log`. This includes generation-policy
tests missing from the previous handoff's broad parser filter.
Parser and server generation-builder source have **not** been modified: the
observed failures do not demonstrate a lost valid native call or a terminal-drain bug.

## Reclassified historical failures

Original official profile: 6/10 unary and 6/10 SSE. Direct inspection of the
eight failed slots gives the same classes in both transports:

| Repeat / seed | Actual cause |
|---|---|
| 1 / 1235 | Prose pseudo-tools; no executable calls |
| 3 / 1237 | Invented narrative without calls |
| 5 / 1239 | Only `cwd` executed; model generated an invalid/misspelled absolute path; host raised before `write` or `read` executed |
| 8 / 1242 | `stop` inside reasoning with empty visible content; no executed tools |

Thus repeat5 is **not** evidence of stopping after two successfully executed
tools. The old summary's unary `native_in_raw=true` is also insufficient:
marker strings quoted inside reasoning are not executable tool calls.
Exact per-response finish reasons and native-call counts are saved in
`historical-failure-taxonomy.json`.

The Gemma memory described a separate terminal/drain failure involving partial
markers. It motivated checking continuation, but is not evidence that this LFM
failure shares its cause. No Gemma code was changed.

## Reproduced RED and implemented correction

Two acceptance regressions were observed before changing the harness:

* `test_empty_final_is_failure_after_three_successful_tools`: FAIL; old harness accepted whitespace final.
* `test_length_final_is_failure_even_with_visible_content`: FAIL; old harness accepted truncated final.

The valid-final control passed. After correction, all seven harness tests pass.
`RED-GREEN.md` records the observed failing cases; `harness-regression.log`
records the final run. Additional tests cover path
normalization, sandbox rejection, returning a failed tool's result with its
original call ID and subsequent recovery, and three complete user rounds with
history retained and constraints released for every final.

Changes in `scripts/windows/lfm-agent-loop.py`:

* Require successful expected actions, exact file bytes, visible expected result,
  `finish_reason=stop`, and SSE `[DONE]`; failures return nonzero process status.
* Return tool execution errors as `role=tool` results with matching call IDs;
  allow bounded correction rather than abandoning the conversation.
* Normalize equivalent absolute/forward-slash sandbox paths; keep access bounded
  to `hello.txt`. Clarify the real tool descriptions to request relative paths.
* Add `--conversation-rounds`: retain the entire transcript across user requests.
  Round1 is `cwd -> write -> read -> final`; subsequent rounds are
  `read -> write -> read -> final`, with new content revisions.
* Add opt-in `action-named` for workflows whose next mandatory tool is known.
  Extend existing `action-required` to every user round. Both release the
  constraint with `none` for the final. Default `auto` is unchanged.

`action-named` is a directed workflow test, not evidence of autonomous planning.
`required` lets the model choose among the registered tools. Neither profile
should force tools on arbitrary conversation turns that need no action.

## Real-agent validation

All new conversations use real HTTP requests, host filesystem operations,
returned tool results, 2048 output-token budget per request, and saved raw
unary/SSE transcripts. Seeds are 1234 and 1235 unless n=1.
Official sampling is temperature0.2/top_k80/repetition_penalty1.05.

The first named-policy test passed **2/2 conversations**, each with **3 user
rounds and 9 successful tool calls**, including content after the second call,
after all tool results, and renewed work after a final answer.

Two independent clients (`multiturn-required` and `multiturn-auto-after`) ran
against the same owned endpoint with isolated sandboxes. Server log entries
`All requests: 2` confirm overlapping requests. This is a bounded overlap check,
not a throughput, fairness or sustained-load acceptance claim.

Final score table is recorded in `SUMMARY.json`; all run directories contain
`RESULT.json` plus per-turn request/response files. `multiturn-auto` is an
earlier native-prompt/parallel=false negative control: invalid paths and a
parallel-policy violation (HTTP400 / incomplete SSE) were correctly rejected.
The native-prompt variant is scored separately because it changes the prompt.

| Run | Conversation PASS | Scope |
|---|---:|---|
| Initial official auto baseline | 2/2 | One user round; old acceptance criterion |
| Named, serial tools | 2/2 | Three user rounds, nine tools each |
| Required, serial tools | 4/4 | Three user rounds, nine tools each; two seeds, unary+SSE |
| Official auto, parallel allowed | 2/4 | Seed1235 emitted narrative/code-fenced pseudo-tools in both transports |
| Native prompt, parallel allowed | 1/4 | Skipped requested pre-edit read in unary seed1234; seed1235 failed to call tools |
| Earlier native prompt, parallel forbidden | 0/4 | Negative control; wrong path / parallel-policy violation |

Successful required runs comprise **12 completed user rounds and 36 successful
tool calls**. Failures are retained, not retried until a passing seed is found.

## Reproduce

With the hash-pinned cleanup server already running on loopback18147:

```powershell
rtk proxy python scripts/windows/test_lfm_agent_loop.py
rtk proxy python scripts/windows/lfm-agent-loop.py --url http://127.0.0.1:18147/v3/chat/completions --output C:/gm/lfm-2026.4/agent-followup-repro --profile official --tool-policy action-required --conversation-rounds 3 --repeats 2 --no-parallel-tool-calls --max-tokens 2048
```

Use a new output directory for each run. `server-receipt.json` records the exact
server command and owned PID. `SUMMARY.json` records final source hashes and
binary hash; `lfm-agent-loop.final.py` preserves the final harness snapshot.
The named run precedes the path/error-handling changes. The required/auto
clients loaded the intermediate harness before the final exit-status/prefix
guard edits; those edits are covered by the final seven offline tests. No
claim is made that their in-memory Python code had the final file hash.

## Acceptance boundary

Parser/policy gate and bounded directed continuation are verified. `auto`
still has model-origin instruction-following failures and must remain
**CONDITIONAL** for autonomous harnesses. A parser cannot safely turn narrative
or quoted reasoning into executable actions. No unconditional model/agent
release acceptance, new loaded-DLL attribution, LFM2-24B retest, Gemma fix,
new product build is claimed. Publication and live serving are separate from
these acceptance results.

Owned server PID33328 was stopped at the end; see `server-stop.json`. Port18147
was checked free after shutdown. Existing source/build pins remain unchanged.
