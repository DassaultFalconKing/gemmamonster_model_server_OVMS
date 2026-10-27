# Рецепт экспорта LFM2.5-24B-A2B в OpenVINO INT4

Нашёл вполне конкретный путь. Есть основания ожидать, что экспорт получится без написания нового конвертера архитектуры.

Главная находка: в исходниках [Optimum Intel](https://github.com/huggingface/optimum-intel/blob/main/optimum/exporters/openvino/model_configs.py?utm_source=chatgpt.com) уже зарегистрирована `LFM2MoeOpenVINOConfig`, поддерживающая `text-generation-with-past`. Для неё существует специальный `Lfm2MoeModelPatcher`, который адаптирует вычисления MoE-экспертов и коротких свёрток к трассировке OpenVINO.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Но обнаружился и потенциальный блокер: экспортёр разрешает Transformers от 5.0 до 5.4.0, тогда как исходная модель указывает в `config.json` версию 5.12.1. Поэтому ставить самый новый Transformers и сразу запускать экспорт не следует.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

LiquidAI/LFM2.5-24B-A2B at main+1



## Предлагаемый маршрут

LiquidAI/LFM2.5-24B-A2B

Оригинальный BF16 checkpoint · \~48 ГБ весов

Transformers 5.3 + Optimum Intel

LFM2MoeModelPatcher · stateful KV/conv cache

NNCF INT4_ASYM

group_size=128 · ratio=0.8

OpenVINO IR

openvino_model.xml + .bin + tokenizer

Gemmamonster / Arc 140V

Проверка загрузки → генерации → agentic tools

Для первого эксперимента я выбираю INT4_ASYM с группой 128 и долей INT4 0,8: это конфигурация уже опубликованной старой LFM2-24B от OpenVINO. Для новой модели это проверенная отправная точка из родственной архитектуры, но не проверенный оптимум.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://huggingface.co\&sz=32)

Hugging Face



## 1. Подготовка окружения

Я бы выполнял сам экспорт не на Core Ultra 258V с 32 ГБ UMA, а на машине с большим объёмом оперативной памяти. Например, на ThinkStation P720 с 384 ГБ, когда она снова доступна.

В отличие от инференса INT4, конвертер сначала должен прочитать большие BF16-веса и построить граф. Для первого запуска я бы выделил от 96 до 128 ГБ RAM и около 150 ГБ свободного диска. Это консервативный бюджет, а не измеренный пик конкретного экспорта.

Рекомендуемая совместимая комбинация для первоначального эксперимента:

| Компонент     | Версия   |
| ------------- | -------- |
| Python        | 3.11     |
| OpenVINO      | 2026.4.0 |
| Optimum Intel | 2.2.0    |
| Transformers  | 5.3.0    |
| NNCF          | 3.4.0    |

Это исследовательский pin, который нужно подтвердить установкой и пробным экспортом, а не уже испытанный набор. Optimum Intel 2.2.0 рекомендует OpenVINO 2026.4 и NNCF 3.4.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### PowerShell: установка

```

$root = 'D:\lfm25-24b-export'
New-Item -ItemType Directory -Force $root | Out-Null

py -3.11 -m venv "$root\.venv"
$py = "$root\.venv\Scripts\python.exe"
$cli = "$root\.venv\Scripts\optimum-cli.exe"

& $py -m pip install --upgrade pip

& $py -m pip install `
  "openvino==2026.4.0" `
  "openvino-tokenizers==2026.4.0.0" `
  "optimum-intel[openvino]==2.2.0" `
  "transformers==5.3.0" `
  "nncf==3.4.0" `
  "accelerate" `
  "huggingface_hub"

& $py -m pip check
& $py -m pip freeze > "$root\requirements.lock.txt"

```

Не устанавливай эти зависимости в существующее окружение OVMS/RC4: получим обычный питоновский зоопарк несовместимых версий.

## 2. Сначала проверка экспортёра без загрузки 48 ГБ

```

& $py -c "
from transformers import AutoConfig
from optimum.exporters.openvino.model_configs import LFM2MoeOpenVINOConfig

cfg = AutoConfig.from_pretrained('LiquidAI/LFM2.5-24B-A2B')
print('Model:', cfg.model_type)
print('Layers:', cfg.num_hidden_layers)
print('Experts:', cfg.num_experts)
print('Vocabulary:', cfg.vocab_size)
print('Exporter min:', LFM2MoeOpenVINOConfig.MIN_TRANSFORMERS_VERSION)
print('Exporter max:', LFM2MoeOpenVINOConfig.MAX_TRANSFORMERS_VERSION)
"

```

Ожидаем `lfm2_moe`, 40 слоёв, 64 эксперта, vocabulary 128000.

Если уже здесь будет ошибка версии или несовместимость полей конфигурации, не надо скачивать все веса. Сначала требуется исправить связку Transformers/Optimum, а не вслепую убирать проверки максимальной версии.

## 3. Скачивание исходной модели

Закрепляем конкретную ревизию Hugging Face и не меняем исходный checkpoint.

\<CodeBlock language="powershell" editable>\
$src = "$root\source"\
$out = "$root\openvino-int4-ratio08"

$revision = & $py -c "\
from huggingface_hub import HfApi\
print(HfApi().model_info('LiquidAI/LFM2.5-24B-A2B').sha)\
"

$revision | Set-Content "$root\source-revision.txt"

$env:LFM_SOURCE_REVISION = $revision\
$env:LFM_SOURCE_DIR = $src

& $py -c "\
import os\
from huggingface_hub import snapshot_download\
snapshot_download(\
&#x20;   repo_id='LiquidAI/LFM2.5-24B-A2B',\
&#x20;   revision=os.environ['LFM_SOURCE_REVISION'],\
&#x20;   local_dir=os.environ['LFM_SOURCE_DIR']\
)\
"\
\</CodeBlock>

## 4. Экспорт с INT4-квантованием

Это основная команда.

\<CodeBlock language="powershell" editable>\
& $cli export openvino \`\
&#x20;   \--model $src \`\
&#x20;   \--task text-generation-with-past \`\
&#x20;   \--weight-format int4 \`\
&#x20;   \--group-size 128 \`\
&#x20;   \--ratio 0.8 \`\
&#x20;   $out

if ($LASTEXITCODE -ne 0) {\
&#x20;   throw "LFM2.5-24B OpenVINO export failed"\
}\
\</CodeBlock>

Я специально использую `text-generation-with-past`, потому что нашей гибридной модели нужны не только attention KV, но и состояние коротких свёрток. Обычный статический граф, который успешно вычисляет первый токен и ломается на следующем, нам совершенно неинтересен.

Указанные параметры поддерживаются CLI Optimum Intel. \<Cite ref="turn484388view2"/>

Если первая конверсия получится, вторым вариантом стоит проверить `--ratio 1.0` для уменьшения веса IR. Именно так квантована опубликованная OpenVINO LFM2.5-8B. \<Cite ref="turn774563view1"/>

## 5. Проверка результата до запуска OVMS

\<CodeBlock language="powershell" editable>\
& $py -c "\
import openvino as ov\
from pathlib import Path

p = Path(r'$out')\
xml = p / 'openvino_model.xml'\
binfile = p / 'openvino_model.bin'

assert xml.is_file(), 'Missing OpenVINO XML'\
assert binfile.is_file(), 'Missing OpenVINO BIN'

model = ov.Core().read_model(str(xml))\
print('IR loaded')\
print('Inputs:', [x.any_name for x in model.inputs])\
print('Outputs:', [x.any_name for x in model.outputs])\
print('BIN GiB:', round(binfile.stat().st_size / 2\*\*30, 2))\
"\
\</CodeBlock>

Здесь проверяется чтение графа, не работоспособность инференса. Затем нужны отдельные испытания: компиляция на GPU, prefill, последовательная генерация, правильная обработка conv-cache, tokenizer, шаблон и только после этого LFM tool parser.

Нельзя считать успешным экспорт, у которого появился `.xml`, но отсутствует рабочее состояние декодирования.

## 6. Альтернативный маршрут через ONNX

Есть ещё одна полезная находка: Liquid AI опубликовала готовый \<Link url="https\://huggingface.co/LiquidAI/LFM2.5-24B-A2B-ONNX" title="LFM2.5-24B-A2B-ONNX"/>. В нём имеются несколько вариантов:

| ONNX-вариант | Размер    | Назначение |
| ------------ | --------- | ---------- |
| Q4           | \~15,3 ГБ | CPU        |
| Q4F16        | \~13,7 ГБ | GPU/CUDA   |
| Q8           | \~27,1 ГБ | CPU        |
| FP16         | \~48 ГБ   | GPU        |

\<Cite ref="turn998769search6"/>

Возможен пробный маршрут `ONNX → ov.convert_model → OpenVINO IR`, но я бы отнёс его к плану B. Готовые ONNX Q4/Q4F16 могут использовать специфические квантованные операторы, которые OpenVINO не обязан преобразовывать напрямую. Кроме того, надо будет правильно связать входы и выходы KV/conv-cache, а не просто сохранить граф в XML.

Зато этот ONNX пригодится для сравнения выходов при диагностике ошибок конверсии из PyTorch.

## 7. Критерий успеха для Gemmamonster

| Гейт                 | Что подтвердить                                                |
| -------------------- | -------------------------------------------------------------- |
| A. Toolchain         | Модель распознаётся, версия совместима                         |
| B. Export            | Получены XML/BIN и артефакты токенизатора                      |
| C. Static validation | Граф читается OpenVINO и имеет ожидаемый интерфейс             |
| D. GPU load          | Arc 140V загружает модель без нарушения memory admission       |
| E. Generation        | Несколько последовательных токенов, корректные KV и conv state |

\| F. Agentic | \`
