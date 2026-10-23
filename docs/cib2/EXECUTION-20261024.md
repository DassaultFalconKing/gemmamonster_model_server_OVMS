# CIB2 offload and family mapping execution

Date: 2026-10-24. Operator authorized execution through external harnesses. ACCEPTED: NO.

## Fixed inputs

- Historical CIB2 plan (archived unchanged): [`archive/20261023/CODE-WORK-PLAN-20261023.md`](archive/20261023/CODE-WORK-PLAN-20261023.md), source branch `feature/cib2-rc3b-otd-preflight-20261023` at `c62aa040d46581625933e536b6b92958f2577bd0`.
- Working runtime/source boundary remains the frozen 2026.4 postfix `eb76a74f7aa39573d452d95443e189b1f5f4d9e8`. Tagged RC3B and working-postfix binary identities remain separate.
- MiniCPM live input fixed at `1caffd79ed1c7868242dbaa23e99289f36cc4ddf` on its independent feature branch. Two actual isolated nightly constructors stopped on physical RAM pressure; no generation/performance acceptance. Its immutable `docs/minicpm-v47/evidence/live-20261024/summary.json` is the resource-failure input, not evidence of native OTD eligibility.
- Program branch: `feature/cib2-offload-family-map-20261024`, from the existing CIB2 plan. Frozen product and other worktrees are read-only.

## First wave and ownership

| Packet | External owner | Allowed output | Acceptance in this wave |
|---|---|---|---|
| MAP-01 / CIB2-02,07 | OpenCode 2.1.3, opencode/glm-5.3-flash-free | static family/layer mapper and focused tests | Actual IR/config evidence, conservative roles, unique BIN-range accounting; no BIN reads or OpenVINO/model imports |
| REPLAY-01 / CIB2-03 | OpenCode 2.1.3, opencode/deepseek-v4.1-flash-free | strict trace parser/replay and focused tests | Exact offline LRU decisions on valid complete traces; invalid/truncated traces rejected; physical NVMe bytes NOT_EXPOSED |
| AUDIT-01 | Cursor Agent 2026.10.22-27dcf5f, grok-4.7-high | read-only native eligibility audit | Source-linked seams and unsupported/unknown distinctions; no source patches |
| INTEGRATE-01 | Coordinator | reviewed real-model maps, evidence, state, commits | Independent host tests and protected-source checks; runtime acceptance remains separate |

External task prompts specify disjoint paths, exact cwd, model selection, forbidden actions, timeout and early partial reports. The private canonical task register and run logs are retained in the orchestration hub; only sanitized status/receipts are published. A local run ID is not a provider session ID. Worker exit0 is NEEDS_REVIEW until independently checked.

## Mapping contract

For each actual exported checkpoint, distinguish operator name, model_type/architecture, language/vision/draft graphs and exact observed layer IDs. Inventory routed experts separately from shared experts/router, dense attention, recurrent state, embeddings, vision and outputs. Aliased and overlapping Const ranges must be union-counted per physical BIN, never charged once per consumer. Unknown roles, config-only overlays and missing checkpoints remain explicit.

Target families: Qwen3.6/Ornith hybrid MoE, Gemma4 dense E4B and routed 26B, MiniCPM-V4.7 hybrid MoE plus vision; record LFM/GLM as NOT_AVAILABLE unless an actual local IR is found. A draft checkpoint does not substitute for the full target model. Static XML may precede runtime fusion: no compiled MOECompressed or actual hotness claim follows from XML/config alone.

Every family needs its own memory/eligibility decision. Disk expert OTD, dense layer CPU offload, host-visible USM residents, mapped cold records and expert hot/cold scheduling are distinct mechanisms. Do not force a routed-expert policy onto dense or unsupported graphs. Layer importance/hotness requires real complete routing traces; no fixed layer IDs or speculative cache placement in this wave.

## Change proposal

1. Cause: MiniCPM full GPU construction twice exhausted safe desktop-session RAM; model architecture labels and OFFLOAD_RATIO alone cannot establish that offload can help.
2. Files: scripts/cib2/family_map.py; scripts/cib2/otd_sim/; tests/cib2/test_family_map.py; tests/cib2/test_otd_sim.py; docs/cib2 execution/evidence documents. No product changes.
3. Implementation: static streaming/XML inspection and exact interval accounting; deterministic strict offline replay; read-only source eligibility/provenance audit. No inference or native compilation in delegated workers.
4. Expected effect: reproducible evidence for subsequent per-family offload experiments, and rejection of malformed/incomplete input. No throughput or memory-saving claim yet.
5. Tests: existing CIB2 provenance unit controls plus new synthetic mapper/replay tests, coordinator-run real local IR inventory, protected frozen blob/diff checks. Native build, GPU, API, protocol/agentic regression remain NOT_RUN.
6. Provenance: existing CIB2 plan; offline simulator lineage 86bab01e with current donor revision recorded separately; exact RC1 core source 61afcb26271140347709138b13d678e8b1b5925c fetched by immutable URL. Source availability is not binary build or runtime equivalence.

## Subsequent gates

Next: CIB2-00 exact working-postfix binary/load-path lock and CIB2-01 unchanged protocol controls; CIB2-02 compiled eligibility on a separate accepted tuple; CIB2-04 native RED for oversize lease before any patch, then CIB2-05 instrumentation. Optional packed backend and UMA placement remain separately gated, default off. No blanket 2026.5 upgrade, copied plugin DLL, new pager or policy activation.

GPU tests remain serialized with real process ownership and memory watchdog. The two MiniCPM pressure stops must not be converted into an unattended retry loop. Future accepted experiment requires actual routed kernel/weights_path/ratio evidence and paired correctness before performance. Protected parser behavior, driver, BIOS, production binaries/models/caches and public endpoints remain unchanged.
