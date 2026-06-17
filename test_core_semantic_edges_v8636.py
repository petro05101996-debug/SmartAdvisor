from engine import analyze, _is_consumption


def fired(res):
    return {f['rule'] for f in res.get('findings', [])}


def test_source_system_broker_step_is_consumer_not_publisher():
    payload = {
        'meta': {'name': 'Broker semantic consumer', 'entity': 'Order', 'load_rps': 1000, 'peak_factor': 2},
        'systems': [
            {'name': 'Producer', 'role': 'internal'},
            {'name': 'Kafka', 'role': 'broker'},
            {'name': 'Consumer', 'role': 'internal'},
        ],
        'steps': [
            {'order': 1, 'name': 'Producer publishes OrderCreated', 'system': 'Producer', 'source_system': 'Producer', 'target_system': 'Kafka', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'compensation': 'outbox'},
            {'order': 2, 'name': 'Consumer reads OrderCreated from Kafka', 'system': 'Consumer', 'source_system': 'Kafka', 'target_system': 'Consumer', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '1', 'data_in': 'filter common topic', 'compensation': 'DLQ replay'},
        ],
    }
    res = analyze(payload)
    assert res['ok'] is True
    steps = {s['order']: s for s in res['model']['steps']}
    assert _is_consumption(res['model'], steps[1]) is False
    assert _is_consumption(res['model'], steps[2]) is True
    assert 'contract_versioning' in fired(res)
    assert 'stream_consumer_controls' in fired(res)


def test_async_consumer_blocking_on_external_target_is_detected():
    payload = {
        'meta': {'name': 'Async handler external target', 'entity': 'Order'},
        'systems': [
            {'name': 'Kafka', 'role': 'broker'},
            {'name': 'Worker', 'role': 'internal'},
            {'name': 'Partner', 'role': 'external'},
        ],
        'steps': [
            {'order': 1, 'name': 'Worker consumes event', 'system': 'Worker', 'source_system': 'Kafka', 'target_system': 'Worker', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'compensation': 'DLQ replay'},
            {'order': 2, 'name': 'Worker calls partner', 'system': 'Worker', 'source_system': 'Worker', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 3000, 'depends_on': '1'},
        ],
    }
    res = analyze(payload)
    assert 'blocking_in_async_handler' in fired(res)
    assert 'external_blocking' in fired(res)


def test_target_rate_limit_and_unstable_are_checked_not_executor_only():
    payload = {
        'meta': {'name': 'Target rate limit', 'entity': 'Request', 'load_rps': 500, 'peak_factor': 2},
        'systems': [
            {'name': 'Service', 'role': 'internal'},
            {'name': 'Partner', 'role': 'external', 'stability': 'limited', 'rate_limit_rps': 100},
        ],
        'steps': [
            {'order': 1, 'name': 'Service calls limited partner', 'system': 'Service', 'source_system': 'Service', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 500},
        ],
    }
    res = analyze(payload)
    rules = fired(res)
    assert 'capacity_vs_limit' in rules
    assert 'unstable_dependency' in rules


def test_join_detects_external_target_branch():
    payload = {
        'meta': {'name': 'Join external target', 'entity': 'Profile'},
        'systems': [
            {'name': 'BFF', 'role': 'internal'},
            {'name': 'Partner', 'role': 'external'},
            {'name': 'Internal', 'role': 'internal'},
        ],
        'steps': [
            {'order': 1, 'name': 'start', 'system': 'BFF', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 50},
            {'order': 2, 'name': 'call partner branch', 'system': 'BFF', 'source_system': 'BFF', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 300, 'depends_on': '1'},
            {'order': 3, 'name': 'call internal branch', 'system': 'BFF', 'source_system': 'BFF', 'target_system': 'Internal', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 200, 'depends_on': '1'},
            {'order': 4, 'name': 'aggregate branches', 'system': 'BFF', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 30, 'depends_on': '2,3'},
        ],
    }
    res = analyze(payload)
    assert 'fanin_partial_failure' in fired(res)
