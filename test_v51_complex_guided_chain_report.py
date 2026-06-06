import json
from integration_architect_pro import Engine, form_page


def base_form():
    return {
        'project_name': 'Complex guided chain',
        'task_type': 'e2e_chain',
        'business_goal': 'Клиент создаёт заявку, дальше идут параллельные ветки CRM, DWH и Notification, есть callback, retry loop и compensation.',
        'criticality': 'high',
        'business_situations': ['application_or_order_creation', 'multi_step_business_process', 'financial_operation', 'webhook_callback'],
        'customer_visible': 'yes',
        'money_impact': 'yes',
        'regulatory_impact': 'unknown',
        'read_frequency': 'high',
        'change_frequency': 'medium',
        'response_time_expectation': 'under_3s',
        'freshness_requirement': 'up_to_1m',
        'business_priority': 'balanced',
        'stale_data_impact': 'financial',
        'unavailable_behavior': 'queue_for_later',
        'external_dependency_stability': 'limited',
        'load_profile': 'medium',
        'rps': '50',
        'peak_factor': '5',
        'latency_sla': 'seconds',
        'consistency': 'business_exactly_once',
        'existing_state': 'production',
        'change_policy': ['add_api', 'add_event', 'add_outbox', 'add_status'],
        'constraint_profile': 'balanced',
        'budget_pressure': 'medium',
        'deadline_pressure': 'normal',
        'new_service_policy': 'allowed',
        'new_infra_policy': 'existing_only',
        'source_change_policy': 'minimal_table_only',
        'risk_appetite': 'medium',
        'existing_capabilities': ['rest_api', 'kafka', 'monitoring', 'status_model'],
        'orchestration': 'orchestrator',
        'chain_depth': 'multi_level',
        'failure_policy': 'retry',
        'result_model': 'tracking',
        'source_system': 'Order API',
        'systems_matrix': 'Order API | владелец операции | Team A | critical | REST | blocking | 3s\nCRM | получатель | Team B | important | REST | non_blocking | 30s\nDWH | аналитика | Data | important | CDC | non_blocking | 15m\nNotification | уведомления | Team N | medium | REST | non_blocking | 10s',
        'fields': 'clientId:uuid|required|indexed|sensitive, amount:decimal|required, idempotencyKey:string|unique',
        'source_of_truth': 'own_db',
        'ownership': 'single',
        'data_volume': 'medium',
        'history': 'status',
        'retention': 'not_defined',
        'event_payload_intent': 'domain_fact',
        'delivery': 'business_exactly_once',
        'allowed_channels': ['rest', 'kafka'],
        'forbidden_channels': ['direct_db_write'],
        'kafka_topology': 'multi_topic_ok',
        'audit_depth': 'normal',
        'sensitivity': 'internal',
        'auth': 'service',
        'availability': 'basic',
        'observability': 'standard',
        'payload_kb': '5',
        'retention_days': '30',
        'target_lag_seconds': '60',
        'rollout': 'canary',
        'testing': 'full',
        'delivery_guarantee': 'business_exactly_once',
        'process_steps': '0 | 1 | root | Принять запрос | Order API | REST | request | accepted | 3s | no | validation error | blocking | Team A',
        'error_matrix': 'timeout | external | non_blocking | yes | retry then manual | Team A',
    }


def test_form_exposes_complex_chain_builder_without_raw_matrix_first():
    html = form_page()
    assert 'Конструктор сложной цепочки' in html
    assert 'data-add-complex="parallel_start"' in html
    assert 'data-add-complex="retry_loop"' in html
    assert 'data-add-complex="wait_callback"' in html
    assert 'data-add-complex="compensation"' in html
    assert 'process_graph_json' in html


