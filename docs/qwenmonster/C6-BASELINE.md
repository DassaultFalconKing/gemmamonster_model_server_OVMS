# C6 frozen baseline

- Repo: `DassaultFalconKing/gemmamonster_model_server_OVMS`
- Source branch: `c6-head-mainline-20261020`
- Source commit: `ba6ec792c3121850fea167fa7d7e190b25fcdc76`
- Source tree: `b60de265b7c50067393c8e1198e51ed555ca6035`
- Source Qwen parser: `src/llm/io_processing/qwen3coder/qwen3coder_tool_parser.{hpp,cpp}`
- Streaming router: `src/llm/io_processing/output_parser.cpp`
- Streamer: `src/llm/ovms_text_streamer.cpp`
- Existing Qwen fixture: `src/test/llm/output_parsers/qwen3coder_output_parser_test.cpp`
- Baseline Qwen parser blob SHA: `a4a6dc595d17f8f000b8b79aa5d3a188eeb79903`
- Baseline Qwen header blob SHA: `d37aa352e6e4e8bdc0843ab1cfacb0f268427dc5`
- Build/runtime versions, DLL inventory and live Gemma / Qwen acceptance: **NOT CAPTURED**; check on deployment host.

## Direct code observations
- The original `sendFullDelta()` throws for more than one parsed call.
- The original completion path does not guarantee a name/id delta before arguments for same-chunk completion.
- Original recovery could close unfinished parameter values at STOP.
- The outer router and streamer support `drainPendingDelta()`.
- `OVMSTextStreamer::end()` currently sends `STOP` to the parser and does not preserve actual LENGTH semantics end-to-end.

Do not infer live regression numbers from these source observations.
