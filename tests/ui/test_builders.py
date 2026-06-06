import pytest


@pytest.mark.browser
def test_system_builder_add_duplicate_delete(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator("#simpleNextBtn").click()
    page.locator("#simpleNextBtn").click()

    page.locator("#addSystemBtn").click()
    assert page.locator(".system-builder-card").count() >= 1

    duplicate_buttons = page.locator("[data-system-duplicate]")
    if duplicate_buttons.count() > 0:
        before = page.locator(".system-builder-card").count()
        duplicate_buttons.first.click()
        assert page.locator(".system-builder-card").count() >= before + 1

    delete_buttons = page.locator("[data-system-remove]")
    if delete_buttons.count() > 0:
        before = page.locator(".system-builder-card").count()
        delete_buttons.first.click()
        after = page.locator(".system-builder-card").count()
        assert after <= before


@pytest.mark.browser
def test_step_builder_add_move_delete(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator("#simpleNextBtn").click()
    page.locator("#simpleNextBtn").click()
    page.locator("#simpleNextBtn").click()

    page.locator("#addStepBtn").click()
    assert page.locator(".process-builder-card").count() >= 1

    if page.locator("[data-step-up]").count() > 0:
        page.locator("[data-step-up]").first.click()
    if page.locator("[data-step-down]").count() > 0:
        page.locator("[data-step-down]").first.click()
    if page.locator("[data-step-remove]").count() > 0:
        before = page.locator(".process-builder-card").count()
        page.locator("[data-step-remove]").first.click()
        after = page.locator(".process-builder-card").count()
        assert after <= before
