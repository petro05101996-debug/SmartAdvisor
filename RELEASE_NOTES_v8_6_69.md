# SmartAdvisor v8.6.69 — Project Navigator

Цель релиза: сделать продукт полезным не только как отчёт/чеклист, а как рабочий штурман проектирования.

## Главное

- Добавлен слой Project Navigator поверх детерминированного ядра.
- Добавлен режим ревью готового решения: сильные стороны, блокеры, первые действия.
- Добавлен проектный пакет: карта source→target, сущности, контракты, статусная модель, ошибки по шагам, ADR, тест-кейсы, production checklist.
- Добавлена матрица готовности: обсуждение / архитектурное проектирование / передача в разработку / production.
- Добавлены вопросы к бизнесу, разработке, эксплуатации и архитектурному ревью.
- CLI получил команды/флаги: `ревью`, `вопросы`, `пакет`, `--review`, `--questions`, `--package`.
- UI результата показывает рабочий проектный пакет отдельным блоком Project Navigator.
- Markdown-отчёт дополняется разделом `Рабочий проектный пакет`.

## Важные исправления

- Исполнитель шага для маршрута `source -> target` теперь выводится из действия: получение/чтение выполняет получатель, сохранение/маппинг/валидация — сервис-источник.
- Сохранена совместимость со старым UI/version checks.
- Добавлены регрессионные тесты Project Navigator.

## Проверки

- `pytest -q`: 66 passed, 2 skipped.
- `python run_tests.py`: 68/68 passed.
- `python release_gate_v8664.py`: OK после clean.
- `python release_gate_v8667.py`: OK после clean.
- `FULL_BROWSER=1 python verify_ui_browser_smoke_v8662.py`: OK.
- `FULL_BROWSER=1 python verify_saas_ui_v8654.py`: OK.
- `FULL_BROWSER=1 python verify_ui_real_user_path_v860.py`: 20 OK, 0 fail.
- `python run_production_audit_v8642.py`: direct 14/14 OK, channel issues 0, api 4/4 OK.
- `python check_ui_wizard_cases.py`: bad 0, ui_ref_issues 0.
