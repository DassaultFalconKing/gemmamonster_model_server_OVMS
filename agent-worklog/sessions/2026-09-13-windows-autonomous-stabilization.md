# Windows autonomous stabilization — 2026-09-13

BRANCH: integration/gemmamonster-rc2-semantic-refit-20260912
START_HEAD: e7cd10a9c20877fd3b82fabd363a744583d69099
PACKAGE: NO
ELIGIBLE_FOR_ACCEPTANCE: NO (validation in progress)

## Publication baseline

Fetched origin. Verified remote 689bbd512bf180d567599baf7155eaf0d514e4ee is an ancestor of 19f432ef3, and that source commit is an ancestor of e7cd10a9c. Pushed without force; re-fetched. Local and remote HEAD both e7cd10a9c20877fd3b82fabd363a744583d69099.

Inherited dirty file: src/version.hpp contains 2026.4.0.689bbd512 / --config=win_mp_on_py_on build stamp. Excluded from source commits.

## D3 investigation

Evidence directory: C:\git\artifacts\windows-autonomous-20260913.

Initial official windows_setupvars.bat cannot initialize on this host: it requires the standard Program Files MSVC path, while installed compiler is C:\BuildTools. Used the maintained Enter-GemmamonsterEnv.ps1 rc1-parity profile (preflight PASS), followed by prescribed C:\opt OpenVINO and OpenCV setup scripts, and the exact binding PYTHONPATH from windows_test.bat. OVMS_MODEL_REPOSITORY_PATH explicitly unset.

Runner initialization mistakes (not product results): Windows PowerShell module discovery after environment sanitation; resolved by pwsh and explicit module import. Dot-sourced preflight overwrites variable Name with OV_USE_BINARY; initial full-run files therefore have that prefix. No test outcome claimed from failed runner initialization.

Full baseline launched with ProcDump -ma -e -t -x. Binary SHA and full environment saved in OV_USE_BINARY.environment.json. Results pending.

Hypothesis from source and inherited logs, not yet proven: unprepared on-disk JSON/pbtxt leaves POSIX paths on Windows; graph fails to load; InferOnSleepingGraph asserts before joining its unloader thread; destroying a joinable std::thread terminates the process. Must distinguish missing sanctioned preparation from source defect using fresh reproduction and controls.

## Collector correction

Initial ProcDump -x launch spent several minutes after test 960 in ntdll heap routines (progress snapshot full-progress.dmp, 3,734,091,045 bytes). Main-thread module offsets include RtlCompareMemory; interpreting this as debugger heap overhead remains a hypothesis. Canceled collector gracefully with -cancel 29152 and terminated only owned test PID 29152. Mark initial run INTERRUPTED, not a test exit verdict. Re-launched full suite normally with redirected stdout/stderr, then attached ProcDump; retained official environment and full filter. Corrected runner to record child ExitCode separately from collector ExitCode. New prefix full-baseline-attach.

## D3 RED and causal chain

Fresh full-baseline-attach: 1281 started / 3152 announced, child exit 3; last started MediapipeStreamFlowAddTest.InferOnSleepingGraph, last completed MediapipeStreamFlowAddTest.Infer (FAILED). Termination dump full-baseline-attach-dumps/ovms_test.exe_260913_193247.dmp (790,121,633 bytes), no exception stream (process termination, not AV). Main thread 29156 stack includes OpenCV terminate handler, ucrtbase, ovms_test. Collector independently records process exit 0x00000003.

Exact command regression: run.ps1 -Filter MediapipeStreamFlowAddTest.InferOnSleepingGraph; d3-red-1/2/3 child exit 3 each. Fixture d3-red-fixture and neighboring predecessor range d3-red-neighbors also exit 3. Classification: intrinsic invalid-fixture precondition, abort/terminate rather than AV; not same-process order contamination.

Causal source chain: on-disk POSIX graph_path is interpreted under Windows fixture base; validation fails, yet registered definition pointer remains non-null; test only asserts pointer, constructs std::thread waiting for first Write; ModelStreamInferImpl cannot create executor from unavailable definition and returns MEDIAPIPE_DEFINITION_NOT_LOADED_YET; fatal ASSERT_EQ returns from test before unloader.join; joinable std::thread destructor invokes terminate, inherited OpenCV terminate handler prints an earlier imdecode error and aborts. Rejected interpretation: the last imdecode error is the direct D3 trigger; isolated failing test has no image input and same exit3.

