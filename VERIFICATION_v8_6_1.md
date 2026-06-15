# Verification v8.6.1-readable-chain-builder

## Цель правки

Пользователь не понимал, как строить цепочку: что такое элемент, как работают связи, откуда берутся поля «откуда / кто выполняет / куда». В v8.6.1 простой режим изменён так, чтобы пользователь работал не с техническими элементами, а с понятным сценарием процесса.

## Проверки

```text
python run_tests.py
68/68 passed
```

```text
pytest -q -rs
23 passed
```

```text
python verify_action_grammar_matrix.py
checked=2880 failures=0
```

```text
python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0
```

```text
python verify_semantic_question_stack_coverage.py
semantic_options=55 channels=55 issues=0
```

```text
python verify_ui_real_user_path_v860.py
SUMMARY: 32 ok, 0 fail
```

```text
python verify_complex_e2e_v860.py
Сложных кейсов проверено: 5
Проваленных кейсов: 0
Технологий покрыто в сложных кейсах: 55 из 55
```

HTTP smoke:

```text
GET /health -> ok
GET / -> 200
POST /api/analyze -> ok
```

## Что важно

- В простом режиме больше не нужно понимать связи руками.
- Следующий шаг автоматически связан с предыдущим.
- При добавлении простого действия маршрут и зависимости пересчитываются.
- В экспертном режиме перемещение и ручная корректировка сохранены.
- Внутренняя логика, отчёты и подбор стека не сломаны.
