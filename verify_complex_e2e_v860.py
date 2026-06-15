#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
from engine import analyze
from report import markdown_report

KNOWN = set(['rest','graphql','odata','grpc','soap','api_gateway','service_mesh','esb','db','read_replica','db_sharding','mongodb','cassandra','dynamodb','clickhouse','data_warehouse','data_lake','lakehouse','redis_cache','memcached','redis_lock','search','vector_db','kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt','webhook','callback','websocket','sse','sftp','file','object_storage','batch','cdc','etl','airflow','spark','dbt','workflow_engine','bpm_engine','cdn','auth_oidc','vault','observability'])
SYNC = {'rest','graphql','odata','grpc','soap','api_gateway','service_mesh','esb','db','read_replica','db_sharding','mongodb','cassandra','dynamodb','clickhouse','data_warehouse','data_lake','lakehouse','redis_cache','memcached','redis_lock','search','vector_db','cdn','auth_oidc','vault','observability'}

def systems(names):
    out=[]
    for name, role in names:
        out.append({'name':name,'role':role,'criticality':'critical' if role in {'db','broker','security','workflow'} else 'high','stability':'stable' if role!='external' else 'limited'})
    return out

def step(i, name, src, sys, tgt, ch, dep='', writes=False, reason=''):
    return {
        'order': i, 'name': name, 'source_system': src, 'system': sys, 'target_system': tgt,
        'channel': ch, 'blocking': 'yes' if ch in SYNC else 'no', 'timeout_ms': '800' if ch in SYNC else '',
        'retry': 'auto', 'idempotency': 'key', 'writes_entity': 'yes' if writes else 'no', 'depends_on': dep,
        'compensation': 'повторная попытка с лимитом, дедупликация, журнал ошибок, ручной разбор',
        'failure_policy': 'очередь ошибок / ручной разбор', 'component_type': 'action',
        'data_in': 'businessId, requestId, correlationId, statusVersion',
        'data_out': 'eventId, correlationId, status, statusVersion', 'stack_reason': reason
    }

def payload(name, entity, goal, systems_list, steps, extra=None):
    meta = {
        'name': name, 'entity': entity, 'goal': goal,
        'lookup_keys': 'businessId + eventId + correlationId; partition key по businessId',
        'statuses': 'CREATED, VALIDATING, WAITING_EXTERNAL, SAVED, SENT, PROCESSING, COMPLETED, FAILED, NEEDS_MANUAL_REVIEW',
        'fields': 'businessId:uuid|required|indexed, eventId:uuid|unique, correlationId:uuid|indexed, status:string|required, statusVersion:int|required',
        'customer_visible': 'mixed', 'money': 'direct', 'regulatory': 'yes', 'ordering': 'per_entity',
        'read_freq': 'high', 'load_rps': '1500', 'peak_factor': '4', 'replacing_legacy':'yes'
    }
    if extra: meta.update(extra)
    return {'meta': meta, 'systems': systems(systems_list), 'steps': steps}

