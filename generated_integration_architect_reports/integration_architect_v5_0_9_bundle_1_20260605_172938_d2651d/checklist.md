# Production Checklist
Recommended architecture: **Неинвазивное расширение существующего процесса**
Gate: **YELLOW** — Можно идти в MVP/разработку только с зафиксированными рисками и архитектурным ревью.
Readiness score: **74%**
## Blocking gaps
- Нужны события/очереди, но broker/queue не выбран
## Checklist
- [ ] ADR approved
- [ ] source of truth and ownership approved
- [ ] API/event/file contracts versioned
- [ ] idempotency for commands/events
- [ ] timeouts for sync calls
- [ ] retry/backoff and DLQ/quarantine for async
- [ ] correlationId/tracing/log masking
- [ ] metrics/alerts/dashboard
- [ ] load/stress/failover tests
- [ ] replay/recovery runbook
- [ ] security review
- [ ] rollback/canary/feature-toggle plan
