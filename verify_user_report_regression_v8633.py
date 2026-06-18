# -*- coding: utf-8 -*-
from engine import analyze
from report import markdown_report
from pathlib import Path

payload = {
    'meta': {'name': 'Черновой разбор процесса', 'goal': 'Предварительно оценить интеграционный процесс по неполному описанию', 'entity': 'Entity', 'money': 'no', 'regulatory': False, 'customer_visible': False, 'sla_ms': 1000},
    'systems': [
        {'name': 'Система-инициатор', 'role': 'external'},
        {'name': 'Сервис процесса', 'role': 'internal'},
        {'name': 'Старый контур', 'role': 'legacy'},
        {'name': 'Внешняя система / партнёр', 'role': 'external'},
        {'name': 'Аналитическое хранилище', 'role': 'analytics'},
    ],
    'steps': [
        {'order': 1, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'system': 'Система-инициатор', 'source_system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'kafka', 'blocking': False, 'retry': 'auto', 'idempotency': 'none', 'timeout_ms': 0, 'writes_entity': False, 'data_out': 'event without envelope'},
        {'order': 2, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'system': 'Система-инициатор', 'source_system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'kafka', 'blocking': False, 'retry': 'auto', 'idempotency': 'none', 'depends_on': 1, 'writes_entity': False, 'data_out': 'event without envelope'},
        {'order': 3, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'system': 'Система-инициатор', 'source_system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': True, 'retry': 'auto', 'idempotency': 'key', 'timeout_ms': 500, 'depends_on': 2, 'writes_entity': False},
        {'order': 4, 'name': 'Сервис процесса передаёт данные в Старый контур', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Старый контур', 'channel': 'esb', 'blocking': True, 'retry': 'auto', 'idempotency': 'key', 'timeout_ms': 500, 'depends_on': 3, 'writes_entity': False},
        {'order': 5, 'name': 'Сервис процесса передаёт данные в Внешняя система / партнёр', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Внешняя система / партнёр', 'channel': 'callback', 'primary_channel': 'rest', 'interaction_timing': 'later', 'interaction_result': 'partner returns later', 'blocking': False, 'retry': 'auto', 'idempotency': 'key', 'timeout_ms': 0, 'depends_on': 4, 'writes_entity': False},
        {'order': 6, 'name': 'Сервис процесса передаёт данные в Аналитическое хранилище', 'system': 'Сервис процесса', 'source_system': 'Сервис процесса', 'target_system': 'Аналитическое хранилище', 'channel': 'etl', 'blocking': False, 'retry': 'auto', 'idempotency': 'key', 'depends_on': 5, 'writes_entity': True, 'data_out': 'контрольная сумма'},
    ]
}
res = analyze(payload)
assert res['ok'], res
md = markdown_report(res)
Path('USER_REPORT_v8_6_33.md').write_text(md, encoding='utf-8')

bad_fragments = [
    'былааа', 'с увеличение паузы', 'по таймаут,', 'потребительs',
    'управляемый флаг включенияs', 'known-degradation', 'pause/resume',
    'Event storm', 'Late события', 'task queue', 'worker-ами', 'DLQ',
    'retry', 'replay', 'runbook', 'Outbox', 'Inbox',
]
for frag in bad_fragments:
    assert frag not in md, frag
# Исходящий запрос к партнёру не должен становиться blocker по подписи входящего webhook.
assert 'Входящий веб-вызов должен проходить проверку подлинности' not in md
# Но схема должна подсказать добавить отдельный входящий результат.
assert 'отдельный входящий шаг от партнёра' in md
# Дубли одинаковых связей должны быть подсвечены.
assert 'несколько одинаковых связей' in md
# Сценарии и acceptance не должны дублировать общий async-блок.
assert '#### Асинхронная обработка без ожидания финального результата' not in md
assert md.count('основной сценарий проходит до финального статуса') <= 1
# Нет старого пустого места без контекста в grouped findings.
assert 'Затронутые места: Затронуто мест:' not in md
print('USER_REPORT_REGRESSION_v8633 ok', 'lines=', len(md.splitlines()))
