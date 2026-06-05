# Архитектурное решение по интеграции: E2E интеграция заявки со скорингом, CRM и DWH

Дата генерации: 2026-06-05 18:05

---

## 0. Финальное решение в 5 строк для новичка

- Проектировать: Неинвазивное расширение существующего процесса.
- Ключевые контроли: Saga / Process State Machine, Integration Publisher / REST Enrichment before Kafka, PostgreSQL OLTP, Highload Controls.
- MVP: Зафиксировать входной контракт и error model.
- Production: Полная наблюдаемость: latency/error rate/availability, traces, stuck process age, DLQ/retry rate.
- Сначала исправить: Не определена свежесть enrichment-данных; Некорректная ссылка на parent step; Нужны события/очереди, но broker/queue не выбран.

## 1. Резюме

**Тип задачи:** e2e_chain

**Нагрузка:** highload, RPS/TPS=500, peak=5

**Рекомендованный вариант:** Неинвазивное расширение существующего процесса

**Оценка варианта:** 100%

**Готовность требований:** 53%

### Пробелы

- Шаг Изменить договор ссылается на несуществующий parent=0.

## 1A. Введённые матрицы полного описания процесса

- Целевые связи: 3 строк
- Переходы процесса: 3 строк
- Контракты: 3 строк
- Бизнес-правила: 3 строк
- Capacity: 2 строк
- Observability: 4 строк
- Rollout/migration: 3 строк
- Data quality/lineage: 3 строк

### Целевые связи

- API/Process Manager → Scoring; channel=REST; contract=POST /score/v1/decision; retry=yes/backoff; dlq=no; idempotency=idempotencyKey

- API/Process Manager → Kafka; channel=Kafka; contract=ApplicationStatusChanged.v1; retry=yes; dlq=yes; idempotency=eventId

- Kafka Consumer → CRM; channel=REST; contract=PUT /crm/v1/application-status; retry=yes/backoff; dlq=yes; idempotency=eventId+aggregateVersion

### Бизнес-правила

- BR1: if сумма > лимита → отправить на ручную проверку [S2]

- BR2: if договор закрыт → не публиковать событие обновления [S3]

- BR3: if пришло старое событие version ниже текущей → игнорировать и записать аудит [Consumer]

## 2. Quality gate требований

**Статус:** risky — Можно сформировать предварительный дизайн, но перед разработкой нужно закрыть открытые вопросы.

### Критично уточнить

1. Какая допустимая задержка DWH, как делаем reconciliation, backfill, lineage и data quality?
2. Какой ключ порядка, sequence/version, и что делать со старыми/out-of-order событиями?
3. Какие target RPS/TPS, peak, payload size, retention, допустимый lag, DB write rate и лимиты внешних API?
4. Кто business owner события, кто technical publisher, кто owner enrichment-данных?
5. Обогащение обязательно или можно публиковать partial payload; что делаем при таймауте enrichment REST?
6. Enrichment-данные нужны на момент изменения сущности, на момент публикации или best effort?
7. Какие поля являются ПДн/секретами, где маскирование, шифрование, retention и аудит доступа?
8. Какие ограничения являются жёсткими, а какие можно пересогласовать: новый сервис, новая инфраструктура, изменение source, сроки, бюджет?
9. Какой остаточный риск бизнес готов принять временно, и какой deadline для перехода к целевому варианту?
10. Что является главным результатом: команда/операция, событие, read-model, batch file, webhook intake, DWH pipeline или migration?

## 2A. Ограничения, компромиссы и реалистичный вариант

### Жёсткие ограничения

- Source-систему нельзя менять: outbox/state-machine в source недоступны без пересогласования.
- Пояснение пользователя: Например: новый сервис слишком дорогой; source менять нельзя; Kafka уже есть только в другом контуре; сроки 2 недели; нужен безопасный минимум.

### Реалистичный v1 при ограничениях

- Реальный v1: CDC/polling/read-only export + enrichment + publish snapshot/export event, а не полноценный domain event.
- Обязательно: watermark/offset, gap detection, reconciliation, manual reload/replay.

### Целевой вариант без ограничений

- Целевой вариант: архитектура без искусственных ограничений — отдельные границы ответственности, outbox/inbox, dedicated publisher/orchestrator при необходимости, полная observability.

### Остаточные риски компромисса

- Нет атомарной гарантии commit source → event; возможны задержки, пропуски при ошибке polling/CDC и расхождения freshness.
- Название события должно быть честным: EntitySnapshotPrepared/ExportReady, не EntityUpdated от имени source.

### Что нельзя выкидывать даже в компромиссе

- correlationId/requestId во всех каналах
- timeouts на sync/REST вызовах
- owner и alert для каждой ошибки
- идемпотентность при retry/async
- логирование без ПДн/секретов
- schema/versioning события
- DLQ/retry/reprocess policy для broker/consumer
- businessOwner/sourceSystem в событии
- enrichmentConsistency/dataAsOf
- FAILED/reprocess для enrichment
- operation table/idempotency key/unique constraint
- audit + reconciliation

### Phase 2 / долг по архитектуре

- Пересогласовать минимальный outbox/source integration table для перехода от export-события к source-owned domain event.

## 2B. Матрица вариантов: правильно / компромисс / workaround

### A. Архитектурно правильный вариант

Когда: Когда можно менять нужные компоненты и есть бюджет на production controls.

Что делать:

