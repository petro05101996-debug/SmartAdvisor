import json
from integration_architect_pro import Engine


def run(form):
    return Engine().generate(form)


def base(name, situations, nodes, edges, **kw):
    form = {
        'project_name': name,
        'task_type': kw.get('task_type', 'e2e_chain'),
        'business_goal': kw.get('business_goal', name),
        'business_situations': situations,
        'customer_visible': kw.get('customer_visible', 'yes'),
        'money_impact': kw.get('money_impact', 'no'),
        'source_system': kw.get('source_system', 'Core API'),
        'source_change_policy': kw.get('source_change_policy', 'minimal_table_only'),
        'change_policy': kw.get('change_policy', ['add_api', 'add_event', 'add_status']),
        'allowed_channels': kw.get('allowed_channels', ['rest', 'kafka', 'queue']),
        'process_graph_json': json.dumps({'nodes': nodes, 'edges': edges}, ensure_ascii=False),
        'systems_matrix': kw.get('systems_matrix', 'Core API | owner | Team A | critical | REST | blocking | 3s\nTarget | receiver | Team B | high | REST/Kafka | non_blocking | 30s'),
        'process_steps': '0 | 1 | root | Старт | Core API | REST | request | accepted | 3s | no | validation error | blocking | Team A',
        'fields': 'operationId:uuid|required|unique, idempotencyKey:string|unique',
        'source_of_truth': 'own_db',
        'delivery': kw.get('delivery', 'business_exactly_once'),
        'result_model': kw.get('result_model', 'tracking'),
        'retention_days': '30',
        'testing': 'full',
        'observability': 'full',
    }
    form.update(kw)
    return form


def assert_readable(md):
    for marker in ['## 0. Читаемый вывод', '## 1. Что система поняла из ввода', '## 2. Построенная цепочка процесса', '## 2A. Схема потоков и переходов', '## 5. Что нельзя делать', '## 6. MVP простыми действиями']:
        assert marker in md
    assert '```mermaid' in md and 'flowchart LR' in md and '-->|' in md
    assert 'Ключевые контроли: CQRS' not in md.split('## 1. Резюме')[0]


def test_webhook_payment_recommends_webhook_intake_not_dwh_from_demo_rows():
    nodes = [
        {'id': 'S1', 'title': 'Принять webhook', 'type': 'webhook_receive', 'system_id': 'Webhook API', 'channel': 'Webhook'},
        {'id': 'S2', 'title': 'Проверить подпись и raw body', 'type': 'validation', 'system_id': 'Webhook API'},
        {'id': 'S3', 'title': 'Сохранить Inbox/raw event', 'type': 'persist_operation', 'system_id': 'Webhook API', 'idempotency_required': True},
        {'id': 'S4', 'title': 'Async обработать платёж', 'type': 'consume_event', 'system_id': 'Payment Worker'},
        {'id': 'S5', 'title': 'Reconciliation provider API', 'type': 'reconciliation', 'system_id': 'Payment Worker'},
    ]
    edges = [{'from_node_id': 'S1', 'to_node_id': 'S2', 'transition_type': 'success'}, {'from_node_id': 'S2', 'to_node_id': 'S3', 'transition_type': 'success'}, {'from_node_id': 'S3', 'to_node_id': 'S4', 'transition_type': 'event_trigger'}, {'from_node_id': 'S4', 'to_node_id': 'S5', 'transition_type': 'technical_error'}]
    res = run(base('payment webhook duplicate delivery', ['webhook_callback', 'financial_operation', 'exactly_once_required'], nodes, edges, task_type='external_partner', money_impact='yes', result_model='callback', allowed_channels=['webhook', 'queue', 'rest']))
    md = res['markdown']
    assert 'Webhook Intake + Inbox Processing' in res['recommended']['name']
    assert_readable(md)
    assert 'signature' in md.lower() or 'подпис' in md.lower()
    assert 'Inbox' in md and 'reconciliation' in md.lower()


