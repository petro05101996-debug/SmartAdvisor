import pytest


SCENARIOS = [
    "Спроектировать новую интеграцию",
    "Kafka / события",
    "DWH / отчётность",
    "Legacy / file exchange",
    "Webhook / callback",
    "Горячий экран статуса",
    "Финансовая / критичная операция",
    "Интеграция с внешним партнёром",
    "Спроектировать сложную E2E-цепочку",
    "Доработать production-процесс",
]


@pytest.mark.browser
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_each_scenario_can_reach_readiness(page, app_server, scenario):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.get_by_text(scenario).click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    assert page.get_by_text("Проверка перед отчётом").is_visible()
    assert page.locator("#simpleReadyScore").is_visible()
