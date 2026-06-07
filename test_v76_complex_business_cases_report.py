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

def run(form):
    return Engine().generate({**BASE, **form})

def steps(rows):
    return json.dumps([{'order': i+1, 'actorLabel': a, 'action': b, 'object': c} for i,(a,b,c) in enumerate(rows)], ensure_ascii=False)

def assert_contains(text, *patterns):
    low = text.lower()
    for p in patterns:
        assert p.lower() in low, p

def test_business_first_detects_saga_not_generic_async():
    res = run({'simple_situation':'async_worker','business_case':'application_creation','business_result_timing':'Нужно принять сейчас, результат получить позже','business_constraints_json':'["compensation","money"]','business_steps_json':steps([('Клиент','Создаёт заявку','Заявка'),('Система','Компенсирует / откатывает шаг','Заявка')])})
    assert res['specialized_case'] == 'saga_state_machine'
    assert_contains(res['case_schema'], 'Process State DB', 'Compensation', 'Manual Recovery')
    assert_contains(res['markdown'], 'partial success', 'compensation_failed', 'manual recovery owner')

def test_business_first_detects_shared_topic_filtering():
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["no_new_topic","highload","many_consumers"]'})
    assert res['specialized_case'] == 'shared_topic_selective_consumer'
    assert_contains(res['markdown'], 'shared topic', 'filtering rules', 'discard rate', 'consumer lag', 'DLQ/reprocess')

def test_business_first_detects_enrichment_before_publish():
    res = run({'simple_situation':'enrichment_kafka','business_case':'data_enrichment','business_constraints_json':'["source_locked"]','business_steps_json':steps([('Система','Дополняет данные','Справочные данные')])})
    assert res['specialized_case'] == 'enrichment_before_kafka'
    assert_contains(res['case_schema'], 'Source-owned Outbox', 'Integration Publisher')
    assert_contains(res['markdown'], 'dataAsOf', 'enrichmentConsistency', 'FAILED/reprocess')

def test_business_first_detects_callback_webhook():
    res = run({'simple_situation':'callback','business_case':'external_check','business_result_timing':'Внешняя система ответит позже','business_constraints_json':'["unstable_external"]'})
    assert res['specialized_case'] == 'webhook_intake'
    assert_contains(res['markdown'], 'signature', 'raw body', 'inbox', 'idempotent callback', 'polling fallback')

def test_business_first_detects_status_fanin():
    res = run({'simple_situation':'status_aggregation','business_case':'status_screen','business_constraints_json':'["many_sources","highload"]'})
    assert res['specialized_case'] == 'bff_api_composition'
    assert_contains(res['markdown'], 'partial response', 'freshness marker', 'per-source timeout', 'cache/read model')

def test_business_first_detects_dwh_pipeline():
    res = run({'simple_situation':'dwh','business_case':'reporting','business_constraints_json':'["replay","regulatory"]'})
    assert res['specialized_case'] == 'dwh_pipeline'
    assert_contains(res['markdown'], 'watermark', 'staging', 'lineage', 'reconciliation', 'backfill', 'retention')

def test_business_first_detects_legacy_file():
    res = run({'simple_situation':'legacy_file','business_case':'legacy_file'})
    assert res['specialized_case'] == 'batch_file_exchange'
    assert_contains(res['markdown'], 'manifest', 'checksum', 'file registry', 'quarantine', 'reprocessing')

def test_business_first_detects_contract_change():
    res = run({'simple_situation':'audit','business_case':'audit','business_constraints_json':'["contract_change"]','business_goal':'Проверить контракт обязательное поле ошибка маппинга duplicate response'})
    assert res['specialized_case'] == 'contract_required_field_missing'
    assert_contains(res['markdown'], 'OpenAPI/AsyncAPI', 'required fields', 'consumer-driven contract tests')

def test_business_first_detects_active_active_financial():
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["money","highload","active_active"]'})
    assert res['specialized_case'] == 'active_active_financial_write'
    assert res['readiness']['status'] in {'RED','YELLOW'}
    assert_contains(res['markdown'], 'single writer', 'ledger', 'split-brain', 'reconciliation')

def test_business_first_detects_privacy_erasure():
    res = run({'simple_situation':'async_worker','business_case':'application_creation','business_constraints_json':'["pii","regulatory","privacy_erasure"]','business_steps_json':steps([('Система','Удаляет/исправляет данные','ПДн')])})
    assert res['specialized_case'] == 'privacy_erasure_pipeline'
    assert_contains(res['markdown'], 'legal hold', 'per-system erasure receipt', 'retention exception', 'audit')

def test_business_first_detects_multi_tenant_noisy_neighbor():
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["multi_tenant","shared_topic","highload"]'})
    assert res['specialized_case'] == 'multi_tenant_noisy_neighbor'
    assert_contains(res['markdown'], 'tenantId', 'per-tenant lag', 'consumer pool isolation', 'quotas')

def test_business_first_detects_migration_strangler():
    res = run({'simple_situation':'legacy_file','business_case':'legacy_file','business_constraints_json':'["migration"]'})
    assert res['specialized_case'] == 'strangler_migration'
    assert_contains(res['markdown'], 'facade', 'parallel run', 'shadow compare', 'feature flags', 'rollback')

def test_report_no_readiness_contradiction():
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["money","highload","active_active"]'})
    assert not ('Готовность требований:** 100%' in res['markdown'] and res['readiness']['status'] in {'RED','YELLOW'})

def test_report_schema_must_handoff_consistent():
    res = run({'simple_situation':'callback','business_case':'external_check','business_result_timing':'Внешняя система ответит позже'})
    for word in ['Async Worker', 'Inbox']:
        assert word in res['case_schema']
    res2 = run({'simple_situation':'event_kafka','business_case':'data_change_distribution'})
    for word in ['Outbox','Inbox']:
        assert word in res2['case_schema']

