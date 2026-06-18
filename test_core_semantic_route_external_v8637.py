import engine


def _base_payload(steps):
    return {
        'meta': {
            'name': 'Semantic route external flag regression',
            'entity': 'Request',
            'goal': 'Проверить route semantics correlationId',
            'customer_visible': 'yes',
            'money': 'no',
            'sla_ms': '1500',
            'fields': 'requestId:string|required|unique, correlationId:string|required|indexed',
            'lookup_keys': 'requestId',
            'statuses': 'NEW,DONE',
        },
        'systems': [
            {'name': 'Client', 'role': 'external', 'criticality': 'medium', 'stability': 'stable'},
            {'name': 'API', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
            {'name': 'SVC', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
            {'name': 'DB', 'role': 'db', 'criticality': 'high', 'stability': 'stable'},
            {'name': 'Partner', 'role': 'external', 'criticality': 'medium', 'stability': 'unstable'},
        ],
        'steps': steps,
    }


def _rules(result):
    return {f['rule']: f for f in result['findings']}


def test_inbound_external_initiator_is_not_external_dependency_for_semantic_route():
    payload = _base_payload([
        {'order': 1, 'name': 'Client calls API', 'source_system': 'Client', 'system': 'Client', 'target_system': 'API', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100', 'idempotency': 'key'},
        {'order': 2, 'name': 'API calls SVC', 'source_system': 'API', 'system': 'API', 'target_system': 'SVC', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '100', 'idempotency': 'key', 'depends_on': '1'},
        {'order': 3, 'name': 'SVC writes DB', 'source_system': 'SVC', 'system': 'SVC', 'target_system': 'DB', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '100', 'idempotency': 'key', 'depends_on': '2', 'writes_entity': 'yes'},
    ])
    result = engine.analyze(payload)
    assert result['ok'], result
    assert not result['model']['steps'][0]['external']
    assert 'external_blocking' not in _rules(result)
    assert _rules(result)['sync_chain_depth']['severity'] == 'high'


def test_outbound_external_target_still_marks_external_dependency():
    payload = _base_payload([
        {'order': 1, 'name': 'API calls partner', 'source_system': 'API', 'system': 'API', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '500', 'idempotency': 'key'},
    ])
    result = engine.analyze(payload)
    assert result['ok'], result
    assert result['model']['steps'][0]['external']
    assert 'external_blocking' in _rules(result)
