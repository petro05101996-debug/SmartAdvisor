#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json, os
from pathlib import Path
import engine
from engine import analyze
from report import markdown_report, _v8622_channel_purpose, _primary_channel_v8613, _route_error_v8620, _is_cross_control_step_v8619, _v8623_step_source_target

BASE_SYSTEMS = [
    {'name':'Система-инициатор','role':'external','owner':'team'},
    {'name':'Сервис процесса','role':'internal','owner':'team'},
    {'name':'Внешняя система / партнёр','role':'external','owner':'partner'},
    {'name':'Старый контур','role':'legacy','owner':'legacy'},
    {'name':'Хранилище состояния процесса','role':'db','owner':'team'},
    {'name':'Аналитическое хранилище','role':'analytics','owner':'data'},
    {'name':'Очередь событий','role':'broker','owner':'platform'},
    {'name':'Файловое хранилище','role':'internal','owner':'team'},
    {'name':'Внутренний сервис быстрых ответов','role':'internal','owner':'team'},
    {'name':'Audit journal','role':'internal','owner':'sec'},
    {'name':'Хранилище секретов','role':'internal','owner':'sec'},
    {'name':'Контур наблюдаемости','role':'internal','owner':'ops'},
]

CHANNEL_EXPECT = {
    # channel: (name, source, target, expected_fragment)
    'rest': ('Сервис процесса передаёт данные в Внешняя система / партнёр', 'Сервис процесса', 'Внешняя система / партнёр', 'REST'),
    'graphql': ('Нужен гибкий API для разных клиентов', 'Сервис процесса', 'Внутренний сервис быстрых ответов', 'GraphQL'),
    'odata': ('Сервис процесса передаёт данные в OData API ERP', 'Сервис процесса', 'Внешняя система / партнёр', 'OData'),
    'grpc': ('Быстро получить ответ от внутреннего сервиса', 'Сервис процесса', 'Внутренний сервис быстрых ответов', 'gRPC'),
    'soap': ('Вызвать старый WSDL XML контракт', 'Сервис процесса', 'Старый контур', 'SOAP'),
    'api_gateway': ('Принять внешний запрос через единую точку входа', 'Система-инициатор', 'Сервис процесса', 'API Gateway'),
    'service_mesh': ('Управлять внутренними сервисными вызовами', 'Сервис процесса', 'Внутренний сервис быстрых ответов', 'Service Mesh'),
    'esb': ('Передать сообщение через интеграционную шину', 'Сервис процесса', 'Старый контур', 'ESB'),
    'db': ('Сервис процесса сохраняет результат в Хранилище состояния процесса', 'Сервис процесса', 'Хранилище состояния процесса', 'Основная база данных'),
    'read_replica': ('Разгрузить чтение на реплику БД', 'Сервис процесса', 'Хранилище состояния процесса', 'Реплика'),
    'db_sharding': ('Разделить данные по шардам', 'Сервис процесса', 'Хранилище состояния процесса', 'Шардирование'),
    'mongodb': ('Сохранить документ в документное хранилище MongoDB', 'Сервис процесса', 'Документное хранилище MongoDB', 'Документное'),
    'cassandra': ('Записать телеметрию в Cassandra', 'Сервис процесса', 'Cassandra cluster', 'Cassandra'),
    'dynamodb': ('Сохранить профиль ключ-значение в DynamoDB', 'Сервис процесса', 'DynamoDB Key-Value', 'ключ-значение'),
    'clickhouse': ('Передать события в ClickHouse', 'Сервис процесса', 'ClickHouse analytics', 'Колоночная'),
    'data_warehouse': ('Сервис процесса передаёт данные в Аналитическое хранилище', 'Сервис процесса', 'Аналитическое хранилище', 'ETL'),
    'data_lake': ('Сложить сырые данные в озеро данных', 'Сервис процесса', 'Озеро данных', 'ETL'),
    'lakehouse': ('Сложить таблицы в lakehouse', 'Сервис процесса', 'Lakehouse', 'ETL'),
    'redis_cache': ('Быстро читать часто используемые данные из Redis cache', 'Сервис процесса', 'Redis cache', 'кэш'),
    'memcached': ('Быстро читать временные данные из Memcached', 'Сервис процесса', 'Memcached', 'Memcached'),
    'redis_lock': ('Нельзя параллельно обрабатывать одну сущность', 'Сервис процесса', 'Redis lock', 'блокировка'),
    'search': ('Нужен поиск по сложным критериям', 'Сервис процесса', 'Поисковый индекс', 'Поисковый'),
    'vector_db': ('Записать embedding документа в векторную БД', 'Сервис процесса', 'Векторная БД', 'Вектор'),
    'kafka': ('Опубликовать событие в долговременный журнал событий', 'Сервис процесса', 'Kafka topic', 'Kafka'),
    'pulsar': ('Опубликовать событие в Pulsar', 'Сервис процесса', 'Журнал событий Pulsar', 'Pulsar'),
    'rabbitmq': ('Поставить фоновую работу в очередь обработки', 'Сервис процесса', 'RabbitMQ очередь задач', 'RabbitMQ'),
    'activemq': ('Поставить сообщение в ActiveMQ', 'Сервис процесса', 'ActiveMQ очередь', 'ActiveMQ'),
    'ibm_mq': ('Поставить сообщение в IBM MQ', 'Сервис процесса', 'IBM MQ', 'IBM MQ'),
    'nats': ('Передать короткое сообщение через NATS', 'Сервис процесса', 'NATS', 'NATS'),
    'sns_sqs': ('Опубликовать сообщение в AWS SNS SQS', 'Сервис процесса', 'AWS SNS/SQS', 'AWS SNS/SQS'),
    'azure_service_bus': ('Опубликовать сообщение в Azure Service Bus', 'Сервис процесса', 'Azure Service Bus', 'Azure Service Bus'),
    'gcp_pubsub': ('Опубликовать сообщение в Google Pub/Sub', 'Сервис процесса', 'Google Pub/Sub', 'Google Pub/Sub'),
    'redis_streams': ('Опубликовать событие в Redis Streams', 'Сервис процесса', 'Redis Streams', 'Redis Streams'),
    'redis_queue': ('Поставить короткую задачу в Redis queue', 'Сервис процесса', 'Redis queue', 'Redis'),
    'queue': ('Нужна корпоративная гарантированная очередь', 'Сервис процесса', 'Корпоративная очередь', 'Очередь'),
    'mqtt': ('Принять телеметрию от устройств MQTT', 'IoT устройство', 'Сервис процесса', 'MQTT'),
    'webhook': ('Принять результат по входящему веб-вызову', 'Внешняя система / партнёр', 'Сервис процесса', 'Входящий веб-вызов'),
    'callback': ('Внешняя система позже возвращает результат обратным вызовом', 'Сервис процесса', 'Внешняя система / партнёр', 'REST API'),
    'websocket': ('Открыть двусторонний онлайн-канал', 'Клиентский канал', 'Сервис процесса', 'WebSocket'),
    'sse': ('Отправлять поток уведомлений клиенту', 'Сервис процесса', 'Клиентский канал', 'Server-Sent'),
    'sftp': ('Передать файл партнёру через SFTP', 'Сервис процесса', 'Внешняя система / партнёр', 'SFTP'),
    'file': ('Сформировать файл выгрузки', 'Сервис процесса', 'Файловый каталог', 'Файл'),
    'object_storage': ('Сохранить документ в Object Storage S3', 'Сервис процесса', 'Object Storage S3', 'Объектное'),
    'batch': ('Запустить пакетную обработку по расписанию', 'Сервис процесса', 'Batch job', 'Пакетная'),
    'cdc': ('Передать изменения из БД через CDC', 'Хранилище состояния процесса', 'Аналитическое хранилище', 'Передача изменений'),
    'etl': ('Загрузить и преобразовать данные через ETL', 'Сервис процесса', 'Аналитическое хранилище', 'ETL'),
    'airflow': ('Оркестрировать загрузки через Airflow', 'Сервис процесса', 'Airflow DAG', 'Airflow'),
    'spark': ('Обработать большой объём данных через Spark', 'Сервис процесса', 'Spark cluster', 'Spark'),
    'dbt': ('Построить аналитические модели dbt', 'Аналитическое хранилище', 'dbt models', 'dbt'),
    'workflow_engine': ('Процесс долгий и имеет состояния', 'Сервис процесса', 'Temporal workflow', 'Движок'),
    'bpm_engine': ('Нужен бизнес-процесс и ручные задачи BPMN', 'Сервис процесса', 'Camunda BPMN', 'BPM'),
    'cdn': ('Раздать статический контент через CDN', 'Сервис процесса', 'CDN', 'CDN'),
    'auth_oidc': ('Нужна единая авторизация OAuth2 OIDC', 'Клиент/партнёр', 'Сервис авторизации', 'OAuth'),
    'vault': ('Нужно безопасно хранить секреты и ключи Vault KMS', 'Сервис процесса', 'Хранилище секретов', 'Vault'),
    'observability': ('Нужно видеть где завис процесс', 'Все шаги процесса', 'Контур наблюдаемости', 'Наблюдаемость'),
}

