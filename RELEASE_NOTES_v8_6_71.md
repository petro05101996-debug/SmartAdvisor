# SmartAdvisor v8.6.71 product-ready-beta

Релиз доводит v8.6.70 до состояния удобной beta-версии для реального проектного ревью.

## Что изменено

- Приведены к зелёному состоянию расширенные проверки `verify_exhaustive_core_variations_v8632.py` и `verify_report_sections_v8625.py`.
- Убраны противоречия готовности: отчёт больше не пишет одновременно низкую архитектурную оценку и `production-ready`.
- Публичный markdown очищен от служебных англо-русских хвостов: `payload`, `DLQ`, `retry`, `replay`, `Inbox`, `Outbox`, `task queue`, `event log`.
- SQL-фрагменты остаются технически валидными после русской вычитки.
- README, UI и release notes синхронизированы на версии v8.6.71.
- Сохранён рабочий сценарий Project Navigator: ревью решения, вопросы, проектный пакет, матрица готовности.

## Проверки релиза

Минимальный набор:

```bash
python -m compileall -q .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python run_tests.py
python verify_exhaustive_core_variations_v8632.py
python verify_report_sections_v8625.py
python release_gate_v8664.py .
python release_gate_v8667.py .
```

## Ограничение

SmartAdvisor остаётся детерминированным архитектурным ревьюером. Он не заменяет архитектора и не должен выдавать финальное решение без подтверждённой карты процесса.
