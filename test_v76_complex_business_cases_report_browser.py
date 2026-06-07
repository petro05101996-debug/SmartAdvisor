import os

import pytest

from ui_browser_test_helpers import chromium_page, click_next, running_app, start_flow

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')

CASES = [
    ('long_process', ['compensation', 'money'], 'saga_state_machine', ['Process State DB', 'Compensation / Manual Recovery']),
    ('data_change_distribution', ['no_new_topic', 'highload', 'many_consumers'], 'shared_topic_selective_consumer', ['Shared Event Stream', 'DLQ/Reprocess']),
    ('data_enrichment', ['source_locked'], 'enrichment_before_kafka', ['Source-owned Outbox', 'Integration Publisher']),
    ('external_check', ['unstable_external'], 'webhook_intake', ['Callback API', 'Inbox']),
    ('status_screen', ['many_sources', 'highload'], 'bff_api_composition', ['BFF/API Composition', 'Partial Response']),
    ('reporting', ['replay', 'regulatory'], 'dwh_pipeline', ['Staging', 'DWH/Reporting']),
    ('legacy_file', [], 'batch_file_exchange', ['Manifest/Checksum', 'Quarantine/Target']),
    ('audit', ['contract_change'], 'contract_required_field_missing', ['Consumer Contract Tests', 'Runtime Validation']),
]

@pytest.mark.parametrize('business_case, flags, expected_case, expected_schema_bits', CASES)
def test_complex_business_cases_report_browser(business_case, flags, expected_case, expected_schema_bits):
    with running_app() as url, chromium_page(url) as (page, js_errors):
        start_flow(page, business_case)
        click_next(page, 1)
        for flag in flags:
            page.locator(f"input[name='constraint_flags'][value='{flag}']").check()
        click_next(page, 2)
        graph = page.locator('#processGraphJson').input_value()
        assert expected_case in graph
        for bit in expected_schema_bits:
            assert bit in graph
        click_next(page, 3)
        click_next(page, 4)
        click_next(page, 5)
        result = page.locator('section[data-constructor-screen="5"]').inner_text()
        assert 'Service Step' not in result
        for bit in expected_schema_bits:
            assert bit in result
        assert not js_errors


def test_complex_case_custom_technical_chain_overrides_canonical_browser():
    with running_app() as url, chromium_page(url) as (page, js_errors):
        start_flow(page, 'data_change_distribution')
        click_next(page, 1)
        page.locator("input[name='constraint_flags'][value='no_new_topic']").check()
        page.locator("input[name='constraint_flags'][value='many_consumers']").check()
        click_next(page, 2)
        assert 'shared_topic_selective_consumer' in page.locator('#processGraphJson').input_value()
        click_next(page, 3)
        page.locator('#openTechnicalConstructor').click()
        page.locator("[data-chain-preset='kafka']").click()
        assert 'Outbox' in page.locator('#customChainJson').input_value()
        click_next(page, 4)
        click_next(page, 5)
        ui_result = page.locator('section[data-constructor-screen="5"]').inner_text()
        assert 'Outbox' in ui_result
        assert 'Event Stream' in ui_result
        page.locator('#submitBtn').click()
        page.wait_for_load_state('networkidle')
        body = page.locator('body').inner_text()
        assert 'Source Service → Outbox → Event Stream → Consumer → Inbox' in body
        assert 'shared_topic_selective_consumer' in body
        assert not js_errors
