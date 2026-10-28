# failures — Qwen3.8 MTP experiment

## 2026-10-28T13:55Z — graph pbtxt parse fail (draft absolute path)

- **Hypothesis:** Windows absolute `--draft_source_model C:\llm\...` → backslash escapes in pbtxt.
- **Evidence:** `...\qwen38-27b-int4-ov-mtp-20261028T135536848Z.log`
- **Fix:** `--draft_source_model .`
- **Status:** FIXED

## 2026-10-28T13:56Z — LM_CB on full VLM package

- **Error:** Models directory indicates VLM, pipeline non-VLM.
- **Evidence:** `...T135619184Z.log`
- **Status:** EXPECTED

## 2026-10-28T13:56Z — VLM_CB + draft MTP blocked (PRIMARY)

- **Error:** Fast Draft speculative decoding is not supported for VLM pipelines.
- **Evidence:** `...T135646685Z.log`
- **Code:** `servable_initializer.cpp` ~568–571 (no MTP exception)
- **Status:** BLOCKED_CAPABILITY

## 2026-10-28T13:57Z — ATTENTION_BACKEND=PA unknown

- **Error:** Option not found: ATTENTION_BACKEND
- **Evidence:** `...baseline...T135713730Z.log`
- **Fix:** PA removed from default; `-AttentionPA` opt-in
- **Status:** FIXED (not re-proven after fix — never reached ready)

## 2026-10-28T13:58Z — LM staging still needs vision IR

- **Setup:** `Qwen3.8-27B-int4-ov-lm-mtp` hardlinks without `openvino_vision_*`; `language_model_only=true`
- **Error:** Could not open `openvino_vision_embeddings_model.xml`
- **Evidence:** `...T135830348Z.log`
- **Status:** FAIL (workaround insufficient)

## 2026-10-28 ~stock probe — OVMS 2026.4.0 crash

- **Setup:** `C:\llm\ovms\ovms.exe` + VLM_CB + draft `.`
- **Result:** exit `-1073741515` (likely missing DLL); no useful log
- **Status:** INCONCLUSIVE
