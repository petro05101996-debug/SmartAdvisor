#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""End-to-end core regression for semantic route model v8.6.37.

Covers source_system/system/target_system semantics, fan-in/fan-out, broker
publish/consume direction, outbound external dependency detection, validation
of cycles and report smoke generation.
"""
from __future__ import annotations
import random
import re
import time
import traceback
import sys

import engine
import report


def base_payload(steps, systems=None, meta=None):
    base_systems = [
        {'name': 'Client', 'role': 'external', 'criticality': 'medium', 'stability': 'stable'},
        {'name': 'API', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
        {'name': 'Service', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
        {'name': 'Worker', 'role': 'internal', 'criticality': 'medium', 'stability': 'stable'},
        {'name': 'DB', 'role': 'db', 'criticality': 'high', 'stability': 'stable'},
        {'name': 'Kafka', 'role': 'broker', 'criticality': 'high', 'stability': 'stable'},
        {'name': 'Rabbit', 'role': 'broker', 'criticality': 'high', 'stability': 'stable'},
        {'name': 'Partner', 'role': 'external', 'criticality': 'medium', 'stability': 'unstable', 'rate_limit_rps': 100},
        {'name': 'Legacy', 'role': 'legacy', 'criticality': 'medium', 'stability': 'limited', 'rate_limit_rps': 50},
        {'name': 'DWH', 'role': 'analytics', 'criticality': 'medium', 'stability': 'stable'},
    ]
    if systems:
        for s in systems:
            base_systems = [x for x in base_systems if x['name'] != s['name']]
            base_systems.append(s)
    m = {
        'name': 'Core E2E semantic route probe',
        'entity': 'Request',
        'goal': 'Проверить route semantics, correlationId и отчёт',
        'customer_visible': 'yes',
        'money': 'no',
        'sla_ms': '1000',
        'read_freq': 'medium',
        'ordering': 'no',
        'load_rps': '200',
        'peak_factor': '1',
        'statuses': 'NEW,DONE',
        'fields': 'requestId:string|required|unique, correlationId:string|required|indexed',
        'lookup_keys': 'requestId',
    }
    if meta:
        m.update(meta)
    normalized = []
    for i, step in enumerate(steps, 1):
        x = {
            'order': i,
            'name': f'Step {i}',
            'system': 'Service',
            'channel': 'rest',
            'blocking': 'yes',
            'timeout_ms': '100',
            'retry': 'none',
            'idempotency': 'key',
            'writes_entity': 'no',
            'depends_on': '',
        }
        x.update(step)
        normalized.append(x)
    return {'meta': m, 'systems': base_systems, 'steps': normalized}


def rules(result):
    return {f['rule'] for f in result.get('findings', [])}


def assert_case(name, steps, expect=(), absent=(), meta=None, report_smoke=False):
    result = engine.analyze(base_payload(steps, meta=meta))
    assert result.get('ok'), (name, result.get('errors'))
    got = rules(result)
    missing = set(expect) - got
    forbidden = set(absent) & got
    assert not missing and not forbidden, (name, 'missing', missing, 'forbidden', forbidden, 'got', sorted(got))
    if report_smoke:
        md = report.markdown_report(result)
        assert isinstance(md, str) and len(md) > 1000 and 'Архитектурный разбор' in md, name
    return result


def deterministic_cases():
    assert_case('fanin_acyclic', [
        {'name': 'Start', 'order': 1},
        {'name': 'Branch A', 'order': 2, 'depends_on': '1'},
        {'name': 'Branch B', 'order': 3, 'depends_on': '1'},
        {'name': 'Join', 'order': 4, 'depends_on': '2,3', 'channel': 'db', 'system': 'Service', 'target_system': 'DB', 'writes_entity': 'yes'},
    ], report_smoke=True)

    result = assert_case('inbound_external_not_external_blocking', [
        {'name': 'Client calls API', 'source_system': 'Client', 'system': 'Client', 'target_system': 'API', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100'},
        {'name': 'API calls SVC', 'source_system': 'API', 'system': 'API', 'target_system': 'Service', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '1'},
        {'name': 'SVC writes DB', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '2', 'writes_entity': 'yes'},
    ], expect={'sync_chain_depth'}, absent={'external_blocking', 'capacity_vs_limit', 'unstable_dependency'}, report_smoke=True)
    sync = [f for f in result['findings'] if f['rule'] == 'sync_chain_depth'][0]
    assert sync['severity'] == 'high', sync
    assert not result['model']['steps'][0]['external']

    assert_case('outbound_external_target_detected', [
        {'name': 'API calls partner', 'source_system': 'API', 'system': 'API', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '800'},
    ], expect={'external_blocking', 'unstable_dependency', 'capacity_vs_limit'}, meta={'load_rps': '200', 'peak_factor': '2'}, report_smoke=True)

    assert_case('legacy_target_detected', [
        {'name': 'Service calls legacy', 'source_system': 'Service', 'system': 'Service', 'target_system': 'Legacy', 'channel': 'soap', 'blocking': 'yes', 'timeout_ms': '700'},
    ], expect={'external_blocking', 'unstable_dependency', 'capacity_vs_limit'}, meta={'load_rps': '100', 'peak_factor': '1'})

    assert_case('publisher_to_kafka_dual_write', [
        {'name': 'Save entity', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'writes_entity': 'yes'},
        {'name': 'Publish event', 'source_system': 'Service', 'system': 'Service', 'target_system': 'Kafka', 'channel': 'kafka', 'blocking': 'no', 'depends_on': '1', 'retry': 'auto', 'idempotency': 'key'},
    ], expect={'dual_write'})

    assert_case('consumer_from_kafka_no_dual_publish', [
        {'name': 'Consumer reads event with filter from common topic', 'source_system': 'Kafka', 'system': 'Worker', 'target_system': 'Worker', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'data_in': 'filter common topic'},
        {'name': 'Consumer writes DB', 'source_system': 'Worker', 'system': 'Worker', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'depends_on': '1', 'writes_entity': 'yes'},
    ], expect={'stream_consumer_controls'}, absent={'dual_write'}, meta={'load_rps': '1000', 'peak_factor': '1'}, report_smoke=True)

    assert_case('consumer_from_rabbit', [
        {'name': 'Worker получает задачу из Rabbit', 'source_system': 'Rabbit', 'system': 'Worker', 'target_system': 'Worker', 'channel': 'rabbitmq', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'data_in': 'селективный consumer'},
    ], expect={'stream_consumer_controls'}, absent={'dual_write'}, meta={'load_rps': '1000', 'peak_factor': '1'})

    assert_case('old_parent_broker_consumption', [
        {'name': 'Kafka topic emits', 'system': 'Kafka', 'target_system': 'Kafka', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key'},
        {'name': 'Consumer reads from topic', 'system': 'Worker', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '1', 'data_in': 'filter'},
    ], expect={'stream_consumer_controls'}, absent={'dual_write'}, meta={'load_rps': '1000', 'peak_factor': '1'})

    assert_case('async_handler_blocks_external', [
        {'name': 'Consumer reads event', 'source_system': 'Kafka', 'system': 'Worker', 'target_system': 'Worker', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key'},
        {'name': 'Consumer calls partner synchronously', 'source_system': 'Worker', 'system': 'Worker', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '700', 'depends_on': '1'},
    ], expect={'blocking_in_async_handler', 'external_blocking', 'unstable_dependency'})

    assert_case('fanin_external_branch_no_policy', [
        {'name': 'Start', 'source_system': 'API', 'system': 'API', 'target_system': 'Service', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100'},
        {'name': 'Call partner A', 'source_system': 'Service', 'system': 'Service', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '400', 'depends_on': '1'},
        {'name': 'Local DB read', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '1'},
        {'name': 'Join results', 'source_system': 'Service', 'system': 'Service', 'target_system': 'API', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '2,3'},
    ], expect={'fanin_partial_failure'})

    assert_case('fanin_external_branch_with_policy', [
        {'name': 'Start', 'source_system': 'API', 'system': 'API', 'target_system': 'Service', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100'},
        {'name': 'Call partner A', 'source_system': 'Service', 'system': 'Service', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '400', 'depends_on': '1'},
        {'name': 'Local DB read', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '1'},
        {'name': 'Join results with partial fallback', 'source_system': 'Service', 'system': 'Service', 'target_system': 'API', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100', 'depends_on': '2,3', 'compensation': 'partial fallback, тайм-аут ветви, деградация'},
    ], absent={'fanin_partial_failure'})

    assert_case('analytics_target_core', [
        {'name': 'Write operational DWH synchronously', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DWH', 'channel': 'data_warehouse', 'blocking': 'yes', 'timeout_ms': '1000'},
    ], expect={'analytics_in_core'})

    assert_case('hot_read_target_db', [
        {'name': 'Read profile', 'source_system': 'API', 'system': 'API', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'writes_entity': 'no'},
    ], expect={'hot_read_no_cache'}, meta={'read_freq': 'very_high', 'sla_ms': '700'})

    assert_case('no_hot_read_for_write', [
        {'name': 'Save profile', 'source_system': 'API', 'system': 'API', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'writes_entity': 'yes'},
    ], absent={'hot_read_no_cache'}, meta={'read_freq': 'very_high', 'sla_ms': '700'})

    assert_case('analytics_nonblocking_ok', [
        {'name': 'Send to DWH async', 'source_system': 'Service', 'system': 'Service', 'target_system': 'DWH', 'channel': 'data_warehouse', 'blocking': 'no', 'timeout_ms': ''},
    ], absent={'analytics_in_core'})

    for name, steps in [
        ('cycle_second_dep', [{'order': 1, 'name': 'A', 'depends_on': '2,3'}, {'order': 2, 'name': 'B', 'depends_on': ''}, {'order': 3, 'name': 'C', 'depends_on': '1'}]),
        ('cycle_long', [{'order': 1, 'name': 'A', 'depends_on': '3'}, {'order': 2, 'name': 'B', 'depends_on': '1'}, {'order': 3, 'name': 'C', 'depends_on': '2'}]),
        ('self_dep', [{'order': 1, 'name': 'A', 'depends_on': '1'}]),
        ('missing_dep', [{'order': 1, 'name': 'A', 'depends_on': '99'}]),
    ]:
        result = engine.analyze(base_payload(steps))
        assert not result.get('ok'), (name, result)


def channel_matrix():
    # All channels must be accepted by normalize/analyze and must preserve sync/async classification.
    for ch in sorted(engine.ALL_CHANNELS):
        result = assert_case(f'channel_{ch}', [
            {'name': f'Channel {ch}', 'source_system': 'API', 'system': 'API', 'target_system': 'Service', 'channel': ch, 'blocking': 'yes' if ch in engine.SYNC_CHANNELS else 'no', 'timeout_ms': '100' if ch in engine.SYNC_CHANNELS else ''},
        ])
        step = result['model']['steps'][0]
        assert step['channel'] == ch
        assert step['sync'] == (ch in engine.SYNC_CHANNELS)

    # Broker publish/consume direction across all broker channels.
    for ch in sorted(engine.BROKER_CHANNELS):
        pub = assert_case(f'publish_{ch}', [
            {'name': f'Publish via {ch}', 'source_system': 'Service', 'system': 'Service', 'target_system': 'Kafka', 'channel': ch, 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key'},
        ])
        assert not engine._is_consumption(pub['model'], pub['model']['steps'][0])
        con = assert_case(f'consume_{ch}', [
            {'name': f'Consume via {ch}', 'source_system': 'Kafka', 'system': 'Worker', 'target_system': 'Worker', 'channel': ch, 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'data_in': 'filter common topic'},
        ], expect={'stream_consumer_controls'}, meta={'load_rps': '1000', 'peak_factor': '1'})
        assert engine._is_consumption(con['model'], con['model']['steps'][0])


def fuzz(seed=8637, count=1000):
    random.seed(seed)
    systems = [
        {'name': 'Client', 'role': 'external', 'criticality': 'medium', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'API', 'role': 'internal', 'criticality': 'high', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'Service', 'role': 'internal', 'criticality': 'high', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'Worker', 'role': 'internal', 'criticality': 'medium', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'DB', 'role': 'db', 'criticality': 'high', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'Kafka', 'role': 'broker', 'criticality': 'high', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'Rabbit', 'role': 'broker', 'criticality': 'high', 'stability': 'stable', 'rate_limit_rps': 0},
        {'name': 'Partner', 'role': 'external', 'criticality': 'medium', 'stability': 'unstable', 'rate_limit_rps': 50},
        {'name': 'Legacy', 'role': 'legacy', 'criticality': 'medium', 'stability': 'limited', 'rate_limit_rps': 50},
        {'name': 'DWH', 'role': 'analytics', 'criticality': 'medium', 'stability': 'stable', 'rate_limit_rps': 0},
    ]
    channels = list(engine.ALL_CHANNELS)
    patterns = ['inbound', 'outbound', 'internal', 'publish', 'consume', 'db', 'dwh', 'legacy']

    def make_payload(i, force_cycle=False):
        n = random.randint(1, 8)
        steps = []
        for order in range(1, n + 1):
            pattern = random.choice(patterns)
            if pattern == 'inbound':
                src, sysn, tgt, ch = 'Client', random.choice(['Client', 'API']), 'API', random.choice(['rest', 'api_gateway', 'webhook'])
            elif pattern == 'outbound':
                src, sysn, tgt, ch = 'Service', 'Service', 'Partner', random.choice(['rest', 'soap', 'grpc'])
            elif pattern == 'legacy':
                src, sysn, tgt, ch = 'Service', 'Service', 'Legacy', random.choice(['soap', 'rest'])
            elif pattern == 'publish':
                src, sysn, tgt, ch = 'Service', 'Service', random.choice(['Kafka', 'Rabbit']), random.choice(['kafka', 'rabbitmq', 'queue'])
            elif pattern == 'consume':
                src, sysn, tgt, ch = random.choice(['Kafka', 'Rabbit']), 'Worker', 'Worker', random.choice(['kafka', 'rabbitmq', 'queue'])
            elif pattern == 'db':
                src, sysn, tgt, ch = 'Service', 'Service', 'DB', random.choice(['db', 'read_replica', 'mongodb'])
            elif pattern == 'dwh':
                src, sysn, tgt, ch = 'Service', 'Service', 'DWH', random.choice(['data_warehouse', 'clickhouse', 'etl', 'batch'])
            else:
                src, sysn, tgt, ch = 'API', 'API', 'Service', random.choice(channels)
            deps = []
            if order > 1:
                deps = [d for d in range(1, order) if random.random() < 0.20]
                if not deps and random.random() < 0.70:
                    deps = [order - 1]
            blocking = 'yes' if (ch in engine.SYNC_CHANNELS or random.random() < 0.25) else 'no'
            steps.append({
                'order': order,
                'name': f'{pattern} step {order}',
                'source_system': src,
                'system': sysn,
                'target_system': tgt,
                'channel': ch,
                'blocking': blocking,
                'timeout_ms': str(random.choice([0, 50, 100, 200, 500, 1000])) if blocking == 'yes' else '',
                'retry': random.choice(['none', 'auto', 'manual']),
                'idempotency': random.choice(['none', 'key', 'natural']),
                'writes_entity': 'yes' if pattern == 'db' or (random.random() < 0.08 and pattern not in ('publish', 'consume')) else 'no',
                'depends_on': ','.join(map(str, deps)),
                'data_in': 'filter common topic' if pattern == 'consume' and random.random() < 0.70 else '',
                'compensation': random.choice(['', 'DLQ replay', 'Outbox Schema Registry DLQ replay', 'partial fallback деградация тайм-аут ветви', 'circuit breaker fallback']),
            })
        if force_cycle and n >= 3:
            steps[0]['depends_on'] = '2,3'
            steps[2]['depends_on'] = '1'
        return {
            'meta': {
                'name': 'Fuzz', 'entity': 'E', 'goal': 'correlationId fuzz',
                'customer_visible': 'yes', 'money': random.choice(['no', 'indirect', 'direct']),
                'sla_ms': str(random.choice([0, 500, 1000, 3000])),
                'read_freq': random.choice(['low', 'medium', 'high', 'very_high']),
                'ordering': random.choice(['no', 'per_entity', 'global']),
                'load_rps': str(random.choice([0, 10, 200, 1000, 5000])),
                'peak_factor': str(random.choice([1, 2, 5])),
                'multi_tenant': random.choice(['yes', 'no']),
                'fields': 'id:string|required|unique, correlationId:string|required|indexed',
                'lookup_keys': 'requestId', 'statuses': 'NEW,DONE',
            },
            'systems': systems,
            'steps': steps,
        }

    ok = invalid = 0
    for i in range(count):
        result = engine.analyze(make_payload(i, force_cycle=(i % 211 == 0)))
        if not result.get('ok'):
            invalid += 1
            assert i % 211 == 0 and any('Циклическая' in e for e in result.get('errors', [])), (i, result)
            continue
        ok += 1
        for f in result['findings']:
            if f['rule'] == 'external_blocking':
                m = re.search(r'Шаг (\d+)', f.get('where', ''))
                if m:
                    step = result['model']['graph']['by_order'][int(m.group(1))]
                    assert engine._v8636_outbound_external_or_legacy(result['model'], step), (i, f, step)
        for step in result['model']['steps']:
            if (step.get('source_system') or step.get('target_system')) and engine._v8636_is_inbound_external(result['model'], step):
                assert not step.get('external'), (i, 'inbound marked external', step)
            if step.get('channel') in engine.BROKER_CHANNELS and step.get('source_system') in ('Kafka', 'Rabbit'):
                assert engine._is_consumption(result['model'], step), (i, 'broker source not consumption', step)
            if step.get('channel') in engine.BROKER_CHANNELS and step.get('target_system') in ('Kafka', 'Rabbit') and step.get('source_system') == 'Service':
                assert not engine._is_consumption(result['model'], step), (i, 'publish misread as consumption', step)
    return ok, invalid


def main():
    started = time.time()
    deterministic_cases()
    channel_matrix()
    ok, invalid = fuzz()
    elapsed = time.time() - started
    print(f'CORE_E2E_SEMANTIC_v8637 ok deterministic=19 channel_matrix={len(engine.ALL_CHANNELS)} broker_matrix={len(engine.BROKER_CHANNELS) * 2} fuzz_ok={ok} invalid_cycles={invalid} elapsed={elapsed:.2f}s')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:  # pragma: no cover - diagnostic CLI output
        print('CORE_E2E_SEMANTIC_v8637 FAILED:', repr(exc))
        traceback.print_exc()
        sys.exit(1)
