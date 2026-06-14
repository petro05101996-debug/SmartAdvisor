#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from engine import analyze, normalize

CHANNELS = [
    'rest','grpc','soap','api_gateway','esb','db','redis_cache','redis_lock','search',
    'kafka','rabbitmq','redis_streams','redis_queue','queue','webhook','callback',
    'sftp','file','object_storage','batch','cdc'
]
SYNC = {'rest','grpc','soap','api_gateway','esb','db','redis_cache','redis_lock','search'}

def step(i, ch):
    return {
        'order': i,
        'name': f'Проверочный шаг {ch}',
        'system': 'Сервис процесса',
        'source_system': 'Источник',
        'target_system': 'Цель',
        'channel': ch,
        'blocking': 'yes' if ch in SYNC else 'no',
        'timeout_ms': '500' if ch in SYNC else '',
        'retry': 'auto',
        'idempotency': 'key',
        'depends_on': str(i-1) if i > 1 else '',
        'compensation': 'timeout circuit breaker DLQ replay TTL checksum watermark reindex fencing token',
        'writes_entity': 'yes' if ch in {'db'} else 'no',
    }

def payload(steps):
    return {
        'meta': {'name':'full stack coverage','entity':'StackCase','fields':'id:uuid|required|unique, eventId:uuid|unique, correlationId:uuid|indexed', 'statuses':'CREATED, PROCESSING, DONE, FAILED'},
        'systems': [
            {'name':'Источник','role':'internal'}, {'name':'Сервис процесса','role':'internal'}, {'name':'Цель','role':'external'},
            {'name':'Redis','role':'cache'}, {'name':'Брокер сообщений','role':'broker'}, {'name':'DWH','role':'analytics'}
        ],
        'steps': steps,
    }

def main():
    issues=[]
    for i,ch in enumerate(CHANNELS,1):
        p=payload([step(1,ch)])
        model=normalize(p)
        got=model['steps'][0]['channel'] if model['steps'] else None
        res=analyze(p)
        if got != ch or not res.get('ok'):
            issues.append((ch, got, res.get('errors')))
    pair_checked=0
    for a in CHANNELS:
        for b in CHANNELS:
            pair_checked += 1
            p=payload([step(1,a), step(2,b)])
            res=analyze(p)
            if not res.get('ok'):
                issues.append((a+'->'+b, 'analyze_failed', res.get('errors')))
    print(f'channels={len(CHANNELS)} single={len(CHANNELS)} pairwise={pair_checked} issues={len(issues)}')
    for x in issues[:20]:
        print('ISSUE', x)
    return 1 if issues else 0

if __name__ == '__main__':
    raise SystemExit(main())
