"""Optional heavy verification for action-grammar coverage.
Run manually: PYTHONPATH=. python verify_action_grammar_matrix.py
This script intentionally is not named test_*.py to avoid slowing normal CI.
"""
from itertools import product
from engine import analyze

STARTS = ['incoming_request', 'event', 'file', 'schedule', 'unknown']
ACTS = ['call_external', 'receive_data', 'send_data', 'validate', 'enrich', 'wait_status']
TIMINGS = ['immediate', 'later', 'both', 'unknown']
RESULTS = ['save', 'forward', 'save_forward', 'update_status', 'compare', 'unknown']
SYSTEMS = ['2', '3', '4', 'unknown']

def sys(name, role='internal'):
    return {'name': name, 'role': role, 'criticality': 'medium', 'stability': 'unknown'}

def step(order, name, src, actor, target, channel='rest', blocking='yes', timeout='500', retry='auto', idem='key', writes='no', dep='', comp='retry, manual review'):
    return {
        'order': order, 'name': name, 'source_system': src, 'system': actor, 'target_system': target,
        'channel': channel, 'blocking': blocking, 'timeout_ms': timeout, 'retry': retry,
        'idempotency': idem, 'writes_entity': writes, 'depends_on': dep,
        'compensation': comp, 'failure_policy': 'DLQ / replay' if channel in {'kafka','queue'} else 'Повторить автоматически',
        'component_type': 'action',
        'data_in': 'partition key / lookup key: businessId; correlationId пробрасывается через шаги',
        'data_out': 'eventId, correlationId, status, statusVersion',
    }

def make_payload(start, act, timing, result, systems):
    proc, db, src, provider, target = 'Сервис процесса', 'БД процесса', 'Система-инициатор', 'Внешняя система / поставщик', 'Целевая система / получатель'
    p = {
        'meta': {
            'name': 'Matrix check', 'entity': 'BusinessEntity',
            'goal': 'Проверить генерацию action grammar payload.',
            'lookup_keys': 'requestId + targetSystem; eventId; correlationId; partition key = requestId',
            'statuses': 'CREATED, PROCESSING, WAITING_RESULT, RESULT_RECEIVED, SAVED, SENT_TO_TARGET, FAILED, NEEDS_MANUAL_REVIEW',
            'fields': 'requestId:string|required|unique, eventId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required, statusVersion:int',
            'customer_visible': 'mixed', 'ordering': 'per_entity',
            'description': f'base={start}/{act}/{timing}/{result}/{systems}',
        },
        'systems': [sys(proc), sys(db, 'db'), sys(src), sys(provider, 'external'), sys(target, 'external'), sys('Kafka / очередь', 'broker')],
        'steps': []
    }
    n = 1
    if start == 'event':
        p['steps'].append(step(n, 'Принять входящее событие и защититься от дублей', 'Kafka / очередь', proc, db, 'kafka', 'no', '', 'auto', 'key', 'yes', '', 'Inbox, UNIQUE eventId, DLQ/replay'))
    elif start == 'file':
        p['steps'].append(step(n, 'Принять файл или batch и создать запись процесса', src, proc, db, 'batch', 'no', '', 'manual', 'natural', 'yes', '', 'batchId, checksum, quarantine, reprocess'))
    elif start == 'schedule':
        p['steps'].append(step(n, 'Запустить процесс по расписанию и зафиксировать старт', 'Планировщик', proc, db, 'batch', 'no', '', 'manual', 'natural', 'yes', '', 'jobId, watermark, повторный запуск без дублей'))
    else:
        p['steps'].append(step(n, 'Принять входящий запрос и создать запись процесса', src, proc, db, 'db', 'yes', '200', 'none', 'key', 'yes', '', 'transaction, audit journal, уникальный requestId'))
    n += 1
    p['steps'].append(step(n, f'Основное действие: {act}', proc, proc, provider, 'rest', 'no' if timing == 'later' else 'yes', '1500', 'auto', 'key', 'no', str(n-1), 'timeout, circuit breaker, retry с idempotencyKey'))
    n += 1
    if timing in {'later', 'both'} or act == 'wait_status':
        p['steps'].append(step(n, 'Принять результат или статус позже', provider, provider, 'Kafka / очередь', 'kafka', 'no', '', 'auto', 'key', 'no', str(n-1), 'DLQ, eventId, statusVersion'))
        n += 1
        p['steps'].append(step(n, 'Дедуплицировать поздний результат и обновить историю', 'Kafka / очередь', proc, db, 'kafka', 'no', '', 'auto', 'key', 'yes', str(n-1), 'Inbox, UNIQUE eventId, replay-safe update, status history'))
        n += 1
    elif timing == 'unknown':
        p['steps'].append(step(n, 'Зафиксировать результат или неизвестное состояние', provider, proc, db, 'db', 'yes', '200', 'none', 'natural', 'yes', str(n-1), 'если ответ придёт позже — принять через Inbox/callback; иначе ручной разбор'))
        n += 1
    if result in {'save', 'save_forward', 'update_status', 'unknown'}:
        p['steps'].append(step(n, 'Сохранить результат и историю состояния', proc, proc, db, 'db', 'yes', '200', 'none', 'natural', 'yes', str(n-1), 'transaction, optimistic locking/statusVersion, status history'))
        n += 1
    if result in {'forward', 'save_forward'}:
        p['steps'].append(step(n, 'Передать результат дальше в целевую систему', proc, proc, target, 'rest', 'yes', '1500', 'auto', 'key', 'no', str(n-1), 'Outbox, retry limit, ручной разбор'))
        n += 1
    if result == 'compare':
        p['steps'].append(step(n, 'Сверить полученные данные с сохранённым состоянием', db, 'Сервис сверки', db, 'batch', 'no', '', 'manual', 'natural', 'yes', str(n-1), 'reconciliation key, окно ожидания, отчёт расхождений'))
    return p

failures = []
colors = {}
for combo in product(STARTS, ACTS, TIMINGS, RESULTS, SYSTEMS):
    payload = make_payload(*combo)
    res = analyze(payload)
    if not res.get('ok'):
        failures.append((combo, res.get('errors') or res))
        break
    colors[res.get('verdict', {}).get('color', 'unknown')] = colors.get(res.get('verdict', {}).get('color', 'unknown'), 0) + 1

print(f'checked={len(STARTS)*len(ACTS)*len(TIMINGS)*len(RESULTS)*len(SYSTEMS)} failures={len(failures)} colors={colors}')
if failures:
    raise SystemExit(failures[0])