- Использовать целевой top-level паттерн: Неинвазивное расширение существующего процесса.
- Разделить ownership: source of truth, technical publisher/adapter, consumer/target, operations owner.
- Сразу заложить production controls: Outbox/Inbox или эквивалент, DLQ/quarantine, replay, observability, contract tests.
- Source-owned outbox + technical publisher + REST enrichment after commit + event version/sourceEventId/dataAsOf.

Риск: Ниже, но дороже/дольше.

### B. Безопасный компромисс

Когда: Когда стек/сроки/бюджет ограничены.

Что делать:

- Оставить существующие ограничения стека/бюджета, но добавить минимально безопасные контроли: correlationId, idempotency/replay where retries exist, timeouts + retry limits, owner + alert, monitoring + runbook, ADR with accepted residual risk.
- Не переименовывать компромисс в “идеальную архитектуру”: явно указать residual risk и дату пересмотра.
- Если source менять нельзя: честный snapshot/export event через CDC/polling + reconciliation, не domain EntityUpdated.

Риск: Средний; допустим только с ADR, monitoring и планом phase 2.

### C. Временный workaround

Когда: Только для короткого периода или emergency.

Что делать:

- Допустим только как временный workaround: manual/reconciliation path, ограниченный scope, feature flag/kill switch, ежедневный контроль расхождений.
- Запрещено скрывать отсутствие ключевых гарантий: если нет atomics/replay/idempotency — это должно быть blocker или accepted risk.
- Не отдавать publish ownership сервису, где “просто есть Kafka”, без явного source ownership и контроля расхождений.

Риск: Высокий; нужен срок жизни, owner, rollback и ручная сверка.

## 3. Главная архитектура и внутренние слои

**Главная архитектура:** Неинвазивное расширение существующего процесса

### Кратко

- Целевая архитектура должна рассматриваться как композиция слоёв, а не как один паттерн.

### Слои

### 1. Входной контур

Принять команду/запрос безопасно и быстро

Компоненты:

- Service API
- Idempotency validation
- Request validation

Контроли:

- Auth/RBAC
- rate limit
- correlationId
- единая error model

### 2. Core process

Управляемая state machine/Saga для многошаговой цепочки

Компоненты:

- Process Manager
- process_steps
- status_history

Контроли:

- timeout per step
- retry policy
- compensation
- manual recovery

Риски:

- Без owner процесса Saga превратится в distributed mess.

### 3A. Event enrichment before Kafka

Собрать финальный payload без переноса ownership события

Компоненты:

- Source outbox/integration table
- Integration Publisher
- REST enrichment adapter
- Kafka final topic

Контроли:

- sourceEventId
- aggregateVersion
- enrichmentConsistency
- retry/backoff/circuit breaker
- FAILED/manual reprocess

Риски:

- Публикация задерживается до enrichment; нужно согласовать freshness и поведение при недоступности REST.

### 5. Read path

Отдельный быстрый контур чтения/статуса

Компоненты:

- Read model/projection
- Cache where allowed
- GET status API

Контроли:

- last_updated
- freshness label
- read-your-writes rule
- TTL/invalidation/cache stampede protection

### 6. Data/DWH

Аналитика и отчётность не блокируют core/client flow

Компоненты:

- CDC/ETL
- staging
- DWH/Data Lake

Контроли:

- lineage
- quality checks
- reconciliation
- backfill/replay
- late events policy

### 7. Security/privacy

Защита данных встроена в интеграцию

Компоненты:

- AuthN/AuthZ
- audit log
- secrets management

Контроли:

- TLS/mTLS
- masking logs
- field minimization
- encryption where needed
- retention

### 8. Observability/SRE

Эксплуатационная готовность

Компоненты:

- logs
- metrics
- traces
- business dashboard

Контроли:

- latency/error rate/availability SLI
- DLQ size
- retry rate
- consumer lag
- stuck process age
- external dependency health

### Сквозные требования

- API lifecycle: versioning, backward compatibility, deprecation policy, pagination/filtering/sorting where needed, rate limits, unified error model.
- Data contracts: schema versioning, compatibility mode, deleted/late/out-of-order events, reprocessing window.
- Enrichment contracts: owner of source event, owner of enrichment data, consistency level, failure/retry/reprocess policy.
- Capacity planning: RPS/TPS, payload size, partitions/consumers/workers, DB pool/indexes, retention, write amplification.

## 4. MVP-вариант

- Зафиксировать входной контракт и error model.
- Добавить correlationId/requestId во все вызовы.
- Сохранить операцию/заявку до внешних вызовов.
- Настроить timeout и ограниченный retry с backoff.
- Логировать технические и бизнес-ошибки без ПДн.
- Минимальная state machine с финальными и ошибочными статусами.
- Transactional Outbox для публикации критичных событий.
- Inbox/deduplication для входящих событий/callback.
- Outbox/integration table со статусами NEW/ENRICHING/PUBLISHED/FAILED для событий, требующих enrichment.
- REST enrichment adapter с timeout и ограниченным retry вне транзакции изменения сущности.
- GET status + понятные статусы для клиента.
- Non-blocking выгрузка в DWH; core-flow не ждёт отчётность.

## 5. Production-вариант

- Полная наблюдаемость: latency/error rate/availability, traces, stuck process age, DLQ/retry rate.
- Runbook и manual recovery для зависших операций.
- Contract/e2e/load/failover tests.
- Security/privacy review: masking, service auth, secrets, retention.
- Process Manager/Saga с таймерами, compensation, manual recovery dashboard.
- Outbox publisher со stuck alerts, replay и мониторингом publish lag.
- Retention, replay и DLQ для Inbox/consumers.
- Topic strategy, partition key, schema registry, compatibility mode, retry topics/DLQ.
- Integration Publisher с circuit breaker, retry/backoff/jitter, reprocess, stuck alerts и метриками enrichment latency/error rate.
- Версионность: aggregateVersion/sourceEventId/enrichmentConsistency/dataVersion/asOf в событии и проверка старых событий потребителем.
- Status read model/cache с last_updated/freshness label и fallback stale-data только для чтения.
- CDC/ETL со staging, data quality checks, reconciliation, lineage, backfill и late-events policy.

