#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full core audit v8.6.39: structural invariants, semantic routes, report/API-ish coverage."""
import json, random, re, sys, traceback
from pathlib import Path
import engine
import report

ALL_CHANNELS = sorted(engine.ALL_CHANNELS)
BROKER = sorted(engine.BROKER_CHANNELS)
SYNC = sorted(engine.SYNC_CHANNELS)
ASYNC = sorted(engine.ASYNC_CHANNELS)

BASE_SYSTEMS = [
    {'name':'Client','role':'external','owner':'business','criticality':'medium','stability':'stable'},
    {'name':'API Gateway','role':'internal','owner':'platform','criticality':'high','stability':'stable'},
    {'name':'Process Service','role':'internal','owner':'team','criticality':'high','stability':'stable'},
    {'name':'Worker','role':'internal','owner':'team','criticality':'medium','stability':'stable'},
    {'name':'Kafka','role':'broker','owner':'platform','criticality':'high','stability':'stable'},
    {'name':'RabbitMQ','role':'broker','owner':'platform','criticality':'high','stability':'stable'},
    {'name':'Main DB','role':'db','owner':'team','criticality':'high','stability':'stable'},
    {'name':'Read Model','role':'db','owner':'team','criticality':'medium','stability':'stable'},
    {'name':'DWH','role':'analytics','owner':'data','criticality':'medium','stability':'stable'},
    {'name':'External Partner','role':'external','owner':'partner','criticality':'high','stability':'limited','rate_limit_rps':50},
    {'name':'Legacy Core','role':'legacy','owner':'legacy','criticality':'high','stability':'unstable','rate_limit_rps':30},
    {'name':'Audit Log','role':'db','owner':'security','criticality':'medium','stability':'stable'},
    {'name':'Observability','role':'internal','owner':'sre','criticality':'medium','stability':'stable'},
]

def payload(steps, **meta):
    m = {
        'name':'core audit case','entity':'Order','goal':'Проверка ядра','customer_visible':'yes','money':'direct',
        'regulatory':'yes','sla_ms':'1000','read_freq':'high','ordering':'per_entity',
        'fields':'orderId:string|required|unique, amount:decimal|required, clientId:string|required, passport:string|sensitive',
        'load_rps':'100','peak_factor':'3','multi_tenant':'yes'
    }
    m.update(meta)
    return {'meta':m,'systems':BASE_SYSTEMS,'steps':steps}

def step(order,name,system='Process Service',channel='rest',blocking=True,depends_on='',source='Client',target='Process Service',**kw):
    d={'order':order,'name':name,'system':system,'channel':channel,'blocking':blocking,'timeout_ms':kw.pop('timeout_ms',100),
       'retry':kw.pop('retry','none'),'idempotency':kw.pop('idempotency','key'),'compensation':kw.pop('compensation',''),
       'writes_entity':kw.pop('writes_entity',False),'depends_on':depends_on,'data_in':kw.pop('data_in','orderId'),
       'data_out':kw.pop('data_out','result'),'source_system':source,'target_system':target,
       'interaction_action':kw.pop('action','call'),'interaction_timing':kw.pop('timing','sync' if blocking else 'async'),
       'interaction_result':kw.pop('result','result')}
    d.update(kw)
    return d

def analyze_ok(p):
    res=engine.analyze(p)
    if not isinstance(res,dict): raise AssertionError('analyze returned non-dict')
    if not res.get('ok'):
        raise AssertionError('expected ok got errors: '+str(res.get('errors')))
    md=report.markdown_report(res)
    if not isinstance(md,str) or len(md)<500:
        raise AssertionError('bad markdown length')
    if re.search(r'\bNone\b|\bnan\b|\{\}|\[\]', md, re.I):
        raise AssertionError('raw placeholder leaked into report')
    return res, md

def rules(res): return {f.get('rule') for f in res.get('findings',[])}
def titles(res): return ' | '.join(f.get('title','') for f in res.get('findings',[]))
def assert_rule(res, rid):
    if rid not in rules(res): raise AssertionError(f'missing rule {rid}; got {sorted(rules(res))}\n{titles(res)}')
def assert_no_rule(res, rid):
    if rid in rules(res): raise AssertionError(f'unexpected rule {rid}; got {titles(res)}')

