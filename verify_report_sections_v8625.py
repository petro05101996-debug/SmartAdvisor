#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка каждого раздела отчёта v8.6.25 на структуру, язык и старые логические регрессии."""
import json
import pathlib
import re
import subprocess
import sys

import engine
from report import markdown_report

ROOT = pathlib.Path(__file__).resolve().parent
payload_file = pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json')
if not payload_file.exists():
    subprocess.run([sys.executable, str(ROOT / 'mega_case_check_v8620.py')], check=True)
payload = json.loads(payload_file.read_text(encoding='utf-8'))

# Edge-шаги, которые раньше ломали отчёт: партнёрский REST, маскирование, audit journal.
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
out = ROOT / 'ALL_TECH_REPORT_v8_6_25_SECTION_AUDIT.md'
out.write_text(md, encoding='utf-8')

errors = []
def must(cond, msg):
    if not cond:
        errors.append(msg)

sections = [
    '# Архитектурный разбор:',
    '## Короткий человеческий вывод',
    '## Что блокирует запуск',
    '## Рекомендуемый порядок действий',
    '## Проверка логики схемы',
    '## Почему выбраны технологии и способы взаимодействия',
    '## Сквозные контроли и служебные компоненты',
    '## Контрольные проверки готовности к промышленному запуску',
    '## Какие вводные нужно уточнить',
    '## Краткая сводка по стеку',
    'Приложение A. Полная таблица по всем шагам',
    'Приложение B. Найденные риски и слабые места',
    'Приложение C. Сценарная основа для дальнейшей разработки',
    'Приложение D. Артефакты для постановки и выпуска',
    'Приложение E. Обязательный архитектурный чек-лист',
    'Приложение F. Матрица деталей, которые нельзя забыть',
    '## Диаграммы процесса',
]
for s in sections:
    must(s in md, f'missing section: {s}')

# Порядок основных разделов должен быть понятным.
order_tokens = [
    '## Короткий человеческий вывод',
    '## Что блокирует запуск',
    '## Рекомендуемый порядок действий',
    '## Проверка логики схемы',
    '## Почему выбраны технологии и способы взаимодействия',
    '## Сквозные контроли и служебные компоненты',
    '## Контрольные проверки готовности к промышленному запуску',
    '## Какие вводные нужно уточнить',
    '## Краткая сводка по стеку',
]
positions = [md.find(x) for x in order_tokens]
must(all(p >= 0 for p in positions), 'main sections missing')
must(positions == sorted(positions), 'main section order is broken')

# Каждая крупная секция должна быть содержательной, а не пустым заголовком.
for i, token in enumerate(order_tokens):
    start = md.find(token)
    end_candidates = [md.find(t, start + 1) for t in order_tokens[i+1:] if md.find(t, start + 1) != -1]
    end = min(end_candidates) if end_candidates else md.find('<details>', start)
    if end == -1:
        end = len(md)
    body = md[start:end].strip()
    must(len(body.splitlines()) >= 3, f'section too short: {token}')

bad_phrases = [
    'нужна таблицу', 'используется таблицу', 'таблица входящих сообщений для дедупликации table',
    'лимит запросовing', 'лимит запросовs', 'повторная обработка должен', 'повторная попытка должен',
    'каждый повторная попытка', 'многоклиентском модель', 'мониторинг накопление', 'без обратное давление',
    'Transactional', 'dead-letter', 'routing key', 'маршрутизация key', 'prefetch', 'persistence',
    'task queue', 'event log', 'Polling', 'Outbox', 'сверка-сверку', 'срок хранения-политикой',
    'retries', 'worker-', 'worker pool', 'Без envelope', 'scope уникальности', 'коммитьте позиция',
    'или дедупликация.', "{'tables'", 'Payload', 'payload',
]
for phrase in bad_phrases:
    must(phrase not in md, f'bad language phrase: {phrase}')

# Проверка старых логических ошибок.
logic_bad = [
    'Основной способ взаимодействия: Аналитическое хранилище',
    'Основной способ взаимодействия: Data Warehouse',
    'Основной способ взаимодействия: Озеро данных',
    'Основной способ взаимодействия: Основная база данных.\n**Где:** связь идёт от «Сервис процесса» к «Внешний партнёр»',
    'Основной способ взаимодействия: Обратный вызов.\n**Где:** связь идёт от «Сервис процесса» к «Внешний партнёр»',
    'Классифицировать и маскировать чувствительные поля». Основной способ взаимодействия: REST API',
    'Записать неизменяемый audit journal». Основной способ взаимодействия: Основная база данных',
]
for phrase in logic_bad:
    must(phrase not in md, f'logic regression: {phrase}')

# Должны присутствовать исправленные смысловые представления.
for expected in [
    'Основной способ взаимодействия: REST API / HTTP-запрос к внешнему партнёру',
    'Основной способ взаимодействия: Входящий веб-вызов',
    '**Назначение:** защита и маскирование данных',
    '**Назначение:** неизменяемый журнал аудита',
    'Основная схема взаимодействий',
    'Условный порядок отображения связей',
    'Сквозные контроли',
    'Сценарные блоки по типам взаимодействий',
    'Ошибочные сценарии и восстановление',
]:
    must(expected in md, f'expected fixed content missing: {expected}')

# Полный all-tech отчёт не должен притворяться одним линейным happy path.
scenario_start = md.find('Приложение C. Сценарная основа')
scenario_end = md.find('Приложение D. Артефакты')
scenario = md[scenario_start:scenario_end]
must('карту множества интеграционных возможностей' in scenario, 'all-tech scenario warning missing')
must('### Основной сценарий' not in scenario, 'all-tech report incorrectly has one main happy path')

# Диаграммы должны быть в markdown и не должны идти через фиктивный self-call исполнителя.
must('```mermaid' in md, 'mermaid diagrams missing')
must('Журнал событий Kafka' in md and 'Очередь задач RabbitMQ' in md, 'main process diagrams missing expected nodes')
must('Сервис процесса → Сервис процесса → Внешний партнёр' not in md, 'old triple route remains')

if errors:
    print('REPORT_SECTIONS_v8625 FAILED')
    for e in errors:
        print('-', e)
    print('report:', out)
    sys.exit(1)
print(f'REPORT_SECTIONS_v8625 ok: sections={len(sections)} lines={len(md.splitlines())} steps={len(res["model"]["steps"])} report={out}')
