# -*- coding: utf-8 -*-
"""Playwright smoke tests for the browser UI navigation and controls."""
import os
import shutil
import subprocess
import time
from contextlib import suppress

import pytest


def _stop(proc):
    proc.terminate()
    with suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=5)
        return
    proc.kill()
    proc.wait(timeout=5)


def _playwright_api():
    pw = pytest.importorskip("playwright.sync_api")
    return pw.expect, pw.sync_playwright


def test_form_js_has_valid_syntax_for_delegated_handlers(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required to syntax-check FORM_JS')

    import ui

    assert '[.document' not in ui.FORM_JS
    assert "[...document.querySelectorAll('#steps tbody tr')]" in ui.FORM_JS
    assert "[...document.querySelectorAll(selector+' a[href^=\"#\"]')]" in ui.FORM_JS

    script = tmp_path / 'form.js'
    script.write_text(ui.FORM_JS, encoding='utf-8')
    result = subprocess.run(
        [node, '--check', str(script)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_builder_navigation_and_buttons():
    expect, sync_playwright = _playwright_api()
    port = "8125"
    env = dict(os.environ, PORT=port, HOST="127.0.0.1")
    proc = subprocess.Popen(
        ["python3", "app.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(1.2)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1366, "height": 900})

            page.goto(f"http://127.0.0.1:{port}/")

            expect(page.get_by_role("link", name="Справочник инвариантов").first).to_be_visible()
            page.get_by_role("link", name="Справочник инвариантов").first.click()
            assert "/invariants" in page.url
            expect(page.get_by_text("Список инвариантов")).to_be_visible()

            page.get_by_role("link", name="Конструктор процесса").first.click()
            assert page.url.rstrip("/").endswith(f":{port}") or page.url.endswith("/")

            page.get_by_role("button", name="Расширенный режим").click()
            expect(page.locator("body")).not_to_have_class("quick-mode")

            page.get_by_role("button", name="Быстрый режим").click()
            expect(page.locator("body")).to_have_class("quick-mode")

            page.locator("button.scenario").filter(has_text="Универсальный докатчик").click()
            expect(page.locator("#selectedScenario")).to_contain_text("Выбран сценарий")
            expect(page.locator("button.scenario.active")).to_contain_text("Универсальный докатчик")
            expect(page.locator("#p_name")).to_have_value("Универсальный докатчик запросов в системы А и Б")
            expect(page.locator("#p_lookup")).to_have_value("operUid + operationType + targetSystem")
            assert page.locator("#systems tbody tr").count() >= 5
            assert page.locator("#steps tbody tr").count() >= 5

            page.get_by_role("button", name="+ REST-вызов").click()
            assert page.locator("#steps tbody tr").count() >= 6

            page.get_by_role("button", name="Проверить архитектуру и сформировать разбор").click()
            page.wait_for_url("**/run/*", timeout=15000)
            expect(page.get_by_text("Что сделать в первую очередь")).to_be_visible()
            expect(page.get_by_role("link", name="справочник инвариантов")).to_be_visible()

            browser.close()
    finally:
        _stop(proc)


def test_buttons_with_set_content_fallback():
    expect, sync_playwright = _playwright_api()
    import ui

    html = ui.form_page()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_content(html, wait_until="load")

        page.get_by_role("button", name="Расширенный режим").click()
        expect(page.locator("body")).not_to_have_class("quick-mode")

        page.get_by_role("button", name="Быстрый режим").click()
        expect(page.locator("body")).to_have_class("quick-mode")

        page.locator("button.scenario").filter(has_text="Обратный поток статусов").click()
        expect(page.locator("#selectedScenario")).to_contain_text("Выбран сценарий")
        expect(page.locator("#p_name")).to_have_value("Обратный поток статусов от УК в банк")
        assert page.locator("#steps tbody tr").count() >= 3

        browser.close()
