# Gemma and Qwen mapper acceptance, 2026-10-24

The mapper/source-lock/replay functionality was already committed at `03b32911b0189791c2ad3b9a746e676871b40eb5`. This separate run re-scanned actual local model exports and independently compared the map with XML Const offset/size fields, actual BIN file bounds, graph hashes and independently merged interval unions. Host suite: **67/67 PASS**.

| Actual export | Result | Routed Const nodes |
|---|---|---:|
| OpenVINO/gemma-4-E4B-it-int4-ov | PASS | 0 |
| OpenVINO/gemma4-google-template-overlay | PASS | 90 |
| OpenVINO/Wondernutts/gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov-new | PASS | 90 |
| ornith-35b-ov | PASS | 120 |
| qwen3.6-35b-a3b-eagle3-ov-int4 | PASS | 0 |
| runtime/gemma4-26-heretic-google-current | PASS | 90 |

The Eagle3 row is a Qwen draft (`llama`), not a full Qwen model; Ornith is the available full `qwen3_5_moe_text` export. Gemma26 aliases/overlays are tested separately and must not be summed as independent resident models. Gemma E4B is a negative control for routed-expert discovery.

For routed Const tensors, this run read up to six pairs of 4 KiB boundary samples per model, without loading complete weights. [Actual evidence and sample hashes](evidence/20261024-gemma-qwen/acceptance.json), [host test log](evidence/20261024-gemma-qwen/host-tests.txt). Sources and weights were opened read-only.

These maps can feed a future packer's input inventory and payload-address validation. Raw node IDs can repeat inside nested IR subgraphs; never key a pack record by raw node ID alone. This run pairs XML nodes in document order and records graph, ordinal, name and byte range for sampled records. A future packer must retain explicit subgraph scope or equivalent unambiguous identity. Divisible leading dimensions are descriptive candidates only: correct expert-axis layout, quantization scales/zero-points, possible transposes and all nine routed tensors must be tied to the exact compiled loader before packaging. No pack was written, no expert payload parity or live GPU/offload result is claimed.
