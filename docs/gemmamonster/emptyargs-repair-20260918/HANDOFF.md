# HANDOFF — F1→F5 token repair track (implementation session)

repo: DassaultFalconKing/openvino.genai (+ OVMS gemmamonster_model_server_OVMS)
frozen control: GenAI C5 15e8f897 / XGrammar f6043f4 / probe a32f0fd8
forensic worktree: C:\git\openvino-genai-emptyargs-test (DO NOT SWITCH)
forensic build: C:\o\openvino_genai_emptyargs\build (DO NOT REUSE for repairs)
immutable runtime: C:\git\gemma4-runtimes\G2-X2\runtime (DO NOT TOUCH)

## Repair branches (re-resolved 2026-09-18)

- F1 test/xgrammar-accept-token-failclosed-20260918 = fa43429a
- F2 test/xgrammar-tokenizer-info-plumbing-20260918 = b1f30bf1
- F1+F2 integration/xgrammar-token-runtime-hardening-20260918 = 0079ae07
- F5 feature/xgrammar-token-structural-tags-api-20260918 = 6cba6ba7
- XHEAD test/xgrammar-head-1de42473-compat-20260918 = 85c74552

## Standing rules

- Re-resolve upstream HEADs before every big step (GenAI master, XGrammar, OVMS main,
  fork branches). Record resolved SHAs in HANDOFF before building/rebasing/live.

## Mutable lanes

- GenAI worktree: C:\git\openvino-genai-token-repair @ integration 045f4456 (pushed; was F5 abe90176)
- GenAI build: C:\o\openvino_genai_token_repair\build (same root, incremental per branch)
- OVMS worktree: C:\git\model_server-gemma4-token-repair @ F3 91a92a29 (pushed; dist packaged+verified)
- Final runtime: C:\git\gemma4-runtimes\TOKEN-REPAIR-ACTIVE\runtime (DONE, manifest inside)

## Gates

- G0 forensic 2 tests + 6/6 group: PASS (exact a32f0fd8, XGrammar f6043f4 rev-parse verified,
  separate build root; evidence C5-frankenstein-newxgrammar/forensic-g0*.log).
  STATIC_GRAMMAR_SEMANTICS=EXONERATED confirmed on frozen control. No more AcceptString attribution tests.
- F1 XGrammarLogitsTransformer 2/2 + group 4/4: PASS (test-only TokenIds compat 06ca3508).
- F2 TokenAware 2/2 + group: PASS 6/6 on b1f30bf1.
- F5 C++ 8/8 PASS (visitor arm fix for TokenTriggeredTags in to_json).
  Python bindings 4/4 PASS (Token/AnyTokens/TokenTag/TokenTriggeredTags + py_obj arms;
  ExcludeToken NOT introduced: no standalone XGrammar counterpart, excludes ride in types).
  Stubs hand-updated (stubgen unavailable offline; format mirrors stubgen output).
  JS/TS types+factories added; tsc shows only the 36 pre-existing env errors (verified via stash).
  Commits: visitor-fix, TokenIds-qualify, python-bindings, js-types. F5 HEAD abe90176, pushed.
- GenAI pre-C6 integration: branch integration/gemma4-token-grammar-pre-c6-20260918 @ 045f4456
  created+pushed (XHEAD pin 1de42473 + 4 F5 commits, cherry-pick clean).
  Integration gates 10/10 PASS under XGrammar 1de42473 (TypedToken 2, TokenAware 2,
  StructuredOutput 4, XGrammarLogitsTransformer 2).
- Runtime slot TOKEN-REPAIR-ACTIVE: DONE. Dll 25204A61… (= fresh build output, verified),
  headers from integration worktree. Manifest inside slot.
- F3 build: PASS after WORKSPACE shadowing fix (91a92a29, pushed); focused 2/2 PASS;
  dist packaged+verified (ovms 73FC8651, genai 25204A61, --version confirms integration branch).
- F3 live A/B 20 runs: DONE. Treatment (token_triggered_tags): filled=0 empty=1 nocall=19
  (empty content, finish=stop, no server errors) vs C5 control 1/3/0 same prompt-temp.
  Verdict: token dispatch does NOT fire as wired — model emits nothing. Points at missing
  TokenizerInfo/plumbing at OVMS->GenAI boundary (F4 scope), NOT at matcher semantics
  (F1 rejects proven) and NOT at parser. F3 stays evidence-only, NOT merged, NOT promoted.
  Evidence C5-*/f3-ab-result.txt, f3-sample.json, f3-server.log. F3 server stopped after.
- F4 focused + live acceptance: NOT_RUN
- Full acceptance: NOT_RUN

## Current gate / next gate

- Last: F3 A/B complete (dispatch-missing verdict); F3 server stopped, host clean.
- Next: F4 (fix/gemma4-control-token-grammar-20260918): re-resolve HEAD, port to typed F5 API,
  equivalence test, focused tests, live acceptance matrix.
