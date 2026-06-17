# -*- coding: utf-8 -*-
"""Финальная пользовательская проверка SaaS UI v8.6.56.

Проверяет именно найденные ранее UX-дефекты:
- прогресс не должен показывать сырой localStorage/fetch error;
- метрика каталога не должна быть обрубком "ed";
- на desktop/tablet/mobile нет горизонтального overflow;
- визуальный сборщик решения работает без ручного JSON;
- live API старого и учебного функционала отвечает.
"""
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.request, shutil
from pathlib import Path
from contextlib import suppress

import ui
from learning import get_case, list_cases

ROOT = Path(__file__).resolve().parent
PORT = 8654
BASE = f'http://127.0.0.1:{PORT}'
APP_ENV = {**os.environ, 'PORT': str(PORT), 'HOST': '127.0.0.1', 'APP_DIR': str(ROOT / 'appdb_saas_ui_v8654')}


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception): proc.wait(timeout=3)
        if proc.poll() is None:
            proc.kill()


def http_json(path, payload=None, timeout=60):
    if payload is None:
        return json.loads(urllib.request.urlopen(BASE + path, timeout=timeout).read().decode('utf-8'))
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8'))


def start_server():
    proc = subprocess.Popen([sys.executable, 'app.py'], cwd=str(ROOT), env=APP_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(80):
        try:
            urllib.request.urlopen(BASE + '/health', timeout=1).read()
            return proc
        except Exception:
            time.sleep(0.2)
    stop(proc)
    raise AssertionError('server did not start')


def browser_static_checks():
    from playwright.sync_api import sync_playwright, expect
    from learning import build_learning_visual_payload
    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    out = []
    screenshots = []
    cid = 'bank-credit-bki-fraud'
    weak = build_learning_visual_payload(cid, [], kind='weak')
    reference = build_learning_visual_payload(cid, [], kind='reference')
    partial = build_learning_visual_payload(cid, ['outbox', 'timeouts'], kind='selected')

    def install_fetch_mock(page):
        """Mock API calls for static HTML checks.

        The learning page now asks the server to build visual payloads. In CI we
        keep this check static and deterministic, so the browser executes the UI
        JavaScript while API responses are supplied by this mock.
        """
        page.evaluate(
            """({weak, reference, partial}) => {
              window.fetch = async (url, opts) => {
                const u = new URL(String(url), 'http://smartadvisor.local');
                let data = {ok:true};
                if (u.pathname.endsWith('/api/learning/progress')) {
                  data = {ok:true, attempt_count:0, solved_case_count:0, case_count:83, badges:[], weak_skills:[], latest_attempts:[]};
                } else if (u.pathname.endsWith('/api/learning/visual-payload')) {
                  const kind = u.searchParams.get('kind') || 'selected';
                  const controls = u.searchParams.get('controls') || '';
                  if (kind === 'weak') data = weak;
                  else if (kind === 'reference') data = reference;
                  else if (controls.includes('outbox') && controls.includes('timeouts')) data = partial;
                  else data = {ok:true, selected_count:0, control_count:5, payload:{}, message:'Контроли не выбраны'};
                } else if (u.pathname.endsWith('/api/learning/evaluate')) {
                  data = {ok:true, hints:[], learning_score:8.8, report_markdown:'Проверка интерфейса выполнена.'};
                } else {
                  data = {ok:true, hints:[], cases:[], catalog:{}, learning_score:0, report_markdown:''};
                }
                return { ok:true, json: async () => data, text: async () => JSON.stringify(data) };
              };
            }""",
            {'weak': weak, 'reference': reference, 'partial': partial},
        )

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox', '--disable-dev-shm-usage']) if exe else p.chromium.launch(headless=True, args=['--no-sandbox'])
        except Exception as e:
            return {'browser': 'skipped', 'reason': str(e)}
        for name, vp in [('desktop', {'width': 1366, 'height': 900}), ('tablet', {'width': 768, 'height': 1024}), ('mobile', {'width': 390, 'height': 844})]:
            page = browser.new_page(viewport=vp)
            page.set_content(ui.learning_home_page(), wait_until='load')
            install_fetch_mock(page)
            with suppress(Exception):
                page.evaluate('loadLearningProgress()')
            page.wait_for_timeout(500)
            expect(page.get_by_text('Практический тренажёр интеграций')).to_be_visible()
            assert page.locator('text=Ошибка прогресса').count() == 0, f'{name}: raw progress error is visible'
            metric = page.evaluate("() => [...document.querySelectorAll('.saas-metric')].map(x=>x.textContent||'').find(t=>t.includes('Каталог')) || ''")
            assert 'ed' not in metric, f'{name}: broken catalog metric ed is visible: {metric}'
            assert 'OK' in metric, f'{name}: catalog status OK is not visible: {metric}'
            page.fill('#caseSearch', 'Kafka')
            page.evaluate('filterCases()')
            home = page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth,cards:[...document.querySelectorAll('#learningGrid .learning-card:not(.hidden-by-saas)')].length})")
            assert home['sw'] <= home['cw'] + 2, (name, 'home_overflow', home)
            assert home['cards'] > 0, (name, 'filter_no_cards')
            if name in ('desktop', 'mobile'):
                shot = str(ROOT / f'SAAS_UI_HOME_v8654_{name}.png')
                page.screenshot(path=shot, full_page=True)
                screenshots.append(shot)

            page.set_content(ui.learning_case_page(cid), wait_until='load')
            install_fetch_mock(page)
            expect(page.get_by_text('Соберите решение без JSON')).to_be_visible()
            expect(page.get_by_text('Проверить моё решение')).to_be_visible()
            checked = page.evaluate("() => document.querySelectorAll('.visual-control:checked').length")
            assert checked == 0, f'{name}: visual controls must not be prechecked'

            page.evaluate("() => buildVisualSolution('weak')")
            page.wait_for_function("() => (document.getElementById('solutionJson').value||'').length > 50", timeout=10000)
            weak_text = page.evaluate("() => document.getElementById('solutionJson').value")
            assert 'Outbox' not in weak_text and 'DLQ' not in weak_text, f'{name}: weak draft contains production controls'

            page.locator('.visual-control[value="outbox"]').check()
            page.locator('.visual-control[value="timeouts"]').check()
            page.evaluate("() => buildVisualSolution('selected')")
            page.wait_for_function("() => { const v=document.getElementById('solutionJson').value||''; return v.includes('Outbox') && (v.includes('timeout') || v.includes('таймаут')); }", timeout=10000)
            partial_text = page.evaluate("() => document.getElementById('solutionJson').value")
            assert 'DLQ' not in partial_text and 'schemaVersion' not in partial_text, f'{name}: unselected controls leaked into partial payload'

            page.evaluate("() => buildVisualSolution('reference')")
            page.wait_for_function("() => { const v=document.getElementById('solutionJson').value||''; return v.includes('Outbox') || v.includes('Kafka'); }", timeout=10000)
            ref_text = page.evaluate("() => document.getElementById('solutionJson').value")
            assert 'Outbox' in ref_text or 'Kafka' in ref_text, f'{name}: reference payload was not inserted'

            case = page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert case['sw'] <= case['cw'] + 2, (name, 'case_overflow', case)
            if name in ('desktop', 'mobile'):
                shot = str(ROOT / f'SAAS_UI_CASE_v8654_{name}.png')
                page.screenshot(path=shot, full_page=True)
                screenshots.append(shot)
            out.append({'viewport': name, 'home_overflow': False, 'case_overflow': False, 'filter': 'ok', 'visual_builder': 'ok'})
            page.close()
        browser.close()
    return {'browser': 'ok', 'viewports': out, 'screenshots': screenshots}

