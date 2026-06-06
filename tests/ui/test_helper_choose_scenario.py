import pytest


@pytest.mark.browser
def test_helper_choose_scenario_kafka(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.get_by_text("Не знаю, помогите выбрать").click()

    assert page.locator("#scenarioHelperPanel").is_visible()
    page.locator("#helperImmediate").select_option("no")
    page.locator("#helperManyConsumers").select_option("yes")
    page.locator("#helperExternal").select_option("no")
    assert page.locator("#helperRecommendation").is_visible()

    page.locator("#applyHelperScenarioBtn").click()
    active_text = page.locator(".scenario-card.is-active").inner_text()
    assert "Kafka" in active_text or "события" in active_text


@pytest.mark.browser
def test_helper_choose_scenario_webhook(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.get_by_text("Не знаю, помогите выбрать").click()

    page.locator("#helperImmediate").select_option("no")
    page.locator("#helperExternal").select_option("yes")
    page.locator("#applyHelperScenarioBtn").click()

    active_text = page.locator(".scenario-card.is-active").inner_text()
    assert "Webhook" in active_text or "callback" in active_text
