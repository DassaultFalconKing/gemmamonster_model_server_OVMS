# Qwenmonster — public C6 companion source cohort

Status: **SOURCE VERIFIED; BUILD, UNIT, GPU AND XML GENERATION NOT VERIFIED**  
Recorded: 2026-10-21  
Canonical publication manifest: [Gemmamonster public component sources](https://github.com/DassaultFalconKing/openvino.genai/blob/docs/public-cohort-20261021/docs/gemmamonster-public-sources.md).  
Canonical machine lock: [public-source-lock.json](https://github.com/DassaultFalconKing/openvino.genai/blob/docs/public-cohort-20261021/docs/public-source-lock.json).  
Local copy: `docs/qwenmonster/public-source-lock.json`.

## Locked cohort (C6 head 20261019)

| Source | SHA | Repo |
|---|---|---|
| OVMS baseline | `ba6ec792c3121850fea167fa7d7e190b25fcdc76` | `DassaultFalconKing/gemmamonster_model_server_OVMS` |
| GenAI | `2decb9ec4bea827e01db47524352ad72d23b33ab` | `DassaultFalconKing/openvino.genai` |
| XGrammar | `c77d5e0d62411d17d4cf55d280463eb5b3bec7ba` | `DassaultFalconKing/xgrammar` |
| OpenVINO | `b5bfb14860320ae2a44d0fc55d78caa9a9d789b9` | `DassaultFalconKing/openvino` |
| Minja | `83eb074e42140b0d1194d1dd61f29c31e4515ee9` | `DassaultFalconKing/minja` |
| Tokenizers | `d73028e255ddc279483fbc6e8ea90dc802e820f5` | `openvinotoolkit/openvino_tokenizers` (upstream, no local patch) |

The published lock's Minja after-lock `1bdb178afd6f527354e17a1db1b3a22b59189f21` is deliberately **not** silently substituted for `83eb074e`. Legacy C6 refs are different cohorts.

## Source-verification findings

- The locked GenAI header explicitly declares `JSONSchema(schema, std::optional<int> whitespace_bound = std::nullopt)` and serializes `max_whitespace_cnt`. This **resolves** the earlier public verification blocker for the 2-argument Gemma call. It does not establish ABI/runtime acceptance.
- Locked GenAI supports `QwenXMLParametersFormat(schema)` → `qwen_xml_parameter`. No XML whitespace-bound parameter equivalent to Gemma `JSONSchema(schema, 2)` is exposed in this struct.
- Locked XGrammar `cpp/grammar_parser.cc` contains the **semantic** `ExcludeToken()` empty-set support from historical `f228574c...`, even though old and new refs are diverged. Locked `cmake/config.cmake` also uses cache-respecting `option()` declarations. Structural source verification only; matcher runtime tests still required.
- Locked Minja has Gemma-native tool capability detection and regression test; locked OpenVINO contains MoECompressed attribute copy and GPU cache serialization changes.
- Neither XGrammar [#650](https://github.com/mlc-ai/xgrammar/issues/650) nor [#802](https://github.com/mlc-ai/xgrammar/issues/802) is fixed by publication. PR [#651](https://github.com/mlc-ai/xgrammar/pull/651), [#803](https://github.com/mlc-ai/xgrammar/pull/803) and [#837](https://github.com/mlc-ai/xgrammar/pull/837) are separate prospective backports.

## Diverged history is not a semantic verdict

Comparing legacy C6 against locked HEAD showed:
- GenAI: 7 ahead / 4 behind;
- XGrammar: 3 ahead / 1 behind;
- OpenVINO: 37 ahead / 1 behind.

Those are **commit graph counts**, not proof of lost or retained functionality. Verify semantic signatures and focused tests; never infer all legacy fixes were forward-ported merely because the new branch is newer. This is a regression gate for future family onboarding.

## Offline preflight (no model or network required)

```powershell
python scripts/qwenmonster/verify_public_cohort.py `
  --genai C:/gm/c6/genai `
  --xgrammar C:/gm/c6/xgrammar `
  --openvino C:/gm/c6/openvino `
  --minja C:/gm/c6/minja `
  --ovms C:/gm/c6/ovms `
  --json-report C:/gm/c6/evidence/qwenmonster-public-cohort-source.json
```

Run this only against checkouts at the pinned commits; if local repository layout differs, adjust source path arguments. The script checks Git identities plus selected semantic source signatures and emits the two required `FETCHCONTENT_SOURCE_DIR_XGRAMMAR` / `FETCHCONTENT_SOURCE_DIR_MINJA` CMake override flags. It does not checkout, build or invoke CMake. Supply `--tokenizers` to check Tokenizers too. Add `--strict-clean` when working trees must be clean.

**Do not use only the GenAI source headers against a different binary.** Match the entire installed GenAI/OpenVINO/XGrammar/Minja cohort. GenAI CMake defaults can fetch upstream bases unless override paths are supplied explicitly. These are not complete build commands.

## Acceptance next

1. `SOURCE`: run offline script on actual checked-out public cohort, save JSON and `git show` for relevant patches.
2. `BUILD`: compile targeted Qwen parser + generation policy against pinned libraries.
3. `MATCHER`: XGrammar empty `ExcludeToken()` test, then distinct Qwen XML zero-args and end-marker drift RED/green tests.
4. `API`: Qwen `none/auto/required/named`, streaming index/id and reasoning-open prompt.
5. `LIVE`: VLM_CB/LM_CB actual GPU and model, single/multi-turn calls, Gemma negative control.

Do not merge or mark ACCEPTED until gates above contain real evidence.
