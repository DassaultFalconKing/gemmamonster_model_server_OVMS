# Commit review inventory

Classification uses reachability from the frozen upstream lineage tip, not author names or subject heuristics for upstream attribution. Documentation/evidence is a subset of Gemmamonster-specific commits; subjects beginning `docs(` identify that subset and include acceptance, review and handoff records.

## Main-only commits (89)

```text
ee773f6fd6f57c50d02fcc739cfd72ee7b9af7e1 docs(gemmamonster): plan latest-2026.4 protocol refit
611bb52c443041a8b13021f98ce289c1310ccb49 test(gemma4): add latest-2026.4 reasoning refit target
895a55f36fa597eec90b85b7a7ee7111c03e1d9d test(gemma4): specify reasoning boundary refit contracts
6c42277a9c1a500810b6c40cc0d09700489b3648 refactor(gemma4): refit model-native reasoning parser onto 2026.4
04089498f9c1d6b6dfbbd446978a4f6d23038b60 refactor(gemma4): parse reasoning natively on 2026.4
f4dc17d6f46091a1312f1b2df278fc034c2b1104 refactor(gemma4): add parser-owned boundary contracts on 2026.4
e3535f9befcf36b3bb067a87f5b767d4f20f73fd refactor(gemma4): refit hardened native tool parser onto 2026.4
184602f2b45eb81e9529766221e55a312e75059c refactor(gemma4): port hardened native argument state machine to 2026.4
77abdb5207f23d2a14af2a803510c94f7cf17696 refactor(gemma4): refit parser-owned routing and reasoning handoff
87f68a2eb41ca6b831fb1a04377d6b83e2fe689c docs(gemmamonster): keep latest maintainer 2026.4 rc2 pins
ecf838087ba6e05bca11c8391ba36ef4c7d9d5fc test(gemma4): add 2026.4 parallel policy contract target
a8654f0157b34f879f644d66cabf531c735bed1b test(gemma4): specify parallel tool policy on 2026.4
94a2df797374eb0635d37d4570e69dec27aef3dc refactor(gemma4): carry parallel tool policy on 2026.4
30a25edf7cf852f57a42581fcbbbfa08cc9a074f refactor(gemma4): expose fail-closed structured output policy on 2026.4
463f0c8b66b826efcc30f30d4703cb5d9e905256 refactor(gemma4): refit structural tool grammar onto 2026.4 rc2
f63814cac96cdbdf149e6556c94b856a797fff1e refactor(gemma4): normalize refit core to exact protocol blobs
055667ece41731c547638309e061f2bf584fe157 refactor(gemma4): refit OpenAI parallel tool policy onto 2026.4
42afd7ddd2dabeed36f664f66a3f5e88f5498414 test(gemma4): pin repeated same-tool generation contract
cd44c60f39391ef3e9fe17b91a6f92bd1dc9fb28 temporary
4c14520a267e77457dc1408e4e22bc0bd2e49b11 do-not-use
41632c3ee2d92230ddad5a54024b19ccb43e3b43 temporary repair staging
5592aa04d3526f7f7eb5d9b7759c4dabaed4952b fix(test): restore exact fde0762 generation contract
477ff43cc098170f5ede3ab43884ae28043bdb32 fix(gemma4): refit exact repeated same-tool grammar onto 2026.4 rc2
697787fdd596022a8ab28d949ae98c1a6d8b857f test(gemma4): pin prompt-state and template overlay contracts
2f15aeafe09c08cf60c27aa59f3c96bd9750526d refactor(gemma4): refit post-render prompt-state adaptation onto 2026.4 rc2
fa6292618c57240b9e4974635d50260532116cb7 test(gemma4): pin full parser recovery and streamer contracts from fde0762
41eee9bcd9d2d1b9f786204d317826e513b158c5 fix(gemma4): refit special-token phase handoff onto 2026.4 rc2
dbb17a686a56cf7ce4392d9fc3ff390d195dd47e refactor(gemma4): align final tool parser and routing with accepted fde0762
bd1e586cdb903de1f9ab623aa1dfc5d36f08b0e6 refactor(llm): restore proven persistent session continuity on 2026.4 rc2
0d6f486586a365ab634680a95901ea1f97943b27 chore(gemmamonster): add stable 2026.4 package workflow
f791a9c2bbf1ff26c5fd62cf6e65dd24c3767092 test(gemmamonster): define stable candidate provenance contract
792bb5acad074c63b812f03e18ef5104bfc2cb4b refactor(gemmamonster): centralize exact 2026.4 runtime profiles
b636d1ba565bfc8c8c775950d8cafe1613401489 feat(gemmamonster): add exact stable candidate verifier
49973813a42c0c3fa0327c66b0e8ed0ad348bc96 feat(gemmamonster): harden stable builder provenance and runtime A/B
8db4916fb0850095016c7264a34860730a20987b feat(gemmamonster): fail closed on runtime module provenance
9f73fa16e2b598188a49958b7406a2fdc9cdf106 test(gemmamonster): add explicit stable source contract runner
80c753ef282c82b94f5a680c34d16ab016e9550b test(gemmamonster): refit standalone package contract to stable envelope
13bf347836ee7ac547876220d99954378d402834 fix(gemmamonster): restore build-mutated source files byte-exact
d3e4cacb72d910d58686863ea07a173794b61903 chore(gemmamonster): add adversarial stable refit audit gate
bffcf8b2b701268a048822881097b80fd98950c6 docs(gemmamonster): make stable refit build handoff reproducible
97741ef4d18fceac2b5da17b06cc1a33bc120874 fix(gemmamonster): trust PowerShell verifier exceptions
644813b727e80c7c1dc023ef7e05e9264c9bb51f fix(gemmamonster): remove stale verifier exit-code check
ebe105ff858816fd181e64a442aaceec147c456c docs(gemmamonster): restore exact provenance Bericht from fde0762
028ec42a9ae9e12aec735f1fab7526ab0a6f9dcc chore(gemmamonster): require exact fde provenance Bericht in audit
69b9f6af38e0c9d85d1c8243b20255584c852ba6 test(gemmamonster): preserve fail-closed hard tool choice contract
0adee88bc53f2ea93d1bcaaaf46be790d35b7cdb docs(gemmamonster): make first Windows build non-destructive
27bd3b0e886ff07cc3caff1456911c80eec035b1 test(gemmamonster): require exact runtime version fingerprints
2f9fbb16e20b7d427fd5c32b45f70da2369c1c13 feat(gemmamonster): verify exact OpenVINO and GenAI runtime fingerprints
dc668c1667a58c3a399a76e3df5c7678b8cdcc80 fix(gemmamonster): bind source contracts to selected runtime profile
3a49286125b15000234c12be15f597359206c3b6 docs(gemmamonster): define internal delta event ownership model
f043bcc6b3961e13183c8aa63d3e8dd42ddd9dbb docs(gemmamonster): distinguish upstream delta substrate from refit ownership
16df6acd96efea26bfa3d5df8f0c47b71c332b15 docs(gemmamonster): inventory capital 2026.4 refit architecture
00d3841830212243fc3c9d97ab0ac0b1f96dd47a fix(gemmamonster): make stable refit audit invocable
55d0c345cb89e69951debda8fee490c3db08473e fix(gemmamonster): serialize stable audit report reliably
88e69b6151c8f6771cd0d6ef24365d6f44e09d87 fix(gemmamonster): bind builder git arguments
e93d501e6e5672549fbbcb8099df5eabfe721525 fix(windows): honor configured Bazel Visual Studio root
90bfa67c38a17843e33024b3bae097e13f5df949 fix(drogon): select configured Python on Windows
56d28532cb9ead75045727e20c79572aed35ee2e feat(gemmamonster): bundle pinned Optimum CLI tooling
13e60df99fe8534b3e4a67096abbea7e0b883e83 fix(windows): propagate Bazel build failures
0532c884c1580c81b10d697ca655ebedc0aff470 fix(drogon): recognize versioned Windows OS names
5b0738253e068408b5f9f1faf8c03aabddaa8c48 fix(windows): use OpenCV 4.14 vc17 layout
cadfcfae370b15040c0af6b5cfdc3b471e844b40 fix(gemmamonster): build RC2 against isolated dep root, not C:\opt
9d85ea6afe218742b8614409b4ce9b4d0b7dec92 fix(gemmamonster): tolerate bazel execroot link in post-build clean check
7124cfc5773578fee8360dd540ca0541669d7b0c fix(gemmamonster): run packaged --version with setupvars env
982aad3dc7e8545134dad7d98a83aa75ee2f9cf4 fix(gemmamonster): tolerate bazel execroot link in source-contract clean check
794296b7c2af312a8cccdcd01e0ded8fca3b1d95 fix(gemmamonster): open test_platform_utils to src/test subtree
865c87204e87119c01379eab4a91b5762ff6936d fix(gemmamonster): give contract tests explicit runtime PATH and PYTHONHOME
8dc4caabf14331d7b99d446a7fec632b7744a000 feat(gemmamonster): two candidate flavors, lean default plus opt-in optimum bundle
c5b1c9a515774003a30de14d7d6fedbb20a46c4c chore(gemmamonster): ignore bazel execroot convenience links
d836566710d930808004b49729cd8fce7705b3e5 docs(gemmamonster): pay down Delta-vs-JSON comment debt in output_parser.hpp
e8c1220205a7aff6ce24ba9f1f6aca89c8b19b51 fix(gemma4): repair parser and grammar contracts
9a1626260614f68a6282b6799842d5152f0dcdff test(gemma4): prove single-tag grammar multiplicity
ea90b6859144a4d1f8ba49cbd04554dfe8e20e4a fix(gemmamonster): run package version checks with setupvars env, gate optimum-cli on flavor
e60a6627a3a9a87297eb3b1739055ee891972bd0 fix(gemmamonster): launcher spawns ovms with full setupvars env
baa303e0bc34f66f434118d2ef279a263932c6bd test(gemmamonster): add comparable speed benchmark harness
b480b8eb8db3ace5ed38450a7647eaf31e0ab2e5 fix(gemmamonster): launcher puts packaged python on spawned server PATH
a9d7cb8cac9b7a336324de65839df94ec1f10c5c fix(gemmamonster): provenance pins the 4 shipped DLLs, driver shims informational
4e48080e45499e7caccbf97df7820b709370feaa docs: freeze known-good Gemma4 tool-calling combo
d9c065998feae4d09ad06db0ac2e6dfdcd0505e0 docs: record known-good source and build provenance
2ed8aa624a5182f1188c864160d7715d6163ef59 docs: position Project Gemmamonster OVMS fork
94785076acb43dacaac5f7752ca550a76c6234ac docs(gemmamonster): add canonical current-state anchor
894537899fbc12caa90bfd15cfa4e3a4c2348f3c docs(gemmamonster): pin canonical current-state snapshot
7593b58b8a01d2066d0f0409ed80fdc2630970dc docs(gemmamonster): finalize canonical state index
ef98371ce679c2b9213d2488c3583b823f77ad78 build(gemmamonster): add fail-closed environment preflight
c6cdef5843afa454c077f618874e7023f3e1b50f docs(gemmamonster): require sanitized environment preflight
5beebaa7ecb478729b251223181896a64ed821ef docs(gemmamonster): add canonical Windows manual build runbook
8a54214fed2a0cb01ad17159364996f8787a92fa docs(gemmamonster): link canonical manual build runbook
74538679377fad4f4bb68f284e82c44b686f65c2 docs: expose frozen current RC and fork release downloads
8f970d4236738ae800b01786af7ad5ad843a62c8 docs: label fork Windows packages accurately
```

