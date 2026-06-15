# Проверка v8.6.32 — полный прогон ядра по вариациям

Дата: 2026-06-15

## Что добавлено

Добавлена проверка `verify_exhaustive_core_variations_v8632.py`, которая прогоняет ядро не только по старым регрессиям, но и по матрице вариаций:

- 55 каналов/технологий каталога;
- корректные пары источник → получатель для каждого канала;
- некорректные/спорные связи: запрос данных через брокер, сохранение в сервис, спорная аналитика;
- реалистичный сквозной процесс: API Gateway → БД → SOAP legacy → внешний партнёр → webhook → Kafka → CDC → аналитика → Vault;
- проверка отчёта на старые логические и языковые дефекты.

## Найдено и исправлено

1. В редких ветках отчёта ещё мог оставаться текстовый хвост `критичного журнал событий`.
2. В сценариях входящего webhook мог оставаться термин `Inbox` вместо русского описания.
3. Дополнительно закрыты остаточные англоязычные хвосты: `Outbox`, `DLQ`, `retry`, `replay`, `runbook`, `payload`, `task queue`, `worker`.
4. Добавлена защитная регулярная вычитка от артефактов вроде `журналааааа событий`.

## Прогоны

```text
python run_tests.py
68/68 passed

pytest -q -rs
31 passed

python verify_exhaustive_core_variations_v8632.py
EXHAUSTIVE_CORE_VARIATIONS_v8632 ok: channels=55 invalid_cases=3 realistic=1

python verify_report_logic_no_contradictions_v8620.py
REPORT_LOGIC_v8620 ok: payloads=7 checked_steps=104

python verify_user_report_regression_v8629.py
USER_REPORT_REGRESSION_v8629 ok

python verify_real_complex_reports_v8630.py
REAL_COMPLEX_REPORTS_v8630 ok: complex_cases=5

python verify_all_tech_report_v8626.py
ALL_TECH_REPORT_v8626 ok: lines=1503 steps=58 findings=82

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий
```

Дополнительно ранее в этом же полном прогоне прошли:

```text
verify_action_grammar_matrix.py — checked=2880 failures=0
verify_full_stack_coverage.py — channels=55 single=55 pairwise=3025 issues=0
verify_branch_question_stack_flow.py — branch_questions=60 channels=55 issues=0
verify_semantic_question_stack_coverage.py — semantic_options=55 channels=55 issues=0
verify_mobile_layout_flow_v869.py — SUMMARY: 36 ok, 0 fail
verify_mobile_no_overlap_v869.py — SUMMARY: 36 ok, 0 fail
verify_ui_real_user_path_v860.py — SUMMARY: 20 ok, 0 fail
```

## Вывод

v8.6.32 закрывает не новый архитектурный класс ошибок, а остаточные дефекты полного прогона ядра: языковые хвосты и редкие ветки отчёта, которые не покрывались обычными тестами. Проверка теперь включает матрицу всех 55 технологий и реалистичный сквозной процесс.
