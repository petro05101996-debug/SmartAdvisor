# SmartAdvisor v8.6.70 real-design-verified

Фокус релиза: проверка и калибровка на реальном проектном кейсе обратного потока статусов УК → Банк → ресурсные системы/DWH.

Исправлено:
- проектный пакет больше не пишет `production-ready`, если матрица готовности блокирует production;
- Kafka fan-out теперь моделируется корректно: несколько consumers зависят от producer-шага в Kafka, а не друг от друга;
- high-risk findings блокируют передачу в разработку и ограничивают score;
- `DLQ/replay/backoff/limit/best-effort`, указанные в названии шага компактного формата, учитываются как recovery controls;
- compact-text parser поддерживает строки `статусы`, `ключи`, `поля`, `regulatory`, даже если `поля` содержит `|`;
- ключ партиционирования распознаётся из названия шага, например `partition key operationId`.

Добавлено:
- регрессионные тесты `test_v8670_real_design_case.py` на сырой и production-ready банковский кейс;
- проверка, что сырой кейс не проходит development/production gates;
- проверка, что доработанный кейс формирует проектный пакет и проходит production gate.
