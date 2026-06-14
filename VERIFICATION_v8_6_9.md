# Проверка v8.6.9 — исправление мобильной раскладки связей

## Что исправлено

На мобильном экране этап «Связи между участниками» мог отображаться в две колонки из-за конфликта CSS-правил: общее мобильное правило переводило конструктор в одну колонку, но более позднее правило для stage-interactions снова возвращало сетку `1fr 320px`. В результате навигация этапов, готовность и карточки связей визуально накладывались друг на друга.

Исправлено:

- для экранов до 900 px все этапы конструктора принудительно идут в одну колонку;
- навигация этапов стала горизонтальной прокручиваемой лентой, а не вертикальным блоком поверх контента;
- карта процесса и готовность уходят ниже формы, а не стоят сбоку;
- нижняя кнопка запуска не перекрывает форму связей;
- блоки схемы, формы и карточек получили `max-width: 100%` и `clear: both`.

## Проверки

- `python run_tests.py` — 68/68 passed
- `pytest -q -rs` — 25 passed
- `python verify_action_grammar_matrix.py` — checked=2880 failures=0
- `python verify_full_stack_coverage.py` — channels=55 single=55 pairwise=3025 issues=0
- `python verify_semantic_question_stack_coverage.py` — semantic_options=55 channels=55 issues=0
- `python verify_branch_question_stack_flow.py` — branch_questions=60 channels=55 issues=0
- `python verify_complex_e2e_v860.py` — 5 сложных кейсов, failed=0, покрыто 55/55 технологий
- `python verify_live_schema_v867.py` — live_schema_checks=ok rows=3 errors=0
- HTTP smoke: `/health`, `/`, `/api/analyze` работают

## Вывод

Ошибка была именно в адаптивной верстке мобильного экрана, не в ядре анализа. Логика построения участников, связей, уточнений, определения стека и отчёта не сломалась.
