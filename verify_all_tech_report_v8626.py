#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Финальная проверка all-tech отчёта v8.6.26: логика, разделы, сценарии, схемы и русский язык."""
import json
import pathlib
import subprocess
import sys
import re

import engine
from report import markdown_report

ROOT = pathlib.Path(__file__).resolve().parent
payload_file = pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json')
if not payload_file.exists():
    subprocess.run([sys.executable, str(ROOT / 'mega_case_check_v8620.py')], check=True)
payload = json.loads(payload_file.read_text(encoding='utf-8'))
for sys_name, role in [('Слой защиты и маскирования', 'security'), ('Audit journal', 'audit')]:
    if not any(x.get('name') == sys_name for x in payload.get('systems', [])):
        payload.setdefault('systems', []).append({'name': sys_name, 'role': role, 'criticality': 'high', 'stability': 'stable'})
base_order = max(int(x.get('order', 0)) for x in payload.get('steps', []))
if not any(x.get('name') == 'Отправить REST-запрос внешнему партнёру' for x in payload.get('steps', [])):
    payload['steps'].extend([
        {'order': base_order + 1, 'name': 'Отправить REST-запрос внешнему партнёру', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Внешний партнёр', 'channel': 'rest', 'blocking': False, 'timeout_ms': 800, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order, 'data_in': 'operationId, externalRequestId', 'data_out': 'запрос партнёру с внешним requestId', 'compensation': 'проверка неизвестного результата'},
        {'order': base_order + 2, 'name': 'Классифицировать и маскировать чувствительные поля', 'system': 'Слой защиты и маскирования', 'source_system': 'Сервис процесса', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': False, 'timeout_ms': 0, 'retry': 'none', 'idempotency': 'none', 'writes_entity': False, 'depends_on': base_order + 1, 'data_in': 'персональные данные', 'data_out': 'маскированное тело сообщения', 'compensation': ''},
        {'order': base_order + 3, 'name': 'Записать неизменяемый audit journal', 'system': 'Audit journal', 'source_system': 'Сервис процесса', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': True, 'timeout_ms': 200, 'retry': 'none', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order + 2, 'data_in': 'correlationId, actor, action, reason', 'data_out': 'append-only audit entry', 'compensation': ''},
    ])
res = engine.analyze(payload)
assert res.get('ok') is True, res
md = markdown_report(res)
out = ROOT / 'ALL_TECH_REPORT_v8_6_26_FINAL_AUDIT.md'
out.write_text(md, encoding='utf-8')
errors = []
def must(cond, msg):
    if not cond:
        errors.append(msg)

for section in [
    '## Короткий человеческий вывод', '## Что блокирует запуск', '## Рекомендуемый порядок действий',
    '## Проверка логики схемы', '## Почему выбраны технологии и способы взаимодействия',
    '## Сквозные контроли и служебные компоненты', '## Контрольные проверки готовности к промышленному запуску',
    '## Какие вводные нужно уточнить', '## Краткая сводка по стеку', '## Найденные риски и слабые места',
    '## Сценарная основа для дальнейшей разработки', '## Диаграммы процесса'
]:
    must(section in md, f'missing section: {section}')

# all-tech не должен притворяться линейным happy path.
must('карту множества интеграционных возможностей' in md, 'all-tech scenario warning missing')
must('### Основной сценарий' not in md, 'all-tech incorrectly contains one happy path')
must('Выполняется после:' not in md, 'all-tech step cards still imply strict linear execution')
must('Условный порядок отображения связей' in md, 'diagram heading must not claim one main sequence')

# Старые логические регрессии.
for bad in [
    'Основной способ взаимодействия: Аналитическое хранилище',
    'Основной способ взаимодействия: Data Warehouse',
    'Основной способ взаимодействия: Озеро данных',
    'Основной способ взаимодействия: Обратный вызов.\n**Где:** связь идёт от «Сервис процесса» к «Внешний партнёр»',
    'Классифицировать и маскировать чувствительные поля». Основной способ взаимодействия: REST API',
    'Записать неизменяемый audit journal». Основной способ взаимодействия: Основная база данных',
    'Сервис процесса → Сервис процесса → Внешний партнёр',
    'Сервис процесса → Сервис процесса →',
]:
    must(bad not in md, f'logic regression: {bad}')

# Технологии all-tech должны быть представлены и не подменены.
for expected in [
    'OData', 'Векторное хранилище', 'Хранилище ключ-значение', 'Входящий веб-вызов',
    'REST API / HTTP-запрос к внешнему партнёру', 'неизменяемый журнал аудита', 'защита и маскирование данных',
    'API Gateway', 'Kafka', 'RabbitMQ', 'Pulsar', 'Redis Streams', 'SFTP', 'SOAP', 'GraphQL', 'gRPC'
]:
    must(expected in md, f'expected term missing: {expected}')

# Остатки машинного языка, которые были найдены ручным чтением.
for bad in [
    'попыткамии', 'транзакционная таблица исходящих', 'outbox/inbox', 'строгой outbox', 'outbox-записей',
    'публикатор вычитывает outbox', 'проверка горячая партиция', 'сценариях доступа', 'неизменяемый модель',
    'documentation', 'repair/compaction', 'throughput', 'cross-shard', 'hot partition', 'namespace', 'standard-очереди',
    'лимит запросовing', 'лимит запросовs', 'table', "{'tables'", 'Payload', 'payload',
    'повторная обработка должен', 'повторная попытка должен', 'каждый повторная попытка', 'коммитьте позиция'
]:
    must(bad not in md, f'bad language leftover: {bad}')

must('```mermaid' in md and md.count('```mermaid') >= 3, 'expected mermaid diagrams missing')

if errors:
    print('ALL_TECH_REPORT_v8626 FAILED')
    for e in errors:
        print('-', e)
    print('report:', out)
    sys.exit(1)
print(f'ALL_TECH_REPORT_v8626 ok: lines={len(md.splitlines())} steps={len(res["model"]["steps"])} findings={len(res.get("findings", []))} report={out}')
