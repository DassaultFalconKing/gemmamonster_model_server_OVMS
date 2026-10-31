# LFM2 / LFM2.5: Generation Protocol & Trace Forensics для GEMMAMONSTER

**Срез:** 31 октября 2026 года. **Цель:** native agentic inference в Windows/Arc 140V/OVMS (линия C6) с lossless tool calls, reasoning и корректным продолжением.  
**Статус:** source audit и анализ опубликованных evidence завершены в пределах перечисленных материалов; **локальные сборки, повторные GPU-прогоны и peer-server differential в этом исследовании НЕ выполнялись**.

## Сводка доказательств и критерии

- **VERIFIED (SOURCE)**: непосредственно прочитанный официальный шаблон, конфигурация или исходный код. Не тождественно live PASS.
- **REPORTED (RUN)**: отчёт разработчика с ревизией и результатами, но его сырые trace-артефакты недоступны для независимого прогона.
- **HYPOTHESIS**: правдоподобная причинно-следственная гипотеза; нужен дискриминирующий эксперимент.
- **UNKNOWN**: нет достаточной информации.
- **SYNTHETIC**: выдуманный специально для тестирования пример; ни при каких обстоятельствах не маркировать raw model trace.

## A. LFM Family Protocol Atlas

### 1. Подтверждённые целевые модели и шаблоны