def check_validation():
    # Empty
    r=engine.analyze({'meta':{},'systems':[],'steps':[]})
    assert not r.get('ok') and 'Добавьте хотя бы один шаг процесса.' in ' '.join(r.get('errors',[]))
    # missing deps
    r=engine.analyze(payload([step(1,'a'), step(2,'b',depends_on='7')]))
    assert not r.get('ok') and 'несуществующего шага 7' in ' '.join(r.get('errors',[]))
    # duplicate orders should not crash and must be invalid
    r=engine.analyze(payload([step(1,'a'), step(1,'b')]))
    assert not r.get('ok') and 'Дублируется порядковый номер шага 1' in ' '.join(r.get('errors',[]))
    # self dep int and csv
    for dep in ['1','0,1','2,1']:
        r=engine.analyze(payload([step(1,'self',depends_on=dep)]))
        assert not r.get('ok') and 'зависит сам от себя' in ' '.join(r.get('errors',[]))
    # multi-parent cycles through second/third parent
    cases=[
        [step(1,'a',depends_on='2,3'), step(2,'b'), step(3,'c',depends_on='1')],
        [step(1,'a',depends_on='4'), step(2,'b',depends_on='1'), step(3,'c',depends_on='2'), step(4,'d',depends_on='3')],
        [step(1,'a',depends_on='2,3'), step(2,'b',depends_on='4'), step(3,'c'), step(4,'d',depends_on='1')],
    ]
    for c in cases:
        r=engine.analyze(payload(c))
        assert not r.get('ok') and 'Циклическая зависимость' in ' '.join(r.get('errors',[])), r
    # valid fan-in must pass
    analyze_ok(payload([step(1,'a'),step(2,'b'),step(3,'join',depends_on='1,2',action='aggregate')]))


def _target_for_channel(ch):
    if ch in BROKER:
        if ch == 'rabbitmq':
            return 'RabbitMQ'
        return 'Kafka'
    if ch in {'data_warehouse','data_lake','lakehouse','clickhouse','spark','dbt','airflow','etl','batch','cdc'}:
        return 'DWH'
    if ch in {'db','read_replica','db_sharding','mongodb','cassandra','dynamodb'}:
        return 'Main DB'
    if ch in {'object_storage','file','sftp'}:
        return 'External Partner' if ch == 'sftp' else 'Main DB'
    return 'External Partner' if ch in SYNC else 'Process Service'

def check_channels_report_coverage():
    expected_tokens = {
        'odata': ['odata'], 'vector_db': ['вектор'], 'dynamodb': ['dynamodb','key-value','ключ-значение'],
        'graphql': ['graphql'], 'grpc': ['grpc'], 'soap': ['soap'], 'kafka': ['kafka'], 'rabbitmq': ['rabbitmq'],
        'clickhouse': ['clickhouse','колоночная аналитическая'],
        'spark': ['spark'], 'dbt': ['dbt'], 'airflow': ['airflow'],
        'object_storage': ['объектное хранилище'], 'sftp': ['sftp'], 'websocket': ['websocket'], 'api_gateway': ['api gateway'],
    }
    for ch in ALL_CHANNELS:
        print(f'channel_coverage {ch}', flush=True)
        tgt=_target_for_channel(ch)
        s=[step(1,f'use {ch}',channel=ch,source='Process Service',target=tgt,blocking=(ch in SYNC),timeout_ms=50)]
        res,md=analyze_ok(payload(s, money='no', regulatory='no'))
        # selected channel should survive normalization
        assert res['model']['steps'][0]['channel']==ch, f'channel downgraded {ch}->{res["model"]["steps"][0]["channel"]}'
        # Important non-rest channels must be visible in the actual markdown, not hidden behind a generic bucket.
        if ch in expected_tokens:
            low=md.lower()
            if not any(tok in low for tok in expected_tokens[ch]):
                raise AssertionError(f'channel {ch} label not found in markdown; tokens={expected_tokens[ch]}')