def test_invalid_actor_action_pair_warns():
    res = run({'simple_situation':'async_worker','business_case':'application_creation','business_steps_json':steps([('Клиент / пользователь','Принимает заявку','Заявка')])})
    assert 'Клиент обычно создаёт/отправляет заявку' in res['markdown']


def test_specialized_schema_not_overwritten_by_business_steps():
    generic_steps = steps([
        ('Клиент', 'Создаёт заявку', 'Заявка'),
        ('Система', 'Проверяет данные', 'Заявка'),
        ('Система', 'Передаёт данные дальше', 'Заявка'),
    ])
    saga = run({'simple_situation':'async_worker','business_case':'long_process','business_constraints_json':'["compensation"]','business_steps_json':generic_steps})
    assert saga['specialized_case'] == 'saga_state_machine'
    assert_contains(saga['case_schema'], 'Process State DB', 'Compensation')
    assert 'Service Step' not in saga['case_schema']
    shared = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["no_new_topic","many_consumers"]','business_steps_json':generic_steps})
    assert_contains(shared['case_schema'], 'Shared Event Stream', 'Filter', 'DLQ/Reprocess')
    enrich = run({'simple_situation':'enrichment_kafka','business_case':'data_enrichment','business_constraints_json':'["source_locked"]','business_steps_json':generic_steps})
    assert_contains(enrich['case_schema'], 'Source-owned Outbox', 'Integration Publisher')


def test_complex_constraint_chips_exist():
    import integration_architect_pro as app
    html = app.form_page()
    for flag in ['contract_change','many_sources','callback_webhook','exactly_once','active_active','privacy_erasure','multi_tenant','migration','shared_topic']:
        assert f"name='constraint_flags' value='{flag}'" in html
    for name, hidden_id in [
        ('business_situations','businessSituationsHidden'),('operation_kind','operationKindHidden'),('result_model','resultModelHidden'),
        ('delivery','deliveryHidden'),('load_profile','loadProfileHidden'),('sensitivity','sensitivityHidden'),('money_impact','moneyImpactHidden'),
        ('regulatory_impact','regulatoryImpactHidden'),('source_change_policy','sourceChangePolicyHidden'),('allowed_channels','allowedChannelsHidden'),
        ('forbidden_channels','forbiddenChannelsHidden'),('orchestration','orchestrationHidden'),('step_count','stepCountHidden'),
        ('chain_depth','chainDepthHidden'),('partial_response_ok','partialResponseOkHidden'),('replay','replayHidden'),('retention','retentionHidden'),
        ('current_controls','currentControlsHidden'),('kafka_topology','kafkaTopologyHidden'),('consistency','consistencyHidden')]:
        assert f"name='{name}'" in html
        assert f"id='{hidden_id}'" in html
    assert 'const specializedIsReal=!!(specialized&&specialized!==c)' in html
    assert 'if(!specializedIsReal){schema=businessTechnicalSchema(schema);}' in html


def test_specialized_explanation_matches_schema():
    saga = run({'simple_situation':'async_worker','business_case':'long_process','business_constraints_json':'["compensation","money"]'})
    assert_contains(saga['markdown'], 'state machine', 'compensation_failed', 'manual recovery')
    shared = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["no_new_topic","many_consumers"]'})
    assert_contains(shared['markdown'], 'filtering', 'discard rate', 'consumer lag')
    callback = run({'simple_situation':'callback','business_case':'external_check','business_result_timing':'Внешняя система ответит позже'})
    assert_contains(callback['markdown'], 'Callback API', 'Inbox', 'idempotent callback')


def test_full_report_no_readiness_contradiction():
    import integration_architect_pro as app
    res = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["money","highload","active_active"]'})
    html = app.result_page(res, 'rid', 'report.md')
    combined = res['markdown'] + html
    assert not ('Готовность требований: 100%' in combined and 'Готовность требований: 0%' in combined)
    assert not ('GREEN' in combined and ('RED / Решение заблокировано' in combined or 'Решение заблокировано' in combined))


def test_specialized_risks_are_case_specific():
    active = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["money","highload","active_active"]'})
    assert_contains(active['markdown'], 'split-brain', 'double spend')
    privacy = run({'simple_situation':'async_worker','business_case':'application_creation','business_constraints_json':'["pii","regulatory","privacy_erasure"]'})
    assert_contains(privacy['markdown'], 'legal hold', 'retention exception')
    shared = run({'simple_situation':'event_kafka','business_case':'data_change_distribution','business_constraints_json':'["no_new_topic","many_consumers"]'})
    assert_contains(shared['markdown'], 'discard rate', 'consumer lag')


def test_custom_technical_chain_overrides_canonical_schema():
    custom_schema = 'Custom A → Custom B → Custom C'
    res = run({
        'simple_situation': 'event_kafka',
        'business_case': 'data_change_distribution',
        'business_constraints_json': '["no_new_topic","many_consumers"]',
        'custom_chain_json': json.dumps({'schema': custom_schema}, ensure_ascii=False),
    })
    assert res['specialized_case'] == 'shared_topic_selective_consumer'
    assert res['case_schema'] == custom_schema
    assert custom_schema in res['markdown']
    assert 'shared_topic_selective_consumer' in res['markdown']
    assert 'Shared Event Stream → Selective Consumer' not in res['case_schema']


def test_business_first_readiness_line_is_not_duplicated():
    res = run({'simple_situation':'callback','business_case':'external_check','business_result_timing':'Внешняя система ответит позже'})
    assert res['markdown'].count('Готовность требований') == 1
