#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
import engine
from report import markdown_report

role_by_channel = {
 'cdn':'cdn','api_gateway':'gateway','auth_oidc':'security','service_mesh':'mesh','esb':'legacy','vault':'security','observability':'observability',
 'db':'db','read_replica':'db','db_sharding':'db','mongodb':'db','cassandra':'db','dynamodb':'db','redis_cache':'cache','memcached':'cache','redis_lock':'cache','search':'search','vector_db':'search',
 'clickhouse':'analytics','data_warehouse':'analytics','data_lake':'analytics','lakehouse':'analytics','dbt':'analytics','spark':'analytics','airflow':'analytics','etl':'analytics','cdc':'analytics','batch':'analytics',
 'kafka':'broker','pulsar':'broker','rabbitmq':'broker','activemq':'broker','ibm_mq':'broker','nats':'broker','sns_sqs':'broker','azure_service_bus':'broker','gcp_pubsub':'broker','redis_streams':'broker','redis_queue':'broker','queue':'broker','mqtt':'broker',
 'sftp':'external','file':'external','object_storage':'storage','soap':'legacy', 'webhook':'external','callback':'external','websocket':'external','sse':'external',
}
channel_target = {
 'cdn':'CDN контент',
 'api_gateway':'API Gateway',
 'auth_oidc':'Сервис авторизации OIDC',
 'service_mesh':'Service Mesh',
 'rest':'REST сервис заявок',
 'graphql':'GraphQL API клиентов',
 'odata':'OData API справочников',
 'grpc':'Внутренний gRPC сервис скоринга',
 'soap':'Legacy SOAP шлюз',
 'esb':'Корпоративная ESB',
 'db':'Основная БД процесса',
 'read_replica':'Реплика чтения',
 'db_sharding':'Шардированный кластер БД',
 'mongodb':'MongoDB документы',
 'cassandra':'Cassandra telemetry store',
 'dynamodb':'Key-Value хранилище',
 'redis_cache':'Redis cache',
 'memcached':'Memcached cache',
 'redis_lock':'Redis lock service',
 'search':'Поисковый индекс',
 'vector_db':'Векторная БД',
 'kafka':'Kafka event log',
 'pulsar':'Pulsar event log',
 'rabbitmq':'RabbitMQ task queue',
 'activemq':'ActiveMQ очередь',
 'ibm_mq':'IBM MQ очередь',
 'nats':'NATS bus',
 'sns_sqs':'AWS SNS/SQS',
 'azure_service_bus':'Azure Service Bus',
 'gcp_pubsub':'Google Pub/Sub',
 'redis_streams':'Redis Streams',
 'redis_queue':'Redis queue',
 'queue':'Корпоративная очередь',
 'mqtt':'MQTT broker',
 'webhook':'Входящий endpoint результата',
 'callback':'Endpoint обратного результата',
 'websocket':'WebSocket канал оператора',
 'sse':'SSE канал уведомлений',
 'sftp':'SFTP сервер партнёра',
 'file':'Файловый каталог обмена',
 'object_storage':'Object Storage S3',
 'batch':'Batch processor',
 'cdc':'CDC pipeline',
 'etl':'ETL/ELT pipeline',
 'airflow':'Airflow DAG',
 'spark':'Spark cluster',
 'dbt':'dbt модели витрин',
 'clickhouse':'ClickHouse аналитика',
 'data_warehouse':'Data Warehouse',
 'data_lake':'Data Lake raw zone',
 'lakehouse':'Lakehouse curated zone',
 'workflow_engine':'Workflow engine Temporal',
 'bpm_engine':'BPMN Camunda',
 'vault':'Vault KMS',
 'observability':'Контур наблюдаемости',
}
channel_names = {
 'cdn':'Отдать статический контент через CDN',
 'api_gateway':'Принять внешний запрос через API Gateway',
 'auth_oidc':'Проверить пользователя через OAuth2/OIDC',
 'service_mesh':'Выполнить внутренний вызов через Service Mesh',
 'rest':'Отправить синхронный REST-запрос в сервис заявок',
 'graphql':'Получить гибкую проекцию через GraphQL',
 'odata':'Прочитать корпоративный справочник через OData',
 'grpc':'Быстро получить ответ от внутреннего gRPC-сервиса',
 'soap':'Вызвать legacy SOAP-контракт',
 'esb':'Передать сообщение через корпоративную ESB',
 'db':'Сохранить состояние процесса в основной БД',
 'read_replica':'Прочитать состояние из реплики чтения',
 'db_sharding':'Записать горячую сущность в шардированный кластер БД',
 'mongodb':'Сохранить документ заявки в MongoDB',
 'cassandra':'Записать высокочастотную телеметрию в Cassandra',
 'dynamodb':'Сохранить ключ-значение в DynamoDB',
 'redis_cache':'Положить горячую модель в Redis cache',
 'memcached':'Положить временный справочник в Memcached',
 'redis_lock':'Поставить распределённую блокировку в Redis',
 'search':'Обновить поисковый индекс',
 'vector_db':'Записать embedding документа в векторную БД',
 'kafka':'Опубликовать бизнес-событие в Kafka',
 'pulsar':'Опубликовать потоковое событие в Pulsar',
 'rabbitmq':'Поставить фоновую задачу в RabbitMQ',
 'activemq':'Отправить корпоративное сообщение в ActiveMQ',
 'ibm_mq':'Передать гарантированное сообщение в IBM MQ',
 'nats':'Передать короткое событие через NATS',
 'sns_sqs':'Разослать облачное событие через SNS/SQS',
 'azure_service_bus':'Поставить сообщение в Azure Service Bus',
 'gcp_pubsub':'Опубликовать сообщение в Google Pub/Sub',
 'redis_streams':'Записать короткий поток в Redis Streams',
 'redis_queue':'Поставить короткую задачу в Redis queue',
 'queue':'Поставить задачу в корпоративную очередь без выбранного брокера',
 'mqtt':'Принять телеметрию устройства через MQTT',
 'webhook':'Принять входящий веб-вызов от партнёра',
 'callback':'Принять поздний результат по обратному вызову',
 'websocket':'Открыть двусторонний WebSocket-канал',
 'sse':'Отправить серверные уведомления через SSE',
 'sftp':'Передать файл партнёру через SFTP',
 'file':'Сформировать файл выгрузки',
 'object_storage':'Сохранить большой документ в Object Storage',
 'batch':'Запустить пакетную обработку периода',
 'cdc':'Передать изменения из БД через CDC',
 'etl':'Загрузить данные в аналитику через ETL/ELT',
 'airflow':'Оркестрировать загрузки через Airflow',
 'spark':'Обработать большой объём данных в Spark',
 'dbt':'Собрать аналитические модели в dbt',
 'clickhouse':'Записать события в ClickHouse',
 'data_warehouse':'Загрузить согласованные витрины в Data Warehouse',
 'data_lake':'Сложить сырые данные в Data Lake',
 'lakehouse':'Опубликовать очищенные таблицы в Lakehouse',
 'workflow_engine':'Запустить длительный процесс в Workflow engine',
 'bpm_engine':'Передать ручной этап в BPMN-процесс',
 'vault':'Получить секрет интеграции из Vault/KMS',
 'observability':'Отправить метрики, логи и трассировки в контур наблюдаемости',
}

