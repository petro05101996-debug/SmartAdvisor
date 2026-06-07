import os

import pytest

from ui_browser_test_helpers import chromium_page, click_next, running_app, start_flow

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')

CASES = [
    ('application_creation', 'async_worker'),
    ('data_change_distribution', 'event_kafka'),
    ('external_check', 'callback'),
    ('data_enrichment', 'enrichment_kafka'),
    ('status_screen', 'status_aggregation'),
    ('reporting', 'dwh'),
    ('legacy_file', 'legacy_file'),
    ('audit', 'audit'),
    ('long_process', 'async_worker'),
]


@pytest.mark.parametrize('business_case, expected_simple', CASES)
def test_all_business_cases_minimal_flow_browser(business_case, expected_simple):
    with running_app() as url, chromium_page(url) as (page, js_errors):
        start_flow(page, business_case)
        assert page.locator('#businessCaseHidden').input_value() == business_case
        assert page.locator('#simpleSituationHidden').input_value() == expected_simple
        click_next(page, 1)
        page.locator('#addBusinessActorBtn').click()
        page.locator('#addBusinessStepBtn').click()
        click_next(page, 2)
        click_next(page, 3)
        click_next(page, 4)
        click_next(page, 5)
        result = page.locator('section[data-constructor-screen="5"]').inner_text()
        for text in ['Бизнес-процесс', 'Схема взаимодействия', 'Что обязательно сделать', 'Главные риски']:
            assert text in result
        assert page.locator('#businessCaseHidden').input_value() == business_case
        assert page.locator('#simpleSituationHidden').input_value() == expected_simple
        assert not js_errors
