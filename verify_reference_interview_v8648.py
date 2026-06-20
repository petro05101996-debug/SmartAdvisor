#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка production-доводки эталонов и собеседований v8.6.48."""
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

from learning import CASES, get_case, evaluate_learning_solution, interview_pack, reference_variants, validate_learning_catalog

BAD_FRAGMENTS = [
    'сырой JSON', 'undefined', 'None', 'bподтверждение', 'параллелизмааа',
    'Outbox-таблица-таблица', 'CREATE TABLE таблица', 'техобруб',
]
REQUIRED_REPORT_SECTIONS = [
    '## 2. Профиль навыков', '## 4. Сравнение с эталоном', '## 8. Эталонная схема решения',
    '### Промышленный эталон', '### Допустимый MVP-вариант', '### Вариант при legacy-ограничениях',
    '### Критерии приёмки', '## 9. Блок собеседования', '### Вопросы интервьюера и ожидаемые тезисы',
    '### Рубрика оценки', '## 10. Полный архитектурный отчёт ядра'
]

SAMPLE_CASES = [
    'bank-credit-bki-fraud', 'uk-bank-status-flow', 'card-authorization-clearing',
    'iot-mqtt-alarms', 'graphql-bff-aggregation', 'search-reindex-bluegreen',
]


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def check_direct():
    cat = validate_learning_catalog(deep=True)
    assert_true(cat.get('ok'), f'catalog invalid: {cat.get("issues")[:5]}')
    assert_true(cat.get('case_count') >= 80, 'expected at least 80 practice cases')
    results = []
    for cid in SAMPLE_CASES:
        case = get_case(cid)
        assert_true(case is not None, f'missing case {cid}')
        ref = reference_variants(cid)
        pack = interview_pack(cid)
        assert_true(ref.get('ok'), f'reference pack failed {cid}')
        assert_true(pack.get('ok'), f'interview pack failed {cid}')
        assert_true(len(ref.get('production', {}).get('steps', [])) >= 3, f'too few reference steps {cid}')
        assert_true(len(ref.get('acceptance_criteria', [])) >= 4, f'acceptance criteria missing {cid}')
        assert_true(len(pack.get('questions', [])) >= 6, f'too few interview questions {cid}')
        ev = evaluate_learning_solution(
            cid,
            case['payload'],
            mode='interview',
            answer_text='Сначала фиксирую границы процесса и участников. Затем объясняю sync/async выбор, контракты, версионирование, идемпотентность, обработку дублей, таймауты, DLQ, повторную обработку, мониторинг, correlationId и эксплуатационные проверки.',
        )
        assert_true(ev.get('ok') and ev.get('base_ok'), f'evaluate failed {cid}')
        assert_true(ev.get('interview_answer_assessment', {}).get('answer_score', 0) >= 6.5, f'interview answer weak {cid}')
        md = ev.get('report_markdown', '')
        for section in REQUIRED_REPORT_SECTIONS:
            assert_true(section in md, f'missing section {section} for {cid}')
        for bad in BAD_FRAGMENTS:
            assert_true(bad not in md, f'bad fragment {bad} for {cid}')
        results.append({'id': cid, 'score': ev['learning_score'], 'answer_score': ev['interview_answer_assessment']['answer_score'], 'report_len': len(md)})
    return {'ok': True, 'sample_results': results, 'catalog_case_count': cat.get('case_count')}


def http_json(url, data=None):
    if data is None:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.loads(r.read().decode('utf-8'))
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=raw, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def check_live():
    env = os.environ.copy()
    env['HOST'] = '127.0.0.1'
    env['PORT'] = '8765'
    env['APP_DIR'] = '/tmp/sa_v8648_verify_app'
    proc = subprocess.Popen([sys.executable, 'app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        base = 'http://127.0.0.1:8765'
        for _ in range(60):
            try:
                http_json(base + '/health')
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError('app did not start')
        cases = http_json(base + '/api/learning/cases')
        assert_true(cases.get('ok') and len(cases.get('cases', [])) >= 80, 'live cases failed')
        cid = 'bank-credit-bki-fraud'
        ref = http_json(base + '/api/learning/reference?case_id=' + cid)
        pack = http_json(base + '/api/learning/interview?case_id=' + cid)
        assert_true(ref.get('ok') and pack.get('ok'), 'live reference/interview failed')
        case = get_case(cid)
        ev = http_json(base + '/api/learning/evaluate', {
            'case_id': cid, 'mode': 'interview', 'learner_id': 'verify_v8648',
            'payload': case['payload'],
            'answer_text': 'Опишу процесс, участников, контракты, версионирование, идемпотентность, дубли, таймауты, очередь ошибок, replay, monitoring и correlationId.'
        })
        assert_true(ev.get('ok') and ev.get('attempt_md_url'), 'live evaluate failed')
        assert_true(ev.get('interview_answer_assessment', {}).get('answer_score', 0) >= 6, 'live interview scoring failed')
        with urllib.request.urlopen(base + ev['attempt_md_url'], timeout=20) as r:
            md = r.read().decode('utf-8')
        assert_true('## 9. Блок собеседования' in md and '### Допустимый MVP-вариант' in md, 'live markdown sections missing')
        # Старый проектировщик не должен сломаться.
        old = http_json(base + '/api/analyze', case['payload'])
        assert_true(old.get('ok') and old.get('id'), 'old api analyze failed')
        with urllib.request.urlopen(base + '/run/' + old['id'] + '.md', timeout=20) as r:
            old_md = r.read().decode('utf-8')
        assert_true('# ' in old_md and len(old_md) > 1000, 'old markdown report failed')
        return {'ok': True, 'case_count': len(cases.get('cases', [])), 'attempt_url': ev['attempt_md_url'], 'old_run': old['id']}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    res = {'direct': check_direct(), 'live': check_live()}
    res['ok'] = res['direct']['ok'] and res['live']['ok']
    Path('REFERENCE_INTERVIEW_VERIFY_v8648.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
