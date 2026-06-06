import pytest


@pytest.mark.browser
def test_simple_design_flow_kafka_to_readiness(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    assert page.get_by_text("Что нужно сделать?").is_visible()
    page.get_by_text("Kafka / события").click()
    page.locator("#simpleNextBtn").click()

    assert page.get_by_text("Что происходит в бизнесе").is_visible()
    page.locator("#simpleNextBtn").click()
    assert page.get_by_text("Какие системы участвуют").is_visible()

    page.locator("#addSystemBtn").click()
    assert page.locator("#systemBuilder").is_visible()

    page.locator("#simpleNextBtn").click()
    assert page.get_by_text("Как идёт процесс").is_visible()

    page.locator("#applyChainTemplateBtn").click()
    page.locator("#addStepBtn").click()

    page.locator("#simpleNextBtn").click()
    assert page.get_by_text("Проверка перед отчётом").is_visible()
    assert page.locator("#simpleReadyScore").is_visible()
    assert page.locator("#simpleGenerateBtn").is_visible()


@pytest.mark.browser
def test_simple_design_no_legacy_blocks_visible(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    assert page.locator("#simpleWizard").is_visible()
    assert page.locator(".legacy-wizard-compat").is_hidden()
    assert page.locator("#progressRail").is_hidden()
    assert page.locator(".quick-mode-panel").evaluate("(e) => getComputedStyle(e).display !== 'none'") is False
