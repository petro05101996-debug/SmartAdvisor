# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.request, urllib.parse
from pathlib import Path
from contextlib import suppress

from learning import list_cases, get_case, evaluate_reference, evaluate_learning_solution, validate_learning_catalog, learning_hints, save_learning_attempt, progress_for_learner
import ui

BAD_FRAGMENTS = [
    'Read-режимl', 'без частичный', 'заявленный целевое', 'CREATE TABLE таблица',
    'Почему\nПочему', 'Открыть база знаний'
]


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception): proc.wait(timeout=3)
        if proc.poll() is None: proc.kill()


def direct_checks():
    issues=[]
    cases=list_cases()
    if len(cases) < 20:
        issues.append('case_count_lt_20')
    cat=validate_learning_catalog(deep=False)
    if not cat['ok']:
        issues.extend(cat['issues'])
    sample=[]
    for c in cases[:8]:
        ev=evaluate_reference(c['id'])
        if not ev.get('base_ok') or ev.get('learning_score',0) < 7.0:
            issues.append(f'reference_bad:{c["id"]}:{ev.get("learning_score")}')
        md=ev.get('report_markdown','')
        for frag in ('Учебный разбор','Профиль навыков','Сравнение с эталоном','Полный архитектурный отчёт ядра'):
            if frag not in md:
                issues.append(f'md_missing:{c["id"]}:{frag}')
        for bad in BAD_FRAGMENTS:
            if bad in md:
                issues.append(f'bad_fragment:{c["id"]}:{bad}')
        h=learning_hints(c['id'], 2)
        if not h.get('ok') or not h.get('hints'):
            issues.append(f'hints_bad:{c["id"]}')
        sample.append({'id':c['id'],'score':ev.get('learning_score'),'level':ev.get('learning_level')})
    invalid=evaluate_learning_solution(cases[0]['id'], {'meta': {'name':'bad'}, 'systems': [], 'steps': []})
    if invalid.get('base_ok') is not False or invalid.get('learning_score') != 0.0:
        issues.append('invalid_solution_not_handled')
    return {'ok':not issues,'issues':issues,'case_count':len(cases),'sample':sample,'catalog':cat['summary']}


def live_checks():
    root=Path(__file__).resolve().parent
    port=8145
    app_dir=root/'appdb_learning_v8645'
    proc=subprocess.Popen([sys.executable,'app.py'], cwd=str(root), env={**os.environ,'PORT':str(port),'HOST':'127.0.0.1','APP_DIR':str(app_dir)}, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(base+'/health', timeout=1).read(); break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError('server_not_started')
        home=urllib.request.urlopen(base+'/learning', timeout=10).read().decode('utf-8')
        assert 'Прогресс ученика' in home and 'Каталог учебных кейсов MVP' in home
        cases=json.loads(urllib.request.urlopen(base+'/api/learning/cases', timeout=10).read().decode('utf-8'))
        assert cases['ok'] and len(cases['cases'])>=20 and cases['catalog']['case_count']>=20
        cid=cases['cases'][0]['id']
        page=urllib.request.urlopen(base+'/learning/'+cid, timeout=10).read().decode('utf-8')
        assert 'Режим собеседования' in page and 'Подсказка 1' in page
        hints=json.loads(urllib.request.urlopen(base+'/api/learning/hints?case_id='+urllib.parse.quote(cid)+'&level=3', timeout=10).read().decode('utf-8'))
        assert hints['ok'] and hints['hints']
        payload=get_case(cid)['payload']
        learner='verify-v8645'
        req=urllib.request.Request(base+'/api/learning/evaluate', data=json.dumps({'case_id':cid,'mode':'learning','learner_id':learner,'payload':payload}, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
        ev=json.loads(urllib.request.urlopen(req, timeout=45).read().decode('utf-8'))
        assert ev['ok'] and ev.get('base_ok') is True and ev.get('attempt_id') and ev.get('learning_score',0)>=7
        assert 'Сравнение с эталоном' in ev.get('report_markdown','')
        md=urllib.request.urlopen(base+ev['attempt_md_url'], timeout=10).read().decode('utf-8')
        assert '# Учебный разбор' in md
        progress=json.loads(urllib.request.urlopen(base+'/api/learning/progress?learner_id='+learner, timeout=10).read().decode('utf-8'))
        assert progress['ok'] and progress['attempt_count']>=1 and progress['solved_case_count']>=1
        # Старый функционал: /api/analyze и /run/{id}.md.
        req2=urllib.request.Request(base+'/api/analyze', data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type':'application/json'})
        ar=json.loads(urllib.request.urlopen(req2, timeout=45).read().decode('utf-8'))
        assert ar['ok'] and ar['id']
        old_md=urllib.request.urlopen(base+'/run/'+ar['id']+'.md', timeout=20).read().decode('utf-8')
        assert 'Архитектурный разбор' in old_md or 'Интеграционный' in old_md or '# ' in old_md
        return {'case_count':len(cases['cases']),'sample_case':cid,'score':ev.get('learning_score'),'progress_attempts':progress['attempt_count']}
    finally:
        stop(proc)


def ui_static_checks():
    issues=[]
    pages=[ui.learning_home_page(), ui.learning_case_page(list_cases()[0]['id']), ui.form_page(), ui.invariant_reference_page(), ui.design_pattern_reference_page()]
    required=['Тренажёр системного аналитика','Режим собеседования','Сформировать отчёт','Открыть базу знаний']
    blob='\n'.join(pages)
    for frag in required:
        if frag not in blob:
            issues.append('ui_missing:'+frag)
    for bad in BAD_FRAGMENTS:
        if bad in blob:
            issues.append('ui_bad_fragment:'+bad)
    return {'ok':not issues,'issues':issues}


if __name__=='__main__':
    result={'direct':direct_checks(), 'live':live_checks(), 'ui_static':ui_static_checks()}
    ok=all(x.get('ok', True) for x in result.values())
    result['ok']=ok
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if not ok:
        raise SystemExit(1)