## Staging-only commits (complete set) (63)

```text
c41202500e09a904534a8d80b3851f4eb0dcb3e5 update OV runtime to 2026.5 dev (#4520)
b935fe8b96a0445f3746297f872b55ed202fa6e5 Accept positive logprobs - report as 0.0 instead of null (#4522)
a3a2abf287d5cb52f454bb1a1a55c0346cd44a35 Fix fuzz build. (#4497)
eb6351421adafcf57f4dd3cbd17fd811ceaae00e mtp demo (#4498)
c4f69fdd62339fe0919016610891bccb1c996379 Improvements of Kokoro-related documentation (#4533)
a9c70edda0cab9cf483121aa4d97ac07c3683d5d Array parsing fix for gemma4 output parser  (#4532)
00fc8b54d69a55ea5ecc7d46b6c424fe20cf572c Embeddings --max_length parameter - error message when value is grater then model's max length (#4521)
fadb3314a3446fd90a7e23ae05ca1e7584d1ed05 add libopenvino_gguf_frontend.so to whitelist (#4538)
6ec5e369a46de4344bc12ef963477c83bfc46ef0 OV from 0910 (#4534)
1e00053baef862c400ae7cbeb266cc5bb017c137 test build-with-token (#4516)
2413b7825df0ec2ec933a02e21fe16045b8624cf groovy changes with improvements for external collaborators (#4407)
500fbaef5f162f7ec5a959d88ee3d160a41db24e Docs: Fix end of file error (#4562)
599f75a2097605b7cf4fc962d8f250db89352fce Remove number of metadata elements check in capi metadata tests (#4558)
a5136cb285482aaef5410a053b5ecd04ff9324ec Move ovms python binding to separate library (#4103)
8488307dfaa2b49c1daac7ff48e4b9c2599533a8 test(gemma4): capture post-4103 tool protocol contracts
bed7a1e54d09edf87c6549978ab9549254fcbdb6 fix(gemma4): harden recursive native argument parsing
e001de937766f702b2e36c93f8747e30ec47c5a9 fix(gemma4): bound registry-aware bare-call recovery
251f4b58c0c1bee57039845b16a6ff8d64a5ab9f test(gemma4): cover special-token phase handoff
f3410cfa8c51ee75307a07703d2b9fb5a76cb768 docs(gemmamonster): refresh Gemma4 parser and generation verdict
a887757ae7546cc5f281d0f14e98f7970f0d0147 fix(gemma4): preserve special-token phase handoff
8495f0cea62cea16cbb3b213e5e17fe4b686fae4 test(gemma4): require native grammar for hard tool choice
9c0b698e0765972d883dd151789a59cfaa49b295 feat(gemma4): enforce required with native tool grammar
45891c27ee202537ca6d512f78db09cac31150f5 test(gemma4): require lazy native grammar for auto tools
5d8327cf6b66f1fd7329db27b7d650771d50273e feat(gemma4): guide auto calls with lazy native trigger
41efa8debd4c98b4d713bf78506e3b2572db300c test(gemma4): pin named tool choice to one native tag
5af1c04724f5d4530c9a5b1907819b128ba7cdf7 feat(gemma4): enforce named tool choice natively
a08d7dae2c9202c438297424f1df9a82907c83a8 test(gemma4): reject competing response and tool grammars
76c792ca20f14a80f037730ba20a569ab7fc4539 fix(gemma4): reject competing structured output policies
92a30faf420110b143a613e85800e1db057fc49b test(gemma4): make hard tool validation fail closed
6eb48031e76a3c7c36def86b900cf613d13f73a0 docs(gemmamonster): checkpoint upstream refit plan
27b66eda147ccbbf90ea5251da4bafdd7cfd3d91 fix(gemma4): mark hard tool grammars as mandatory
5a88a600cc6fda2017d1a2d9042e524b5854a115 docs(gemmamonster): checkpoint local-agent handoff
d90a7e6769fa903d414d13a5617814efe07379b8 docs(gemmamonster): add local refit verification handoff
58fe7b7d8275969fa3b55536c3dd968481cadb6a hygiene(gemma4): restore parser utility declaration include
7d2ef35d4f1cd28b72b6051f4eaa0a24443b4753 test(gemma4): fail hard tool policy at validation boundary
cf6fc0412024a0f358048470da144abaa101046d fix(gemma4): fail hard structured validation at API boundary
9914848098f5405a0742baca33a2cac4693526fe docs(gemmamonster): checkpoint verified API boundary GREEN
18de2c26cf80317113167712f40cd39b7e3b5987 test(gemma4): cover parallel tool call policy at HTTP boundary
7be4b7aa4ac6a72e15e8972d3a0b685c8b01ebf7 fix(gemma4): plumb parallel_tool_calls into Gemma4 generation policy
447718b8daafecd7e9dcc5466a3e1a7a7caf29f6 test(gemma4): reject unsafe tool names in generation policy
547df803094d6a87d0fc07ecc56d74d3ed05822b fix(gemma4): validate tool names before installing native grammar
fe894aad9acb4bee1252dc047f59f3fd61a0c127 test(gemma4): expose phantom tool-call publication on malformed input
81f9a133458601569ebcdfb606bbe9f29e039e30 docs(gemmamonster): checkpoint parallel GREEN, tool-name GREEN, phantom RED
e2bcbc9e3eadba9948c83e6fe2a0766c28ebdb2b docs(gemmamonster): publish adversarial semantic review
4e5bb54a691b4f90ff01269d248098da5c327b7a docs(gemmamonster): record post-Astra P0 recovery checkpoint
76c486675ab0d0fbb2c21cc3b65c69a9edc71328 test(gemma4): preserve explicit hard tool intent at HTTP boundary
3755dc85b9410dd23c2b0ee9dc33f3dcd598009b fix(openai): reject hard tool choice without usable tools
585a6af8e0dd679ef5bdcdf94bbfd6b6b3ada9ba test(gemma4): reject policy-keyword tool name collisions
355ae00c18ea056e7a3bbbfeaa916cc34f55f9e9 fix(gemma4): reserve tool policy names at request boundary
909e21f0770d3feff76b39cc3448ac5f6660cc5b fix(gemma4): commit validated tool envelopes atomically
3c05feb290af98912f257ffda876d971c0d2c16b test(gemma4): pin rendered thought continuation state
c746a9b970ccebc1866b8d199bb567abe803427a fix(gemma4): reconcile rendered thought state before generation
30dfdbfd3b1f0cdd44098642bd099ed0d8e96454 test(gemma4): cover multi-turn tool history contracts
2b1dfb812e603e09ae0e4a105388a472ab3e64c8 fix(gemma4): drain parser progress independent of chunking
31985d037189384ad446c4804fe7ce9184309914 test(gemma4): pin F7 argument contracts
079eb6f66c923dfc86ff2a045e2bb68b91242eef fix(gemma4): enforce object-root tool schemas
474bc82ac04c2c4e5d942314d22a9c7aca21184b test(gemma4): pin bounded candidate guards
66c66140113c4a6be8ce0b11b5aa23ccc774ac22 fix(gemma4): bound malformed tool candidates
5d2db97f8c5dc06eb5f180ab133f664d710ad049 docs(gemmamonster): declare Gemma4 semantic refit frozen
b722aa440b5555041f24e6d6f7aea8bda100bdf7 docs(gemmamonster): pin exact behavioral freeze SHA
801d6fb66faba79c613e195188054eecbc480815 docs(gemmamonster): handoff freeze candidate to live acceptance tester
e6458ef78636113edf12f1aee6bc36825e773651 docs(acceptance): final report for gemma4-u4-mtp experiment
43bc254e8996f17b929afef79f310d0b0b0cc139 docs(acceptance): corrective Gemma4 live acceptance on 2026.5 freeze binary
```

