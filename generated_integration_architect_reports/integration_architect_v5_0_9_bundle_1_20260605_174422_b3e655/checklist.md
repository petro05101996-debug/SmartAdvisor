# Production Checklist
Recommended architecture: **Неинвазивное расширение существующего процесса**
Gate: **GREEN** — Можно отдавать в разработку после обычного ревью и фиксации ADR.
Readiness score: **82%**
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