def case_bank_onboarding():
    sys=[('Клиентское приложение','external'),('CDN','cdn'),('API Gateway','gateway'),('Сервис авторизации','security'),('Service Mesh','mesh'),('Сервис анкеты','internal'),('Профильный сервис','internal'),('Legacy АБС','legacy'),('БД процесса','db'),('Реплика чтения','db'),('Redis кэш','cache'),('Redis блокировка','cache'),('Поисковый индекс','search'),('Kafka','broker'),('RabbitMQ','broker'),('Объектное хранилище','storage'),('Webhook партнёра','external'),('DWH','analytics'),('Observability','ops'),('Vault/KMS','security')]
    st=[
        step(1,'Клиент открывает статические ресурсы анкеты','CDN','CDN','Клиентское приложение','cdn'),
        step(2,'Клиент входит через единый контур авторизации','Клиентское приложение','Сервис авторизации','API Gateway','auth_oidc','1'),
        step(3,'Внешний вход проверяет токен и лимиты','Клиентское приложение','API Gateway','Сервис анкеты','api_gateway','2'),
        step(4,'Внутренний вызов проходит через управляемый сервисный контур','API Gateway','Service Mesh','Сервис анкеты','service_mesh','3'),
        step(5,'Сервис анкеты быстро получает профиль клиента','Сервис анкеты','Профильный сервис','Профильный сервис','grpc','4'),
        step(6,'Профиль часто читается из кэша','Профильный сервис','Redis кэш','Сервис анкеты','redis_cache','5'),
        step(7,'Одну анкету нельзя обрабатывать параллельно','Сервис анкеты','Redis блокировка','Сервис анкеты','redis_lock','6'),
        step(8,'Сервис сверяет клиента со старой АБС по старому контракту','Сервис анкеты','Сервис анкеты','Legacy АБС','soap','7'),
        step(9,'Сервис сохраняет состояние анкеты','Сервис анкеты','Сервис анкеты','БД процесса','db','8',True),
        step(10,'Чтение списка анкет разгружается на реплику','БД процесса','Реплика чтения','Сервис анкеты','read_replica','9'),
        step(11,'Поиск клиентов идёт через поисковый индекс','БД процесса','Поисковый индекс','Сервис анкеты','search','9'),
        step(12,'Скан паспорта хранится как объект, в событиях передаётся ссылка','Сервис анкеты','Сервис анкеты','Объектное хранилище','object_storage','9'),
        step(13,'Сервис публикует событие о создании анкеты нескольким потребителям','Сервис анкеты','Сервис анкеты','Kafka','kafka','9'),
        step(14,'OCR получает фоновую задачу на обработку документа','Сервис анкеты','Сервис анкеты','RabbitMQ','rabbitmq','12'),
        step(15,'Партнёр позже присылает статус проверки','Webhook партнёра','API Gateway','Сервис анкеты','webhook','13'),
        step(16,'Изменения состояния передаются в аналитику','БД процесса','DWH','DWH','cdc','9'),
        step(17,'Регламентная сверка DWH запускается пачкой по расписанию','DWH','DWH','DWH','batch','16'),
        step(18,'Аналитическое хранилище хранит согласованные витрины','DWH','DWH','DWH','data_warehouse','17'),
        step(19,'Секреты внешних интеграций берутся из защищённого хранилища','Сервис анкеты','Vault/KMS','Legacy АБС','vault','8'),
        step(20,'Сквозные метрики и трассировки показывают, где зависла анкета','Сервис анкеты','Observability','Observability','observability','15')]
    return payload('Сложный кейс 1: цифровое открытие банковского продукта', 'ClientApplication', 'Клиент открывает продукт через приложение, процесс должен проверять старый контур, документы, статус партнёра и аналитику.', sys, st)

def case_iot():
    sys=[('Устройства','external'),('MQTT broker','broker'),('Pulsar','broker'),('Redis Streams','broker'),('Cassandra','db'),('ClickHouse','analytics'),('Data Lake','analytics'),('Spark','analytics'),('Airflow','analytics'),('dbt','analytics'),('Сервис тревог','internal'),('WebSocket канал','external'),('SSE канал','external'),('NATS','broker'),('Observability','ops')]
    st=[step(1,'Датчики отправляют телеметрию лёгким протоколом','Устройства','MQTT broker','MQTT broker','mqtt'),
        step(2,'Сырые события складываются в масштабный журнал событий','MQTT broker','Pulsar','Pulsar','pulsar','1'),
        step(3,'Короткий поток последних измерений идёт во внутренние обработчики','Pulsar','Redis Streams','Сервис тревог','redis_streams','2'),
        step(4,'Лёгкая внутренняя рассылка уведомляет сервисы о тревоге','Сервис тревог','NATS','Сервис тревог','nats','3'),
        step(5,'Огромные записи по устройству хранятся по ключу устройства','Pulsar','Cassandra','Cassandra','cassandra','2',True),
        step(6,'Аналитические агрегаты пишутся в колоночную БД','Pulsar','ClickHouse','ClickHouse','clickhouse','2'),
        step(7,'Сырые файлы телеметрии складываются в озеро данных','Pulsar','Data Lake','Data Lake','data_lake','2'),
        step(8,'Большая распределённая обработка пересчитывает историю','Data Lake','Spark','ClickHouse','spark','7'),
        step(9,'Зависимые загрузки управляются расписанием','Spark','Airflow','dbt','airflow','8'),
        step(10,'Аналитические модели собираются управляемо','ClickHouse','dbt','ClickHouse','dbt','9'),
        step(11,'Оператор получает онлайн-тревоги в двустороннем канале','Сервис тревог','WebSocket канал','Устройства','websocket','4'),
        step(12,'Панель мониторинга получает поток уведомлений','Сервис тревог','SSE канал','SSE канал','sse','4'),
        step(13,'Наблюдаемость контролирует лаги и потерянные сообщения','Pulsar','Observability','Observability','observability','2')]
    return payload('Сложный кейс 2: IoT-телеметрия и онлайн-тревоги', 'DeviceTelemetry', 'Датчики присылают события, нужны быстрые тревоги, хранение истории, аналитика и онлайн-каналы.', sys, st, {'money':'none','regulatory':'no'})

