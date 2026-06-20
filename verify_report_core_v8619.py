# -*- coding: utf-8 -*-
from engine import analyze
from report import markdown_report, _channel_decision, _is_cross_control_step_v8619

payload = {
    'meta': {'name': 'v8.6.19 контроль отчёта', 'entity': 'Entity', 'regulatory': 'yes', 'statuses': 'NEW, SENT, DONE'},
    'systems': [
        {'name': 'Система-инициатор', 'role': 'external'},
        {'name': 'Сервис процесса', 'role': 'internal'},
        {'name': 'Хранилище состояния процесса', 'role': 'db'},
        {'name': 'Внешняя система / партнёр', 'role': 'external'},
        {'name': 'Аналитическое хранилище', 'role': 'analytics'},
        {'name': 'Контур наблюдаемости', 'role': 'observability'},
        {'name': 'Хранилище секретов', 'role': 'security'},
        {'name': 'Audit journal', 'role': 'audit'},
        {'name': 'Внутренний сервис быстрых ответов', 'role': 'internal'},
    ],
    'steps': [
        {'order': 1, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'source_system': 'Система-инициатор', 'system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': 'yes', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 2, 'name': 'Сервис процесса сохраняет результат в Хранилище состояния процесса', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Хранилище состояния процесса', 'channel': 'db', 'blocking': 'yes', 'writes_entity': 'yes', 'depends_on': '1', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 3, 'name': 'Сервис процесса передаёт данные в Внешняя система / партнёр', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Внешняя система / партнёр', 'channel': 'db', 'blocking': 'no', 'writes_entity': 'yes', 'depends_on': '2', 'retry': 'auto', 'idempotency': 'key', 'interaction_action': 'send_data', 'interaction_timing': 'later', 'interaction_result': 'save'},
        {'order': 4, 'name': 'Сервис процесса передаёт данные в Аналитическое хранилище', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Аналитическое хранилище', 'channel': 'data_warehouse', 'blocking': 'no', 'depends_on': '2', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 5, 'name': 'Быстро получить ответ от внутреннего сервиса', 'source_system': 'Аналитическое хранилище', 'system': 'Сервис процесса', 'target_system': 'Внутренний сервис быстрых ответов', 'channel': 'grpc', 'blocking': 'yes', 'depends_on': '4'},
        {'order': 6, 'name': 'Нужно видеть, где завис процесс', 'source_system': 'Все шаги процесса', 'system': 'Сервис процесса', 'target_system': 'Контур наблюдаемости', 'channel': 'observability', 'blocking': 'no'},
        {'order': 7, 'name': 'Нужно безопасно хранить секреты и ключи', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Хранилище секретов', 'channel': 'vault', 'blocking': 'yes'},
        {'order': 8, 'name': 'Записать неизменяемый audit journal', 'source_system': 'Сервис процесса', 'system': 'Audit journal', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': 'yes'},
    ],
}
res = analyze(payload)
md = markdown_report(res)
open('REPORT_CORE_v8_6_19.md','w',encoding='utf-8').write(md)

failures = []
# Step decisions
steps = {s['order']: s for s in res['model']['steps']}
if _channel_decision(steps[3])['primary_channel'] in ('callback','webhook','db'):
    failures.append('outbound_external_wrong_primary')
if _channel_decision(steps[4])['primary_channel'] in ('db','data_warehouse','data_lake','lakehouse'):
    failures.append('analytics_target_wrong_primary')
if not _is_cross_control_step_v8619(steps[6]) or not _is_cross_control_step_v8619(steps[7]) or not _is_cross_control_step_v8619(steps[8]):
    failures.append('cross_controls_not_classified')
# Report text guards
bad = [
    'Основной способ взаимодействия: Обратный вызов',
    'Основной способ взаимодействия: Аналитическое хранилище',
    'Маршрут:',
    'лимит запросовs',
    'таблица входящих сообщений для дедупликации table',
    'повторная обработка должен',
    'каждый повторная попытка',
]
for b in bad:
    if b in md:
        failures.append('bad_text:' + b)
required = [
    '## Почему выбраны технологии и способы взаимодействия',
    '## Сквозные контроли и служебные компоненты',
    '## Проверка логики схемы',
    'Сервис процесса передаёт данные в Аналитическое хранилище». Основной способ взаимодействия: ETL/ELT-загрузка',
    'Быстро получить ответ от внутреннего сервиса». Основной способ взаимодействия: сначала исправить схему',
]
for r in required:
    if r not in md:
        failures.append('missing:' + r)
if failures:
    print('FAIL', failures)
    raise SystemExit(1)
print('REPORT_CORE_v8619 ok')
