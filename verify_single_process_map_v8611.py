# -*- coding: utf-8 -*-
"""Проверка, что на этапе связей нет двух конкурирующих схем."""
import re, shutil
from playwright.sync_api import sync_playwright, expect
import ui

html = ui.form_page()

def launch(p):
    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width":390,"height":844})
    page.set_default_timeout(7000)
    page.set_content(html, wait_until='load')

    for text in ['Добавить инициатора','Добавить сервис процесса','Добавить внешнюю систему','Добавить хранилище состояния','Добавить аналитику','Добавить ручной разбор']:
        page.get_by_text(text, exact=False).first.click()
    page.get_by_role('button', name=re.compile('Дальше: связи')).click()

    expect(page.get_by_text('Живая схема взаимодействий')).not_to_be_visible()
    expect(page.get_by_text('Единая схема процесса').first).to_be_visible()
    expect(page.locator('#chainList')).not_to_be_visible()
    expect(page.locator('.human-step-adder')).not_to_be_visible()

    def add(src,tgt,action,timing,result,basis):
        page.locator('#interactionSource').select_option(value=src)
        page.locator('#interactionTarget').select_option(value=tgt)
        page.locator('#interactionAction').select_option(action)
        page.locator('#interactionTiming').select_option(timing)
        page.locator('#interactionResult').select_option(result)
        page.locator('#interactionBasis').select_option(label=basis)
        page.get_by_role('button', name='Добавить связь в цепочку').click()

    add('Система-инициатор','Сервис процесса','send_data','sync','pass_next','результат предыдущего взаимодействия')
    add('Сервис процесса','Внешняя система / партнёр','request_data','sync','save','после ответа внешней системы')
    add('Сервис процесса','Хранилище состояния процесса','save','sync','save','после сохранения состояния')

    expect(page.locator('#processMap .schema-row')).to_have_count(3)
    expect(page.locator('#interactionSummary .relation-card')).to_have_count(3)
    expect(page.locator('#chainList')).not_to_be_visible()
    overflow = page.evaluate('Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)-window.innerWidth')
    assert overflow <= 4, overflow
    browser.close()
    print('single_process_map=ok rows=3 overflow=', overflow)