sync_channels = engine.SYNC_CHANNELS
channels = sorted(engine.ALL_CHANNELS)
steps=[]
prev = 0
for i,ch in enumerate(channels,1):
    target = channel_target[ch]
    if ch in ('webhook','callback'):
        source = 'Внешний партнёр'
        system = 'Сервис процесса'
    elif ch in ('mqtt',):
        source = 'IoT устройство'
        system = 'Сервис телеметрии'
    elif ch in ('cdn','api_gateway','auth_oidc'):
        source = 'Клиентский канал'
        system = target
    else:
        source = 'Сервис процесса'
        system = 'Сервис процесса'
    blocking = ch in sync_channels
    timeout = 300 if blocking else 0
    retry = 'auto' if ch in engine.BROKER_CHANNELS or ch in ('rest','grpc','soap','webhook','callback','sftp','batch','cdc','etl') else 'none'
    idem = 'key' if ch in engine.BROKER_CHANNELS or ch in ('rest','grpc','webhook','callback','db','cdc','etl','sftp','file','object_storage') else 'none'
    writes = ch in {'db','db_sharding','mongodb','cassandra','dynamodb','clickhouse','data_warehouse','data_lake','lakehouse','object_storage','file','search','vector_db','kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt','cdc','etl','batch','airflow','spark','dbt','audit'}
    data_out = f"{ch}: событие/запись/результат с eventId, businessId, correlationId"
    if ch in engine.BROKER_CHANNELS:
        data_in = f"businessId как ключ партиционирования; eventId; channel={ch}"
    elif ch in ('webhook','callback'):
        data_in = "providerEventId + providerCode + подпись HMAC + timestamp"
    elif ch in ('data_warehouse','clickhouse','data_lake','lakehouse','cdc','etl','batch','airflow','spark','dbt'):
        data_in = "controlCount, checksum, watermark, период загрузки"
    else:
        data_in = "businessId, operationId, correlationId"
    steps.append({
        'order': i, 'name': channel_names[ch], 'system': system, 'source_system': source, 'target_system': target,
        'channel': ch, 'blocking': blocking, 'timeout_ms': timeout, 'retry': retry, 'idempotency': idem,
        'writes_entity': writes, 'depends_on': prev if prev else 0,
        'data_in': data_in, 'data_out': data_out,
        'compensation': 'ручной разбор и безопасная повторная обработка' if ch in engine.ASYNC_CHANNELS else '',
    })
    prev = i