## 5A. Impact analysis / что ещё затронет изменение

- Специальный impact-analysis не требуется по выбранным формам; достаточно обычных contract/error/rollout checks.

## 6. Почему не выбраны опасные альтернативы

- **Чистая синхронная REST-цепочка** — Длинная/многоуровневая цепочка нестабильна, плохо восстанавливается и усиливает latency внешних систем.

- **DWH как часть core-flow** — Отчётность не должна блокировать клиентский или финансовый процесс.

- **Публикация события сервисом, где просто есть Kafka** — Kafka-инфраструктура не определяет владельца бизнес-события; сервис с частью данных не должен публиковать EntityUpdated как владелец изменения.

- **REST enrichment внутри транзакции изменения сущности** — Сбой enrichment-сервиса не должен откатывать или блокировать бизнес-факт изменения; enrichment нужен после commit через outbox/publisher.

## 7. Capacity planning lite

- Peak RPS/TPS: 2500
- Payload: 5 KB
- Поток: ~12.21 MB/s
- Дневной объём: ~205.99 GB/day
- Retention: 30 days
- Рекомендуемый стартовый минимум partitions/workers: 6
- Стартовый диапазон для теста: 6–12

### Capacity notes

- Это не sizing, а стартовая гипотеза для нагрузочного теста; финальное число partitions/workers считается по latency, consumer lag, DB write amplification, лимитам downstream и storage.
- Нужны backpressure, rate limit, отдельный capacity plan для consumers/workers и БД.
- Partition key должен совпадать с aggregate/entity id, иначе порядок статусов не гарантируется.
- Проверьте retention, storage cost, compaction/archiving и write amplification.
- Для DWH считать batch window, late events, backfill throughput и reconciliation window.
- Для enrichment считать не только Kafka throughput, но и REST RPS/latency/error rate, retry storm и размер очереди pending outbox.

## 8. Проверка текущего состояния против целевого

- Добавить Transactional Outbox.
- Добавить Inbox/idempotency.
- Добавить DLQ.
- Добавить Monitoring/metrics.
- Добавить Audit.
- Добавить Status model.
- Добавить Broker/event stream.

## 9. Отчёты для ролей

### selected_analyst

- Описать статусы, error matrix, source of truth, контракты, owner/SLA, retry/replay и acceptance criteria.
- Проверить открытые вопросы из quality gate до передачи в разработку.

## 10. ADR export

### ADR-001: Интеграционный подход для E2E интеграция заявки со скорингом, CRM и DWH

#### Контекст

- Бизнес-цель: Source обновляет договор. Перед отправкой в Kafka нужно REST-обогащение из Enrichment Service. Kafka-инфраструктуры в source нет, можно добавить только минимальную таблицу/outbox.
- Основная рекомендация: Неинвазивное расширение существующего процесса.
- Готовность требований: 53%.

#### Решение

- Использовать Неинвазивное расширение существующего процесса как главную архитектуру.
- Частные паттерны оформлять как внутренние слои, а не как конкурирующие top-level решения.
- Для критичных операций использовать idempotency, state tracking, audit и recovery.
- Для enrichment-before-Kafka: source-сервис владеет фактом изменения, integration publisher технически обогащает и публикует, REST enrichment выполняется после commit/outbox, а consistency level фиксируется в контракте.

#### Альтернативы

- Чистая синхронная REST-цепочка: отклонено/ограничено — Длинная/многоуровневая цепочка нестабильна, плохо восстанавливается и усиливает latency внешних систем.
- DWH как часть core-flow: отклонено/ограничено — Отчётность не должна блокировать клиентский или финансовый процесс.
- Публикация события сервисом, где просто есть Kafka: отклонено/ограничено — Kafka-инфраструктура не определяет владельца бизнес-события; сервис с частью данных не должен публиковать EntityUpdated как владелец изменения.
- REST enrichment внутри транзакции изменения сущности: отклонено/ограничено — Сбой enrichment-сервиса не должен откатывать или блокировать бизнес-факт изменения; enrichment нужен после commit через outbox/publisher.

#### Последствия

- Потребуется ownership процесса, контракты, тесты, SRE-метрики и runbook.
- Решение должно пройти архитектурное ревью перед production.

## 11. Дополнительные диаграммы

### Context diagram

```mermaid

flowchart LR
  User[User/Initiator] --> API[API / Entry Point]
  API --> PM[Process Manager / State Machine]
  PM --> S0[Contract Service]
  PM --> S1[Enrichment Service]
  PM -. async/non-blocking .-> S2[Kafka Consumer]
  PM -. CDC/ETL non-blocking .-> DWH[DWH / Reporting]
  PM --> Status[Status Read Model]
  Status --> User

```

### Event flow

