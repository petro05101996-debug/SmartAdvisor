import pytest


@pytest.mark.browser
def test_expert_mode_shows_legacy_and_sections(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startExpertBtn").click()

    assert page.locator(".legacy-wizard-compat").is_visible()
    visible_sections = page.locator("details.section").evaluate_all(
        "(els) => els.filter(e => getComputedStyle(e).display !== 'none').length"
    )
    assert visible_sections > 0
    assert page.locator(".sticky-submit button[type='submit']").is_visible()
