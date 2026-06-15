# VERIFICATION v8.6.23 — проверка схем и диаграмм

## Что проверялось

Проверка была направлена именно на схемы в отчёте:

- Mermaid flowchart строится по фактической связи `source_system → target_system`, а не через внутреннее поле `system`/исполнитель.
- Исполнитель шага больше не вставляется внутрь маршрута как промежуточный участник.
- Основная бизнес-схема отделена от сквозных контролей.
- Сквозные контроли показываются отдельной схемой: авторизация, CDN, наблюдаемость, Service Mesh, Vault/KMS, маскирование, audit journal.
- Sequence diagram строится по тем же реальным связям, что и основная схема.
- В all-tech кейсе не должно быть ложных self-loop маршрутов вида `Сервис процесса → Сервис процесса`.

## Результаты

```text
python run_tests.py
68/68 passed

pytest -q -rs
31 passed

python verify_report_logic_no_contradictions_v8620.py
REPORT_LOGIC_v8620 ok: payloads=7 checked_steps=104

python verify_all_tech_report_v8621.py
ALL_TECH_REPORT_v8621 ok: steps=58 visible_steps=51 findings=80

python verify_readable_report_v8622.py
READABLE_REPORT_v8622 ok

python verify_diagrams_v8623.py
DIAGRAMS_v8623 ok: diagrams=3

python verify_action_grammar_matrix.py
checked=2880 failures=0

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_semantic_question_stack_coverage.py
semantic_options=55 channels=55 issues=0

python verify_branch_question_stack_flow.py
branch_questions=60 channels=55 issues=0

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail
```

## Итог

В v8.6.22 схемы в отчёте были читаемыми не полностью: они могли строиться через исполнителя шага и давать ложные маршруты. В v8.6.23 схема строится по реальной связи `кто → кому`, а сквозные контроли вынесены отдельно.
