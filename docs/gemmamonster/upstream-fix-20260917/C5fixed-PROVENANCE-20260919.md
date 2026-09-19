# Provenance bundle — C5fixed known-good reference runtime (2026-09-19)

Status: KNOWN-GOOD REFERENCE for forward-port comparison.
NOT claimed: FULLY REPRODUCIBLE FROM CLEAN HOST (see gap at bottom).

## Launch profile (exact)

```text
C:\llm\ovms-C5fixed\ovms.exe --rest_port 18091 --rest_bind_address 127.0.0.1
  --port 9000 --grpc_bind_address 127.0.0.1 --config_path C:\live_accept\config.json
```

Env: `PYTHONHOME=C:\opt\Python312` (dist embed lacks stdlib; env-only, zero file mutation).
Model: `gemma4` from `C:/llm/models/runtime/gemma4-26-heretic-google-current`
(config `C:\live_accept\config.json`).

## Request fixtures / scripts

- `C:\Users\testc\AppData\Local\Temp\opencode\ab22.ps1` (exact 2x2)
- `C:\Users\testc\AppData\Local\Temp\opencode\c5fixed-agentloop.ps1` (T1/T2/T3 loop)
- `C:\Users\testc\AppData\Local\Temp\opencode\c5fixed-negative.ps1` (4 negatives)
- Canonical probe: `C5-frankenstein-newxgrammar/emptyargs-probe-request.json`
  (temp 0.0, max_tokens 256, calculator required-expression)
- `g5g6-gate.ps1` (Reps 50, prompt 5232) + `livelike-suite.ps1` (6 cases unary+stream)

## Model / template revision (content-addressed, small files)

```text
A62FF7EB0A97A7C6  config.json
A2619FE11B50DBED  tokenizer.json
F24FB2ADFA622CF3  tokenizer_config.json
AE53464BF3BE2580  chat_template.jinja   <- strict arguments-mapping guard lives here
5439541D3BF0BA9A  generation_config.json
```

Weights (26 GB): NOT hashed (dir listing + sizes on request). Trust boundary noted.

## Binary hashes (dist)

```text
56AD64A0B09F8DC1  ovms.exe (unchanged; handler lives in shared lib)
DD3B5D28F13147E5  ovms_mediapipe_runtime_shared.dll (rebuilt @8c6f8b00, fix verified inside)
8C7F1F0CD4061EDD  openvino_genai.dll (= G2-X2 slot bits, XGrammar f6043f4)
F7797C7D89C78E67  openvino.dll
5722341D2E9297D9  openvino_tokenizers.dll
```

Source: detached HEAD `8c6f8b00912e8baa24fb1566a843b031584f1eaa`
(`openai_api_handler.cpp` +57 only vs `5fa8b4c4e`).
Python: 3.12.10 (`C:\opt\Python312`, jinja2 3.1.6).

## Gap to clean-room reproducible

Missing: weights hash, full OpenVINO install manifest, pip freeze of system python,
exact Bazel flag transcript (partially in `C:\opt\owi5bgwi\command.log`),
single-command rebuild script. Until then: reference runtime, not clean-room proof.
