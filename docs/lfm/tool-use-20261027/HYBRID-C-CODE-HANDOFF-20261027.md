# LFM2.5 Hybrid C source handoff — 2026-10-27

Status: **CODE CANDIDATE, NOT GPU ACCEPTED**. Base `990174b4b`, separate review branch `review/lfm25-design-c-semantic-refit-20261027`, [PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34). Never overwrite RC4 or A9 candidate-final binaries.

## Implementation

- `OutputParser` now stages emitted `ContentDelta` across both `DefaultContentParser` and `Lfm2ToolParser` paths, then classifies on a native `ToolCallDelta`, a distinct reasoning/finish event, or after terminal drain.
- `tool_parser=lfm2` + `reasoning_parser=lfm2` + `toolsAvailable=true` enables demotion; LFM2-24B tool-only, other parser families, and requests without tools are unchanged. The strict registry/schema retainer is untouched.
- Native envelopes alone create executable tool deltas; pseudo-plan JSON and `[tool:...]` never do.
- Pending content is bounded to 1 MiB and cleared on parser reset. Intercepting `drainPendingDelta` ensures an intentionally withheld `ContentDelta` does not stop subsequent tool/event draining. Events preserve original tool order.
- Plain content with the LFM2.5 demotion profile and tools enabled is intentionally withheld until a delimiter or terminal response; do **not** claim incremental text SSE latency is unchanged.
- The pure classifier uses a closed key set and pseudo-tool-lines-only D2 profile. A valid JSON user answer containing `plan` can still be demoted if tools are enabled: **known false-positive risk**. Do not promote to stable default before live UX review.
- `start-lfm25.ps1`: r0+U4 by default through `plugin_config.KV_CACHE_PRECISION`, rollback `-KvPrecision auto`; no offload added. Candidate EXE override requires full SHA256. Model staging is per-port and the script checks port availability before replacing files.

## Build (Windows target only, no live smoke yet)

Use the existing locked SDK and Windows toolchain, from a clean checkout and with RTK proxy where configured:

```powershell
git fetch origin
git switch review/lfm25-design-c-semantic-refit-20261027
git status --porcelain=v1
$root = 'C:\gm\lfm-2026.4\hybrid-c-review-20261027'
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

## Isolated GPU smoke (operator controlled)

Do not stop the working listener on 8137; use 18147, one model and one owned process at a time. First hash the **newly built** EXE:

```powershell
$exe = Join-Path $root 'build-py_off\bin\ovms.exe'
$sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
pwsh -NoProfile -File .\scripts\windows\start-lfm25.ps1 -Port 18147 -KvPrecision u4 -ExecutablePath $exe -ExecutableSha256 $sha
```

The launcher checks the RC4 DLL manifest and candidate EXE checksum, uses a per-port serving clone, binds localhost only, and does not kill any existing OVMS. In another terminal, run the existing protocol and tool-use harness with a distinct output directory:

```powershell
python .\scripts\windows\lfm-tool-use-probe.py --url http://127.0.0.1:18147/v3/chat/completions --model lfm25-8b-a1b-int4 --output C:\gm\lfm-2026.4\hybrid-c-review-20261027\smoke-u4
```

For the A/B baseline, terminate **only this owned 18147 process**, restart with `-KvPrecision auto` and archive separate logs. The existing 8137 control service must remain untouched. Test pseudo-plan fixture injection at unit level and actual `auto` model generation separately; do not claim agent auto success merely because malformed prose moved to reasoning.

## Residual blockers

- Actual Windows build, focused/unit suites, raw unary/SSE and live GPU: NOT_RUN in cloud code session.
- `tool_choice=none` final-prose hang: separate generation/streamer/client problem; this patch does not fix it.
- U4 measured speed numbers and offload cliff are taken from the handoff, not reproduced in this branch.
- Full model/agent correctness and context-pressure tests remain local acceptance.
- Do not merge PR #34 as stable until the local gate and false-positive decision are recorded.
