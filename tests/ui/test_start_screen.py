import pytest


@pytest.mark.browser
def test_start_screen_has_only_three_main_actions(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    start = page.locator("#startScreen")

    assert start.get_by_role("button", name="Спроектировать новую интеграцию").is_visible()
    assert start.get_by_role("button", name="Проверить существующее решение").is_visible()
    assert start.get_by_role("button", name="Разобрать сложный кейс").is_visible()
    assert start.locator(".mode-choice").count() == 3
    assert start.get_by_role("button", name="Выбрать готовый пример").is_visible()
    assert start.get_by_text("Быстро разобрать задачу").count() == 0
    assert start.get_by_text("Продвинутый режим").count() == 0
    assert start.get_by_text("Глубокий / расширенный режим").count() == 0


@pytest.mark.browser
def test_start_design_opens_clean_simple_mode(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    assert page.locator("#simpleWizard").is_visible()
    assert page.locator("#progressRail").is_visible()
    assert page.locator(".legacy-wizard-compat").is_hidden()
    assert page.locator("details.section").count() >= 1

    visible_sections = page.locator("details.section").evaluate_all(
        "(els) => els.filter(e => getComputedStyle(e).display !== 'none').length"
    )
    assert visible_sections == 0
