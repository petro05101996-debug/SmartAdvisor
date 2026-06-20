# SmartAdvisor v8.6.72-production-ready

Инструмент для проектирования интеграций и тренировки системного аналитика.

Основные разделы:

- конструктор процесса и интеграционной схемы;
- справочник инвариантов;
- справочник паттернов;
- тренажёр кейсов и собеседований;
- HTML и markdown отчёты по архитектуре.

## Быстрый запуск

```bash
python app.py
```

Переменные окружения:

- `PORT` — порт приложения, по умолчанию `8110`;
- `HOST` — хост, по умолчанию `127.0.0.1`;
- `APP_DIR` — каталог для временных run/attempt данных.

## Проверка перед деплоем

```bash
python -m compileall -q .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
python run_real_complex_audit_v8641.py
python run_production_audit_v8642.py
python verify_exhaustive_core_variations_v8632.py
python verify_full_core_audit_v8639.py
python verify_full_core_audit_v8640.py
python verify_learning_production_v8645.py
python verify_saas_ui_v8654.py
python verify_ui_full_v8643.py
python verify_language_quality_v8647.py
python production_smoke_v8672.py
```

Подробности релиза: `RELEASE_NOTES_v8_6_72.md`.


## Финальная проверка релиза

Перед упаковкой архива выполните:

```bash
python clean_generated_artifacts.py
python release_gate_v8664.py .
```

`release_gate_v8664.py` падает, если в релиз попали runtime-базы, PNG-скриншоты, Python-кэши или старые audit-артефакты.


## Production endpoints

- `/health` и `/livez` — быстрый health check.
- `/readyz` и `/healthz` — readiness с проверкой каталога данных, SQLite и количества учебных кейсов.
- `/api/version` — версия приложения.
- `/api/diagnostics` — диагностический JSON для поддержки.

Для Timeweb можно оставлять Docker `HEALTHCHECK NONE`, а внешний health probe направлять на `/readyz`.


## v8.6.64 complete-uiux

Добавлен сценарный UX-слой: навигация, глоссарий, progress/reports, command palette, режимы тренажёра, карта рисков и executive summary отчётов.

## v8.6.64 user-friendly

Фокус релиза: сделать интерфейс понятнее для живого пользователя, а не только для технического проверяющего.

Добавлено:
- простой старт на главной странице;
- режим новичка в учебном кейсе через 5 понятных вопросов;
- объяснения «простыми словами» рядом с чекбоксами решений;
- кнопки, которые выбирают реальные архитектурные контроли без ручного поиска;
- подсказки, как читать отчёт: вердикт → риски → действия → детали;
- дополнительный verifier `verify_user_friendly_v8664.py`;
- release gate учитывает новые user-friendly verifier artifacts.


## v8.6.72 production-ready

Фокус релиза: довести инструмент до production-ready версии для реального архитектурного ревью.

Закрыто:
- проходят базовые, legacy, release, exhaustive и report-section проверки;
- убраны противоречия вида `0/10`, но `production-ready`;
- публичный markdown вычищен от англо-русских хвостов (`payload`, `DLQ`, `retry`, `Inbox`, `task queue` и др.);
- версии README/UI/release notes синхронизированы;
- Project Navigator остаётся главным рабочим сценарием: карта процесса, ревью, вопросы, проектный пакет, readiness gates.

Правильное позиционирование: не автопроектировщик вместо архитектора, а архитектурный ревьюер и штурман системного аналитика.

## v8.6.70 real-design-verified

Проверено на реальном проектном кейсе обратного потока статусов УК → Банк → ресурсные системы/DWH.
Добавлены регрессионные тесты для сырого и production-ready варианта: fan-out Kafka, readiness gates, проектный пакет, event envelope, outbox, DLQ/replay, status model и partition key.

## v8.6.68 project-map-gated

Фокус релиза: один полный gate от распаковки до отчёта, без старых runtime-артефактов и без устаревших проверок.

Закрыто:
- быстрый и стабильный `check_ui_wizard_cases.py` для релизного gate;
- устаревшие report/verifier ожидания;
- русско-английские хвосты в отчётах (`dead-letter`, `Outbox`, `envelope`, `hot partition` и др.);
- появление REST/Kafka до шага выбора стека в пользовательском конструкторе;
- `localStorage` pageerror в restricted/browser-smoke окружении;
- очистка `COMPLEX_CASE_*.md` и других generated artifacts перед упаковкой;
- workflow распаковки ожидает актуальный архив `SmartAdvisor-main-v8_6_72-production-ready.zip`.

