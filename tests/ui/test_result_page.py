import re

import pytest


@pytest.mark.browser
def test_generate_report_and_exports_visible(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator("[data-scenario='kafka']").click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    page.locator("#simpleGenerateBtn").click()
    page.wait_for_selector("text=Короткий итог")

    assert page.locator("h3", has_text="Короткий итог").is_visible()
    assert page.locator("h3", has_text="Визуальная схема").is_visible()
    assert page.locator("h3", has_text="Обязательные элементы").is_visible()
    assert page.locator("h3", has_text="Риски и вопросы").is_visible()
    assert page.get_by_role("link", name=re.compile("Скачать markdown")).is_visible()
    assert page.get_by_role("link", name=re.compile("Скачать JSON")).is_visible()
    assert page.get_by_role("link", name=re.compile("Скачать export")).is_visible()
    assert page.locator("summary", has_text="Полный технический отчёт").is_visible()
