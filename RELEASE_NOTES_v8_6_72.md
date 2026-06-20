# SmartAdvisor v8.6.72 production-ready

Финальный production-hardening поверх v8.6.71.

## Что добавлено

- Подробные `/health`, `/healthz`, `/readyz`, `/livez` с проверкой каталога данных и SQLite.
- `/api/version` и `/api/diagnostics` для поддержки и деплоя.
- `production_smoke_v8672.py`: direct + HTTP smoke, проверка запуска сервера, health, version, `/api/analyze`, markdown отчёта и публичных формулировок.
- Регрессионные тесты v8.6.72 на production-polish и diagnostics.
- Финальная вычитка публичного markdown: нет `Без таймаут`, `production-ready`-хвостов и противоречий readiness.
- README синхронизирован с фактическим портом `8110` и production-проверками.

## Позиционирование

SmartAdvisor остаётся не автозаменой архитектора, а production-ready штурманом и ревьюером проектирования: строит карту процесса, показывает дыры, формирует проектный пакет и блокирует передачу сырого решения в разработку/production.

## Финальная проверка

```bash
python -m compileall -q .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python run_tests.py
python production_smoke_v8672.py
python run_real_complex_audit_v8641.py
python run_production_audit_v8642.py
python verify_exhaustive_core_variations_v8632.py
python verify_report_sections_v8625.py
python verify_report_logic_no_contradictions_v8620.py
python release_gate_v8664.py .
python release_gate_v8667.py .
```