def case_retail_order():
    sys=[('Web/Mobile','external'),('API Gateway','gateway'),('GraphQL BFF','internal'),('Каталог','internal'),('OData ERP','legacy'),('БД заказов','db'),('Шардированное хранилище','db'),('DynamoDB','db'),('MongoDB','db'),('Memcached','cache'),('Redis queue','broker'),('Generic queue','broker'),('Kafka','broker'),('SFTP партнёра','external'),('Файловый шлюз','storage'),('Object Storage','storage'),('CDN','cdn'),('Векторный поиск','search'),('Search index','search'),('Azure Service Bus','broker')]
    st=[step(1,'Клиент получает каталог через гибкий API','Web/Mobile','GraphQL BFF','Каталог','graphql'),
        step(2,'Статика и изображения товаров отдаются быстро','CDN','CDN','Web/Mobile','cdn','1'),
        step(3,'Поиск товара идёт по поисковому индексу','GraphQL BFF','Search index','Web/Mobile','search','1'),
        step(4,'Семантический поиск похожих товаров использует векторы','GraphQL BFF','Векторный поиск','Web/Mobile','vector_db','1'),
        step(5,'Каталог читает редко меняющиеся данные из простого временного кэша','Каталог','Memcached','GraphQL BFF','memcached','1'),
        step(6,'ERP отдаёт корпоративные сущности через OData','Каталог','OData ERP','Каталог','odata','1'),
        step(7,'Заказ сохраняется в основную БД','GraphQL BFF','GraphQL BFF','БД заказов','db','1',True),
        step(8,'Данные заказов разделяются по ключу клиента','БД заказов','Шардированное хранилище','Шардированное хранилище','db_sharding','7',True),
        step(9,'Идемпотентный быстрый доступ к корзине идёт по ключу','GraphQL BFF','DynamoDB','GraphQL BFF','dynamodb','7'),
        step(10,'Гибкий документ состава заказа хранится как документ','GraphQL BFF','MongoDB','GraphQL BFF','mongodb','7'),
        step(11,'Короткая внутренняя задача пересчитывает рекомендации','GraphQL BFF','Redis queue','Каталог','redis_queue','7'),
        step(12,'Если брокер ещё не выбран, задача уходит в нейтральную очередь','GraphQL BFF','Generic queue','Каталог','queue','7'),
        step(13,'Событие о заказе публикуется многим потребителям','GraphQL BFF','Kafka','Kafka','kafka','7'),
        step(14,'В корпоративном Microsoft-контуре заказ передаётся в очередь','GraphQL BFF','Azure Service Bus','OData ERP','azure_service_bus','13'),
        step(15,'Партнёр получает защищённый файл по SFTP','Файловый шлюз','SFTP партнёра','SFTP партнёра','sftp','13'),
        step(16,'Одиночный файл накладной передаётся отдельным файлом','Файловый шлюз','Файловый шлюз','SFTP партнёра','file','13'),
        step(17,'Большие вложения заказа хранятся отдельно','GraphQL BFF','Object Storage','Object Storage','object_storage','7')]
    return payload('Сложный кейс 3: заказ в e-commerce с каталогом, ERP и партнёрами', 'Order', 'Клиент создаёт заказ, нужны каталог, поиск, ERP, партнёрский файл, события и масштабирование хранения.', sys, st)

