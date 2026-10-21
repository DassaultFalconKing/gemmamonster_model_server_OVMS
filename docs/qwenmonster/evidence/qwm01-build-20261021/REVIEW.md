# Reviewed external findings

Worker: OpenCode 1.19.3, explicit model opencode/glm-5.3-flash-free.
Shell preflight executed the exact HEAD probe successfully. Independent review
owned stdout only and read sanitized public source snapshots. No source writes,
builds or live test claims were delegated. Exact session identities: RESULTS.json.

- R1 (required key absent from properties): reproduced in BOTH baseline and #802
  libraries. The XML converter accepts empty arguments despite required:[a].
  This is an inherited grammar/profile gap, not demonstrated #802 regression.
  Keep OPEN; output validator still rejects missing required executable arguments.
- R2 (max_properties sentinel): rejected after source inspection:
  ObjectSpec::max_properties defaults to -1. Explicit required-property native
  positive and empty-negative controls pass with both libraries. No code fix.
- R3 (epsilon might leave undefined rule): runtime grammar compilation, 29 native
  assertions and hard/lazy actual-vocabulary masks pass. Concern not reproduced.
- R4 (new Bazel dependency could be attached to wrong target): full BUILD source
  confirms it is on openai_api_handler and the parser target. Dependency placement
  is correct; HTTP handler compile/link remains UNVERIFIED due environment blocker.
- R5 (stricter request compatibility): expected QWM-01 contract, retained in
  implementation handoff. Unsupported schemas and omitted parameters are intended
  request errors. Actual HTTP400 mapping NOT RUN.

Review findings are inputs, not acceptance authority. No speculative reviewer
suggestion was applied without source/runtime verification.
