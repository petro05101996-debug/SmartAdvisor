# Отчёт по интеграционному решению

## 1. Бизнес-процесс
1. Клиент создаёт заявку / запрос — Заявка.
2. Внутренняя система принимает заявку — Заявка.
3. Внутренняя система проверяет данные — Заявка.
4. Внешняя система обрабатывает запрос — Заявка.
5. Внешняя система получает ответ позже — Заявка.
6. Внутренняя система обновляет статус — Статус.
7. Оператор отправляет на ручной разбор — Заявка.

**Готовность требований:** 100% (GREEN).

**Архитектурный риск:** YELLOW. Это не дублирует полноту ввода: даже при полном вводе риск может оставаться YELLOW из-за highload, ПДн, external provider, active-active или компенсаций.

## 2. Класс сложного кейса
Базовый case_type: async_worker.
Главный класс: saga_state_machine (long-running process / saga state machine).
Почему:
- заявка создаётся пользователем и проходит несколько шагов.
- есть внешний шаг/провайдер.
- есть обновление статуса или отложенный результат.
- выбрана компенсация/откат.
Дополнительные признаки:
- multi-tenant/noisy neighbor: добавляет требования, риски и тесты, но не заменяет основную схему.
- highload/пиковая нагрузка: добавляет требования, риски и тесты, но не заменяет основную схему.
- регуляторика: добавляет требования, риски и тесты, но не заменяет основную схему.
- ПДн/персональные данные: добавляет требования, риски и тесты, но не заменяет основную схему.
- active-active риск: добавляет требования, риски и тесты, но не заменяет основную схему.
- несколько получателей: добавляет требования, риски и тесты, но не заменяет основную схему.
- replay/backfill: добавляет требования, риски и тесты, но не заменяет основную схему.
- внешняя зависимость: добавляет требования, риски и тесты, но не заменяет основную схему.
- callback/webhook: добавляет требования, риски и тесты, но не заменяет основную схему.
- нестабильный внешний провайдер: добавляет требования, риски и тесты, но не заменяет основную схему.

## 3. Схема взаимодействия
**Client/UI → Application API → Process State DB → Validation Step → External Provider Adapter/Worker → Status DB → Compensation / Manual Recovery**

- **Client/UI**: инициирует бизнес-операцию, получает trackingId/processId и затем смотрит статус, а не ждёт завершения всех внутренних шагов.
- **Application API**: принимает заявку/команду, выполняет минимальную синхронную валидацию, создаёт processId/trackingId и фиксирует старт процесса.
- **Process State DB**: хранит состояние процесса, статусы шагов, retry-счётчики, ссылки на внешние запросы, причину ошибки и данные для ручного восстановления.
- **Validation Step**: проверяет обязательные данные и бизнес-правила до внешнего вызова, чтобы не отправлять некорректный запрос партнёру.
- **External Provider Adapter/Worker**: изолирует работу с внешней системой: timeout, retry, mapping ошибок, callback/polling fallback и лимиты провайдера.
- **Status DB**: хранит итоговый и промежуточный статус для GET /status, экрана пользователя, поддержки и мониторинга зависших процессов.
- **Compensation / Manual Recovery**: содержит явные сценарии компенсации, compensation_failed и очередь ручного восстановления с владельцем решения.
- **Ошибка/retry/manual recovery/status**: отдельно фиксируются retry limit, владелец ошибки, финальный статус, ручное восстановление и метрики зависших операций.

