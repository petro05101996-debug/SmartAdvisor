import shutil

import pytest
sync_playwright = pytest.importorskip('playwright.sync_api').sync_playwright

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
        assert page.locator('.scenario-card:visible').count() == 3
        assert page.get_by_text('Спроектировать новую интеграцию').is_visible()
        assert page.get_by_text('Проверить существующее решение').is_visible()
        assert page.get_by_text('Разобрать сложный кейс').is_visible()
        assert page.locator('#processGraphJson').input_value() == ''
        assert page.locator('details.matrix-section:visible').count() == 0

        page.locator('#simpleNextBtn').click()
        situation_panel = page.locator("[data-simple-panel='1']")
        assert situation_panel.is_visible()
        assert situation_panel.locator("input[name='simple_situation']").count() == 10
        for label in [
            'Один сервис вызывает другой и ждёт ответ',
            'Нужно принять запрос сейчас, а обработать позже',
            'Нужно отправить событие об изменении данных',
            'Нужно обогатить данные перед отправкой',
            'Внешняя система ответит позже callback-ом',
            'Нужно собрать статус из нескольких систем',
            'Нужно передать данные в DWH/отчётность',
            'Есть legacy-система или файлы',
            'Kafka одна, consumer фильтрует только нужные события',
            'Не знаю, помогите выбрать',
        ]:
            assert situation_panel.get_by_text(label).is_visible()

        page.locator('#simplePrevBtn').click()
        page.locator('.scenario-card:visible').first.click()
        assert len(page.locator('#processGraphJson').input_value()) > 100
        assert page.locator('details.matrix-section:visible').count() == 0
        browser.close()
