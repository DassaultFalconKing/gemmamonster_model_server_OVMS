# CIB2-03 — offline OTD trace replay

Stdlib-only, deterministic offline replay for `moe_otd_trace v1` traces. It never starts
inference, loads a model, builds native code, touches the GPU, or mutates a runtime cache.
Runtime acceptance remains **NO**; this is an offline analysis tool.

## Provenance / attribution

Adapted from the Intel OpenVINO Intel GPU tool
`src/plugins/intel_gpu/tools/moe_otd_sim/otd_sim.py` (Apache-2.0). Intel copyright and SPDX
headers are preserved.

- Original donor import: `86bab01ebf2558e9d796be754c1b179677efc1b3`.
- Donor research repository inspected read-only at HEAD
  `956d5eca956f45b9b76a29daafc3642eb2d9520f`; the donor directory was last changed by
  `f054eecc7767c9c45627beb4a7883f1642916125` (`--precheck` → `--legacy-partial-lease`).
  The current donor file is therefore not byte-identical to `86bab01e`.
- The donor was not modified.

CIB2 adds strict trace-v1 validation, closed-call accounting, explicit offline-only output
metadata, and logical-vs-physical byte separation.

## Trace format

```text
# moe_otd_trace v1
L,<layer>,<layer_key>,<model_key>,<capacity>,<num_expert>,<top_k>
C,<call>,<t_ns>,<layer>,<S|O>,<routed>,<ok|overflow>,<unique experts in first-occurrence order>
E,<call>,<t_ns>,<layer>,<expert>,<slot>,<hit>,<evicted|-1>,<bytes>,<reads>,<read_ns>,<transform_ns>,<copy_ns>
```

Validation is strict and has no lenient mode:

- exact header on the first line (UTF-8 BOM accepted); no duplicate header or header after data;
- exact field counts and base-10 integers;
- unique layer/call IDs; layers must be registered before calls;
- layer, expert, slot and eviction bounds; no duplicate experts in a lease;
- `ok`/`overflow` status must agree with `capacity`; an overflowing `S` lease has no `E`
  records and never touches the cache;
- events must match lease order and each call must be fully closed; truncated or incomplete
  traces are rejected rather than silently accepted;
- a cache hit has slot 0..capacity-1 and zero bytes/reads/timings.

## Byte accounting

`logical_bytes.requested`, `.read_from_storage` and `.copied_to_slots` describe expert
payloads implied by the trace or by a simulated miss. They are **logical** numbers.

`physical_bytes.nvme_read` and `.nvme_write` are always `NOT_EXPOSED`: trace-v1 has no
device counters, so physical reads, writeback, readahead, retries and amplification cannot be
derived from it. Supply external OS/NVMe counters if physical bytes are required. Do not
present logical bytes as measured device traffic.

## Commands

```text
rtk proxy python scripts/cib2/otd_sim/otd_sim.py verify   <trace> [--decisions]
rtk proxy python scripts/cib2/otd_sim/otd_sim.py summary  <trace>
rtk proxy python scripts/cib2/otd_sim/otd_sim.py simulate <trace> [--policy lru|clock|2q|opt]... \
       [--capacity N... | --capacity-fraction F...] [--legacy-partial-lease] \
       [--committed-tokens N]
```

`verify` replays recorded capacities with the exact LRU model and compares every recorded
slot/hit/eviction decision. It exits 1 on mismatch and 2 on an invalid trace.

`simulate` replays per layer at recorded or alternative capacities. Recorded fallback calls
are skipped when a simulated lease succeeds. When a smaller simulated capacity turns a
recorded successful lease into an overflow, per-expert fallback calls are synthesized in
sorted order. A lease already recorded as `overflow` is never given invented cache accesses:
it contributes zero loads, and only recorded fallback calls (if present) touch the cache.
`--legacy-partial-lease` is an offline what-if only and is not a policy promotion.

Synthetic C1/C2/C4 and lease-overflow traces are accepted as offline inputs only. They are
never evidence of a live workload, throughput, or runtime behavior.

## Tests

```text
rtk proxy python -m unittest discover -s tests/cib2 -p test_otd_sim.py -v
```
