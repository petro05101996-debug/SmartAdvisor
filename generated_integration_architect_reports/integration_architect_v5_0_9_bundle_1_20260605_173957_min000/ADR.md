# ADR-001: Integration Architecture Decision
## Context
- Бизнес-цель: Простая REST интеграция
- Входные данные недостаточны для выбора архитектуры.
- Готовность требований: 32%.
## Decision
- Архитектурное решение не утверждать до закрытия блокирующих вопросов.
- Сначала заполнить business goal, systems, steps, source of truth, ownership, load/SLA и error handling.
- После уточнения повторно сформировать ADR.
## Alternatives
- Альтернативы не сравнивались: недостаточно входных данных.
## Consequences
- Нельзя передавать решение в разработку как финальное.
- Следующий шаг — уточнение требований и повторная генерация отчёта.
## Rollback
- Feature toggle/canary rollback.
- Replay/reconciliation plan before full rollout.
