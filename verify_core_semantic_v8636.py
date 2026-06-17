#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deep core semantic regression for v8.6.36."""
import json, random, traceback
import engine


def fired(res):
    return {f['rule'] for f in res.get('findings', [])}

checks = []

# 1. Invalid dependency graph coverage: duplicate, missing, self, multi-parent cycle.
invalid_payloads = [
    ({'meta': {}, 'systems': [], 'steps': []}, 'Добавьте хотя бы один шаг'),
    ({'meta': {}, 'systems': [], 'steps': [
        {'order': 1, 'name': 'A', 'system': 'S'}, {'order': 1, 'name': 'B', 'system': 'S'}]}, 'Дублируется'),
    ({'meta': {}, 'systems': [], 'steps': [
        {'order': 1, 'name': 'A', 'system': 'S', 'depends_on': '2'}]}, 'несуществующего'),
    ({'meta': {}, 'systems': [], 'steps': [
        {'order': 1, 'name': 'A', 'system': 'S', 'depends_on': '1'}]}, 'зависит сам'),
    ({'meta': {}, 'systems': [], 'steps': [
        {'order': 1, 'name': 'A', 'system': 'S', 'depends_on': '2,3'},
        {'order': 2, 'name': 'B', 'system': 'S'},
        {'order': 3, 'name': 'C', 'system': 'S', 'depends_on': '1'},
    ]}, 'Циклическая зависимость'),
]
for payload, token in invalid_payloads:
    res = engine.analyze(payload)
    assert res.get('ok') is False, res
    assert any(token in e for e in res.get('errors', [])), (token, res)
checks.append('invalid_graph_guards')

# 2. Broker semantic consumer: source_system is broker, system is consumer.
p = {
    'meta': {'name': 'Broker semantic consumer', 'entity': 'Order', 'load_rps': 1000, 'peak_factor': 2},
    'systems': [{'name': 'Producer', 'role': 'internal'}, {'name': 'Kafka', 'role': 'broker'}, {'name': 'Consumer', 'role': 'internal'}],
    'steps': [
        {'order': 1, 'name': 'Producer publishes OrderCreated', 'system': 'Producer', 'source_system': 'Producer', 'target_system': 'Kafka', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'compensation': 'outbox'},
        {'order': 2, 'name': 'Consumer reads OrderCreated from Kafka', 'system': 'Consumer', 'source_system': 'Kafka', 'target_system': 'Consumer', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '1', 'data_in': 'filter common topic', 'compensation': 'DLQ replay'},
    ],
}
r = engine.analyze(p)
assert r['ok'] is True
steps = {s['order']: s for s in r['model']['steps']}
assert engine._is_consumption(r['model'], steps[1]) is False
assert engine._is_consumption(r['model'], steps[2]) is True
assert {'contract_versioning', 'stream_consumer_controls'} <= fired(r), fired(r)
checks.append('broker_consumer_semantics')

# 3. Current UI style outbound dependency: executor is our service, target is external.
p = {
    'meta': {'name': 'Target dependency semantics', 'entity': 'Request', 'load_rps': 500, 'peak_factor': 2, 'read_freq': 'very_high', 'customer_visible': 'yes', 'sla_ms': 500},
    'systems': [{'name': 'Service', 'role': 'internal'}, {'name': 'Partner', 'role': 'external', 'stability': 'limited', 'rate_limit_rps': 100}],
    'steps': [{'order': 1, 'name': 'Service reads/calls limited partner', 'system': 'Service', 'source_system': 'Service', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 500}],
}
r = engine.analyze(p)
assert {'external_blocking', 'capacity_vs_limit', 'unstable_dependency', 'hot_read_no_cache'} <= fired(r), fired(r)
checks.append('target_endpoint_risks')

# 4. Async handler blocks on external target.
p = {
    'meta': {'name': 'Async handler external target', 'entity': 'Order'},
    'systems': [{'name': 'Kafka', 'role': 'broker'}, {'name': 'Worker', 'role': 'internal'}, {'name': 'Partner', 'role': 'external'}],
    'steps': [
        {'order': 1, 'name': 'Worker consumes event', 'system': 'Worker', 'source_system': 'Kafka', 'target_system': 'Worker', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'compensation': 'DLQ replay'},
        {'order': 2, 'name': 'Worker calls partner', 'system': 'Worker', 'source_system': 'Worker', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 3000, 'depends_on': '1'},
    ],
}
r = engine.analyze(p)
assert {'blocking_in_async_handler', 'external_blocking'} <= fired(r), fired(r)
checks.append('async_handler_external_target')

