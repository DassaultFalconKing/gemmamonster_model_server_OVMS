# LFM2.5 Hybrid C source handoff — 2026-10-27

Status: **HISTORICAL GPU PROTOCOL PASS, SOURCE CLEANUP NEEDS REBUILD**. Local validation of EXE `d9663aa6…` is recorded in `HYBRID-C-LOCAL-VALIDATION-20261027.md` (LFM2.5 official agent 2/4 FAIL). New source in [PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34) protects valid JSON and streams ordinary prose early: **NOT YET COMPILED/SMOKED**. Start scripts still pin that historical EXE; defaults changed to KV auto. Do not overwrite known-good RC4 or A9 binaries.

## Implementation

- `OutputParser` now stages emitted `ContentDelta` across both `DefaultContentParser` and `Lfm2ToolParser` paths, then classifies on a native `ToolCallDelta`, a distinct reasoning/finish event, or after terminal drain.
- `tool_parser=lfm2` + `reasoning_parser=lfm2` + `toolsAvailable=true` enables demotion; LFM2-24B tool-only, other parser families, and requests without tools are unchanged. The strict registry/schema retainer is untouched.
- Native envelopes alone create executable tool deltas; pseudo-plan JSON and `[tool:...]` never do.
- Pending content is bounded to 1 MiB and cleared on parser reset. Intercepting `drainPendingDelta` ensures an intentionally withheld `ContentDelta` does not stop subsequent tool/event draining. Events preserve original tool order.
- Ordinary noncandidate prose is now streamed promptly; JSON-like and `[tool:` candidate segments can still be buffered until a boundary. Live SSE latency and parity must be remeasured.
- The heuristic classifier remains closed-profile. The runtime now validates standalone JSON with RapidJSON and preserves it in `content` even when it contains `plan` or `commands`. This change is **source only** until rebuilt. Malformed pseudo-JSON and literal pseudo-tool documentation remain possible ambiguous cases; require live negative tests.
- `start-lfm25.ps1`: r0 with KV auto by default (conservative; historical A/B u4 55.12 vs auto 56.24 tok/s at n=3), explicit `-KvPrecision u4` memory variant. Same auto default now on 24B pending comparative data. No offload added. EXE override requires SHA256, staging isolated per port.

## New source cleanup: Windows rebuild and smoke required

Use the existing locked SDK and Windows toolchain, from a clean checkout and with RTK proxy where configured:

```powershell
git fetch origin
git switch review/lfm25-design-c-semantic-refit-20261027
git status --porcelain=v1
$root = 'C:\gm\lfm-2026.4\hybrid-c-cleanup-20261027'
pwsh -NoProfile -File .\scripts\windows\build-rc4.ps1 -Python off -Output $root -Jobs 4
```

If the immutable output directory already exists, choose a new one; never delete an accepted build receipt to make the script pass. Check build-py_off/COMPLETE.json and exact SHA256. The script builds `ovms.exe` and `ovms_test.exe` from this branch; using A9 candidate-final EXE would **not** test the new parser.

## Unit gate

From the checkout root using the existing pinned test environment (Python/SDK fixture conventions from `docs/lfm/PROGRESS.md`):

```powershell
$testExe = Join-Path $root 'build-py_off\bin\ovms_test.exe'
& $testExe --gtest_filter='LfmThoughtDemotionReview.*:*LfmStrictOutputParserTest.*:*Lfm2*:*Lfm25*:*Gemma4*:*Qwen3Coder*' --gtest_output=xml:lfm-hybrid-c-focused.xml
if ($LASTEXITCODE -ne 0) { throw 'LFM hybrid unit gate failed' }
```

Record exact filter, binary/DLL hashes, tests passed/failed/skipped and whether tokenizer fixtures are the genuine target versions. A missing fixture is BLOCKED, not PASS. Confirm source compiles on MSVC/Bazel: source review and standalone host classifier checks are not a product build.

### Required assertions

1. Prose-only D1 and D2 demote to reasoning for LFM2.5; no `tool_calls`.
2. Same input stays visible for tool-only LFM2-24B and `toolsAvailable=false`.
3. One and multiple native tool envelopes preserve IDs, names, argument values, ordering and SSE/unary reconstruction.
4. Plan preceding a tool; prose following a tool; fragmented open/close markers; STOP and LENGTH; same-chunk terminal; reset/cancel.
5. Real `<think>` primary reasoning unchanged; Gemma/Qwen unchanged.
6. A very large plain response fails closed at 1 MiB and is not partially published as an executable tool.
7. False positives: deliberately ask for literal JSON `{"plan":[]}` with tools provided; record whether demotion is acceptable before any production promotion.

## Isolated GPU smoke for NEW EXE (operator controlled)

Do not stop the working listener on 8137; use 18147, one model and one owned process at a time. First hash the **newly built** EXE:

```powershell
$exe = Join-Path $root 'build-py_off\bin\ovms.exe'
$sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
pwsh -NoProfile -File .\scripts\windows\start-lfm25.ps1 -Port 18147 -KvPrecision auto -ExecutablePath $exe -ExecutableSha256 $sha
```

The launcher checks the RC4 DLL manifest and candidate EXE checksum, uses a per-port serving clone, binds localhost only, and does not kill any existing OVMS. In another terminal, run the existing protocol and tool-use harness with a distinct output directory:

```powershell
python .\scripts\windows\lfm-tool-use-probe.py --url http://127.0.0.1:18147/v3/chat/completions --model lfm25-8b-a1b-int4 --output C:\gm\lfm-2026.4\hybrid-c-review-20261027\smoke-u4
```

For optional U4 memory/speed A/B, terminate **only this owned 18147 process**, restart with `-KvPrecision u4` and archive separate logs. The historical U4 results do not prove a repeatable advantage. The existing 8137 control service must remain untouched. Test pseudo-plan fixture injection at unit level and actual `auto` model generation separately; do not claim agent auto success merely because malformed prose moved to reasoning.

## Residual blockers

- Historical Hybrid C candidate: Windows build/197P+2S/GPU protocol PASS. **Latest cleanup revision:** Windows build, focused/unit suites, raw unary/SSE and live GPU NOT_RUN.
- `tool_choice=none` final-prose hang: separate generation/streamer/client problem; this patch does not fix it.
- U4 measured speed numbers and offload cliff are taken from the handoff, not reproduced in this branch.
- New source: valid-plan JSON and early normal-prose SSE must pass explicitly. Official-agent LFM2.5 remains conditional (2/4 on historical candidate); do not infer any improvement from demotion.
- Do not merge PR #34 as stable until the local gate and false-positive decision are recorded.
