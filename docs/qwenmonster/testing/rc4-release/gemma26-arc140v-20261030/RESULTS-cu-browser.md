# OMP ComputerUse + BrowserUse on lean Gemma26 (2026-10-30)

Single OVMS: `gemma26` PID 21732 (seqs=2, batch=1024, workers=4).

## Preconditions fixed

OMP model cache still listed `gemma12` after server switch. `omp models refresh` made `openvino-server-ornith/gemma26` available. Default role set back to gemma26.

## ComputerUse

**PASS.** Fixture challenge `CU-791585` entered and verified via AX; final reply `CU_OK CU-791585`.  
Artifacts: `cu.utf8.jsonl`, `fixture-action-result.json`.

## BrowserUse / relay

**PASS.** Relay answered on `9224` (OMP 18.14.0). Listed Google relay targets, opened `about:blank` into `tab` (not overwriting `browser`), final `BROWSER_OK about:blank`.  
Artifacts: `browser.utf8.jsonl`, `relay-after.json`.

## Note

OMP JSONL on Windows is UTF-16; decode as utf-16 when inspecting.
