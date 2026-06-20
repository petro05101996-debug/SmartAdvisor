# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path
from contextlib import suppress

import ui
from learning import list_cases, get_case


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception): proc.wait(timeout=3)
        if proc.poll() is None:
            proc.kill()


def live_check():
    root=Path(__file__).resolve().parent
    port=8144
    base=f'http://127.0.0.1:{port}'
    proc=subprocess.Popen([sys.executable,'app.py'], cwd=str(root), env={**os.environ,'PORT':str(port),'HOST':'127.0.0.1','APP_DIR':str(root/'appdb_learning_v8644')}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base+'/health', timeout=1).read(); break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError('server did not start')
        home=urllib.request.urlopen(base+'/learning', timeout=5).read().decode('utf-8')
        assert 'Тренажёр системного аналитика' in home and 'Как пользоваться' in home
        cases=json.loads(urllib.request.urlopen(base+'/api/learning/cases', timeout=5).read().decode('utf-8'))
        assert cases['ok'] and len(cases['cases'])>=10
        cid=cases['cases'][0]['id']
        page=urllib.request.urlopen(base+'/learning/'+cid, timeout=5).read().decode('utf-8')
        assert 'Проверить выбранное решение' in page and 'REFERENCE_PAYLOAD' in page
        payload=get_case(cid)['payload']
        req=urllib.request.Request(base+'/api/learning/evaluate', data=json.dumps({'case_id':cid,'mode':'reference','payload':payload}, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
        ev=json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
        assert ev['ok'] and ev.get('base_ok') is True and ev.get('learning_score',0)>=7
        assert 'Профиль навыков' in ev.get('html','')
        assert 'Учебный разбор' in ev.get('report_markdown','')
        return {'case_count':len(cases['cases']), 'sample_case':cid, 'sample_score':ev.get('learning_score')}
    finally:
        stop(proc)


def browser_static_check():
    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception:
        return {'browser':'skipped: playwright unavailable'}
    checks=[]
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
            expect(page.get_by_text('Тренажёр системного аналитика')).to_be_visible()
            vals=page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert vals['sw'] <= vals['cw'] + 2, (name, vals)
            page.set_content(ui.learning_case_page(list_cases()[0]['id']), wait_until='load')
            expect(page.get_by_text('Проверить выбранное решение')).to_be_visible()
            vals=page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert vals['sw'] <= vals['cw'] + 2, (name, vals)
            checks.append(name)
        browser.close()
    return {'browser':'ok','viewports':checks}

if __name__=='__main__':
    result={'live': live_check(), 'static_ui': browser_static_check()}
    print(json.dumps({'ok':True, **result}, ensure_ascii=False, indent=2))
