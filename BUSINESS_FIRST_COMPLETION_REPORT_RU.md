# Business-first constructor completion report

Сделано:

- Основной путь начинается с бизнес-процесса, а не с технических блоков.
- Первый экран не показывает Kafka/Outbox/Inbox/DB/Worker/REST/BFF/Cache.
- Пользователь описывает процесс выбором: бизнес-ситуация, участники, шаги, бизнес-объект, срок результата, итог процесса, требования и ограничения.
- Текущий технический конструктор сохранён как вторичный слой «Показать технический конструктор».
- Бизнесовый ввод автоматически строит техническую цепочку и заполняет hidden-поля для engine/report.
- Результат и полный отчёт начинаются с бизнес-процесса, затем показывают схему взаимодействия, объяснение выбора схемы, must-have, риски и handoff.
- Сохранены и покрыты case_type: async_worker, event_kafka, callback, enrichment_kafka, status_aggregation, dwh, legacy_file, audit.
- Ограничения влияют на рекомендации: no_new_topic, compensation, highload, money/pii/regulatory, replay/backfill, many_consumers, source_locked.

Проверка:

- `python -m pytest -q` → 116 passed, 1 skipped.
- `RUN_BROWSER_TESTS=1 python -m pytest -q test_v68_business_first_browser.py` → skipped в текущем окружении, потому что Chromium executable не установлен и скачать его нельзя из-за DNS/network. Сам тест добавлен и будет запускаться в CI/локально при установленном Playwright Chromium.
- JS проверен через `node --check` на inline script из `form_page()`.
