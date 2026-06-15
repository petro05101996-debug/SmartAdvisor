# VERIFICATION v8.6.24 — сценарии отчёта

## Что проверялось

Проверялась не просто генерация раздела «Сценарии», а смысл сценарного блока в отчёте:

- основной сценарий не должен быть сырой выгрузкой всех шагов подряд;
- all-tech / карта возможностей не должна выдаваться за один happy path;
- сквозные контроли не должны попадать в основной бизнес-сценарий;
- альтернативные сценарии должны иметь триггер, ход, ожидаемый результат и обязательные проверки;
- ошибочные сценарии должны описывать восстановление, а не только название проблемы;
- русский язык в сценариях не должен содержать машинные фразы.

## Найденная проблема в v8.6.23

В отчёте сценарный раздел строился как простой список `main_flow` из всех шагов. На all-tech кейсе это давало бессмысленный «основной сценарий» из десятков несвязанных технологий: ActiveMQ, Airflow, API Gateway, OAuth2, Azure Service Bus и т.д. Сквозные контроли и инфраструктурные элементы могли выглядеть как обычные шаги бизнес-процесса.

## Исправление v8.6.24

- Для больших all-tech/portfolio схем отчёт теперь явно пишет, что это карта интеграционных возможностей, а не один линейный happy path.
- Вместо искусственного основного сценария формируются сценарные блоки по типам взаимодействий:
  - API и онлайн-взаимодействие;
  - асинхронный обмен;
  - данные и чтение;
  - аналитика и загрузки;
  - файлы и доставка контента;
  - оркестрация процесса.
- Сквозные контроли вынесены в отдельный сценарный блок.
- Альтернативные сценарии раскрываются как мини-use-case: когда возникает, как проходит, ожидаемый результат, обязательные проверки.
- Ошибочные сценарии показывают восстановление.
- Добавлена проверка `verify_scenarios_v8624.py`.

## Прогоны

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

python verify_scenarios_v8624.py
SCENARIOS_v8624 ok: scenario_lines=141

python verify_action_grammar_matrix.py
checked=2880 failures=0

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_semantic_question_stack_coverage.py
semantic_options=55 channels=55 issues=0

python verify_branch_question_stack_flow.py
branch_questions=60 channels=55 issues=0

python verify_complex_e2e_v860.py
5 complex cases, failed=0, covered 55/55 technologies

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail
```

## Проверочный отчёт

В архив включён файл:

```text
ALL_TECH_REPORT_v8_6_24_SCENARIOS.md
```
