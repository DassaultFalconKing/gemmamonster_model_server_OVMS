# Empty-args repair: tests and incremental builds

Date: 2026-09-18

## 1. Minimal gate policy

Every stage gets only:
1. build;
2. focused tests;
3. live Gemma when runtime behavior changes.

Full suites wait until a candidate is worth promotion.

## 2. G0 forensic baseline

- worktree: C:\git\openvino-genai-emptyargs-test
- HEAD: a32f0fd827c51feb3d2e4294e7cbec9fa3c5b4b4
- XGrammar: f6043f4daafd0d018f77c3ec07bcfcd70b7e0532
- run only the two committed empty-required-args tests first.

## 3. Mutable GenAI repair worktree

Recommended source path:
C:\git\openvino-genai-token-repair

Recommended build root:
C:\o\openvino_genai_token_repair\build

Branch order:
1. test/xgrammar-accept-token-failclosed-20260918
2. test/xgrammar-tokenizer-info-plumbing-20260918
3. integration/xgrammar-token-runtime-hardening-20260918
4. feature/xgrammar-token-structural-tags-api-20260918
5. test/xgrammar-head-1de42473-compat-20260918

Configure once using the already proven G0 values:
- CMake 3.31;
- correct OpenVINO_DIR;
- correct Python3_ROOT_DIR;
- ENABLE_TESTS=ON;
- ENABLE_XGRAMMAR=ON;
- correct generator syntax.

Incremental target:
cmake --build C:\o\openvino_genai_token_repair\build --config Release --target tests_continuous_batching --parallel 16

Focused filters:
- F1: XGrammarLogitsTransformer.*
- F2: TokenAwareStructuralTagParser.*
- F5: TypedTokenStructuralTags.*
- common: StructuredOutputJSONSchema.*

XGrammar HEAD compatibility uses the same build root and exactly the same focused filters.

## 4. Runtime slot

F3/F4 Windows GenAI points to:
C:\git\gemma4-runtimes\TOKEN-REPAIR-ACTIVE\runtime

G2-X2 remains immutable C5 control.

## 5. Mutable OVMS worktree

Recommended:
C:\git\model_server-gemma4-token-repair

Branch order:
1. test/gemma4-token-trigger-ab-20260918
2. fix/gemma4-control-token-grammar-20260918

Focused Bazel tests:
- //src/test/llm/gemma4_generation:gemma4_generation_policy_test
- //src/test/llm/gemma4_generation:gemma4_whitespace_bound_test

Do not bazel clean between F3 and F4.

## 6. Live gates

F3:
- reproduce C5 guided-ON calculator{};
- F3 guided ON x20 with same model/prompt/temp;
- question: does token-triggered auto remove empty args?

F4 minimum:
- auto calculator x20;
- named calculator x10;
- required calculator x10;
- required reasoning->tool x10;
- streaming calculator x10;
- parallel false x5;
- parallel true x5.

Acceptance:
- zero schema-required empty argument objects;
- zero matcher desync errors;
- parser behavior preserved;
- parallel policy preserved.

## 7. XGrammar 1de42473 gate

Branch: test/xgrammar-head-1de42473-compat-20260918

Only:
1. incremental compile;
2. XGrammarLogitsTransformer.*;
3. TokenAwareStructuralTagParser.*;
4. TypedTokenStructuralTags.*;
5. StructuredOutputJSONSchema.*;
6. one short F4 live calculator run.

If all green: XGRAMMAR_HEAD_COMPAT=PASS.

## 8. Promotion

After F4 live is green:
- migrate F4 raw grammar builder to F5 typed API;
- add F5 Python/JS bindings;
- run full suites;
- freeze runtime hashes/SHAs;
- then consider replacing C5 XGrammar pin with 1de42473.