# -*- coding: utf-8 -*-
"""Smoke/E2E tests for the flexible process builder UI."""
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


def _launch_chromium(p):
    try:
        return p.chromium.launch(headless=True, args=["--no-sandbox"])
    except Exception as exc:  # browser binaries may be absent in CI/container
        pytest.skip(f"Playwright Chromium is not installed: {exc}")


def test_form_js_has_valid_syntax_for_flexible_builder(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required to syntax-check FORM_JS')

    import ui

    assert "const state={mode:'quick',systems:[],steps:[]}" in ui.FORM_JS
    assert "function renderSystems()" in ui.FORM_JS
    assert "function renderSteps()" in ui.FORM_JS
    assert "function renderProcessMap()" in ui.FORM_JS
    assert "function buildPayload()" in ui.FORM_JS
    assert "dragstart" in ui.FORM_JS

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


def test_static_html_contains_flexible_builder_and_card_reference():
    import ui

    html = ui.form_page()
    assert 'id="chain-builder"' in html
    assert 'id="systemsCards"' in html
    assert 'id="chainList"' in html
    assert 'id="processMap"' in html
    assert '+ REST-вызов' in html
    assert '+ Kafka-событие' in html
    assert '+ запись в БД' in html
    assert '+ CDC' in html
    assert 'legacy-store' in html

    inv = ui.invariant_reference_page()
    assert '<details class="refcard"' in inv
    assert 'ref-content' in inv
    assert 'filterInvariants' in inv


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
            browser = _launch_chromium(p)
            page = browser.new_page(viewport={"width": 1366, "height": 900})

            page.goto(f"http://127.0.0.1:{port}/")

            expect(page.get_by_role("link", name="Справочник инвариантов").first).to_be_visible()
            page.get_by_role("link", name="Справочник инвариантов").first.click()
            assert "/invariants" in page.url
            expect(page.get_by_text("Список инвариантов")).to_be_visible()
            assert page.locator("details.refcard").count() > 10

            page.get_by_role("link", name="Конструктор процесса").first.click()
            assert page.url.rstrip("/").endswith(f":{port}") or page.url.endswith("/")

            page.get_by_role("button", name="Экспертный режим").click()
            expect(page.locator("body")).not_to_have_class("quick-mode")

            page.get_by_role("button", name="Простой режим").click()
            expect(page.locator("body")).to_have_class("quick-mode")

            page.locator("button.scenario").filter(has_text="Универсальный докатчик").click()
            expect(page.locator("#selectedScenario")).to_contain_text("Выбран сценарий")
            expect(page.locator("button.scenario.active")).to_contain_text("Универсальный докатчик")
            expect(page.locator("#p_name")).to_have_value("Универсальный докатчик запросов в системы А и Б")
            expect(page.locator("#p_lookup")).to_have_value("operUid + operationType + targetSystem")
            assert page.locator(".system-card").count() >= 5
            assert page.locator(".chain-component").count() >= 5
            expect(page.locator("#processMap")).to_contain_text("Система А")

            before = page.locator(".chain-component").count()
            page.get_by_role("button", name="+ REST-вызов").click()
            assert page.locator(".chain-component").count() == before + 1

            page.locator(".chain-component").last.get_by_title("Копировать").click()
            assert page.locator(".chain-component").count() == before + 2

            page.locator(".chain-component").last.get_by_title("Удалить").click()
            assert page.locator(".chain-component").count() == before + 1

            page.get_by_role("button", name="Проверить архитектуру").click()
            page.wait_for_url("**/run/*", timeout=15000)
            expect(page.get_by_text("Что сделать в первую очередь")).to_be_visible()
            expect(page.get_by_role("link", name="справочник инвариантов")).to_be_visible()

            browser.close()
    finally:
        _stop(proc)


def test_mobile_layout_and_reference_cards_with_set_content():
    expect, sync_playwright = _playwright_api()
    import ui

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_content(ui.form_page(), wait_until="load")

        page.locator("button.scenario").filter(has_text="Обратный поток статусов").click()
        expect(page.locator("#chain-builder")).to_be_visible()
        assert page.locator(".chain-component").count() >= 4
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

        inv_page = browser.new_page(viewport={"width": 390, "height": 844})
        inv_page.set_content(ui.invariant_reference_page(), wait_until="load")
        assert inv_page.locator("details.refcard").count() > 10
        assert inv_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

        browser.close()
