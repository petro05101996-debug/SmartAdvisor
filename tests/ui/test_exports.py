import os
import re

import pytest


@pytest.mark.browser
def test_result_download_links_return_files(page, app_server, tmp_path):
    page.goto(app_server)
    page.wait_for_selector("#startDesignBtn")
    page.locator("#startDesignBtn").click()
    page.locator("[data-scenario='kafka']").click()

    for _ in range(4):
        page.locator("#simpleNextBtn").click()

    page.locator("#simpleGenerateBtn").click()
    page.wait_for_selector("text=Короткий итог")

    for link_pattern in [r"Скачать markdown", r"Скачать JSON", r"Скачать export"]:
        with page.expect_download() as download_info:
            page.get_by_role("link", name=re.compile(link_pattern)).first.click()
        download = download_info.value
        target = tmp_path / download.suggested_filename
        download.save_as(target)
        assert target.exists()
        assert os.path.getsize(target) > 0
