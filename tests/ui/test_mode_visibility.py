import pytest


@pytest.mark.browser
def test_simple_mode_visibility_contract(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    hidden_selectors = [
        "#progressRail",
        ".legacy-wizard-compat",
        ".quick-mode-panel",
        ".ultra-panel",
        ".beginner-panel",
        ".sticky-submit",
    ]
    for selector in hidden_selectors:
        if page.locator(selector).count() > 0:
            assert page.locator(selector).is_hidden(), f"{selector} should be hidden in simple-mode"


@pytest.mark.browser
def test_expert_mode_visibility_contract(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startExpertBtn").click()

    assert page.locator(".legacy-wizard-compat").is_visible()
    visible_sections = page.locator("details.section").evaluate_all(
        "(els) => els.filter(e => getComputedStyle(e).display !== 'none').length"
    )
    assert visible_sections > 0