```mermaid

sequenceDiagram
  participant Source as Source Service / Owner
  participant DB as Source DB
  participant Outbox as Outbox
  participant Pub as Integration Publisher
  participant Enrich as Enrichment REST Service
  participant Broker as Kafka single topic
  participant Consumer as Target Consumer
  Source->>DB: update entity + increment aggregateVersion
  Source->>Outbox: insert pending event in same transaction
  Pub->>Outbox: poll NEW event
  Pub->>Enrich: REST resolve(aggregateId, aggregateVersion, sourceEventId)
  alt enrichment success
    Enrich-->>Pub: enrichment data + dataVersion/asOf
    Pub->>Broker: publish final enriched event
    Pub->>Outbox: mark PUBLISHED
    Broker->>Consumer: deliver event
    Consumer->>Consumer: idempotency + aggregateVersion check
  else timeout/error
    Pub->>Outbox: retry later / FAILED / manual reprocess
  end

```

### Data flow

```mermaid

flowchart TD
  Source[(Source of Truth)] --> Core[(Operational DB)]
  Core --> Audit[(Audit/Status History)]
  Core --> Projection[(Read Model)]
  Projection --> Cache[(Cache)]
  Cache --> UI[Client/UI]
  Core -. CDC/ETL .-> Staging[(DWH Staging)]
  Staging --> Quality[Quality Checks]
  Quality --> DWH[(DWH/Data Mart)]

```

### Failure flow

```mermaid

sequenceDiagram
  participant Caller
  participant API
  participant Core
  participant External
  participant Ops as Manual Recovery
  Caller->>API: request with correlationId/idempotencyKey
  API->>Core: persist operation + status
  Core->>External: call with timeout
  alt timeout/error
    Core->>Core: retry with backoff
    Core->>Ops: create manual task if retries exhausted
    Core-->>Caller: trackingId + status PROCESSING/ERROR
  else success
    Core-->>Caller: result/status
  end

```

## 12. Библиотека похожих шаблонов

- REST request-response integration
- REST + external API adapter
- Kafka event publication with Outbox
- Event enrichment before Kafka publish
- Single Kafka topic + REST enrichment
- Kafka consumer + Postgres idempotent sink
- Shared topic selective consumer
- Webhook intake + Inbox
- Batch/File/SFTP exchange
- SFTP reconciliation
- Saga orchestration / process manager
- BFF/API Composition / Customer 360
- Status screen with cache/read model
- DWH offloading and retention
- CDC replication
- Legacy strangler migration
- Reference/master-data synchronization
- Regulatory data model change
- Current solution review / audit
- Queue-based async worker
- Near real-time decision flow

## 12A. Production gate / можно ли отдавать в разработку

**Статус:** RED — Нельзя отдавать в разработку как production-решение: есть блокирующие риски.

### Закрыть до разработки

- REST-обогащение перед Kafka требует явного ownership и recovery

### Закрыть до production

- SLO/alerts/runbook
- load test
- replay/recovery drill
- contract tests
- security review
- rollback plan

## 12B. Self-check результата

- source of truth выбран: True
- owner процесса/систем указан: True
- консистентность указана: True
- failure handling указан: True
- контекстный ключ надёжности проверен: Idempotency-Key / operation_id + unique constraint
- observability указана: True
- security/auth указаны: True
- rollback/replay указаны: True
- contracts сгенерированы: API/Event/File/CDC/DWH по выбранным паттернам
- test cases сформированы: True

## 13. Архитектурные варианты

### Вариант 1. Неинвазивное расширение существующего процесса

- Оценка: 100%

- Сложность: Средняя

- Задержка: batch/near-real-time

- Надёжность: Средняя/высокая

- Паттерны:

- Saga / Process State Machine
- Integration Publisher / REST Enrichment before Kafka
- PostgreSQL OLTP
- Контроли highload

- Почему:

- Production/source flow менять нельзя, поэтому допустимы read-only/CDC/file/adapter подходы или явно рискованный export/snapshot compromise.
- Выбранный класс кейса требует именно этот top-level каркас: Non-invasive extension of existing/source flow

- Риски:

- Нельзя гарантировать атомарную связь бизнес-изменения и публикации события из read-only канала; нужен ADR с residual risk.

### Вариант 2. Compromise: CDC/Polling + Enrichment Export

- Оценка: 72%

- Сложность: Средняя/высокая

- Задержка: Near-real-time или batch

- Надёжность: Средняя

- Паттерны:

- Integration Publisher / обогащение события
- Inbox / идемпотентный consumer
- Fallback / управляемая деградация
- PostgreSQL OLTP
- Контроли highload

- Почему:

- Жёсткий компромисс: source менять нельзя, поэтому надёжный source-owned outbox недоступен. Допустим только read-only/CDC/polling подход, который должен быть честно оформлен как рискованный export/snapshot, а не как полноценное доменное событие владельца.

- Риски:

- Нельзя гарантировать атомарную связь commit source → enrichment → Kafka publish.
- Нужны reconciliation, gap detection, watermark/offset, manual replay; event name лучше EntitySnapshotPrepared/ExportReady, не EntityUpdated.
- Enrichment/publisher — это слой доставки события внутри E2E/Saga/Fan-out архитектуры, а не главный вариант бизнес-процесса.

### Вариант 3. Контур данных / DWH

- Оценка: 68%

- Сложность: Средняя

- Задержка: Batch/near-real-time

- Надёжность: Высокая для аналитики

- Паттерны:

- PostgreSQL OLTP
- Контроли highload

- Почему:

- Аналитика, регуляторная отчётность или near-real-time DWH/offload; главный смысл — retention, watermark/offset, lineage, quality checks и reconciliation, а не просто transport batch/file.

- Риски:

- Нужны reconciliation, lineage, data quality, retention/archive и backfill.
- DWH/ETL — это слой data/reporting, он не должен подменять core-flow.
- Это полезный внутренний слой, но не главный архитектурный каркас для класса кейса non_invasive_extension.

## 14. Выбранные паттерны и контроли

