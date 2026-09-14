# Intel GPU `CL_OUT_OF_RESOURCES` dossier for GEMMAMONSTER

Status vocabulary: `CONFIRMED`, `STRONGLY_SUPPORTED`, `OPEN`, `SUPERSEDED`, `REJECTED`.

## Executive finding

`CL_OUT_OF_RESOURCES` / OpenCL error `-5` must **not** be treated as a synonym for "the GPU ran out of total memory".

The OpenCL specification uses `CL_OUT_OF_RESOURCES` for failure to allocate resources required by the OpenCL implementation on the device. OpenVINO's own GPU error text explicitly calls out at least two major classes: genuine memory pressure and out-of-bounds GPU kernel access. OpenVINO history contains additional concrete root causes including register pressure, local/private-memory pressure, incorrect buffer sizing, invalid pitches/offsets, and driver/context corruption after a device fault.

For GEMMAMONSTER this changes the investigation target. The behavioral discriminator "many distinct structured grammars eventually kill the process while one repeatedly reused grammar survives" is real and valuable, but it does **not** prove that XGrammar compiler objects themselves leak memory. Distinct structured grammars may instead perturb prompt length/shape, matcher masks, tensor shapes, dispatch paths, or kernel/runtime state downstream of XGrammar.

## Project evidence to preserve

Current project findings:

1. The Gemma4 whitespace loop is an independent defect. Stock RC2 survived multiple whitespace-loop requests and later died from an unrelated `CL_OUT_OF_RESOURCES`. Therefore:
   - `WHITESPACE_LOOP_CAUSES_GPU_DEATH = DISPROVED`
   - bounded whitespace repair remains valid and should not be reverted.
2. A 60-request homogeneous structured-grammar workload can remain stable.
3. Heterogeneous/distinct grammar churn has produced fatal runs after roughly a few dozen successful distinct schemas; observed counts include approximately `31 / 24 / 24`.
4. XGrammar compiler cache enabled/disabled does not discriminate the failure. Cache-off can still die.
5. Rebuilt GenAI and stock RC2 can both reproduce the fatal OCL signature. `REBUILT_GENAI_IS_ROOT_CAUSE = SUPERSEDED`.
6. A known-good 2026.4 runtime handled real agentic loops without `CL_OUT_OF_RESOURCES`, but those workloads reused a small stable tool/schema set. That does not yet test distinct-schema churn.
7. Some earlier heterogeneous harness iterations generated inconsistent JSON Schemas. All future causal runs must assert recursively that every `required` member exists in the corresponding `properties` object.

The exact low-level mechanism is still `OPEN`.

## OpenCL semantics

Khronos `clFinish` documentation:

https://registry.khronos.org/OpenCL/specs/unified/refpages/man/html/clFinish.html

`CL_OUT_OF_RESOURCES` means the implementation failed to allocate resources required on the device. It is distinct from host-memory exhaustion.

The practical lesson is that global/free memory numbers alone cannot exonerate device-resource exhaustion. A workload can fail because a single required allocation, a kernel-local resource, a register/SLM budget, an address/pitch error, or another implementation resource cannot be satisfied.

## Closest public analogues

### A. Stock OVMS agent-style workload: delayed `clFinish -5`, then permanent executor wedge

OpenVINO Model Server issue #4469:

https://github.com/openvinotoolkit/model_server/issues/4469

This is the closest public system-level analogue found so far.

Reported properties:

- stock `openvino/model_server:2026.2-gpu` and `2026.3-gpu`;
- public Qwen3.5-9B INT8 model;
- VLM legacy pipeline;
- sustained agent-style workload;
- one request triggers `clFinish, error code: -5 CL_OUT_OF_RESOURCES`;
- after the fault the server process remains alive and the servable remains advertised as available, but the LLM executor no longer processes requests;
- only restart recovers the executor;
- kernel logs show an Xe engine reset and device coredump;
- increasing KV cache delays but does not eliminate the failure;
- apparently small changes in request/payload shape can remove the reproducer while comparable token-heavy workloads remain healthy.

Most important implication for GEMMAMONSTER:

`CL_OUT_OF_RESOURCES` can be strongly workload-shape/state dependent in stock OVMS. The failure need not be explained by our Gemma parser, our XGrammar update, or a simple monotonic model-memory leak.

### B. Gemma4 itself: multi-turn `CL_OUT_OF_RESOURCES`

OpenVINO issue #35723:

https://github.com/openvinotoolkit/openvino/issues/35723

Environment:

