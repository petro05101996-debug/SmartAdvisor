#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
from engine import analyze
from report import markdown_report
from verify_full_core_audit_v8639 import payload, step

PORT=18139
APPDIR='/tmp/sa_v8639_app'
steps=[
 step(1,'Client calls API Gateway',system='API Gateway',channel='rest',source='Client',target='API Gateway',blocking=True,timeout_ms=100),
 step(2,'Gateway routes to service',system='Process Service',channel='rest',source='API Gateway',target='Process Service',depends_on='1',blocking=True,timeout_ms=100),
 step(3,'Save aggregate',system='Process Service',channel='db',source='Process Service',target='Main DB',action='save',writes_entity=True,depends_on='2',blocking=True,timeout_ms=150),
 step(4,'Call external partner',system='Process Service',channel='rest',source='Process Service',target='External Partner',depends_on='3',blocking=True,timeout_ms=500,retry='auto',idempotency='none'),
 step(5,'Publish event to Kafka',system='Process Service',channel='kafka',source='Process Service',target='Kafka',depends_on='3',blocking=False,retry='auto',idempotency='key'),
 step(6,'Consume event from Kafka',system='Worker',channel='kafka',source='Kafka',target='Worker',depends_on='5',blocking=False,retry='auto',idempotency='key',compensation='retry with DLQ',data_in='filter shared topic by tenant'),
 step(7,'Write ClickHouse mart',system='Process Service',channel='clickhouse',source='Process Service',target='DWH',depends_on='4,6',blocking=False,retry='auto',idempotency='key'),
 step(8,'Audit Log evidence',system='Process Service',channel='db',source='Process Service',target='Audit Log',action='save',writes_entity=True,depends_on='4,6',blocking=True,timeout_ms=50),
]
p=payload(steps, money='direct', regulatory='yes', customer_visible='yes', sla_ms='900', load_rps='600', peak_factor='2')
# Direct baseline
res=analyze(p)
assert res.get('ok'), res
md_direct=markdown_report(res)
assert 'Основной способ взаимодействия: API Gateway' not in md_direct
assert 'Колоночная аналитическая база данных' in md_direct or 'ClickHouse' in md_direct
assert 'получатель не похож на хранилище' not in md_direct.lower()

proc=subprocess.Popen([sys.executable,'app.py'], cwd=Path(__file__).parent, env={**os.environ,'PORT':str(PORT),'APP_DIR':APPDIR,'HOST':'127.0.0.1'}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    for _ in range(80):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=1).read()
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError('app did not start')
    data=json.dumps(p, ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(f'http://127.0.0.1:{PORT}/api/analyze', data=data, headers={'Content-Type':'application/json'}, method='POST')
    resp=json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    assert resp.get('ok') and resp.get('id'), resp
    md_api=urllib.request.urlopen(f'http://127.0.0.1:{PORT}/run/{resp["id"]}.md', timeout=10).read().decode('utf-8')
    assert md_api == md_direct, 'API markdown differs from direct engine report'
    Path('/mnt/data/LIVE_API_REPORT_v8_6_39.md').write_text(md_api, encoding='utf-8')
    print(json.dumps({'status':'ok','steps':len(steps),'findings':len(res.get('findings',[])),'rules':len({f.get('rule') for f in res.get('findings',[])})}, ensure_ascii=False))
finally:
    proc.terminate()
    try: proc.wait(timeout=3)
    except subprocess.TimeoutExpired: proc.kill()
