# LFM generation protocol forensics — 2026-10-31

Research drop for GEMMAMONSTER LFM2/LFM2.5 native agentic inference on Windows / Intel Arc 140V.

## Artifacts

- [LFM_GEMMAMONSTER_Protocol_Forensics_2026-10-31.md](LFM_GEMMAMONSTER_Protocol_Forensics_2026-10-31.md): source-based protocol atlas, streaming/reasoning/tool FSM, parser/runtime comparison, project gap analysis, test and acceptance plan.
- [lfm_synthetic_parser_fixtures_72.json](lfm_synthetic_parser_fixtures_72.json): **72 synthetic design/acceptance cases**, NOT observed raw model traces, NOT a green test run. Includes intentionally failing/unsupported candidate cases.

## Evidence and execution status

- Source investigation and existing repository evidence are described in the report; historical local results are reported rather than independently replayed.
- **No new Windows build, GPU benchmark, peer-runtime differential, or fresh live agent-chain test was performed for this drop.**
- The new fixtures are **contracts** for future local tests. They are not wired into GTest yet and must not be counted as passing tests.
- Existing active implementation: `review/lfm25-design-c-semantic-refit-20261027` ([draft PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34)). Keep its current Windows acceptance blocker in place.
- Prior reference: A9 branch `dev/lfm-family-hardening-20261026` (upstream [PR #4697](https://github.com/openvinotoolkit/model_server/pull/4697), closed without merge).

## Local-agent next steps (Windows only)

1. Pin exact HEAD, model/tokenizer revisions and executable hash. Do not reuse historical EXE test status for fresh source.
2. Review and map synthetic fixtures onto deterministic GTests. Preserve source trace vs synthetic provenance explicitly; do not blindly mark unsupported cases green.
3. Run parser/tokenizer/Minja tests and Gemma/Qwen regressions.
4. Run Arc 140V live unary/SSE tool cycles, `tool_choice` modes, 5–10-step continuation, and final-prose hang reproduction on port 18147 without disturbing the production listener.
5. Attach raw token IDs, decoded stream, emitted deltas, prompt round-trip and `finish_reason`, with secrets redacted, before accepting any bug fix.

Minimal JSON integrity check:

```powershell
python -c "import json; p='docs/lfm/forensics-20261031/lfm_synthetic_parser_fixtures_72.json'; x=json.load(open(p,encoding='utf-8')); assert x['synthetic'] is True and len(x['fixtures'])==72; print('72 synthetic fixtures: OK')"
```

This directory is documentation and test input only, not a change to OVMS runtime behavior.
