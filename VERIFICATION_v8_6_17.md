# Проверка v8.6.17 — контекстные уточнения по конкретным связям

## Что изменено

Этап «Уточнения процесса» больше не показывает общий список вопросов в вакууме. Теперь вопросы строятся из схемы пользователя и группируются по каждой конкретной связи.

Для каждой связи показывается:

- номер шага;
- название связи;
- маршрут «участник → участник»;
- только релевантные группы вопросов;
- пояснение, почему этот вопрос относится именно к этой связи.

Пример: если в схеме есть связь «Сервис процесса → Внешняя система / партнёр», рядом с ней будут вопросы про синхронный вызов, поздний результат, внешний контур и безопасность. Если есть связь «Хранилище состояния → Аналитическое хранилище», рядом будут вопросы про аналитику, загрузку, сверку, большие данные и контроль полноты.

## Проверки

```text
python run_tests.py
68/68 passed

pytest -q -rs
29 passed

python verify_action_grammar_matrix.py
checked=2880 failures=0

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_semantic_question_stack_coverage.py
semantic_options=55 channels=55 issues=0

python verify_branch_question_stack_flow.py
branch_questions=60 channels=55 issues=0

python verify_deep_schema_validation_v8616.py
7 ok, 0 fail

python verify_contextual_clarifications_v8617.py
contextual_clarifications=ok cards>=4 strict_fast_read=1

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий

python verify_ui_real_user_path_v860.py
20 ok, 0 fail

python verify_single_process_map_v8611.py
single_process_map=ok
```

## Вывод

Уточнения теперь не должны восприниматься как отдельный опросник. Они являются продолжением построенной схемы: каждая группа вопросов относится к конкретной связи и помогает точнее определить стек именно для этого места процесса.
