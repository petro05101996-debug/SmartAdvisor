import pytest


@pytest.mark.browser
def test_generate_report_and_exports_visible(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.get_by_text("Kafka / события").click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    page.locator("#simpleGenerateBtn").click()
    page.wait_for_selector("text=Короткий итог")

    assert page.get_by_text("Короткий итог").is_visible()
    assert page.get_by_text("Визуальная схема").is_visible()
    assert page.get_by_text("Обязательные элементы").is_visible()
    assert page.get_by_text("Риски").is_visible()
    assert page.get_by_text("Скачать markdown").is_visible()
    assert page.get_by_text("Скачать JSON").is_visible()
    assert page.get_by_text("Скачать export").is_visible()
    assert page.get_by_text("Полный технический отчёт").is_visible()