### Saga / менеджер процесса — оценка 80

- Почему:

- Многошаговый управляемый процесс.

- Контроли:

- state machine
- process_steps
- attempts
- timeouts
- compensation
- manual recovery

- Риски:

- Без компенсаций не работает.

### Integration Publisher / обогащение события — оценка 78

- Почему:

- Технический publisher читает outbox/integration table, обогащает payload через владельца дополнительных данных и публикует событие без переноса ownership.

- Контроли:

- pending outbox
- REST timeout
- retry/backoff
- failed/reprocess status
- sourceEventId
- aggregateVersion
- consistency marker

- Риски:

- REST-обогащение может задержать публикацию; нужна политика при сбое и согласованная свежесть enrichment-данных.

### Inbox / идемпотентный consumer — оценка 70

- Почему:

- Защита от дублей.

- Контроли:

- message registry
- payload hash
- unique keys
- retention

- Риски:

- Нужен retention.

### Read model из бизнес-требований — оценка 70

- Почему:

- Из бизнес-контекста следует отдельный быстрый контур чтения/статусов.

- Контроли:

- projection table
- last_updated
- rebuild
- read-your-writes rule
- freshness marker

- Риски:

- Нужно явно объяснять пользователю свежесть данных.

### Контроли highload — оценка 70

- Почему:

- Высокая/пиковая нагрузка.

- Контроли:

- rate limit
- backpressure
- autoscaling
- partitioning
- connection pools
- load tests
- capacity plan

- Риски:

- Без capacity plan решение рискованно.

### Кэш / быстрый контур чтения — оценка 68

- Почему:

- Частое чтение, допустимое устаревание и/или горячий клиентский экран.

- Контроли:

- TTL
- invalidation
- cache stampede protection
- warmup
- stale marker

- Риски:

- Не использовать кэш для финального финансового/юридического решения.

### Workflow/BPM-движок — оценка 65

- Почему:

- 8+ шагов, human tasks или сложный workflow.

- Контроли:

- process definition
- human tasks
- timeouts
- audit

- Риски:

- Может быть избыточен.

### Fallback / управляемая деградация — оценка 60

- Почему:

- Бизнес допускает последний известный/частичный результат или есть нестабильные зависимости.

- Контроли:

- stale response policy
- partial response
- circuit breaker
- degraded status
- manual review

- Риски:

- Fallback должен быть явно виден пользователю/оператору.

### PostgreSQL OLTP — оценка 60

- Почему:

- Транзакционное хранилище.

- Контроли:

- constraints
- indexes
- migrations
- backup
- partitioning

- Риски:

- Не shared DB между сервисами.

### CQRS / read-модели — оценка 55

- Почему:

- Разные модели чтения/записи, highload/fan-out.

- Контроли:

- projections
- rebuild
- eventual consistency

- Риски:

- Усложняет систему.

## 15. Anti-pattern checker

- **HIGH — Не определена свежесть enrichment-данных**: Непонятно, должны ли дополнительные данные соответствовать моменту изменения сущности или моменту публикации события. Исправление: Зафиксировать AS_OF_CHANGE / CURRENT_AT_PUBLISH / BEST_EFFORT; для критичных данных нужен snapshot или versioned API.

- **HIGH — Некорректная ссылка на parent step**: Шаг Изменить договор ссылается на parent=0, которого нет. Исправление: Исправить parent в матрице шагов; для корня использовать root.

- **HIGH — Нужны события/очереди, но broker/queue не выбран**: Событийный сценарий не обеспечен инфраструктурой. Исправление: Разрешить Kafka/event broker/queue или изменить channel.

- **CRITICAL — REST-обогащение перед Kafka требует явного ownership и recovery**: Без outbox/integration state событие можно потерять или ошибочно передать ownership enrichment-сервису. Исправление: Зафиксировать source-owned outbox/integration table, publisher, consistency rule, retry/FAILED/reprocess и DLQ/quarantine.

## 16. Матрица систем

- **Contract Service** — role: Владелец договора; owner: Core; criticality: high; channel: rest; blocking: blocking; SLA: 2s

- **Enrichment Service** — role: Дополнительные атрибуты; owner: Data; criticality: high; channel: rest; blocking: blocking; SLA: 2s

- **Kafka Consumer** — role: Получатель; owner: Target; criticality: high; channel: kafka; blocking: async; SLA: 30s

## 17. Многоуровневая матрица шагов

- level 1 / order 1 / parent 0: **Изменить договор** → Contract Service via db; timeout=1s; retry=retry; compensation=manual; owner=Core

- level 1 / order 2 / parent 1: **Записать pending outbox** → Contract Service via db; timeout=1s; retry=retry; compensation=stuck alert; owner=Core

- level 1 / order 3 / parent 2: **Обогатить данные** → Enrichment Service via rest; timeout=2s; retry=retry_backoff; compensation=FAILED; owner=Data

- level 1 / order 4 / parent 3: **Опубликовать enriched event** → Kafka Consumer via kafka; timeout=30s; retry=retry; compensation=DLQ; owner=Target

## 17A. Карта цепочки сервисов, БД и интеграций
### Что делает каждый сервис
- **Contract Service** — роль: Владелец договора; owner: Core; SLA: 2s.
  - Делает: Изменить договор; канал: db; input: contract; output: changed; retry: retry; compensation: manual.
  - Делает: Записать pending outbox; канал: db; input: contractId; output: outboxEventId; retry: retry; compensation: stuck alert.
