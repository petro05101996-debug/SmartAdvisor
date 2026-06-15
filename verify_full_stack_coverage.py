#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from engine import analyze, normalize
CHANNELS=['rest', 'graphql', 'odata', 'grpc', 'soap', 'api_gateway', 'service_mesh', 'esb', 'db', 'read_replica', 'db_sharding', 'mongodb', 'cassandra', 'dynamodb', 'clickhouse', 'data_warehouse', 'data_lake', 'lakehouse', 'redis_cache', 'memcached', 'redis_lock', 'search', 'vector_db', 'kafka', 'pulsar', 'rabbitmq', 'activemq', 'ibm_mq', 'nats', 'sns_sqs', 'azure_service_bus', 'gcp_pubsub', 'redis_streams', 'redis_queue', 'queue', 'mqtt', 'webhook', 'callback', 'websocket', 'sse', 'sftp', 'file', 'object_storage', 'batch', 'cdc', 'etl', 'airflow', 'spark', 'dbt', 'workflow_engine', 'bpm_engine', 'cdn', 'auth_oidc', 'vault', 'observability']
SYNC={'search', 'cdn', 'mongodb', 'vector_db', 'grpc', 'service_mesh', 'api_gateway', 'db', 'graphql', 'vault', 'esb', 'dynamodb', 'redis_cache', 'read_replica', 'db_sharding', 'memcached', 'rest', 'auth_oidc', 'odata', 'redis_lock', 'soap'}
def step(i,ch):
    return {'order':i,'name':f'Проверочный шаг {ch}','system':'Сервис процесса','source_system':'Источник','target_system':'Цель','channel':ch,'blocking':'yes' if ch in SYNC else 'no','timeout_ms':'500' if ch in SYNC else '','retry':'auto','idempotency':'key','depends_on':str(i-1) if i>1 else '','compensation':'контроль ошибок, повторная обработка, ручной разбор, мониторинг','writes_entity':'yes' if ch=='db' else 'no'}
def payload(steps):
    return {'meta':{'name':'full stack coverage','entity':'StackCase','fields':'id:uuid|required|unique, eventId:uuid|unique, correlationId:uuid|indexed','statuses':'CREATED, PROCESSING, DONE, FAILED'},'systems':[{'name':'Источник','role':'internal'},{'name':'Сервис процесса','role':'internal'},{'name':'Цель','role':'external'},{'name':'БД процесса','role':'db'},{'name':'Брокер сообщений','role':'broker'},{'name':'Аналитика','role':'analytics'},{'name':'Кэш','role':'cache'}],'steps':steps}
def main():
    issues=[]
    for ch in CHANNELS:
        p=payload([step(1,ch)]); m=normalize(p); got=m['steps'][0]['channel']; res=analyze(p)
        if got!=ch or not res.get('ok'): issues.append((ch,got,res.get('errors')))
    pair=0
    for a in CHANNELS:
        for b in CHANNELS:
            pair+=1; res=analyze(payload([step(1,a),step(2,b)]))
            if not res.get('ok'): issues.append((a+'->'+b,'failed',res.get('errors')))
    print(f'channels={len(CHANNELS)} single={len(CHANNELS)} pairwise={pair} issues={len(issues)}')
    for x in issues[:30]: print('ISSUE',x)
    return 1 if issues else 0
if __name__=='__main__': raise SystemExit(main())
