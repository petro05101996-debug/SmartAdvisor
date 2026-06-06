import pytest


@pytest.mark.browser
def test_no_disabled_placeholder_buttons_in_simple_mode(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    disabled_buttons = page.locator("button:disabled").evaluate_all(
        "(els) => els.map(e => e.id || e.innerText.trim())"
    )
    assert disabled_buttons == []
