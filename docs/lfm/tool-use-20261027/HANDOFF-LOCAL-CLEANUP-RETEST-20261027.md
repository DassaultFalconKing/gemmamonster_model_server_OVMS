# LOCAL HANDOFF — LFM Hybrid-C cleanup retest (2026-10-27)

## Mission and priority
Build and test the CURRENT head of `review/lfm25-design-c-semantic-refit-20261027`. The earlier GPU PASS belongs ONLY to the binary pinned SHA256 `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`, not to these source fixes. Do NOT replace/erase that binary, RC4 SDK/DLLs, A9 pin, 8137 server, model sources or production logs.

### What changed since validated binary
1. `output_parser.cpp`: syntactically valid standalone JSON objects always remain `content`, even with tools and plan-like top-level keys. This prevents confirmed `{"plan":[]}` false demotion. Malformed pseudo plans and whole pseudo-tool-line segments may still demote to `reasoning_content`; no invented executable tools.
2. Ordinary prose starting with anything other than candidate `{` or `[tool:` is emitted immediately. This fixes the accidental no-tool prose SSE delay. Candidate spans still buffer through the classifier (bounded to 1 MiB).
3. `output_parser.hpp`: per-segment plain-content fast-path state, reset with the parser and on native-tool/reasoning boundaries.
4. Both `start-lfm25.ps1` and `start-lfm2-24b.ps1`: KV precision default `auto` (no forced plugin property). Explicit `-KvPrecision u4` retained. Historical U4 scores were not repeatably faster and no 24B A/B established.

## Step 0: identity and safety
- `git fetch origin`, confirm branch head, `git status --porcelain` clean, record SHA and every pinned SDK/GenAI/OpenVINO DLL hash. Do not reset an agent's dirty work.
- Build in a FRESH immutable directory, e.g. `C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027`. Never reuse the already COMPLETE `hybrid-c-review-20261027` directory.
- Keep existing service/ports/other models untouched. New server only on localhost `18147` with its own per-port staging directory. Do not stop 8137 or blindly kill any `ovms.exe`.

## Step 1: Windows compiler + focused regressions
```powershell
git fetch origin
git switch review/lfm25-design-c-semantic-refit-20261027
git status --porcelain=v1
$root = 'C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027'
pwsh -NoProfile -File .\scripts\windows\build-rc4.ps1 -Python off -Output $root -Jobs 4
$testExe = Join-Path $root 'build-py_off\bin\ovms_test.exe'
& $testExe --gtest_filter='LfmThoughtDemotionReview.*:*LfmStrictOutputParserTest.*:*Lfm2*:*Lfm25*:*Gemma4*:*Qwen3Coder*' --gtest_output=xml:lfm-hybrid-c-cleanup.xml
if ($LASTEXITCODE) { throw 'Hybrid C cleanup regression failed' }
```
Inspect exact pass/skip/fail, not just process exit code. Changed golden tests must prove `{"plan":[]}`, `{"explanation":"ok","plan":[...]}` and `{"commands":[]}` remain content. Retain native tool execution, all fragmented tag boundaries, malformed pseudo-plan demotion, 1-MiB limit, reset, STOP/LENGTH and plain-prose nonterminal immediate delta. Repeat Gemma/Qwen parser suites unchanged. Fail closed on missing tokenizer fixtures.

## Step 2: hash-locked GPU smoke
```powershell
$exe = Join-Path $root 'build-py_off\bin\ovms.exe'
$sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
pwsh -NoProfile -File .\scripts\windows\start-lfm25.ps1 -Port 18147 -KvPrecision auto -ExecutablePath $exe -ExecutableSha256 $sha
```
Use another terminal for requests. Run existing `scripts/windows/lfm-tool-use-probe.py` for BOTH unary and SSE, tool_choice none/auto/required/named, native multi-tool and literal JSON. Run native chain `cwd -> write -> read`, and one code write/execute. Collect raw SSE, final `[DONE]`, exact tool_calls, reasoning_content/content separation and API finish_reason. If a legitimate JSON object demotes, STOP acceptance. Replay LFM2-24B sequentially using `start-lfm2-24b.ps1 -Port 18147 -KvPrecision auto -ExecutablePath $exe -ExecutableSha256 $sha`, never concurrently on the same port.

### Differential agent gate (LFM2.5)
Historical official profile: **2/4 PASS** (one unary and one SSE failed by printing `[ cwd() ]` prose). Run at least **10 identical reproducible attempts per unary/SSE** with fixed request, seed list, tool schemas, chat template revision, no forced action policy unless prior run used it. Save raw request/response and server log. Compare success/failure raw tokens (specifically did native `<|tool_call_start|>` occur?) and host tool invocation. A parser cannot turn a prose pseudo-tool into an executable native call; distinguish model choice, tokenizer, template, missing special tokens, policy and stop condition. Do not score the model based only on whether it *said* it would call a tool.

### Final prose hang
For tool_choice=none after write/run_python capture start/last-token times, raw SSE `[DONE]`, server finish_reason, prompt and generation config, stream decode trace, client timeout. Classify as model/streamer/parser/client. Do not use the harness skip-final-prose as proof of a fix.

## Step 3: quick KV A/B and status
On LFM2.5, compare new EXE `-KvPrecision auto` vs `-KvPrecision u4` with identical prompts, max_tokens, batch and n>=5, clean process restarts, separate logs. Track decode p50, TTFT, GPU shared/resident memory, host memory and output consistency. Keep `OFFLOAD_RATIO=0`; offload cliff is separate. For 24B do not claim U4 faster without an A/B. Do not change Pack/CIB2.

## Deliverable / acceptance decision
Write `docs/lfm/tool-use-20261027/HYBRID-C-CLEANUP-VALIDATION-20261027.md` plus an evidence rollup with actual paths, SHA256 of source/exe/DLLs/models, command receipts, test XML and reproduced requests. Separate gate statuses:
- `BUILD`, `PARSER_REGRESSION`, `LFM25_PROTOCOL`, `LFM24_PROTOCOL`;
- `JSON_FALSE_POSITIVE`, `SSE_LATENCY`, `OFFICIAL_AGENT_RELIABILITY`, `PROSE_HANG`, `U4_AB`.
Use PASS / FAIL / NOT_RUN / CONDITIONAL. Historical EXE PASS does not transfer to new source. Production merge only after local acceptance and an explicit decision about any remaining ambiguous pseudo-tool documentation.

## HARD TOKEN ECONOMY
Read only files in this handoff and touched diffs. Do not repeat web research, re-audit other model families, rebuild SDK, clone peers, refactor CIB2 or invent additional tasks. Use existing harness and locked build pipeline. Keep reports compact (SHA, commands, PASS/FAIL, evidence, blockers); do not paste massive logs into chats. Escalate from cheaper coding model only when a concrete failing test and a minimal reproduction justify it. No background or unowned server actions.