def test_shared_topic_highload_outputs_filter_lag_dlq_controls():
    nodes = [
        {'id': 'S1', 'title': 'Читать shared topic', 'type': 'consume_event', 'system_id': 'Selective Consumer', 'channel': 'Kafka'},
        {'id': 'S2', 'title': 'Фильтр полезных 0.2%', 'type': 'validation', 'system_id': 'Selective Consumer'},
        {'id': 'S3', 'title': 'Inbox/dedup sink', 'type': 'persist_operation', 'system_id': 'Selective Consumer', 'idempotency_required': True},
        {'id': 'S4', 'title': 'DLQ reprocess', 'type': 'reprocess', 'system_id': 'Ops'},
    ]
    edges = [{'from_node_id': 'S1', 'to_node_id': 'S2', 'transition_type': 'success'}, {'from_node_id': 'S2', 'to_node_id': 'S3', 'transition_type': 'success'}, {'from_node_id': 'S4', 'to_node_id': 'S3', 'transition_type': 'reprocess'}]
    res = run(base('shared topic selective consumer', ['shared_topic_selective_consumer', 'highload_write_stream', 'exactly_once_required'], nodes, edges, task_type='event_domain', load_profile='highload', rps='10000', capacity_matrix='shared_topic_filter | 10000 | 50000 | 8 | 100 | 50000000 | 0.2% | 24 | 12 | 50 | 300s | 6h | 12h | target API 100 rps'))
    md = res['markdown']
    assert 'Shared Topic Selective Consumer' in res['recommended']['name']
    assert_readable(md)
    assert '0.2%' in md and 'DLQ' in md and ('lag' in md.lower() or 'consumer_lag' in md)


def test_saga_compensation_report_is_step_based():
    nodes = [
        {'id': 'S1', 'title': 'Принять заказ', 'type': 'api_request', 'system_id': 'Order API', 'idempotency_required': True},
        {'id': 'S2', 'title': 'Сохранить операцию', 'type': 'persist_operation', 'system_id': 'Order API', 'idempotency_required': True},
        {'id': 'S3', 'title': 'Авторизовать платёж', 'type': 'rest_call', 'system_id': 'Order PM', 'target_system_id': 'Payment'},
        {'id': 'S4', 'title': 'Компенсировать платёж', 'type': 'compensation', 'system_id': 'Order PM', 'target_system_id': 'Payment'},
    ]
    edges = [{'from_node_id': 'S1', 'to_node_id': 'S2', 'transition_type': 'success'}, {'from_node_id': 'S2', 'to_node_id': 'S3', 'transition_type': 'success'}, {'from_node_id': 'S3', 'to_node_id': 'S4', 'transition_type': 'compensation'}]
    res = run(base('order payment saga compensation', ['application_or_order_creation', 'financial_operation', 'distributed_transaction_saga'], nodes, edges, money_impact='yes'))
    md = res['markdown']
    assert_readable(md)
    assert 'compensation' in md.lower() and 'idempotency' in md.lower()
    assert 'Паттерны по шагам, а не набор терминов' in md


def test_fanin_customer360_has_partial_deadline_freshness():
    nodes = [
        {'id': 'S1', 'title': 'GET customer card', 'type': 'api_request', 'system_id': 'BFF', 'channel': 'REST'},
        {'id': 'S2', 'title': 'Fan-in ABS/CRM/KYC', 'type': 'fan_in', 'system_id': 'BFF'},
        {'id': 'S3', 'title': 'Partial response', 'type': 'decision', 'system_id': 'BFF'},
    ]
    edges = [{'from_node_id': 'S1', 'to_node_id': 'S2', 'transition_type': 'success'}, {'from_node_id': 'S2', 'to_node_id': 'S3', 'transition_type': 'parallel_join'}]
    res = run(base('customer 360 fan-in', ['multi_source_aggregation', 'customer_360', 'api_composition', 'highload_read'], nodes, edges, task_type='new_from_scratch', money_impact='indirect', unavailable_behavior='partial_response', read_frequency='very_high'))
    md = res['markdown']
    assert 'BFF/API Composition' in res['recommended']['name']
    assert_readable(md)
    assert 'Fan-in' in md and 'partial' in md.lower() and ('freshness' in md.lower() or 'свеж' in md.lower())