# 5. Fan-in with external target branch.
p = {
    'meta': {'name': 'Join external target', 'entity': 'Profile'},
    'systems': [{'name': 'BFF', 'role': 'internal'}, {'name': 'Partner', 'role': 'external'}, {'name': 'Internal', 'role': 'internal'}],
    'steps': [
        {'order': 1, 'name': 'start', 'system': 'BFF', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 50},
        {'order': 2, 'name': 'call partner branch', 'system': 'BFF', 'source_system': 'BFF', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 300, 'depends_on': '1'},
        {'order': 3, 'name': 'call internal branch', 'system': 'BFF', 'source_system': 'BFF', 'target_system': 'Internal', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 200, 'depends_on': '1'},
        {'order': 4, 'name': 'aggregate branches', 'system': 'BFF', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 30, 'depends_on': '2,3'},
    ],
}
r = engine.analyze(p)
assert 'fanin_partial_failure' in fired(r), fired(r)
checks.append('fanin_external_target')

# 6. Inbound external initiator must not be treated as our outbound external dependency.
p = {
    'meta': {'name': 'Inbound external initiator', 'entity': 'Request', 'customer_visible': 'yes', 'sla_ms': 300},
    'systems': [{'name': 'Partner', 'role': 'external', 'stability': 'limited', 'rate_limit_rps': 1}, {'name': 'Service', 'role': 'internal'}],
    'steps': [{'order': 1, 'name': 'Partner calls our webhook', 'system': 'Partner', 'source_system': 'Partner', 'target_system': 'Service', 'channel': 'webhook', 'blocking': 'yes', 'timeout_ms': 100}],
}
r = engine.analyze(p)
assert 'external_blocking' not in fired(r), fired(r)
assert 'capacity_vs_limit' not in fired(r), fired(r)
checks.append('inbound_not_outbound')

# 7. Random robustness smoke: no exceptions; ok models are valid DAGs.
channels = sorted(engine.ALL_CHANNELS)
roles = ['internal', 'external', 'broker', 'db', 'legacy', 'analytics', 'security', 'audit', 'observability']
random.seed(8636)
for k in range(1500):
    systems = [{'name': f'S{i}', 'role': random.choice(roles), 'criticality': random.choice(['low','medium','high','critical']), 'stability': random.choice(['stable','unknown','unstable','limited']), 'rate_limit_rps': random.choice([0, 10, 100, 1000])} for i in range(random.randint(1, 10))]
    steps = []
    for i in range(1, random.randint(1, 35) + 1):
        src = random.choice(systems)['name']; tgt = random.choice(systems)['name']; sysname = random.choice([src, tgt, random.choice(systems)['name']])
        deps = [] if i == 1 or random.random() < 0.25 else random.sample(range(1, i), random.randint(1, min(3, i-1)))
        steps.append({'order': i, 'name': f'Step {i}', 'system': sysname, 'source_system': src, 'target_system': tgt, 'channel': random.choice(channels), 'blocking': random.choice(['yes','no']), 'timeout_ms': random.choice([0,100,300,1000]), 'retry': random.choice(['none','auto','manual']), 'idempotency': random.choice(['none','key','natural']), 'writes_entity': random.choice(['yes','no']), 'depends_on': ','.join(map(str, deps)), 'data_in': random.choice(['','eventId aggregateId correlationId','filter common topic','operUid operationType']), 'data_out': random.choice(['','outbox','eventId eventType eventVersion aggregateId occurredAt correlationId','audit evidence']), 'compensation': random.choice(['','DLQ replay','partial response','circuit breaker fallback'])})
    payload = {'meta': {'name': 'random', 'entity': 'Entity', 'customer_visible': random.choice(['yes','no']), 'money': random.choice(['no','direct']), 'regulatory': random.choice(['yes','no']), 'sla_ms': random.choice([0,500,1000,5000]), 'read_freq': random.choice(['low','medium','high','very_high']), 'ordering': random.choice(['no','per_entity','global']), 'load_rps': random.choice([0,100,1000,5000]), 'peak_factor': random.choice([1,2,10]), 'fields': 'id:uuid|required|unique'}, 'systems': systems, 'steps': steps}
    res = engine.analyze(payload)
    assert 'ok' in res
    if res.get('ok'):
        orders = {s['order'] for s in res['model']['steps']}
        for s in res['model']['steps']:
            assert s['order'] not in s.get('deps', [])
            assert all(d in orders for d in s.get('deps', []))
            assert s['channel'] in engine.ALL_CHANNELS
        assert all(f.get('severity') in engine.SEVERITY_ORDER for f in res['findings'])
checks.append('random_robustness_1500')

print('CORE_SEMANTIC_v8636 ok:', ', '.join(checks))
