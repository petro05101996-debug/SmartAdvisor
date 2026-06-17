# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.parse, urllib.request, shutil
from pathlib import Path
from contextlib import suppress
from collections import Counter

import ui
from learning import (
    list_cases, get_case, evaluate_reference, evaluate_learning_solution,
    validate_learning_catalog, learning_hints, learning_catalog_summary,
)

BAD_FRAGMENTS = [
    'Read-режимl', 'без частичный', 'заявленный целевое', 'CREATE TABLE таблица',
    'Почему\nПочему', 'Открыть база знаний', 'undefined', 'null/10'
]


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception): proc.wait(timeout=3)
        if proc.poll() is None:
            proc.kill()


def direct_catalog_check():
    issues=[]
    cases=list_cases()
    if len(cases) < 80:
        issues.append(f'case_count_lt_80:{len(cases)}')
    summary=learning_catalog_summary()
    level_counts=Counter(c.get('level') for c in cases)
    for lvl in ('Junior+','Middle','Middle+','Senior'):
        if level_counts.get(lvl,0) <= 0:
            issues.append(f'missing_level:{lvl}')
    if len(summary.get('tracks',{})) < 35:
        issues.append(f'too_few_tracks:{len(summary.get("tracks",{}))}')
    deep=validate_learning_catalog(deep=True)
    if not deep.get('ok'):
        issues.extend(deep.get('issues',[]))
    ids=[c['id'] for c in cases]
    sample_ids=[ids[0], ids[1], ids[5], ids[len(ids)//3], ids[len(ids)//2], ids[-10], ids[-5], ids[-1]]
    sample=[]
    for cid in sample_ids:
        ev=evaluate_reference(cid)
        if not ev.get('ok') or not ev.get('base_ok') or ev.get('learning_score',0)<7:
            issues.append(f'reference_bad:{cid}:{ev.get("learning_score")}')
        md=ev.get('report_markdown') or ''
        for frag in ('Учебный разбор', 'Профиль навыков', 'Сравнение с эталоном', 'Следующие задания'):
            if frag not in md:
                issues.append(f'report_missing:{cid}:{frag}')
        for bad in BAD_FRAGMENTS:
            if bad in md:
                issues.append(f'bad_fragment:{cid}:{bad}')
        for lvl in (1,2,3,4):
            h=learning_hints(cid,lvl)
            if not h.get('ok') or not h.get('hints'):
                issues.append(f'hint_bad:{cid}:{lvl}')
        sample.append({'id':cid,'score':ev.get('learning_score'),'level':ev.get('learning_level')})
    invalid=evaluate_learning_solution(ids[0], {'meta': {'name':'bad'}, 'systems': [], 'steps': []})
    if invalid.get('base_ok') is not False or invalid.get('learning_score') != 0.0 or not invalid.get('validation_errors'):
        issues.append('invalid_solution_not_rejected')
    return {'ok':not issues,'issues':issues,'case_count':len(cases),'levels':dict(level_counts),'track_count':len(summary.get('tracks',{})),'sample':sample,'deep_checked':len(deep.get('deep_results',[]))}


def ui_static_check():
    issues=[]
    home=ui.learning_home_page()
    if 'caseSearch' not in home or 'levelFilter' not in home or 'trackFilter' not in home or 'filterCases' not in home:
        issues.append('filters_missing')
    if home.count('data-level=') < 80:
        issues.append(f'not_enough_case_cards:{home.count("data-level=")}')
    case_page=ui.learning_case_page(list_cases()[-1]['id'])
    for frag in ('Проверить моё решение','Режим собеседования','Подсказка 1','Подставить эталон'):
        if frag not in case_page:
            issues.append(f'case_page_missing:{frag}')
    blob=home+'\n'+case_page
    for bad in BAD_FRAGMENTS:
        if bad in blob:
            issues.append(f'ui_bad_fragment:{bad}')
    return {'ok':not issues,'issues':issues,'cards':home.count('data-level=')}


def browser_filter_check():
    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception:
        return {'ok': True, 'browser':'skipped: playwright unavailable'}
    exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        try:
            browser=p.chromium.launch(headless=True, args=['--no-sandbox'])
        except Exception:
            if not exe:
                return {'ok': True, 'browser':'skipped: chromium unavailable'}
            browser=p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            out=[]
            for name, vp in [('desktop',{'width':1366,'height':900}),('tablet',{'width':768,'height':1024}),('mobile',{'width':390,'height':844})]:
                page=browser.new_page(viewport=vp)
                page.set_content(ui.learning_home_page(), wait_until='load')
                expect(page.locator('#caseSearch')).to_be_visible()
                vals=page.evaluate("""() => ({
                    sw: document.documentElement.scrollWidth,
                    cw: document.documentElement.clientWidth,
                    cards: document.querySelectorAll('.learning-card').length,
                    visible: [...document.querySelectorAll('.learning-card')].filter(x => getComputedStyle(x).display !== 'none').length
                })""")
                assert vals['cards'] >= 80 and vals['visible'] == vals['cards'], (name, vals)
                assert vals['sw'] <= vals['cw'] + 2, (name, vals)
                page.fill('#caseSearch', 'kafka')
                page.evaluate('filterCases()')
                filtered=page.evaluate("""() => [...document.querySelectorAll('.learning-card')].filter(x => getComputedStyle(x).display !== 'none').length""")
                assert 0 < filtered < vals['cards'], (name, filtered, vals['cards'])
                page.fill('#caseSearch', '')
                page.select_option('#levelFilter', 'Senior')
                page.evaluate('filterCases()')
                senior=page.evaluate("""() => [...document.querySelectorAll('.learning-card')].filter(x => getComputedStyle(x).display !== 'none').length""")
                assert senior > 0, (name, senior)
                out.append({'viewport':name,'cards':vals['cards'],'kafka_filtered':filtered,'senior_filtered':senior})
                page.close()
            return {'ok':True,'browser':'ok','viewports':out}
        finally:
            browser.close()


def live_api_check():
    root=Path(__file__).resolve().parent
    port=8146
    base=f'http://127.0.0.1:{port}'
    app_dir=root/'appdb_learning_v8646'
    proc=subprocess.Popen([sys.executable,'app.py'], cwd=str(root), env={**os.environ,'PORT':str(port),'HOST':'127.0.0.1','APP_DIR':str(app_dir)}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(base+'/health', timeout=1).read(); break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError('server_not_started')
        home=urllib.request.urlopen(base+'/learning', timeout=10).read().decode('utf-8')
        assert 'caseSearch' in home and 'Кейсов: 83' in home
        cases=json.loads(urllib.request.urlopen(base+'/api/learning/cases', timeout=10).read().decode('utf-8'))
        assert cases['ok'] and cases['catalog']['case_count'] >= 80
        deep=json.loads(urllib.request.urlopen(base+'/api/learning/catalog/validate?deep=1', timeout=30).read().decode('utf-8'))
        assert deep['ok'] and deep['case_count'] >= 80
        cid=cases['cases'][-1]['id']
        page=urllib.request.urlopen(base+'/learning/'+urllib.parse.quote(cid), timeout=10).read().decode('utf-8')
        assert 'REFERENCE_PAYLOAD' in page and 'Проверить эталон' in page
        payload=get_case(cid)['payload']
        learner='verify-v8646'
        req=urllib.request.Request(base+'/api/learning/evaluate', data=json.dumps({'case_id':cid,'mode':'learning','learner_id':learner,'payload':payload}, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
        ev=json.loads(urllib.request.urlopen(req, timeout=45).read().decode('utf-8'))
        assert ev['ok'] and ev.get('base_ok') is True and ev.get('learning_score',0) >= 7 and ev.get('attempt_id')
        md=urllib.request.urlopen(base+ev['attempt_md_url'], timeout=10).read().decode('utf-8')
        assert '# Учебный разбор' in md
        progress=json.loads(urllib.request.urlopen(base+'/api/learning/progress?learner_id='+learner, timeout=10).read().decode('utf-8'))
        assert progress['ok'] and progress['attempt_count'] >= 1 and progress['case_count'] >= 80
        # Старый API проектировщика остаётся рабочим.
        req2=urllib.request.Request(base+'/api/analyze', data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
        old=json.loads(urllib.request.urlopen(req2, timeout=45).read().decode('utf-8'))
        assert old['ok'] and old['id']
        old_md=urllib.request.urlopen(base+'/run/'+old['id']+'.md', timeout=20).read().decode('utf-8')
        assert 'Архитектурный разбор' in old_md
        return {'ok':True,'case_count':cases['catalog']['case_count'],'sample_case':cid,'score':ev.get('learning_score'),'old_api_run':old['id']}
    finally:
        stop(proc)


if __name__ == '__main__':
    result={
        'direct_catalog': direct_catalog_check(),
        'ui_static': ui_static_check(),
        'browser_filter': browser_filter_check(),
        'live_api': live_api_check(),
    }
    result['ok']=all(v.get('ok', False) for v in result.values())
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if not result['ok']:
        raise SystemExit(1)
