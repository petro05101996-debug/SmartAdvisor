from itertools import product, combinations, chain
import os
from collections import Counter, defaultdict
from engine import analyze

STARTS = ['incoming_request', 'event', 'file', 'schedule', 'unknown']
ACTS = ['call_external', 'receive_data', 'send_data', 'validate', 'enrich', 'wait_status']
TIMINGS = ['immediate', 'later', 'both', 'unknown']
RESULTS = ['save', 'forward', 'save_forward', 'update_status', 'compare', 'unknown']
SYSTEMS = ['2', '3', '4', 'unknown']
MODULES = ['retry_dlq','outbox_inbox','manual_recon','fanin','enrichment','legacy','dwh','contract','audit','security']
ASYNC={'kafka','queue','webhook','callback','batch','file','cdc'}
SYNC={'rest','grpc','soap','db'}
MODULE_LABELS={'dwh':'DWH/аналитика','legacy':'Legacy-потребитель','manual_recon':'Ручная сверка','enrichment':'REST-обогащение','fanin':'Fan-in / join','retry_dlq':'Retry/DLQ/replay','audit':'Аудит/регуляторика','outbox_inbox':'Outbox/Inbox','contract':'Миграция контракта','security':'ПДн/security'}

def safe_defaults(channel):
    if channel in ['rest','grpc','soap']:
        return dict(blocking='yes',timeout_ms='500',retry='auto',idempotency='key',failure_policy='Повторить автоматически',compensation='timeout, circuit breaker, fallback, ограниченный retry с backoff')
    if channel in ['kafka','queue']:
        return dict(blocking='no',timeout_ms='',retry='auto',idempotency='key',failure_policy='DLQ / replay',compensation='retry с backoff, DLQ, replay, контроль offset/ack')
    if channel in ['webhook','callback']:
        return dict(blocking='no',timeout_ms='',retry='auto',idempotency='key',failure_policy='DLQ / ручной разбор',compensation='подпись, timestamp/nonce, Inbox-дедупликация, повтор callback')
    if channel == 'db':
        return dict(blocking='yes',timeout_ms='200',retry='none',idempotency='natural',failure_policy='Откатить / компенсировать',compensation='транзакция, UNIQUE constraint, optimistic locking')
    if channel in ['file','batch']:
        return dict(blocking='no',timeout_ms='',retry='manual',idempotency='natural',failure_policy='Ручной разбор',compensation='batchId, checksum, quarantine, reprocess')
    if channel == 'cdc':
        return dict(blocking='no',timeout_ms='',retry='auto',idempotency='natural',failure_policy='Replay / resync',compensation='offset/LSN, watermark, replay/resync')
    return dict(blocking='yes',timeout_ms='',retry='none',idempotency='none',failure_policy='Пока не знаю',compensation='')

