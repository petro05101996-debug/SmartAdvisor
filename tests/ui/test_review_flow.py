import pytest


@pytest.mark.browser
def test_review_mode_opens_audit_flow(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startReviewBtn").click()

    assert page.locator("#simpleWizard").is_visible()
    active = page.locator(".scenario-card.is-active").inner_text()
    assert "Проверить существующее решение" in active or "аудит" in active.lower()
    assert page.locator("#progressRail").is_hidden()
    assert page.locator(".legacy-wizard-compat").is_hidden()