- **Enrichment Service** — роль: Дополнительные атрибуты; owner: Data; SLA: 2s.
  - Делает: Обогатить данные; канал: rest; input: contractId; output: extra fields; retry: retry_backoff; compensation: FAILED.
- **Kafka Consumer** — роль: Получатель; owner: Target; SLA: 30s.
  - Делает: Опубликовать enriched event; канал: kafka; input: enriched event; output: consumed; retry: retry; compensation: DLQ.
### Связи между сервисами
- **API/Process Manager → Scoring** через REST; mode=sync; contract=POST /score/v1/decision; data=scoring_request; retry=yes/backoff; DLQ=no; idempotency=idempotencyKey.
- **API/Process Manager → Kafka** через Kafka; mode=async; contract=ApplicationStatusChanged.v1; data=status_event; retry=yes; DLQ=yes; idempotency=eventId.
- **Kafka Consumer → CRM** через REST; mode=async; contract=PUT /crm/v1/application-status; data=crm_update; retry=yes/backoff; DLQ=yes; idempotency=eventId+aggregateVersion.
### Взаимодействие с БД/хранилищем
- **loan_application** — Локальная read/projection copy, не меняет source system. Индексы: (status), (created_at), (correlation_id), (client_id), unique(idempotency_key).
- **loan_application_status_history** — История статусов. Индексы: (loan_application_id, changed_at), (new_status, changed_at).
- **audit_log** — Аудит и security-события. Индексы: (correlation_id), (entity_type, entity_id), (created_at).
- **reconciliation_runs** — Сверка batch/CDC/DWH загрузок. Индексы: (source_name,target_name,created_at), (status).


## 18. Компонентная диаграмма

```mermaid

flowchart LR
I[Initiator]
S[Contract Service]
I --> S
S --> DB[(Primary DB)]
S --> T1[Contract Service]
S --> T2[Enrichment Service]
S --> T3[Kafka Consumer]
S --> OBS[(Logs/Metrics/Traces/Audit)]

```

## 19. Последовательность основного сценария

```mermaid

sequenceDiagram
participant I as Initiator
participant S as Contract Service
participant DB as Primary DB
participant T1 as Contract Service
participant T2 as Enrichment Service
participant T3 as Kafka Consumer
I->>S: command/request
S->>S: auth + validation + idempotency
S->>DB: save entity/status
DB-->>S: commit ok
S-->>I: trackingId/status/result

```

## 20. Последовательность ошибки / retry / DLQ

```mermaid

sequenceDiagram
participant W as Worker/PM
participant T as Target System
participant DB as DB
participant DLQ as DLQ/Manual Recovery
W->>T: call step
T--xW: timeout/5xx
W->>DB: save failed attempt
W->>W: retry with backoff
W->>DLQ: after retry exhausted
DLQ-->>W: manual/replay decision

```

## 21. Последовательность компенсации

```mermaid

sequenceDiagram
participant PM as Process Manager
participant S1 as Successful Step
participant C as Compensation
participant M as Manual Task
PM->>PM: detect failed blocking step
PM->>C: run compensation for completed steps
C-->>PM: compensation result
alt compensation failed
PM->>M: create manual recovery task
end

```

## 22. Основной сценарий

1. Инициатор отправляет команду или событие старта.
2. Contract Service сохраняет состояние LoanApplication.
3.   Шаг 1: Изменить договор → Contract Service через db (blocking).
4.   Шаг 2: Записать pending outbox → Contract Service через db (blocking).
5.   Шаг 3: Обогатить данные → Enrichment Service через rest (blocking).
6.   Шаг 4: Опубликовать enriched event → Kafka Consumer через kafka (non_blocking).
7. Финальный статус фиксируется в entity/status_history/audit_log.

## 23. Альтернативные сценарии и ошибки

### validation_error

1. Где: API
2. Блокирует: blocking
3. Retry: no
4. После retry: reject request
5. Owner: Продуктовая команда

### scoring_timeout

1. Где: Сервис скоринга
2. Блокирует: blocking
3. Retry: yes
4. После retry: SCORING_ERROR + manual task
5. Owner: Команда рисков

### crm_error

1. Где: CRM
2. Блокирует: non_blocking
3. Retry: yes
4. После retry: DLQ/manual
5. Owner: Команда CRM

### notification_error

1. Где: Сервис уведомлений
2. Блокирует: non_blocking
3. Retry: yes
4. После retry: DLQ
5. Owner: Команда коммуникаций

### dwh_export_error

1. Где: DWH
2. Блокирует: non_blocking
3. Retry: yes
4. После retry: replay/reconciliation
5. Owner: Команда данных

### Общий путь обработки ошибки

1. Техническая ошибка фиксируется в integration_attempts/event_enrichment_attempts.
2. Если retry=yes — выполняется retry with exponential backoff + jitter.
3. При ошибке REST enrichment исходное изменение не откатывается; outbox остаётся в NEW/ENRICHING/FAILED до retry или ручного reprocess.
4. После исчерпания retry сообщение уходит в DLQ/FAILED или создаётся manual_recovery_task.
5. Алерт уходит владельцу шага и дежурной команде.

## 24. Контракты

### API

- Не указано

### EVENTS

- Не указано

### QUEUE

- Не указано

### SELECTIVE_CONSUMER

- Не указано

### ENRICHMENT

- Не указано

### FILES

- Не указано

### CDC

- Не указано

### DWH

- Staging with load_id/batch_id/snapshot_id
- Watermark/offset policy for incremental load
- Data quality: record count, checksum, required fields, referential checks
- Reconciliation report
- Late arriving data and backfill policy
- Retention/archive policy for prod offload and DWH storage growth
- PII minimization/masking for analytics

