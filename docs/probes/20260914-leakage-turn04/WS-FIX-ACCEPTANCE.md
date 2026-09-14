# WS-FIX candidate acceptance (2026-09-14, evening)

Candidate: `17064400-maintainer-rc2-whitespace-fix-20260914T172941Z`
- ovms.exe SHA256 `AF921BB2…55AF7B0A`, version `2026.4.0.170644006`
- source `17064400`, branch `fix/gemma4-whitespace-loop-20260914`
  (whitespace fix: bounded tool-JSON whitespace, TOOL_CALL diagnostic reason,
  terminal flush, contract tests; src delta vs RC2 in base_output_parser.hpp,
  gemma4_tool_parser.hpp, generation_config_builder.hpp, output_parser.hpp,
  ovms_text_streamer.cpp/hpp, servable.cpp)
- openvino_genai.dll REBUILT (`cac5bb7e…` vs RC2 `9d1639af…`): same GenAI branch
  `7ea25468` + bleeding-edge XGrammar, C++-only, bounded schema API
- openvino.dll / tokenizers / tbb12: byte-identical to RC2 and known-good
  (`def53dd3…`, `ef29a1d5…`, `60e4501c…`)
- model export unchanged (same Heretic dir); same graph (VLM_CB, GPU,
  max_num_seqs 256, prefix_caching true); single-instance discipline throughout

## What was tested (all on Heretic, ports 18091/18092)

- Short probes (RC2 request files verbatim): echo auto, real-Exa auto/minimal/
  required/named, contaminated auto → 6/6 canonical `tool_calls[]`,
  `finish=tool_calls`, content empty, zero `<call:` — NO functional regression.
- Sweep t0 (orig RC2 conditions: temp=0, ptc default, max 256): **32/32 clean**.
- Sweep t1 (K config that failed @28/@22 on RC2: temp=1.0, ptc=false):
  **32/32 clean** — whitespace loop never observed in ~134 candidate generations.
- Plain chat, no tools: `stop`, "15" — base runtime infers fine.
- Agentic (fresh instance): A1 exa call → A2 grounded synthesis
  ("Austria / Hallucination"); B1 direct answer "15" with no tool call
  (correct routing); B2 routes to exa; C1 required exa →
  C2 grounded "The capital of Kazakhstan is Astana." Zero `<call:`.
  **While alive, the model holds real agentic tasks, incl. tool-result roundtrips.**

## What leaked: GPU CL_OUT_OF_RESOURCES deaths (STABILITY REGRESSION, blocker)

- `23620`: served 70 requests (6 short + 32 t0 + 32 t1, all clean), then died:
  `[llm_executor] ... [GPU] CL_OUT_OF_RESOURCES`.
- `4896`, `5400`, `14120`: died on the FIRST grammar inference (A1 exa request),
  same GPU exception. Plain-no-tools inference on `16656` works → the OOM is
  tied to the tools/structured-grammar path, not base model execution.
- RC2 binary NEVER logged a GPU error in any session (~300 requests across
  instances), though RC2 instances also vanished quietly 3x (benign log tails,
  no exception — different, uncharacterized mode).
- Discriminator (same machine state): RC2 served 65 requests fine while fresh
  candidate instances OOM'd on first inference → not global driver exhaustion;
  candidate-specific GPU memory behavior (per-request accumulation in the
  rebuilt-GenAI/XGrammar grammar path is the prime suspect; crash-pinned
  allocations may additionally poison the shared pool for the next launch).

## Candidate-to-candidate changes (RC2 908d6695 → 17064400)

1. ovms.exe rebuilt with the whitespace fix (grammar bounding + LENGTH
   incomplete-frame diagnostic + terminal flush).
2. openvino_genai.dll rebuilt with bleeding-edge XGrammar (only DLL that changed
   hash besides ovms.exe).
3. Deps pins, model export, graph, toolchain profile: unchanged.

## Verdict

- FUNCTIONAL: PASS. No protocol regression, no whitespace loop observed,
  agentic routing/grounding/roundtrips all correct.
- STABILITY: FAIL/BLOCKER. Repeatable GPU OOM deaths on the grammar path;
  an agent session cannot survive on this candidate as-is.
- NEXT: soak with GPU-pool monitoring from a clean driver state (reboot
  baseline) to confirm per-request accumulation rate; then fix the leak in the
  grammar/XGrammar allocation path, not in the parser.

Evidence (local, uncommitted): `C:\Users\testc\AppData\Local\Temp\opencode\wsfix-acceptance-20260914\`
(short/, wsfix-sweep-t0/, wsfix-sweep-t1/, agentic/, plain-*, server.stdout.log
with CL_OUT_OF_RESOURCES lines, run-*.ps1). Live instance at report time:
candidate PID 16656 on 18091/18092.
