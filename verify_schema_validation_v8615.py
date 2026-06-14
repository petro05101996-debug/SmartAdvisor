# -*- coding: utf-8 -*-
from pathlib import Path
import re, shutil
from playwright.sync_api import sync_playwright
import ui

html = ui.form_page()
checks=[]
def ok(name, details=''): checks.append(('OK', name, details))
def fail(name, details=''): checks.append(('FAIL', name, details))
def launch(p):
    exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

with sync_playwright() as p:
    browser=launch(p)
    page=browser.new_page(viewport={'width':390,'height':844})
    page.set_default_timeout(7000)
    console=[]
    page.on('console', lambda msg: console.append((msg.type,msg.text)))
    page.on('pageerror', lambda exc: console.append(('pageerror',str(exc))))
    page.set_content(html, wait_until='load')
    page.wait_for_timeout(400)
    for text in ['Добавить инициатора','Добавить сервис процесса','Добавить внешнюю систему','Добавить хранилище состояния']:
        page.get_by_text(text, exact=False).first.click()
    page.get_by_role('button', name=re.compile('Дальше: связи')).click()
    page.select_option('#interactionSource', value='Сервис процесса')
    page.select_option('#interactionTarget', value='Внешняя система / партнёр')
    page.select_option('#interactionAction', value='send_data')
    page.select_option('#interactionTiming', value='sync')
    page.get_by_role('button', name='Добавить связь в цепочку').click()
    page.wait_for_timeout(200)
    # Имитируем ошибку пользователя/эксперта: связь названа как внешняя, но получатель стал БД.
    step_id = page.locator('[data-step-field="target_system"]').first.get_attribute('data-id')
    page.evaluate("([id,val])=>{ updateStep(id,'target_system',val); }", [step_id, 'Хранилище состояния процесса'])
    page.wait_for_timeout(100)
    page.locator('[data-action="flow-stage"][data-stage="stack"]').click(force=True)
    page.wait_for_timeout(100)
    page.locator('[data-action="generate-stack"]').first.click()
    page.wait_for_timeout(300)
    body=page.locator('body').inner_text()
    if 'Перед подбором стека проверьте логику схемы' in body and 'Внешняя связь ведёт в хранилище' in body:
        ok('validation_blocks_bad_schema')
    else:
        fail('validation_blocks_bad_schema', body[:500])
    # Схема должна быть минимальной: без тегов стека/зависимостей в единой схеме.
    map_text=page.locator('#processMap').inner_text()
    if 'Стек:' not in map_text and 'после шага' not in map_text and 'Связь выглядит корректно' not in map_text:
        ok('minimal_process_map')
    else:
        fail('minimal_process_map', map_text)
    if page.locator('[data-action="apply-schema-fixes"]').count():
        page.locator('[data-action="apply-schema-fixes"]').click()
        page.wait_for_timeout(300)
        ok('apply_fixes_button_visible')
    else:
        fail('apply_fixes_button_visible')
    page.locator('[data-action="generate-stack"]').first.click()
    page.wait_for_timeout(400)
    body2=page.locator('body').inner_text()
    if 'Стек сформирован' in body2 and 'Перед подбором стека проверьте логику схемы' not in body2:
        ok('stack_after_fix')
    else:
        fail('stack_after_fix', body2[:800])
    errs=[x for x in console if x[0] in ('error','pageerror')]
    if errs: fail('console_errors', str(errs[:5]))
    else: ok('console_errors','0')
    browser.close()

lines=['# Проверка минимальной схемы и валидации перед стеком v8.6.15','']
for st,name,details in checks:
    lines.append(f'- {st}: {name}' + (f' — {details}' if details else ''))
lines.append('')
lines.append(f"SUMMARY: {sum(1 for x,_,__ in checks if x=='OK')} ok, {sum(1 for x,_,__ in checks if x!='OK')} fail")
Path('SCHEMA_VALIDATION_v8_6_15.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
if any(x!='OK' for x,_,__ in checks):
    raise SystemExit(1)