### SOAP

- Не указано

### SECURITY

- Auth scopes/roles per endpoint/topic/file/feed
- Sensitive fields masked in logs
- mTLS/TLS for service channels
- Audit event for access/change

### PRIVACY

- Не указано

### DECISION

- Не указано

## 25. БД и хранение

### Storage

- PostgreSQL OLTP
- Read replicas where needed
- Connection pooling
- Partitioned hot tables
- DWH/Data Lake
- Archive/Object storage for cold data

### Таблицы

**Важно:** сценарий неинвазивный; таблицы описывают локальную проекцию/целевой контур, а не изменение source system.

#### loan_application

Назначение: Локальная read/projection copy, не меняет source system

Поля:

- id uuid primary key
- client_id uuid not null
- amount numeric(18,2) not null
- term_months integer not null
- purpose text not null
- idempotency_key text
- decision text
- rejection_reason text
- score integer
- status text not null
- version integer not null default 1
- correlation_id text
- created_at timestamp not null default now()
- updated_at timestamp not null default now()
- archived_at timestamp

Индексы:

- (status)
- (created_at)
- (correlation_id)
- (client_id)
- unique(idempotency_key)

#### loan_application_status_history

Назначение: История статусов

Поля:

- id uuid primary key
- loan_application_id uuid not null
- old_status text
- new_status text not null
- reason text
- changed_by text
- changed_at timestamp not null default now()

Индексы:

- (loan_application_id, changed_at)
- (new_status, changed_at)

#### audit_log

Назначение: Аудит и security-события

Поля:

- id uuid primary key
- correlation_id text
- actor text
- action text not null
- entity_type text
- entity_id text
- result text
- metadata jsonb
- created_at timestamp not null default now()

Индексы:

- (correlation_id)
- (entity_type, entity_id)
- (created_at)

#### reconciliation_runs

Назначение: Сверка batch/CDC/DWH загрузок

Поля:

- id uuid primary key
- source_name text not null
- target_name text not null
- load_id text
- records_source integer
- records_target integer
- checksum_source text
- checksum_target text
- status text not null
- created_at timestamp not null default now()

Индексы:

- (source_name,target_name,created_at)
- (status)

### Partitioning / capacity

- Partition audit/history/outbox/inbox/integration_attempts/event_enrichment_attempts by created_at.
- Use aggregateId/entityId as Kafka partition key.
- Capacity plan: broker partitions, DB indexes, connection pools, worker concurrency.

### Retention

- Retention: 3_years.
- Outbox/inbox/integration_attempts имеют отдельный retention.
- Audit/security срок согласовать с ИБ/юристами.

## 26. Draft SQL DDL

```sql

-- Draft SQL DDL. Требует DBA/security review.
-- Статусы: CREATED, VALIDATED, SENT_TO_SCORING, APPROVED, REJECTED, SCORING_ERROR, CRM_UPDATED, NOTIFICATION_SENT, DWH_EXPORTED

-- Локальная read/projection copy, не меняет source system
create table loan_application (
    id uuid primary key,
    client_id uuid not null,
    amount numeric(18,2) not null,
    term_months integer not null,
    purpose text not null,
    idempotency_key text,
    decision text,
    rejection_reason text,
    score integer,
    status text not null,
    version integer not null default 1,
    correlation_id text,
    created_at timestamp not null default now(),
    updated_at timestamp not null default now(),
    archived_at timestamp
);
create index idx_loan_application_1 on loan_application(status);
create index idx_loan_application_2 on loan_application(created_at);
create index idx_loan_application_3 on loan_application(correlation_id);
create index idx_loan_application_4 on loan_application(client_id);
create unique index ux_loan_application_5 on loan_application(idempotency_key);

-- История статусов
create table loan_application_status_history (
    id uuid primary key,
    loan_application_id uuid not null,
    old_status text,
    new_status text not null,
    reason text,
    changed_by text,
    changed_at timestamp not null default now()
);
create index idx_loan_application_status_history_1 on loan_application_status_history(loan_application_id, changed_at);
create index idx_loan_application_status_history_2 on loan_application_status_history(new_status, changed_at);

-- Аудит и security-события
create table audit_log (
    id uuid primary key,
    correlation_id text,
    actor text,
    action text not null,
    entity_type text,
    entity_id text,
    result text,
    metadata jsonb,
    created_at timestamp not null default now()
);
create index idx_audit_log_1 on audit_log(correlation_id);
create index idx_audit_log_2 on audit_log(entity_type, entity_id);
create index idx_audit_log_3 on audit_log(created_at);

-- Сверка batch/CDC/DWH загрузок
create table reconciliation_runs (
    id uuid primary key,
    source_name text not null,
    target_name text not null,
    load_id text,
    records_source integer,
    records_target integer,
    checksum_source text,
    checksum_target text,
    status text not null,
    created_at timestamp not null default now()
);
create index idx_reconciliation_runs_1 on reconciliation_runs(source_name,target_name,created_at);
create index idx_reconciliation_runs_2 on reconciliation_runs(status);

-- Highload: validate indexes with EXPLAIN, avoid unbounded scans, tune pool sizes and batch sizes.

```

## 27. Бэклог

