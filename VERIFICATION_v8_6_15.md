# Проверка v8.6.15

Исправления:
- Единая схема процесса упрощена: показывает только последовательность, участников и связь между ними. Убраны теги стека, зависимости, readiness и объяснения из самой схемы.
- Перед определением стека добавлена проверка логичности схемы.
- Если схема противоречивая, стек не формируется сразу: показываются замечания и предложения автоправки.
- Пользователь может применить предложенные улучшения или продолжить без исправлений.

Проверки:

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

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail

python verify_single_process_map_v8611.py
single_process_map=ok rows=3 overflow=0

python verify_schema_validation_v8615.py
SUMMARY: 5 ok, 0 fail
```