- Gemma4 E4B INT8;
- Intel Arc B580;
- OpenVINO 2026.2 nightly;
- GPU inference.

The model runs quickly, then fails with `CL_OUT_OF_RESOURCES` after several conversation turns. A newer nightly and lower token budget increase the number of turns before failure but do not eliminate it.

This is directly relevant to the planned GEMMAMONSTER hardening of smaller Gemma4 variants. E4B already has a public model-bound/multi-turn GPU failure history independent of our current Heretic parser work.

### C. Qwen3.5 VLMPipeline: failure scales with model shape rather than total memory

OpenVINO issue #36151:

https://github.com/openvinotoolkit/openvino/issues/36151

Reported properties include:

- iGPU;
- VLMPipeline;
- Qwen3.5 INT8;
- model successfully loaded with substantial shared memory remaining;
- failure threshold changes with `hidden_dim × seq_len`;
- INT4 and CPU variants survive cases where GPU INT8 fails;
- OpenVINO's own exception says `CL_OUT_OF_RESOURCES` is commonly either insufficient resources for the inference or an out-of-bounds kernel access.

This is strong evidence against equating error `-5` with total committed-memory exhaustion.

### D. Driver/context poisoning after the first fault

OpenVINO issue #32665:

https://github.com/openvinotoolkit/openvino/issues/32665

The report observes monotonic GPU memory growth and eventual `CL_OUT_OF_RESOURCES` under the Xe driver, followed by `CL_INVALID_EVENT` and hangs. The same workload is stable with i915. Resources are released after killing the process.

For GEMMAMONSTER this keeps "post-fault poisoned GPU/runtime state" as a separate hypothesis from the primary trigger. Runs after the first fatal device error must not be treated as equivalent to clean-reboot runs.

### E. Shared-state/concurrency corruption can surface as `CL_OUT_OF_RESOURCES`

OpenVINO issue #36458:

https://github.com/openvinotoolkit/openvino/issues/36458

Concurrent state reset/prefill behavior on Intel GPUs can corrupt shared state; a lock-step variant can surface as `CL_OUT_OF_RESOURCES`. This demonstrates that runtime lifecycle/state-management errors can map to the same OpenCL error code without being simple global-memory exhaustion.

## OpenVINO GPU fixes: root-cause taxonomy behind the same error

OpenVINO's own commit history is the strongest warning against treating `CL_OUT_OF_RESOURCES` as one bug class.

### 1. Out-of-bounds `ScatterUpdate` index -> memory corruption / driver crash

Commit:

`2f6e8b6d1c397adf3bdf695544635d2a80fd6fd6`

https://github.com/openvinotoolkit/openvino/commit/2f6e8b6d1c397adf3bdf695544635d2a80fd6fd6

Unchecked OCL scatter indices could silently corrupt memory; gross or negative OOB indices could surface as driver-level `CL_OUT_OF_RESOURCES`.

### 2. Incorrect crop/reshape padding -> bad packed-QKV offset/pitch

Commit:

`951cafd2128dbdf0d9df6ec8fb981d16d3329e69`

https://github.com/openvinotoolkit/openvino/commit/951cafd2128dbdf0d9df6ec8fb981d16d3329e69

A regression in in-place crop padding propagation through reshape produced incorrect offsets/pitches for packed QKV views and could produce wrong output or `CL_OUT_OF_RESOURCES`.

### 3. SDPA micro-prefetch bounds -> GenAI Llama `CL_OUT_OF_RESOURCES`

Commit:

`1c26dc7b64739af6cbf220457577685b4ef81694`

https://github.com/openvinotoolkit/openvino/commit/1c26dc7b64739af6cbf220457577685b4ef81694

OpenVINO explicitly states that corrected SDPA prefetch bounds avoid `CL_OUT_OF_RESOURCES` in a GenAI Llama benchmark.

### 4. GEMM K-leftover OOB read -> intermittent `clFinish` `CL_OUT_OF_RESOURCES`

Commit:

`993492c10f48a09ab0a9401d537d762e1788314f`

https://github.com/openvinotoolkit/openvino/commit/993492c10f48a09ab0a9401d537d762e1788314f

A vectorized GEMM load read beyond the valid K tail. The bug was always logically present but only faulted when the over-read hit an unmapped page. The externally visible symptom was intermittent `CL_OUT_OF_RESOURCES` at `clFinish`.

This is particularly important for interpreting GEMMAMONSTER: an intermittent `clFinish -5` after many successful requests can represent a latent bad GPU memory access, not accumulation to an OOM threshold.

### 5. Paged-attention OOB lane -> intermittent `CL_OUT_OF_RESOURCES`

