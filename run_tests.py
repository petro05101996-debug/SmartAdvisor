#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты v6. Запуск: python run_tests.py  (pytest не требуется).

Каждая функция test_* — независимый тест на assert'ах.
"""
import json
import threading
import urllib.request

import engine
from engine import analyze, normalize, build_graph
from report import markdown_report


def step(order, name, system, channel='rest', blocking='yes', timeout=0,
         retry='none', idem='none', comp='', writes='no', dep=0, din='', dout=''):
    return {'order': order, 'name': name, 'system': system, 'channel': channel,
            'blocking': blocking, 'timeout_ms': timeout, 'retry': retry,
            'idempotency': idem, 'compensation': comp, 'writes_entity': writes,
            'depends_on': dep, 'data_in': din, 'data_out': dout}


def base(meta=None, systems=None, steps=None):
    return {'meta': {'name': 'P', 'entity': 'Order', **(meta or {})},
            'systems': systems or [], 'steps': steps or []}


def rules_fired(res):
    return {f['rule'] for f in res['findings']}


# ------------------------------------------------------------ нормализация
def test_normalize_and_fields():
    m = normalize(base(meta={'fields': 'a:uuid|required|indexed, b:decimal, c:string|unique'}))
    f = m['meta']['fields']
    assert len(f) == 3
    assert f[0] == {'name': 'a', 'type': 'uuid', 'required': True,
                    'unique': False, 'indexed': True, 'sensitive': False}
    assert f[2]['unique'] is True


def test_validate_errors():
    res = analyze(base())
    assert res['ok'] is False and any('хотя бы один шаг' in e for e in res['errors'])
    res = analyze(base(steps=[step(1, 'a', 'S'), step(1, 'b', 'S')]))
    assert res['ok'] is False and any('Дублируется' in e for e in res['errors'])
    res = analyze(base(steps=[step(1, 'a', 'S', dep=99)]))
    assert res['ok'] is False and any('несуществующего' in e for e in res['errors'])


# ------------------------------------------------------------ граф
def test_critical_path_and_budget():
    m = build_graph(normalize(base(steps=[
        step(1, 'a', 'S1', timeout=100),
        step(2, 'b', 'S2', timeout=200, dep=1),
        step(3, 'c', 'S3', blocking='no', dep=2),
        step(4, 'd', 'S4', timeout=300, dep=2),
    ])))
    g = m['graph']
    assert [s['order'] for s in g['critical_path']] == [1, 2, 4]
    assert g['critical_budget_ms'] == 600
    assert g['sync_depth'] == 3


def test_cycle_does_not_hang():
    m = build_graph(normalize(base(steps=[step(1, 'a', 'S', dep=2), step(2, 'b', 'S', dep=1)])))
    assert isinstance(m['graph']['critical_path'], list)  # не зависли


# ------------------------------------------------------------ правила
def test_rule_sync_chain_depth():
    res = analyze(base(steps=[step(1, 'a', 'S1'), step(2, 'b', 'S2', dep=1),
                              step(3, 'c', 'S3', dep=2)]))
    assert 'sync_chain_depth' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'a', 'S1'), step(2, 'b', 'S2', dep=1)]))
    assert 'sync_chain_depth' not in rules_fired(res2)


def test_rule_external_blocking_severity():
    sysx = [{'name': 'Партнёр', 'role': 'external'}]
    res = analyze(base(meta={'customer_visible': 'yes', 'sla_ms': 500},
                       systems=sysx, steps=[step(1, 'вызов', 'Партнёр', timeout=400)]))
    f = [x for x in res['findings'] if x['rule'] == 'external_blocking'][0]
    assert f['severity'] == 'critical'
    res2 = analyze(base(systems=sysx, steps=[step(1, 'вызов', 'Партнёр', timeout=400)]))
    f2 = [x for x in res2['findings'] if x['rule'] == 'external_blocking'][0]
    assert f2['severity'] == 'high'


def test_rule_retry_without_idempotency_money():
    res = analyze(base(meta={'money': 'direct'},
                       steps=[step(1, 'списать', 'Биллинг', retry='auto', writes='yes')]))
    f = [x for x in res['findings'] if x['rule'] == 'retry_without_idempotency'][0]
    assert f['severity'] == 'critical' and 'double-spend' in f['why']
    res2 = analyze(base(meta={'money': 'direct'},
                        steps=[step(1, 'списать', 'Биллинг', retry='auto', idem='key', writes='yes')]))
    assert 'retry_without_idempotency' not in rules_fired(res2)


def test_rule_money_multiple_writers():
    res = analyze(base(meta={'money': 'direct'}, steps=[
        step(1, 'a', 'S1', writes='yes', idem='key'),
        step(2, 'b', 'S2', writes='yes', idem='key', dep=1)]))
    f = [x for x in res['findings'] if x['rule'] == 'money_controls']
    assert f and f[0]['severity'] == 'critical' and 'писат' in f[0]['why'] or 'писа' in f[0]['title'].lower()


def test_rule_async_without_recovery():
    res = analyze(base(steps=[step(1, 'pub', 'Kafka', channel='kafka', blocking='no')]))
    assert 'async_without_recovery' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'pub', 'Kafka', channel='kafka',
                                    blocking='no', retry='auto')]))
    assert 'async_without_recovery' not in rules_fired(res2)


def test_rule_saga_without_compensation():
    res = analyze(base(steps=[step(1, 'a', 'S1', writes='yes'),
                              step(2, 'b', 'S2', writes='yes', dep=1)]))
    assert 'saga_without_compensation' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'a', 'S1', writes='yes'),
                               step(2, 'b', 'S2', writes='yes', dep=1, comp='откат')]))
    assert 'saga_without_compensation' not in rules_fired(res2)


def test_rule_sla_budget_numbers():
    res = analyze(base(meta={'sla_ms': 500},
                       steps=[step(1, 'a', 'S1', timeout=400),
                              step(2, 'b', 'S2', timeout=400, dep=1)]))
    f = [x for x in res['findings'] if x['rule'] == 'sla_budget'][0]
    assert '800' in f['why'] and '500' in f['why'] and f['severity'] == 'critical'


def test_rule_missing_timeouts():
    res = analyze(base(steps=[step(1, 'a', 'S1'), step(2, 'b', 'S2', dep=1, timeout=100)]))
    f = [x for x in res['findings'] if x['rule'] == 'missing_timeouts'][0]
    assert '«a»' in f['where'] and '«b»' not in f['where']


def test_rule_dual_write_outbox():
    res = analyze(base(steps=[step(1, 'save', 'S1', writes='yes', idem='key'),
                              step(2, 'pub', 'S1', channel='kafka', dep=1, retry='auto')]))
    assert 'dual_write' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'save', 'S1', writes='yes', idem='key'),
                               step(2, 'pub', 'S1', channel='kafka', dep=1,
                                    retry='auto', comp='outbox')]))
    assert 'dual_write' not in rules_fired(res2)


def test_rule_callback_inbox():
    res = analyze(base(steps=[step(1, 'callback провайдера', 'PSP', channel='webhook',
                                   blocking='no', retry='auto')]))
    assert 'callback_inbox' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'callback', 'PSP', channel='webhook',
                                    blocking='no', retry='auto', idem='key')]))
    assert 'callback_inbox' not in rules_fired(res2)


def test_rule_slow_channel_and_analytics():
    res = analyze(base(meta={'customer_visible': 'yes'},
                       steps=[step(1, 'выгрузка', 'Файлообмен', channel='file')]))
    assert 'slow_channel_in_fast_path' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'в витрину', 'DWH', channel='rest')]))
    assert 'analytics_in_core' in rules_fired(res2)
    res3 = analyze(base(steps=[step(1, 'в витрину', 'DWH', channel='cdc', blocking='no', retry='auto')]))
    assert 'analytics_in_core' not in rules_fired(res3)


def test_rule_regulatory_audit():
    res = analyze(base(meta={'regulatory': 'yes'}, steps=[step(1, 'a', 'S')]))
    assert 'regulatory_audit' in rules_fired(res)
    res2 = analyze(base(meta={'regulatory': 'yes'},
                        steps=[step(1, 'a', 'S'), step(2, 'записать аудит', 'Журнал', dep=1)]))
    assert 'regulatory_audit' not in rules_fired(res2)


def test_rule_ordering():
    res = analyze(base(meta={'ordering': 'per_entity'},
                       steps=[step(1, 'pub', 'Kafka', channel='kafka', blocking='no', retry='auto')]))
    assert 'ordering' in rules_fired(res)
    res2 = analyze(base(meta={'ordering': 'per_entity'},
                        steps=[step(1, 'pub', 'Kafka', channel='kafka', blocking='no',
                                    retry='auto', din='partition key = orderId')]))
    assert 'ordering' not in rules_fired(res2)
    res3 = analyze(base(meta={'ordering': 'global'}, steps=[step(1, 'a', 'S')]))
    assert any(f['rule'] == 'ordering' and f['severity'] == 'high' for f in res3['findings'])


def test_rule_fanout_sync():
    res = analyze(base(steps=[step(1, 'root', 'S0')] +
                       [step(i, f'call{i}', f'S{i}', dep=1) for i in range(2, 5)]))
    assert 'fanout_sync' in rules_fired(res)


def test_rule_unstable_dependency():
    systems = [{'name': 'Партнёр', 'role': 'external', 'stability': 'unstable'},
               {'name': 'API', 'role': 'external', 'stability': 'limited'}]
    res = analyze(base(systems=systems,
                       steps=[step(1, 'a', 'Партнёр', timeout=100),
                              step(2, 'b', 'API', blocking='no', channel='queue',
                                   dep=1, retry='auto')]))
    fired = rules_fired(res)
    assert 'unstable_dependency' in fired
    sev = {f['title'] for f in res['findings'] if f['rule'] == 'unstable_dependency'}
    assert any('нестабильной' in t for t in sev) and any('rate limit' in t for t in sev)


def test_rule_status_model_and_spof():
    steps = [step(1, 'a', 'Core', timeout=100, idem='key'),
             step(2, 'b', 'Core', timeout=100, dep=1),
             step(3, 'c', 'S3', channel='kafka', blocking='no', dep=2, retry='auto'),
             step(4, 'd', 'S4', channel='kafka', blocking='no', dep=3, retry='auto')]
    res = analyze(base(systems=[{'name': 'Core', 'criticality': 'critical'}], steps=steps))
    fired = rules_fired(res)
    assert 'status_model' in fired and 'spof' in fired
    res2 = analyze(base(meta={'statuses': 'A,B'},
                        systems=[{'name': 'Core', 'criticality': 'critical'}], steps=steps))
    assert 'status_model' not in rules_fired(res2)


# ------------------------------------------------------------ паттерны/схема
def test_patterns_composition():
    res = analyze(base(
        meta={'money': 'direct', 'customer_visible': 'yes', 'read_freq': 'very_high'},
        systems=[{'name': 'Партнёр', 'role': 'external'}, {'name': 'S2'}, {'name': 'S3'}],
        steps=[step(1, 'списание', 'S2', writes='yes', idem='key', timeout=100),
               step(2, 'вызов партнёра', 'Партнёр', dep=1, timeout=500),
               step(3, 'событие', 'S2', channel='kafka', blocking='no', dep=2,
                    retry='auto', comp='outbox'),
               step(4, 'callback', 'S3', channel='webhook', blocking='no',
                    dep=3, retry='auto', idem='key')]))
    pids = {p['id'] for p in res['patterns']}
    assert {'outbox', 'dlq_replay', 'idempotent_consumer', 'tracking',
            'circuit_breaker', 'ledger', 'read_model'} <= pids


def test_db_schema_tables():
    res = analyze(base(
        meta={'money': 'direct', 'entity': 'Loan App',
              'fields': 'amount:decimal|required, key:string|unique, clientId:uuid|indexed'},
        steps=[step(1, 'save', 'S1', writes='yes', idem='key'),
               step(2, 'pub', 'S1', channel='kafka', dep=1, retry='auto', comp='outbox'),
               step(3, 'cb', 'PSP', channel='callback', blocking='no', dep=2,
                    retry='auto', idem='key')]))
    t = res['schema']['tables']
    assert 'loan_app' in t and 'outbox' in t and 'inbox' in t and 'ledger' in t \
           and 'loan_app_step_log' in t
    ddl = res['schema']['ddl']
    assert 'amount numeric(18,2) NOT NULL' in ddl
    assert 'key text UNIQUE' in ddl
    assert 'idx_loan_app_clientid'.lower() in ddl.lower()


# ------------------------------------------------------------ отчёт/диаграммы
def test_report_and_diagrams():
    res = analyze(base(meta={'sla_ms': 1000, 'statuses': 'A,B'},
                       steps=[step(1, 'a', 'S1', timeout=100, idem='key'),
                              step(2, 'b', 'S2', channel='kafka', blocking='no',
                                   dep=1, retry='auto', comp='outbox')]))
    md = markdown_report(res)
    for token in ('# Архитектурный разбор', '## Найденные риски и слабые места', '```sql',
                  '## Чек-лист проверок и тестов', 'mermaid'):
        assert token in md
    assert res['diagrams']['flow'].startswith('flowchart')
    assert 'sequenceDiagram' in res['diagrams']['sequence']
    assert '-.->' in res['diagrams']['flow']  # non-blocking пунктиром


def test_verdict_levels():
    good = analyze(base(meta={'statuses': 'A,B'},
                        steps=[step(1, 'a', 'S1', timeout=100, idem='key')]))
    assert good['verdict']['color'] == 'green'
    bad = analyze(base(meta={'money': 'direct', 'sla_ms': 100},
                       steps=[step(1, 'a', 'S1', retry='auto', writes='yes', timeout=500),
                              step(2, 'b', 'S2', dep=1, timeout=500),
                              step(3, 'c', 'S3', dep=2)]))
    assert bad['verdict']['color'] == 'red' and bad['verdict']['counts']['critical'] >= 2


def test_e2e_loan_demo_scenario():
    """Сценарий из кнопки «заполнить примером» — целиком."""
    res = analyze({
        'meta': {'name': 'Оформление кредитной заявки', 'entity': 'LoanApplication',
                 'customer_visible': 'yes', 'money': 'direct', 'sla_ms': 1000,
                 'statuses': 'CREATED, APPROVED, REJECTED',
                 'fields': 'clientId:uuid|required|indexed, amount:decimal|required, idempotencyKey:string|unique'},
        'systems': [{'name': 'Сервис заявок', 'role': 'internal', 'criticality': 'high'},
                    {'name': 'Сервис скоринга', 'role': 'external',
                     'criticality': 'critical', 'stability': 'unstable'},
                    {'name': 'Kafka', 'role': 'broker'},
                    {'name': 'CRM'}, {'name': 'DWH', 'role': 'analytics'}],
        'steps': [step(1, 'Создать заявку', 'Сервис заявок', timeout=500, idem='key', writes='yes'),
                  step(2, 'Отправить на скоринг', 'Сервис скоринга', timeout=5000,
                       retry='auto', dep=1),
                  step(3, 'Опубликовать статус', 'Kafka', channel='kafka', dep=2,
                       retry='auto', comp='outbox + retry'),
                  step(4, 'Обновить CRM', 'CRM', channel='kafka', blocking='no',
                       dep=3, retry='auto'),
                  step(5, 'Выгрузить в DWH', 'DWH', channel='cdc', blocking='no',
                       dep=3, retry='auto')]})
    assert res['ok']
    fired = rules_fired(res)
    # Бюджет 500+5000+(kafka 0) > SLA 1000 и retry скоринга без идемпотентности — должны поймать.
    assert 'sla_budget' in fired and 'retry_without_idempotency' in fired
    assert 'unstable_dependency' in fired and 'external_blocking' in fired
    assert res['verdict']['color'] == 'red'
    md = markdown_report(res)
    assert 'Сервис скоринга' in md


# ------------------------------------------------------------ HTTP
def test_http_smoke():
    import app as appmod
    appmod.APP_DIR.mkdir(exist_ok=True)
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(('127.0.0.1', 0), appmod.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        html = urllib.request.urlopen(f'http://127.0.0.1:{port}/').read().decode()
        assert 'Конструктор процесса'.upper() in html.upper() and 'addStep' in html

        payload = json.dumps({'meta': {'name': 'X', 'entity': 'E'},
                              'steps': [step(1, 'a', 'S', timeout=100, idem='key')]}).encode()
        req = urllib.request.Request(f'http://127.0.0.1:{port}/api/analyze', data=payload,
                                     headers={'Content-Type': 'application/json'})
        d = json.loads(urllib.request.urlopen(req).read())
        assert d['ok'] and len(d['id']) == 32

        page = urllib.request.urlopen(f'http://127.0.0.1:{port}/run/{d["id"]}').read().decode()
        assert 'Слабые места'.upper() in page.upper()
        md = urllib.request.urlopen(f'http://127.0.0.1:{port}/run/{d["id"]}.md').read().decode()
        assert md.startswith('# Архитектурный разбор')

        bad = urllib.request.Request(f'http://127.0.0.1:{port}/api/analyze',
                                     data='{не json'.encode('utf-8'),
                                     headers={'Content-Type': 'application/json'})
        try:
            urllib.request.urlopen(bad)
            assert False, 'ожидали 400'
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()



def test_rule_dual_write_consumption_not_flagged():
    """Воркер, читающий из очереди и пишущий БД, — не dual write."""
    res = analyze(base(
        systems=[{'name': 'Redis', 'role': 'broker'}],
        steps=[step(1, 'в очередь', 'Redis', channel='queue', timeout=50),
               step(2, 'воркер пишет БД', 'Воркер', channel='queue', blocking='no',
                    dep=1, retry='auto', writes='yes', idem='key', comp='DLQ после 5 попыток')]))
    assert 'dual_write' not in rules_fired(res)


def test_rule_poison_retry():
    res = analyze(base(steps=[step(1, 'обработка', 'Воркер', channel='queue',
                                   blocking='no', retry='auto', idem='key')]))
    assert 'poison_retry' in rules_fired(res)
    res2 = analyze(base(steps=[step(1, 'обработка', 'Воркер', channel='queue', blocking='no',
                                    retry='auto', idem='key', comp='DLQ после 5 попыток')]))
    assert 'poison_retry' not in rules_fired(res2)


def test_rule_inbound_security():
    res = analyze(base(steps=[step(1, 'принять webhook', 'API', channel='webhook',
                                   blocking='no', idem='key', retry='auto')]))
    f = [x for x in res['findings'] if x['rule'] == 'inbound_security'][0]
    assert f['severity'] == 'high'
    res2 = analyze(base(steps=[step(1, 'принять webhook, проверить подпись', 'API',
                                    channel='webhook', blocking='no', idem='key', retry='auto')]))
    f2 = [x for x in res2['findings'] if x['rule'] == 'inbound_security'][0]
    assert f2['severity'] == 'info'



def test_new_rules_negative_cases():
    # sensitive поля с описанной политикой — не срабатывает
    res = analyze(base(meta={'fields': 'passport:string|sensitive',
                             'goal': 'retention 5 лет, маскирование в логах'},
                       steps=[step(1, 'a', 'S', timeout=100, idem='key')]))
    assert 'sensitive_data_policy' not in rules_fired(res)
    # нагрузка ниже лимита партнёра — не срабатывает
    res2 = analyze(base(meta={'load_rps': 50, 'peak_factor': 2},
                        systems=[{'name': 'P', 'role': 'external', 'rate_limit_rps': 200}],
                        steps=[step(1, 'a', 'P', timeout=100, idem='key', retry='auto')]))
    assert 'capacity_vs_limit' not in rules_fired(res2)
    # без multi_tenant флага — не срабатывает
    res3 = analyze(base(steps=[step(1, 'q', 'Б', channel='queue', blocking='no',
                                    retry='auto', comp='DLQ', idem='key')]))
    assert 'multi_tenant_fairness' not in rules_fired(res3)
    # низкая нагрузка — stream-правила молчат
    assert 'stream_ingestion' not in rules_fired(res3)


def test_capacity_vs_limit_numbers():
    res = analyze(base(meta={'load_rps': 800, 'peak_factor': 5},
                       systems=[{'name': 'P', 'role': 'external', 'rate_limit_rps': 100}],
                       steps=[step(1, 'a', 'P', timeout=100, idem='key', retry='auto')]))
    f = [x for x in res['findings'] if x['rule'] == 'capacity_vs_limit'][0]
    assert '4000' in f['where'] and '100' in f['where'] and f['severity'] == 'critical'


# ------------------------------------------------- v6.1: новые правила и граф
def test_validate_cycle_and_self_dep():
    res = analyze(base(steps=[step(1, 'a', 'S', dep=2), step(2, 'b', 'S', dep=1)]))
    assert res['ok'] is False and any('икл' in e for e in res['errors'])
    res2 = analyze(base(steps=[step(1, 'a', 'S', dep=1)]))
    assert res2['ok'] is False and any('сам от себя' in e for e in res2['errors'])
    # валидный DAG ошибок не даёт
    res3 = analyze(base(steps=[step(1, 'a', 'S', timeout=100, idem='key'),
                               step(2, 'b', 'S2', dep=1, timeout=50)]))
    assert res3['ok'] is True


def test_latency_critical_path_beats_count():
    """Критический путь — по латентности: тяжёлая ветка не должна теряться."""
    m = build_graph(normalize(base(steps=[
        step(1, 'root', 'S1', timeout=50),
        step(2, 'fast', 'S2', dep=1, timeout=80),
        step(3, 'slow', 'S3', dep=1, timeout=900)])))
    assert [s['order'] for s in m['graph']['critical_path']] == [1, 3]
    assert m['graph']['critical_budget_ms'] == 950
    # и SLA-правило ловит скрытую тяжёлую ветку
    res = analyze(base(meta={'sla_ms': 500}, steps=[
        step(1, 'root', 'S1', timeout=50),
        step(2, 'fast', 'S2', dep=1, timeout=80),
        step(3, 'slow', 'S3', dep=1, timeout=900)]))
    assert 'sla_budget' in rules_fired(res)


def test_rule_timeout_inversion():
    res = analyze(base(steps=[step(1, 'p', 'S1', timeout=300),
                              step(2, 'c', 'S2', dep=1, timeout=800, writes='yes')]))
    f = [x for x in res['findings'] if x['rule'] == 'timeout_inversion'][0]
    assert f['severity'] == 'high'
    res2 = analyze(base(steps=[step(1, 'p', 'S1', timeout=800),
                               step(2, 'c', 'S2', dep=1, timeout=300)]))
    assert 'timeout_inversion' not in rules_fired(res2)


def test_rule_retry_amplification():
    sysx = [{'name': 'A', 'role': 'external'}, {'name': 'B', 'role': 'external'}]
    res = analyze(base(systems=sysx, steps=[
        step(1, 'A', 'A', timeout=500, retry='auto'),
        step(2, 'B', 'B', dep=1, timeout=500, retry='auto')]))
    assert 'retry_amplification' in rules_fired(res)
    # единственное retry-звено — не усиление
    res2 = analyze(base(systems=sysx, steps=[
        step(1, 'A', 'A', timeout=500, retry='auto'),
        step(2, 'B', 'B', dep=1, timeout=500)]))
    assert 'retry_amplification' not in rules_fired(res2)
    # circuit breaker заявлен — не срабатывает
    res3 = analyze(base(systems=sysx, steps=[
        step(1, 'A', 'A', timeout=500, retry='auto', dout='circuit breaker'),
        step(2, 'B', 'B', dep=1, timeout=500, retry='auto', dout='circuit breaker')]))
    assert 'retry_amplification' not in rules_fired(res3)


def test_rule_read_your_writes():
    res = analyze(base(meta={'customer_visible': 'yes'}, systems=[{'name': 'K', 'role': 'broker'}],
                       steps=[step(1, 'async write', 'S', channel='kafka', blocking='no',
                                   writes='yes', retry='auto', comp='DLQ'),
                              step(2, 'show', 'BFF', dep=1, timeout=200)]))
    assert 'read_your_writes' in rules_fired(res)
    # не клиентский сценарий — молчит
    res2 = analyze(base(systems=[{'name': 'K', 'role': 'broker'}],
                        steps=[step(1, 'async write', 'S', channel='kafka', blocking='no',
                                    writes='yes', retry='auto', comp='DLQ'),
                               step(2, 'show', 'BFF', dep=1, timeout=200)]))
    assert 'read_your_writes' not in rules_fired(res2)


def test_rule_blocking_in_async_handler():
    sysx = [{'name': 'Q', 'role': 'broker'}, {'name': 'Partner', 'role': 'external'}]
    res = analyze(base(systems=sysx, steps=[
        step(1, 'enqueue', 'Q', channel='queue', timeout=50),
        step(2, 'worker', 'W', channel='queue', blocking='no', dep=1, retry='auto',
             comp='DLQ', idem='key'),
        step(3, 'call partner', 'Partner', dep=2, timeout=3000)]))
    assert 'blocking_in_async_handler' in rules_fired(res)
    # внешнего блокирующего ребёнка нет — молчит
    res2 = analyze(base(systems=[{'name': 'Q', 'role': 'broker'}], steps=[
        step(1, 'enqueue', 'Q', channel='queue', timeout=50),
        step(2, 'worker', 'W', channel='queue', blocking='no', dep=1, retry='auto',
             comp='DLQ', idem='key', writes='yes')]))
    assert 'blocking_in_async_handler' not in rules_fired(res2)


def test_rule_no_correlation_id():
    res = analyze(base(systems=[{'name': 'K', 'role': 'broker'}], steps=[
        step(1, 'create', 'A', writes='yes', idem='key', timeout=200),
        step(2, 'pay', 'B', dep=1, timeout=300),
        step(3, 'notify', 'K', channel='kafka', blocking='no', dep=2, retry='auto', comp='DLQ')]))
    assert 'no_correlation_id' in rules_fired(res)
    # correlationId упомянут — молчит
    res2 = analyze(base(systems=[{'name': 'K', 'role': 'broker'}], steps=[
        step(1, 'create', 'A', writes='yes', idem='key', timeout=200, dout='correlationId'),
        step(2, 'pay', 'B', dep=1, timeout=300),
        step(3, 'notify', 'K', channel='kafka', blocking='no', dep=2, retry='auto', comp='DLQ')]))
    assert 'no_correlation_id' not in rules_fired(res2)


def test_rule_unbounded_growth():
    res = analyze(base(systems=[{'name': 'K', 'role': 'broker'}], steps=[
        step(1, 'save', 'S', writes='yes', idem='key', timeout=200),
        step(2, 'publish', 'S', channel='kafka', dep=1, retry='auto', comp='outbox')]))
    assert 'unbounded_growth' in rules_fired(res)
    res2 = analyze(base(systems=[{'name': 'K', 'role': 'broker'}], steps=[
        step(1, 'save', 'S', writes='yes', idem='key', timeout=200),
        step(2, 'publish', 'S', channel='kafka', dep=1, retry='auto',
             comp='outbox', dout='retention 90 дней, партиционирование по дате')]))
    assert 'unbounded_growth' not in rules_fired(res2)


# ------------------------------------------------- v6.2: fan-in / DAG и правила
def test_multi_parent_join_graph():
    """depends_on списком -> join с несколькими родителями; латентность = max ветви."""
    m = build_graph(normalize(base(steps=[
        step(1, 'root', 'BFF', timeout=50),
        step(2, 'ветвь A', 'A', dep=1, timeout=80),
        step(3, 'ветвь B', 'B', dep=1, timeout=400),
        {'order': 4, 'name': 'собрать', 'system': 'BFF', 'channel': 'rest',
         'blocking': 'yes', 'timeout_ms': 30, 'depends_on': [2, 3]}])))
    g = m['graph']
    join = g['by_order'][4]
    assert join['is_join'] and set(join['deps']) == {2, 3}
    # критический путь идёт через медленную ветвь B: 50+400+30 = 480
    assert g['critical_budget_ms'] == 480
    assert [s['order'] for s in g['critical_path']] == [1, 3, 4]
    assert g['joins'] and g['joins'][0]['order'] == 4


def test_csv_deps_backward_compatible():
    """Строка '2,3' тоже задаёт двух родителей; одиночный int — как раньше."""
    m = normalize(base(steps=[step(1, 'a', 'S'), step(2, 'b', 'S'),
                              {'order': 3, 'name': 'j', 'system': 'S', 'depends_on': '1,2'}]))
    assert m['steps'][2]['deps'] == [1, 2] and m['steps'][2]['depends_on'] == 1


def test_rule_fanin_partial_failure():
    sysx = [{'name': 'Ext', 'role': 'external'}]
    res = analyze(base(meta={'customer_visible': 'yes', 'sla_ms': 400}, systems=sysx, steps=[
        step(1, 'старт', 'BFF', timeout=30),
        step(2, 'свой источник', 'CRM', dep=1, timeout=100),
        step(3, 'внешний источник', 'Ext', dep=1, timeout=300),
        {'order': 4, 'name': 'собрать карточку', 'system': 'BFF', 'channel': 'rest',
         'blocking': 'yes', 'timeout_ms': 20, 'depends_on': [2, 3]}]))
    assert 'fanin_partial_failure' in rules_fired(res)
    assert any(p['id'] == 'partial_response' for p in res['patterns'])
    # та же агрегация, но с заявленной политикой partial response — молчит
    res2 = analyze(base(meta={'customer_visible': 'yes'}, systems=sysx, steps=[
        step(1, 'старт', 'BFF', timeout=30),
        step(2, 'свой источник', 'CRM', dep=1, timeout=100),
        step(3, 'внешний источник', 'Ext', dep=1, timeout=300),
        {'order': 4, 'name': 'собрать', 'system': 'BFF', 'channel': 'rest',
         'blocking': 'yes', 'timeout_ms': 20, 'depends_on': [2, 3],
         'data_out': 'partial response, таймаут на ветвь, деградация'}]))
    assert 'fanin_partial_failure' not in rules_fired(res2)


def test_rule_contract_versioning():
    sysx = [{'name': 'Kafka', 'role': 'broker'}]
    res = analyze(base(systems=sysx, steps=[
        step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
        step(2, 'в Kafka', 'Kafka', channel='kafka', dep=1, retry='auto', comp='outbox'),
        step(3, 'потребить и обновить', 'CRM', channel='kafka', blocking='no', dep=2,
             retry='auto', comp='DLQ', idem='key')]))
    assert 'contract_versioning' in rules_fired(res)
    res2 = analyze(base(systems=sysx, steps=[
        step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
        step(2, 'в Kafka', 'Kafka', channel='kafka', dep=1, retry='auto',
             comp='outbox', dout='avro schema registry, обратная совместимость'),
        step(3, 'потребить', 'CRM', channel='kafka', blocking='no', dep=2,
             retry='auto', comp='DLQ', idem='key')]))
    assert 'contract_versioning' not in rules_fired(res2)


def test_rule_hot_read_no_cache():
    sysx = [{'name': 'Источник', 'role': 'external'}]
    res = analyze(base(meta={'read_freq': 'very_high', 'customer_visible': 'yes', 'sla_ms': 300},
                       systems=sysx,
                       steps=[step(1, 'читать профиль', 'Источник', timeout=200)]))
    assert 'hot_read_no_cache' in rules_fired(res)
    # кэш заявлен — молчит
    res2 = analyze(base(meta={'read_freq': 'very_high', 'customer_visible': 'yes'},
                        systems=sysx,
                        steps=[step(1, 'читать профиль из кэша', 'Источник', timeout=200,
                                    din='cache TTL 60s')]))
    assert 'hot_read_no_cache' not in rules_fired(res2)
    # обычная частота чтения — молчит
    res3 = analyze(base(meta={'read_freq': 'medium', 'customer_visible': 'yes'},
                        systems=sysx, steps=[step(1, 'читать', 'Источник', timeout=200)]))
    assert 'hot_read_no_cache' not in rules_fired(res3)




# ------------------------------------------------------------ v6.3 quality model
def test_rule_event_core_fields_and_negative_case():
    sysx = [{'name': 'Kafka', 'role': 'broker'}]
    res = analyze(base(systems=sysx, steps=[
        step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
        step(2, 'опубликовать', 'Kafka', channel='kafka', dep=1, retry='auto', comp='outbox'),
        step(3, 'потребить', 'CRM', channel='kafka', blocking='no', dep=2,
             retry='auto', comp='DLQ', idem='key')]))
    assert 'event_core_fields' in rules_fired(res)
    res2 = analyze(base(systems=sysx, steps=[
        step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
        step(2, 'опубликовать', 'Kafka', channel='kafka', dep=1, retry='auto', comp='outbox',
             dout='schema version, eventId, eventType, eventVersion, aggregateId orderId, occurredAt, correlationId'),
        step(3, 'потребить', 'CRM', channel='kafka', blocking='no', dep=2,
             retry='auto', comp='DLQ replay', idem='key')]))
    assert 'event_core_fields' not in rules_fired(res2)


def test_completeness_check_finds_missing_inputs():
    sysx = [{'name': 'Kafka', 'role': 'broker'}]
    res = analyze(base(systems=sysx, steps=[
        step(1, 'создать', 'Банк', writes='yes', idem='key', timeout=200),
        step(2, 'статус в топик', 'Kafka', channel='kafka', blocking='no', dep=1,
             retry='auto')]))
    comp = res['completeness']
    assert comp['score_pct'] < 100
    questions = ' '.join(i['question'] for i in comp['missing'])
    assert 'статусы' in questions.lower() or 'статус' in questions.lower()
    assert 'schema' in questions.lower() or 'схема' in questions.lower()
    assert 'correlation' in questions.lower()


def test_quality_gates_and_architecture_checklist_are_returned():
    res = analyze(base(meta={'customer_visible': 'yes', 'sla_ms': 500},
                       systems=[{'name': 'Ext', 'role': 'external'}],
                       steps=[step(1, 'принять', 'API'),
                              step(2, 'вызвать партнера', 'Ext', dep=1, timeout=2000,
                                   retry='auto', writes='yes')]))
    assert 'quality_gates' in res and 'checklist' in res and 'alternatives' in res
    assert res['quality_gates']['overall'] in {'fail', 'warn'}
    assert any('timeout' in i['title'].lower() or 'retry' in i['title'].lower()
               for i in res['checklist']['items'])
    assert len(res['alternatives']) == 3


def test_project_artifacts_in_report():
    res = analyze(base(meta={'name': 'Reverse status', 'entity': 'Application'},
                       systems=[{'name': 'Kafka', 'role': 'broker'}],
                       steps=[step(1, 'создать заявку', 'Банк', writes='yes', idem='key', timeout=100),
                              step(2, 'опубликовать статус', 'Kafka', channel='kafka', dep=1,
                                   retry='auto', comp='outbox DLQ replay',
                                   dout='schema version, eventId, eventType, eventVersion, aggregateId applicationId, occurredAt, correlationId')]))
    md = markdown_report(res)
    assert 'Проверка готовности к production' in md
    assert 'Обязательный архитектурный чек-лист' in md
    assert 'Варианты архитектурного решения' in md
    assert 'Definition of Done' in md
    assert 'Черновик контракта события' in md


def test_async_reconciliation_and_observability_rules():
    sysx = [{'name': 'Kafka', 'role': 'broker'}]
    res = analyze(base(meta={'regulatory': 'yes', 'statuses': 'CREATED, DONE'}, systems=sysx, steps=[
        step(1, 'принять документ', 'Банк', writes='yes', idem='key', timeout=200),
        step(2, 'передать событие', 'Kafka', channel='kafka', blocking='no', dep=1,
             retry='auto', comp='DLQ')]))
    fired = rules_fired(res)
    assert 'async_reconciliation_missing' in fired
    assert 'observability_missing' in fired
    res2 = analyze(base(meta={'regulatory': 'yes', 'statuses': 'CREATED, DONE',
                              'goal': 'есть audit, reconciliation-сверка, metrics dashboard, alert DLQ'},
                        systems=sysx, steps=[
        step(1, 'принять документ', 'Банк', writes='yes', idem='key', timeout=200,
             dout='audit evidence'),
        step(2, 'передать событие', 'Kafka', channel='kafka', blocking='no', dep=1,
             retry='auto', comp='DLQ replay')]))
    fired2 = rules_fired(res2)
    assert 'async_reconciliation_missing' not in fired2
    assert 'observability_missing' not in fired2


def test_russian_text_refactor_is_visible_in_outputs():
    """Пользовательский слой должен говорить полноценными русскими формулировками."""
    res = analyze(base(meta={'name': 'Проверка текста', 'entity': 'Application',
                             'customer_visible': 'yes', 'sla_ms': 500},
                       systems=[{'name': 'Kafka', 'role': 'broker'},
                                {'name': 'Partner', 'role': 'external'}],
                       steps=[step(1, 'создать заявку', 'Банк', writes='yes', idem='key', timeout=100),
                              step(2, 'отправить статус', 'Kafka', channel='kafka', dep=1,
                                   retry='auto', comp='outbox DLQ replay'),
                              step(3, 'вызвать партнёра', 'Partner', dep=2, timeout=1000)]))
    md = markdown_report(res)
    assert 'Почему это важно' in md
    assert 'Что нужно сделать' in md
    assert 'Обязательный архитектурный чек-лист' in md
    assert 'Какие вводные нужно уточнить' in md
    assert 'production-readiness:' not in md
    assert all(f['title'].endswith('.') for f in res['findings'])
    assert all(i['title'].endswith('.') for i in res['checklist']['items'])


def test_finding_groups_reduce_repeated_findings_in_report():
    """Один класс риска на многих шагах должен отображаться сгруппированно."""
    steps = [
        step(1, 'записать A', 'S1', retry='auto', writes='yes'),
        step(2, 'записать B', 'S2', retry='auto', writes='yes', dep=1),
        step(3, 'записать C', 'S3', retry='auto', writes='yes', dep=2),
    ]
    res = analyze(base(meta={'money': 'direct'}, steps=steps))
    raw = [f for f in res['findings'] if f['rule'] == 'retry_without_idempotency']
    grouped = [g for g in res['finding_groups'] if g['rule'] == 'retry_without_idempotency']
    assert len(raw) == 3
    assert len(grouped) == 1
    assert grouped[0]['count'] == 3
    md = markdown_report(res)
    assert 'затронуто мест: 3' in md
    assert md.count('### Критично') >= 1 and 'Затронутые места:' in md



def test_composite_key_for_universal_dispatcher():
    res = analyze(base(
        meta={
            'name': 'Универсальный докатчик',
            'entity': 'DispatchOperation',
            'goal': 'универсальный докатчик отправляет запросы в систему А и систему Б; поиск выполняется по operUid',
            'fields': 'operUid:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed',
            'lookup_keys': 'operUid',
        },
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
        steps=[step(1, 'отправить в систему А', 'Система А', retry='auto', idem='key'),
               step(2, 'отправить в систему Б с тем же operUid', 'Система Б', retry='auto', idem='key', dep=1)]))
    assert 'ambiguous_composite_business_key' in rules_fired(res)
    assert any(p['id'] == 'composite_business_key' for p in res['patterns'])
    md = markdown_report(res)
    assert 'operUid + operationType' in md
    assert 'Одинаковый operUid для разных типов операций' in md


def test_development_scenario_is_generated():
    res = analyze(base(meta={'name': 'Сценарий', 'entity': 'Order', 'statuses': 'CREATED, DONE'},
                       systems=[{'name': 'Kafka', 'role': 'broker'}, {'name': 'Partner', 'role': 'external'}],
                       steps=[step(1, 'создать заказ', 'Orders', writes='yes', idem='key', timeout=100),
                              step(2, 'публиковать событие', 'Kafka', channel='kafka', blocking='no', retry='auto', comp='DLQ replay', dep=1),
                              step(3, 'вызвать партнёра', 'Partner', dep=2, timeout=500, retry='auto', idem='key')]))
    sc = res.get('scenario')
    assert sc and len(sc['main_flow']) == 3
    assert sc['alternative_flows']
    md = markdown_report(res)
    assert 'Сценарная основа для дальнейшей разработки' in md
    assert 'Основной сценарий' in md
    assert 'Альтернативные сценарии' in md



def test_detail_radar_anti_forgetting_matrix():
    res = analyze(base(
        meta={
            'name': 'Сложная интеграция с мелкими деталями',
            'entity': 'Request',
            'customer_visible': 'yes',
            'sla_ms': 500,
            'lookup_keys': 'requestId',
            'goal': 'универсальный адаптер отправляет запросы в несколько внешних систем',
        },
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
        steps=[step(1, 'создать запрос', 'Core', writes='yes', retry='auto'),
               step(2, 'отправить в систему А', 'Система А', dep=1, retry='auto'),
               step(3, 'отправить в систему Б', 'Система Б', dep=1, retry='auto')]))
    radar = res.get('detail_radar')
    assert radar and radar['probes']
    text = ' '.join(p['title'] + ' ' + p['question'] + ' ' + p['how'] for p in radar['probes'])
    assert 'область уникальности' in text.lower()
    assert 'SELECT' in text or 'UPSERT' in text
    md = markdown_report(res)
    assert 'Матрица деталей, которые нельзя забыть' in md
    assert 'Идентичность и ключи' in md


def test_generic_identifier_scope_ambiguity():
    res = analyze(base(
        meta={'name': 'Общий адаптер', 'entity': 'ExternalRequest',
              'lookup_keys': 'requestId',
              'goal': 'общий сервис используется несколькими системами; один requestId может встречаться в разных направлениях'},
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
        steps=[step(1, 'запрос в А', 'Система А', retry='auto', idem='key'),
               step(2, 'запрос в Б', 'Система Б', retry='auto', idem='key', dep=1)]))
    assert 'generic_identifier_scope_ambiguity' in rules_fired(res)
    # Если scope указан явно, правило не должно шуметь.
    res2 = analyze(base(
        meta={'name': 'Общий адаптер', 'entity': 'ExternalRequest',
              'lookup_keys': 'requestId, operationType, targetSystem',
              'goal': 'общий сервис используется несколькими системами'},
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
        steps=[step(1, 'запрос в А', 'Система А'), step(2, 'запрос в Б', 'Система Б', dep=1)]))
    assert 'generic_identifier_scope_ambiguity' not in rules_fired(res2)


def test_universal_invariant_catalog_v69_is_applied():
    res = analyze(base(
        meta={'name': 'Каталог инвариантов', 'entity': 'Request', 'customer_visible': 'yes',
              'money': 'direct', 'regulatory': 'yes', 'load_rps': 800, 'peak_factor': 3,
              'fields': 'requestId:string|required, phone:string|sensitive',
              'lookup_keys': 'requestId',
              'goal': 'клиентский процесс с деньгами, событиями, внешним провайдером и витриной'},
        systems=[{'name': 'Kafka', 'role': 'broker'}, {'name': 'Provider', 'role': 'external'}, {'name': 'DWH', 'role': 'analytics'}],
        steps=[step(1, 'создать заявку', 'Core', writes='yes', retry='auto'),
               step(2, 'опубликовать событие', 'Kafka', channel='kafka', blocking='no', retry='auto', dep=1),
               step(3, 'вызвать провайдера', 'Provider', dep=2, retry='auto', timeout=300),
               step(4, 'выгрузить в DWH', 'DWH', channel='cdc', blocking='no', dep=1)]))
    radar = res.get('detail_radar') or {}
    stats = radar.get('catalog_stats') or {}
    assert stats.get('total', 0) >= 100
    assert stats.get('applicable', 0) >= 60
    text = ' '.join(p['area'] + ' ' + p['title'] for p in radar.get('probes', []))
    assert 'Асинхронность и брокеры' in text
    assert 'Безопасность' in text
    assert 'Комплаенс и аудит' in text
    assert 'Тестирование' in text



def test_checklist_fails_when_generic_lookup_key_has_no_scope():
    res = analyze(base(
        meta={'name': 'Общий адаптер', 'entity': 'ExternalRequest',
              'lookup_keys': 'requestId',
              'fields': 'requestId:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed, tenantId:string|indexed',
              'multi_tenant': 'yes',
              'goal': 'общий адаптер используется несколькими системами; один requestId может повторяться в разных направлениях'},
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}, {'name': 'Сервис', 'role': 'internal'}],
        steps=[step(1, 'запрос в А', 'Система А', retry='auto', idem='key'),
               step(2, 'запрос в Б', 'Система Б', retry='auto', idem='key', dep=1)]))
    assert 'generic_identifier_scope_ambiguity' in rules_fired(res)
    key_items = [i for i in res['checklist']['items'] if 'Ключ поиска' in i['title']]
    assert key_items and key_items[0]['status'] == 'fail'
    assert 'requestId + operationType + targetSystem' in key_items[0]['fix']

    res2 = analyze(base(
        meta={'name': 'Общий адаптер', 'entity': 'ExternalRequest',
              'lookup_keys': 'requestId, operationType, targetSystem, tenantId',
              'fields': 'requestId:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed, tenantId:string|indexed',
              'multi_tenant': 'yes',
              'goal': 'общий адаптер используется несколькими системами'},
        systems=[{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
        steps=[step(1, 'запрос в А', 'Система А'), step(2, 'запрос в Б', 'Система Б', dep=1)]))
    key_items2 = [i for i in res2['checklist']['items'] if 'Ключ поиска' in i['title']]
    assert key_items2 and key_items2[0]['status'] == 'ok'


def test_development_scenario_has_channel_specific_failure_handling():
    res = analyze(base(
        meta={'name': 'Каналы ошибок', 'entity': 'Request'},
        systems=[{'name': 'Kafka', 'role': 'broker'}, {'name': 'Partner', 'role': 'external'}, {'name': 'PSP', 'role': 'external'}],
        steps=[step(1, 'вызвать партнёра', 'Partner', channel='rest', timeout=300, retry='auto'),
               step(2, 'прочитать событие', 'Kafka', channel='kafka', blocking='no', retry='auto', dep=1),
               step(3, 'принять callback', 'PSP', channel='webhook', blocking='no', retry='auto', dep=2),
               step(4, 'записать статус', 'DB', channel='db', writes='yes', dep=3)]))
    flows = {x['channel']: x['failure_handling'] for x in res['scenario']['main_flow']}
    assert 'circuit breaker' in flows['rest'] and '429' in flows['rest']
    assert 'Offset/ack' in flows['kafka'] and 'DLQ' in flows['kafka']
    assert 'подписи' in flows['webhook'] and 'Inbox' in flows['webhook']
    assert 'транзакция' in flows['db'] and 'UNIQUE' in flows['db']
    assert all('Нужно явно описать поведение при ошибке: retry, DLQ, компенсация или ручной разбор' not in v for v in flows.values())

# ------------------------------------------------------------ v7.1 invariant reference UI
def test_invariant_reference_page_contains_all_items_and_examples():
    import ui
    from invariant_catalog import INVARIANT_CATALOG
    html = ui.invariant_reference_page()
    assert 'Справочник архитектурных инвариантов' in html
    assert 'Что проверить' in html and 'Почему это важно' in html and 'Как закрыть' in html and 'Пример' in html
    assert 'filterInvariants' in html
    assert html.count('class="refcard"') == len(INVARIANT_CATALOG)
    assert 'operUid' in html or 'requestId' in html


def test_http_invariant_reference_page():
    import app as appmod
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(('127.0.0.1', 0), appmod.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        html = urllib.request.urlopen(f'http://127.0.0.1:{port}/invariants').read().decode()
        assert 'Справочник архитектурных инвариантов' in html
        assert 'refcard' in html and 'Вернуться в конструктор процесса' in html
        index = urllib.request.urlopen(f'http://127.0.0.1:{port}/').read().decode()
        assert '/invariants' in index and 'Открыть справочник инвариантов' in index
    finally:
        srv.shutdown()




def test_ui_v73_process_designer_convenience_elements():
    import ui
    html = ui.form_page()
    assert 'Проектирование:' in html
    assert '+ REST-вызов' in html and '+ Kafka-событие' in html and '+ запись в БД' in html
    assert 'безопасные настройки всем шагам' in html
    assert 'Что ещё заполнить, чтобы разбор был полезнее' in html or 'liveGuide' in html
    assert 'Краткая сводка ввода' in html
    assert 'requestId + operationType + targetSystem' in html
    assert 'suggestBasics' in html and 'applySafeDefaultsAll' in html


def test_http_index_contains_v73_process_designer_elements():
    import app as appmod
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(('127.0.0.1', 0), appmod.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        html = urllib.request.urlopen(f'http://127.0.0.1:{port}/').read().decode()
        assert 'Проектирование:' in html
        assert 'Быстро добавить типовой шаг' in html
        assert 'Краткая сводка ввода' in html
    finally:
        srv.shutdown()



def test_invariant_reference_v74_has_full_learning_context():
    import ui
    from invariant_catalog import INVARIANT_CATALOG
    html = ui.invariant_reference_page()
    for label in ['Когда использовать', 'На каком этапе процесса', 'Последствия, если не соблюдать', 'Эталонный кейс', 'Как проверить на практике', 'Пример ошибки']:
        assert label in html
    assert html.count('class="refcard"') == len(INVARIANT_CATALOG)
    assert 'requestId + operationType + targetSystem + tenantId' in html
    assert 'Если правило нарушить' not in html or 'Последствия' in html


def test_invariant_reference_v74_search_index_includes_context():
    import ui
    html = ui.invariant_reference_page()
    assert 'data-search=' in html
    assert 'cutover' in html and 'replay' in html and 'contract tests' in html
    assert 'На каком этапе проектирования' in html or 'На каком этапе процесса' in html


def test_invariant_reference_v75_has_expanded_plain_language_explanations():
    import ui
    from invariant_catalog import INVARIANT_CATALOG
    html = ui.invariant_reference_page()
    for label in ['Простыми словами', 'Как выглядит правильное решение', 'Вопросы для ревью']:
        assert label in html
    assert html.count('class="refbox reflead"') == len(INVARIANT_CATALOG)
    assert html.count('class="refbox okbox"') == len(INVARIANT_CATALOG)
    assert 'Любой id кажется уникальным' in html
    assert 'контракт описан в OpenAPI' in html


def test_invariant_reference_v75_search_index_includes_expanded_explanations():
    import ui
    html = ui.invariant_reference_page()
    assert 'data-search=' in html
    assert 'review' in html.lower() or 'ревью' in html.lower()
    assert 'Нормальное состояние' in html


def test_design_patterns_reference_page_has_all_cards_and_expand_contract():
    import ui
    from design_patterns import DESIGN_PATTERN_CATALOG
    html = ui.design_pattern_reference_page()
    assert 'Список шаблонов проектирования' in html
    assert html.count('class="refcard pattern-card"') == len(DESIGN_PATTERN_CATALOG)
    for label in ['Что это за паттерн', 'Для чего нужен', 'На каких этапах', 'Что будет, если не использовать']:
        assert label in html
    assert 'Expand / Contract migration' in html
    assert 'Transactional Outbox' in html
    assert 'partition_by_aggregate' in html


def test_http_patterns_reference_page():
    import app as appmod
    from http.server import ThreadingHTTPServer
    import threading
    import urllib.request
    srv = ThreadingHTTPServer(('127.0.0.1', 0), appmod.Handler)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        html = urllib.request.urlopen(f'http://127.0.0.1:{port}/patterns').read().decode()
        assert 'Шаблоны проектирования интеграций' in html
        assert 'Expand / Contract migration' in html
        assert 'filterPatterns' in html
    finally:
        srv.shutdown()

# ------------------------------------------------------------ runner
def main():
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith('test_') and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f'  ok   {name}')
        except AssertionError as e:
            failed += 1
            print(f'  FAIL {name}: {e}')
        except Exception as e:  # noqa: BLE001 — нужен полный отчёт по падению
            failed += 1
            print(f'  ERR  {name}: {type(e).__name__}: {e}')
    total = len(tests)
    print(f'\n{total - failed}/{total} passed' + (f', {failed} failed' if failed else ''))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