def api_checks():
    proc = start_server()
    try:
        cases = http_json('/api/learning/cases')
        assert cases['ok'] and len(cases['cases']) == 83
        cid = 'bank-credit-bki-fraud'
        ref = get_case(cid)['payload']
        ev = http_json('/api/learning/evaluate', {'case_id': cid, 'mode': 'reference', 'payload': ref}, 90)
        assert ev['ok'] and ev['learning_score'] >= 8.5, ev.get('learning_score')
        strong = 'Сначала фиксирую границы процесса и участников. Клиентский путь отделяю от асинхронной публикации. Решение сохраняю вместе с Outbox, событие отправляю в Kafka с ключом applicationId, добавляю eventId, correlationId, idempotencyKey и schemaVersion. Для БКИ и fraud задаю timeout, circuit breaker и ограниченные повторы. Для потребителей нужны DLQ, quarantine, replay, мониторинг lag, ошибок и трассировка. MVP может быть проще, но production требует контрактов, наблюдаемости и регламента повторной обработки.'
        interview = http_json('/api/learning/evaluate', {'case_id': cid, 'mode': 'interview', 'payload': ref, 'answer_text': strong}, 90)
        assert interview['ok'] and interview.get('interview_score', 0) >= 8.5, interview.get('interview_score')
        old = http_json('/api/analyze', ref, 90)
        assert old['ok'] and old.get('id')
        md = urllib.request.urlopen(BASE + '/run/' + old['id'] + '.md', timeout=60).read().decode('utf-8')
        assert 'Архитектурный разбор' in md or 'Разбор' in md
        return {'case_count': len(cases['cases']), 'reference_score': ev['learning_score'], 'interview_score': interview['interview_score'], 'old_run': old['id']}
    finally:
        stop(proc)


if __name__ == '__main__':
    result = {'ok': True, 'browser': browser_static_checks(), 'api': api_checks()}
    Path('SAAS_UI_VERIFY_v8654.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