systems = [
 {'name':'Клиентский канал','role':'external','criticality':'high','stability':'stable'},
 {'name':'Сервис процесса','role':'internal','criticality':'critical','stability':'stable'},
 {'name':'Сервис телеметрии','role':'internal','criticality':'high','stability':'stable'},
 {'name':'Внешний партнёр','role':'external','criticality':'high','stability':'limited'},
]
for ch,target in channel_target.items():
    systems.append({'name': target, 'role': role_by_channel.get(ch,'internal'), 'criticality':'high', 'stability':'stable'})

payload = {
 'meta': {
  'name':'Ультра-кейс: все цепочки и все технологии',
  'entity':'EnterpriseProcess',
  'goal':'Проверить отчёт на полном наборе интеграционных цепочек и технологий.',
  'description':'Синтетический enterprise-процесс со всеми типами интеграций: синхронные API, брокеры, файлы, аналитика, кэш, хранилища, realtime, security и observability.',
  'lookup_keys':'businessId + operationId + eventId + providerCode + correlationId; partition key по businessId',
  'customer_visible': True, 'money':'direct', 'regulatory': True, 'sla_ms':2500, 'read_freq':'high', 'ordering':'per_entity',
  'statuses':['CREATED','VALIDATING','WAITING_EXTERNAL','PROCESSING','SENT','COMPLETED','FAILED','NEEDS_MANUAL_REVIEW'],
  'fields':[
    {'name':'businessId','type':'uuid','required':True,'unique':False,'indexed':True,'sensitive':False},
    {'name':'operationId','type':'uuid','required':True,'unique':True,'indexed':True,'sensitive':False},
    {'name':'eventId','type':'uuid','required':True,'unique':True,'indexed':True,'sensitive':False},
    {'name':'correlationId','type':'uuid','required':True,'unique':False,'indexed':True,'sensitive':False},
    {'name':'personalData','type':'json','required':False,'unique':False,'indexed':False,'sensitive':True},
  ],
  'load_rps':5000,'peak_factor':5,'multi_tenant':True,'replacing_legacy':True
 },
 'systems': systems,
 'steps': steps
}
open('/mnt/data/mega_all_tech_payload_v8620.json','w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2))
res = engine.analyze(payload)
open('/mnt/data/mega_all_tech_result_v8620.json','w',encoding='utf-8').write(json.dumps(res,ensure_ascii=False,indent=2))
md = markdown_report(res)
open('/mnt/data/mega_all_tech_report_v8620.md','w',encoding='utf-8').write(md)
print('ok',res.get('ok'),'steps',len(steps),'findings',len(res.get('findings',[])),'patterns',len(res.get('patterns',[])))
print('report_len',len(md))
print(md[:2000])