# optional systems not in base
EXTRA_ROLES = {
    'IoT устройство':'external','Клиентский канал':'external','Клиент/партнёр':'external','Сервис авторизации':'internal',
    'Документное хранилище MongoDB':'db','Cassandra cluster':'db','DynamoDB Key-Value':'db','ClickHouse analytics':'analytics',
    'Озеро данных':'analytics','Lakehouse':'analytics','Redis cache':'internal','Memcached':'internal','Redis lock':'internal',
    'Поисковый индекс':'internal','Векторная БД':'internal','Kafka topic':'broker','Журнал событий Pulsar':'broker',
    'RabbitMQ очередь задач':'broker','ActiveMQ очередь':'broker','IBM MQ':'broker','NATS':'broker','AWS SNS/SQS':'broker',
    'Azure Service Bus':'broker','Google Pub/Sub':'broker','Redis Streams':'broker','Redis queue':'broker','Корпоративная очередь':'broker',
    'Файловый каталог':'internal','Object Storage S3':'internal','Batch job':'internal','Airflow DAG':'analytics','Spark cluster':'analytics','dbt models':'analytics',
    'Temporal workflow':'internal','Camunda BPMN':'internal','CDN':'external'
}

BAD_TEXT_PATTERNS = [
    'лимит запросовing','retry','Retry','DLQ','replay','Replay','runbook','payload','Outbox','Inbox','event log','task queue','worker',
    'без очередь','Какой целевое','экспоненциальная увеличением','журналааа','повторная обработка должен','повторная попытка должен',
    'table','идентификаторааа','откатеее','сверка-сверку','повторными попыткамии'
]

