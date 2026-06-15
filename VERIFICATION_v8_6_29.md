# Проверка v8.6.29 — фиксы отчёта после реального пользовательского отчёта

Исправлено:

1. `запрашивает данные` больше не получает уверенный Kafka-стек без уточнения. Если выбран брокер, отчёт требует исправить смысл связи: запрос-ответ через API/файл/batch/CDC либо переименовать связь в публикацию события/команды.
2. `Аналитическое хранилище` больше не получает `Документное хранилище` как основной способ взаимодействия. Для передачи в аналитику выбирается способ доставки: ETL/ELT, CDC, batch, поток событий или файл.
3. `Система-инициатор → Сервис процесса` больше не считается вторым писателем сущности только из-за входящего запроса.
4. Сохранение в обычный сервис теперь блокируется проверкой логики схемы: нужно либо выбрать хранилище, либо изменить действие на передачу данных.
5. SQL-черновик заменён на валидный SQL с техническими именами `event_id`, `correlation_id`, `event_body`, `inbox_dedup`; убран дубль `status`.
6. Матрица деталей больше не показывает строки с пустыми колонками `— / —`.
7. Дедублированы критерии приёмки сценариев.
8. Добавлены дополнительные правки русского языка в отчёте и приложениях.

Проверки:

```text
python run_tests.py
68/68 passed

pytest -q -rs
31 passed

python verify_clarification_step_toggle_v8628.py
CLARIFICATION_STEP_TOGGLE_v8628 ok

python verify_user_report_regression_v8629.py
USER_REPORT_REGRESSION_v8629 ok

python verify_report_logic_no_contradictions_v8620.py
REPORT_LOGIC_v8620 ok: payloads=7 checked_steps=104

python verify_readable_report_v8622.py
READABLE_REPORT_v8622 ok

python verify_diagrams_v8623.py
DIAGRAMS_v8623 ok

python verify_scenarios_v8624.py
SCENARIOS_v8624 ok

python verify_report_sections_v8625.py
REPORT_SECTIONS_v8625 ok

python verify_all_tech_report_v8626.py
ALL_TECH_REPORT_v8626 ok

python verify_final_report_confidence_v8627.py
FINAL_REPORT_CONFIDENCE_v8627 ok

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий
```
