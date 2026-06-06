import shutil

import pytest
from playwright.sync_api import sync_playwright

from integration_architect_pro import form_page


@pytest.mark.skipif(shutil.which('chromium') is None, reason='system chromium not installed')
def test_service2_worker_template_is_one_click_and_deep_mode_has_no_prechecked_risks():
    html = form_page()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1365, 'height': 900})
        page.set_content(html, wait_until='domcontentloaded')
        page.locator('#startDesignBtn').click()

        page.locator(".scenario-card[data-scenario='service2_worker']").click()
        assert page.locator('#processGraphJson').input_value().find('Worker сервиса 2') > -1
        assert page.locator('#processGraphJson').input_value().find('Сервис 3') > -1
        assert page.locator('#simpleChainTemplate').input_value() == 'service2_async_worker'
        assert page.locator('.complex-flow-node:visible').count() >= 5
        assert page.locator('details.matrix-section:visible').count() == 0

        page.locator('#backToStart').click()
        page.locator('#startExpertBtn').click()
        # Deep mode is simple too: no raw matrices and no prechecked risk chips from previous defaults.
        assert page.locator('details.matrix-section:visible').count() == 0
        assert page.locator("input[name='risk_duplicate_event']:checked").count() == 0
        assert page.locator("input[name='risk_lost_event']:checked").count() == 0
        assert page.locator("input[name='risk_external_timeout']:checked").count() == 0
        assert page.locator("input[name='risk_traceability']:checked").count() == 0
        browser.close()


@pytest.mark.skipif(shutil.which('chromium') is None, reason='system chromium not installed')
def test_help_me_choose_recommends_worker_chain_when_user_can_process_later():
    html = form_page()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 390, 'height': 900})
        page.set_content(html, wait_until='domcontentloaded')
        page.locator('#startDesignBtn').click()
        page.locator(".scenario-card[data-scenario='help_me_choose']").click()
        page.locator('#helperImmediate').select_option('no')
        page.locator('#helperSaveOrReport').select_option('save')
        page.locator('#helperExternal').select_option('no')
        assert 'worker' in page.locator('#helperRecommendation').inner_text().lower()
        page.locator('#applyHelperScenarioBtn').click()
        assert 'Worker сервиса 2' in page.locator('#processGraphJson').input_value()
        # Mobile: the graph should be visible and not force broad horizontal overflow.
        assert page.locator('.complex-flow-node:visible').count() >= 5
        overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 25')
        assert not overflow
        browser.close()
