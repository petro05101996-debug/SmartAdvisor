# -*- coding: utf-8 -*-
from urllib.parse import urlencode

from integration_architect_pro import (
    Engine,
    apply_progressive_ui_mapping,
    compute_production_gate_from_controls,
    defaults,
    map_draft_to_internal_fields,
    normalize_wizard_draft,
    parse_post,
)


def test_mapping_layer_kafka_async_populates_existing_internal_fields():
    raw = {
        'ux_mode': ['wizard'],
        'wizard_task_type': ['kafka_event'],
        'wizard_source_name': ['Contract Service'],
        'wizard_target_name': ['Reporting Service'],
        'wizard_process_template': ['kafka'],
        'risk_duplicate_event': ['yes'],
        'risk_lost_event': ['yes'],
        'risk_bad_messages': ['yes'],
    }
    mapped = apply_progressive_ui_mapping(raw, defaults())
    assert 'Contract Service' in mapped['systems_matrix']
    assert 'Reporting Service' in mapped['target_integration_matrix']
    assert 'Kafka' in mapped['target_integration_matrix']
    assert 'eventId' in mapped['contract_matrix']
    assert 'DLQ' in mapped['error_matrix']
    assert 'consumer_lag' in mapped['observability_matrix']
    assert 'outbox' in mapped['existing_capabilities']
    assert 'idempotency' in mapped['wizard_defaults_applied']


def test_quick_unknown_answers_do_not_block_report_generation():
    body = urlencode({
        'ux_mode': 'quick',
        'quick_description': 'Contract Service должен отправлять изменения договоров в Reporting Service через Kafka.',
        'quick_goal': 'unknown',
        'quick_speed': 'unknown',
        'quick_broker': 'unknown',
        'quick_external': 'unknown',
        'quick_load': 'unknown',
    })
    form = parse_post(body)
    assert 'quick_goal' in form['wizard_missing_information']
    assert form['systems_matrix']
    res = Engine().generate(form)
    assert res['markdown']
    assert 'Markdown' not in res['recommended']['name']


def test_rest_case_does_not_make_kafka_mandatory():
    draft = normalize_wizard_draft({
        'ux_mode': ['wizard'],
        'quick_description': ['UI вызывает Order API, Order API должен получить статус доставки из Delivery Service и вернуть пользователю.'],
        'wizard_process_template': ['rest'],
        'wizard_source_name': ['Order API'],
        'wizard_target_name': ['Delivery Service'],
    })
    mapped = map_draft_to_internal_fields(draft, defaults())
    assert mapped['allowed_channels'] == ['rest']
    assert 'REST' in mapped['target_integration_matrix']
    assert 'Kafka' not in mapped['target_integration_matrix']
    assert 'timeout' in mapped['wizard_defaults_applied']
    assert 'correlationId' in mapped['wizard_defaults_applied']


def test_expert_mode_preserves_raw_matrices():
    base = defaults()
    base['systems_matrix'] = 'raw system | raw role | raw owner | critical | REST | blocking | 1s'
    raw = {'ux_mode': ['expert']}
    mapped = apply_progressive_ui_mapping(raw, base)
    assert mapped['systems_matrix'] == base['systems_matrix']


def test_report_generation_after_new_wizard_flow_reuses_engine():
    body = urlencode({
        'ux_mode': 'wizard',
        'wizard_task_type': 'kafka_event',
        'wizard_source_name': 'Contract Service',
        'wizard_target_name': 'Reporting Service',
        'wizard_process_template': 'rest_enrichment_kafka',
        'risk_duplicate_event': 'yes',
        'risk_lost_event': 'yes',
        'risk_external_timeout': 'yes',
        'risk_traceability': 'yes',
    })
    form = parse_post(body)
    res = Engine().generate(form)
    assert 'Outbox' in res['markdown'] or 'outbox' in res['markdown'].lower()
    assert res['production_gate']['level'] in {'GREEN', 'YELLOW', 'RED'}
    assert res['advanced'].get('adr')