## Upstream commits introduced by clean refit (14)

```text
c41202500e09a904534a8d80b3851f4eb0dcb3e5 update OV runtime to 2026.5 dev (#4520)
b935fe8b96a0445f3746297f872b55ed202fa6e5 Accept positive logprobs - report as 0.0 instead of null (#4522)
a3a2abf287d5cb52f454bb1a1a55c0346cd44a35 Fix fuzz build. (#4497)
eb6351421adafcf57f4dd3cbd17fd811ceaae00e mtp demo (#4498)
c4f69fdd62339fe0919016610891bccb1c996379 Improvements of Kokoro-related documentation (#4533)
a9c70edda0cab9cf483121aa4d97ac07c3683d5d Array parsing fix for gemma4 output parser  (#4532)
00fc8b54d69a55ea5ecc7d46b6c424fe20cf572c Embeddings --max_length parameter - error message when value is grater then model's max length (#4521)
fadb3314a3446fd90a7e23ae05ca1e7584d1ed05 add libopenvino_gguf_frontend.so to whitelist (#4538)
6ec5e369a46de4344bc12ef963477c83bfc46ef0 OV from 0910 (#4534)
1e00053baef862c400ae7cbeb266cc5bb017c137 test build-with-token (#4516)
2413b7825df0ec2ec933a02e21fe16045b8624cf groovy changes with improvements for external collaborators (#4407)
500fbaef5f162f7ec5a959d88ee3d160a41db24e Docs: Fix end of file error (#4562)
599f75a2097605b7cf4fc962d8f250db89352fce Remove number of metadata elements check in capi metadata tests (#4558)
a5136cb285482aaef5410a053b5ecd04ff9324ec Move ovms python binding to separate library (#4103)
```

