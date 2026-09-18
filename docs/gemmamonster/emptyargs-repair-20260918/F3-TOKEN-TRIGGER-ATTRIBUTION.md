# F3 evidence freeze + token-trigger attribution verdict (2026-09-18)

F3 branch: test/gemma4-token-trigger-ab-20260918 @ 91a92a29 (pushed; dist ovms 73FC8651).
TOKEN-REPAIR-ACTIVE slot: GenAI 045f4456 / XGrammar 1de42473 /
dll 25204A61FAE4957075622AFC29D2DEB7612EEEF29892919E9A28AAA32474C205 (manifest inside slot).
No parser changes. No reverts (F1/F2/F5 intact). XGrammar untouched by this probe.

## Frozen evidence (C5-frankenstein-newxgrammar/, sha16)

- 23227CC6D54ACF1A f3-ab-result.txt (20 runs: filled=0 empty=1 nocall=19)
- AFB205D4F859C712 f3-sample.json (empty content, finish=stop)
- C807C6E92AF6614D f3-server.log (no errors)
- g5g6-gate.ps1 (C5 control runs: 1 filled / 3 empty same prompt-temp)

## Real tokenizer (model tokenizer.json, tokenizers lib)

- `<|tool_call>` = id 48 (single token); `<tool_call|>` = 49; `<|channel>` = 100; `<channel|>` = 101
- vocab 262144 entries (31 contain embedded newlines; length-prefixed dump used)
- m_vocab[48] = `<|tool_call|>` confirmed inside XGrammar TokenizerInfo

## Trigger grammar A(string) vs B(numeric) — production-exact wire

Wire = F3 buildTokenAutoToolGrammar byte shape: string `tag` with Token begin/end,
sequence[ConstString(trailing), json_schema bound=2] content. XGrammar lib f6043f4
AND 1de42473 (both probed, identical results):

- A string trigger `["<|tool_call>"]`: COMPILE_OK, bit 48 allowed, AcceptToken(48)=1
- B numeric trigger `[48]`: COMPILE_OK, bit 48 allowed, AcceptToken(48)=1
- (Probe detour recorded: TokenTag-typed tags also compile; my earlier abort was a
  1-D vs 2-D bitmask tensor + kDLUInt vs kDLInt harness bug, then an invalid
  string-begin wire that GenAI never emits. Harness fixed, results above are clean.)
- Probes: Temp\opencode\xgprobe2.cpp (+xgprobe2-1de.exe log); logs xgprobe2.log, xgprobe2-1de.log.

## Verdict (directive matrix, third arm)

string PASS + numeric PASS offline, live no-dispatch (0/1/19 empty+stop)
=> **GenAI live mask application / sampling integration bug**.
NOT string resolution, NOT matcher semantics, NOT parser, NOT schema ingestion.
F4 continues on this basis. F3 stays evidence-only.