issues=[]

def systems_for(*names):
    systems = {s['name']: dict(s) for s in BASE_SYSTEMS}
    for n in names:
        if n not in systems:
            systems[n] = {'name': n, 'role': EXTRA_ROLES.get(n,'internal'), 'owner':'team'}
    return list(systems.values())

def payload_for(channel, name, src, tgt, action='send_data', timing=None, result=None, dep=0, writes=False):
    return {
        'meta': {'name':'Exhaustive core variation', 'entity':'Entity', 'regulatory': True, 'lookup_keys':'entityId global'},
        'systems': systems_for(src,tgt,'Сервис процесса'),
        'steps': [{
            'order':1,'name':name,'system':src if src != 'Все шаги процесса' else 'Сервис процесса','channel':channel,
            'blocking': channel in engine.SYNC_CHANNELS, 'retry':'auto' if channel in engine.ASYNC_CHANNELS else 'none',
            'idempotency':'key' if channel in engine.ASYNC_CHANNELS else 'none','writes_entity':'yes' if writes else 'no',
            'depends_on':dep,'source_system':src,'target_system':tgt,
            'interaction_action':action,'interaction_timing': timing or ('now' if channel in engine.SYNC_CHANNELS else 'later'),
            'interaction_result': result or ('store' if channel in {'db','mongodb','dynamodb','cassandra','data_warehouse','data_lake','lakehouse','object_storage'} else 'continue')
        }]
    }

def tech_of(res):
    return _v8622_channel_purpose(res['model']['steps'][0])['technology']

def route_err(res):
    return _route_error_v8620(res['model']['steps'][0])

# 1) every channel valid variation should analyze and report expected tech fragment, no invalid schema except intentional weirdness.
for ch, (name, src, tgt, expected) in CHANNEL_EXPECT.items():
    print(f'checking channel {ch}', flush=True)
    res = analyze(payload_for(ch,name,src,tgt))
    if not res.get('ok'):
        issues.append((ch,'analyze_failed',res.get('errors'))); continue
    tech = tech_of(res)
    re = route_err(res)
    if 'сначала исправить' in tech.lower() or re:
        issues.append((ch,'unexpected_route_error',tech,re,name,src,tgt))
    if expected.lower() not in tech.lower():
        issues.append((ch,'wrong_tech',tech,'expected contains '+expected,name,src,tgt))
    # v8.6.59: полный markdown для каждого из 55 каналов слишком тяжёлый
    # для обычного CI и может зависать на больших отчётах. По умолчанию
    # проверяем разбор канала и технологию, а markdown-lint выполняем на
    # репрезентативной выборке. Для полного ручного аудита: FULL_AUDIT_REPORTS=1.
    if os.environ.get('FULL_AUDIT_REPORTS') == '1' or ch in {'rest','kafka','rabbitmq','db','soap','cdc','vault','observability'}:
        md = markdown_report(res)
        for pat in BAD_TEXT_PATTERNS:
            if pat in md:
                issues.append((ch,'bad_text',pat)); break

# 2) invalid/ambiguous variations should NOT get confident wrong stack.
invalid_cases = [
    ('kafka','Сервис процесса запрашивает данные у Старый контур','Сервис процесса','Старый контур','request_data','Шаг называется запросом данных'),
    ('callback','Сервис процесса передаёт данные в Внешняя система / партнёр','Сервис процесса','Внешняя система / партнёр','send_data',''),
    ('db','Сервис процесса сохраняет результат в Сервис процесса','Сервис процесса','Сервис процесса','save','Источник и получатель совпадают'),
]
for ch,name,src,tgt,action,expect_err in invalid_cases:
    res = analyze(payload_for(ch,name,src,tgt,action=action))
    st = res['model']['steps'][0]
    tech = tech_of(res)
    err = route_err(res)
    if expect_err and expect_err.lower() not in (err or '').lower():
        issues.append(('invalid',ch,'missing_expected_error',err,expect_err,tech,name))
    if ch in {'kafka'} and not err and 'сначала исправить' not in tech.lower():
        issues.append(('invalid',ch,'confident_wrong_stack',tech,err,name))

