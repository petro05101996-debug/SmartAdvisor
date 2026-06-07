# Финальная добивка смешанных сложных кейсов

Исправлено ядро после жёсткой проверки смешанных сценариев.

## Что исправлено

1. Audit/privacy-erasure больше не уходит в старую audit-ветку, если сценарий пришёл из business-first конструктора и содержит privacy/contract/specialized признаки.
2. Callback + compensation теперь остаётся saga/process-state как primary, но получает callback/webhook modifiers: Callback API, callback inbox, idempotent callback transition, polling fallback, reconciliation.
3. Business-first readiness больше не показывает GREEN/100 вместе со старыми legacy-gaps вида “Не заполнено обязательное поле…”.
4. Active-active financial write остаётся YELLOW до ADR/single-writer/ledger/reconciliation.
5. Добавлены regression tests:
   - test_v78_mixed_core_final_fixes.py
   - test_v77_mixed_complex_cases_browser.py

## Проверка

- `python -m pytest -q` → `167 passed, 25 skipped`
- `node --check extracted-ui-script.js` → OK
- `RUN_BROWSER_TESTS=1 python -m pytest -q test_v77_mixed_complex_cases_browser.py -rs` → skipped, потому что Chromium не установлен в текущем окружении.

## Ручная матрица

Проверены смешанные кейсы:

- application + external + compensation + highload + PII/regulatory + multi-tenant + active-active
- callback + compensation + unstable external provider
- audit + privacy erasure + legal hold
- data change + no new topic + highload + multi-tenant
- enrichment + source locked + no new topic
- status fan-in + highload + PII
- reporting + replay + regulatory
- legacy + migration
- audit + contract change / required field
- financial + active-active

Все проверенные core-сценарии прошли: primary не заменяется вторичным modifier, схема соответствует primary, modifiers добавляют must-have/risks.
