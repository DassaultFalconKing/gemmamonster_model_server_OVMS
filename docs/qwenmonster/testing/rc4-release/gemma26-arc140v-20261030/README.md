# Tested working combination: Gemma26 lean / Arc 140V

Recorded on **2026-10-30**. Operator-accepted lean OVMS profile for
**Gemma4-26B-A4B INT4** on Intel Arc 140V, with OMP **18.14.0** ComputerUse and
BrowserUse (Neon relay) passing on a **single** OVMS instance (`:8137`).

This directory is the **commit-safe, anonymized** publication of the local
full-success freeze. User profile paths, machine-unique PnP instance IDs,
session JSONL, browser process inventories, and binaries are omitted. The
local frozen pin retains the complete DLL/runtime/tool tree.

## Configuration

| Parameter | Tested setting |
| --- | --- |
| Runtime | GEMMAMONSTER 2026.4 RC4, Windows x86_64 Python Off |
| Model | Wondernutts Gemma4-26B-A4B INT4 OV (Heretic/uncensored QAT build) |
| Hardware | Intel Arc 140V |
| GPU driver | `32.0.101.9150` |
| Device / pipeline | `GPU` / `VLM_CB` |
| Scheduler slots | `max_num_seqs=2` |
| Prefill batch | `max_num_batched_tokens=1024` |
| HTTP workers | `rest_workers=4` |
| KV | dynamic (`cache_size=0`), precision auto |
| Prefix cache | Off |
| Tool guided generation | Off (OMP eval schema) |
| Tool / reasoning parsers | `gemma4` / `gemma4` |
| OMP | 18.14.0; ComputerUse + BrowserUse relay |
| Constraint | One OVMS only |

See `SUCCESS.lock.json` and `LEAN-LAUNCH.lock.json` for hashed runtime cohort
entries and acceptance summary. Example launcher: `start-gemma26.example.ps1`
(placeholders `<RC4_OVMS_PACKAGE>`, `<MODEL_ROOT>`, identity-lock paths).

## Acceptance

| Check | Status |
| --- | --- |
| Agent tools on lean profile | PASS |
| ComputerUse (AX fixture) | PASS |
| BrowserUse / Neon relay | PASS |
| Memory vs prior heavier defaults | PASS (relative) |

Details: `RESULTS-cu-browser.md`, `RESULTS-mem-agent.md`.

## Anonymization

- `%USERPROFILE%` replaces `C:\\Users\\<user>`
- PnP device instance tails replaced with `<instance>`
- No `omp.exe`, OpenVINO/OVMS DLLs, or model weights
- No OMP session JSONL / live process command lines with profile paths
- Local pin name retained only as an opaque label + SHA256 of the private lock

Local private freeze (not in this tree): `gemma26-full-success-arc140v-20261030T010005Z`
(`IDENTITY-LOCK.sha256` = `fbc3d16ab402ad31b91b32a873de7c3a2d8f7a61a67e56262b8da6f3dfbe5089`).