Commit:

`e8ab30f96edaf966ac96d9835d9ffa08a8b65b61`

https://github.com/openvinotoolkit/openvino/commit/e8ab30f96edaf966ac96d9835d9ffa08a8b65b61

An invalid lane in the last partial target block could index `token_type_ids` out of range. The resulting dGPU failure appeared as intermittent `CL_OUT_OF_RESOURCES`.

### 6. Register/private-memory pressure -> `CL_OUT_OF_RESOURCES` with memory still available

Commit:

`26811446dc8de991d5ec365f93f2f68d3a0420c1`

https://github.com/openvinotoolkit/openvino/commit/26811446dc8de991d5ec365f93f2f68d3a0420c1

A 1D convolution kernel used enough private `line_cache` storage to consume the Xe-LPG register-file budget. Fused operations then required additional registers and the kernel failed with `CL_OUT_OF_RESOURCES`.

This is direct proof that the error may mean exhausted *execution resources* rather than exhausted global/device memory.

### 7. Kernel-build resource limit

Commit:

`b1d171dd1c5ed53128bb17716eaf7001038fd008`

https://github.com/openvinotoolkit/openvino/commit/b1d171dd1c5ed53128bb17716eaf7001038fd008

OpenVINO added logging specifically because generated OpenCL kernels can fail at build time with `CL_OUT_OF_RESOURCES` when they exceed device limits such as SLM/local-memory limits. Previous logging obscured the kernel build log for this error path.

### 8. Runtime dispatch/internal buffer sizing mismatch

Commit:

`d039da47f60d959e81d34dccb9425e35bcfefe78`

https://github.com/openvinotoolkit/openvino/commit/d039da47f60d959e81d34dccb9425e35bcfefe78

An ArgMax kernel used inconsistent internal-buffer sizing between initial kernel creation and runtime dispatch-update paths, producing `clFinish -5`.

### 9. Additional OOB examples

- `428e583a20d710f25b8aa153931aeb0451ea1e2b`: convolution OOB reads; Xe2+ produces `CL_OUT_OF_RESOURCES` where older devices can silently return zero.
- `feac04e7d7bad17f09bd01b11ef73d9919ad7825`: convolution OOB reads producing `CL_OUT_OF_RESOURCES`.
- `c4ce6e562a6e69d8f186f4b296c25b109bb91589`: non-aligned GEMM tile OOB memory access producing `CL_OUT_OF_RESOURCES`.

## Practical taxonomy for GEMMAMONSTER

When we see `CL_OUT_OF_RESOURCES`, classify candidate mechanisms into separate buckets:

### A. Genuine memory-capacity / allocation failure

Examples:

- model + KV cache + temporary buffers genuinely exceed allocable memory;
- one requested memory object exceeds the maximum single-allocation size;
- large allocation mode/addressing restrictions.

### B. Fragmentation or sub-pool limit

Total visible host/shared memory may remain large, while the GPU runtime cannot obtain one required allocation or satisfy a specific USM/device pool.

### C. Kernel execution-resource pressure

Examples:

- register/GRF exhaustion;
- SLM/local-memory limit;
- excessive private memory;
- generated kernel exceeds device resource limits.

### D. Invalid GPU memory access

Examples:

- OOB read/write;
- bad pitch/offset;
- bad dynamic-tail handling;
- invalid scatter index;
- partial-block lane error.

This class often becomes visible only at a synchronization point such as `clFinish`, so the failing API call is not necessarily the origin of the bad access.

### E. Incorrect runtime allocation/dispatch bookkeeping

A buffer may be correctly sized in one code path but incorrectly sized when the dynamic dispatch is updated.

### F. Lifecycle/state/concurrency failure

Shared compiled-model or infer-request state can become inconsistent and drive the GPU into an invalid dispatch or resource state.

### G. Post-fault driver/context poisoning

After the first device-fatal error, subsequent OpenCL calls may hang/fail. Treat all later observations on that GPU context as contaminated until a clean process or reboot establishes otherwise.

## GPU properties that must be captured in future runs

OpenVINO exposes useful Intel GPU properties:

https://docs.openvino.ai/2026/api/c_cpp_api/group__ov__runtime__ocl__gpu__prop__cpp__api.html

Capture at minimum:

- `GPU_DEVICE_TOTAL_MEM_SIZE`
- `GPU_DEVICE_MAX_ALLOC_MEM_SIZE`
- `GPU_MEMORY_STATISTICS`
- GPU architecture / execution-unit count
- supported USM capability

