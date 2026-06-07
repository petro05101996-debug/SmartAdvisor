import json
from integration_architect_pro import Engine

BASE = {
    'ux_mode': 'business_first_constructor',
    'simple_goal': 'new',
    'simple_q_systems': '3',
    'simple_q_immediate': 'Принять сейчас, результат позже',
    'simple_q_payload': 'Заявка',
    'simple_q_risk': 'Потерять данные',
    'simple_q_error': 'Сохранить и обработать потом',
    'simple_q_status': 'Да',
}

def steps(rows):
    return json.dumps([{'order': i+1, 'actorLabel': a, 'action': b, 'object': c} for i,(a,b,c) in enumerate(rows)], ensure_ascii=False)

def run(form):
    return Engine().generate({**BASE, **form})

def assert_contains(text, *patterns):
    low = str(text).lower()
    for p in patterns:
        assert p.lower() in low, p

def mixed_application_form():
    return {
        'simple_situation': 'async_worker',
        'business_case': 'application_creation',
        'business_result_timing': 'Нужно принять сейчас, результат получить позже',
        'business_object': 'Заявка',
        'business_result_type': 'Обновлён статус',
        'business_criticality': 'Потерять данные',
        'business_steps_json': steps([
            ('Клиент', 'Создаёт заявку', 'Заявка'),
            ('Внутренняя система', 'Принимает заявку', 'Заявка'),
            ('Внутренняя система', 'Проверяет данные', 'Заявка'),
            ('Внешняя система', 'Обрабатывает запрос', 'Заявка'),
            ('Внутренняя система', 'Обновляет статус', 'Статус'),
        ]),
        'business_constraints_json': json.dumps(['highload','regulatory','pii','many_consumers','compensation','multi_tenant','active_active'], ensure_ascii=False),
    }


def test_multi_tenant_does_not_override_saga_primary_case():
    res = run(mixed_application_form())
    assert res['primary_specialized_case'] == 'saga_state_machine'
    assert res['specialized_case'] == 'saga_state_machine'
    assert 'multi_tenant_noisy_neighbor' in res['secondary_modifiers']
    assert 'highload' in res['secondary_modifiers']
    assert ('regulatory_process' in res['secondary_modifiers'] or 'personal_data_exchange' in res['secondary_modifiers'])
    assert_contains(res['case_schema'], 'Process State DB', 'Compensation')
    assert not res['case_schema'].startswith('Shared Stream')
    assert_contains(res['markdown'], 'tenantId key', 'Process State DB', 'compensation_failed')


def test_modifiers_extend_must_have_not_replace_primary():
    res = run(mixed_application_form())
    md = res['markdown']
    assert_contains(md, 'Process State DB', 'compensation_failed', 'tenantId key', 'per-tenant quotas', 'audit trail', 'access control', 'backpressure')


def test_primary_schema_not_replaced_by_modifier_schema():
    res = run(mixed_application_form())
    assert res['primary_specialized_case'] == 'saga_state_machine'
    assert 'multi_tenant_noisy_neighbor' in res['secondary_modifiers']
    assert 'Shared Stream → Tenant-aware Consumer Pool' not in res['case_schema']
    assert 'Process State DB' in res['case_schema']


def test_constraints_are_explained_not_raw_flags():
    res = run(mixed_application_form())
    md = res['markdown']
    assert_contains(md, 'Highload: нужны backpressure', 'PII/ПДн', 'Регуляторика', 'Multi-tenant')
    assert '- highload\n' not in md
    assert '- pii\n' not in md


def test_technical_details_match_primary_case():
    res = run(mixed_application_form())
    md = res['markdown']
    assert_contains(md, 'Process State DB', 'compensation step', 'manual recovery queue', 'Status API', 'External Provider Adapter/Worker')


def test_business_first_readiness_uses_business_fields():
    res = Engine().generate({
        'ux_mode': 'business_first_constructor',
        'business_case': 'application_creation',
        'business_result_timing': 'Нужно принять сейчас, результат получить позже',
        'business_object': 'Заявка',
        'business_result_type': 'Обновлён статус',
        'business_criticality': 'Потерять данные',
        'business_steps_json': mixed_application_form()['business_steps_json'],
        'business_constraints_json': json.dumps(['compensation'], ensure_ascii=False),
    })
    assert res['readiness']['score'] >= 60
    assert res['readiness']['status'] != 'RED'


def test_application_highload_pii_without_erasure_is_not_privacy_primary():
    res = run({
        'business_case': 'application_creation',
        'business_result_timing': 'Нужно принять сейчас, результат получить позже',
        'business_steps_json': mixed_application_form()['business_steps_json'],
        'business_constraints_json': json.dumps(['highload','pii','regulatory'], ensure_ascii=False),
    })
    assert res['primary_specialized_case'] in {'saga_state_machine', 'async_worker'}
    assert res['primary_specialized_case'] != 'privacy_erasure_pipeline'
    assert 'personal_data_exchange' in res['secondary_modifiers']


def test_data_change_no_new_topic_highload_multi_tenant_primary_shared_or_tenant():
    res = run({
        'simple_situation': 'event_kafka',
        'business_case': 'data_change_distribution',
        'business_constraints_json': json.dumps(['no_new_topic','highload','many_consumers','multi_tenant'], ensure_ascii=False),
    })
    assert res['primary_specialized_case'] in {'shared_topic_selective_consumer','multi_tenant_noisy_neighbor'}
    assert_contains(res['markdown'], 'consumer lag', 'tenant')


def test_financial_active_active_write_still_primary_when_really_financial():
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["money","highload","active_active"]'})
    assert res['primary_specialized_case'] == 'active_active_financial_write'
    assert_contains(res['case_schema'], 'Single Writer/Ledger')
    assert_contains(res['markdown'], 'split-brain', 'double spend')


def test_custom_schema_overrides_primary_schema_but_keeps_modifiers():
    custom = 'Custom A → Custom B → Custom C'
    form = mixed_application_form()
    form['custom_chain_json'] = json.dumps({'schema': custom}, ensure_ascii=False)
    res = run(form)
    assert res['case_schema'] == custom
    assert res['primary_specialized_case'] == 'saga_state_machine'
    assert 'multi_tenant_noisy_neighbor' in res['secondary_modifiers']
    assert custom in res['markdown']
    assert 'tenantId key' in res['markdown']