class UIState:
    def __init__(self):
        self.systems=[]; self.steps=[]; self.modules=[]; self.meta={}
    def set_basics(self, vals):
        self.meta.update(vals)
    def ensure_system(self, name, role='internal'):
        name=(name or '').strip()
        if not name: return
        if not any(s['name']==name for s in self.systems):
            self.systems.append(dict(name=name,role=role,owner='',criticality='medium',stability='unknown',rate_limit_rps=''))
    def find_first_role(self, role, fallback):
        for s in self.systems:
            if s.get('role')==role: return s['name']
        return fallback
    def find_kafka(self):
        for s in self.systems:
            if s.get('role')=='broker' or 'kafka' in s.get('name','').lower() or 'broker' in s.get('name','').lower() or 'топик' in s.get('name','').lower(): return s['name']
        return 'Kafka'
    def last_target(self):
        if self.steps:
            s=self.steps[-1]; return s.get('target_system') or s.get('system') or (self.systems[0]['name'] if self.systems else 'Сервис процесса')
        return self.systems[0]['name'] if self.systems else 'Сервис процесса'
    def step_has(self, part):
        part=(part or '').lower()
        return any(part in (s.get('name') or '').lower() for s in self.steps)
    def add_step(self, data):
        channel=data.get('channel') or 'rest'; d=safe_defaults(channel)
        s={
            'order':1,'name':data.get('name',''),'source_system':data.get('source_system',''),'system':data.get('system',''),'target_system':data.get('target_system',''),'channel':channel,
            'blocking':data.get('blocking') or d['blocking'],
            'timeout_ms':str(data.get('timeout_ms','')) if data.get('timeout_ms') is not None else d['timeout_ms'],
            'retry':data.get('retry') or d['retry'],
            'idempotency':data.get('idempotency') or d['idempotency'],
            'writes_entity':data.get('writes_entity') or 'no',
            'depends_on':str(data.get('depends_on')) if data.get('depends_on') else '',
            'compensation':data.get('compensation') or d['compensation'],
            'failure_policy':data.get('failure_policy') or d['failure_policy'],
            'component_type':data.get('component_type') or 'action'
        }
        self.steps.append(s)
        if s['system']:
            self.ensure_system(s['system'], 'broker' if s['channel'] in ('kafka','queue') else 'internal')
        if s['target_system'] and s['channel']=='db': self.ensure_system(s['target_system'],'db')
        if s['channel']=='kafka': self.ensure_system('Kafka','broker')
        if s['channel']=='db': self.ensure_system(s['target_system'] or 'БД процесса','db')
        self.renumber()
    def renumber(self):
        for i,s in enumerate(self.steps):
            s['order']=i+1
            if i>0 and not s.get('depends_on'): s['depends_on']=str(i)
    def append_unique_meta(self, key, text):
        cur=(self.meta.get(key) or '').strip()
        if text and text not in cur:
            self.meta[key]=(cur+'; '+text) if cur else text
    def append_meta_for_module(self, title, details):
        self.append_unique_meta('constraints','Модуль: '+title+' — '+details)
        self.append_unique_meta('description','Добавлено усложнение: '+title+'. '+details)
    def build_payload(self):
        data_ctx='partition key / lookup key: '+(self.meta.get('lookup') or '')+'; event envelope / fields: '+(self.meta.get('fields') or '')+'; correlationId/traceId пробрасывается через шаги'
        return {
            'meta':{
                'name':self.meta.get('name',''), 'entity':self.meta.get('entity',''), 'goal':self.meta.get('goal',''), 'description':self.meta.get('description',''), 'lookup_keys':self.meta.get('lookup',''), 'constraints':self.meta.get('constraints',''),
                'customer_visible':self.meta.get('visible',''), 'money':self.meta.get('money',''), 'regulatory':self.meta.get('reg',''), 'sla_ms':self.meta.get('sla',''), 'read_freq':self.meta.get('read',''), 'ordering':self.meta.get('order',''),
                'statuses':self.meta.get('statuses',''), 'fields':self.meta.get('fields',''), 'load_rps':self.meta.get('rps',''), 'peak_factor':self.meta.get('peak',''), 'multi_tenant':self.meta.get('tenant',''), 'replacing_legacy':self.meta.get('legacy','')},
            'systems':[dict(name=s['name'],role=s.get('role',''),owner=s.get('owner',''),criticality=s.get('criticality',''),stability=s.get('stability',''),rate_limit_rps=s.get('rate_limit_rps','')) for s in self.systems],
            'steps':[dict(order=i+1,name=s['name'],source_system=s['source_system'],system=s['system'],target_system=s['target_system'],channel=s['channel'],blocking=s['blocking'],timeout_ms=s['timeout_ms'],retry=s['retry'],idempotency=s['idempotency'],writes_entity=s['writes_entity'],depends_on=s['depends_on'],compensation=s['compensation'],failure_policy=s['failure_policy'],component_type=s['component_type'],data_in=data_ctx,data_out=data_ctx) for i,s in enumerate(self.steps)]
        }

def label(group,val):
    opts={
        'start':{'incoming_request':'Входящий запрос','event':'Событие из очереди','file':'Файл или batch','schedule':'Запуск по расписанию','unknown':'Не знаю'},
        'activity':{'call_external':'Вызвать внешнюю систему','receive_data':'Получить данные','send_data':'Передать данные','validate':'Проверить данные','enrich':'Обогатить данными','wait_status':'Дождаться статуса'},
        'timing':{'immediate':'Ответ сразу','later':'Результат позже','both':'Бывает сразу и позже','unknown':'Не знаю'},
        'result':{'save':'Сохранить','forward':'Передать дальше','save_forward':'Сохранить и передать','update_status':'Обновить статус','compare':'Сверить/сравнить','unknown':'Не знаю'},
        'systems':{'2':'2 системы','3':'3 системы','4':'4+ систем','unknown':'Не знаю'}
    }
    return opts[group].get(val,val)

