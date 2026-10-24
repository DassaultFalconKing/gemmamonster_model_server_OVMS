# Static nine-slice co-occurrence

Compiled expert kind: **UNKNOWN**. Runtime acceptance: **NO**.
Weights BIN was not opened. Name co-occurrence is not compiled eligibility.

- Graph: `openvino_language_model.xml`
- Source: `C:\llm\models\ornith-35b-ov\openvino_language_model.xml`
- Layers seen: 15765
- Matched routed Const slots: 120
- Blocks with a routed slot: 40
- Blocks with all nine slots: 0

| Slot | Count |
| --- | ---: |
| `gate/weight` | 0 |
| `gate/scale` | 0 |
| `gate/zp` | 0 |
| `up/weight` | 0 |
| `up/scale` | 0 |
| `up/zp` | 0 |
| `down/weight` | 40 |
| `down/scale` | 40 |
| `down/zp` | 40 |

## Block 0

| Slot | Ordinal | Layer id | Offset | Size |
| --- | ---: | --- | ---: | ---: |
| `down/weight` | 379 | 344 | 309329201 | 134217728 |
| `down/zp` | 381 | 346 | 443546929 | 2097152 |
| `down/scale` | 384 | 349 | 445644081 | 8388608 |
