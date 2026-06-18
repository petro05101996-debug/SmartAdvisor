# -*- coding: utf-8 -*-
import os
import sys
from copy import deepcopy
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

from learning import get_case

PORT = int(os.environ.get('TEST_PORT', '8129'))
BASE = f'http://127.0.0.1:{PORT}'

def http_get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return r.status, r.read().decode('utf-8')

def http_post(path, obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read().decode('utf-8'))

def weak_payload(case_id='bank-credit-bki-fraud'):
    payload = deepcopy(get_case(case_id)['payload'])
    for s in payload['steps']:
        s['name'] = str(s.get('name','')).replace('outbox', 'запись статуса').replace('Outbox', 'запись статуса')
        s['compensation'] = ''
        s['retry'] = 'none'
        s['idempotency'] = 'none'
        s['timeout_ms'] = ''
    payload['meta']['lookup_keys'] = 'applicationId'
    payload['meta']['fields'] = 'applicationId,status,updatedAt'
    return payload

def main():
    env = os.environ.copy()
    env['PORT'] = str(PORT)
    env['HOST'] = '127.0.0.1'
    env['APP_DIR'] = '/tmp/sa_v8649_live_user'
    proc = subprocess.Popen([sys.executable, 'app.py'], cwd='.', env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(60):
            try:
                status, _ = http_get('/health')
                if status == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError('server did not start')
        status, html = http_get('/learning')
        assert status == 200 and 'Тренаж' in html and 'Каталог' in html
        status, case_html = http_get('/learning/bank-credit-bki-fraud')
        assert status == 200 and 'Проверить выбранное решение' in case_html and 'Вопросы интервьюера' in case_html
        status, cases = http_get('/api/learning/cases')
        cases_json = json.loads(cases)
        assert cases_json['ok'] and len(cases_json['cases']) >= 83
        ref_payload = get_case('bank-credit-bki-fraud')['payload']
        st, ref_ev = http_post('/api/learning/evaluate', {'case_id':'bank-credit-bki-fraud','payload':ref_payload,'mode':'reference','learner_id':'live-user'})
        assert st == 200 and ref_ev['ok'] and ref_ev['learning_score'] >= 9.0
        st, weak_ev = http_post('/api/learning/evaluate', {'case_id':'bank-credit-bki-fraud','payload':weak_payload(),'mode':'learning','learner_id':'live-user'})
        assert st == 200 and weak_ev['ok'] and weak_ev['learning_score'] <= 5.5, weak_ev.get('learning_score')
        assert not {h['id'] for h in weak_ev.get('control_hits', [])} & {'dlq_replay','timeouts','versioning','kafka_key'}
        strong_answer = 'Сначала описываю границы процесса и участников. Разделяю синхронный путь и асинхронные события. Внешние вызовы идут с timeout и circuit breaker. Решение сохраняется с outbox. Kafka получает событие с partition key applicationId, eventId, correlationId, eventType, occurredAt и schemaVersion. Consumer идемпотентен через inbox, есть DLQ, quarantine и replay. Контракт версионируется, есть backward compatibility. В эксплуатации проверяем lag, trace, alerting, SLA и audit. На MVP нельзя выбрасывать идемпотентность, outbox, DLQ и версионирование.'
        st, int_ev = http_post('/api/learning/evaluate', {'case_id':'bank-credit-bki-fraud','payload':ref_payload,'mode':'interview','answer_text':strong_answer,'learner_id':'live-user'})
        assert st == 200 and int_ev['ok'] and int_ev['learning_score'] >= 8.5
        status, md = http_get(int_ev['attempt_md_url'])
        assert status == 200 and '### Короткий вывод' in md and 'Блок собеседования' in md
        st, old = http_post('/api/analyze', ref_payload)
        assert st == 200 and old['ok'] and old.get('id')
        status, old_md = http_get('/run/' + old['id'] + '.md')
        assert status == 200 and 'Архитектурный разбор' in old_md
        print(json.dumps({'ok': True, 'case_count': len(cases_json['cases']), 'reference_score': ref_ev['learning_score'], 'weak_score': weak_ev['learning_score'], 'interview_score': int_ev['learning_score'], 'old_api': old['id']}, ensure_ascii=False))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == '__main__':
    main()
    sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