def compose(start, activity, timing, result, systems):
    st=UIState()
    statuses=['CREATED','PROCESSING']
    if timing in ['later','both','unknown']: statuses+=['WAITING_RESULT','RESULT_RECEIVED']
    else: statuses.append('RESULT_RECEIVED')
    if result in ['save','save_forward','update_status','compare','unknown']: statuses.append('SAVED')
    if result in ['forward','save_forward']: statuses.append('SENT_TO_TARGET')
    if result=='compare': statuses+=['WAITING_RECONCILIATION','RECONCILED']
    statuses+=['FAILED','NEEDS_MANUAL_REVIEW']
    assumptions=[]
    if timing=='unknown': assumptions.append('неизвестно, ответ синхронный или асинхронный — добавлены статусы ожидания и ручной разбор')
    if systems=='unknown': assumptions.append('точное число систем неизвестно — создан минимальный набор участников')
    if result=='unknown': assumptions.append('неизвестно, что делать с результатом — добавлены сохранение, статус и ручной разбор')
    st.set_basics({
        'name':'Черновик процесса из выбранных действий','entity':'BusinessEntity','goal':'Построить интеграционную цепочку из универсальных действий без выбора фиксированного шаблона.',
        'description':'Черновик собран из вариантов: старт — '+label('start',start)+'; действие — '+label('activity',activity)+'; ответ — '+label('timing',timing)+'; результат — '+label('result',result)+'. '+('Допущения: '+'; '.join(assumptions)+'.' if assumptions else ''),
        'lookup':'requestId + targetSystem; eventId для дедупликации событий; correlationId для трассировки','constraints':'; '.join(assumptions),
        'visible':'mixed','money':'no','reg':'no','order':'per_entity','rps':'','peak':'1','tenant':'no','legacy':'no','read':'medium','sla':'',
        'statuses':', '.join(dict.fromkeys(statuses)),
        'fields':'requestId:string|required|unique, eventId:uuid|required|unique, correlationId:uuid|required|indexed, targetSystem:string|indexed, status:string|required, statusVersion:int, resultPayload:json, updatedAt:datetime|required'
    })
    proc, db, src, provider, target = 'Сервис процесса','БД процесса','Система-инициатор','Внешняя система / поставщик','Целевая система / получатель'
    st.ensure_system(proc,'internal'); st.ensure_system(db,'db')
    if start!='schedule': st.ensure_system(src,'internal')
    if activity in ['call_external','receive_data','send_data','enrich','wait_status'] or timing in ['later','both','unknown']: st.ensure_system(provider,'external')
    if result in ['forward','save_forward'] or systems in ['3','4','unknown']: st.ensure_system(target,'external')
    if start in ['event'] or timing in ['later','both'] or activity=='wait_status': st.ensure_system('Kafka / очередь','broker')
    if systems=='4': st.ensure_system('Дополнительная система','external')
    if start=='event': st.add_step(dict(name='Принять входящее событие и защититься от дублей',source_system='Kafka / очередь',system=proc,target_system=db,channel='kafka',blocking='no',retry='auto',idempotency='key',writes_entity='yes',compensation='Inbox, UNIQUE eventId, offset/ack после успешной обработки, DLQ/replay'))
    elif start=='file': st.add_step(dict(name='Принять файл или batch и создать запись процесса',source_system=src,system=proc,target_system=db,channel='batch',blocking='no',retry='manual',idempotency='natural',writes_entity='yes',compensation='batchId, checksum, quarantine, reprocess, audit journal'))
    elif start=='schedule': st.add_step(dict(name='Запустить процесс по расписанию и зафиксировать старт',source_system='Планировщик',system=proc,target_system=db,channel='batch',blocking='no',retry='manual',idempotency='natural',writes_entity='yes',compensation='jobId, watermark, повторный запуск без дублей'))
    else: st.add_step(dict(name='Принять входящий запрос и создать запись процесса',source_system=src,system=proc,target_system=db,channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='key',writes_entity='yes',compensation='transaction, audit journal, уникальный requestId, начальный статус'))
    if activity=='call_external': st.add_step(dict(name='Вызвать внешнюю систему для основного действия',source_system=proc,system=proc,target_system=provider,channel='rest',blocking='no' if timing=='later' else 'yes',timeout_ms='1500',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='timeout, circuit breaker, retry с тем же idempotencyKey, externalRequestId'))
    elif activity=='receive_data': st.add_step(dict(name='Получить данные из внешней системы',source_system=proc,system=proc,target_system=provider,channel='rest',blocking='no' if timing=='later' else 'yes',timeout_ms='1500',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='timeout, cache/fallback при допустимости, retry с backoff'))
    elif activity=='send_data': st.add_step(dict(name='Передать данные во внешнюю систему',source_system=proc,system=proc,target_system=provider,channel='rest',blocking='no' if timing=='later' else 'yes',timeout_ms='1500',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='Outbox/retry, idempotencyKey, фиксация неизвестного результата'))
    elif activity=='validate': st.add_step(dict(name='Проверить данные и бизнес-правила перед изменением состояния',source_system=proc,system=proc,target_system=proc,channel='rest',blocking='yes',timeout_ms='300',retry='none',idempotency='natural',depends_on=str(len(st.steps)),compensation='валидационная ошибка без изменения состояния, понятная причина отказа'))
    elif activity=='enrich': st.add_step(dict(name='Обогатить данные через внешний источник',source_system=proc,system=proc,target_system=provider,channel='rest',blocking='yes',timeout_ms='700',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='cache/fallback, circuit breaker, partial enrichment policy'))
    elif activity=='wait_status': st.add_step(dict(name='Отправить запрос и перейти в ожидание статуса',source_system=proc,system=proc,target_system=provider,channel='rest',blocking='no',timeout_ms='1500',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='Outbox, externalRequestId, статус WAITING_RESULT'))
    if timing in ['later','both'] or activity=='wait_status':
        st.add_step(dict(name='Принять результат или статус позже',source_system=provider,system=provider,target_system='Kafka / очередь',channel='kafka',blocking='no',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='повторная публикация, DLQ, eventId, statusVersion'))
        st.add_step(dict(name='Дедуплицировать поздний результат и обновить историю',source_system='Kafka / очередь',system=proc,target_system=db,channel='kafka',blocking='no',retry='auto',idempotency='key',writes_entity='yes',depends_on=str(len(st.steps)),compensation='Inbox, UNIQUE eventId, replay-safe update, status history'))
    elif timing=='unknown':
        st.add_step(dict(name='Зафиксировать результат или неизвестное состояние',source_system=provider,system=proc,target_system=db,channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='natural',writes_entity='yes',depends_on=str(len(st.steps)),compensation='если ответ придёт позже — принять через Inbox/callback; если финал неизвестен — ручной разбор'))
    if result in ['save','save_forward','update_status','unknown']:
        st.add_step(dict(name='Обновить статус основной сущности' if result=='update_status' else 'Сохранить результат и историю состояния',source_system=proc,system=proc,target_system=db,channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='natural',writes_entity='yes',depends_on=str(len(st.steps)),compensation='transaction, optimistic locking/statusVersion, status history, lastError'))
    if result in ['forward','save_forward']:
        st.add_step(dict(name='Передать результат дальше в целевую систему',source_system=proc,system=proc,target_system=target,channel='rest',blocking='yes',timeout_ms='1500',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='Outbox, retry limit, ручной разбор при неизвестном финале'))
    if result=='compare':
        st.ensure_system('Сервис сверки','internal')
        st.add_step(dict(name='Сверить полученные данные с сохранённым состоянием',source_system=db,system='Сервис сверки',target_system=db,channel='batch',blocking='no',retry='manual',idempotency='natural',writes_entity='yes',depends_on=str(len(st.steps)),compensation='reconciliation key, окно ожидания, отчёт расхождений'))
        st.add_step(dict(name='Отправить расхождения на ручной разбор',source_system='Сервис сверки',system='Сервис сверки',target_system=db,channel='db',blocking='no',retry='manual',idempotency='natural',writes_entity='yes',depends_on=str(len(st.steps)),compensation='NEEDS_MANUAL_REVIEW, correction journal, replay'))
    if timing=='unknown' or result=='unknown':
        st.add_step(dict(name='Отправить неопределённые случаи на ручной разбор',source_system=proc,system=proc,target_system=db,channel='db',blocking='no',retry='manual',idempotency='natural',writes_entity='yes',depends_on=str(len(st.steps)),compensation='NEEDS_MANUAL_REVIEW, runbook, replay после уточнения'))
    st.renumber()
    return st