def check_route_semantics():
    # inbound external client to our service is NOT outbound external dependency
    res,md=analyze_ok(payload([step(1,'Client calls API',system='Process Service',channel='rest',source='Client',target='Process Service',blocking=True,timeout_ms=100)], money='no', regulatory='no'))
    assert_no_rule(res,'external_blocking')
    # outbound internal to external target is external dependency
    res,md=analyze_ok(payload([step(1,'Call partner',system='Process Service',channel='rest',source='Process Service',target='External Partner',blocking=True,timeout_ms=100)], money='no', regulatory='no'))
    assert_rule(res,'external_blocking')
    assert 'External Partner' in md
    # REST via API gateway must keep REST as primary, API Gateway as component
    res,md=analyze_ok(payload([step(1,'Mobile through gateway',system='API Gateway',channel='rest',source='Client',target='API Gateway',blocking=True,timeout_ms=100), step(2,'Gateway routes to service',system='Process Service',channel='rest',source='API Gateway',target='Process Service',depends_on='1',blocking=True,timeout_ms=100)], money='no', regulatory='no'))
    bad='Основной способ взаимодействия: API Gateway'
    if bad in md: raise AssertionError('API Gateway wrongly used as transport')
    assert 'REST API' in md
    # target-based DWH/audit/storage semantics
    res,md=analyze_ok(payload([step(1,'Save audit evidence',system='Process Service',channel='db',source='Process Service',target='Audit Log',action='save',writes_entity=True,blocking=True,timeout_ms=50)], money='no', regulatory='no'))
    if 'получатель не похож на хранилище' in md.lower():
        raise AssertionError('Audit Log falsely treated as non-storage')


def check_broker_semantics():
    # producer write+publish should trigger outbox
    res,md=analyze_ok(payload([
        step(1,'Save aggregate',channel='db',source='Process Service',target='Main DB',action='save',writes_entity=True,blocking=True),
        step(2,'Publish event to Kafka',channel='kafka',source='Process Service',target='Kafka',system='Process Service',depends_on='1',blocking=False,retry='auto',idempotency='key')
    ], money='no', regulatory='no'))
    assert_rule(res,'dual_write')
    # consumer from Kafka should not be treated as publisher/outbox, but should require consumer controls
    res,md=analyze_ok(payload([
        step(1,'Consume event from Kafka',channel='kafka',source='Kafka',target='Worker',system='Worker',blocking=False,retry='auto',idempotency='key',compensation='retry with DLQ',data_in='filter shared topic by tenant')
    ], money='no', regulatory='no', customer_visible='no', sla_ms='0', load_rps='600', peak_factor='2'))
    assert_no_rule(res,'dual_write')
    assert_rule(res,'stream_consumer_controls')
    # async consumer then external sync call should trigger blocking_in_async
    res,md=analyze_ok(payload([
        step(1,'Consume event from Kafka',channel='kafka',source='Kafka',target='Worker',system='Worker',blocking=False,retry='auto',idempotency='key',compensation='retry with DLQ'),
        step(2,'Call partner in handler',channel='rest',source='Worker',target='External Partner',system='Worker',depends_on='1',blocking=True,timeout_ms=500)
    ], money='no', regulatory='no', customer_visible='no', sla_ms='0'))
    assert_rule(res,'blocking_in_async_handler')


def check_fanin_and_self_routes():
    # fan-in risky no partial should fire
    base=[
        step(1,'Call partner A',channel='rest',source='Process Service',target='External Partner',blocking=True,timeout_ms=100),
        step(2,'Async risk branch',channel='kafka',source='Process Service',target='Kafka',blocking=False,retry='auto',idempotency='key',compensation='DLQ'),
        step(3,'Join branches without policy',channel='rest',source='Process Service',target='Process Service',system='Process Service',depends_on='1,2',blocking=True,action='aggregate',data_in='без partial response policy',timeout_ms=100)
    ]
    res,md=analyze_ok(payload(base, money='no', regulatory='no'))
    assert_rule(res,'fanin_partial_failure')
    # same with explicit partial response should not fire
    base[2]['data_in']='partial response policy with timeout per branch and fallback'
    res,md=analyze_ok(payload(base, money='no', regulatory='no'))
    assert_no_rule(res,'fanin_partial_failure')
    # self-route aggregation should not be schema blocker
    if 'источник и получатель совпадают' in md.lower(): raise AssertionError('self-route aggregate still marked route error')
    # audit fan-in should not fire fanin partial
    res,md=analyze_ok(payload([
        step(1,'Call partner A',channel='rest',source='Process Service',target='External Partner',blocking=True,timeout_ms=100),
        step(2,'Publish branch',channel='kafka',source='Process Service',target='Kafka',blocking=False,retry='auto',idempotency='key',compensation='DLQ'),
        step(3,'Audit Log evidence',channel='db',source='Process Service',target='Audit Log',system='Process Service',depends_on='1,2',blocking=True,action='save',writes_entity=True,timeout_ms=50)
    ], money='no', regulatory='yes'))
    assert_no_rule(res,'fanin_partial_failure')


