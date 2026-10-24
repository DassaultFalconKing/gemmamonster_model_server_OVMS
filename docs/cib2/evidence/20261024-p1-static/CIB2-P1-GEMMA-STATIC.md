# CIB2-P1-GEMMA — Static name/offset co-occurrence (GEMMA)

Generated: 2026-10-24

Method: static scan of `openvino_language_model.xml` only (Python `xml.etree`). No model was loaded, no `.bin` was opened, nothing was compiled. Layer elements are read in document order; the ordinal is the 0-based index among **all** layer elements; only `Const` layers can be slots. `offset`/`size` come from the layer `data` element and are stored as `null` when absent (never substituted with 0). `fq_weights`, `subtract`, `convert`, `MatMul`, and `shared_expert` const layers are ignored.

**This is not compiled eligibility.** `compiled_kind`: UNKNOWN; `runtime_acceptance`: NO. No ELIGIBLE verdict is claimed for any model below.

## C:\llm\models\OpenVINO\Wondernutts\gemma-4-26B-A4B-it-qat-q4_0-unquantized-uncensored-heretic-int4-ov-new

- XML status: **FOUND**
- Layer elements (document order): 10687; Const layers: 4450
- Const names containing `.mlp.experts.`: **0**; containing `.experts.`: 90; containing `shared_expert`: 0
- **Matched routed slots (total): 0** — no Const layer name contains `.mlp.experts.`, so all nine slot counts are 0 by the specified rules (this is a naming-convention fact of these IRs, not a scan defect).
- **blocks_with_all_nine: 0**; distinct blocks with any matched slot: 0

| slot | count |
|---|---|
| gate_weight | 0 |
| gate_scale | 0 |
| gate_zp | 0 |
| up_weight | 0 |
| up_scale | 0 |
| up_zp | 0 |
| down_weight | 0 |
| down_scale | 0 |
| down_zp | 0 |

### Block 0 — matched slots (ordinal is 0-based over ALL layer elements)

_No block-0 slots matched under the protocol (empty)._

### Naming actually present in this IR (reference only — NOT counted under the protocol)

Routed-expert storage is named `self.model.language_model.layers.<L>.mlp.{gate,up,down}_proj.weight[/scale|/zero_point]` plus an extra `self.model.language_model.layers.<L>.experts.down_proj[/scale|/zero_point]` trio, and packed gate/up blobs under `__module...experts/prim::ListUnpack/VariadicSplit.*` (no proj-suffixed scale/zp names). Applied to those names, the following counts would arise — provenance only, not protocol results, and carrying no eligibility meaning:

| slot (mlp-named) | count | slot (experts.down_proj-named) | count |
|---|---|---|---|
| gate_weight | 30 | gate_weight |  |
| gate_scale | 30 | gate_scale |  |
| gate_zp | 30 | gate_zp |  |
| up_weight | 30 | up_weight |  |
| up_scale | 30 | up_scale |  |
| up_zp | 30 | up_zp |  |
| down_weight | 30 | down_weight | 30 |
| down_scale | 30 | down_scale | 30 |
| down_zp | 30 | down_zp | 30 |

- Blocks containing all nine slots under those mlp-named patterns: 30; blocks containing the `experts.down_proj` trio: 30.

## C:\llm\models\runtime\gemma4-26-heretic-google-current

- XML status: **FOUND**
- Layer elements (document order): 10687; Const layers: 4450
- Const names containing `.mlp.experts.`: **0**; containing `.experts.`: 90; containing `shared_expert`: 0
- **Matched routed slots (total): 0** — no Const layer name contains `.mlp.experts.`, so all nine slot counts are 0 by the specified rules (this is a naming-convention fact of these IRs, not a scan defect).
- **blocks_with_all_nine: 0**; distinct blocks with any matched slot: 0

| slot | count |
|---|---|
| gate_weight | 0 |
| gate_scale | 0 |
| gate_zp | 0 |
| up_weight | 0 |
| up_scale | 0 |
| up_zp | 0 |
| down_weight | 0 |
| down_scale | 0 |
| down_zp | 0 |

### Block 0 — matched slots (ordinal is 0-based over ALL layer elements)

_No block-0 slots matched under the protocol (empty)._

### Naming actually present in this IR (reference only — NOT counted under the protocol)

Routed-expert storage is named `self.model.language_model.layers.<L>.mlp.{gate,up,down}_proj.weight[/scale|/zero_point]` plus an extra `self.model.language_model.layers.<L>.experts.down_proj[/scale|/zero_point]` trio, and packed gate/up blobs under `__module...experts/prim::ListUnpack/VariadicSplit.*` (no proj-suffixed scale/zp names). Applied to those names, the following counts would arise — provenance only, not protocol results, and carrying no eligibility meaning:

| slot (mlp-named) | count | slot (experts.down_proj-named) | count |
|---|---|---|---|
| gate_weight | 30 | gate_weight |  |
| gate_scale | 30 | gate_scale |  |
| gate_zp | 30 | gate_zp |  |
| up_weight | 30 | up_weight |  |
| up_scale | 30 | up_scale |  |
| up_zp | 30 | up_zp |  |
| down_weight | 30 | down_weight | 30 |
| down_scale | 30 | down_scale | 30 |
| down_zp | 30 | down_zp | 30 |

- Blocks containing all nine slots under those mlp-named patterns: 30; blocks containing the `experts.down_proj` trio: 30.

---
Reminder: this report records static name/offset co-occurrence only. **It is not compiled eligibility.** `compiled_kind` is UNKNOWN and `runtime_acceptance` is NO for all models listed, and no ELIGIBLE claim is made.
