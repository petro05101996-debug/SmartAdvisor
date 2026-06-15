# Проверка v8.6.13 — исправление ядра выбора стека и отчёта

## Что исправлено

1. Основной стек теперь определяется по связи между участниками, а не по служебному сохранению состояния.
2. БД, outbox/inbox, аудит и сверка выводятся как служебные компоненты, если основной канал связи другой.
3. Отчёт исправляет противоречия старых payload: если связь идёт к партнёру, в аналитику или в Pulsar, отчёт больше не подменяет её основной БД или Kafka.
4. Для каждого шага в отчёте теперь отдельно указаны:
   - что происходит;
   - где именно связь между участниками;
   - основной способ взаимодействия;
   - служебные компоненты;
   - почему выбран способ;
   - почему не другой вариант;
   - что проверить перед выпуском.

## Команды проверки

- python run_tests.py — 68/68 passed
- pytest -q -rs — 26 passed
- python verify_action_grammar_matrix.py — checked=2880 failures=0
- python verify_full_stack_coverage.py — channels=55 single=55 pairwise=3025 issues=0
- python verify_semantic_question_stack_coverage.py — semantic_options=55 channels=55 issues=0
- python verify_branch_question_stack_flow.py — branch_questions=60 channels=55 issues=0
- python verify_complex_e2e_v860.py — 5 сложных кейсов, failed=0, покрыто 55/55 технологий
- python verify_ui_real_user_path_v860.py — 20 ok, 0 fail
- python verify_single_process_map_v8611.py — single_process_map=ok

## Регрессионный кейс из проблемного отчёта

Добавлен тест `test_report_stack_route_consistency_v8613.py`.
Он проверяет, что:

- передача `Система-инициатор → Сервис процесса` не превращается в основную БД;
- передача `Сервис процесса → Внешняя система / партнёр` не превращается в основную БД;
- передача в аналитическое хранилище не превращается в основную БД;
- `Журнал событий Pulsar` не подменяется Kafka;
- БД показывается как служебный компонент, если она нужна для фиксации статуса или outbox/inbox.