## 4. Почему выбрана такая техническая схема
Базово это async-процесс, но из-за многошаговости, денег/договоров и компенсации это не просто worker, а управляемая state machine. Поэтому нужны Process State DB, статусы шагов, retry per step, compensation_failed и manual recovery.
Дополнительно: из-за multi-tenant нужны tenantId, квоты и метрики по tenant; из-за highload нужны backpressure, rate limits и нагрузочный тест; из-за ПДн/регуляторики нужны audit, masking, retention и access control; из-за ПДн/регуляторики нужны audit, masking, retention и access control; active-active фиксируется как риск двойного исполнения/split-brain и требует ADR; callback/webhook добавляет Callback API, callback inbox, идемпотентный переход статуса и polling fallback; нестабильный внешний провайдер требует timeout budget, fallback/reconciliation и ручной проверки.
Порядок бизнес-шагов учтён: 1. Клиент создаёт заявку / запрос — Заявка. → 2. Внутренняя система принимает заявку — Заявка. → 3. Внутренняя система проверяет данные — Заявка. → 4. Внешняя система обрабатывает запрос — Заявка. → 5. Внешняя система получает ответ позже — Заявка. → 6. Внутренняя система обновляет статус — Статус. → 7. Оператор отправляет на ручной разбор — Заявка.
- Главный риск: partial success без модели состояний — часть шагов выполнена, но владелец восстановления непонятен.
- Обязательно реализовать: process state model.

## 5. Пошаговый процесс
1. Клиент создаёт заявку / запрос — Заявка
2. Внутренняя система принимает заявку — Заявка
3. Внутренняя система проверяет данные — Заявка
4. Внешняя система обрабатывает запрос — Заявка
5. Внешняя система получает ответ позже — Заявка
6. Внутренняя система обновляет статус — Статус
7. Оператор отправляет на ручной разбор — Заявка

## 6. Что обязательно реализовать
### State machine / статусы / восстановление
- process state model
- step status matrix
- compensation matrix
- compensation_failed process
- manual recovery owner
- watermark/offset tracking
### Внешний провайдер / callback
- external timeout budget
- provider error mapping
- Callback API
- callback endpoint contract
- callback signature validation
- raw callback body preservation
- callback inbox
- idempotent callback transition
- polling fallback
- provider timeout budget
- manual provider check
- provider SLA/owner
### Multi-tenant / изоляция нагрузки
- tenantId key
- per-tenant quotas
- per-tenant lag/latency metrics
- tenant-level alerts
- consumer pool isolation if needed
### Highload / производительность
- backpressure
- rate limits
- capacity/load test
- queue/lag metrics
- scaling policy
### ПДн / регуляторика / аудит
- audit trail
- change history
- approval/traceability
- retention policy
- evidence for regulator
- masking
- access control
- PII audit trail
- data minimization
### Active-active / консистентность
- single-writer decision or ADR
- split-brain handling
- reconciliation procedure
- duplicate execution guard
- fallback/reconciliation
- reconciliation
- reconciliation job
### Контракты / совместимость
- schema compatibility
### Replay / DWH / сверка
- replay procedure
- backfill window
- deduplication
### Разработка / эксплуатация
- partial success tests
- fan-out/consumer groups decision
- consumer idempotency
- consumer lag ownership
- partner SLA/owner
- timeout waiting policy

## 7. Главные риски
| Риск | Что будет | Как закрыть |
|---|---|---|
| partial success без модели состояний | часть шагов выполнена, но владелец восстановления непонятен | Process State DB, step status matrix, compensation_failed и manual recovery owner |
| компенсация не сработала | деньги/резервы/договоры остаются в подвешенном состоянии | compensation matrix, audit trail и ручной recovery queue |
| noisy neighbor | крупный tenant создаёт lag для остальных | tenantId key, per-tenant quotas и isolated consumer pool |
| aggregate metrics hide tenant SLA | SLA одного tenant нарушается незаметно | per-tenant lag/latency metrics и tenant-level alerts |
| queue lag grows faster than consumers | очередь/stream накапливает задержку быстрее обработки | backpressure, scaling policy, capacity/load test |
| retry storm | повторы добивают зависимые системы | retry budget, jitter и rate limits |
| missing audit evidence | невозможно доказать корректность решения регулятору | audit trail, change history, evidence retention |
| PII leakage | персональные данные уходят неавторизованному потребителю | masking, access control, minimization |
| retention violation | данные хранятся дольше разрешённого срока | retention policy и audit trail |
| double execution / split-brain | два региона могут выполнить одну операцию дважды | single-writer ADR, duplicate guard, reconciliation |
| external provider timeout | внешний провайдер задерживает или теряет ответ | timeout budget, fallback/polling, reconciliation |
| callback не пришёл | процесс зависает без финального статуса | timeout waiting policy, polling fallback, reconciliation |
| callback пришёл повторно | статус может обновиться дважды | callback inbox и idempotent callback transition |
| callback подделан | в систему попадёт ложный результат | signature/auth validation и raw body preservation |
| unstable external provider | провайдер может отвечать с задержкой или нестабильно | provider timeout budget, polling fallback и manual provider check |