## Gemmamonster-specific commits (including docs/evidence) (49)

```text
8488307dfaa2b49c1daac7ff48e4b9c2599533a8 test(gemma4): capture post-4103 tool protocol contracts
bed7a1e54d09edf87c6549978ab9549254fcbdb6 fix(gemma4): harden recursive native argument parsing
e001de937766f702b2e36c93f8747e30ec47c5a9 fix(gemma4): bound registry-aware bare-call recovery
251f4b58c0c1bee57039845b16a6ff8d64a5ab9f test(gemma4): cover special-token phase handoff
f3410cfa8c51ee75307a07703d2b9fb5a76cb768 docs(gemmamonster): refresh Gemma4 parser and generation verdict
a887757ae7546cc5f281d0f14e98f7970f0d0147 fix(gemma4): preserve special-token phase handoff
8495f0cea62cea16cbb3b213e5e17fe4b686fae4 test(gemma4): require native grammar for hard tool choice
9c0b698e0765972d883dd151789a59cfaa49b295 feat(gemma4): enforce required with native tool grammar
45891c27ee202537ca6d512f78db09cac31150f5 test(gemma4): require lazy native grammar for auto tools
5d8327cf6b66f1fd7329db27b7d650771d50273e feat(gemma4): guide auto calls with lazy native trigger
41efa8debd4c98b4d713bf78506e3b2572db300c test(gemma4): pin named tool choice to one native tag
5af1c04724f5d4530c9a5b1907819b128ba7cdf7 feat(gemma4): enforce named tool choice natively
a08d7dae2c9202c438297424f1df9a82907c83a8 test(gemma4): reject competing response and tool grammars
76c792ca20f14a80f037730ba20a569ab7fc4539 fix(gemma4): reject competing structured output policies
92a30faf420110b143a613e85800e1db057fc49b test(gemma4): make hard tool validation fail closed
6eb48031e76a3c7c36def86b900cf613d13f73a0 docs(gemmamonster): checkpoint upstream refit plan
27b66eda147ccbbf90ea5251da4bafdd7cfd3d91 fix(gemma4): mark hard tool grammars as mandatory
5a88a600cc6fda2017d1a2d9042e524b5854a115 docs(gemmamonster): checkpoint local-agent handoff
d90a7e6769fa903d414d13a5617814efe07379b8 docs(gemmamonster): add local refit verification handoff
58fe7b7d8275969fa3b55536c3dd968481cadb6a hygiene(gemma4): restore parser utility declaration include
7d2ef35d4f1cd28b72b6051f4eaa0a24443b4753 test(gemma4): fail hard tool policy at validation boundary
cf6fc0412024a0f358048470da144abaa101046d fix(gemma4): fail hard structured validation at API boundary
9914848098f5405a0742baca33a2cac4693526fe docs(gemmamonster): checkpoint verified API boundary GREEN
18de2c26cf80317113167712f40cd39b7e3b5987 test(gemma4): cover parallel tool call policy at HTTP boundary
7be4b7aa4ac6a72e15e8972d3a0b685c8b01ebf7 fix(gemma4): plumb parallel_tool_calls into Gemma4 generation policy
447718b8daafecd7e9dcc5466a3e1a7a7caf29f6 test(gemma4): reject unsafe tool names in generation policy
547df803094d6a87d0fc07ecc56d74d3ed05822b fix(gemma4): validate tool names before installing native grammar
fe894aad9acb4bee1252dc047f59f3fd61a0c127 test(gemma4): expose phantom tool-call publication on malformed input
81f9a133458601569ebcdfb606bbe9f29e039e30 docs(gemmamonster): checkpoint parallel GREEN, tool-name GREEN, phantom RED
e2bcbc9e3eadba9948c83e6fe2a0766c28ebdb2b docs(gemmamonster): publish adversarial semantic review
4e5bb54a691b4f90ff01269d248098da5c327b7a docs(gemmamonster): record post-Astra P0 recovery checkpoint
76c486675ab0d0fbb2c21cc3b65c69a9edc71328 test(gemma4): preserve explicit hard tool intent at HTTP boundary
3755dc85b9410dd23c2b0ee9dc33f3dcd598009b fix(openai): reject hard tool choice without usable tools
585a6af8e0dd679ef5bdcdf94bbfd6b6b3ada9ba test(gemma4): reject policy-keyword tool name collisions
355ae00c18ea056e7a3bbbfeaa916cc34f55f9e9 fix(gemma4): reserve tool policy names at request boundary
909e21f0770d3feff76b39cc3448ac5f6660cc5b fix(gemma4): commit validated tool envelopes atomically
3c05feb290af98912f257ffda876d971c0d2c16b test(gemma4): pin rendered thought continuation state
c746a9b970ccebc1866b8d199bb567abe803427a fix(gemma4): reconcile rendered thought state before generation
30dfdbfd3b1f0cdd44098642bd099ed0d8e96454 test(gemma4): cover multi-turn tool history contracts
2b1dfb812e603e09ae0e4a105388a472ab3e64c8 fix(gemma4): drain parser progress independent of chunking
31985d037189384ad446c4804fe7ce9184309914 test(gemma4): pin F7 argument contracts
079eb6f66c923dfc86ff2a045e2bb68b91242eef fix(gemma4): enforce object-root tool schemas
474bc82ac04c2c4e5d942314d22a9c7aca21184b test(gemma4): pin bounded candidate guards
66c66140113c4a6be8ce0b11b5aa23ccc774ac22 fix(gemma4): bound malformed tool candidates
5d2db97f8c5dc06eb5f180ab133f664d710ad049 docs(gemmamonster): declare Gemma4 semantic refit frozen
b722aa440b5555041f24e6d6f7aea8bda100bdf7 docs(gemmamonster): pin exact behavioral freeze SHA
801d6fb66faba79c613e195188054eecbc480815 docs(gemmamonster): handoff freeze candidate to live acceptance tester
e6458ef78636113edf12f1aee6bc36825e773651 docs(acceptance): final report for gemma4-u4-mtp experiment
43bc254e8996f17b929afef79f310d0b0b0cc139 docs(acceptance): corrective Gemma4 live acceptance on 2026.5 freeze binary
```

