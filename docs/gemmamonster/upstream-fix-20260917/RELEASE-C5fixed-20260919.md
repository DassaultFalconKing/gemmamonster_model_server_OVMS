# Release: C5fixed 20260919 (pinned working distribution)

Source: `8c6f8b00912e8baa24fb1566a843b031584f1eaa`
(`fix/gemma4-agentic-transition-recovery-c5-20260918`)
Tag: `c5fixed-20260919` (points at the source HEAD above).

## Distribution

Live: `C:\llm\ovms-C5fixed\` (149MB+ with embed python).
Pinned copy: `C:\llm\ovms-C5fixed-pinned-20260919\` (mirror minus logs/live-tests).

```text
56AD64A0B09F8DC1  ovms.exe
DD3B5D28F13147E5  ovms_mediapipe_runtime_shared.dll (history fix)
8C7F1F0CD4061EDD  openvino_genai.dll (G2-X2 / XGrammar f6043f4)
F7797C7D89C78E67  openvino.dll
5722341D2E9297D9  openvino_tokenizers.dll
```

Model `gemma4` = `C:/llm/models/runtime/gemma4-26-heretic-google-current`
(config `C:\live_accept\config.json`; template/small-file hashes in provenance doc).
Python 3.12.10. Launch: `C:\llm\ovms-C5fixed\START-SERVER.md` (variant B).

## Proven on this exact binary

- Exact 2x2 history replay 4/4 (pre-fix: 2x400).
- Public arguments-as-STRING preserved.
- Agent loop T1/T2/T3 + multitool chain (calculator -> 2x get_weather -> search_docs).
- Negatives 4/4 HTTP400 with parse position. MEDIAPIPE_TEMPLATE_ERRORS=0.
- Live thinking traces (784-char 3-step plans) + reasoning+tool_calls together.
- G2 pack, live-like 5/6, 7 focused probes (see handoffs/VERDICT files).

## Reproduce

Recipe: `C5fixed-RECIPE-20260919.md`. Source tag `c5fixed-20260919` + GenAI
`15e8f897` + OpenVINO `c:/o/openvino` + build flags in recipe = same bits
(modulo timestamps).
