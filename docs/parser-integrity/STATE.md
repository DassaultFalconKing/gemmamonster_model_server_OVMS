# RLC + TLP-H state and evidence ledger

Last updated: 2026-10-24.
ACTIVE_STAGE: **DOCS_BASELINE_CREATED**.
ACCEPTED: **NO**. MERGE_AUTHORIZATION: **NO**.
WORK_BRANCH: `docs/rlc-tlp-h-20261024`.
BASE_REF: `feature/minicpm-v47-arc140v-eval-20261023` (MFP-1 / A3.1 reference).
RUNNING_PRODUCTION_CHANGED: **NO**.
SOURCE_PATCHES_ON_THIS_BRANCH: **NONE**.
TEST_CASES_ADDED_TO_SOURCE_ON_THIS_BRANCH: **NONE**. The document [TEST-MATRIX.md](TEST-MATRIX.md) specifies test cases for incremental implementation.
LAST_GREEN_TESTS_ON_THIS_BRANCH: **NONE; NOT_RUN**.
LIVE_STATUS: **NOT_RUN**.
NEXT_ACTION: on an isolated implementation worktree, pin exact source commit and tokenizer/template/runtime identities, add first RLC R0 and TLP T0 source fixtures as individual test-only commits, capture RED (or NOT_REPRODUCED) before minimal fixes. Do not claim new acceptance from docs.

## Existing evidence, not re-executed here

- The source-based audit identified potential Qwen3 first-entry prefix loss, Gemma4 ambiguous one-line channel-header stripping, GPT-OSS opening-chunk loss and streamer phase-boundary risks. These are **candidates**, not observed RED from this branch.
- Previous Qwen3Coder lossless test receipt (2026-10-23) reports focused 34/34 and `*Qwen3Coder*` 81/81, overlapping test groups, plus successful test/server builds on its pinned environment. It does **not** establish that this branch's binary was tested, or live model/tool API acceptance.
- Current family adaptation protocol is [MFP-1](../qwenmonster/OVMS-MODEL-FAMILY-ADAPTATION-PROTOCOL.md); Gemma and Qwen have different native handoff rules.
- MiniCPM-V4.7 evaluation in this base branch was memory-blocked; this documentation program makes no new MiniCPM execution claims.

## Independent work packages

| Packet | Owner scope | Status | Test injection rule |
| --- | --- | --- | --- |
| RLC-R0 / RLC-R1 | Reasoning parsers + streamer seam | SPECIFIED / NOT_RUN | 2–5 focused fixtures per touched behavior plus existing family negatives |
| TLP-T0 | Qwen reference and new negative controls | SPECIFIED / NOT_RUN | Preserve 2026-10-23 receipts separately; rerun on actual source checkout |
| TLP-T1 | One tool parser family at a time | SPECIFIED / NOT_RUN | Raw-argument exactness, rejection, split invariant, lifecycle per patch |
| RLC-I / TLP-I / MIX-I | HTTP/SSE & cross-phase | NOT_RUN | Gate only after actual parser-focused unit evidence |
| LIVE-I | Machine & model runtime | NOT_RUN | Explicit authorization + exact runtime provenance |

## Update this ledger after every implementation packet

~~~text
DATE:
IMPLEMENTATION_BRANCH:
BASE_SHA:
CURRENT_HEAD:
CHANGESET / TEST_IDS:
NATIVE_MODEL_TEMPLATE_AND_TOKENIZER:
RAW_FIXTURE_SOURCE: SYNTHETIC | CAPTURED_MODEL
EXPECTED:
OBSERVED_BEFORE / RED_EVIDENCE:
TEST_COMMAND:
EXIT_CODE:
PASS_FAIL_COUNTS:
BUILD_AND_BINARY_IDENTITY:
STATUS: SPECIFIED | RED_OBSERVED | NOT_REPRODUCED | FIXED_UNIT_GREEN | INTEGRATION_GREEN | LIVE_GREEN | BLOCKED
REGRESSION_CONTROLS:
NEXT_ACTION:
ROLLBACK_POINT:
~~~

Documentation patches alone are not acceptance evidence. Keep implementation stage separate from this documentation-branch checkpoint.
