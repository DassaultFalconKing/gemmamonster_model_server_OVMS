# Frozen parser-green 2026.5 point; semantic refit target 2026.4

**FROZEN / DO NOT CONTINUE ON THIS BASIS. Operator decision: 2026-10-23.**

This freezes the historical **parser-green** point, not the later drafter or current branch runtime. The operator reports a sensitive performance regression in the 2026.5 line and directs preparation of a semantic refit onto the known-good 2026.4 tuple. No new performance experiment, build or inference was run for this freeze; it does not establish the regression's mechanism.

## Exact checkpoints

| Point | Full commit | Evidence scope |
|---|---|---|
| Bounded parser repair | `6378400a6aa984dd064dd47b3a0af9082a7420df` | 2026-10-21 18:28 Europe/Berlin: Gemma 79/79, Qwen 69/69, core 29/29, policy 9/9 |
| Repair report | `de5032f71ca17fe8d61edcf858ea7a030a91c9e6` | Records the BUILD/UNIT PASS checkpoint |
| Integrated product | `ac2d190d565b693c5ca0e67ddae904a4d10d5342` | 2026-10-21 18:54 Europe/Berlin: full diagnostic executable, selected Qwen/Gemma 148/148, zero disabled/errors/failures |

All three commits have dedicated `qwm-parser-green-20261021-*` Git tags. Exact source/tree/archive hashes, historical loaded DLL hashes and auxiliary component identities are in [PARSER-GREEN-20261021-PINS.json](evidence/PARSER-GREEN-20261021-PINS.json). Actual local paths are retained only in the private manifest and private physical-address handoff. The published source lock is retained unchanged.

| Component | Historical source pin |
|---|---|
| OpenVINO | `b5bfb14860320ae2a44d0fc55d78caa9a9d789b9` |
| GenAI | `2decb9ec4bea827e01db47524352ad72d23b33ab` |
| XGrammar | `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba` |
| Minja public lock | `83eb074e42140b0d1194d1dd61f29c31e4515ee9` |
| Minja existing build tree | `1bdb178afd6f527354e17a1db1b3a22b59189f21` (production include tree previously verified identical; distinct tree retained explicitly) |
| Tokenizers | `d73028e255ddc279483fbc6e8ea90dc802e820f5` |

Source pins and actual loaded binary hashes are separate identities. The historical build reused existing staged libraries; this freeze does not invent a fresh dependency rebuild attestation.

## Preserved binaries and limitations

The four focused parser/core/policy executables still match their historical confirmation hashes and have been copied into the private freeze. The historical GenAI DLL was recovered from backup and verified as `7892465a3bca67e103e26b198f47fb1d5c0a98fc2cc7cb4616ba0e8d5ad054da`; the later `442452...` DLL is **excluded** from the parser-green tuple. Matching historical OpenVINO, Tokenizers and available auxiliary DLLs have also been preserved. Current SDK libraries and the staged GPU plugin are labelled with their observation scope; parser tests do not prove GPU loading.

The old full `ovms_test.exe` SHA-256 was `3526f552cf9eab1014eecb2f59cf2e31d5cfc46229499e47bb71625d88bda12f`. Its old output path now contains a different executable. Preserve its historical hash, original command, fresh green XML and log; **do not claim the old full executable itself has been recovered**. Missing/replaced auxiliary binaries are recorded individually in the manifest.

Source commit-tree archives and local pin refs are preserved. Git submodule and LFS payloads are not automatically a self-contained build package. Parser unit fixtures, XML, logs and build receipts are retained privately. There was no inference model in this parser-unit acceptance tuple; Ornith weights/drafters must not be appended to it as if tested here.

## Known-good destination: 2026.4

File version resources and full SHA-256 identities were checked without executing the runtime:

| Layer | Confirmed local identity | SHA-256 |
|---|---|---|
| Core | `2026.4.0-22930-61afcb26271-releases/2026/4` | `829c4642e287522f8a8e748a726d4ad3117a701e22ab46adc82771f98e5d2f7e` |
| GPU plugin | `2026.4.0-22930-61afcb26271-moe38545-backport` | `21a2fd9f5d856c297416059325832f0f902c84a4e78b840f859ca508f5aea66d` |
| GenAI | `2026.4.0.0-3401-5f7f1278107` | `5a2904f2564e4ce002db5ef5fe003a782e6f296f6377cd66df1b2db41d4c5e8d` |
| OVMS | operator-designated `073ED783...` executable | `073ed783610883f9060fe861736c683a7edff59937b25dbd18e1fdeea14007fc` |

Operator-established decode baseline: **31.8-33.0 tok/s**; not retested here. Operator-provided existing GenAI capabilities: `QwenXMLParametersFormat`, `qwen_xml_parameter`, `TriggeredTags`, `TagsWithSeparator`, `stop_after_first`. Their presence does not by itself establish semantic equivalence; source mapping and negative controls belong to refit preparation. A separate copy of these reference binaries and their physical addresses is retained privately; the original runtime was not changed.

## Work rule for every agent

1. Do not resume the 2026.5 drafter benchmark, optimize this runtime, advance its dependencies or promote it. Earlier resume instructions are superseded by this freeze.
2. Preserve the frozen source/artifact identities. Never rebuild into their directories, overwrite snapshots, or reset the current shared checkout to an old commit.
3. Next work is **preparation of a semantic refit on the exact known-good 2026.4 basis**, in separate future workspace/artifact locations. Inventory the semantic changes and existing 2026.4 APIs first; do not merge the 2026.5 dependency cohort wholesale or perform a blanket downgrade of shared directories.
4. Carry parser behavior/contracts and tests: content visibility vs internal marker decoding, reasoning routing/terminal drain, raw native-string semantics, Qwen schema validation and policy. Preserve the distinction between the two production Gemma repairs and the contradictory escaped-quote fixture correction.
5. Re-establish BUILD/UNIT, protocol/live/agentic gates and a matched performance control on the new tuple. Historic 148/148 does not transfer automatically; neither does the reported 2026.4 decode rate.

**No refit implementation/build/inference has been started by this freeze task. ACCEPTED remains NO.**
