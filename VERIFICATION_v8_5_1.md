# Проверка v8.5.1 — full stack inference fixed

## Что проверялось
- синтаксис Python и встроенного JS;
- обычные unit/regression тесты ядра;
- pytest-регрессия UI/wizard/auto-route/auto-stack/full-stack;
- матрица wizard action grammar: 2880 конфигураций;
- покрытие каналов: 21 канал, одиночные и pairwise комбинации;
- ordered triples каналов: 21^3 = 9261 цепочка;
- semantic auto-stack inference: проверка, что Redis Streams не схлопывается в Redis cache, Redis queue не схлопывается в Redis cache, generic queue не схлопывается в Kafka, webhook не схлопывается в callback, file не схлопывается в batch;
- HTTP smoke: `/`, `/health`, `/api/analyze`.

## Исправление относительно v8.5.0
В v8.5.0 порядок правил автоподбора стека был недостаточно точным:
- `Redis Streams` мог определяться как `Redis cache`;
- `Redis queue` мог определяться как `Redis cache`;
- generic `очередь` могла уходить в `Kafka`;
- `webhook` мог отображаться как `callback`;
- простой `file` мог отображаться как `batch`.

В v8.5.1 эти правила разделены и покрыты regression-тестом `test_full_stack_inference_v851.py`.

## Результаты

```text
python -m py_compile app.py engine.py report.py design_patterns.py invariant_catalog.py ui.py
OK
```

```text
node --check FORM_JS
OK
```

```text
python run_tests.py
68/68 passed
```

```text
pytest -q -rs
17 passed, 2 skipped
```

2 skipped — browser/Playwright без установленного Chromium в окружении.

```text
python verify_action_grammar_matrix.py
checked=2880 failures=0 colors={'green': 420, 'yellow': 2400, 'red': 60}
```

```text
python verify_full_stack_coverage.py
channels=21 single=21 pairwise=441 issues=0
```

```text
ordered channel triples
triple_channels=9261 issues=0
```

Semantic auto-stack inference:

```text
rest => rest
grpc => grpc
soap => soap
api_gateway => api_gateway
esb => esb
db => db
redis_cache => redis_cache
redis_lock => redis_lock
search => search
kafka => kafka
rabbitmq => rabbitmq
redis_streams => redis_streams
redis_queue => redis_queue
queue => queue
webhook => webhook
callback => callback
sftp => sftp
file => file
object_storage => object_storage
batch => batch
cdc => cdc
```

HTTP smoke:

```text
GET / 200
GET /health 200
POST /api/analyze 200
```

## Вывод
Конструктор и рекомендации по стеку не падают на базовой матрице, pairwise/triple цепочках и semantic-trigger проверках. Основной UX сохранён: пользователь не выбирает стек на старте, система подбирает канал по смыслу шага; ручное переопределение остаётся в экспертном блоке.
