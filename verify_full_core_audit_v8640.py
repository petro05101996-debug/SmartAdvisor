#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8.6.40 full core audit runner.
Runs the same checks as v8.6.39 in callable form, plus report quality smoke.
"""
import json, re, time
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
t=time.time(); rnd=v.check_random_robustness(1200,100); print(f'random_robustness ok {rnd} {time.time()-t:.2f}s')

# Report language/structure quality smoke on the real API payload and all-tech payload.
paths = [Path('LIVE_CORE_AUDIT_v8638/live_payload.json')]
mega = Path('/mnt/data/mega_all_tech_payload_v8620.json')
if mega.exists(): paths.append(mega)
else: paths.append(Path('mega_all_tech_payload_v8620.json'))
bad = [
    'CREATE TABLE таблица', 'happy path', 'Payload', 'payload', 'без частичный', 'заявленный целевое',
    'с идентификатор отслеживания', 'без модель для чтения', 'рассчитанооо', 'Read-режим',
    'freshness contract', 'change process', 'Основной способ взаимодействия: API Gateway\n**Где:**',
    'Сервис процесса → Сервис процесса → Внешний партнёр', 'таблица входящих сообщений_dedup',
]
for p in paths:
    data=json.loads(p.read_text(encoding='utf-8'))
    res=engine.analyze(data)
    assert res.get('ok') is True, res
    md=report.markdown_report(res)
    assert '## Короткий человеческий вывод' in md
    assert '## Диаграммы процесса' in md
    assert 'CREATE TABLE inbox_dedup' in md
    assert 'CREATE TABLE outbox_messages' in md
    for frag in bad:
        assert frag not in md, f'{p}: bad fragment {frag!r}'
print(json.dumps({'status':'ok','channels':len(engine.ALL_CHANNELS),'rules':len(engine.RULES),'random_cases':1200}, ensure_ascii=False))