## 8. Ограничения и компромиссы
- Highload: нужны backpressure, rate limits, capacity/load test и метрики очередей/лагов.
- PII/ПДн: нужны masking, access control, data minimization, retention и PII audit trail.
- Регуляторика: нужны audit trail, change history, traceability и evidence retention.
- Compensation: нужна state machine, compensation step, compensation_failed и manual recovery owner.
- Multi-tenant: нужны tenantId, per-tenant quota, tenant-level metrics и защита от noisy neighbor.
- Active-active: если есть write/financial operation, нужен single-writer/ledger; иначе зафиксировать как риск инфраструктуры и ADR.
- Нестабильный внешний провайдер: нужны timeout budget, polling fallback, reconciliation и manual provider check.
- Replay/backfill: нужны watermark/offset, deduplication, replay window и reconciliation.

## 9. Что отдать разработке
### State machine / статусы / восстановление
- process state model
- step status matrix
- compensation matrix
- compensation_failed process
- manual recovery owner
- watermark/offset tracking
### Внешний провайдер / callback
- external timeout budget
- provider error mapping
- Callback API
- callback endpoint contract
- callback signature validation
- raw callback body preservation
- callback inbox
- idempotent callback transition
- polling fallback
- provider timeout budget
- manual provider check
- provider SLA/owner
### Multi-tenant / изоляция нагрузки
- tenantId key
- per-tenant quotas
- per-tenant lag/latency metrics
- tenant-level alerts
- consumer pool isolation if needed
### Highload / производительность
- backpressure
- rate limits
- capacity/load test
- queue/lag metrics
- scaling policy
### ПДн / регуляторика / аудит
- audit trail
- change history
- approval/traceability
- retention policy
- evidence for regulator
- masking
- access control
- PII audit trail
- data minimization
### Active-active / консистентность
- single-writer decision or ADR
- split-brain handling
- reconciliation procedure
- duplicate execution guard
- fallback/reconciliation
- reconciliation
- reconciliation job
### Контракты / совместимость
- schema compatibility
### Replay / DWH / сверка
- replay procedure
- backfill window
- deduplication
### Разработка / эксплуатация
- partial success tests
- fan-out/consumer groups decision
- consumer idempotency
- consumer lag ownership
- partner SLA/owner
- timeout waiting policy

## 10. Что нужно уточнить
- нет критичных неизвестных

## 11. Тест-кейсы
### State machine / статусы / восстановление
- compensation_failed: компенсация тоже упала и задача ушла в manual recovery
- duplicate command: повтор с тем же idempotencyKey возвращает тот же processId/trackingId
- stuck process: процесс завис в IN_PROGRESS и сработал alert
- GET /status показывает промежуточный и финальный статус
- evidence для регулятора сохраняется и находится по correlationId/processId
### Внешний провайдер / callback
- callback пришёл повторно и не изменил статус второй раз
- callback не пришёл и включился polling fallback
- manual provider check закрывает зависший запрос
### Multi-tenant / изоляция нагрузки
- tenant создаёт lag другим tenant — проверяется per-tenant quota и alert
- tenant-level SLA виден отдельно от aggregate metrics
### Highload / производительность
- пиковая нагрузка проходит capacity/load test
- retry storm ограничивается retry budget/rate limits/backpressure
### ПДн / регуляторика / аудит
- audit trail содержит who/what/when/why
- PII masking скрывает чувствительные поля
- retention policy удаляет/архивирует данные в срок
### Active-active / консистентность
- reconciliation находит конфликтующие записи
### Replay / DWH / сверка
- backfill переигрывает период без дублей
- deduplication защищает target при replay
### Разработка / эксплуатация
- happy path: заявка проходит все шаги и получает финальный статус
- partial success: внешний шаг упал после успешной валидации
- access denied для неавторизованного потребителя
- одна операция не исполняется дважды в двух регионах
- провайдер отвечает медленно и не ломает весь процесс

