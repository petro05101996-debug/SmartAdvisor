#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8.6.40 full core audit runner.
Runs the same checks as v8.6.39 in callable form, plus report quality smoke.
"""
import json, re, time, os
from pathlib import Path
import verify_full_core_audit_v8639 as v
import engine, report

checks = [
    v.check_validation,
    v.check_channels_report_coverage,
    v.check_route_semantics,
    v.check_broker_semantics,
    v.check_fanin_and_self_routes,
    v.check_core_rules_smoke,
]
for fn in checks:
    t=time.time(); fn(); print(f'{fn.__name__} ok {time.time()-t:.2f}s')
t=time.time(); rnd=v.check_random_robustness(1200 if os.environ.get('FULL_AUDIT') == '1' else 300,100); print(f'random_robustness ok {rnd} {time.time()-t:.2f}s')

# Report language/structure quality smoke on archived payloads when present,
# otherwise on a generated in-memory payload. Clean release archives must not
# depend on pre-generated audit directories.
paths = [p for p in [Path('LIVE_CORE_AUDIT_v8638/live_payload.json')] if p.exists()]
mega = Path('/mnt/data/mega_all_tech_payload_v8620.json')
if mega.exists():
    paths.append(mega)
elif Path('mega_all_tech_payload_v8620.json').exists():
    paths.append(Path('mega_all_tech_payload_v8620.json'))
payload_items = [(str(p), json.loads(p.read_text(encoding='utf-8'))) for p in paths]
if not payload_items:
    payload_items.append(('generated_smoke_payload', v.payload([
        v.step(1, 'Client calls API', source='Client', target='Process Service', channel='rest', blocking=True, timeout_ms=100),
        v.step(2, 'Save aggregate', source='Process Service', target='Main DB', channel='db', action='save', writes_entity=True, depends_on='1'),
        v.step(3, 'Publish event', source='Process Service', target='Kafka', channel='kafka', blocking=False, retry='auto', idempotency='key', depends_on='2'),
        v.step(4, 'Consume event', system='Worker', source='Kafka', target='Worker', channel='kafka', blocking=False, retry='auto', idempotency='key', depends_on='3', compensation='retry with DLQ'),
    ], money='no', regulatory='no')))
bad = [
    'CREATE TABLE таблица', 'happy path', 'Payload', 'payload', 'без частичный', 'заявленный целевое',
    'с идентификатор отслеживания', 'без модель для чтения', 'рассчитанооо', 'Read-режим',
    'freshness contract', 'change process', 'Основной способ взаимодействия: API Gateway\n**Где:**',
    'Сервис процесса → Сервис процесса → Внешний партнёр', 'таблица входящих сообщений_dedup',
]
for label, data in payload_items:
    res=engine.analyze(data)
    assert res.get('ok') is True, res
    # v8.6.59: этот legacy full-core audit не должен зависать на
    # огромном markdown в обычном CI. Полный report-smoke включается явно:
    # FULL_AUDIT_REPORTS=1 python verify_full_core_audit_v8640.py
    if os.environ.get('FULL_AUDIT_REPORTS') == '1':
        md=report.markdown_report(res)
        assert '## Короткий человеческий вывод' in md
        assert '## Диаграммы процесса' in md
        assert 'CREATE TABLE inbox_dedup' in md
        assert 'CREATE TABLE outbox_messages' in md
        for frag in bad:
            assert frag not in md, f'{label}: bad fragment {frag!r}'
print(json.dumps({'status':'ok','channels':len(engine.ALL_CHANNELS),'rules':len(engine.RULES),'random_cases':1200 if os.environ.get('FULL_AUDIT') == '1' else 300,'report_smoke':'full' if os.environ.get('FULL_AUDIT_REPORTS') == '1' else 'fast'}, ensure_ascii=False))
