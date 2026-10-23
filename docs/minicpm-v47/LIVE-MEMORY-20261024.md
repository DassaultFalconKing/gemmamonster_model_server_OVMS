# Live memory experiment, 2026-10-24

Verdict: **MEMORY_BLOCKED**. The operator authorized memory reclamation and live runs. Two GPU VLMPipeline constructor attempts were actually launched; neither completed construction or reached generation. This advances the historical 2026-10-23 admission-only evidence, not its correctness or performance gates.

## Reclamation

Initial available RAM was 17.584 GiB. Desktop applications accounted for most reclaimable working sets: Cursor 2360 MiB aggregate, ChatGPT 1675 MiB, WebView 991 MiB, Discord 802 MiB, Signal 769 MiB (shared pages can be counted in multiple processes). No ovms/model_server/benchmark/python inference worker was found before starting.
One EmptyWorkingSet pass on 59 selected desktop processes increased available RAM from 17.584 to 19.108 GiB. Applications, unsaved IDE state, VPN service and production runtime were kept running. This trims residency; it does not free application private commit and can move pages into compression/pagefile. Standby was already available memory and was not purged. A second, disjoint pass on five GUI/shell processes increased available RAM from 20.863 to 21.177 GiB. No process was deliberately closed; no service/registry/driver/BIOS/pagefile setting or shared model cache was changed.
Final available RAM after both test trees exited was 22.587 GiB. The full final gain cannot be attributed solely to the trim calls: Windows also reclaimed/compressed/paged application pages during the attempted load. Final pagefile usage was 1.049 GiB. Counts sin/sout in psutil on Windows are not evidence of zero paging. Hard faults were not measured.

## Bounded live attempts

Both use the independently isolated OpenVINO 2026.5.0.dev20261023 / GenAI 2026.5.0.0.dev20261023 environment already pinned in the original report, with unchanged model snapshot 8b28ee2fe3a13fe38826d615579141af1c6d406a. The original BIN+3 GiB admission was a conservative experimental margin, not an SDK requirement. These explicitly bounded attempts used BIN+0 admission; the independent 3 GiB live physical-RAM stop and 600-second deadline remained enabled.

| Attempt | Start available | Duration to safety stop | Minimum sampled available | Peak sampled tree RSS/private | Result |
|---|---:|---:|---:|---|---|
| Default compilation threads | 20.125 GiB | 29.047 s | 2.796 GiB | UNKNOWN: initial monitor sampled redirector only | BLOCKED, memory floor |
| COMPILATION_NUM_THREADS=1 | 21.184 GiB | 32.469 s | 1.970 GiB | 20.578 / 20.651 GiB | BLOCKED, memory floor; phase constructing |

The second run's WDDM GPUProcessMemory snapshot for its actual compute PID recorded SharedUsage=19852402688 bytes (18.489 GiB), TotalCommitted=19869310976 bytes, DedicatedUsage=0. This is a point sample, not a peak. GPU shared memory, process RSS/private and physical RAM overlap on this platform: do not add them. No valid GPU utilization snapshot was retained.
The watchdog checks every 0.5 seconds: it reacted to the first sampled value below 3 GiB, which was already 1.970 GiB in the second run. The threshold is not an instantaneous hard allocation cap. It terminated the owned PID/creation-time tree only; final process inventory contains no surviving Python/inference worker. The System log query for Display event 4101 in the selected 30-minute window returned no records. This narrow check does not establish zero GPU errors of every kind.

No unsupported-op exception was returned before the safety stop. No successful full compilation, load, generation, model output, TTFT, tokens/s or benchmark can be claimed. Standalone text remains BLOCKED; image/video, image-prefill, C1 performance and OVMS live remain NOT_RUN. Full-platform memory fit is unresolved: these are failures to complete safely in the observed desktop session, not a proof that every 32 GB Arc 140V configuration is impossible.

## Harness corrections and controls

The initial resumed smoke was blocked by its own Windows venv Python ancestor. Own ancestors are now excluded, while an unrelated Python process still blocks admission. The monitor now sums the actual owned descendant tree rather than only the launcher; cleanup checks PID plus creation time before termination. Partial constructor phase survives forced/native exit, and failure returns nonzero.
Offline controls: **3/3 PASS** — external Python blocks without creating a child; timeout kills fake-pipeline child and grandchild; native exit 7 is preserved as FAIL with constructor phase. These tests use a fake import and do not load OpenVINO, a model, or the GPU. Captured output is in evidence/live-20261024/supervisor-tests.txt.
The exact second-run script snapshot is preserved as evidence/live-20261024/smoke-single-thread-source.py, SHA256 `6328641e94ef322bf06e09537f7b67e2c11a7db6b0f7282bcd8c0c63b3234c96`. The first run's mutable script hash was not captured at execution time and is not retroactively claimed. Loaded module paths/versions from the second compute process were captured while live; after-run on-disk hashes are in loaded-modules.json. Physical paths are retained privately and replaced with placeholders in public evidence.

## Reproduction and next gate

Run from the feature worktree, with $Python, $Model and $Evidence pointing at the isolated nightly Python, original model and a new evidence directory:

```powershell
rtk proxy $Python scripts/minicpm-v47/reclaim_working_sets.py --group desktop --apply --output "$Evidence/trim.json"
rtk proxy $Python scripts/minicpm-v47/smoke.py --model $Model --output "$Evidence/text.json" --compile-threads 1 --admission-reserve-gib 0 --timeout 600
```

The second command is a reproduction of the observed pressure stop, not permission for an unattended retry loop. After two memory-floor stops, extended tests were stopped as required by the mission. Before another model run, reduce the persistent application footprint further or establish a measured, supported memory-saving model-loading/compile configuration in an isolated experiment. Lowering the safety floor or using the large pagefile to force completion is not acceptance. Do not terminate active IDE/agent tasks or production inference merely to satisfy an artificial admission estimate.

Production DLLs, model weights, shared caches and frozen source were not modified. Changes are confined to this feature branch's test scripts and evidence. All original roadmap/parser/API/agentic gates remain independently unaccepted.