Important detail: on an iGPU, `GPU_DEVICE_TOTAL_MEM_SIZE` is reported from host memory size. It is **not** proof that an arbitrary device allocation of that size is possible. `GPU_DEVICE_MAX_ALLOC_MEM_SIZE` is the more relevant bound for a single memory object. `GPU_MEMORY_STATISTICS` gives allocation-type accounting (`cl_mem`, USM classes, etc.) and should be sampled around the reproducer.

OpenVINO also exposes `GPU_ENABLE_LARGE_ALLOCATIONS`; this bypasses the ordinary max-allocation check/addressing path for allocations above 4 GiB, but it should be used only as a diagnostic if evidence shows a single-allocation constraint. It is not a generic fix for the current failure.

## Implication for the 2026.4 -> 2026.5 chronology

Project chronology says the first GEMMAMONSTER `CL_OUT_OF_RESOURCES` incidents appeared after the 2026.5 stack entered the project, while the earlier `freeze/gemmamonster-2026.4-known-good` line was stable under its real agentic workload.

That chronology is important but not yet causal because the old known-good workload reused a small stable set of tools. It did not intentionally churn 100+ distinct schemas.

Therefore the cleanest release-line experiment is:

```text
A: exact early 2026.4 frozen known-good runtime
   branch: freeze/gemmamonster-2026.4-known-good
   source anchor: c48366fee1f10cdf6b5fe3c181522ed0c58fc9fd
   exact known-good runtime dependencies
   corrected VALID-HETERO-120 harness

B: exact 2026.5 frozen-gate runtime
   branch: integration/gemma4-protocol-hardening-2026.5
   semantic checkpoint: 52c6b534dab9cb2cb413eb175541870785cdd2c3
   docs head: 5d995cfafdb2ec90578678aa15714dedebc843b8
   its exact runtime dependencies
   identical VALID-HETERO-120 harness
```

Do not modify parser, chat template, XGrammar policy, or request semantics between A and B beyond what belongs to each historical stack.

Interpretation:

- 2026.4 passes / 2026.5 fails: regression window is real; bisect OpenVINO/GenAI/GPU-plugin/runtime delta.
- both fail at comparable distinct-schema count: latent structured/agentic workload bug predates the apparent 2026.5 chronology; known-good simply never exercised the trigger.
- both pass from clean boot: previous failures depended on contaminated GPU/runtime state or a different workload dimension.

The exact OpenVINO runtime SHA/package used by the historical 2026.5 frozen gate must be recovered from its runtime/build evidence before claiming an OpenVINO commit-level regression. The source branch alone only points at `C:\opt\openvino\runtime`; it does not establish the binary provenance.

## Diagnostics to add before another speculative fix

The next useful instrumentation should answer **which GPU/runtime operation actually precedes `clFinish -5`**.

Priority:

1. Enable Intel GPU/OpenVINO verbose kernel logging and preserve OpenCL build logs.
2. Record the last kernel/primitive/operation submitted before the fatal synchronization.
3. Capture `GPU_MEMORY_STATISTICS` and `GPU_DEVICE_MAX_ALLOC_MEM_SIZE` before every Nth distinct grammar and immediately before/after the failing request if possible.
4. Split GenAI structured-output instrumentation at least across:
   - grammar materialization;
   - XGrammar compile;
   - matcher creation;
   - token-mask creation/materialization;
   - OpenVINO tensor creation;
   - logits masking / inference submission.
5. Record exact schema fingerprint, prompt token count, generated-token count, request phase, and tool-choice mode.
6. On Linux/Xe, preserve GPU engine reset/coredump data when available. On Windows, capture the closest available Intel GPU/ETW/driver diagnostics.
7. After any device-fatal error, mark the runtime state `POISONED` and do not mix subsequent runs into clean causal evidence.

## Working conclusion

The strongest current conclusion is not "XGrammar leaks" and not "Arc 140V simply runs out of RAM".

It is:

> GEMMAMONSTER can drive the Intel GPU structured/agentic inference path into a device-fatal OpenCL `CL_OUT_OF_RESOURCES` state under heterogeneous workload churn. OpenVINO's public history shows the same surface error can be caused by OOB accesses, incorrect offsets/pitches, runtime buffer-sizing bugs, register/SLM pressure, genuine allocation limits, or poisoned GPU state. We must localize the last GPU primitive/allocation before fixing anything else.

The most valuable next comparison is exact frozen 2026.4 known-good vs exact frozen 2026.5 gate under the same corrected valid-schema churn workload, with GPU allocation/kernel diagnostics enabled.
