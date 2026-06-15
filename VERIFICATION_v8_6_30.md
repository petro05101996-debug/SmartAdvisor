# VERIFICATION v8.6.30 — real complex report audit

## Что проверено

Проверка выполнена не только по unit/regression-тестам, но и через реальный прогон пяти сложных payload-кейсов с последующим чтением markdown-отчётов:

1. Цифровое открытие банковского продукта.
2. IoT-телеметрия и онлайн-тревоги.
3. E-commerce заказ с каталогом, ERP и партнёрами.
4. Миграция enterprise-процесса со старого контура.
5. Страховая выплата с партнёрами и документами.

Также добавлен пользовательский regression-кейс из последнего отчёта:
- входящий инициатор не должен считаться внешней блокирующей зависимостью;
- запрос данных через Kafka не должен утверждаться как корректный стек;
- аналитическое хранилище не должно превращаться в документное хранилище;
- система-инициатор не должна считаться вторым писателем сущности только из-за входящего запроса.

## Исправления

1. Старые component/self шаги больше не превращаются в ложное «сначала исправить схему», если настоящая технология находится в поле `system`: MongoDB, DynamoDB, Redis lock/cache, OData ERP, dbt, DWH, RabbitMQ, NATS и т.д.
2. Диаграммы, таблицы и сценарии используют эффективный маршрут, например `GraphQL BFF → MongoDB`, а не старый сырой маршрут `GraphQL BFF → GraphQL BFF`.
3. Входящий внешний инициатор больше не считается внешней блокирующей зависимостью. Риск external blocking срабатывает только на исходящий блокирующий вызов во внешнюю систему/legacy.
4. Маскирование данных, аудит, секреты и наблюдаемость снова имеют приоритет над component-step логикой и не превращаются в REST/обычную БД.
5. Отчёты дополнительно вычитаны: убраны остатки `event log`, `worker`, `task queue`, `клиентский лимиты запросовer`, `операционном основной поток` и другие машинные фразы.

## Проверки

```text
python verify_real_complex_reports_v8630.py
REAL_COMPLEX_REPORTS_v8630 ok: complex_cases=5, output=REAL_COMPLEX_REPORTS_v8_6_30

python verify_report_logic_no_contradictions_v8620.py
REPORT_LOGIC_v8620 ok: payloads=7 checked_steps=104

python verify_diagrams_v8623.py
DIAGRAMS_v8623 ok: diagrams=3

python verify_scenarios_v8624.py
SCENARIOS_v8624 ok

python verify_report_sections_v8625.py
REPORT_SECTIONS_v8625 ok

python verify_all_tech_report_v8626.py
ALL_TECH_REPORT_v8626 ok

python verify_final_report_confidence_v8627.py
FINAL_REPORT_CONFIDENCE_v8627 ok

python verify_clarification_step_toggle_v8628.py
CLARIFICATION_STEP_TOGGLE_v8628 ok

python verify_ui_real_user_path_v860.py
SUMMARY: 20 ok, 0 fail

python verify_full_stack_coverage.py
channels=55 single=55 pairwise=3025 issues=0

python verify_complex_e2e_v860.py
5 сложных кейсов, failed=0, покрыто 55/55 технологий

pytest -q -rs
31 passed

python run_tests.py
68/68 passed
```

## Итог

v8.6.30 закрывает ошибки, найденные при чтении реальных сложных отчётов после v8.6.29. Проверка теперь включает отдельный real complex report audit, а не только старые зелёные unit-тесты.
