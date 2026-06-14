# Verification v8.4.7 — auto route on move

Изменение: при перемещении шага внутри цепочки UI автоматически пересчитывает:

- `source_system` / «Откуда берутся данные»;
- `system` / «Кто выполняет шаг»;
- `target_system` / «Куда попадает результат»;
- `channel` для типовых шагов CDC/Kafka/DB/DWH;
- `depends_on`, включая защиту от self-dependency и ссылок на несуществующие шаги.

Проверки:

```text
python run_tests.py
68/68 passed

pytest -q -rs
10 passed, 2 skipped

python verify_action_grammar_matrix.py
checked=2880 failures=0 colors={'green': 420, 'yellow': 2400, 'red': 60}

node --check FORM_JS
OK
```

Ограничение: 2 Playwright browser-теста пропущены из-за отсутствия установленного Chromium в окружении.