def case_enterprise_migration():
    sys=[('Старый фронт','external'),('ESB','esb'),('ActiveMQ','broker'),('IBM MQ','broker'),('Mainframe','legacy'),('Workflow engine','workflow'),('BPM engine','workflow'),('БД процесса','db'),('CDC','analytics'),('ETL','analytics'),('Lakehouse','analytics'),('Data Warehouse','analytics'),('Spark','analytics'),('Airflow','analytics'),('dbt','analytics'),('Google Pub/Sub','broker'),('AWS SNS/SQS','broker'),('API Gateway','gateway')]
    st=[step(1,'Старый фронт входит через единый внешний вход','Старый фронт','API Gateway','ESB','api_gateway'),
        step(2,'Шина маршрутизирует запрос в несколько старых систем','API Gateway','ESB','Mainframe','esb','1'),
        step(3,'Корпоративная JMS-очередь передаёт задачу в Java-контур','ESB','ActiveMQ','Workflow engine','activemq','2'),
        step(4,'Гарантированная очередь передаёт команду в мейнфрейм','ESB','IBM MQ','Mainframe','ibm_mq','2'),
        step(5,'Длительный процесс хранит состояние и таймеры','ActiveMQ','Workflow engine','БД процесса','workflow_engine','3',True),
        step(6,'Ручные согласования ведутся в BPMN-процессе','Workflow engine','BPM engine','БД процесса','bpm_engine','5',True),
        step(7,'Изменения операционной БД передаются из CDC','БД процесса','CDC','ETL','cdc','6'),
        step(8,'Загрузка и преобразование данных готовит слой аналитики','CDC','ETL','Lakehouse','etl','7'),
        step(9,'Озеро с табличной аналитикой хранит историю','ETL','Lakehouse','Lakehouse','lakehouse','8'),
        step(10,'Распределённая обработка пересчитывает большие периоды','Lakehouse','Spark','Data Warehouse','spark','9'),
        step(11,'Оркестратор управляет зависимыми загрузками','Spark','Airflow','dbt','airflow','10'),
        step(12,'Аналитические модели собирают витрины','Data Warehouse','dbt','Data Warehouse','dbt','11'),
        step(13,'Событие уходит в облачную очередь AWS','Workflow engine','AWS SNS/SQS','AWS SNS/SQS','sns_sqs','6'),
        step(14,'Событие уходит в облачный pub/sub Google','Workflow engine','Google Pub/Sub','Google Pub/Sub','gcp_pubsub','6')]
    return payload('Сложный кейс 4: миграция enterprise-процесса со старого контура', 'EnterpriseCase', 'Есть старый контур, шина, очереди, длительный процесс, ручные согласования и аналитическая миграция.', sys, st)

def case_insurance_claim():
    sys=[('Мобильное приложение','external'),('API Gateway','gateway'),('OAuth/OIDC','security'),('Сервис страховой заявки','internal'),('Workflow engine','workflow'),('Legacy core','legacy'),('REST антифрод','external'),('RabbitMQ','broker'),('Object Storage','storage'),('Callback оплаты','external'),('Webhook доставки','external'),('Kafka','broker'),('БД процесса','db'),('Redis cache','cache'),('Redis lock','cache'),('Search index','search'),('SFTP медпартнёра','external'),('DWH','analytics'),('Vault/KMS','security'),('Observability','ops')]
    st=[step(1,'Клиент отправляет заявку через внешний вход','Мобильное приложение','API Gateway','Сервис страховой заявки','api_gateway'),
        step(2,'Пользователь подтверждает доступ через единую авторизацию','Мобильное приложение','OAuth/OIDC','API Gateway','auth_oidc','1'),
        step(3,'Процесс выплаты долгий и хранит состояния','Сервис страховой заявки','Workflow engine','БД процесса','workflow_engine','2',True),
        step(4,'Сервис получает полис из старого core по WSDL','Workflow engine','Сервис страховой заявки','Legacy core','soap','3'),
        step(5,'Документы заявки сохраняются отдельно от БД','Сервис страховой заявки','Сервис страховой заявки','Object Storage','object_storage','3'),
        step(6,'OCR получает фоновую задачу','Сервис страховой заявки','RabbitMQ','Сервис страховой заявки','rabbitmq','5'),
        step(7,'Антифрод вызывается синхронно и возвращает решение','Сервис страховой заявки','Сервис страховой заявки','REST антифрод','rest','4'),
        step(8,'Нельзя одновременно менять одну выплату','Сервис страховой заявки','Redis lock','Сервис страховой заявки','redis_lock','7'),
        step(9,'Итоговый статус выплаты сохраняется','Сервис страховой заявки','Сервис страховой заявки','БД процесса','db','8',True),
        step(10,'Профиль выплаты часто читается из кэша','БД процесса','Redis cache','Сервис страховой заявки','redis_cache','9'),
        step(11,'Поиск заявок идёт по индексу','БД процесса','Search index','Сервис страховой заявки','search','9'),
        step(12,'Платёжный провайдер присылает поздний результат','Callback оплаты','API Gateway','Сервис страховой заявки','callback','9'),
        step(13,'Партнёр доставки сам присылает статус документа','Webhook доставки','API Gateway','Сервис страховой заявки','webhook','9'),
        step(14,'Медицинский партнёр получает защищённый файловый пакет','Сервис страховой заявки','SFTP медпартнёра','SFTP медпартнёра','sftp','9'),
        step(15,'События выплаты читают уведомления, аудит и аналитика','Сервис страховой заявки','Kafka','Kafka','kafka','9'),
        step(16,'Изменения передаются в аналитическое хранилище','БД процесса','DWH','DWH','cdc','9'),
        step(17,'Секреты партнёров и ключи подписи хранятся защищённо','Сервис страховой заявки','Vault/KMS','REST антифрод','vault','7'),
        step(18,'Наблюдаемость показывает зависшие выплаты и ошибки партнёров','Сервис страховой заявки','Observability','Observability','observability','12,13')]
    return payload('Сложный кейс 5: страховая выплата с партнёрами и документами', 'InsuranceClaim', 'Заявка на выплату проходит legacy, OCR, антифрод, оплату, документы, callback/webhook и аналитику.', sys, st)

