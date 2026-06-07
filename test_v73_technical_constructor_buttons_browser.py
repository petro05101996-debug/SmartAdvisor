import json
import os

import pytest

from ui_browser_test_helpers import active_step, chromium_page, click_next, hidden_json, running_app, start_flow

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')


def _schema(page):
    return json.loads(page.locator('#customChainJson').input_value())


def test_technical_constructor_buttons_and_presets_browser():
    with running_app() as url, chromium_page(url) as (page, js_errors):
        start_flow(page)
        click_next(page, 1)
        page.locator("[data-business-preset='deferred_application']").click()
        click_next(page, 2)
        click_next(page, 3)
        assert active_step(page) == '3'
        page.locator('#openTechnicalConstructor').click()
        assert active_step(page) == '3'
        page.locator('#addParticipantBtn').click()
        page.locator('#addParticipantBtn').click()
        page.locator('#addConnectionBtn').click()
        chain = _schema(page)
        assert len(chain['participants']) == 2
        assert len(chain['connections']) == 1
        hidden_json(page, '#processGraphJson')
        page.locator('#addConnectionBtn').click()
        assert len(_schema(page)['connections']) == 1
        assert page.locator('#builderMessage').inner_text() == 'Такая связь уже есть'
        page.locator('#connType').select_option(label='Передать событие')
        page.locator('#connError').select_option(label='Отправить в ручной разбор')
        page.locator('#addConnectionBtn').click()
        assert any(c['type'] == 'Передать событие' for c in _schema(page)['connections'])
        page.locator('#connectionList [data-del-conn]').first.click()
        assert len(_schema(page)['connections']) >= 1
        page.locator('#participantList [data-del-part]').first.click()
        assert len(_schema(page)['participants']) >= 1
        page.locator('#resetCustomChainBtn').click()
        assert _schema(page)['participants'] == []

        presets = {
            'async': ['Service API', 'integration_task DB', 'Worker'],
            'kafka': ['Outbox', 'Event Stream', 'Inbox'],
            'status': ['UI', 'Status Aggregation', 'Cache'],
            'legacy': ['Legacy System', 'File Export', 'Validation/Checksum'],
        }
        for preset, expected_nodes in presets.items():
            page.locator(f"[data-chain-preset='{preset}']").click()
            payload = _schema(page)
            names = ' '.join(p['name'] for p in payload['participants'])
            for node in expected_nodes:
                assert node in names
            for selector in ['#systemsMatrixHidden', '#processStepsHidden', '#targetIntegrationHidden', '#processGraphJson']:
                assert page.locator(selector).input_value().strip()
            assert expected_nodes[0] in page.locator('#manualDiagram').inner_text()
            assert expected_nodes[0] in page.locator('#autoSchemeReview').inner_text()
        assert not js_errors
