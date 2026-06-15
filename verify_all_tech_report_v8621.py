#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Глубокая проверка отчёта на synthetic all-stack/all-chain case."""
import json, re, subprocess, sys, pathlib
import engine
from report import markdown_report

# Переиспользуем payload, который создаётся mega_case_check_v8620.py, чтобы проверка была стабильной.
script = pathlib.Path(__file__).with_name('mega_case_check_v8620.py')
if not pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json').exists():
    subprocess.run([sys.executable, str(script)], check=True)
payload = json.loads(pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json').read_text(encoding='utf-8'))
# Дополнительные edge-связи сверх 55 каналов: исходящий REST к партнёру, маскирование и audit journal.
for sys_name, role in [('Слой защиты и маскирования','security'), ('Audit journal','audit')]:
    if not any(x.get('name') == sys_name for x in payload.get('systems', [])):
        payload.setdefault('systems', []).append({'name': sys_name, 'role': role, 'criticality': 'high', 'stability': 'stable'})
base_order = max(int(x.get('order', 0)) for x in payload.get('steps', []))
payload['steps'].extend([
    {'order': base_order + 1, 'name': 'Отправить REST-запрос внешнему партнёру', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Внешний партнёр', 'channel': 'rest', 'blocking': False, 'timeout_ms': 800, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order, 'data_in': 'operationId, externalRequestId', 'data_out': 'запрос партнёру с внешним requestId', 'compensation': 'проверка неизвестного результата'},
    {'order': base_order + 2, 'name': 'Классифицировать и маскировать чувствительные поля', 'system': 'Слой защиты и маскирования', 'source_system': 'Сервис процесса', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': False, 'timeout_ms': 0, 'retry': 'none', 'idempotency': 'none', 'writes_entity': False, 'depends_on': base_order + 1, 'data_in': 'персональные данные', 'data_out': 'маскированное тело сообщения', 'compensation': ''},
    {'order': base_order + 3, 'name': 'Записать неизменяемый audit journal', 'system': 'Audit journal', 'source_system': 'Сервис процесса', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': True, 'timeout_ms': 200, 'retry': 'none', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order + 2, 'data_in': 'correlationId, actor, action, reason', 'data_out': 'append-only audit entry', 'compensation': ''},
])
res = engine.analyze(payload)
assert res.get('ok') is True, res
md = markdown_report(res)
out = pathlib.Path('/mnt/data/ALL_TECH_REPORT_v8_6_21.md')
out.write_text(md, encoding='utf-8')

errors = []
def must(cond, msg):
    if not cond:
        errors.append(msg)

def contains(text):
    return text in md

# 1. Старые критичные регрессии.
must('Регуляторика: да' in md, 'boolean meta regulatory/customer_visible must be preserved')
must('Прочитать корпоративный справочник через OData». Основной способ взаимодействия: OData' in md, 'OData must not be downgraded to REST')
must('Записать embedding документа в векторную БД». Основной способ взаимодействия: Векторное хранилище' in md, 'Vector DB must not be downgraded to File')
must('Сохранить запись формата «ключ-значение» в DynamoDB». Основной способ взаимодействия: Хранилище ключ-значение' in md, 'DynamoDB must not be classified as Vault/KMS')
must('### Контроль 21. Сформировать файл выгрузки' not in md, 'File exchange must not be classified as observability because of word "каталог"')
must('Схема не содержит очевидных противоречий' in md, 'well-formed all-tech payload must not produce false schema issues')

# 2. Сквозные контроли отделены от бизнес-цепочки, но ссылки на них читаемы.
for n, title in [(4, 'OAuth2/OIDC'), (11, 'CDN'), (33, 'метрики'), (45, 'Service Mesh'), (51, 'Vault/KMS')]:
    must(f'### Контроль {n}.' in md, f'cross-control {n} must be in controls section')
    must(f'сквозной контроль {n}' in md or n == 4, f'dependencies to hidden control {n} should be labeled as cross-control when referenced')

# В основной цепочке не должно быть ссылок "после: шаг X" на шаг, который вынесен в контроль.
visible = {int(n) for n, _ in re.findall(r'^### Шаг (\d+)\. (.+)$', md, flags=re.M)}
hidden_refs = sorted(set(int(x) for x in re.findall(r'Выполняется после: шаг (\d+) ', md) if int(x) not in visible))
must(not hidden_refs, f'main flow contains hidden step dependencies: {hidden_refs}')

# 3. Технологии не должны подменяться соседними/служебными понятиями.
for bad in [
    'Основной способ взаимодействия: Аналитическое хранилище',
    'Основной способ взаимодействия: Data Warehouse',
    'Основной способ взаимодействия: Озеро данных',
    'лимит запросовing', 'лимит запросовs', 'table', "{'tables'", 'Payload',
    'повторная обработка должен', 'повторная попытка должен', 'каждый повторная попытка',
]:
    must(bad not in md, f'bad phrase/regression found: {bad}')

# 4. Все важные семейства стеков представлены в отчёте.
for expected in [
    'ActiveMQ/Artemis', 'Airflow', 'API Gateway', 'Azure Service Bus', 'Пакетная обработка',
    'BPM/BPMN-движок', 'Входящий веб-вызов', 'Cassandra/ScyllaDB', 'Передача изменений из базы данных',
    'Колоночная аналитическая база данных', 'ETL/ELT-загрузка', 'Основная база данных',
    'Шардирование базы данных', 'dbt', 'Хранилище ключ-значение', 'Интеграционная шина ESB',
    'Файловая передача', 'Google Pub/Sub', 'GraphQL', 'gRPC', 'IBM MQ', 'Kafka', 'Memcached',
    'MongoDB', 'MQTT', 'NATS', 'Объектное хранилище', 'OData', 'Pulsar', 'RabbitMQ',
    'Реплика БД', 'Redis как кэш', 'Redis как распределённая блокировка', 'Redis как короткая очередь задач',
    'Redis Streams', 'REST API / HTTP-запрос к внешнему партнёру', 'SFTP', 'SOAP', 'Spark',
    'Server-Sent Events', 'Векторное хранилище', 'WebSocket', 'Движок длительного процесса',
    'неизменяемый журнал аудита', 'защита и маскирование данных', 'Vault/KMS', 'OAuth2/OIDC',
    'Наблюдаемость', 'CDN', 'Service Mesh'
]:
    must(expected in md, f'expected technology missing or renamed badly: {expected}')

if errors:
    print('ALL_TECH_REPORT_v8621 FAILED')
    for e in errors:
        print('-', e)
    print('report:', out)
    sys.exit(1)
print(f'ALL_TECH_REPORT_v8621 ok: steps={len(res['model']['steps'])} visible_steps={len(visible)} findings={len(res.get("findings", []))} report={out}')
