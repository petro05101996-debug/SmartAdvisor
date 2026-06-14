# Проверка v8.4.4: wizard UI case coverage

Проверка выполнена для нового пошагового UI: старт + действие + время результата + обработка результата + масштаб.

## Что было найдено и исправлено

1. В 120 базовых комбинациях wizard создавал ссылку на `Внешняя система / поставщик`, но не добавлял эту систему в список участников. Исправлено: если результат может быть позже/неизвестен, поставщик добавляется как external-система.
2. В надстройке Outbox/Inbox при отсутствии Kafka в базовой цепочке создавался Inbox-шаг от `Kafka`, но брокер не добавлялся в список систем. Исправлено: перед добавлением Inbox UI явно добавляет broker.

## Проверка базовой матрицы

Комбинации:

- 5 вариантов старта
- 6 вариантов основного действия
- 4 варианта времени результата
- 6 вариантов обработки результата
- 4 варианта масштаба

Итого: `5 × 6 × 4 × 6 × 4 = 2880`.

Результат после исправлений:

```text
BASE checked=2880 bad=0 ui_reference_issues=0
colors={'green': 1064, 'yellow': 1768, 'red': 48}
avg_score=7.38 min_score=4.9 max_score=9.0
missing_artifacts={}
```

Все базовые комбинации:

- проходят через `analyze(payload)`;
- не создают шагов на отсутствующие системы;
- генерируют main flow;
- генерируют DDL/schema;
- генерируют checklist;
- генерируют event contract skeleton.

## Проверка надстроек сложности

Надстройки:

- Retry/DLQ/replay
- Outbox/Inbox
- Ручная сверка
- Fan-in / join
- REST-обогащение
- Legacy-потребитель
- DWH/аналитика
- Миграция контракта
- Аудит/регуляторика
- ПДн/security

Payload-level проверка:

```text
SINGLE_MODULE_PAYLOAD_VALIDATE checked=28800 ui_reference_issues=0
SUBSETS_HARD_PAYLOAD_VALIDATE checked=1024 ui_reference_issues=0
```

## Анализ сложных выборок

```text
SINGLE_MODULE_SEEDS checked=100 bad=0 ui_reference_issues=0
colors={'yellow': 75, 'green': 18, 'red': 7}
avg_score=6.91 min_score=3.7 max_score=9.0
missing_artifacts={}

PAIR_MODULE_SEEDS checked=270 bad=0 ui_reference_issues=0
colors={'yellow': 211, 'red': 47, 'green': 12}
avg_score=6.25 min_score=1.2 max_score=8.3
missing_artifacts={}

ALL_SUBSETS_HARD checked=1024 bad=0 ui_reference_issues=0
colors={'yellow': 260, 'red': 764}
avg_score=4.46 min_score=2.3 max_score=7.1
missing_artifacts={}
```

Красные результаты в тяжёлых наборах ожидаемы: они означают, что модель нашла production-риски, а не что UI/ядро сломались.

Чаще всего срабатывали правила:

- timeout_inversion
- poison_retry
- sync_chain_depth
- event_core_fields
- multiple_writers
- migration_cutover
- cdc_projection_controls
- read_your_writes
- api_error_contract
- async_reconciliation_missing

## Регрессия и smoke

```text
python -m py_compile app.py engine.py report.py design_patterns.py invariant_catalog.py ui.py check_ui_wizard_cases.py
OK

node --check FORM_JS
OK

python run_tests.py
68/68 passed

pytest -q test_ui_e2e.py test_semantic_composer.py test_wizard_ui_v843.py -rs
8 passed, 2 skipped
```

`2 skipped` — это browser Playwright-тесты без установленного Chromium в окружении.

HTTP smoke:

```text
GET /        200
GET /health  {"ok":true}
POST /api/analyze  {"ok":true,"id":"..."}
GET /run/<id>     200
GET /run/<id>.md  200
```
