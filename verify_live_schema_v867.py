# -*- coding: utf-8 -*-
"""Совместимая проверка схемы: с v8.6.11 видимой является одна схема процесса."""
import re, shutil
from playwright.sync_api import sync_playwright, expect
import ui

html = ui.form_page()

def launch(p):
    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width":1366,"height":900})
    page.set_default_timeout(10000)
    page.set_content(html, wait_until='domcontentloaded')
    for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему", "Добавить хранилище состояния", "Добавить аналитику"]:
        page.get_by_role("button", name=name).click()
    page.get_by_role("button", name=re.compile('Дальше: связи')).click()
    expect(page.get_by_text("Живая схема взаимодействий")).not_to_be_visible()
    expect(page.get_by_text("Единая схема процесса").first).to_be_visible()

    def add_link(src_idx, tgt_idx, action, timing, result):
        page.locator('#interactionSource').select_option(index=src_idx)
        page.locator('#interactionTarget').select_option(index=tgt_idx)
        page.locator('#interactionAction').select_option(action)
        page.locator('#interactionTiming').select_option(timing)
        page.locator('#interactionResult').select_option(result)
        page.get_by_role("button", name="Добавить связь в цепочку").click()

    add_link(1, 2, 'send_data', 'sync', 'pass_next')
    add_link(2, 3, 'request_data', 'sync', 'save')
    add_link(3, 4, 'save', 'sync', 'save')
    expect(page.locator('#processMap .schema-row')).to_have_count(3)
    expect(page.locator('#interactionSummary .relation-card')).to_have_count(3)
    page.evaluate("generateStackRecommendations(false)")
    expect(page.locator('#processMap')).to_contain_text('Стек:')
    browser.close()
    print('single_visible_schema_checks=ok rows=3')
