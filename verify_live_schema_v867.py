# -*- coding: utf-8 -*-
"""Smoke-проверка живой схемы взаимодействий v8.6.7."""
import shutil
from playwright.sync_api import sync_playwright, expect
import ui

html = ui.form_page()

def launch(p):
    system = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    try:
        return p.chromium.launch(headless=True, args=['--no-sandbox'])
    except Exception:
        return p.chromium.launch(headless=True, executable_path=system, args=['--no-sandbox','--disable-dev-shm-usage'])

with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_default_timeout(10000)
    page.set_content(html, wait_until='domcontentloaded', timeout=10000)

    for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему", "Добавить хранилище состояния", "Добавить аналитику"]:
        page.get_by_role("button", name=name).click()
    page.get_by_role("button", name="Дальше: связи между участниками").click()
    expect(page.get_by_text("Живая схема взаимодействий")).to_be_visible()
    expect(page.locator('#interactionGraph')).to_contain_text('Схема появится')

    def add_link(src_idx, tgt_idx, action, timing, result):
        page.locator('#interactionSource').select_option(index=src_idx)
        page.locator('#interactionTarget').select_option(index=tgt_idx)
        page.locator('#interactionAction').select_option(action)
        page.locator('#interactionTiming').select_option(timing)
        page.locator('#interactionResult').select_option(result)
        page.get_by_role("button", name="Добавить связь в цепочку").click()

    add_link(1, 2, 'send_data', 'sync', 'pass_next')
    expect(page.locator('#interactionGraph .schema-row')).to_have_count(1)
    expect(page.locator('#processMap .schema-row')).to_have_count(1)
    expect(page.locator('#interactionGraph')).to_contain_text('Стек ещё не определён')

    add_link(2, 3, 'request_data', 'sync', 'save')
    add_link(3, 4, 'save', 'sync', 'save')
    expect(page.locator('#interactionGraph .schema-row')).to_have_count(3)
    before = page.locator('#interactionGraph').inner_text()
    assert '→' not in before or 'Стек ещё не определён' in before

    page.evaluate("generateStackRecommendations(false)")
    expect(page.locator('#processMap')).to_contain_text('Стек:')
    expect(page.locator('#interactionGraph')).to_contain_text('Стек:')

    page.get_by_role("button", name="Открыть экспертный режим").click()
    page.locator('[data-action="move-step"][data-dir="1"]').first.click()
    expect(page.locator('#processMap .schema-row')).to_have_count(3)
    assert not errors, errors
    print('live_schema_checks=ok rows=3 errors=0')
    browser.close()