Minimal test-only patch asserts definition availability before constructing unloader. This repairs only the observed precondition; it does not claim to repair arbitrary later streaming failures. Regression expectation with unprepared files is ordinary FAILED exit1, not exit3/crash. Prepared target must then PASS. Official build running before any GREEN claim.

## D3 validated checkpoint

Official windows_build.bat with Python/tests: exit0, 133.201s, 3 actions; logs d3-build.stdout/stderr.log and d3-build.exit.txt. ovms_test SHA256 AFFA8BD406830730EC3B590D025B8847701EEF260F58CE2E7B1BCD75FB168D85.

Unprepared exact regression after patch: d3-noabort-1/2/3 all ordinary test FAILED exit1 with full final summary and teardown, versus prior abort exit3. Availability assertion repairs proven abort precondition. Then ran prescribed windows_change_test_configs.py (official-config-preparation.log), retaining configs-before.zip backup. Prepared target d3-green PASS1/1 exit0, fixture PASS4/4 exit0, related neighbors PASS6/6 exit0. Source-only commit 215eb1b3c08e55253748d0e0d617917354eed1c6 fix(test): require available graph before starting stream unloader. Pushed without force, fetched, verified local=remote. No new skips/exclusions, no src/llm edits. Full-prepared-1 launched immediately with same environment/binary and prepared data.

Contract: executed python -m unittest tests.python.test_windows_stress_harness_contract, PASS5/5; saved contract-5-5.log.

## D2 path and string fixtures

Original path failures are a preparation omission, not proven product normalization bug. Expected config_standard_dummy base_path is Windows absolute workspace/src/test/dummy after sanctioned transformation; actual unprepared /ovms/src/test/dummy is treated relative to config directory and joined into workspace/src/test/configs//ovms/src/test/dummy. windows_change_test_configs.py preserves JSON escaping using doubled backslashes. Existing getGenericFullPathForSrcTest uses forward slashes for filename strings. No blanket normalization patch. Prepared CAPI family: 14/16 PASS, 2 string tests fail.

Independent string fixture defect: automatic recommended target GPU receives STRING tensor and fails in intel_gpu kernel_selector_helper.cpp:280, unable to convert string data type. Exact RED filter CAPIInference.String:CAPIInference.AcceptInputRejectOutputStringPrecision:HttpRestApiHandlerWithStringModelTest.* gives 4/8 failed, exit1, 3/3 repeated (d2-string-red-1/2/3). Set CPU only in config_string.json and HTTP string CLI fixture. Official build PASS exit0, 88.841s, 23 actions, SHA256 6EE87B9D5864AAEC079863A19FD6B36AFECB6780F37D75F50728F12625113F57. Latest logs copied to d2-build.*; initial D3 raw build logs were inadvertently overwritten by runner, D3 executed result remains recorded above and in tool transcript. Subsequent build labels are distinct. Targeted GREEN8/8, broader22/22, exit0. Commit b264c0a00ac3f4d2e1f8f290c80dbbb1bf9a77e0 fix(test): use CPU for string model API fixtures; pushed/fetched, local=remote. Committed config retains POSIX paths; re-applied official local preparation afterward.

## D4 independent blocker

Full-prepared-1 aborts in embeddings suite setup after 1208 started tests (last completed FileSystem.SetPath); exit3, termination dump 941,123,485 bytes. Isolated EmbeddingsTokenizeHttpTest.* also exit3 (d4-red-isolated). No expected thenlper/gte-small/ov model artifact. Maintained ovms --pull successfully downloaded raw HF repository but did not produce required OpenVINO IR/ov layout; success of pull is not model acceptance. First attempt incorrectly supplied text-only weight_format to embeddings and was rejected by CLI, then corrected. Official windows_prepare_llm_models.bat launched; installs prescribed exporter requirements into new repo-local .venv, no dependency pins modified.