| Checkpoint | Источники | Generation prefix / reasoning | Tool envelope / template | Состояние GEMMAMONSTER |
|---|---|---|---|---|
| **LFM2-24B-A2B** | [Official template](https://huggingface.co/LiquidAI/LFM2-24B-A2B/blob/main/chat_template.jinja), model card, project pinned revision `a3bbacd91a678b97712f0e323e52f8c24ba29542` | `assistant\n`, нет безусловного `<think>`-prefill; шаблон условно сериализует past thinking | Pythonic `[...]`, native tool markers; model-specific system tool-list/history | A9 локальные live cycles PASS по отчёту; Hybrid C 24B 8/8 chains по историческому отчёту |
| **LFM2.5-8B-A1B** | [Official template](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B/blob/main/chat_template.jinja), revision `5dd22602c2e9f6a097b1de4c4efe0658b605015c` в peer dossier | `assistant\n`, при генерации модель может открыть `<think>`; reasoning не обязательно безусловно prefilled | Pythonic native; официальная `format_arg_value` для части строковых значений требует проверки escape-правил | A9 native required PASS; Hybrid C official agent 2/4 (historical) |
| **LFM2.5-24B-A2B** | [Official template](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/chat_template.jinja), [config](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/config.json), [generation config](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/generation_config.json) | **`assistant\n<think>`**, то есть `<think>` уже входит в rendered prompt! Условная сохранность past thinking; `preserve_thinking`. | native envelope; история tool_calls ожидает mapping arguments, строковый OpenAI JSON надо нормализовать | официальная OpenVINO IR и live GEMMAMONSTER протокольная проверка НЕ подтверждены данным аудитом |
| **LFM2.5-1.2B-Instruct** | [Official docs](https://docs.liquid.ai/lfm/key-concepts/tool-use), HF model repo | **Не приписывать 24B prefix автоматически** | Pythonic tool use по docs на уровне семейства; точные IDs и overrides проверить | UNKNOWN |
| **LFM2.5-1.2B-Thinking** | HF model repo; [SGLang cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/LiquidAI/LFM2.5.mdx) | Отдельная схема always-on reasoning; SGLang `qwen3-thinking` в отличие от 8B `qwen3` | Отличие thinking parser по inference recipe | UNKNOWN |
| **LFM2.5-2.6B** | HF model repo; [2026-08-08 incident](https://gist.github.com/osolmaz/ca84291496c43b3943f5e02dfca0a700) | Нельзя наследовать 24B политику | Pythonic tool calls; опубликованы peer streaming regressions | Не квалифицирован в наших Windows-гейтах |
| **LFM2.5-230M, 350M, 1.2B-JP, VL-450M, VL-1.6B, LFM2 small/VL** | [SGLang Liquid cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/LiquidAI/LFM2.5.mdx), Liquid docs | Мультимодальность/специализация требуют отдельной загрузки tokenizer+processor | У некоторых разновидностей нет заявленной tool ability; *наличие семейного имени недостаточно* | OUT OF ACCEPTED SCOPE |

*Не подтверждённое точное количество слоёв/голов/экспертов у каждой модели не восстанавливается по имени.* Для 24B-A2B `config.json` сообщает `Lfm2MoeForCausalLM`, 40 layers, 64 experts, 4 experts routed, `max_position_embeddings=131072`, `eos_token_id=124900`, `bos_token_id=124894` (source-level). Полный набор специальных token IDs всех checkpoints, включая `tool_call_end`, требует tokenizer-level probe с pinned revisions; комментарий OVMS с start-id `124905` (2.5) и `10` (2) ещё не является независимой верификацией.

**Документационная коллизия:** общий [Liquid Chat Template guide](https://docs.liquid.ai/lfm/key-concepts/chat-template) говорит о LFM2/LFM2.5 без `<think>` prefill, но **official 24B-A2B chat_template.jinja явно заканчивается `assistant\n<think>`**. Код конкретной модели первичнее семейного текста. Ещё одно расхождение: общий [tool guide](https://docs.liquid.ai/lfm/key-concepts/tool-use) приписывает LFM2 `<|tool_list_start|>` / `<|tool_response_start|>`-обёртки, в то время как исследованная версия `LFM2-24B-A2B` Jinja использует «List of tools» и plain tool role. Вывод: не включать эти маркеры без revision-specific golden.

**LFM3** теперь документирован Liquid AI с другим Qwen/XML-подобным tool protocol. **LFM3 нельзя пропускать через Lfm2ToolParser по совпадению производителя.**

### 2. Маркеры, по функциям

| Маркер | Семантика | Что известно | Действие в OVMS |
|---|---|---|---|
| `<|startoftext|>` | BOS | официальный tokenizer/template | никогда не трактовать как tool/handoff |
| `<|im_start|>` | роль + начало сообщения | tokenizer/template | prompt serializer, не generated tool event |
| `<|im_end|>` | конец сообщения / EOS для конкретной модели | конфиг/шаблоны | завершение assistant message, **не** `tool_calls` само по себе |
| `<think>` | reasoning start | official templates, Lfm25 parser treats as special | открыть reasoning, если не уже prefilled |
| `</think>` | reasoning end | official templates/parser | переключить в не-reasoning; не исполнить tool |
| `<|tool_call_start|>` | native tool region start | официально special token | начать удержание (retainer), ещё не исполнять |
| `<|tool_call_end|>` | native tool region end | официально special token | при полном envelope + schema validation подтвердить один/несколько вызовов |
| `<|tool_list_start/end|>` | определения инструментов LFM2 | в общих docs и части templates, не универсально | model/revision-specific prompt только |
| `<|tool_response_start/end|>` | результат инструментов в некоторых LFM2 formats | общий docs, model-specific проверка | history serialization, не generated call |
| `CONTINUE_FINAL_MESSAGE_TAG ` | trailing literal marker внутри 24B Jinja | появляется при обработке `content`, удаляется/возвращается | **не считать подтверждённым special token или finish marker** |

Для точной классификации «специальный token ID vs обычная строка» выполнить `convert_tokens_to_ids` и сравнить с `unk_token_id`, проверить `added_tokens_decoder`, `tokenizer.json`; затем `encode()` с `add_special_tokens=False`, decode special=True, токеновые границы. Особенно это важно для `<think>`, tool markers и `CONTINUE_FINAL_MESSAGE_TAG`.

### 3. Восемь разных уровней, которые нельзя смешивать

`API messages → Jinja/Minja rendered prompt → input token IDs → generated token IDs → decoded raw text (specials intact) → reasoning/tool FSM → OpenAI unary/SSE deltas → stored assistant/tool messages → next rendered prompt`.

Ошибка на каждом переходе имеет собственное доказательство. Например, `tool_call_start` присутствует в raw token IDs, но исчезает из decoded text при `skip_special_tokens=true`: это decoder policy, не вина модели. Точно такой риск отдельно закрывает vLLM `Lfm2ToolParser.adjust_request`.

## B. Native generation grammar & finite-state machine

### 1. Каноническая *структурная* грамматика (вывод для компилятора, не утверждение обо всех сырых генерациях)

```ebnf
assistant_turn  = [reasoning], {content | tool_envelope}, [message_end] ;
reasoning       = THINK_OPEN, reasoning_bytes, THINK_CLOSE ;
tool_envelope   = TOOL_START, "[", call, {",", call}, "]", TOOL_END ;
call            = identifier, "(", [kwargs], ")" ;
kwargs          = kwarg, {",", kwarg} ;
kwarg           = identifier, "=", value ;
value           = quoted_string | number | boolean | null
                | "[", [value, {",", value}], "]"
                | "{", [quoted_string, ":", value,
                   {",", quoted_string, ":", value}], "}" ;
boolean         = "True" | "False" | "true" | "false" ;
null            = "None" | "null" ;
```

Синтаксис `value` выше схематический; точная допустимая подграмматика определяется pinned tokenizer/template/`python_literal.hpp` и моделью. `ast.parse` не является лицензией исполнять expression, attribute access, unpacking или function call внутри аргументов.

**Ключевое ограничение:** `assistant_turn` не означает, что любой порядок `reasoning/content/tools` допустим для любой модели. `tool before </think>` и `reasoning resumed after tool` являются **test probes**; в текущем OVMS LFM-профиле вызов **внутри открытого reasoning не должен становиться исполняемым**. В отдельных runtime возможно иное; сначала raw trace+reference template, затем решение о расширении.

### 2. FSM и инварианты

```text
UNKNOWN
 ├─ think-open -------------------> REASONING
 ├─ tool-start -------------------> TOOL_PENDING
 ├─ normal text ------------------> CONTENT
 └─ terminal --------------------> FINAL

REASONING
 ├─ thought text -----------------> REASONING
 ├─ think-close ------------------> CONTENT
 ├─ tool-like text --------------> REASONING (NO EXECUTE)
 └─ STOP/LENGTH ------------------> REASONING_INCOMPLETE / NO TOOL

CONTENT
 ├─ text ------------------------> CONTENT (stream)
 ├─ tool-start (structural) -----> TOOL_PENDING
 ├─ think-open? -----------------> REASONING only if model policy admits
 └─ STOP/EOS --------------------> FINAL

TOOL_PENDING
 ├─ pending bytes ---------------> TOOL_PENDING (withhold tool delta)
 ├─ complete envelope + valid schema -> TOOL_COMMITTED / HANDOFF
 ├─ syntax/schema failure --------> INVALID_TOOL / NO EXECUTE
 └─ STOP/LENGTH before closer ----> INCOMPLETE_TOOL / NO EXECUTE

TOOL_COMMITTED
 ├─ trailing prose --------------> CONTENT
 ├─ additional complete envelope -> TOOL_COMMITTED if parallel allowed
 └─ host tool output ------------> HISTORY_ROUNDTRIP -> next generation
```

**Tool-handoff evidence =** native tool-start token (or verified structural decoded marker), complete matching native end, valid nonempty list and literal parse, tools included in request, recognized tool name, schema-conformant arguments, correct `parallel_tool_calls`/tool_choice, no active reasoning suppression, exactly-once publication. One marker or prose such as `[tool:run_python]`, `I'll call ...`, JSON with key `commands` **не даёт разрешения** на side effect. `finish_reason=tool_calls` присваивается только после успешного `tool_calls`, не по надежде или лексическому совпадению.

**Транзакционность:** `g(), f(a=)` в одной native list должна отвергнуть всю list до публикации любого ID. Если первый tool уже принят и *отдельный второй envelope* оказывается ошибочным, нужен явно определённый per-envelope commit boundary; нельзя задним числом откатить уже переданный на исполнение tool.

### 3. Поведение на трудных переходах

- `<think>` в prompt (24B) не дублировать. Renderer должен выставлять `implicitReasoningStart=true` из суффикса rendered prompt; reasoner должен ожидать закрытие `</think>`.
- `</think>` закрывает reasoning, **не** assistant turn. Сразу следующий native tool_start должен быть обработан тем же router pass, даже если границы в одном decode chunk.
- native tool marker, пришедший как строковый аргумент, не должен закрывать envelope; token ID vs literal text важно зафиксировать в raw tokens.
- `tool_call_end` с текстом после него: инструмент собирается отдельно, текст не теряется и не дублируется; в SSE это может потребовать нескольких deltas.
- Missing end + `finish=length/stop` → incomplete/error; синтетическое закрытие запрещено.
- Несколько независимых envelope в одном assistant turn допускаются только по активному adapter contract, в `parallel=false` reject second envelope.
- `CONTINUE_FINAL_MESSAGE_TAG` не может служить автоматическим условием handoff.

## C. Trace Corpus: реальные свидетельства и классы дефектов

**Важное ограничение:** опубликованные локальные GEMMAMONSTER отчёты зачастую указывают пути `C:\gm\lfm-2026.4\...`, но не включают полный raw token-stream. Прочтение markdown-отчёта **не даёт права утверждать**, что просмотрены исходные логи. Ниже отделены raw-excerpt, агрегатная метрика и воспроизводимый source-level дефект.

| ID | Категория | Источник / revision | Фактическое наблюдение | Первый вероятный слой | Доказательность |
|---|---|---|---|---|---|
| R01 | A valid canonical | [GEMMAMONSTER A9 FINAL-REPORT](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/dev/lfm-family-hardening-20261026/docs/lfm/tool-use-20261027/FINAL-REPORT.md) | 6/6 agent tool loops у двух моделей с native+action-required | end-to-end accepted under constrained mode | REPORTED; полные raw логи off-repo |
| R02 | B / F | [HYBRID-C LOCAL-VALIDATION](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/review/lfm25-design-c-semantic-refit-20261027/docs/lfm/tool-use-20261027/HYBRID-C-LOCAL-VALIDATION-20261027.md), binary SHA `d9663aa6...` | 8B official agent 2/4, два ответа с pseudo-tool prose `[ cwd() ]...` вместо native tool call | generated semantic protocol (модель/selection), не retainer | REPORTED, нужно raw token stream |
| R03 | D parser defect | тот же Hybrid C binary | корректный standalone `{"plan":[]}` демонтирован в reasoning | content classification | REPORTED и подтверждённой source cleanup гипотезой; новый бинарник не тестирован |
| R04 | E or F | [HANDOFF-CLOUD-REVIEW](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/dev/lfm-family-hardening-20261026/docs/lfm/tool-use-20261027/HANDOFF-CLOUD-REVIEW.md) | после write + run_python `tool_choice=none` final prose висит; harness пропускает final answer | generation/finish condition vs harness | REPORTED; raw logs нужны |
| R05 | B policy boundary | A9 FINAL-REPORT | LFM2-24B produces multi-call with `parallel=false`; retainer fail-closed | request contract + model output | REPORTED, корректная реакция политики, не lost tool bug |
| R06 | D streaming defect | [osolmaz repro 2026-08-08](https://gist.github.com/osolmaz/ca84291496c43b3943f5e02dfca0a700), LFM2.5-2.6B vLLM v0.26.0 | nested JSON/quotes в streaming distorted, nonstream правильный | incremental Python completion (`make_valid_python`) | REPORTED with self-contained reproduction; это *исторический* runtime, не доказательство дефекта latest vLLM |
| R07 | D transport/runtime | тот же источник, llama.cpp b10156 | Python string с shell single quotes вызывает HTTP500 в SSE, nonstream корректен | streaming parser/JSON serialization | REPORTED reproducible; latest status проверять отдельно |
| R08 | E continuation | [HF LFM2.5-2.6B discussion #18](https://huggingface.co/LiquidAI/LFM2.5-2.6B/discussions/18) | после ряда tool loops репортятся обрывы/пустые пары, не всегда воспроизводимо | history / model policy | REPORTED/INDETERMINATE, без доступного raw provenance |
| R09 | D parser detection | [llama.cpp issue #20245](https://github.com/ggml-org/llama.cpp/issues/20245) | raw LFM tool representation instead of `tool_calls` (historical; fix #20251) | auto parser / structural detection | REPORTED; исторический дефект |
| R10 | D / F | [LM Studio issue #1593](https://github.com/lmstudio-ai/lmstudio-bug-tracker/issues/1593) | LFM2 tool recognition changes with number of tools | tool catalog / model / adapter | REPORTED; неконклюзивно |
| R11 | A tests | [lfm_retainer_test.cpp](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/review/lfm25-design-c-semantic-refit-20261027/src/test/llm/output_parsers/lfm_retainer_test.cpp) | literal marker nested in string, `1.10`, 64-bit integers, chunk splits и schema validation предусмотрены | C++ deterministic unit | VERIFIED SOURCE, **synthetic fixtures**, не raw model evidence |
| R12 | F | [PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34), head `1b87c2b...` | source fixes JSON preservation and SSE latency; no post-cleanup build/live verification | acceptance governance | VERIFIED PR metadata, CODE UNACCEPTED |

**Граница доказательства:** в R06/R07 демонстрационный native `[write(path=...)]` из README является *описанием класса входа*, не доказанным байт-в-байт generated token stream. Для настоящих raw traces приоритет: локальные saved `raw_output`, token IDs, `skip_special_tokens`, source revision, request payload, parser events и API deltas. Не смешивать их с метриками и документационными примерами.

**Таксономия**: A canonical valid; B noncanonical valid; C malformed model generation; D runtime/parser/decoder; E history/continuation; F indeterminate. Для каждого нового incident фиксировать самое раннее несовпадение между [token stream] и [API event], а не обвинять модель по последнему видимому `tool_calls=[]`.

## D. Differential: Transformers / llama.cpp / vLLM / SGLang / OpenVINO / OVMS

| Runtime | Source path / механизм | Плюсы | Риски и переносимость в GEMMAMONSTER |
|---|---|---|---|
| **Transformers** | `tokenizer.apply_chat_template()` + per-checkpoint Jinja | Референс rendered prompt, `thinking` alias, tool-role replay, tokenization | Не является end-to-end tool executor. Golden compare Jinja→Minja для точных checkpoint revisions. |
| **llama.cpp** | [`common/parsers/lfm2.cpp`](https://github.com/ggml-org/llama.cpp/blob/master/common/parsers/lfm2.cpp), [`common/chat-peg-parser.cpp`](https://github.com/ggml-org/llama.cpp/blob/master/common/chat-peg-parser.cpp), [`parsing.md`](https://github.com/ggml-org/llama.cpp/blob/master/docs/development/parsing.md) | PEG, Pythonic structural grammar, optional JSON booleans, reasoning mapping `reasoning_content`→`thinking` | Конкретный parser сейчас допускает optional closed think + content + tool envelope; сложные mid-thought multi transitions требуют отдельной проверки. Не копировать схему без теста. |
| **vLLM** | [`vllm/tool_parsers/lfm2_tool_parser.py`](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/lfm2_tool_parser.py), [`utils.py`](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/utils.py) | `skip_special_tokens=false` при инструментах; ast parser, streaming and nonstream | Исторические проблемы incremental repair. Не копировать `make_valid_python`, изменение leading zeros/quotes как факт. |
| **SGLang** | [`lfm2_detector.py`](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/function_call/lfm2_detector.py), [Liquid cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/LiquidAI/LFM2.5.mdx) | Буферизация native envelope, literal AST, Pythonic+JSON, отдельный reasoning recipe (`qwen3` vs `qwen3-thinking`) | Есть recovery malformed + salvage отдельных siblings: это иная, менее транзакционная политика, для side effects не переносить без ADR. |
| **OpenVINO GenAI** | [openvino.genai](https://github.com/openvinotoolkit/openvino.genai), OV tokenizer, generated token streaming | Транспорт token IDs, decode, structured output конфиг | В этом исследовании **нет независимых парных запусков** против других engine revisions. |
| **OVMS upstream** | [openvinotoolkit/model_server](https://github.com/openvinotoolkit/model_server) | API router и streaming | PR [#4697](https://github.com/openvinotoolkit/model_server/pull/4697) **closed, not merged**. Не считать нашу ветку upstream acceptance. |
| **GEMMAMONSTER A9/Hybrid C** | `src/llm/io_processing/lfm2/{lfm2_tool_parser.cpp,python_literal.hpp,lfm25_reasoning_parser.hpp,tool_grammar.hpp}` + `output_parser.cpp` | Validated registry, strict per-envelope publication, lossless numeric lexemes, native EBNF hard choice, reasoning prefill detection | A9 constrained good; Hybrid C source cleanup not accepted; official 8B agent 2/4, final prose hang и peer differential open. |

**Что переносить**: token ID and exact decode policy (vLLM), PEG as differential oracle (llama.cpp), complete-envelope buffering and separate reasoning recipes (SGLang), canonical Jinja rendered prompt golden (Transformers). **Что не переносить**: неоднозначную модификацию аргументов, regex-only Pythonic parsing, auto-promotion prose, частичное исполнение повреждённой multi-call list.

## E. GAP ANALYSIS: фактические изменения и состояние веток

### 1. Branch truth (критично для интеграции)

- A9 branch `dev/lfm-family-hardening-20261026`, PR upstream [#4697](https://github.com/openvinotoolkit/model_server/pull/4697), commit `990174b4bfc21e0d623c4917ea860246e929bc06`: native tool support, tests и handoff. PR **закрыт без merge**.
- Hybrid C fork [PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34), `review/lfm25-design-c-semantic-refit-20261027`, HEAD `1b87c2b645356c0ea1733a620fab1406029e0986`: **Draft Open**. Изменения после historical Hybrid-C build пока **NOT BUILT / NOT TESTED** на Windows.
- Исторический Hybrid C EXE `d9663aa6ca29880ae6d3d85ff5f341a2461affd7bc539dd2c8cd3df9fa71136e`: 197 PASS / 2 SKIP GTests, official 8B agents 2/4 PASS, LFM2-24B 8/8; валидное `{"plan":[]}` ошибочно демотировалось. SOURCE нового HEAD сохранил валидный JSON, но ретест не подтверждён.
- A9 candidate EXE SHA `95FB62B5DF7D68A880457378A4D3503CC606B5F06A82C23E70010D96358272BA`, 319 PASS/1 SKIP по archived report. Отдельные бинарники и source revisions нельзя смешивать в одну приёмку.

### 2. Code-level verified

1. `lfm2/python_literal.hpp`: ограниченный recursive literal reader до 1MiB, depth64, entries4096, bool/null spelling normalization, escape syntax, duplicate keys reject, exact decimal lexeme preservation. **Базу не переписывать**.
2. `lfm2/lfm2_tool_parser.cpp::retainEnvelope`: сначала полностью проверить list и schema, потом создать IDs и deltas; max4096; `parallel=false` rejects multi/second. **Здоровая транзакционная граница**.
3. `lfm2/generation_config_builder.hpp`: named/required produce native EBNF root; `auto` unconstrained, `none` not promoted, unsupported schema hard-fail. Не заменять на JSON-only.
4. `output_parser.cpp::detectAndSetImplicitReasoningStart`: проверяет суффикс rendered prompt, может корректно обслужить `<think>`-prefill. На 24B новый модельный adapter всё равно требует отдельного golden.
5. `output_parser.cpp::parseToolCallChunk`: сохраняет `remainder` после закрытия tool region и не скармливает его дважды tool parser. **Есть TODO** о phase transitions, если начало и конец попали в один chunk: это точная проверка, **не доказанный провал без теста**.
6. `lfm2/thought_demotion.hpp` + `OutputParser::finishLfm25PendingContent`: ограниченная эвристика classification псевдопланов; полноценный standalone valid JSON теперь сохраняется в `content`. Никаких side effects из псевдоплана.
7. LFM2.5-24B official `render_tool_calls`: OpenAI `function.arguments` строкой не всегда допускается; нужно канонизировать string→mapping до Jinja, не после генерации.

### 3. Gap table

| Gap | Evidence | Fix | Риск Gemma/Qwen |
|---|---|---|---|
| G01 Valid JSON incorrectly demoted (historical) | `{"plan":[]}` на старом EXE | Правка уже в SOURCE; build+GPU regression | Низкий при `tool_parser==lfm2 && reasoning_parser==lfm2` |
| G02 Native call after reasoning boundary in same chunk | `output_parser.cpp` router TODO | Добавить byte-split and all-in-one tests; код менять **только** после RED | Средний: shared router, Gemma handoff |
| G03 8B official agent uses prose not calls | historical 2/4 | controlled native+required vs auto, raw token capture, root choice analysis | Низкий, policy model-local |
| G04 Final prose hang with tool_choice=none | A9 handoff | pinned no-tool streaming + termination log, distinguish endless model vs lost stop | Средний shared streamer |
| G05 LFM2.5-24B history/string arg | official Jinja | JSON.parse string and enforce object mapping, preserving call IDs in API | Средний chat template adapter shared; scope per model |
| G06 Dynamic JSON/pythonic mixed outputs | Liquid JSON instruction + peer tolerances | Legacy Pythonic native as primary; JSON profile opt-in only after raw evidence; fail-close otherwise | Низкий isolated parser |
| G07 Direct vLLM/SGLang/llama parity | `PEER-DOSSIER.md` NOT_RUN | identical fixtures + live raw cross-compare, pin commits | Нет production change |
| G08 Exact token ID atlas | model source comments vs tokenizer | tokenizer/config/token ID JSON snapshots pinned | Нет production change |
| G09 24B export | ADR says not verified | export as independent gate; do not promise running 24B-A2B in OVMS | GPU/resource risk |

## F. C++ Parser Design Specification (minimum delta)

### Interfaces и event-contract

```cpp
struct LfmEvent {
    enum class Kind { ReasoningBytes, ContentBytes, ToolBegin,
                      ToolCommitted, ToolIncomplete, ToolInvalid,
                      MessageEnd, Handoff } kind;
    uint64_t request_seq;
    size_t raw_byte_offset;
    std::optional<int64_t> token_id;
    std::string_view payload;       // borrowed only within callback
};

struct LfmTraceIdentity {
    std::string model_revision, tokenizer_revision, template_sha256;
    std::string ovms_commit, genai_version, parser_profile;
};
```

Изменение дизайна: `OutputParser` остаётся фазовым владельцем, `Lfm2ToolParser` остаётся единственным владельцем native envelope. **Не создавать вторую параллельную FSM для тех же байтов**, вместо этого ввести диагностические events, exact handoff boundary и тестировать существующую router integration.

```text
on_raw_chunk(chunk, token_ids, finish):
  append once to bounded byte queue; record raw offset/hash
  while progress:
    if in reasoning:
      consume up to verified </think>; publish reasoning exactly once
      if tool marker appears before close: keep non-executable per LFM policy
    else if in native tool region:
      retain without emitting speculative args or ID
      on complete envelope: validate entire list + registry/schema; commit once
    else:
      stream proved content incrementally, hold only possible marker suffix
      on tool-start -> native pending; on think-start -> reasoning
  terminal:
    flush legal content; incomplete reasoning -> recorded truncation
    incomplete tool -> discard candidate; NEVER synthesize a call/end marker
    finalize only once; choose finish_reason from committed output/events
```

**Memory rules**: ≤1MiB candidate (already present), total call max4096 (already present, consider tighter operational cap per request), streaming suffix capped to max marker bytes; no quadratic full replay. Logger redacts secrets, truncates raw, full artefacts only opt-in restricted file. IDs once, one call per committed list element, no retried tool on repeated END.

**Literal retainer RLC/TLP-H**: Preserve `VIN`, GUID, Windows path `C:\...`, text containing `\u`, 17-digit strings, `9007199254740993`, `1.10`, `1e3`, Cyrillic, CJK, emoji, control escape. Compare parsed canonical JSON via `json.loads`, also preserve raw per-argument string values exactly. JSON `1.10` vs numeric `1.1` are mathematically equal but **lexical preservation requirement must be tested separately**. Do not silently normalize phone/VIN as numbers.

**Error codes proposal:** `LFM_REGION_INCOMPLETE`, `LFM_TOOL_EMPTY`, `LFM_TOOL_SYNTAX`, `LFM_TOOL_NOT_REGISTERED`, `LFM_TOOL_SCHEMA`, `LFM_TOOL_PARALLEL_DISALLOWED`, `LFM_REASONING_UNCLOSED`, `LFM_RAW_OVERFLOW`, `LFM_HISTORY_ARG_NOT_OBJECT`, `LFM_TEMPLATE_MISMATCH`. Not claims of existing production enums.

## G. History round-trip, generation policies и Test Gates

### 1. OpenAI history → native history (SYNTHETIC illustrative example)

```json
[
  {"role":"system","content":"Use registered tools when required."},
  {"role":"user","content":"Read a file."},
  {"role":"assistant","content":null,
   "tool_calls":[{"id":"call_001","type":"function","function":{"name":"read_file","arguments":"{\"path\":\"C:\\\\work\\\\a.txt\"}"}}]},
  {"role":"tool","tool_call_id":"call_001","content":"sample content"}
]
```

Перед Jinja: `function.arguments` JSON STRING безопасно разобрать в mapping `{"path":"C:\\work\\a.txt"}`; валидировать, что объект, а не string/array. Jinja модельной ревизии сериализует `read_file(path='C:\\work\\a.txt')` (точная кавычка/escape зависит от шаблона), затем `tool` role content и open assistant prefix. **Не вставлять reasoning прошлых ходов повторно**, если `preserve_thinking=false`; `reasoning_content`, `reasoning`, `thinking` нормализовать в один внутренний representation в prompt serializer, но API-доступность сохранять отдельно. `call_001` остаётся API связывающим ID; в нативном тексте LFM обычно нет сопоставимого ID, значит index/order должны быть stable.

Для 24B-A2B render prompt после истории может завершиться `assistant\n<think>`, для 8B-А1В и 24B older обычно `assistant\n`. Конкретное байтовое сравнение `transformers.apply_chat_template(tokenize=False)` и Minja — обязательный gate.

**Round-trip acceptance:** first call → tool result → next prompt, 2/5/10 tool cycles, 1/2/4 parallel, repeated tool, empty tool return, 4KiB code argument, invalid history JSON arguments, different escape/UTF-8 literals, `preserve_thinking` toggles. Передавать возвращённые ID без изменений. SSE/nonstream API final structures must be equal modulo transient ID generation and chunk timing.

### 2. Три generation profiles (первые два экспериментальные, НЕ гарантированные)

| Profile | Tool choice | Guidance | Sampling | Критерий |
|---|---|---|---|---|
| Correctness | `required` или named | native EBNF schema constrained; fail closed | В 24B official generation_config: `temperature=0.1`, `top_k=50`, `repetition_penalty=1.05` — **для этого checkpoint**, другие не наследуют автоматически | 100% valid envelopes/arguments on harness; не равно семантической правильности |
| Balanced | `auto`, модельный template | native parser, никаких forced tool-from-prose; при agent-required действии ставить `required` только на соответствующем шаге | per checkpoint official defaults, сравнить 0.1/0.3 и seeds | tool task success ≥ заданной цели, error class distribution |
| Throughput | `auto` или `none` для чистого текста | без избыточного hard grammar на no-tool шагах | controlled model-local temp/top-k, offload r0 vs r20 | при валидности на golden corpus, измерять TTFT и decoded t/s отдельно |

`temperature=0` может снижать вариативность, но **не делает неправильную политику tool calling правильной**. `top_p`, `max_new_tokens`, default EOS, stop list держать per-checkpoint. **Результат эксперимента**, а не «best preset» из воздуха. Hard required from first token may suppress think; это осознанное изменение semantic path, измерять task success отдельно.

### 3. Test matrix and acceptance gates

В дополнение к уже существующим C++ тестам приложен [`lfm_synthetic_parser_fixtures_72.json`](lfm_synthetic_parser_fixtures_72.json): **72 отдельные SYNTHETIC fixtures**, с входом, модельным профилем, планом byte splits, ожидаемой классификацией, API-style parsed call names/args, state transitions и PASS/FAIL критериями. Это архитектурный тестовый корпус, **не результат выполнения C++ тестов**. Existing tests already cover every two-way split, escaped `<|tool_call_end|>`, exact digits, parallel false, buffer limits; не выдавать новые fixtures за ранее отсутствующее покрытие.

| Layer | Test ID range | Condition | PASS/FAIL |
|---|---|---|---|
| 1 Tokenizer/template | TPL-001..014 (план) | tokenizer IDs, prompt prefixes, `<think>` prefill, null/content/tool_args typing, `preserve_thinking`, Jinja vs Minja | Rendered bytes/tokens identical per pinned checkpoint |
| 2 Raw parser | FIX-001..072 (fixture JSON) | canonical + noncanonical + negative | All valid calls mapped exactly; malformed no execution |
| 3 Streaming | CHUNK-001..072 | 1-byte splits, every 2-way split, mixed SSE, split marker, UTF-8 | unary == SSE final; content emitted once; no speculative IDs |
| 4 Live model | LIVE-001..020 (план) | LFM2-24B, 2.5-8B, 2.5-24B only after actual export gate; fixed prompts/seeds | ≥10 samples per mode; raw token provenance saved |
| 5 Agentic loop | LOOP-001..012 (план) | native+required, auto, no-tools final, 2/5/10 tools, file/JSON/shell; parallel toggles | Consistent tool ledger, no duplicate side effects, final prose termination |
| 6 Regression | REG-001..015 (план) | Gemma4/Qwen, shared OutputParser, no-tools response, long SSE | Existing suites non-regressed |

**Gate levels**: G0 source+pin proof; G1 deterministic tests; G2 Windows clean build + modules; G3 port **18147 only** unary/SSE native; G4 10 official agent loops per variant/mode; G5 fresh cross-engine differential and adverse data. **Не касаться 8137** и ранее принятого production binary до прохождения G0–G4. Любые SOURCE after historical EXE → new SHA, new test report, no inherited PASS.

## H. Trace instrumentation, performance, prioritized roadmap

### Trace events JSONL contract

```json
{
 "seq":12,"request_id":"opaque","model_revision":"pinned-sha",
 "template_sha256":"...","ovms_commit":"...","genai_version":"...",
 "stage":"parser","phase_before":"REASONING","phase_after":"CONTENT",
 "raw_byte_offset":281,"token_offset":91,"token_id":null,
 "event":"THINK_CLOSE","cause":"verified_special_token",
 "finish_reason":null,"error_code":null,
 "raw_artifact_sha256":"...","api_delta_index":8
}
```

Append monotonically ordered events for request ingress (hash messages), rendered prompt SHA, input/output raw token IDs, decode policy, special marker offsets, parser-state change, tool-commit ledger, API SSE deltas, host call result hash, next rendered prompt hash. Файлы с prompts, секретами, персональными данными публиковать нельзя; для отчётов использовать санитарно очищенные артефакты и редактировать пути. **Без raw token stream не различить точно model vs decoder vs parser.**

### Performance на Core Ultra 258V/Arc 140V: не путать цифры

| Конфигурация | Reported client-observed decode | Ограничения свидетельства |
|---|---:|---|
| LFM2.5-8B-A1B-int4-ov, GPU, OFFLOAD_RATIO=0, 128 output, n=3 | **~54.9–55.0 tok/s** | in-repo `task5-gpu-lfm25-bench-RESULT.json`; клиентские first/last SSE deltas, не GPU internal timestamps |
| historical A9 r0 u4 short | ~58.54 tok/s | исходная местная raw matrix off-repo; позднее A/B не подтвердило преимущество |
| historical Hybrid C 8B short A/B, n=3 | u4 **55.12** vs auto **56.24** | иная версия EXE/условия; нельзя объединить с предыдущей матрицей |
| historical offload r20 / r30 | **31.53 / 23.96** tok/s | report-only; падение throughput, ни dyn-KV, ни warm cache в представленном эксперименте не устранили cliff |
| historical Hybrid C LFM2-24B 512 output, short / long input | **37.79 / 34.79** tok/s | report-only; отдельный model/export, не сравнивать напрямую с 8B |

Отличить `prompt tokens/sec` от TG, `TTFT`, server usage completion tokens и client SSE-visible `content`; reasoning stripped from API content не означает, что GPU эти токены не генерировал. При каждом run записывать prompt/token length, context, `max_new_tokens`, batch, seqs, KV precision, offload ratio, weights path, cache dir, CPU/GPU memory, module versions, commit/binary SHA. **Для ускорения не менять parser semantics.**

### Roadmap: практическая очередь

**P0.** Заморозить source+binary identity. Сначала Windows rebuild PR #34 HEAD + GTests, native SSE JSON preservation, candidate `[{...}]` chunk ambiguity, official 8B chain и 24B control; **без merge**. Добавить pinned 24B-A2B official template token golden и JSON string→mapping history adapter.

**P1.** Если RED обнаружится: исправить exact phase transitions в shared `OutputParser`, оставив Lfm2ToolParser retainer и Gemma/Qwen regression tests. Tool handoff/finish reason only on committed native envelope. 1-byte, dual marker and 5–10 turn loops mandatory.

**P2.** Классифицировать 8B official 2/4 pseudo-tools: `auto` vs `required`, fixed seed, rendered template, raw tokens, parser events. Установить, где начинается несоблюдение: модель не генерирует native tool marker или runtime его теряет. Аналогично исследовать `none` prose hang: token stream закончился? EOS возник? Что сделал streamer?

**P3.** Сделать matched differential с pinned Transformers, llama.cpp, vLLM, SGLang, OpenVINO GenAI, OVMS для одинаковых saved raw strings и затем live prompts. Портировать только доказанно нужные элементы, без агрессивного «исправления» аргументов.

**P4.** Отдельно экспорт/интеграция LFM2.5-24B и speed/memory tuning (r0/u4/auto/offload), только после P0–P3. Сначала корректность agentic protocol, затем ускорение.

### Фактологический итог

- **VERIFIED:** native Pythonic envelope, model-specific Jinja differences, LFM2.5-24B `<think>`-prefill, existing GEMMAMONSTER retainer/grammar/policies, PR states.
- **REPORTED:** A9 successful constrained loops, historical 8B official 2/4, 24B 8/8, old false-demotion, client SSE speed and offload cliff, peer historical streaming failures.
- **HYPOTHESIS:** unhandled all-in-one phase transitions can break a subset of streams; official 8B missed calls are generation/choice behavior rather than parser loss; none prose hang may be stop/tokenization.
- **UNKNOWN:** complete Oct31 raw model trace corpus for all scenarios; tokenizer IDs of all variants; post-cleanup live PASS; LFM2.5-24B-A2B actual OpenVINO export and GPU service; full cross-runtime differential; semantic agent success over 10 long loops.

## Primary sources index

1. Liquid [Tool Use](https://docs.liquid.ai/lfm/key-concepts/tool-use), [Chat Template](https://docs.liquid.ai/lfm/key-concepts/chat-template) (current 2026-10-31, includes LFM3 separately).
2. Hugging Face official model files: [LFM2-24B-A2B](https://huggingface.co/LiquidAI/LFM2-24B-A2B/tree/main), [LFM2.5-8B-A1B](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B/tree/main), [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/tree/main) (config/tokenizer/generation/template).
3. llama.cpp [LFM parser](https://github.com/ggml-org/llama.cpp/blob/master/common/parsers/lfm2.cpp), [PEG](https://github.com/ggml-org/llama.cpp/blob/master/common/chat-peg-parser.cpp).
4. vLLM [LFM parser](https://github.com/vllm-project/vllm/blob/main/vllm/tool_parsers/lfm2_tool_parser.py), [Tool Calling guide](https://docs.vllm.ai/en/stable/features/tool_calling/).
5. SGLang [LFM detector](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/function_call/lfm2_detector.py), [Liquid cookbook](https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/LiquidAI/LFM2.5.mdx).
6. GEMMAMONSTER fork [PR #34](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/pull/34), upstream [PR #4697](https://github.com/openvinotoolkit/model_server/pull/4697), [2026-10-27 handoff](https://github.com/DassaultFalconKing/gemmamonster_model_server_OVMS/blob/dev/lfm-family-hardening-20261026/docs/lfm/tool-use-20261027/HANDOFF-CLOUD-REVIEW.md).
7. Peer observed [Aug 8 streaming incident](https://gist.github.com/osolmaz/ca84291496c43b3943f5e02dfca0a700), [llama issue #20245](https://github.com/ggml-org/llama.cpp/issues/20245), [HF LFM2.5-2.6B discussion #18](https://huggingface.co/LiquidAI/LFM2.5-2.6B/discussions/18).

**На уровне доказательств эта работа не утверждает завершённость 100% raw-trace coverage или live correctness: для них необходимы локально записанные token IDs и новый Windows прогон именно свежего HEAD.**