- Утвердить owner процесса и систем.
- Утвердить source of truth и владение полями.
- Утвердить статусную модель и финальные статусы.
- Согласовать API/event/file/CDC/DWH contracts.
- API lifecycle: versioning, backward compatibility, deprecation policy, pagination/filtering/sorting, rate limits, unified error model.
- Data governance: schema versioning, compatibility mode, late/out-of-order/deleted events, lineage, quality checks, reprocessing window.
- Capacity plan: RPS/TPS, payload size, partitions/consumers/workers, DB pool/indexes, retention, write amplification.
- SRE/SLI: latency, error rate, availability, consumer lag, DLQ size, retry rate, stuck process age, external dependency health.
- Security/privacy: masking logs, RBAC/service auth, secrets, retention, minimization, encryption where needed.
- Реализовать миграции БД и индексы.
- Добавить correlationId/requestId во все каналы.
- Настроить logs/metrics/traces/audit.
- Подготовить integration/contract/e2e tests.
- Зафиксировать ADR trade-off: почему целевой вариант невозможен сейчас, какой риск принимаем, кто owner риска, когда пересматриваем.
- Разделить delivery на Safe MVP и Phase 2 hardening; запретить “временные” решения без даты пересмотра.
- Подготовить capacity plan: RPS, partitions, workers, DB pool, indexes.
- Провести load/stress/soak tests.
- Настроить backpressure/rate limits/autoscaling.
- Закрыть critical/high anti-patterns до production.

## 28. ADR

### ADR-001: Non-invasive Existing Process Extension

- Решение: Использовать Неинвазивное расширение существующего процесса.

- Последствия: Требуются владельцы, контракты, monitoring и recovery.

### ADR-002: Source of truth

- Решение: Source of truth: own_db; direct DB write запрещён.

- Последствия: Изменения только через согласованный доменный контракт.

### ADR-003: Failure policy

- Решение: Failure policy: retry_compensate_manual.

- Последствия: Каждый шаг должен иметь retry/compensation/manual recovery.

## 29. Стратегия тестирования

- Unit tests бизнес-правил.
- Integration tests DB/external clients.
- Contract tests API/events/files.
- E2E happy path and negative paths.
- Load tests.
- Stress tests.
- Soak tests.
- Failover tests.
- DLQ/retry/replay tests.
- Security tests.
- Masking logs verification.
- Audit trail verification.

## 30. План внедрения

- Phase 1: contracts + DB + observability.
- Phase 2: async/outbox/inbox.
- Phase 3: consumers/DWH.
- Phase 4: production readiness review.

## 31. Критерии приёмки

- Happy path выполняется.
- Повтор не создаёт дубль.
- Каждый шаг имеет status, owner, timeout, retry/after_retry.
- DWH/analytics не блокирует клиентский процесс.
- Контракты версионируются и имеют compatibility policy.
- API имеет версионирование, error model, rate limits, idempotency rules для POST/команд.
- Логи не содержат чувствительные данные.
- Метрики и алерты покрывают API, DB, broker, DLQ, outbox, stuck steps, lag, retry rate и external dependency health.
- Проведён load/stress test на целевой RPS и peak factor.
- Есть backpressure/rate limit/autoscaling policy.


## 17B. Специализированные сложные кейсы, распознанные моделью
Этот раздел добавлен, чтобы результат не сводился к общему “E2E”. Здесь перечислены конкретные архитектурные боли, которые модель увидела во входных данных.

### REST-обогащение перед публикацией в Kafka
**Почему сработало:** Source фиксирует бизнес-факт, но финальное событие должно быть дополнено данными из другого REST-сервиса.

**Решение:**
- Факт изменения остаётся во владении source-сервиса.
- Минимальный безопасный v1: source-owned outbox/integration table со статусами NEW/ENRICHING/PUBLISHED/FAILED.
- Technical Integration Publisher читает pending-записи, вызывает REST enrichment, публикует только финальный enriched event.
- Enrichment-сервис владеет только дополнительными атрибутами, но не становится владельцем события.
- При ошибке REST enrichment событие не теряется: retry, FAILED, manual reprocess и reconciliation обязательны.

**Обязательные контроли:**
- outbox/integration table
- sourceEventId
- aggregateId
- aggregateVersion
- eventId
- correlationId
- enrichmentConsistency
- dataAsOf
- retry/backoff
- FAILED/reprocess
- DLQ или quarantine
- stuck alerts

**Основные риски:**
- Перенос ownership события в enrichment-сервис.
- Потеря события между commit и publish.
- Публикация raw event без обязательного enrichment.
- Устаревшие enrichment-данные без dataAsOf/consistency rule.

**Тесты, которые нужно заложить:**
- REST enrichment недоступен: outbox остаётся FAILED/RETRY, Kafka не получает неполный event.
- Повтор publisher не создаёт дубль благодаря eventId/sourceEventId.
- Потребитель отвергает старую aggregateVersion.

### Долгий процесс, Saga и partial success
**Почему сработало:** Процесс нельзя держать в одном синхронном запросе: нужны состояния, компенсации и ручное восстановление.

**Решение:**
- Ввести process state machine с business/technical statuses.
- Для каждого шага указать owner, timeout, retry, compensation и terminal statuses.
- Partial success должен быть отдельным осознанным состоянием, а не “ошибкой где-то в логах”.
- Manual recovery — часть дизайна, а не аварийная импровизация.

**Обязательные контроли:**
- orchestrator или choreography decision
- status model
- compensation rules
- manual recovery queue
- audit
- reconciliation
- status API
- correlationId

**Основные риски:**
- Деньги/резервы/заявки остаются в подвешенном состоянии.
- Невозможно объяснить пользователю, где процесс.
- Операторы чинят руками без audit.

**Тесты, которые нужно заложить:**
- Шаг N упал после успеха N-1: статус partial/manual_review и компенсация корректны.
- Повтор не создаёт дубль.
- Операторское исправление аудируется.

