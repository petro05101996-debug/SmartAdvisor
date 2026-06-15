# Проверка сложных кейсов v8.6.0

## Сложный кейс 1: цифровое открытие банковского продукта
- Шагов: 20
- Каналы/технологии: api_gateway, auth_oidc, batch, cdc, cdn, data_warehouse, db, grpc, kafka, object_storage, observability, rabbitmq, read_replica, redis_cache, redis_lock, search, service_mesh, soap, vault, webhook
- analyze.ok: True
- Ошибки ссылок цепочки: 0
- Общие/пустые объяснения в отчёте: нет
- Вердикт: red / 0.0/10
- Риски: critical=0, high=12, medium=13

## Сложный кейс 2: IoT-телеметрия и онлайн-тревоги
- Шагов: 13
- Каналы/технологии: airflow, cassandra, clickhouse, data_lake, dbt, mqtt, nats, observability, pulsar, redis_streams, spark, sse, websocket
- analyze.ok: True
- Ошибки ссылок цепочки: 0
- Общие/пустые объяснения в отчёте: нет
- Вердикт: red / 3.7/10
- Риски: critical=0, high=4, medium=8

## Сложный кейс 3: заказ в e-commerce с каталогом, ERP и партнёрами
- Шагов: 17
- Каналы/технологии: azure_service_bus, cdn, db, db_sharding, dynamodb, file, graphql, kafka, memcached, mongodb, object_storage, odata, queue, redis_queue, search, sftp, vector_db
- analyze.ok: True
- Ошибки ссылок цепочки: 0
- Общие/пустые объяснения в отчёте: нет
- Вердикт: red / 0.0/10
- Риски: critical=1, high=11, medium=15

## Сложный кейс 4: миграция enterprise-процесса со старого контура
- Шагов: 14
- Каналы/технологии: activemq, airflow, api_gateway, bpm_engine, cdc, dbt, esb, etl, gcp_pubsub, ibm_mq, lakehouse, sns_sqs, spark, workflow_engine
- analyze.ok: True
- Ошибки ссылок цепочки: 0
- Общие/пустые объяснения в отчёте: нет
- Вердикт: red / 0.0/10
- Риски: critical=1, high=7, medium=7

## Сложный кейс 5: страховая выплата с партнёрами и документами
- Шагов: 18
- Каналы/технологии: api_gateway, auth_oidc, callback, cdc, db, kafka, object_storage, observability, rabbitmq, redis_cache, redis_lock, rest, search, sftp, soap, vault, webhook, workflow_engine
- analyze.ok: True
- Ошибки ссылок цепочки: 0
- Общие/пустые объяснения в отчёте: нет
- Вердикт: red / 0.0/10
- Риски: critical=1, high=12, medium=12

## Итог
- Сложных кейсов проверено: 5
- Проваленных кейсов: 0
- Технологий покрыто в сложных кейсах: 55 из 55
- Не использовались в этих 5 кейсах, но покрыты матрицей: нет