def validate_payload(p):
    names={s['name'] for s in p['systems']}
    issues=[]
    orders={s['order'] for s in p['steps']}
    for st in p['steps']:
        if st['channel'] not in KNOWN: issues.append(f"unknown channel {st['channel']} step {st['order']}")
        for fld in ('source_system','system','target_system'):
            val=st.get(fld)
            if val and val not in names: issues.append(f"missing system {val} in step {st['order']}")
        deps=[int(x) for x in re.findall(r'\d+', str(st.get('depends_on','')))]
        for d in deps:
            if d==st['order']: issues.append(f"self dependency step {st['order']}")
            if d not in orders: issues.append(f"bad dependency {d} in step {st['order']}")
    return issues

def main():
    cases=[case_bank_onboarding(), case_iot(), case_retail_order(), case_enterprise_migration(), case_insurance_claim()]
    out=[]; overall=[]; covered=set()
    out.append('# Проверка сложных кейсов v8.6.0')
    out.append('')
    for p in cases:
        name=p['meta']['name']; issues=validate_payload(p); res=analyze(p); rep=markdown_report(res)
        chans={s['channel'] for s in p['steps']}; covered|=chans
        generic='Другой вариант не выбран' in rep or 'нет детального шаблона' in rep
        ok=res.get('ok') and not issues and not generic
        overall.append(ok)
        out.append(f'## {name}')
        out.append(f'- Шагов: {len(p["steps"])}')
        out.append(f'- Каналы/технологии: {", ".join(sorted(chans))}')
        out.append(f'- analyze.ok: {res.get("ok")}')
        out.append(f'- Ошибки ссылок цепочки: {len(issues)}')
        out.append(f'- Общие/пустые объяснения в отчёте: {"да" if generic else "нет"}')
        out.append(f'- Вердикт: {res.get("verdict",{}).get("color")} / {res.get("verdict",{}).get("score")}/10')
        findings=res.get('verdict',{}).get('counts',{})
        out.append(f'- Риски: critical={findings.get("critical",0)}, high={findings.get("high",0)}, medium={findings.get("medium",0)}')
        if issues:
            for i in issues: out.append(f'  - ISSUE: {i}')
        out.append('')
        slug=re.sub(r'[^a-zA-Z0-9а-яА-Я]+','_', name).strip('_')[:60]
        Path(f'COMPLEX_CASE_{slug}.md').write_text(rep, encoding='utf-8')
        Path(f'COMPLEX_CASE_{slug}.json').write_text(json.dumps(res,ensure_ascii=False,indent=2), encoding='utf-8')
    missing=KNOWN-covered
    out.append('## Итог')
    out.append(f'- Сложных кейсов проверено: {len(cases)}')
    out.append(f'- Проваленных кейсов: {overall.count(False)}')
    out.append(f'- Технологий покрыто в сложных кейсах: {len(covered)} из {len(KNOWN)}')
    out.append(f'- Не использовались в этих 5 кейсах, но покрыты матрицей: {", ".join(sorted(missing)) if missing else "нет"}')
    Path('COMPLEX_E2E_v8_6_0_REPORT.md').write_text('\n'.join(out), encoding='utf-8')
    print('\n'.join(out))
    return 0 if all(overall) else 1
if __name__=='__main__': raise SystemExit(main())
