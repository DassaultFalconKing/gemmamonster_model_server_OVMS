# Handoff — Gemma4 empty-args repair

Date: 2026-09-18

Current baseline build:
- C:\git\openvino-genai-emptyargs-test
- HEAD a32f0fd8
- XGrammar f6043f4
- do not modify while G0 runs.

GenAI branches:
- F1 test/xgrammar-accept-token-failclosed-20260918 @ fa43429a3e73
- F2 test/xgrammar-tokenizer-info-plumbing-20260918 @ b1f30bf13a10
- integration/xgrammar-token-runtime-hardening-20260918 @ 0079ae07036a
- F5 feature/xgrammar-token-structural-tags-api-20260918 @ 6cba6ba789b5
- XGrammar HEAD compat test/xgrammar-head-1de42473-compat-20260918 @ 85c74552a742

OVMS branches:
- F3 test/gemma4-token-trigger-ab-20260918 @ ebc641a4d82c
- F4 fix/gemma4-control-token-grammar-20260918 @ this documentation commit

Execution order:
1. collect G0 result;
2. F1 focused build/test;
3. F2 focused build/test;
4. integration focused build/test;
5. stage TOKEN-REPAIR-ACTIVE;
6. F3 build/test/live A-B;
7. F4 build/test/live;
8. F5 C++ typed API build/test;
9. XGrammar 1de42473 compatibility build/test/live;
10. migrate F4 raw grammar to F5 typed API.

Stop only on concrete evidence:
- F1 catches AcceptToken(false);
- F2 cannot resolve real special token;
- F3 still emits calculator{} with synchronized matcher;
- XGrammar HEAD changes focused behavior.

Otherwise continue down the ladder. Do not reopen parser work.