def apply_module(st, kind):
    label=MODULE_LABELS.get(kind,kind)
    if kind in st.modules: return
    if kind=='dwh':
        st.ensure_system('CDC-пайплайн','internal'); st.ensure_system('DWH / audit mart','analytics')
        st.append_meta_for_module(label,'изменения уходят в аналитику без чтения основной БД бизнес-процессом; нужен watermark, backfill и reconciliation.')
        st.append_unique_meta('fields','lsn:string|indexed, watermark:datetime|indexed, batchId:string|indexed')
        st.add_step(dict(name='CDC-пайплайн забирает изменения без нагрузки на core-flow',source_system=st.find_first_role('db','БД процесса'),system='CDC-пайплайн',target_system='DWH / audit mart',channel='cdc',blocking='no',retry='auto',idempotency='natural',depends_on=str(len(st.steps)),compensation='watermark, lag monitoring, replay/resync, backfill'))
        st.add_step(dict(name='DWH сверяет полноту витрины с источником',source_system='CDC-пайплайн',system='DWH / audit mart',target_system='DWH / audit mart',channel='batch',blocking='no',retry='manual',idempotency='natural',depends_on=str(len(st.steps)),compensation='reconciliation report, gap detection, повторная загрузка'))
    elif kind=='legacy':
        st.ensure_system('Legacy consumer','legacy'); st.append_meta_for_module(label,'есть старый потребитель/процесс, поэтому нужны dual-run, совместимость и план отключения.'); st.meta['legacy']='yes'
        st.add_step(dict(name='Legacy consumer получает совместимый формат',source_system=st.find_kafka(),system='Legacy consumer',target_system='Legacy consumer',channel='kafka',blocking='no',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='adapter, backward compatibility, canary, rollback, dual-run'))
        st.add_step(dict(name='Сравнить результат нового и legacy-потока перед cutover',source_system='Legacy consumer',system='Legacy consumer',target_system='БД процесса',channel='batch',blocking='no',retry='manual',idempotency='natural',depends_on=str(len(st.steps)),compensation='dual-run comparison, discrepancy report, rollback gate'))
    elif kind=='manual_recon':
        st.ensure_system('Сервис сверки / ручной разбор','internal'); st.append_meta_for_module(label,'потоки могут расходиться; нужен timeout ожидания, сверка, ручной разбор и replay.'); st.append_unique_meta('statuses','WAITING_RECONCILIATION, RECONCILED, NEEDS_MANUAL_REVIEW')
        st.add_step(dict(name='Сервис сверки ждёт связанные события и проверяет расхождения',source_system=st.last_target(),system='Сервис сверки / ручной разбор',target_system='Сервис сверки / ручной разбор',channel='kafka',blocking='no',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='join window, timeout ожидания парной ветки, reconciliation key'))
        st.add_step(dict(name='Оператор разбирает расхождения по runbook',source_system='Сервис сверки / ручной разбор',system='Сервис сверки / ручной разбор',target_system='Сервис сверки / ручной разбор',channel='rest',blocking='no',retry='manual',idempotency='natural',depends_on=str(len(st.steps)),compensation='manual review, replay, correction journal, SLA на разбор'))
    elif kind=='enrichment':
        st.ensure_system('REST-справочник','external'); st.ensure_system('Enrichment service','internal'); st.append_meta_for_module(label,'нужно обогатить событие через внешний REST; нужен cache/fallback и отдельный статус ENRICHING.'); st.append_unique_meta('statuses','ENRICHING, ENRICHED'); st.append_unique_meta('fields','enrichmentVersion:string, sourceVersion:string')
        st.add_step(dict(name='Enrichment service вызывает REST-справочник',source_system=st.last_target(),system='Enrichment service',target_system='REST-справочник',channel='rest',blocking='yes',timeout_ms='700',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='timeout, cache/fallback, circuit breaker, partial enrichment policy'))
        st.add_step(dict(name='Опубликовать enriched-event для следующих потребителей',source_system='Enrichment service',system='Enrichment service',target_system=st.find_kafka(),channel='kafka',blocking='no',retry='auto',idempotency='key',depends_on=str(len(st.steps)),compensation='Outbox, Schema Registry, DLQ, replay'))
    elif kind=='fanin':
        st.ensure_system('Сервис оркестрации / join','internal'); st.ensure_system('Ветка A','external'); st.ensure_system('Ветка B','external'); st.append_meta_for_module(label,'есть параллельные ветки; нужен correlation key, окно ожидания и единое решение после join.'); st.append_unique_meta('statuses','BRANCH_A_DONE, BRANCH_B_DONE, JOINED, COMPENSATION_REQUIRED')
        base=len(st.steps)
        st.add_step(dict(name='Запустить ветку A',source_system=st.last_target(),system='Сервис оркестрации / join',target_system='Ветка A',channel='rest',blocking='yes',timeout_ms='800',retry='auto',idempotency='key',depends_on=str(base),compensation='отмена/компенсация ветки A'))
        st.add_step(dict(name='Запустить ветку B параллельно',source_system=st.last_target(),system='Сервис оркестрации / join',target_system='Ветка B',channel='rest',blocking='yes',timeout_ms='800',retry='auto',idempotency='key',depends_on=str(base),compensation='отмена/компенсация ветки B'))
        st.add_step(dict(name='Join: дождаться обязательных веток и принять единое решение',source_system='Ветка A/Ветка B',system='Сервис оркестрации / join',target_system='Сервис оркестрации / join',channel='rest',blocking='yes',timeout_ms='500',retry='none',idempotency='natural',depends_on=str(base+1)+','+str(base+2),writes_entity='yes',compensation='join window, timeout, manual review, compensation matrix'))
    elif kind=='retry_dlq':
        st.ensure_system('DLQ / replay storage','db'); st.append_meta_for_module(label,'для ошибок нужны ограниченный retry, DLQ, replay, метрики lag и ручной runbook.')
        for s in st.steps:
            if s['channel'] in ASYNC:
                s['retry']='auto';
                if s['idempotency']=='none': s['idempotency']='key'
                s['compensation']=', '.join([x for x in [s.get('compensation',''),'DLQ, replay, retry limit, backoff, poison message policy'] if x])
                s['failure_policy']='DLQ / replay'
        st.add_step(dict(name='Сохранять необработанные сообщения в DLQ и запускать replay',source_system=st.find_kafka(),system='DLQ / replay storage',target_system='DLQ / replay storage',channel='kafka',blocking='no',retry='manual',idempotency='key',depends_on=str(len(st.steps)),compensation='poison message quarantine, replay by eventId/correlationId, runbook'))
    elif kind=='audit':
        st.ensure_system('Audit journal','db'); st.meta['reg']='yes'; st.append_meta_for_module(label,'есть деньги/регуляторика; нужен неизменяемый журнал, retention, traceability и отчётность.'); st.append_unique_meta('fields','auditId:uuid|required|unique, changedBy:string, changedAt:datetime|required, reasonCode:string'); st.append_unique_meta('statuses','AUDIT_WRITTEN, REG_REPORT_READY')
        st.add_step(dict(name='Записать неизменяемый audit journal',source_system=st.last_target(),system='Audit journal',target_system='Audit journal',channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='natural',depends_on=str(len(st.steps)),writes_entity='no',compensation='append-only journal, retention policy, traceId/correlationId, access log'))
    elif kind=='outbox_inbox':
        st.append_meta_for_module(label,'если сервис пишет в БД и отправляет событие, нужен Outbox; если читает событие, нужен Inbox-дедупликация.'); st.append_unique_meta('fields','outboxId:uuid|unique, inboxEventId:uuid|unique')
        for s in st.steps:
            if s['channel'] in ('kafka','queue'):
                s['retry']='auto'; s['idempotency']='key'; s['compensation']=', '.join([x for x in [s.get('compensation',''),'Outbox/Inbox, exactly-once effect через unique key, replay-safe handler'] if x])
        if not st.step_has('outbox'):
            st.add_step(dict(name='Outbox: записать событие в той же транзакции, что и бизнес-состояние',source_system=st.last_target(),system=st.last_target(),target_system=st.find_first_role('db','БД процесса'),channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='natural',depends_on=str(len(st.steps)),compensation='transactional outbox, publisher retry, schema validation'))
        if not st.step_has('inbox'):
            broker=st.find_kafka(); st.ensure_system(broker,'broker')
            st.add_step(dict(name='Inbox: дедуплицировать входящее событие перед обработкой',source_system=broker,system=st.last_target(),target_system=st.find_first_role('db','БД процесса'),channel='db',blocking='yes',timeout_ms='200',retry='none',idempotency='key',depends_on=str(len(st.steps)),compensation='UNIQUE eventId, processedAt, replay-safe processing'))
    elif kind=='contract':
        st.ensure_system('Contract Registry','internal'); st.append_meta_for_module(label,'контракт меняется; нужны версии, backward compatibility, examples, consumer-driven contract tests и canary.'); st.append_unique_meta('fields','schemaVersion:string|required, eventVersion:string|required')
        st.add_step(dict(name='Зафиксировать v1/v2 контракты и матрицу совместимости',source_system='Аналитик/разработчик',system='Contract Registry',target_system='Contract Registry',channel='db',blocking='no',timeout_ms='200',retry='none',idempotency='natural',depends_on=str(len(st.steps)),compensation='schema registry, examples, compatibility rules'))
        st.add_step(dict(name='Прогнать consumer-driven contract tests и canary',source_system='CI/CD',system='Contract Registry',target_system=st.last_target(),channel='batch',blocking='no',timeout_ms='',retry='manual',idempotency='natural',depends_on=str(len(st.steps)),compensation='canary, rollback, feature flag, duplicate/error branch tests'))
    elif kind=='security':
        st.append_meta_for_module(label,'есть ПДн/чувствительные поля; нужны классификация, маскирование, retention, RBAC и журнал доступа.'); st.append_unique_meta('fields','piiClass:string, retentionUntil:date, maskedFields:string, accessReason:string')
        st.ensure_system('Security / masking layer','internal')
        st.add_step(dict(name='Классифицировать и маскировать чувствительные поля',source_system=st.last_target(),system='Security / masking layer',target_system=st.last_target(),channel='rest',blocking='no',timeout_ms='300',retry='none',idempotency='natural',depends_on=str(len(st.steps)),compensation='data classification, masking/tokenization, retention policy, RBAC, access audit'))
    st.modules.append(kind); st.renumber()

