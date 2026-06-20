#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production E2E-прогон ядра и отчёта через direct + HTTP API.

v8.6.59: скрипт больше не зависит от внешнего live_payload.json. Он сам
собирает реалистичный payload с source_system/system/target_system и проверяет:
- ядро находит ключевые классы рисков;
- отчёт не искажает REST/API Gateway, audit/control шаги и fan-in;
- HTTP API создаёт run и отдаёт markdown, совпадающий с direct markdown.
"""
from __future__ import annotations
import atexit
import json
import os
import shutil
import tempfile
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
OUT_DIR = Path(os.environ.get('LIVE_CORE_AUDIT_OUT_DIR') or tempfile.mkdtemp(prefix='smartadvisor_live_core_'))
OUT_DIR.mkdir(exist_ok=True)
if os.environ.get('KEEP_AUDIT_ARTIFACTS') != '1' and 'LIVE_CORE_AUDIT_OUT_DIR' not in os.environ:
    atexit.register(lambda: shutil.rmtree(OUT_DIR, ignore_errors=True))


def default_payload() -> dict:
    return {
        'meta': {
            'name': 'Live core v8638: заявка с внешними проверками, Kafka, CRM, DWH и аудитом',
            'entity': 'Application',
            'goal': 'Проверить заявку, сохранить решение, отправить событие и обновить внешние/аналитические контуры.',
            'customer_visible': 'yes',
            'money': 'no',
            'regulatory': 'yes',
            'sla_ms': '900',
            'read_freq': 'very_high',
            'ordering': 'per_entity',
            'statuses': 'NEW, CHECKING, WAITING_EXTERNAL, DONE, FAILED, NEEDS_MANUAL_REVIEW',
            'lookup_keys': 'applicationId + eventId + correlationId; partition key applicationId',
            'fields': 'applicationId:uuid|required|indexed, eventId:uuid|unique, correlationId:uuid|indexed, statusVersion:int|required',
            'load_rps': '600',
            'peak_factor': '3',
        },
        'systems': [
            {'name': 'Клиент', 'role': 'external', 'criticality': 'high', 'stability': 'stable'},
            {'name': 'API Gateway', 'role': 'gateway', 'criticality': 'critical', 'stability': 'stable'},
            {'name': 'Сервис заявок', 'role': 'internal', 'criticality': 'critical', 'stability': 'stable'},
            {'name': 'БД заявок', 'role': 'db', 'criticality': 'critical', 'stability': 'stable'},
            {'name': 'KYC партнёр', 'role': 'external', 'criticality': 'critical', 'stability': 'limited', 'rate_limit_rps': '120'},
            {'name': 'Legacy скоринг', 'role': 'legacy', 'criticality': 'critical', 'stability': 'limited', 'rate_limit_rps': '90'},
            {'name': 'Kafka', 'role': 'broker', 'criticality': 'critical', 'stability': 'stable'},
            {'name': 'Processor', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
            {'name': 'CRM', 'role': 'external', 'criticality': 'high', 'stability': 'limited', 'rate_limit_rps': '80'},
            {'name': 'DWH', 'role': 'analytics', 'criticality': 'medium', 'stability': 'stable'},
            {'name': 'Audit Log', 'role': 'audit', 'criticality': 'high', 'stability': 'stable'},
        ],
        'steps': [
            {'order': 1, 'name': 'Клиент отправляет заявку', 'source_system': 'Клиент', 'system': 'API Gateway', 'target_system': 'Сервис заявок', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '300', 'retry': 'auto', 'idempotency': 'key', 'data_in': 'applicationId, correlationId'},
            {'order': 2, 'name': 'Gateway вызывает сервис заявок', 'source_system': 'API Gateway', 'system': 'API Gateway', 'target_system': 'Сервис заявок', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '300', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '1', 'data_in': 'applicationId, correlationId'},
            {'order': 3, 'name': 'Сервис читает текущий профиль из БД', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'БД заявок', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '500', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '2'},
            {'order': 4, 'name': 'Вызвать KYC партнёра', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'KYC партнёр', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '1000', 'retry': 'auto', 'idempotency': 'none', 'depends_on': '3'},
            {'order': 5, 'name': 'Сведение веток KYC и скоринга', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'БД заявок', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '300', 'retry': 'none', 'idempotency': 'key', 'writes_entity': 'yes', 'depends_on': '4,6'},
            {'order': 6, 'name': 'Вызвать Legacy скоринг', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'Legacy скоринг', 'channel': 'soap', 'blocking': 'yes', 'timeout_ms': '900', 'retry': 'auto', 'idempotency': 'none', 'depends_on': '3'},
            {'order': 7, 'name': 'Сохранить решение заявки', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'БД заявок', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '250', 'retry': 'auto', 'idempotency': 'none', 'writes_entity': 'yes', 'depends_on': '5'},
            {'order': 8, 'name': 'Опубликовать событие решения', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'Kafka', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'none', 'depends_on': '7', 'data_out': 'applicationId, status'},
            {'order': 9, 'name': 'Processor читает событие из Kafka', 'source_system': 'Kafka', 'system': 'Processor', 'target_system': 'Processor', 'channel': 'kafka', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'none', 'writes_entity': 'yes', 'depends_on': '8'},
            {'order': 10, 'name': 'Processor вызывает CRM', 'source_system': 'Processor', 'system': 'Processor', 'target_system': 'CRM', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': '700', 'retry': 'auto', 'idempotency': 'none', 'depends_on': '9'},
            {'order': 11, 'name': 'Сервис пишет витрину в DWH', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'DWH', 'channel': 'data_warehouse', 'blocking': 'yes', 'timeout_ms': '1000', 'retry': 'auto', 'idempotency': 'key', 'depends_on': '7'},
            {'order': 12, 'name': 'Сведение результатов аналитики с partial response policy', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'БД заявок', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '200', 'retry': 'none', 'idempotency': 'key', 'depends_on': '9,11', 'compensation': 'partial response policy, manual review'},
            {'order': 13, 'name': 'Аудитирует результат обработки', 'source_system': 'Сервис заявок', 'system': 'Audit Log', 'target_system': 'Audit Log', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': '150', 'retry': 'none', 'idempotency': 'natural', 'depends_on': '7', 'data_out': 'applicationId, correlationId, audit event'},
        ],
    }


def load_payload() -> dict:
    payload_path = OUT_DIR / 'live_payload.json'
    if payload_path.exists():
        return json.loads(payload_path.read_text(encoding='utf-8'))
    payload = default_payload()
    if os.environ.get('WRITE_VERIFY_ARTIFACTS') == '1' or 'LIVE_CORE_AUDIT_OUT_DIR' in os.environ:
        payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


payload = load_payload()
res = engine.analyze(payload)
assert res.get('ok') is True, res
md_direct = markdown_report(res)
rule_set = {f.get('rule') for f in res.get('findings', [])}
expected_subset = {'external_blocking', 'capacity_vs_limit', 'unstable_dependency', 'fanin_partial_failure', 'stream_consumer_controls', 'contract_versioning', 'analytics_in_core'}
missing = sorted(expected_subset - rule_set)
assert not missing, f'missing expected rules: {missing}; got={sorted(rule_set)}'
assert 'regulatory_audit' not in rule_set
assert any(f['rule'] == 'external_blocking' and 'KYC партнёр' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'external_blocking' and 'Legacy скоринг' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'stream_consumer_controls' and 'Processor читает событие из Kafka' in f.get('where', '') for f in res['findings'])
assert any(f['rule'] == 'fanin_partial_failure' and 'Шаг 5' in f.get('where', '') for f in res['findings'])
assert not any(f['rule'] == 'fanin_partial_failure' and 'Шаг 12' in f.get('where', '') for f in res['findings'])

step1 = md_direct.split('#### Шаг 1. Клиент отправляет заявку', 1)[1].split('#### Шаг 2', 1)[0]
step2 = md_direct.split('#### Шаг 2. Gateway вызывает сервис заявок', 1)[1].split('#### Шаг 3', 1)[0]
assert 'Основной способ взаимодействия: REST API' in step1
assert 'Основной способ взаимодействия: REST API' in step2
assert 'API Gateway используется как точка входа' in md_direct
assert 'Аудитирует результат обработки»: Шаг описан как сохранение результата, но получатель не похож' not in md_direct
assert 'Агрегация ветвей выполняется без политики частичного отказа' in md_direct

app_env = os.environ.copy()
app_env['PORT'] = str(PORT)
app_env['HOST'] = '127.0.0.1'
app_env['APP_DIR'] = str(OUT_DIR / '.architect6_verify')
proc = subprocess.Popen([sys.executable, 'app.py'], cwd=str(ROOT), env=app_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    deadline = time.time() + 10
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
    api_res = json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
    assert api_res.get('ok') is True, api_res
    md_api = urllib.request.urlopen(BASE + f"/run/{api_res['id']}.md", timeout=30).read().decode('utf-8')
    assert md_api == md_direct
    if os.environ.get('WRITE_VERIFY_ARTIFACTS') == '1' or 'LIVE_CORE_AUDIT_OUT_DIR' in os.environ:
        (OUT_DIR / 'verified_api_report.md').write_text(md_api, encoding='utf-8')
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

print(f'LIVE_CORE_REAL_REPORT_v8638 ok: steps={len(res["model"]["steps"])} findings={len(res["findings"])} rules={len(rule_set)} score={res["verdict"]["score"]}')
