#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, re, sys, time, subprocess, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get('LIVE_AUDIT_PORT','8127'))
BASE = f'http://127.0.0.1:{PORT}'

payload = {
  'meta': {
    'name': 'E2E реальный кейс: оформление продукта с KYC, партнёром, Kafka, fan-in и DWH',
    'entity': 'Application',
    'goal': 'Клиент оформляет финансовый продукт; сервис должен проверить KYC, создать заявку, отправить события в downstream и построить витрину.',
    'description': 'Новые связи UI: source_system/system/target_system. Есть inbound запрос, outbound партнёр, запись в БД, publish в Kafka, consumer, блокирующий вызов из async handler, fan-in, DWH.',
    'customer_visible': 'yes',
    'money': 'indirect',
    'regulatory': 'yes',
    'sla_ms': 900,
    'read_freq': 'very_high',
    'ordering': 'per_entity',
    'load_rps': 800,
    'peak_factor': 3,
    'statuses': 'draft,kyc_pending,created,processing,completed,error',
    'lookup_keys': 'applicationId, customerId, correlationId',
    'fields': 'applicationId:uuid|required|unique|indexed, customerId:uuid|required|indexed, status:string|required|indexed, amount:decimal|required, createdAt:datetime|required, correlationId:string|required|indexed'
  },
  'systems': [
    {'name': 'Мобильное приложение', 'role': 'external', 'criticality': 'medium', 'stability': 'stable'},
    {'name': 'API Gateway', 'role': 'internal', 'criticality': 'critical', 'stability': 'stable'},
    {'name': 'Сервис заявок', 'role': 'internal', 'criticality': 'critical', 'stability': 'stable'},
    {'name': 'KYC партнёр', 'role': 'external', 'criticality': 'high', 'stability': 'limited', 'rate_limit_rps': 400},
    {'name': 'Legacy скоринг', 'role': 'legacy', 'criticality': 'high', 'stability': 'unstable', 'rate_limit_rps': 300},
    {'name': 'БД заявок', 'role': 'db', 'criticality': 'critical', 'stability': 'stable'},
    {'name': 'Kafka Applications Topic', 'role': 'broker', 'criticality': 'critical', 'stability': 'stable'},
    {'name': 'Application Processor', 'role': 'internal', 'criticality': 'high', 'stability': 'stable'},
    {'name': 'Notification Service', 'role': 'internal', 'criticality': 'medium', 'stability': 'stable'},
    {'name': 'CRM', 'role': 'external', 'criticality': 'medium', 'stability': 'limited', 'rate_limit_rps': 100},
    {'name': 'DWH', 'role': 'analytics', 'criticality': 'medium', 'stability': 'stable'},
    {'name': 'Audit Log', 'role': 'db', 'criticality': 'high', 'stability': 'stable'}
  ],
  'steps': [
    {'order': 1, 'name': 'Клиент отправляет заявку', 'source_system': 'Мобильное приложение', 'system': 'Мобильное приложение', 'target_system': 'API Gateway', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 250, 'retry': 'none', 'idempotency': 'key', 'writes_entity': 'no', 'depends_on': 0, 'data_in': 'client payload + idempotency key + correlationId', 'data_out': 'HTTP request', 'interaction_action': 'call', 'interaction_timing': 'sync', 'interaction_result': 'request'},
    {'order': 2, 'name': 'Gateway вызывает сервис заявок', 'source_system': 'API Gateway', 'system': 'API Gateway', 'target_system': 'Сервис заявок', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 200, 'retry': 'none', 'idempotency': 'key', 'writes_entity': 'no', 'depends_on': 1, 'data_in': 'validated request', 'data_out': 'command create application', 'interaction_action': 'call', 'interaction_timing': 'sync', 'interaction_result': 'command'},
    {'order': 3, 'name': 'Сервис синхронно проверяет KYC у партнёра', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'KYC партнёр', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 700, 'retry': 'auto', 'idempotency': 'none', 'writes_entity': 'no', 'depends_on': 2, 'data_in': 'customerId, passport', 'data_out': 'kyc status', 'interaction_action': 'call', 'interaction_timing': 'sync', 'interaction_result': 'external_check'},
    {'order': 4, 'name': 'Сервис читает скоринговый профиль из legacy без read-model', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'Legacy скоринг', 'channel': 'soap', 'blocking': 'yes', 'timeout_ms': 650, 'retry': 'none', 'idempotency': 'none', 'writes_entity': 'no', 'depends_on': 2, 'data_in': 'customerId', 'data_out': 'score profile', 'interaction_action': 'read', 'interaction_timing': 'sync', 'interaction_result': 'external_profile'},
    {'order': 5, 'name': 'Join KYC и скоринга без partial response policy', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'Сервис заявок', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 100, 'retry': 'none', 'idempotency': 'key', 'writes_entity': 'no', 'depends_on': '3,4', 'data_in': 'kyc status + score profile', 'data_out': 'decision', 'interaction_action': 'aggregate', 'interaction_timing': 'sync', 'interaction_result': 'decision'},
    {'order': 6, 'name': 'Сервис сохраняет заявку в БД', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'БД заявок', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': 120, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': 'yes', 'depends_on': 5, 'data_in': 'application aggregate', 'data_out': 'application row', 'interaction_action': 'save', 'interaction_timing': 'sync', 'interaction_result': 'stored'},
    {'order': 7, 'name': 'Сервис публикует ApplicationCreated в Kafka', 'source_system': 'Сервис заявок', 'system': 'Сервис заявок', 'target_system': 'Kafka Applications Topic', 'channel': 'kafka', 'blocking': 'no', 'timeout_ms': 0, 'retry': 'auto', 'idempotency': 'key', 'compensation': '', 'writes_entity': 'no', 'depends_on': 6, 'data_in': 'applicationId, status, correlationId, partition key = applicationId', 'data_out': 'ApplicationCreated v1', 'interaction_action': 'publish', 'interaction_timing': 'async', 'interaction_result': 'event'},
    {'order': 8, 'name': 'Processor читает событие из Kafka', 'source_system': 'Kafka Applications Topic', 'system': 'Application Processor', 'target_system': 'Application Processor', 'channel': 'kafka', 'blocking': 'no', 'timeout_ms': 0, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': 'no', 'depends_on': 7, 'data_in': 'ApplicationCreated v1, consumer group, applicationId as key', 'data_out': 'processing command', 'interaction_action': 'consume', 'interaction_timing': 'async', 'interaction_result': 'message'},
    {'order': 9, 'name': 'Processor блокирующе вызывает CRM при обработке события', 'source_system': 'Application Processor', 'system': 'Application Processor', 'target_system': 'CRM', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 500, 'retry': 'auto', 'idempotency': 'none', 'writes_entity': 'no', 'depends_on': 8, 'data_in': 'customerId', 'data_out': 'CRM enrichment', 'interaction_action': 'call', 'interaction_timing': 'sync_in_async_handler', 'interaction_result': 'enrichment'},
    {'order': 10, 'name': 'Processor отправляет уведомление', 'source_system': 'Application Processor', 'system': 'Application Processor', 'target_system': 'Notification Service', 'channel': 'rabbitmq', 'blocking': 'no', 'timeout_ms': 0, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': 'no', 'depends_on': 8, 'data_in': 'applicationId status', 'data_out': 'notification task', 'interaction_action': 'publish', 'interaction_timing': 'async', 'interaction_result': 'task'},
    {'order': 11, 'name': 'Поток выгружает данные заявки в DWH напрямую из core-flow', 'source_system': 'Application Processor', 'system': 'Application Processor', 'target_system': 'DWH', 'channel': 'rest', 'blocking': 'yes', 'timeout_ms': 400, 'retry': 'auto', 'idempotency': 'none', 'writes_entity': 'yes', 'depends_on': 9, 'data_in': 'application facts', 'data_out': 'analytics row', 'interaction_action': 'save', 'interaction_timing': 'sync', 'interaction_result': 'analytics_write'},
    {'order': 12, 'name': 'Аудитирует результат обработки', 'source_system': 'Application Processor', 'system': 'Application Processor', 'target_system': 'Audit Log', 'channel': 'db', 'blocking': 'yes', 'timeout_ms': 100, 'retry': 'auto', 'idempotency': 'key', 'writes_entity': 'yes', 'depends_on': '9,10,11', 'data_in': 'processing status + correlationId', 'data_out': 'audit record', 'interaction_action': 'save', 'interaction_timing': 'sync', 'interaction_result': 'audit'}
  ]
}

out_dir = ROOT / 'LIVE_CORE_AUDIT_v8638'
out_dir.mkdir(exist_ok=True)
(out_dir / 'live_payload.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

# direct engine result
sys.path.insert(0, str(ROOT))
import engine
from report import markdown_report
res = engine.analyze(payload)
(out_dir / 'direct_result.json').write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
md_direct = markdown_report(res) if res.get('ok') else json.dumps(res, ensure_ascii=False, indent=2)
(out_dir / 'direct_report.md').write_text(md_direct, encoding='utf-8')

# start real HTTP server
app_env = os.environ.copy(); app_env['PORT'] = str(PORT); app_env['HOST'] = '127.0.0.1'; app_env['APP_DIR'] = str(out_dir / '.architect6')
proc = subprocess.Popen([sys.executable, 'app.py'], cwd=str(ROOT), env=app_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
try:
    deadline = time.time() + 8
    last_err = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE + '/health', timeout=0.5).read()
            break
        except Exception as e:
            last_err = e; time.sleep(0.2)
    else:
        raise RuntimeError(f'server did not start: {last_err}; stdout={proc.stdout.read() if proc.stdout else ""}; stderr={proc.stderr.read() if proc.stderr else ""}')
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + '/api/analyze', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    api_res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode('utf-8'))
    (out_dir / 'api_response.json').write_text(json.dumps(api_res, ensure_ascii=False, indent=2), encoding='utf-8')
    if not api_res.get('ok'):
        raise RuntimeError(f'api returned error: {api_res}')
    rid = api_res['id']
    html = urllib.request.urlopen(BASE + f'/run/{rid}', timeout=15).read().decode('utf-8')
    md = urllib.request.urlopen(BASE + f'/run/{rid}.md', timeout=15).read().decode('utf-8')
    (out_dir / 'api_result_page.html').write_text(html, encoding='utf-8')
    (out_dir / 'api_report.md').write_text(md, encoding='utf-8')
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

# semantic checks
rules = [f.get('rule') for f in res.get('findings', [])]
findings_by_rule = {}
for f in res.get('findings', []):
    findings_by_rule.setdefault(f.get('rule'), []).append(f)
expected_rules = [
    'external_blocking', 'sla_budget', 'retry_without_idempotency',
    'capacity_vs_limit', 'unstable_dependency', 'hot_read_no_cache',
    'fanin_partial_failure', 'dual_write', 'blocking_in_async_handler',
    'stream_consumer_controls', 'contract_versioning', 'analytics_in_core',
    'regulatory_audit'
]
missing = [r for r in expected_rules if r not in rules]
# false positives / contradictions by text
report_text = md_direct
forbidden = []
if re.search(r'Мобильное приложение[^\n]{0,120}блокируется на нестабильной|Мобильное приложение[^\n]{0,120}rate limit', report_text, re.I):
    forbidden.append('inbound mobile app treated as outbound dependency')
if 'Processor читает событие из Kafka' in report_text and re.search(r'Processor читает событие из Kafka[^\n]{0,180}публику', report_text, re.I):
    forbidden.append('Kafka consumer described as publisher')
if 'Общая оценка: 100/100' in report_text and rules:
    forbidden.append('perfect score despite findings')
summary = {
    'ok': bool(res.get('ok')),
    'steps': len(res.get('model',{}).get('steps',[])),
    'findings': len(res.get('findings', [])),
    'rules': sorted(set(rules)),
    'expected_missing': missing,
    'forbidden': forbidden,
    'critical_findings': [f for f in res.get('findings', []) if f.get('severity') == 'critical'],
    'api_response': api_res,
    'direct_api_report_equal': md_direct == md,
    'direct_report_path': str(out_dir / 'direct_report.md'),
    'api_report_path': str(out_dir / 'api_report.md')
}
(out_dir / 'audit_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
