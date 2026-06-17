#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Реальный E2E-прогон ядра и отчёта через HTTP API.
Проверяет новые semantic-связи source_system/system/target_system и то, что
markdown-отчёт не искажает выводы ядра.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import engine
from report import markdown_report

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get('LIVE_AUDIT_PORT', '8138'))
BASE = f'http://127.0.0.1:{PORT}'
PAYLOAD_PATH = ROOT / 'LIVE_CORE_AUDIT_v8638' / 'live_payload.json'

payload = json.loads(PAYLOAD_PATH.read_text(encoding='utf-8'))
res = engine.analyze(payload)
assert res.get('ok') is True, res
md_direct = markdown_report(res)
rules = [f.get('rule') for f in res.get('findings', [])]
rule_set = set(rules)
expected = {
    'external_blocking', 'sla_budget', 'retry_without_idempotency',
    'capacity_vs_limit', 'unstable_dependency', 'hot_read_no_cache',
    'fanin_partial_failure', 'dual_write', 'blocking_in_async_handler',
    'stream_consumer_controls', 'contract_versioning', 'analytics_in_core'
}
missing = sorted(expected - rule_set)
assert not missing, f'missing expected rules: {missing}'
# Audit is present, so regulatory_audit must NOT fire.
assert 'regulatory_audit' not in rule_set

# New relation semantics.
assert any(f['rule'] == 'external_blocking' and 'KYC партнёр' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'external_blocking' and 'Legacy скоринг' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'blocking_in_async_handler' and 'CRM' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'stream_consumer_controls' and 'Processor читает событие из Kafka' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'fanin_partial_failure' and 'Шаг 5' in f.get('where', '') for f in res['findings'])
assert not any(f['rule'] == 'fanin_partial_failure' and 'Шаг 12' in f.get('where', '') for f in res['findings'])

# Report semantics: API Gateway is component, not transport; Audit Log is valid storage/control;
# internal aggregation is not schema error.
step1 = md_direct.split('#### Шаг 1. Клиент отправляет заявку', 1)[1].split('#### Шаг 2', 1)[0]
step2 = md_direct.split('#### Шаг 2. Gateway вызывает сервис заявок', 1)[1].split('#### Шаг 3', 1)[0]
assert 'Основной способ взаимодействия: REST API' in step1
assert 'Основной способ взаимодействия: REST API' in step2
assert 'API Gateway используется как точка входа' in md_direct
assert 'Шаг 12 «Аудитирует результат обработки»: Шаг описан как сохранение результата, но получатель не похож' not in md_direct
assert 'Шаг 5 «Сведение веток KYC' not in md_direct.split('## Проверка логики схемы', 1)[1].split('## Почему выбраны', 1)[0]
assert 'Агрегация ветвей выполняется без политики частичного отказа' in md_direct

# Real HTTP/API path.
out_dir = ROOT / 'LIVE_CORE_AUDIT_v8638'
out_dir.mkdir(exist_ok=True)
app_env = os.environ.copy()
app_env['PORT'] = str(PORT)
app_env['HOST'] = '127.0.0.1'
app_env['APP_DIR'] = str(out_dir / '.architect6_verify')
proc = subprocess.Popen([sys.executable, 'app.py'], cwd=str(ROOT), env=app_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE + '/health', timeout=0.5).read()
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise AssertionError('server did not start')
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + '/api/analyze', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    api_res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode('utf-8'))
    assert api_res.get('ok') is True, api_res
    md_api = urllib.request.urlopen(BASE + f"/run/{api_res['id']}.md", timeout=20).read().decode('utf-8')
    assert md_api == md_direct
    (out_dir / 'verified_api_report.md').write_text(md_api, encoding='utf-8')
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

print(f'LIVE_CORE_REAL_REPORT_v8638 ok: steps={len(res["model"]["steps"])} findings={len(res["findings"])} rules={len(rule_set)}')
