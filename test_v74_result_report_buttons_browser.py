import os

import pytest

from ui_browser_test_helpers import chromium_page, click_next, go_to_result_with_preset, running_app

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')


def test_result_report_buttons_browser():
    with running_app() as url, chromium_page(url) as (page, js_errors):
        go_to_result_with_preset(page, 'deferred_application')
        page.locator('#prevBtn').click()
        page.locator("section.constructor-screen.is-active[data-constructor-screen='4']").wait_for()
        click_next(page, 5)
        details = page.locator('section[data-constructor-screen="5"] details.legacy-questions-details')
        assert not details.evaluate('e => e.open')
        details.locator('summary').click()
        assert details.evaluate('e => e.open')
        page.locator('#submitBtn').click()
        page.wait_for_load_state('networkidle')
        body = page.locator('body').inner_text()
        for text in ['Бизнес-процесс', 'Схема взаимодействия', 'Почему выбрана такая техническая схема', 'Что обязательно сделать', 'Главные риски', 'Что отдать разработке']:
            assert text in body
        page.get_by_text('Открыть полный отчёт').click()
        assert page.locator('details.full-report').first.evaluate('e => e.open')
        download_links = page.locator("a[href^='/download']")
        if download_links.count():
            with page.expect_download(timeout=10000) as download_info:
                download_links.first.click()
            assert download_info.value.suggested_filename
        assert not js_errors