## Acceptance/evidence/documentation commits (subset) (13)

```text
f3410cfa8c51ee75307a07703d2b9fb5a76cb768 docs(gemmamonster): refresh Gemma4 parser and generation verdict
6eb48031e76a3c7c36def86b900cf613d13f73a0 docs(gemmamonster): checkpoint upstream refit plan
5a88a600cc6fda2017d1a2d9042e524b5854a115 docs(gemmamonster): checkpoint local-agent handoff
d90a7e6769fa903d414d13a5617814efe07379b8 docs(gemmamonster): add local refit verification handoff
9914848098f5405a0742baca33a2cac4693526fe docs(gemmamonster): checkpoint verified API boundary GREEN
81f9a133458601569ebcdfb606bbe9f29e039e30 docs(gemmamonster): checkpoint parallel GREEN, tool-name GREEN, phantom RED
e2bcbc9e3eadba9948c83e6fe2a0766c28ebdb2b docs(gemmamonster): publish adversarial semantic review
4e5bb54a691b4f90ff01269d248098da5c327b7a docs(gemmamonster): record post-Astra P0 recovery checkpoint
5d2db97f8c5dc06eb5f180ab133f664d710ad049 docs(gemmamonster): declare Gemma4 semantic refit frozen
b722aa440b5555041f24e6d6f7aea8bda100bdf7 docs(gemmamonster): pin exact behavioral freeze SHA
801d6fb66faba79c613e195188054eecbc480815 docs(gemmamonster): handoff freeze candidate to live acceptance tester
e6458ef78636113edf12f1aee6bc36825e773651 docs(acceptance): final report for gemma4-u4-mtp experiment
43bc254e8996f17b929afef79f310d0b0b0cc139 docs(acceptance): corrective Gemma4 live acceptance on 2026.5 freeze binary
```
