# Risk Register

| Риск | Severity | Где | Что сделать | Owner |
|---|---|---|---|---|
| Не определена свежесть enrichment-данных | high | process | Зафиксировать AS_OF_CHANGE / CURRENT_AT_PUBLISH / BEST_EFFORT; для критичных данных нужен snapshot или versioned API. | TBD |
| Некорректная ссылка на parent step | high | process | Исправить parent в матрице шагов; для корня использовать root. | TBD |
| Нужны события/очереди, но broker/queue не выбран | high | process | Разрешить Kafka/event broker/queue или изменить channel. | TBD |
| REST-обогащение перед Kafka требует явного ownership и recovery | critical | specialized_case | Зафиксировать source-owned outbox/integration table, publisher, consistency rule, retry/FAILED/reprocess и DLQ/quarantine. | TBD |
