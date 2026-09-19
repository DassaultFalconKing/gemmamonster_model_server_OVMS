# Worklog Session

SESSION_ID: 2026-09-12-b-parity-build-acceptance-plan
AGENT: ChatGPT GPT-5.6 Sol
DATE: 2026-09-12
TASK: Convert RC1 forensic findings, semantic-refit lineage and current OpenVINO/OVMS performance evidence into a causal B-PARITY build recipe and a separate acceptance/tuning ladder.
BRANCH: integration/gemmamonster-rc2-semantic-refit-20260912

## Findings

- RC1 build parity must preserve Bazel 6.4.0/C:\opt, Python 3.12.10, MSVC 14.44.35207, exact 2026.4 RC2 dependency pins and the three-file build patch, without attributing speed causally to that patch.
- Build tuning and runtime tuning must be separated. One immutable B-PARITY package is the input to all performance profiles.
- Exact OpenVINO `227c337...` contains Intel GPU INT4/U4 KV cache support for Paged Attention.
- Exact OVMS/GenAI line supports generic plugin config plus scheduler controls including max_num_batched_tokens, dynamic_split_fuse and prefix caching; exact 2026.4 prefix-caching default is false.
- Dedicated Gemma4 test targets exist under `src/test/llm/gemma4_fast` and `src/test/llm/gemma4_overlay`.

## Decisions

- Build agent does NOT enable U4 KV, prefix caching, scheduler changes or driver changes.
- Test agent establishes P0 semantic correctness first, then tests P1 U4, P2/P3 batched-token values, P4 prefix caching, and optional P5 DSF A/B, using a fresh process per profile.
- Keep driver 32.0.101.8991 for the causal ladder.
- Prefix caching is rejected for promotion if it produces reproducible zero-token or corrupted continuation behavior.

## Files added/updated

- `docs/gemmamonster/RC2-B-PARITY-BUILD-RUNBOOK-20260912.md`
- `docs/gemmamonster/RC2-B-PARITY-ACCEPTANCE-RUNBOOK-20260912.md`
- `agent-worklog/CURRENT.md`
- this session record

## Verification state

- Repository/source capabilities were verified by reading exact branch/OpenVINO/GenAI source and BUILD files.
- Current OpenVINO documentation was used only as supplemental tuning guidance; exact pinned source governs capability/default claims.
- No Windows tests, build, package or runtime acceptance were executed in this chat environment.

## Handoff

Builder: use the pinned build runbook only, return one immutable package and provenance record.
Tester: after the package exists, use the pinned acceptance runbook; never rebuild or patch source during profile comparison.