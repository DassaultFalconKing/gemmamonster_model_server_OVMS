# Actual family inventory, 2026-10-24

Static XML/config scan of seven local exported checkpoint directories. All seven are structurally complete under the mapper contract. `complete` is not runtime acceptance. BIN files were statted, not loaded or hashed; configuration and graph hashes and per-block roles are in [the machine-readable map](evidence/20261024/family-inventory.json). Full node maps and their hashes are retained privately.

| Checkpoint | Text model_type | Graphs | BIN GiB | Observed named transformer blocks per graph |
|---|---|---:|---:|---|
| minicpm-v47-35b-a3b-int4-ov | qwen3_5_moe_text | 5 | 18.368 | openvino_language_model.xml: 40; openvino_vision_embeddings_model.xml: 27 |
| OpenVINO/gemma-4-E4B-it-int4-ov | gemma4_text | 6 | 5.979 | openvino_language_model.xml: 42; openvino_vision_embeddings_model.xml: 16 |
| OpenVINO/gemma4-google-template-overlay | gemma4_text | 6 | 15.015 | openvino_language_model.xml: 30; openvino_vision_embeddings_model.xml: 27 |
| OpenVINO/Wondernutts/gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov-new | gemma4_text | 6 | 15.015 | openvino_language_model.xml: 30; openvino_vision_embeddings_model.xml: 27 |
| ornith-35b-ov | qwen3_5_moe_text | 7 | 18.270 | openvino_language_model.xml: 40; openvino_vision_embeddings_merger_model.xml: 27 |
| qwen3.6-35b-a3b-eagle3-ov-int4 | llama | 1 | 0.605 | none parsed (draft IR) |
| runtime/gemma4-26-heretic-google-current | gemma4_text | 6 | 15.015 | openvino_language_model.xml: 30; openvino_vision_embeddings_model.xml: 27 |

Repeated Gemma26 directories are variants/overlays, not independent resident models; do not sum their payloads. The Eagle3 checkpoint is a draft, not the full Qwen3.6 target. No LFM or GLM export was found in this bounded root. Name-derived block indices and raw IR node IDs remain separate. Missing names remain unknown; no hotness or fixed cache allocation is invented.

Qwen/Ornith and MiniCPM routed text are static candidates for compiled GEMM3 MoE inspection. Gemma26 needs its own expert-kind check; a routed label does not establish GEMM3 eligibility. Gemma E4B's observed graph/config has no routed expert inventory, so expert OTD is not an evidenced mechanism for it. Dense layer offload requires a separate implementation/measurement path. Vision, attention, recurrent state, embeddings, shared experts and router weights stay outside the RC1 routed-expert disk loader.
