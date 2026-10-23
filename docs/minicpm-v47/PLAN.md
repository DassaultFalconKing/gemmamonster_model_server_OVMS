# MiniCPM-V 4.7 isolated evaluation

Goal: evaluate the supplied checkpoint without changing the accepted runtime.
Base: eb76a74f7aa39573d452d95443e189b1f5f4d9e8.
Branch: feature/minicpm-v47-arc140v-eval-20261023.

1. Record file hashes, download revision, IR interfaces and architecture, host memory and driver. Keep physical paths and full process details in private evidence.
2. Create uv environments: pinned SDK Python bindings with process-local DLL search paths, then independent latest packages if pinned fails.
3. Probe Core/GPU and read every actual IR; retain separate results. Pinned unsupported-model dispatch can be tested without allocating the language graph.
4. Gate compilation on free RAM >= total BIN bytes + 3 GiB and absence of another inference worker. This is a conservative experiment admission policy, not a measured model peak or physical impossibility claim. Stop on insufficient memory; do not evict/stop other applications.
5. Only after text correctness, run image fixtures, then bounded video and performance. C1, 512/2048 tokens, 128 generated tokens, 1 warmup + 3 timed runs. Do not report unexecuted metrics.
6. Inspect native template and exact frozen parser/OVMS boundaries. Static agreement is not native parser RED/GREEN or deployment acceptance.
7. Publish sanitized evidence and separate verdicts in atomic feature-only commits.

Files: scripts/minicpm-v47/evaluate.py; docs/minicpm-v47/{STATE,MODEL-IDENTITY,COMPATIBILITY-MATRIX,TOOL-PROTOCOL-FIT,FINAL-REPORT}.md; docs/minicpm-v47/evidence/*.json.
No product source edits, builds, deployment, model mutation, or shared-cache writes.
