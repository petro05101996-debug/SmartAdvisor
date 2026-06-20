#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка читаемости отчёта v8.6.22 на полном all-tech кейсе."""
import json
import pathlib
import subprocess
import sys

import engine
from report import markdown_report

# Используем тот же all-tech payload, что и глубокий v8.6.21 аудит.
script = pathlib.Path(__file__).with_name('mega_case_check_v8620.py')
payload_file = pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json')
if not payload_file.exists():
    subprocess.run([sys.executable, str(script)], check=True)
payload = json.loads(payload_file.read_text(encoding='utf-8'))

for sys_name, role in [('Слой защиты и маскирования', 'security'), ('Audit journal', 'audit')]:
    if not any(x.get('name') == sys_name for x in payload.get('systems', [])):
        payload.setdefault('systems', []).append({'name': sys_name, 'role': role, 'criticality': 'high', 'stability': 'stable'})
base_order = max(int(x.get('order', 0)) for x in payload.get('steps', []))
# Не дублируем edge-шаги, если скрипт запускали несколько раз в одном процессе/файле.
if not any(x.get('name') == 'Отправить REST-запрос внешнему партнёру' for x in payload.get('steps', [])):
    payload['steps'].extend([
        {'order': base_order + 1, 'name': 'Отправить REST-запрос внешнему партнёру', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Внешний партнёр', 'channel': 'rest', 'blocking': False, 'timeout_ms': 800, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order, 'data_in': 'operationId, externalRequestId', 'data_out': 'запрос партнёру с внешним requestId', 'compensation': 'проверка неизвестного результата'},
        {'order': base_order + 2, 'name': 'Классифицировать и маскировать чувствительные поля', 'system': 'Слой защиты и маскирования', 'source_system': 'Сервис процесса', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': False, 'timeout_ms': 0, 'retry': 'none', 'idempotency': 'none', 'writes_entity': False, 'depends_on': base_order + 1, 'data_in': 'персональные данные', 'data_out': 'маскированное тело сообщения', 'compensation': ''},
        {'order': base_order + 3, 'name': 'Записать неизменяемый audit journal', 'system': 'Audit journal', 'source_system': 'Сервис процесса', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': True, 'timeout_ms': 200, 'retry': 'none', 'idempotency': 'key', 'writes_entity': True, 'depends_on': base_order + 2, 'data_in': 'correlationId, actor, action, reason', 'data_out': 'append-only audit entry', 'compensation': ''},
    ])

res = engine.analyze(payload)
md = markdown_report(res)
out = pathlib.Path('ALL_TECH_REPORT_v8_6_22_READABLE.md')
out.write_text(md, encoding='utf-8')

errors = []
def must(cond, msg):
    if not cond:
        errors.append(msg)

for section in [
    '## Короткий человеческий вывод',
    '## Что блокирует запуск',
    '## Рекомендуемый порядок действий',
    '## Проверка логики схемы',
    '## Почему выбраны технологии и способы взаимодействия',
    '## Сквозные контроли и служебные компоненты',
    '## Контрольные проверки готовности к промышленному запуску',
    '## Какие вводные нужно уточнить',
    'Приложение B. Найденные риски и слабые места',
    'Приложение E. Обязательный архитектурный чек-лист',
    'Приложение F. Матрица деталей, которые нельзя забыть',
]:
    must(section in md, f'missing readable section: {section}')

bad_phrases = [
    'Transactional таблица', 'таблица входящих сообщений для дедупликации table',
    'сверка-сверку', 'повторная обработка должен', 'повторная попытка должен', 'каждый повторная попытка',
    'лимит запросовing', 'лимит запросовs', "{'tables'", 'Payload', 'payload', 'retry', 'Retry',
    'replay', 'Replay', 'runbook', 'event envelope', 'срок хранения-политикой',
]
for phrase in bad_phrases:
    must(phrase not in md, f'bad phrase found: {phrase}')

# Смысловые регрессии, которые раньше ломали доверие к отчёту.
must('Основной способ взаимодействия: Аналитическое хранилище' not in md, 'analytics target used as transport')
must('Основной способ взаимодействия: Озеро данных' not in md, 'data lake target used as transport')
must('Основной способ взаимодействия: Data Warehouse' not in md, 'DWH target used as transport')
must('Основной способ взаимодействия: REST API / HTTP-запрос к внешнему партнёру' in md, 'outbound partner request missing')
must('Основной способ взаимодействия: Входящий веб-вызов' in md, 'inbound webhook missing')
must(('Основной способ взаимодействия: Реплика БД' in md) or ('Основной способ взаимодействия: Реплика базы данных для чтения' in md), 'read replica label missing')
must('Служебная запись в БД не должна подменять канал взаимодействия с получателем.' in md, 'service DB warning missing')
must('Сквозные вещи — аудит, безопасность, авторизация, наблюдаемость, секреты — вынесены отдельно' in md, 'cross-control separation explanation missing')

# Отчёт должен быть структурирован: основной вывод короткий, детали спрятаны в приложения.
must(md.index('## Что блокирует запуск') < md.index('Приложение B. Найденные риски'), 'details appear before summary')
must(md.count('<details>') >= 4, 'long appendices should be collapsed')

if errors:
    print('READABLE_REPORT_v8622 FAILED')
    for e in errors:
        print('-', e)
    print('report:', out)
    sys.exit(1)
print(f'READABLE_REPORT_v8622 ok: report={out} lines={len(md.splitlines())} steps={len(res["model"]["steps"])}')