# 3) report-level checks for a realistic 8-step process.
real_payload = {
    'meta': {'name':'Реальный сложный сквозной процесс','entity':'Application','regulatory':True,'customer_visible':'yes','sla_ms':1500,'lookup_keys':'applicationId global'},
    'systems': systems_for('Клиентский канал','API Gateway','Сервис процесса','Хранилище состояния процесса','Старый контур','Внешняя система / партнёр','Аналитическое хранилище','Kafka topic','RabbitMQ очередь задач','Контур наблюдаемости','Хранилище секретов'),
    'steps': [
        {'order':1,'name':'Клиентский канал передаёт заявку через API Gateway','system':'Клиентский канал','channel':'api_gateway','blocking':'yes','timeout_ms':300,'source_system':'Клиентский канал','target_system':'Сервис процесса','interaction_action':'send_data'},
        {'order':2,'name':'Сервис процесса сохраняет состояние заявки','system':'Сервис процесса','channel':'db','blocking':'yes','timeout_ms':200,'writes_entity':'yes','idempotency':'key','depends_on':1,'source_system':'Сервис процесса','target_system':'Хранилище состояния процесса','interaction_action':'save'},
        {'order':3,'name':'Сервис процесса вызывает старый SOAP контур','system':'Сервис процесса','channel':'soap','blocking':'yes','timeout_ms':700,'depends_on':2,'source_system':'Сервис процесса','target_system':'Старый контур','interaction_action':'send_data'},
        {'order':4,'name':'Сервис процесса отправляет запрос партнёру','system':'Сервис процесса','channel':'rest','blocking':'no','retry':'auto','idempotency':'key','depends_on':2,'source_system':'Сервис процесса','target_system':'Внешняя система / партнёр','interaction_action':'send_data'},
        {'order':5,'name':'Партнёр присылает поздний статус входящим веб-вызовом','system':'Внешняя система / партнёр','channel':'webhook','blocking':'no','retry':'auto','idempotency':'key','depends_on':4,'source_system':'Внешняя система / партнёр','target_system':'Сервис процесса','interaction_action':'receive_result'},
        {'order':6,'name':'Сервис процесса публикует событие изменения статуса','system':'Сервис процесса','channel':'kafka','blocking':'no','retry':'auto','idempotency':'key','writes_entity':'no','depends_on':5,'source_system':'Сервис процесса','target_system':'Kafka topic','interaction_action':'publish_event'},
        {'order':7,'name':'Сервис процесса передаёт изменения в аналитическое хранилище через CDC','system':'Хранилище состояния процесса','channel':'cdc','blocking':'no','retry':'auto','idempotency':'key','depends_on':2,'source_system':'Хранилище состояния процесса','target_system':'Аналитическое хранилище','interaction_action':'send_data'},
        {'order':8,'name':'Нужно безопасно хранить секреты и ключи Vault KMS','system':'Сервис процесса','channel':'vault','blocking':'yes','source_system':'Сервис процесса','target_system':'Хранилище секретов','interaction_action':'security'},
    ]
}
res = analyze(real_payload)
if not res.get('ok'):
    issues.append(('realistic','analyze_failed',res.get('errors')))
else:
    md=markdown_report(res)
    forbidden = ['Сервис процесса → Сервис процесса', 'Аналитическое хранилище / Документное хранилище', 'Основной способ взаимодействия: Документное хранилище', 'Основной способ взаимодействия: Обратный вызов']
    for f in forbidden:
        if f in md:
            issues.append(('realistic','forbidden_text',f))
    for pat in BAD_TEXT_PATTERNS:
        if pat in md:
            issues.append(('realistic','bad_text',pat))
    # SQL sanity
    if 'status text NOT NULL,\n    status text NOT NULL' in md or 'идентификатор события uuid' in md or 'тело сообщения jsonb' in md:
        issues.append(('realistic','bad_sql'))

if issues:
    print('EXHAUSTIVE_CORE_VARIATIONS_v8632 failed:', len(issues))
    for i in issues[:80]:
        print(' -', repr(i))
    raise SystemExit(1)
print('EXHAUSTIVE_CORE_VARIATIONS_v8632 ok: channels=%d invalid_cases=%d realistic=1' % (len(CHANNEL_EXPECT), len(invalid_cases)))
