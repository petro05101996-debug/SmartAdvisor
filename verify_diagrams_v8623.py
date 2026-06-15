#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка Mermaid-схем отчёта: маршруты строятся по source→target, без ложных self-loop и без смешивания контролей."""
import json, pathlib, re, subprocess, sys
import engine
from report import markdown_report

script = pathlib.Path(__file__).with_name('mega_case_check_v8620.py')
if not pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json').exists():
    subprocess.run([sys.executable, str(script)], check=True)
payload = json.loads(pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json').read_text(encoding='utf-8'))
for sys_name, role in [('Слой защиты и маскирования','security'), ('Audit journal','audit')]:
    if not any(x.get('name') == sys_name for x in payload.get('systems', [])):
        payload.setdefault('systems', []).append({'name': sys_name, 'role': role, 'criticality': 'high', 'stability': 'stable'})
base_order = max(int(x.get('order', 0)) for x in payload.get('steps', []))
payload['steps'].extend([
    {'order': base_order + 1, 'name': 'Отправить REST-запрос внешнему партнёру', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Внешний партнёр', 'channel': 'rest', 'blocking': False, 'timeout_ms': 800, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order},
    {'order': base_order + 2, 'name': 'Классифицировать и маскировать чувствительные поля', 'system': 'Слой защиты и маскирования', 'source_system': 'Сервис процесса', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': False, 'timeout_ms': 0, 'retry': 'none', 'idempotency': 'none', 'writes_entity': False, 'depends_on': base_order + 1},
    {'order': base_order + 3, 'name': 'Записать неизменяемый audit journal', 'system': 'Audit journal', 'source_system': 'Сервис процесса', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': True, 'timeout_ms': 200, 'retry': 'none', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order + 2},
])
res = engine.analyze(payload)
md = markdown_report(res)
out = pathlib.Path('/mnt/data/ALL_TECH_REPORT_v8_6_23_DIAGRAMS.md')
out.write_text(md, encoding='utf-8')
errors = []

def must(cond, msg):
    if not cond:
        errors.append(msg)

must('## Диаграммы процесса' in md, 'diagram section missing')
must('### Основная схема взаимодействий' in md, 'main flow diagram missing')
must(('### Последовательность основной цепочки' in md) or ('### Условный порядок отображения связей' in md), 'sequence/conditional order diagram missing')
must('### Сквозные контроли' in md, 'controls diagram missing')
must('Исполнитель шага не подставляется внутрь маршрута' in md, 'diagram explanation missing')

# Старые ложные маршруты из v8.6.22: граф строился через executor/system и давал много self-loop.
for bad in [
    'Сервис_процесса -->|15.',
    'Сервис_процесса -.->|26.',
    'Сервис_процесса -->|51.',
    'Сервис_процесса -.->|57.',
    'Сервис процесса → Сервис процесса →',
]:
    must(bad not in md, f'old executor-based route remains: {bad}')

# Важные маршруты должны быть source→target, а не source→executor→target.
for expected in [
    'Сервис процесса"]\n N2["ActiveMQ очередь',
    'Отправить корпоративное сообщение в ActiveMQ',
    'Клиентский канал',
    'API Gateway',
    'Внешний партнёр',
    'Эндпоинт обратного результата',
    'Слой защиты и маскирования',
    'Audit journal',
]:
    must(expected in md, f'expected node/route missing: {expected}')

# Не должно быть графических петель node->same node в Mermaid-схемах отчёта.
for line in md.splitlines():
    m = re.match(r'\s*(N\d+)\s+(?:-->|-\.->)\|.*\|\s+(N\d+)\s*$', line)
    if m and m.group(1) == m.group(2):
        errors.append(f'self-loop in Mermaid diagram: {line}')

if errors:
    print('DIAGRAMS_v8623 FAILED')
    for e in errors:
        print('-', e)
    print('report:', out)
    sys.exit(1)
print(f'DIAGRAMS_v8623 ok: diagrams=3 report={out}')
