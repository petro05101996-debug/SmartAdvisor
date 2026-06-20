# SmartAdvisor v8.6.68 project-map-gated

Фокус релиза: сделать инструмент полезнее именно при проектировании, а не только при генерации отчёта.

## Что исправлено

- Исправлен баг `indirect -> direct`: теперь `indirect` не распознаётся как `direct` из-за подстроки `direct`.
- Добавлена нормальная карта маршрута шага: `source_system -> target_system`, `producer`, `consumer`, `executor_system`, `route`.
- Компактный CLI-формат теперь поддерживает `действие | источник -> получатель | канал | флаги`.
- Старый формат `действие | система | канал | флаги` сохранён; маршрут выводится из предыдущего шага, чтобы отчёт не строил `System -> System`.
- Для обычного свободного текста добавлен best-effort разбор с обязательным снижением уверенности и предупреждением: карту процесса нужно подтвердить.
- Добавлен блок `process_understanding`: «Я понял процесс так» с route по каждому шагу.
- Добавлен quality gate «Карта процесса» и уровни готовности: discussion/design/development/production.
- Запрещено завышать score для эвристически разобранного текста: пока карта не подтверждена, verdict красный и score ограничен.
- Обновлён CLI: при ручном добавлении шага теперь спрашиваются источник и получатель связи.
- Синхронизированы `pytest` и legacy `run_tests.py`.

## Проверки

- `python -m compileall -q .`
- `pytest -q` -> 63 passed, 2 skipped
- `python run_tests.py` -> 68/68 passed
- `python release_gate_v8664.py` -> RELEASE_GATE_OK
- `python release_gate_v8667.py` -> RELEASE_GATE_OK
- `FULL_BROWSER=1 python verify_ui_browser_smoke_v8662.py` -> ok
- `FULL_BROWSER=1 python verify_saas_ui_v8654.py` -> ok
- `FULL_BROWSER=1 python verify_ui_real_user_path_v860.py` -> 20 ok, 0 fail
- `python run_real_complex_audit_v8641.py` -> ok
- `python run_production_audit_v8642.py` -> ok
- `python check_ui_wizard_cases.py` -> ok

## Ограничение

Свободный текст всё ещё не является полноценным LLM/NLP-парсером. Он разбирается эвристически и специально требует подтверждения карты процесса перед финальным проектным отчётом.