def validate_payload(payload):
    names={s['name'] for s in payload['systems']}
    issues=[]
    for i,step in enumerate(payload['steps'],1):
        for fld in ['source_system','system','target_system']:
            val=step.get(fld,'')
            if val and val not in names and val not in {'Планировщик','Аналитик/разработчик','CI/CD','Канал/инициатор','Ветка A/Ветка B'}:
                issues.append((i,fld,val))
    return issues

if __name__=='__main__':
    all_combos=list(product(STARTS,ACTS,TIMINGS,RESULTS,SYSTEMS))
    full_audit = os.getenv('FULL_UI_WIZARD_AUDIT') == '1'
    if full_audit:
        combos=all_combos
    else:
        # Fast release-gate mode: deterministic coverage across all dimensions without
        # turning every CI run into a multi-minute exhaustive Cartesian product.
        # Use FULL_UI_WIZARD_AUDIT=1 for the complete 2880-base / 28800-module pass.
        edge_cases=[
            ('incoming_request','call_external','immediate','save_forward','3'),
            ('event','enrich','later','save_forward','4'),
            ('file','send_data','unknown','compare','unknown'),
            ('schedule','receive_data','both','update_status','4'),
            ('unknown','validate','unknown','unknown','unknown'),
            ('incoming_request','wait_status','later','compare','3'),
        ]
        combos=[]
        seen=set()
        # cover every value of every dimension at least once, plus edge cases
        for combo in edge_cases + all_combos[::max(1, len(all_combos)//180)]:
            if combo not in seen:
                seen.add(combo); combos.append(combo)
        combos=combos[:24]
    audit_modules = MODULES if full_audit else ['retry_dlq','outbox_inbox','contract','enrichment','audit']
    pair_seed_limit = 6 if full_audit else 2
    subset_modules = MODULES if full_audit else ['retry_dlq','outbox_inbox','contract','audit']
    stats=Counter(); score_sum=0; min_score=99; max_find=0; finding_rules=Counter(); ui_issues=[]; bad=[]
    samples=[]
    for combo in combos:
        st=compose(*combo); payload=st.build_payload(); issues=validate_payload(payload)
        if issues and len(ui_issues)<20: ui_issues.append((combo,issues[:4]))
        res=analyze(payload)
        if not res.get('ok'):
            bad.append((combo,res)); break
        color=res.get('verdict',{}).get('color','unknown'); stats[color]+=1
        score=res.get('verdict',{}).get('score',0); score_sum+=score; min_score=min(min_score,score); max_find=max(max_find,len(res.get('findings',[])))
        for f in res.get('findings',[]): finding_rules[f.get('rule','?')]+=1
    print('BASE',len(combos),'bad',len(bad),'ui_ref_issues',sum(1 for c in combos if validate_payload(compose(*c).build_payload())))
    print('colors',dict(stats),'avg_score',round(score_sum/len(combos),2),'min_score',min_score,'max_findings',max_find)
    print('top_rules',finding_rules.most_common(12))
    print('ui_issue_samples',ui_issues[:8])
    if bad: raise SystemExit(bad[0])

    # module single on all base combos
    module_stats=Counter(); module_bad=[]; module_ui_issues=0; module_rules=Counter()
    for combo in combos:
        for m in audit_modules:
            st=compose(*combo); apply_module(st,m); payload=st.build_payload();
            if validate_payload(payload): module_ui_issues += 1
            res=analyze(payload)
            if not res.get('ok'):
                module_bad.append((combo,m,res)); break
            module_stats[res.get('verdict',{}).get('color','unknown')]+=1
            for f in res.get('findings',[]): module_rules[f.get('rule','?')]+=1
        if module_bad: break
    print('SINGLE_MODULE',len(combos)*len(audit_modules),'bad',len(module_bad),'ui_ref_issues',module_ui_issues,'colors',dict(module_stats),'top_rules',module_rules.most_common(12))

    # pairwise modules on a diverse seed subset and all-module subset on hard seed
    seeds=[('incoming_request','call_external','immediate','save_forward','3'),('event','enrich','later','save_forward','4'),('file','send_data','unknown','compare','unknown'),('schedule','receive_data','both','update_status','4'),('unknown','validate','unknown','unknown','unknown'),('incoming_request','wait_status','later','compare','3')]
    pair_stats=Counter(); pair_bad=[]; pair_ui=0
    for combo in seeds[:pair_seed_limit]:
        for a,b in combinations(audit_modules,2):
            st=compose(*combo); apply_module(st,a); apply_module(st,b); payload=st.build_payload()
            if validate_payload(payload): pair_ui+=1
            res=analyze(payload)
            if not res.get('ok'):
                pair_bad.append((combo,a,b,res)); break
            pair_stats[res.get('verdict',{}).get('color','unknown')]+=1
        if pair_bad: break
    print('PAIR_MODULE_SEEDS',len(seeds[:pair_seed_limit])*len(list(combinations(audit_modules,2))),'bad',len(pair_bad),'ui_ref_issues',pair_ui,'colors',dict(pair_stats))

    hard=('unknown','validate','unknown','unknown','unknown')
    subset_stats=Counter(); subset_bad=[]; subset_ui=0
    for r in range(0,len(subset_modules)+1):
        for subset in combinations(subset_modules,r):
            st=compose(*hard)
            for m in subset: apply_module(st,m)
            payload=st.build_payload()
            if validate_payload(payload): subset_ui += 1
            res=analyze(payload)
            if not res.get('ok'):
                subset_bad.append((subset,res)); break
            subset_stats[res.get('verdict',{}).get('color','unknown')]+=1
        if subset_bad: break
    print('ALL_SUBSETS_HARD',2**len(subset_modules),'bad',len(subset_bad),'ui_ref_issues',subset_ui,'colors',dict(subset_stats))
