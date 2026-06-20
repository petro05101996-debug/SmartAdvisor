from engine import analyze


def base(step):
    return {
        'meta': {'name': 'validation', 'entity': 'E'},
        'systems': [{'name': 'A', 'role': 'internal'}, {'name': 'B', 'role': 'internal'}],
        'steps': [step],
    }


def test_unknown_channel_is_rejected_v8641():
    res = analyze(base({'order': 1, 'name': 'bad channel', 'system': 'A', 'source_system': 'A', 'target_system': 'B', 'channel': 'telepathy'}))
    assert res['ok'] is False
    assert any('неизвестный канал' in e for e in res['errors'])


def test_unknown_target_system_is_rejected_v8655():
    res = analyze(base({'order': 1, 'name': 'bad target', 'system': 'A', 'source_system': 'A', 'target_system': 'Missing', 'channel': 'rest'}))
    assert res['ok'] is False
    assert any('неизвестный получатель связи' in e for e in res['errors'])


def test_async_fanin_without_policy_is_reported_v8641():
    payload = {
        'meta': {'name': 'fanin', 'entity': 'E', 'lookup_keys': 'businessId'},
        'systems': [{'name': 'API', 'role': 'internal'}, {'name': 'Partner', 'role': 'external'}, {'name': 'Queue', 'role': 'broker'}, {'name': 'Joiner', 'role': 'internal'}],
        'steps': [
            {'order': 1, 'name': 'call partner', 'system': 'API', 'source_system': 'API', 'target_system': 'Partner', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '500'},
            {'order': 2, 'name': 'publish async branch', 'system': 'API', 'source_system': 'API', 'target_system': 'Queue', 'channel': 'kafka', 'blocking': 'no'},
            {'order': 3, 'name': 'join without policy', 'system': 'Joiner', 'source_system': 'Joiner', 'target_system': 'Joiner', 'channel': 'workflow_engine', 'blocking': 'no', 'depends_on': '1,2', 'compensation': 'без политики частичного ответа'},
        ],
    }
    res = analyze(payload)
    assert res['ok'] is True
    assert any(f.get('title') == 'Агрегация ветвей выполняется без политики частичного отказа.' for f in res['findings'])
