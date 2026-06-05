# Risk Register

| Риск | Severity | Где | Что сделать | Owner |
|---|---|---|---|---|
| Нужны события/очереди, но broker/queue не выбран | high | process | Разрешить Kafka/event broker/queue или изменить channel. | TBD |
| REST-обогащение перед Kafka требует явного ownership и recovery | critical | specialized_case | Зафиксировать source-owned outbox/integration table, publisher, consistency rule, retry/FAILED/reprocess и DLQ/quarantine. | TBD |
