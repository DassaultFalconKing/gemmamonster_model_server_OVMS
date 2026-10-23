# Compatibility matrix

| Stage | Pinned SDK RC1 | Isolated nightly |
|---|---|---|
| OpenVINO | `2026.4.0-22930-61afcb26271-releases/2026/4` | `2026.5.0-23594-7e507a4ca9a` |
| GenAI | `2026.4.0.0-3401-5f7f1278107` | `2026.5.0.0-3556-73c4b0db060` |
| Core sees GPU | PASS | PASS |
| Read all five actual IR graphs | PASS | PASS |
| VLMPipeline creation | FAIL: unsupported minicpmv4_7 | BLOCKED: memory admission |
| Language/visual GPU compile | NOT_RUN: dispatcher rejects first | BLOCKED |
| First generation | NOT_RUN | BLOCKED |

PyPI initially resolved 2026.4.1 / 2026.4.1.0; that environment was then upgraded in place to the official nightly, still isolated from the pinned SDK. Stable 2026.4.1 was not given a pipeline verdict. Early tokenizer read errors were harness setup errors from missing extension registration, corrected before the final reads; they are not checkpoint incompatibilities. Initial pinned import needed process-local SDK TBB lookup; no DLL was replaced.

Nightly source at `73c4b0db060` contains minicpmv4_7 model dispatch, InputsEmbedderMiniCPMv4_7, and VisionEncoderMiniCPMv4_7. This verifies source routing, not GPU execution. GPU plugin versions and actual loaded DLL names, bytes, SHA256 are in probe evidence; physical paths remain in private evidence.
