# ADR-001: Integration Architecture Decision
## Context
- Бизнес-цель: Есть общий Kafka topic, source менять нельзя, отдельный topic запрещён, нужно фильтровать 1% событий и писать их в Postgres.
- Основная рекомендация: Shared Topic Selective Consumer + Idempotent Sink.
- Готовность требований: 87%.
## Decision
- Использовать Shared Topic Selective Consumer + Idempotent Sink как главную архитектуру.
- Частные паттерны оформлять как внутренние слои, а не как конкурирующие top-level решения.
- Для критичных операций использовать idempotency, state tracking, audit и recovery.
- Для shared Kafka topic: не подменять кейс Outbox-ом; главный контур — selective consumer, capacity/backpressure, idempotent sink, DLQ/quarantine, lag/filter metrics и replay plan.
## Alternatives
- Альтернативы не выявлены по заполненным данным.
## Consequences
- Потребуется ownership процесса, контракты, тесты, SRE-метрики и runbook.
- Решение должно пройти архитектурное ревью перед production.
## Rollback
- Feature toggle/canary rollback.
- Replay/reconciliation plan before full rollout.
