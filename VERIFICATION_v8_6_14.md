# Проверка v8.6.14 — аудит логики стека и отчёта

Исправлено после проверки v8.6.13:

1. Поздний результат от внешнего участника в наш сервис теперь определяется как входящий веб-вызов, а не как обратный вызов.
2. Если участник или целевая платформа явно называется RabbitMQ, Pulsar, NATS, Redis Streams, ClickHouse, Object Storage и т.д., отчёт больше не подменяет эту технологию соседним автоподбором.
3. Сообщение об исправлении канала больше не пишет про БД, когда исходная ошибка была не в БД, а в подмене Kafka/Pulsar, callback/webhook и т.п.
4. UI-логика и report-логика синхронизированы по правилам явного стека и направлению позднего результата.

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
20 ok, 0 fail
```

Добавлен regression-тест:

```text
test_report_stack_route_consistency_v8614.py
```
