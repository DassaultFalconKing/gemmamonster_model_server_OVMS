# Gemma4 empty-args repair track

Date: 2026-09-18

## 1. Attribution

- parser: EXONERATED; raw calculator{} is faithfully transported;
- schema ingestion: EXONERATED; required fields survive builder serialization;
- model-native propensity: not primary; guided OFF is stable while guided ON regresses;
- active suspect: token-level guided-generation runtime path.

Working hypothesis:

Gemma4 control token -> string TriggeredTags -> token/FSM divergence -> ignored AcceptToken(false) -> grammar runtime can fail open.

## 2. Repair stack

F1 — fail closed on matcher rejection
- repo: DassaultFalconKing/openvino.genai
- branch: test/xgrammar-accept-token-failclosed-20260918
- HEAD: fa43429a3e732a9676f4111d048876554415bd33
- checks GrammarMatcher::AcceptToken() and fails request on rejection.

F2 — tokenizer-aware structural tags
- branch: test/xgrammar-tokenizer-info-plumbing-20260918
- HEAD: b1f30bf13a104bfbec03e03bb56f7f1bac21c5cd
- retains TokenizerInfo and passes it into Grammar::FromStructuralTag;
- enables string references to real special-token IDs.

F1+F2 integration
- branch: integration/xgrammar-token-runtime-hardening-20260918
- HEAD: 0079ae07036a2411c9a235424e155a9456acbfee

F3 — Gemma4 auto A/B
- repo: DassaultFalconKing/gemmamonster_model_server_OVMS
- branch: test/gemma4-token-trigger-ab-20260918
- HEAD: ebc641a4d82cd5a7364330d5eced1c33cf8771e4
- only auto changes from string TriggeredTags to token_triggered_tags;
- schema bytes and max_whitespace_cnt=2 remain unchanged;
- named/required remain controls.

F4 — complete Gemma4 control-token grammar
- branch: fix/gemma4-control-token-grammar-20260918
- code HEAD before docs: c8d06a28445743f12c79fab66786d3e121508293
- auto: token trigger + token tool opener/closer;
- required/named: token-boundary tags inside existing tags_with_separator semantics;
- reasoning-to-tool: Token(<|channel>) + literal thought\n + AnyTokens + Token(<channel|>);
- parallel/stop-after-first semantics preserved;
- guard forbids returning control markers to string tag boundaries.

F5 — typed GenAI token structural API
- branch: feature/xgrammar-token-structural-tags-api-20260918
- HEAD: 6cba6ba789b527286b6f867be16c7522d2569e4e
- types: Token, AnyTokens, TokenTag, TokenTriggeredTags;
- existing string Tag remains source-compatible;
- C++ compile/replay gate first; Python/JS bindings after that.

## 3. XGrammar upstream HEAD compatibility

- C5 pin: f6043f4daafd0d018f77c3ec07bcfcd70b7e0532
- upstream HEAD under test: 1de42473b51ca176ab24aa0b5f434b293503e4a9
- delta: exactly 3 commits ahead;
- no public XGrammar include/header changes in compare;
- semantic delta mainly 38b97c0 matcher/mask and schema correctness/performance;
- compatibility branch: test/xgrammar-head-1de42473-compat-20260918
- HEAD: 85c74552a74255b70f87f86db85acc806c523558
- only stack change is XGrammar pin bump.

Rule: attribution stays on pinned C5 XGrammar; HEAD compatibility is a separate build/test/live gate.

## 4. Frozen controls

- OVMS C5: a671ddf9f10f31a8afda849b44400291c35148ea
- GenAI C5: 15e8f897c19154294c6d00a518a2bb28d99905df
- XGrammar C5: f6043f4daafd0d018f77c3ec07bcfcd70b7e0532
- baseline probe: a32f0fd827c51feb3d2e4294e7cbec9fa3c5b4b4
- do not mutate C:\git\openvino-genai-emptyargs-test
- do not mutate C:\o\openvino_genai_emptyargs\build
- do not mutate C:\git\gemma4-runtimes\G2-X2\runtime
- repair runtime slot: C:\git\gemma4-runtimes\TOKEN-REPAIR-ACTIVE\runtime