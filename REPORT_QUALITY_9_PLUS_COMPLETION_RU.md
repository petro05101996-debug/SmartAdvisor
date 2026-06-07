# Доработка качества отчёта до уровня 9+/10

Сделано:

1. Улучшены описания узлов схемы: вместо одинакового текста “делает свою часть потока” каждый узел объясняет свою роль: Application API, Process State DB, External Provider Adapter/Worker, Status DB, Compensation / Manual Recovery и т.д.
2. Добавлено разделение “полнота требований” и “архитектурный риск”: отчёт может иметь полный ввод, но YELLOW-risk из-за highload, ПДн, active-active, внешнего провайдера или компенсаций.
3. Handoff и must-have сгруппированы по смысловым блокам: state machine, callback, multi-tenant, highload, ПДн/регуляторика, active-active, контракты, replay/DWH.
4. Тест-кейсы расширены: теперь они покрывают primary case и modifiers, включая partial success, compensation_failed, duplicate command, callback duplicate/missing, tenant lag, PII masking, active-active double execution, replay/backfill.
5. ADR context стал бизнесовым: описывает реальный бизнес-процесс и modifiers, а не generic “Service 1 → Service 2 → Service 3”.
6. Добавлен тестовый файл `test_v79_report_quality_9plus.py`.

Проверка:

```bash
pytest -q
# 172 passed, 25 skipped

node --check extracted-ui-script.js
# OK
```

Ограничение: browser click-through в текущем окружении не подтверждён, потому что Chromium/Playwright browser не установлен. Browser-тесты находятся в проекте и должны быть прогнаны в окружении с установленным Chromium.
