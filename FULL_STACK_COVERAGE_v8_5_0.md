# Проверка полного покрытия техстека — v8.5.0

## Что добавлено

Автоподбор стека расширен с базового набора REST/Kafka/БД/Batch/CDC до полной матрицы:

- REST API
- gRPC
- SOAP
- API Gateway
- ESB / интеграционная шина
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
- Batch / job
- CDC

## Принцип UI

Пользователь по-прежнему не выбирает стек на основном пути. Он выбирает смысл процесса. Конструктор сам подбирает стек и объясняет выбор.

Ручной выбор остаётся только в экспертном блоке «Переопределить стек вручную».

## Логика выбора

- синхронный внешний вызов → REST API
- быстрый внутренний стабильный вызов → gRPC
- legacy/WSDL → SOAP
- внешний вход, auth, rate limit, routing → API Gateway
- enterprise routing/transformation/legacy landscape → ESB
- сохранение состояния → БД / OLTP
- кэширование/TTL/read-through → Redis cache
- распределённая блокировка → Redis lock
- поисковая/read-model проекция → Search index
- durable event log/replay/fan-out/highload/order key → Kafka
- команды/worker queue/routing/prefetch/DLX → RabbitMQ
- лёгкий stream/consumer group/low latency → Redis Streams
- короткоживущие фоновые задачи → Redis queue
- неизвестный брокер → Generic queue
- поздний статус от внешнего партнёра → Callback/Webhook
- legacy/партнёрский файловый обмен → SFTP/File
- большие документы и payload → Object storage
- пакетная сверка/DWH job → Batch
- передача изменений из OLTP в аналитику → CDC

## Проверки

- `python run_tests.py` → 68/68 passed
- `pytest -q -rs` → 16 passed, 2 skipped
- `python verify_action_grammar_matrix.py` → checked=2880 failures=0
- `python verify_full_stack_coverage.py` → channels=21 single=21 pairwise=441 issues=0
- `python -m py_compile app.py engine.py report.py design_patterns.py invariant_catalog.py ui.py` → OK
- `node --check FORM_JS` → OK

2 skipped — браузерные Playwright-тесты без установленного Chromium в контейнере.
