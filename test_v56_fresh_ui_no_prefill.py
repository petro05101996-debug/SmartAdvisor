import shutil

import pytest
from playwright.sync_api import sync_playwright

from integration_architect_pro import form_page


@pytest.mark.skipif(shutil.which('chromium') is None, reason='system chromium not installed')
def test_fresh_ui_has_no_previous_process_prefill_until_user_selects_scenario():
    html = form_page()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1365, 'height': 900})
        page.set_content(html, wait_until='domcontentloaded')
        assert page.locator('#processGraphJson').input_value() == ''
        assert page.locator('details.matrix-section:visible').count() == 0
        assert page.locator('textarea:visible').count() == 0

        page.locator('#startDesignBtn').click()
        assert page.locator('.scenario-card:visible').count() >= 8
        assert page.locator('#processGraphJson').input_value() == ''
        assert page.locator('details.matrix-section:visible').count() == 0

        page.locator('.scenario-card:visible').first.click()
        assert len(page.locator('#processGraphJson').input_value()) > 100
        assert page.locator('details.matrix-section:visible').count() == 0
        browser.close()
