# GEMMAMONSTER runtime archaeology: 2026.4 known-good to 2026.5 / RC2

Status vocabulary used below: `CONFIRMED`, `STRONGLY_SUPPORTED`, `OPEN`, `SUPERSEDED`.

## Purpose

This note preserves the repository and runtime archaeology needed to reason about the Gemma4 tool-calling stack and the later `CL_OUT_OF_RESOURCES` failures without collapsing multiple eras into one "known-good" label.

The important distinction is that GEMMAMONSTER had an earlier **2026.4 frozen known-good runtime line** before the later, much larger parser/protocol hardening and before the 2026.5 frozen gate.

## Verified branch / commit timeline

### 1. Early 2026.4 integration candidate

Branch:

`integration/gemma4-2026.4-rc1-candidate`

Verified HEAD:

`e894bac71dc02616a68b669af7445a0f8fdb3361`

This is the base from which the later frozen 2026.4 known-good line is directly descended. GitHub compare reports the frozen known-good HEAD as 95 commits ahead and 0 behind this commit.

### 2. Early 2026.4 contiguous integration line

Branch:

`integration/gemma4-2026.4-rc1-contiguous`

Verified HEAD:

`0a537f08987a3df4c0254c1614162c06ac20b968`

HEAD message:

`fix: let tool start terminate open reasoning phase`

This belongs to the early 2026.4 integration era, before the later 2026.5 protocol-hardening gate.

### 3. Frozen 2026.4 known-good runtime

Branch:

`freeze/gemmamonster-2026.4-known-good`

Verified HEAD:

`c48366fee1f10cdf6b5fe3c181522ed0c58fc9fd`

Immediate parent:

`73419fca131afc7389e493cf3f2bbb7ef7ac8ec6`

Important merge message at `73419fca...`:

`merge: integrate complete Gemma4 runtime and harness work`

Another nearby runtime commit:

`202d5e898d86af6dffd5e53fdc4e875f9de4ebed`

`fix(gemma4): refresh tool matrix near generation turn`

This branch is the best repository anchor for the **earlier successful 2026.4 runtime candidate**, before the later large parser/protocol hardening campaigns.

Runtime history associated with this era includes real agentic loops using a small stable set of tool definitions. No `CL_OUT_OF_RESOURCES` failure was observed in that known-good workload.

### 4. Later semantic/tool-calling known-good

Commit:

`9a1626260614f68a6282b6799842d5152f0dcdff`

This is a later semantic/tool-calling known-good used heavily in subsequent comparisons.

Important: it must not be confused with the earlier frozen 2026.4 runtime line above. GitHub history shows the two lines diverged from an older common base rather than one simply being a label on the other.

### 5. Frozen 2026.5 protocol-hardening gate

Branch:

`integration/gemma4-protocol-hardening-2026.5`

Verified docs HEAD:

`5d995cfafdb2ec90578678aa15714dedebc843b8`

Immediate parent / semantic checkpoint:

`52c6b534dab9cb2cb413eb175541870785cdd2c3`

This is later than the frozen 2026.4 known-good and represents the 2026.5 forward-port / protocol-hardening era.

Session history places the first observed `CL_OUT_OF_RESOURCES` failures in the project after the 2026.5 stack entered the GEMMAMONSTER line. This is a chronology fact, not yet a root-cause attribution to one particular 2026.5 component.

### 6. RC2 source and later whitespace repair

RC2 source under acceptance:

`908d669563f57535ab4eb747989e9ab33dfd5267`

Whitespace-loop repair product branch:

`fix/gemma4-whitespace-loop-20260914`

Initial repair HEAD:

`170644006a5334cb971b05824e4a8c95b495c4e2`

Later diagnostics/cache-control work advanced the product line to:

`52a32a8d3...`

The whitespace repair itself remained intact while cache diagnostics and cache-off control were added.

Current evidence branch:

`docs/rc2-acceptance-20260914`

As of the stock grammar-churn evidence commit:

`d0ed9765d1d48c93ac71628402791cd2f99fb31c`

Commit message:

`docs(rc2): record stock grammar-churn GPU exhaustion`

## Dependency archaeology

### OpenVINO GenAI 2026.4

GenAI commit used in the 2026.4 family:

`7ea2546852a382cd16bd22dea0cfad2db70ed744`

Its build configuration pins:

`XGrammar v0.1.31`

### OpenVINO GenAI 2026.5

GenAI commit used in the investigated 2026.5 family:

`2e3b291a30e84fa067b042e35b8826d18d273882`

It also pins:

`XGrammar v0.1.31`

Therefore OpenVINO GenAI did **not** advance the XGrammar pin between the investigated 2026.4 and 2026.5 stacks.

### GEMMAMONSTER whitespace-repair stack

The whitespace-repair experiment deliberately advanced XGrammar to:

