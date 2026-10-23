# Model identity

Repository: OpenVINO/MiniCPM-V-4.7-35B-A3B-int4-ov.
HF snapshot: `8b28ee2fe3a13fe38826d615579141af1c6d406a`.
20/20 local files match pinned download ETags (SHA256 for LFS; Git blob SHA1 for regular files); all metadata has the same snapshot revision. The pinned HF API response was also retrieved; source URL and digest are in evidence/sources.json. Original model artifacts were read, never written.
Total files: 19752272919 bytes. BIN payload: 19722705824 bytes (18.368 GiB).

Architecture: `MiniCPMV4_7ForConditionalGeneration` / `minicpmv4_7`; text `qwen3_5_moe_text`.
40 text layers: 30 linear attention and 10 full attention; hidden 2048, attention heads 16, KV heads 2, head_dim 256; 256 routed experts, top-8 per token, routed intermediate 512, shared expert intermediate 512. These are config values, not measured active execution.
Vision: MiniCPM-V 4.7 encoder, hidden 1152, intermediate 4304, 27 layers, 16 heads, patch 14, configured vision size 980 and outer image size 448; 2x2 merge, canvas M-RoPE, downsample 16x. Actual visual IR takes pixel_values, position_ids, window_index, merge_index and returns hidden size 2048.
Language IR takes inputs_embeds, attention_mask, 3-axis position_ids and beam_idx; emits logits of vocabulary 248144. IR opset census and all interfaces are in evidence/inventory.json.
Quantization: asymmetric INT4 language, group 64, ratio 1.0, INT8 symmetric backup; text and vision embeddings INT8 symmetric. Config dtype bfloat16 describes source; it does not describe every IR tensor.
Native context configured at 262144. No long-context test was run.

KV: actual IR declares 20 full-attention key/value state tensors, each FP32 [batch,2,sequence,256]. At C1 this is 40960 bytes/token: 20 MiB at 512, 80 MiB at 2048, 10 GiB at 262144, before allocator padding, image tokens, outputs and linear states. GPU may change precision/layout; these are graph-level arithmetic estimates, not measured VRAM. Remaining 60 ReadValue tensors belong to linear recurrent/conv state; exact shapes/types are in evidence/state-shapes.json. A naive 40-layer dense-KV estimate would be wrong.
MTP config has one prediction layer, but no dedicated draft/MTP IR is supplied. Speculative decoding on this exported VLM is NOT established. Native expert OTD is NOT established: no execution trace or per-expert residency evidence; OFFLOAD_RATIO property presence does not prove demand-driven expert loading. No such option was enabled.

| File | Bytes | SHA256 |
|---|---:|---|
| `.gitattributes` | 1570 | `34448b82c17d60fec9b65b1f093c115ddbaadc04beb1b0140b6bfed2e012a930` |
| `chat_template.jinja` | 7250 | `c4531cacbf2a0ab65170433d7a4f371d11b7599cf96c04b192e6372432636c70` |
| `config.json` | 3445 | `4ef15092c1e980ebd036a0bf0e6436b48df33ac92f29bc62c333648bef6e7d14` |
| `generation_config.json` | 188 | `402b12b1edb604100b161f4f29dba1e31474ed095bd816793424c25c697da123` |
| `openvino_config.json` | 2472 | `f298b0ade72bdbf1a2fa59544ddcb37415b23f336b77fe9804563fb3d0d8da6d` |
| `openvino_detokenizer.bin` | 3829740 | `4958d4da72efaf03840400261e0b14b548c39594688e218aae2bd955ce04b30f` |
| `openvino_detokenizer.xml` | 14991 | `4134832be07affc156834703350e9165a924563c9ac03c6ceb087679060c2068` |
| `openvino_language_model.bin` | 18646197448 | `c420194c98379a15872bdb301cbd28785c8f97198fc3ac1e46d14b7051abab21` |
| `openvino_language_model.xml` | 8201196 | `80ba3775361b9e090acf0d1bdc4aac118351069888ea2805e7e65a885257b701` |
| `openvino_text_embeddings_model.bin` | 508695204 | `e9d2a678a59357aabea2ec7315ecdcf4dda406bda0bc4f19972054cf1ea02b97` |
| `openvino_text_embeddings_model.xml` | 5915 | `fecf15a80c9fcd5d08acc569df3814bbe16a016bdf1d02439eb4588abda7c483` |
| `openvino_tokenizer.bin` | 9635064 | `dd69a774718352bf4531ca8d1c7d342a77d08489b3405cb93af0a233eee23550` |
| `openvino_tokenizer.xml` | 33600 | `c11339aad3605744517c5c0e665ab8700a562b94ef14ee9adb1aef9caa1e1a02` |
| `openvino_vision_embeddings_model.bin` | 554348368 | `26d0050ae071f170d8b8b682a62bf469695e1ecbdff5ee9223f10b4b3eb28582` |
| `openvino_vision_embeddings_model.xml` | 1284764 | `c1172341075423fd7e05eb89d5669d213f6eb40ea8ae364fc310376d7647e1f7` |
| `preprocessor_config.json` | 476 | `8a75300d690678e02e1ff79438d258f94dc25641096081cc0d3ec017359d8972` |
| `processor_config.json` | 1254 | `fcec69f50643334bbbd03ed183e2c65d1d4897966dc7630d6a62036200784279` |
| `README.md` | 6415 | `5aec5f444190b2f66f1b03e0905e7e67c9dbb89148ef81da81caa53dc94cf44c` |
| `tokenizer.json` | 20001935 | `e4608c5d7b3f4f30ba83be16a82cdac856b2e7191d40f0a08cbacc76c2a926ee` |
| `tokenizer_config.json` | 1624 | `770962bf1cc602db426a0e18f6127b245f4beb20121ba17715a8d1dec5612be0` |
