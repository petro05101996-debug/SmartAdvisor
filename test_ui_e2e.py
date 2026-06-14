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
    """Launch Playwright browser. Prefer bundled Chromium, fall back to system Chromium.

This keeps the UI smoke test useful in CI containers where Playwright is installed
but browser binaries were not downloaded.
"""
    try:
        return p.chromium.launch(headless=True, args=["--no-sandbox"])
    except Exception as first_exc:
        system_chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if system_chromium:
            try:
                return p.chromium.launch(headless=True, executable_path=system_chromium, args=["--no-sandbox", "--disable-dev-shm-usage"])
            except Exception as second_exc:
                pytest.skip(f"Playwright Chromium is not available: {first_exc}; system browser failed: {second_exc}")
        pytest.skip(f"Playwright Chromium is not installed: {first_exc}")


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
    assert 'id="complexity-modules"' in html
    assert 'data-action="module"' in html
    assert 'Есть аналитическое хранилище' in html
    assert 'Могут быть дубли' in html
    assert 'id="chain-builder"' in html
    assert 'id="systemsCards"' in html
    assert 'id="chainList"' in html
    assert 'id="processMap"' in html
    assert 'Вызвать систему и ждать ответ' in html
    assert 'Отправить событие, результат будет позже' in html
    assert 'Сохранить данные/статус' in html
    assert 'Передать изменения в аналитику' in html
    assert 'legacy-store' in html

    inv = ui.invariant_reference_page()
    assert '<details class="refcard"' in inv
    assert 'ref-content' in inv
    assert 'filterInvariants' in inv


def test_builder_navigation_and_buttons():
    expect, sync_playwright = _playwright_api()
    import ui

    html = ui.form_page().replace(
        "</head>",
        """<script>
        window.__submittedPayloads = [];
        window.fetch = async function(url, opts) {
          if (String(url).includes('/api/analyze')) {
            try { window.__submittedPayloads.push(JSON.parse(opts && opts.body || '{}')); } catch (e) { window.__submittedPayloads.push({parseError: String(e)}); }
            return new Response(JSON.stringify({ok:true,id:'ui-test-run'}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          return new Response('{}', {status:200, headers:{'Content-Type':'application/json'}});
        };
        </script></head>""",
    )

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(7000)
        page.set_content(html, wait_until="load")

        # Новый основной путь: сначала участники, никаких карточек старого wizard на экране.
        expect(page.get_by_role("heading", name="1. Участники процесса")).to_be_visible()
        expect(page.get_by_text("Сначала определите участников.")).to_be_visible()
        expect(page.get_by_role("heading", name="1. Соберите цепочку из универсальных вариантов")).not_to_be_visible()
        expect(page.get_by_text("REST API — синхронный вызов")).not_to_be_visible()

        for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему", "Добавить хранилище состояния", "Добавить аналитику"]:
            page.get_by_role("button", name=name).click()
        expect(page.locator("#systemSummarySimple")).to_contain_text("Участники процесса определены")

        page.get_by_role("button", name="Дальше: связи между участниками").click()
        expect(page.get_by_role("heading", name="2. Порядок взаимодействия между участниками")).to_be_visible()
        expect(page.get_by_role("heading", name="4. Формирование стека")).not_to_be_visible()

        # Строим цепочку через связи между участниками, а не через технологические элементы.
        def add_link(src_idx, tgt_idx, action, timing, result):
            page.locator('#interactionSource').select_option(index=src_idx)
            page.locator('#interactionTarget').select_option(index=tgt_idx)
            page.locator('#interactionAction').select_option(action)
            page.locator('#interactionTiming').select_option(timing)
            page.locator('#interactionResult').select_option(result)
            page.get_by_role("button", name="Добавить связь в цепочку").click()

        add_link(1, 2, 'send_data', 'sync', 'pass_next')
        add_link(2, 3, 'request_data', 'sync', 'save')
        add_link(2, 4, 'save', 'sync', 'save')
        add_link(4, 5, 'compare', 'background', 'check')
        expect(page.locator("#chainList .chain-component")).to_have_count(4)
        expect(page.get_by_text("стек ещё не определён").first).to_be_visible()

        page.get_by_role("button", name="Дальше: уточнения").click()
        page.locator('[data-action="module"][data-module="fast_read"]').click()
        page.locator('[data-action="module"][data-module="dwh"]').click()
        page.locator('[data-action="module"][data-module="event_history"]').click()

        page.get_by_role("button", name="Определить стек по процессу").click()
        expect(page.get_by_text("Предложенный стек:").first).to_be_visible()
        expect(page.locator(".channel-chip").first).to_be_visible()

        page.get_by_role("button", name="Открыть экспертный режим").click()
        expect(page.locator("body")).not_to_have_class("quick-mode")
        page.locator('[data-action="move-step"][data-dir="1"]').first.click()
        page.locator('[data-action="duplicate-step"]').first.click()
        page.evaluate('document.querySelectorAll("details").forEach(d => d.open = true)')
        if page.locator('[data-action="set-channel"][data-channel="rabbitmq"]').count() > 0:
            page.locator('[data-action="set-channel"][data-channel="rabbitmq"]').first.click()
            page.locator('[data-action="auto-channel"]').first.click()

        page.get_by_role("button", name="Проверить архитектуру").click()
        page.wait_for_timeout(500)
        submitted = page.evaluate("window.__submittedPayloads.length")
        assert submitted == 1
        payload = page.evaluate("window.__submittedPayloads[0]")
        assert len(payload.get("steps", [])) >= 4
        assert len(payload.get("systems", [])) >= 5
        sysnames = {s["name"] for s in payload.get("systems", [])}
        for idx, step in enumerate(payload.get("steps", []), start=1):
            for field in ("source_system", "system", "target_system"):
                assert not step.get(field) or step[field] in sysnames
            deps = [int(x.strip()) for x in str(step.get("depends_on", "")).replace(";", ",").split(",") if x.strip().isdigit()]
            assert idx not in deps
            assert all(1 <= d <= len(payload.get("steps", [])) for d in deps)

        browser.close()


def test_mobile_layout_and_reference_cards_with_set_content():
    expect, sync_playwright = _playwright_api()
    import ui

    with sync_playwright() as p:
        browser = _launch_chromium(p)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_content(ui.form_page(), wait_until="load")

        expect(page.get_by_role("heading", name="1. Участники процесса")).to_be_visible()
        for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему"]:
            page.get_by_role("button", name=name).click()
        page.get_by_role("button", name="Дальше: связи между участниками").click()
        page.locator('#interactionSource').select_option(index=1)
        page.locator('#interactionTarget').select_option(index=2)
        page.get_by_role("button", name="Добавить связь в цепочку").click()
        expect(page.locator("#chain-builder")).to_be_visible()
        assert page.locator(".chain-component").count() >= 1
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

        inv_page = browser.new_page(viewport={"width": 390, "height": 844})
        inv_page.set_content(ui.invariant_reference_page(), wait_until="load")
        assert inv_page.locator("details.refcard").count() > 10
        assert inv_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")

        browser.close()
