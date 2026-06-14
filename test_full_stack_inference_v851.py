# -*- coding: utf-8 -*-
"""Regression: auto stack inference should not collapse specific technologies into generic Redis/Kafka/Batch."""
import re
import subprocess
import tempfile
from pathlib import Path
import ui


def test_auto_stack_inference_covers_specific_stack_signals():
    js = ui.FORM_JS
    with tempfile.TemporaryDirectory() as td:
        js_path = Path(td) / 'form.js'
        probe_path = Path(td) / 'probe.js'
        js_path.write_text(js, encoding='utf-8')
        probe_path.write_text(r'''
const fs=require('fs'), vm=require('vm');
const code=fs.readFileSync(process.argv[2],'utf8');
const context={console, document:{addEventListener:()=>{}, querySelectorAll:()=>[], querySelector:()=>null, getElementById:()=>null, documentElement:{dataset:{},classList:{add:()=>{}}}}, location:{href:''}, fetch:()=>{}, setTimeout};
context.window=context; context.addEventListener=()=>{};
vm.createContext(context); vm.runInContext(code, context);
const cases={
  rest:{name:'Вызвать внешнюю систему и получить ответ',source_system:'Сервис',system:'Сервис',target_system:'Внешняя система'},
  grpc:{name:'Внутренний быстрый вызов между сервисами',source_system:'Сервис A',system:'Сервис A',target_system:'Сервис B'},
  soap:{name:'Вызвать legacy SOAP WSDL систему',source_system:'Сервис',system:'Сервис',target_system:'Legacy-система',compensation:'WSDL'},
  api_gateway:{name:'API Gateway принимает внешний запрос auth rate limit routing',source_system:'Клиент',system:'API Gateway',target_system:'Сервис',compensation:'gateway auth rate limit'},
  esb:{name:'ESB шина маршрутизирует и трансформирует сообщение',source_system:'Legacy',system:'ESB',target_system:'Сервис',compensation:'шина трансформации'},
  db:{name:'Сохранить результат в БД',writes_entity:'yes',source_system:'Сервис',system:'Сервис',target_system:'БД процесса'},
  redis_cache:{name:'Прочитать данные из кэша Redis cache с TTL',source_system:'Сервис',system:'Сервис',target_system:'Redis',compensation:'TTL cache-aside'},
  redis_lock:{name:'Взять distributed lock Redis lock перед обработкой',source_system:'Сервис',system:'Сервис',target_system:'Redis',compensation:'fencing token lock TTL'},
  search:{name:'Обновить поисковый индекс OpenSearch',source_system:'БД',system:'Indexer',target_system:'Search index',compensation:'reindex alias switch'},
  kafka:{name:'Опубликовать событие для replay и fan-out',source_system:'Сервис',system:'Сервис',target_system:'Kafka',compensation:'replay partition key'},
  rabbitmq:{name:'Отправить команду в RabbitMQ worker queue routing DLX',source_system:'Сервис',system:'Сервис',target_system:'RabbitMQ',compensation:'rabbit dlx routing prefetch'},
  redis_streams:{name:'Отправить событие в Redis Streams consumer group',source_system:'Сервис',system:'Сервис',target_system:'Redis Streams',compensation:'redis streams consumer group'},
  redis_queue:{name:'Поставить короткую фоновую задачу в Redis queue',source_system:'Сервис',system:'Сервис',target_system:'Redis queue',compensation:'redis queue TTL'},
  queue:{name:'Отправить задачу в очередь без выбора брокера',source_system:'Сервис',system:'Сервис',target_system:'Очередь',compensation:'очередь'},
  webhook:{name:'Принять webhook от внешней системы',source_system:'Внешняя система',system:'Сервис',target_system:'БД'},
  callback:{name:'Принять callback со статусом от внешней системы',source_system:'Внешняя система',system:'Сервис',target_system:'БД'},
  sftp:{name:'Передать файл по SFTP внешнему партнёру',source_system:'Сервис',system:'Сервис',target_system:'Партнёр',compensation:'sftp checksum'},
  file:{name:'Обработать файл',source_system:'File storage',system:'Сервис',target_system:'БД'},
  object_storage:{name:'Сохранить большой документ в object storage S3 MinIO',source_system:'Сервис',system:'Сервис',target_system:'Object storage'},
  batch:{name:'Запустить batch по расписанию и сверку',source_system:'БД',system:'Batch job',target_system:'DWH'},
  cdc:{name:'CDC-пайплайн забирает изменения',component_type:'cdc',source_system:'БД',system:'CDC',target_system:'DWH'}
};
let issues=[];
for (const [want,s] of Object.entries(cases)) {
  const got=context.inferChannelForStep(s,0).channel;
  if (got!==want) issues.push(`${want}->${got}`);
}
if (issues.length) { console.error(issues.join('\n')); process.exit(1); }
''', encoding='utf-8')
        result = subprocess.run(['node', str(probe_path), str(js_path)], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr or result.stdout


def test_auto_stack_specific_signals_win_over_generic_cache_and_lock_words():
    js = ui.FORM_JS
    with tempfile.TemporaryDirectory() as td:
        js_path = Path(td) / 'form.js'
        probe_path = Path(td) / 'probe_specific_priority.js'
        js_path.write_text(js, encoding='utf-8')
        probe_path.write_text(r'''
const fs=require('fs'), vm=require('vm');
const code=fs.readFileSync(process.argv[2],'utf8');
const context={console, document:{addEventListener:()=>{}, querySelectorAll:()=>[], querySelector:()=>null, getElementById:()=>null, documentElement:{dataset:{},classList:{add:()=>{}}}}, location:{href:''}, fetch:()=>{}, setTimeout};
context.window=context; context.addEventListener=()=>{};
vm.createContext(context); vm.runInContext(code, context);
const cases=[
  ['grpc', {name:'Внутренний быстрый gRPC вызов Profile service для customer context', source_system:'BFF', system:'BFF', target_system:'Profile service', compensation:'deadline, fallback to cached profile'}],
  ['db', {name:'Сохранить заявку, статус и audit journal в БД / OLTP', source_system:'BFF', system:'BFF', target_system:'БД', writes_entity:'yes', compensation:'transaction, UNIQUE requestId, optimistic locking, audit journal'}],
];
let issues=[];
for (const [want,s] of cases) {
  const got=context.inferChannelForStep(s,0).channel;
  if (got!==want) issues.push(`${s.name}: want ${want}, got ${got}`);
}
if (issues.length) { console.error(issues.join('\n')); process.exit(1); }
''', encoding='utf-8')
        result = subprocess.run(['node', str(probe_path), str(js_path)], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr or result.stdout
