# VERIFICATION v8.5.2 — full stack priority fix + ultra-chain check

## Что исправлено относительно v8.5.1

В ультра-цепочке нашли два дефекта приоритета автоподбора стека:

1. `gRPC`-шаг с текстом `fallback to cached profile` ошибочно уходил в `Redis cache`, потому что правило cache срабатывало раньше явного `gRPC`.
2. DB-шаг с `optimistic locking` ошибочно уходил в `Redis lock`, потому что слово `locking` в compensation срабатывало раньше признака записи в БД.

Исправление: явный `gRPC` и признаки записи в БД теперь имеют приоритет над общими словами `cache/lock`.

## Проверки

- `python run_tests.py` → `68/68 passed`
- `pytest -q -rs` → `18 passed, 2 skipped`
- `python verify_action_grammar_matrix.py` → `checked=2880 failures=0`
- `python verify_full_stack_coverage.py` → `channels=21 single=21 pairwise=441 issues=0`
- HTTP smoke: `/`, `/health`, `/api/analyze` отвечают успешно.

`2 skipped` — только browser/Playwright без установленного Chromium.

## Ультра-кейс

Прогнана end-to-end цепочка из 23 шагов и 23 систем. Покрыты все 21 канала:

- REST API
- gRPC
- SOAP
- API Gateway
- ESB
- БД / OLTP
- Redis cache
- Redis lock
- Search index
- Kafka
- RabbitMQ
- Redis Streams
- Redis queue
- Generic queue
- Webhook
- Callback
- SFTP
- File
- Object storage
- Batch
- CDC

Результат: `analyze ok=True`, `UI-reference issues=0`, `missing stack channels=нет`, verdict `red`, score `0.0/10`.

Красный verdict ожидаем: кейс специально содержит деньги, ПДн, регуляторику, legacy, внешних провайдеров, callback/webhook, несколько writer-ов, DWH и ручной разбор.
