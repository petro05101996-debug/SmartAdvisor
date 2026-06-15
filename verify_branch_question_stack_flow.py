#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path
import ui
from engine import analyze

EXPECTED = {
    'rest': ['sync_external_api'],
    'graphql': ['graphql_query'],
    'odata': ['odata_entity_api'],
    'grpc': ['fast_internal_call'],
    'soap': ['old_web_contract'],
    'api_gateway': ['external_entry_control'],
    'service_mesh': ['service_mesh_control'],
    'esb': ['central_routing'],
    'db': ['relational_storage'],
    'read_replica': ['read_replica'],
    'db_sharding': ['sharded_storage'],
    'mongodb': ['document_store'],
    'cassandra': ['wide_column_store'],
    'dynamodb': ['key_value_store'],
    'clickhouse': ['columnar_analytics'],
    'data_warehouse': ['dwh_target_layer'],
    'data_lake': ['data_lake'],
    'lakehouse': ['lakehouse'],
    'redis_cache': ['fast_read'],
    'memcached': ['memcached_cache'],
    'redis_lock': ['exclusive_processing'],
    'search': ['search_projection'],
    'vector_db': ['vector_search'],
    'kafka': ['event_history'],
    'pulsar': ['pulsar_event_log'],
    'rabbitmq': ['task_queue'],
    'activemq': ['enterprise_jms_queue'],
    'ibm_mq': ['enterprise_mq'],
    'nats': ['nats_light_pubsub'],
    'sns_sqs': ['cloud_messaging'],
    'azure_service_bus': ['cloud_messaging_azure'],
    'gcp_pubsub': ['cloud_messaging_google'],
    'redis_streams': ['short_stream'],
    'redis_queue': ['short_queue'],
    'queue': ['unknown_async_buffer'],
    'mqtt': ['mqtt_iot'],
    'webhook': ['external_push_result'],
    'callback': ['delayed_callback'],
    'websocket': ['websocket_realtime'],
    'sse': ['sse_notifications'],
    'sftp': ['partner_file_exchange'],
    'file': ['simple_file_exchange'],
    'object_storage': ['large_files'],
    'batch': ['batch_processing'],
    'cdc': ['dwh'],
    'etl': ['etl_pipeline'],
    'airflow': ['airflow_orchestration'],
    'spark': ['spark_processing'],
    'dbt': ['dbt_models'],
    'workflow_engine': ['workflow_engine'],
    'bpm_engine': ['bpm_engine'],
    'cdn': ['cdn_static'],
    'auth_oidc': ['auth_oidc'],
    'vault': ['vault_secrets'],
    'observability': ['observability_stack'],
}
SYNC={'search', 'cdn', 'mongodb', 'vector_db', 'grpc', 'service_mesh', 'api_gateway', 'db', 'graphql', 'vault', 'esb', 'dynamodb', 'redis_cache', 'read_replica', 'db_sharding', 'memcached', 'rest', 'auth_oidc', 'odata', 'redis_lock', 'soap'}

def simple_payload(ch):
    return {'meta':{'name':'branch coverage '+ch,'entity':'BranchCase','fields':'id:uuid|required|unique,eventId:uuid|unique,correlationId:uuid|indexed','statuses':'CREATED,DONE,FAILED'},'systems':[{'name':'Источник','role':'internal'},{'name':'Сервис процесса','role':'internal'},{'name':'Получатель','role':'external'},{'name':'БД процесса','role':'db'}],'steps':[{'order':1,'name':'Проверочный смысловой шаг '+ch,'source_system':'Источник','system':'Сервис процесса','target_system':'Получатель','channel':ch,'blocking':'yes' if ch in SYNC else 'no','timeout_ms':'500' if ch in SYNC else '','retry':'auto','idempotency':'key','compensation':'контроль ошибок и восстановление','writes_entity':'yes' if ch=='db' else 'no'}]}

def main():
    src=Path('ui.py').read_text(encoding='utf-8')
    start=src.index('const STACK_BRANCH_QUESTIONS')
    end=src.index('function hasModule', start)
    questions=src[start:end]
    found=set(re.findall(r"\['([^']+)'\s*,", questions))
    issues=[]
    for ch, mods in EXPECTED.items():
        if not any(m in found for m in mods):
            issues.append(f'missing_question_for_channel:{ch}:{mods}')
        res=analyze(simple_payload(ch))
        if not res.get('ok'):
            issues.append(f'analyze_failed:{ch}:{res.get("errors")}')
    html=ui.form_page()
    static_clar=re.search(r'<section class="flow-panel clarifications-section">(.*?)<section class="flow-panel stack-section">', html, re.S)
    visible=re.sub(r'<[^>]+>',' ', static_clar.group(1)) if static_clar else ''
    forbidden=['REST API','Kafka','RabbitMQ','Redis','SOAP','gRPC','GraphQL','OData','Pulsar','NATS','SFTP','Object Storage']
    for term in forbidden:
        if term in visible:
            issues.append('tech_visible_before_stack:'+term)
    print(f'branch_questions={len(found)} channels={len(EXPECTED)} issues={len(issues)}')
    for x in issues[:60]: print('ISSUE',x)
    return 1 if issues else 0
if __name__=='__main__':
    raise SystemExit(main())