Source causal path: EmbeddingsNodeInitializer::initialize calls SidepacketServable::initialize, which constructs ov::genai::Tokenizer from missing models path; exception crosses Status-returning initializer and graph validate; fixture server thread has no exception conversion, std::terminate exit3. New runtime regression EmbeddingsNodeInitializerTest.MissingModelsReturnsInitializationError invokes real registered initializer with fresh absent path, requires error Status and empty side-packet map. RED build in progress, production untouched for D4.

## D4 exception-contract checkpoint

Regression RED3/3 with exact real initializer yielded C++ exception from core.cpp:84, frontend.cpp:120: Could not open missing/openvino_model.xml. This refines prior hypothesis: failure is already in EmbeddingsServable constructor model read, before tokenizer initialize. Narrow patch converts only ov::Exception around constructor/initialize into logged LLM_NODE_RESOURCE_STATE_INITIALIZATION_FAILED; side-packet insertion occurs only after success. No catch-all or success masking.

Official RED test build PASS37.045s, SHA CB3A1BF065AD64B21255B5B59B97699A2B2FCA5B5FD42E4D11FF6C787B1C9D9D. GREEN official build PASS38.966s, 6 actions; SHA 0A4CA6DBA2CDB4721D57FA3CCC93C5A814EA5EF0BA76A8D7856CED26EB9A3AE1. d4-regression-green PASS1/1, d4-related-green PASS36/36 (initializer, pooling, streaming, CAPI). Original embeddings semantic family remains UNVERIFIED pending required model IR; this checkpoint proves failure-status contract, not missing-artifact acceptance. Commit 7758aafec85ab9da64bf1ccdc8cffddb5587e345 pushed/fetched, local=remote. Full-after-d4 launched immediately. Official model preparer is still installing dependencies and has not exported models; record any concurrent preparation if it starts before suite ends.

## D5 rerank initialization exception

Full-after-d4: 1449 started tests, last completed MediapipeIdleUnloadGuard.MultipleGuardsNested; abort in RerankHttpTest suite setup, exit3; dump ovms_test.exe_260913_194731.dmp (944,069,695 bytes). Same uncaught ov::Exception pattern in separate RerankNodeInitializer (no required BAAI/bge-reranker-base/ov files). Added real registry regression RerankNodeInitializerTest.MissingModelsReturnsInitializationError. Initial test build FAILED due missing test_file_utils.hpp include defining TempDir; corrected, rebuild PASS28.963s, SHA48DA57B8619C61A1CF4CA843F0459C45E6B32E0873490B21B3F34698F5551EE1. RED3/3 ordinary exception failure, exact core.cpp/frontend.cpp missing openvino_model.xml message. Narrow rerank ov::Exception-to-error-Status patch added only after executed RED, GREEN rebuild pending.

## D5 validated failure-status contract

Official GREEN build PASS36.241s, 5 actions, SHA03B9558A97B43C5F3DB2C55527CE581F36736AB733FCC64B5A325830082ED2AD. d5-green PASS2/2 real missing-resource initializer regressions, d5-related-green PASS30/30 rerank chunking/pooling/streaming/initializer checks. Commit 88ac984e2ad7e70586728ced16212b364404e762 fix(rerank): report OpenVINO resource initialization failures; pushed/fetched, local=remote. Original real-model rerank HTTP family is pending IR artifacts. Full-after-d5 launched.

## Exporter environment repair

Official preparer initial attempt stalled on installing setuptools build dependency for optimum. Downloaded diagnostic py-spy wheel to evidence directory, without installing into runtime/global environment. Saved live stack pip-truststore-hang.log: Windows native certificate chain verification pip vendor truststore/_windows.py:436. Package index independently returns200 using verified Python TLS. Installed pip source explicitly supports legacy-certs in cmdoptions.py/index_command.py. Gracefully recorded preparer attempt as INTERRUPTED; killed only its known process tree rooted PID28552, archived raw log as official-model-preparation-truststore-interrupted.log. Restarted same windows_prepare_llm_models.bat with PIP_USE_DEPRECATED=legacy-certs; TLS verification still enabled through certifi, requirements/pins unchanged. It passed previously stuck build dependencies and progressed to normal dependency metadata resolution. This is host exporter environment repair, not a test retry/exclusion/timeout fix.

