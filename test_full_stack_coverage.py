# -*- coding: utf-8 -*-
import ui
from engine import normalize, analyze


def test_full_stack_options_are_present_in_ui_and_manual_override():
    html = ui.form_page()
    for text in [
        'RabbitMQ', 'Redis — кэш для быстрого чтения', 'Redis — распределённая блокировка', 'SOAP', 'SFTP',
        'Объектное хранилище', 'API Gateway', 'ESB — интеграционная шина',
        'Redis Streams', 'Поисковый индекс'
    ]:
        assert text in html
    assert 'технический способ взаимодействия подбирается автоматически' in html


def test_engine_preserves_extended_stack_channels():
    channels = [
        'rabbitmq', 'redis_streams', 'redis_queue', 'redis_cache', 'redis_lock',
        'sftp', 'object_storage', 'api_gateway', 'esb', 'search', 'soap'
    ]
    payload = {
        'meta': {'name': 'full stack', 'entity': 'E', 'fields': 'id:uuid|required|unique'},
        'systems': [{'name': 'S', 'role': 'internal'}, {'name': 'Target', 'role': 'external'}],
        'steps': [
            {'order': i + 1, 'name': f'step {ch}', 'system': 'S', 'target_system': 'Target',
             'channel': ch, 'blocking': 'no' if ch not in {'soap','api_gateway','esb','redis_cache','redis_lock'} else 'yes',
             'timeout_ms': '100' if ch in {'soap','api_gateway','esb','redis_cache','redis_lock'} else '',
             'retry': 'auto', 'idempotency': 'key', 'compensation': 'DLQ replay TTL fencing checksum reindex'}
            for i, ch in enumerate(channels)
        ]
    }
    model = normalize(payload)
    assert {s['channel'] for s in model['steps']} == set(channels)
    res = analyze(payload)
    assert res['ok'] is True


def test_stack_specific_failure_hints_cover_rabbit_redis_soap():
    payload = {
        'meta': {'name': 'stack hints', 'entity': 'E', 'fields': 'id:uuid|required|unique'},
        'systems': [{'name': 'S', 'role': 'internal'}],
        'steps': [
            {'order': 1, 'name': 'SOAP legacy call', 'system': 'S', 'channel': 'soap', 'blocking': 'yes', 'timeout_ms': '500', 'retry': 'auto', 'idempotency': 'key'},
            {'order': 2, 'name': 'RabbitMQ command', 'system': 'S', 'channel': 'rabbitmq', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '1'},
            {'order': 3, 'name': 'Redis cache read', 'system': 'S', 'channel': 'redis_cache', 'blocking': 'yes', 'timeout_ms': '50', 'retry': 'none', 'idempotency': 'natural', 'depends_on': '2'},
        ]
    }
    flows = {x['channel']: x['failure_handling'] for x in analyze(payload)['scenario']['main_flow']}
    assert 'SOAP/WSDL' in flows['soap']
    assert 'RabbitMQ' in flows['rabbitmq'] and 'DLX' in flows['rabbitmq']
    assert 'Redis cache' in flows['redis_cache'] and 'TTL' in flows['redis_cache']
