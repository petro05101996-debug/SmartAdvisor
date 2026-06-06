import pytest


SCENARIOS = [
    ("Спроектировать новую интеграцию", "new_rest"),
    ("Kafka / события", "kafka"),
    ("DWH / отчётность", "dwh"),
    ("Legacy / file exchange", "legacy_file"),
    ("Webhook / callback", "webhook"),
    ("Горячий экран статуса", "hot_status"),
    ("Финансовая / критичная операция", "financial"),
    ("Интеграция с внешним партнёром", "external_partner"),
    ("Спроектировать сложную E2E-цепочку", "e2e"),
    ("Доработать production-процесс", "production"),
]


@pytest.mark.browser
@pytest.mark.parametrize("_label,scenario_id", SCENARIOS)
def test_each_scenario_can_reach_readiness(page, app_server, _label, scenario_id):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator(f"[data-scenario='{scenario_id}']").click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    assert page.locator("[data-simple-panel='4'] h3").is_visible()
    assert page.locator("#simpleReadyScore").is_visible()