def test_complex_graph_report_is_readable_and_mentions_all_complex_parts():
    form = base_form()
    graph = {
        'nodes': [
            {'id':'S1','title':'Принять запрос','type':'api_request','system_id':'Order API','channel':'REST','user_waits':True,'idempotency_required':True},
            {'id':'S2','title':'Сохранить операцию и статус','type':'persist_operation','system_id':'Order API','channel':'DB','user_waits':False,'idempotency_required':True},
            {'id':'S3','title':'Запустить параллельные ветки','type':'parallel_start','system_id':'Process Manager','channel':'Internal','user_waits':False},
            {'id':'S4','title':'Обновить CRM','type':'rest_call','system_id':'CRM Consumer','target_system_id':'CRM','channel':'REST','user_waits':False,'retry_policy':'max 3 backoff'},
            {'id':'S5','title':'Выгрузить в DWH','type':'dwh_export','system_id':'DWH Pipeline','channel':'DWH','user_waits':False},
            {'id':'S6','title':'Дождаться callback провайдера','type':'wait_callback','system_id':'Webhook API','channel':'Webhook','user_waits':False},
            {'id':'S7','title':'Retry loop внешнего скоринга','type':'retry_loop','system_id':'Worker','channel':'Timer/Scheduler','user_waits':False},
            {'id':'S8','title':'Компенсировать резерв при ошибке','type':'compensation','system_id':'Order API','channel':'REST','user_waits':False},
            {'id':'S9','title':'Переобработать DLQ','type':'reprocess','system_id':'Consumer','channel':'Kafka','user_waits':False},
        ],
        'edges': [
            {'from_node_id':'S1','to_node_id':'S2','transition_type':'success'},
            {'from_node_id':'S2','to_node_id':'S3','transition_type':'success'},
            {'from_node_id':'S3','to_node_id':'S4','transition_type':'parallel_start'},
            {'from_node_id':'S3','to_node_id':'S5','transition_type':'parallel_start'},
            {'from_node_id':'S4','to_node_id':'S8','transition_type':'compensation'},
            {'from_node_id':'S7','to_node_id':'S7','transition_type':'retry'},
            {'from_node_id':'S9','to_node_id':'S4','transition_type':'reprocess'},
        ],
    }
    form['process_graph_json'] = json.dumps(graph, ensure_ascii=False)
    md = Engine().generate(form)['markdown']
    assert '## 0. Читаемый вывод' in md
    assert '## 2. Построенная цепочка процесса' in md
    assert 'Параллельные ветки: да' in md
    assert 'Циклы/retry/polling/reconciliation: да' in md
    assert 'Wait event/callback: да' in md
    assert 'Compensation/manual/reprocess: да' in md
    assert 'Паттерны по шагам, а не набор терминов' in md
    assert 'Что нельзя делать' in md
    assert 'MVP простыми действиями' in md


def test_complex_chain_preview_is_flow_not_disconnected_cards():
    html = form_page()
    assert 'Схема потоков и последовательности' in html
    assert 'complex-flow-map' in html
    assert 'complex-flow-edge' in html
    assert 'complex-edge-label' in html
    assert 'fork/join' in html
    assert 'Это не набор карточек' in html


def test_report_contains_process_flow_diagram_not_only_text_cards():
    form = base_form()
    graph = {
        'nodes': [
            {'id':'S1','title':'Принять запрос','type':'api_request','system_id':'Order API','channel':'REST','user_waits':True},
            {'id':'S2','title':'Сохранить операцию','type':'persist_operation','system_id':'Order API','channel':'DB'},
            {'id':'S3','title':'Fork CRM/DWH','type':'parallel_start','system_id':'Process Manager','channel':'Internal'},
            {'id':'S4','title':'Обновить CRM','type':'rest_call','system_id':'CRM Consumer','target_system_id':'CRM','channel':'REST'},
            {'id':'S5','title':'Retry loop scoring','type':'retry_loop','system_id':'Worker','channel':'Timer'},
            {'id':'S6','title':'Компенсация резерва','type':'compensation','system_id':'Order API','channel':'REST'},
        ],
        'edges': [
            {'from_node_id':'S1','to_node_id':'S2','transition_type':'success'},
            {'from_node_id':'S2','to_node_id':'S3','transition_type':'success'},
            {'from_node_id':'S3','to_node_id':'S4','transition_type':'parallel_start'},
            {'from_node_id':'S4','to_node_id':'S5','transition_type':'timeout'},
            {'from_node_id':'S5','to_node_id':'S5','transition_type':'retry'},
            {'from_node_id':'S4','to_node_id':'S6','transition_type':'compensation'},
        ],
    }
    form['process_graph_json'] = json.dumps(graph, ensure_ascii=False)
    md = Engine().generate(form)['markdown']
    assert '## 2A. Схема потоков и переходов' in md
    assert '```mermaid' in md
    assert 'flowchart LR' in md
    assert '-->|parallel_start|' in md
    assert '-->|retry|' in md
    assert '-->|compensation|' in md
    assert 'Схема показывает не отдельные карточки, а поток' in md