def check_core_rules_smoke():
    # Each registered rule function must execute on a rich model without exception.
    steps=[]
    o=1
    steps.append(step(o,'Client start',channel='rest',source='Client',target='Process Service',blocking=True,timeout_ms=100)); o+=1
    steps.append(step(o,'Validate and save aggregate',channel='db',source='Process Service',target='Main DB',action='save',writes_entity=True,depends_on='1',blocking=True,timeout_ms=300,retry='auto',idempotency='none')); o+=1
    steps.append(step(o,'Call external limited partner',channel='rest',source='Process Service',target='External Partner',depends_on='2',blocking=True,timeout_ms=900,retry='auto',idempotency='none')); o+=1
    steps.append(step(o,'Publish event',channel='kafka',source='Process Service',target='Kafka',depends_on='2',blocking=False,retry='auto',idempotency='key')); o+=1
    steps.append(step(o,'Consume event',channel='kafka',source='Kafka',target='Worker',system='Worker',depends_on='4',blocking=False,retry='auto',idempotency='key')); o+=1
    steps.append(step(o,'Write DWH synchronously',channel='data_warehouse',source='Process Service',target='DWH',depends_on='3,5',blocking=True,timeout_ms=500,action='save',writes_entity=True)); o+=1
    res,md=analyze_ok(payload(steps, load_rps='200', peak_factor='2'))
    # sanity: lots of rules should fire, and grouping/checklists should exist
    assert len(res['findings']) >= 8, len(res['findings'])
    assert res.get('checklist') and res.get('quality_gates') and res.get('scenario') and res.get('tests')
    # Every rule fn can be invoked directly on this model without raising.
    bad=[]
    for r in engine.RULES:
        try:
            out=r['fn'](res['model'])
            assert isinstance(out,list), r['id']
        except Exception as e:
            bad.append((r['id'],repr(e)))
    if bad: raise AssertionError('rule fn errors: '+str(bad))


def check_random_robustness(n=2500, report_every=25):
    rng=random.Random(8639)
    systems=[s['name'] for s in BASE_SYSTEMS]
    channels=ALL_CHANNELS
    actions=['call','send_event','consume','save','update_status','aggregate','notify','query','archive']
    rendered=0
    for i in range(n):
        count=rng.randint(1,10)
        steps=[]
        for o in range(1,count+1):
            ch=rng.choice(channels)
            src=rng.choice(systems)
            tgt=rng.choice(systems)
            sysname=rng.choice([src,tgt,'Process Service','Worker'])
            deps=[]
            if o>1:
                for _ in range(rng.randint(0,min(3,o-1))):
                    deps.append(rng.randint(1,o-1))
            steps.append(step(o, f'random {i}-{o} {rng.choice(actions)}', system=sysname, channel=ch, blocking=rng.choice([True,False]), depends_on=','.join(map(str,sorted(set(deps)))), source=src, target=tgt, action=rng.choice(actions), timeout_ms=rng.choice([0,50,100,300,1000]), retry=rng.choice(['none','auto','manual']), idempotency=rng.choice(['none','key','natural']), writes_entity=rng.choice([True,False]), compensation=rng.choice(['','DLQ','manual recovery','partial response fallback','без partial response policy'])) )
        p=payload(steps, money=rng.choice(['no','indirect','direct']), regulatory=rng.choice(['yes','no']), customer_visible=rng.choice(['yes','no']), sla_ms=str(rng.choice([0,500,1000,3000])), read_freq=rng.choice(['low','medium','high','very_high']))
        try:
            res=engine.analyze(p)
            if res.get('ok'):
                assert len(res['model']['steps'])==len([s for s in res['model']['steps'] if s.get('name')])
                # Rendering every Nth successful case gives real report coverage without making fuzz unbearably slow.
                if i % report_every == 0:
                    md=report.markdown_report(res)
                    rendered += 1
                    assert isinstance(md,str) and len(md) > 1000
        except Exception:
            raise AssertionError(f'random robustness failed at case {i}\n{json.dumps(p,ensure_ascii=False,indent=2)}\n{traceback.format_exc()}')
    return {'cases': n, 'reports_rendered': rendered}


def main():
    checks=[
        check_validation,
        check_channels_report_coverage,
        check_route_semantics,
        check_broker_semantics,
        check_fanin_and_self_routes,
        check_core_rules_smoke,
        lambda: check_random_robustness(1200,100),
    ]
    for c in checks:
        c(); print(c.__name__ if hasattr(c,'__name__') else 'random_robustness', 'ok')
    print(json.dumps({'status':'ok','channels':len(ALL_CHANNELS),'rules':len(engine.RULES),'random_cases':1200},ensure_ascii=False))

if __name__=='__main__':
    main()
