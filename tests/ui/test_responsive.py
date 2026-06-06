import pytest


VIEWPORTS = [
    (360, 740),
    (390, 844),
    (768, 1024),
    (1024, 768),
    (1440, 900),
]


@pytest.mark.browser
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_simple_mode_no_horizontal_scroll(page, app_server, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()

    has_horizontal_scroll = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert has_horizontal_scroll is False
    assert page.locator("#simpleWizard").is_visible()
    assert page.locator("#simpleNextBtn").is_visible()


@pytest.mark.browser
@pytest.mark.parametrize("width,height", VIEWPORTS)
def test_result_page_no_horizontal_scroll(page, app_server, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator("[data-scenario='kafka']").click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    page.locator("#simpleGenerateBtn").click()
    page.wait_for_selector("text=Короткий итог")

    has_horizontal_scroll = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert has_horizontal_scroll is False