def test_production_gate_marks_missing_blockers():
    gate = compute_production_gate_from_controls(['timeout', 'monitoring'], 'kafka_async')
    assert gate['verdict'] == 'RED'
    assert any('idempotency' in g['title'] for g in gate['gaps'])


def test_quick_mode_ignores_hidden_wizard_template_and_detects_kafka_enrichment():
    body = urlencode({
        'ux_mode': 'quick',
        'quick_description': 'Contract Service отправляет изменения через Kafka, перед этим обогащает через REST из Client Service',
        'quick_broker': 'yes',
        'wizard_process_template': 'rest',  # hidden browser default from wizard panel must not win
    })
    form = parse_post(body)
    assert form['allowed_channels'] == ['rest', 'kafka']
    assert 'Kafka' in form['target_integration_matrix']
    assert 'REST enrichment' in form['process_steps'] or 'enrichment' in form['compromise_comment'].lower()
    assert 'async' in form['wizard_decision_summary']


def test_html_hides_legacy_panels_in_new_modes_and_forces_expert_sections_visible():
    from integration_architect_pro import form_page
    html = form_page()
    assert 'body.quick-mode .ultra-panel' in html
    assert 'body.wizard-mode .beginner-panel' in html
    assert 'body.review-mode .ultra-panel' in html
    assert 'body.expert-mode details.section' in html
    assert 'body.expert-mode details.matrix-section' in html
    assert "if(mode === 'expert') document.body.classList.add('power-mode')" in html


def test_review_mode_is_separate_and_maps_to_audit_existing_solution():
    from integration_architect_pro import form_page
    html = form_page()
    assert "data-mode-panel='review'" in html
    assert "switchProgressiveMode('review')" in html
    assert "if(mode === 'review') mode = 'wizard'" not in html
    body = urlencode({
        'ux_mode': 'review',
        'review_description': 'Сейчас consumer читает Kafka, фильтрует события по полю и сохраняет нужные в Postgres.',
        'wizard_process_template': 'rest',
    })
    form = parse_post(body)
    assert form['task_type'] == 'audit_existing_solution'
    assert form['business_goal'].startswith('Сейчас consumer читает Kafka')


def test_wizard_production_gate_is_exposed_to_engine_result():
    body = urlencode({
        'ux_mode': 'wizard',
        'wizard_task_type': 'kafka_event',
        'wizard_source_name': 'Contract Service',
        'wizard_target_name': 'Reporting Service',
        'wizard_process_template': 'kafka',
    })
    form = parse_post(body)
    res = Engine().generate(form)
    assert res.get('wizard_production_gate')
    assert res['ctx'].get('wizard_production_gate') == res['wizard_production_gate']


def test_expert_mode_preserves_raw_matrices_even_with_hidden_wizard_defaults():
    base = defaults()
    base['systems_matrix'] = 'raw system | raw role | raw owner | critical | REST | blocking | 1s'
    base['target_integration_matrix'] = 'raw source | raw target | SOAP | sync | raw trigger | raw data | raw contract | 10s | no | 0 | no | raw key | raw auth | raw limit | raw owner'
    base['process_steps'] = '0 | 1 | root | Raw expert step | Raw System | SOAP | raw input | raw output | 10s | no | none | blocking | Raw owner'
    raw = {
        'ux_mode': ['expert'],
        # Hidden defaults submitted by the browser from hidden wizard controls:
        'wizard_task_type': ['kafka_event'],
        'wizard_process_template': ['kafka'],
        'wizard_source_name': ['Contract Service'],
        'wizard_target_name': ['Reporting Service'],
        'risk_duplicate_event': ['yes'],
    }
    mapped = apply_progressive_ui_mapping(raw, base)
    assert mapped['systems_matrix'] == base['systems_matrix']
    assert mapped['target_integration_matrix'] == base['target_integration_matrix']
    assert mapped['process_steps'] == base['process_steps']
    assert 'wizard_defaults_applied' not in mapped


def test_start_page_exposes_advanced_mode_card():
    from integration_architect_pro import form_page
    html = form_page()
    assert "value='advanced'" in html
    assert 'Продвинутый режим' in html
    assert "switchProgressiveMode('advanced')" in html
