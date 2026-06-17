# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path
from contextlib import suppress

from learning import get_case, list_cases
import ui

ROOT=Path(__file__).resolve().parent
PORT=8153
BASE=f'http://127.0.0.1:{PORT}'
APP_ENV={**os.environ,'PORT':str(PORT),'HOST':'127.0.0.1','APP_DIR':str(ROOT/'appdb_saas_ui_v8653')}

def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception): proc.wait(timeout=3)
        if proc.poll() is None: proc.kill()

def http_json(path, payload=None, timeout=30):
    if payload is None:
        return json.loads(urllib.request.urlopen(BASE+path, timeout=timeout).read().decode('utf-8'))
    req=urllib.request.Request(BASE+path, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8'))

def start():
    proc=subprocess.Popen([sys.executable,'app.py'], cwd=str(ROOT), env=APP_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(BASE+'/health', timeout=1).read(); return proc
        except Exception:
            time.sleep(0.2)
    stop(proc); raise AssertionError('server did not start')

def api_checks():
    cases=http_json('/api/learning/cases')
    assert cases['ok'] and len(cases['cases'])==83
    cid='bank-credit-bki-fraud'
    ref=get_case(cid)['payload']
    ev=http_json('/api/learning/evaluate', {'case_id':cid,'mode':'reference','payload':ref}, 60)
    assert ev['ok'] and ev['learning_score']>=8.5, ev.get('learning_score')
    strong='Сначала фиксирую границы процесса и участников. Клиентский путь отделяю от асинхронной публикации. Решение сохраняю вместе с Outbox, событие отправляю в Kafka с ключом applicationId, добавляю eventId, correlationId, idempotencyKey и schemaVersion. Для БКИ и fraud задаю timeout, circuit breaker и ограниченные повторы. Для потребителей нужны DLQ, quarantine, replay, мониторинг lag, ошибок и трассировка. MVP может быть проще, но production требует контрактов, наблюдаемости и регламента повторной обработки.'
    interview=http_json('/api/learning/evaluate', {'case_id':cid,'mode':'interview','payload':ref,'answer_text':strong}, 60)
    assert interview['ok'] and interview.get('interview_score',0)>=8.5
    old=http_json('/api/analyze', ref, 60)
    assert old['ok'] and old.get('id')
    md=urllib.request.urlopen(BASE+'/run/'+old['id']+'.md', timeout=20).read().decode('utf-8')
    assert 'Архитектурный разбор' in md or 'Разбор' in md
    return {'case_count':len(cases['cases']), 'reference_score':ev['learning_score'], 'interview_score':interview['interview_score'], 'old_run':old['id']}

def browser_checks():
    """Статический браузерный прогон UI без сети: живые API проверяются отдельно.
    Это устойчивее в CI/контейнере, где Chromium иногда блокирует localhost-порты.
    """
    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception:
        return {'browser':'skipped: playwright unavailable'}
    out=[]
    screenshots=[]
    with sync_playwright() as p:
        exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
        try:
            browser=p.chromium.launch(headless=True, args=['--no-sandbox'])
        except Exception:
            if not exe:
                return {'browser':'skipped: chromium unavailable'}
            browser=p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])
        for name, vp in [('desktop',{'width':1366,'height':900}),('tablet',{'width':768,'height':1024}),('mobile',{'width':390,'height':844})]:
            page=browser.new_page(viewport=vp)
            page.set_content(ui.learning_home_page(), wait_until='load')
            expect(page.get_by_text('Практический тренажёр интеграций')).to_be_visible()
            expect(page.get_by_text('Рекомендуемые кейсы для старта')).to_be_visible()
            expect(page.locator('#caseSearch')).to_be_visible()
            page.fill('#caseSearch', 'Kafka')
            page.evaluate('filterCases()')
            vals=page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth, cards:[...document.querySelectorAll('#learningGrid .learning-card:not(.hidden-by-saas)')].length})")
            assert vals['sw'] <= vals['cw'] + 2, (name,'home_overflow',vals)
            assert vals['cards'] > 0, (name,'filter_no_cards')
            if name=='desktop':
                shot=str(ROOT/f'SAAS_UI_HOME_v8653_{name}.png'); page.screenshot(path=shot, full_page=True); screenshots.append(shot)
            page.set_content(ui.learning_case_page('bank-credit-bki-fraud'), wait_until='load')
            expect(page.get_by_text('Соберите решение без JSON')).to_be_visible()
            expect(page.get_by_text('Проверить моё решение')).to_be_visible()
            expect(page.get_by_text('Режим собеседования')).to_be_visible()
            vals=page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert vals['sw'] <= vals['cw'] + 2, (name,'case_overflow',vals)
            page.get_by_text('Собрать слабый черновик для проверки').click()
            weak_len=page.evaluate("() => (document.getElementById('solutionJson').value||'').length")
            assert weak_len > 50
            page.get_by_text('Подставить эталон').click()
            ref_text=page.evaluate("() => document.getElementById('solutionJson').value")
            assert 'Outbox' in ref_text or 'Kafka' in ref_text
            if name=='desktop':
                shot=str(ROOT/f'SAAS_UI_CASE_v8653_{name}.png'); page.screenshot(path=shot, full_page=True); screenshots.append(shot)
            out.append({'viewport':name,'home_overflow':False,'case_overflow':False,'filter':'ok','visual_builder':'ok'})
            page.close()
        browser.close()
    return {'browser':'ok','viewports':out,'screenshots':screenshots}

if __name__=='__main__':
    proc=start()
    try:
        result={'ok':True,'api':api_checks(),'browser':browser_checks()}
        Path('SAAS_UI_VERIFY_v8653.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        stop(proc)