## 12. ADR
- Context: клиентская/бизнес-заявка проходит многошаговый процесс (Клиент создаёт заявку / запрос → Внутренняя система принимает заявку → Внутренняя система проверяет данные → Внешняя система обрабатывает запрос → Внешняя система получает ответ позже → Внутренняя система обновляет статус) с управляемыми статусами, внешними зависимостями и восстановлением; дополнительные признаки: multi-tenant/noisy neighbor, highload/пиковая нагрузка, регуляторика, ПДн/персональные данные, active-active риск, несколько получателей, replay/backfill, внешняя зависимость, callback/webhook, нестабильный внешний провайдер.
- Decision: использовать Client/UI → Application API → Process State DB → Validation Step → External Provider Adapter/Worker → Status DB → Compensation / Manual Recovery.
- Primary case: saga_state_machine.
- Modifiers: multi_tenant_noisy_neighbor, highload, regulatory_process, personal_data_exchange, active_active_warning, many_consumers, replay_required, external_dependency, webhook_callback, unstable_external_provider.
- Alternatives: generic async_worker, синхронная цепочка, adapter/orchestrator, событийный поток там, где это оправдано.
- Consequences: нужны case-specific контракты, правила повторов, владельцы ошибок, мониторинг, тесты по primary и modifiers.

## 13. Технические детали
<details class="expert-details">
<summary>Показать технические детали</summary>

- Process State DB
- Process Coordinator
- step status matrix
- External Provider Adapter/Worker
- Status API
- compensation step
- compensation_failed
- manual recovery queue
- audit trail
- stuck process monitoring
- tenantId key
- per-tenant quotas
- per-tenant lag/latency metrics
- tenant-level alerts
- consumer pool isolation if needed
- backpressure
- rate limits
- capacity/load test
- queue/lag metrics
- scaling policy
- change history
- approval/traceability
- retention policy
- evidence for regulator
- masking
- access control
- PII audit trail
- data minimization
- single-writer decision or ADR
- split-brain handling
- reconciliation procedure
- duplicate execution guard
- fan-out/consumer groups decision
- consumer idempotency
- schema compatibility
- consumer lag ownership
- replay procedure
- backfill window
- deduplication
- watermark/offset tracking
- external timeout budget
- provider error mapping
- fallback/reconciliation
- partner SLA/owner
- Callback API
- callback endpoint contract
- callback signature validation
- raw callback body preservation
- callback inbox
- idempotent callback transition
- timeout waiting policy
- polling fallback
- reconciliation
- provider timeout budget
- reconciliation job
- manual provider check
- provider SLA/owner

</details>

### Долгий многошаговый процесс / компенсации
- Если часть шагов уже выполнена, а следующий шаг упал, нельзя оставлять процесс в неопределённом состоянии. Нужна статусная модель процесса.
- Для каждого критичного шага нужно указать: успешный статус, ошибочный статус, retry limit, owner и что делать после исчерпания retry.
- Если нужен откат, компенсация должна быть явным шагом: что откатываем, кто владелец, как аудируется, что делать при compensation_failed.
- Для ручного восстановления нужна очередь manual recovery с причиной, владельцем, временем создания и финальным решением.
- Минимальные тесты: сбой после частичного успеха, повтор команды, упавшая компенсация, ручное восстановление, проверка статуса процесса.
