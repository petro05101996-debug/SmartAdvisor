# Проверка v8.6.11: единая схема процесса без дублирования

Исправление: на этапе проектирования связей больше нет двух конкурирующих схем. Убрана видимая секция «Живая схема взаимодействий» из рабочей формы. Осталась одна понятная схема — «Единая схема процесса».

Что проверено:

- пользователь видит форму добавления связи;
- ниже формы есть компактный список «Добавленные связи» для порядка, удаления и перестановки;
- справа или ниже на мобильном есть одна схема процесса;
- полноценные карточки действий с техническими настройками скрыты в простом режиме и не дублируют схему;
- стек не показывается до этапа определения стека;
- после определения стека технология появляется в единой схеме;
- горизонтального переполнения на мобильном сценарии нет.

Проверки:

```text
python run_tests.py
68/68 passed

pytest -q -rs
25 passed

python verify_action_grammar_matrix.py
checked=2880 failures=0

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_semantic_question_stack_coverage.py
semantic_options=55 channels=55 issues=0

python verify_branch_question_stack_flow.py
branch_questions=60 channels=55 issues=0

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail

python verify_single_process_map_v8611.py
single_process_map=ok rows=3 overflow=0
```