`9aa840b6d16abf094f3e8e2ac9c10465b77656c9`

and patched the GenAI structured-output interface so Gemma4 tool schemas can carry a bounded whitespace setting (`max_whitespace_cnt=2`).

This modern XGrammar jump is important for the whitespace repair, but later evidence shows it is **not sufficient to explain `CL_OUT_OF_RESOURCES` by itself**, because stock RC2 can reproduce the same fatal OCL error under distinct-grammar churn.

## Failure archaeology

### Whitespace loop

Root behavior:

`<|tool_call>call:<tool>{` followed by repeated insignificant whitespace until token budget exhaustion.

Status:

`CONFIRMED` as an independent model/grammar liveness defect.

Repair:

bounded whitespace in the structural grammar.

The repair works functionally.

Stock RC2 later reproduced whitespace loops during churn and survived them, proving:

`WHITESPACE_LOOP_CAUSES_GPU_DEATH = DISPROVED`

### `CL_OUT_OF_RESOURCES`

Observed fatal signature:

- oneDNN / OpenCL path
- `CL_OUT_OF_RESOURCES`
- OCL `errcode -5`
- executor/process death or quarantine

Important discriminators accumulated so far:

1. Homogeneous repeated grammar workload can run 60/60 clean.
2. Distinct grammar churn repeatedly reaches a fatal state after roughly a few dozen distinct compilations.
3. Observed successful-distinct counts before fatal failure include approximately `31 / 24 / 24` across different runs/builds.
4. Cache-enabled and cache-off builds both fail, so retained XGrammar compiler cache is not a necessary cause.
5. Rebuilt GenAI and stock RC2 can both fail, so `rebuilt GenAI is the root cause` is `SUPERSEDED`.
6. Stock RC2 can survive multiple whitespace loops and then later die from `CL_OUT_OF_RESOURCES`, separating the two bug classes.
7. The frozen 2026.4 known-good workload used a small stable set of tool schemas, so long-running agentic loops there do not contradict a distinct-grammar-churn problem.

Current strongest behavioral predictor:

`number / lifecycle of distinct structured-grammar constructions in the lifetime of the runtime / GPU resource state`

Exact mechanism remains `OPEN`.

Candidate mechanisms include:

- transient high-water allocation while materializing a new grammar/matcher;
- downstream matcher / logits-mask / tensor lifecycle rather than XGrammar compiler cache itself;
- GPU/USM sub-pool fragmentation;
- deferred GPU resource destruction;
- single-allocation or sub-pool limits that are much smaller than total visible shared memory;
- poisoned long-lived GPU/runtime state after a prior fatal allocation.

## Superseded conclusions preserved explicitly

### `rebuilt GenAI is guilty`

`SUPERSEDED`

Reason: stock RC2 later reproduced the same fatal `CL_OUT_OF_RESOURCES` signature under grammar churn.

### `XGrammar compiler cache accumulation is the root cause`

`REJECTED` as a necessary cause.

Reason: cache-off control still died, and died at a similar distinct-schema count.

### `whitespace loop causes CL_OUT_OF_RESOURCES`

`DISPROVED`

Reason: stock RC2 survived multiple whitespace-loop requests and continued serving before a later independent OCL failure.

## Current clean discriminator

The remaining high-value discriminator is:

1. reboot / clean GPU state;
2. stock RC2 / stock GenAI / stock XGrammar;
3. corrected VALID heterogeneous schema harness;
4. 120 distinct grammar requests;
5. no rebuilt DLLs and no modern XGrammar in this control.

Interpretation:

- If clean stock again dies after roughly 20-35 distinct grammar constructions, distinct-grammar accumulation/lifecycle becomes `CONFIRMED` at the behavioral level, while the exact allocation mechanism remains open.
- If clean stock completes 120/120, dirty/poisoned GPU/runtime state becomes necessary to explain the earlier stock death and the simple per-compile accumulation theory is weakened.

## Why the branch distinction matters

For future forward-port archaeology, use the following names deliberately:

```text
EARLY WORKING 2026.4 RUNTIME
freeze/gemmamonster-2026.4-known-good
c48366fee1f10cdf6b5fe3c181522ed0c58fc9fd

LATER SEMANTIC / TOOL-CALLING KNOWN-GOOD
9a1626260614f68a6282b6799842d5152f0dcdff

2026.5 FROZEN PROTOCOL-HARDENING GATE
integration/gemma4-protocol-hardening-2026.5
52c6b534... semantic checkpoint
5d995cfa... docs head

RC2 ACCEPTANCE SOURCE
908d669563f57535ab4eb747989e9ab33dfd5267

WHITESPACE-REPAIR PRODUCT LINE
170644006... and descendants
```

Do not collapse these into one generic "known-good" baseline. They answer different regression questions.
