# Risk Register

| Риск | Severity | Где | Что сделать | Owner |
|---|---|---|---|---|
| Не зафиксирован запрет прямой записи в чужую БД | medium | process | В форме отметить запрет direct_db_write; исключение — только собственная projection/sink БД с отдельным owner. | TBD |
| Синхронная цепочка из нескольких блокирующих систем | critical | process | Сделать async acceptance + status tracking/queue/orchestrator. | TBD |
| Нет контекстного ключа надёжности для financial_command | critical | process | Добавить: Idempotency-Key / operation_id + unique constraint. | TBD |
| Highload + низкая latency + цепочка | high | process | Вернуть accepted/trackingId, обработку вынести async. | TBD |
| Некорректная ссылка на parent step | high | process | Исправить parent в матрице шагов; для корня использовать root. | TBD |
| Fan-out/Fan-in без явного join-шага | medium | process | Добавить join/aggregation step с parent вида 2,3 или описать partial success policy. | TBD |
| Нужны события/очереди, но broker/queue не выбран | high | process | Разрешить Kafka/event broker/queue или изменить channel. | TBD |