## D6 STT initialization exception

Full-after-d5 aborted after 1930 started tests; last completed SttServableParseTemperatureTest.positiveTemperatureEnablesSampling. Child exit3, termination dump ovms_test.exe_260913_195429.dmp, 804458415 bytes. Speech2Text fixture requires absent openai/whisper-tiny. Real registry regression SttNodeInitializerTest.MissingModelsReturnsInitializationError RED3/3 exit1 with GenAI pipeline.cpp:24 stream.is_open check for missing/config.json. RED build PASS31.969s, SHA7F8A0D0E2D102C91B05EBC503260FD81E9AB013DBC40A96A51A2EE138356370A. Added narrow ov::Exception-to-error-Status around STT construction and insertion, preserving log and leaving side packets empty on failure. No src/llm edits. GREEN build in progress.

Correction to speculative preparation observation: current tracked windows_prepare_llm_models.bat already specifies --model_name thenlper/gte-small/ov for embedding export; no preparation source patch necessary. Official preparation passed dependency installation and is exporting Kokoro and Whisper; artifact existence will be checked separately from command success.

D6 GREEN official build PASS38.366s, 5 actions, SHA5D31496B5B7D183608EECA98ED9F49E7E55CB53CB053F607B43F9DCC4F8FAC36. Regression PASS1/1, related PASS50/50. Commit d7bc3496b77618cc3d3cf6c389ecedab6a517c9b fix(stt): report OpenVINO resource initialization failures pushed/fetched; local=remote. Full-after-d6 launched immediately. Original STT real-model family remains pending completed export.

## D7 FP32 streaming fixture

StreamingWithOVMSCalculatorsCliTest.OVInferenceCalculatorWith2InputsSendSeparately RED3/3 exit1. Automatic GPU compilation advertises f16 and returns 8.20312 instead of8.2 and100.875 instead of100.9. Test checks exact FP32 stream values. Added target_device CPU only in cli/subconfig/subconfig.json. Official build PASS10.203s, binary unchanged SHA5D31496B5B7D183608EECA98ED9F49E7E55CB53CB053F607B43F9DCC4F8FAC36. First GREEN attempt failed because my Windows PowerShell UTF8 writer introduced BOM, JSON invalid value; removed BOM, d7-green-2 PASS2/2 CLI/config counterparts. Commit06980ea76f3bfcc0adbbc75770762c38863f4bb2 pushed/fetched local=remote. Canonical committed path POSIX; official preparation reapplied.

## D8 assisted decoding device mismatch

Full-after-d6 ended exit3 at assisted decoding, not a continuing hang: collector required time to write 5397248311-byte termination dump ovms_test.exe_260913_200103.dmp. Live dump attempt afterward found no process. Minimal existing test unaryCompletionsJsonSpeculativeDecoding RED3/3 exit3. Automatic GPU selected for test graph while reference pipeline is explicitly CPU f32. GPU initialization exception paged_attention.cpp73 key-cache BY_CHANNEL expected block20 got24, followed by shutdown Python thread mismatch and termination. Device alignment patch limited to two test graphs, no production src/llm edit. First attempt used wrong proto field target_device and failed parsing; corrected to actual LLMCalculatorOptions.device. Official build PASS (d8-build), unchanged binary; family validation in progress. Official model preparation command completed exit0, IR exports and tokenizers recorded in raw log; final helper prints root tokenizer absent, so exit0 alone is not sufficient artifact proof.

D8 family d8-green-2 PASS8/8 exit0, CPU graphs/reference. Commit ccb145e8ffe80ca67b0f633de2484017f2ba67e1 pushed/fetched local=remote. Models-family-ready PASS60/60 exit0 after artifacts exported: Embeddings HTTP/tokenization, MediapipeEmbeddings, Rerank HTTP/tokenization, STT HTTP/streaming. This supplies real-model family validation for D4/D5/D6, distinct from missing-resource regressions. Full-after-d8 launched after sanctioned preparation completed, XML enabled without termination dumps (previous dump5.4GB, disk7.6GB free). Raw full-after-d6 RUN marker count is1769; use recomputed markers/XML for final counts instead of provisional progress counts.
