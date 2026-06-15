#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Интеграционный проектировщик v7.1 — ядро.

Принцип: пользователь описывает бизнес-процесс как граф (шаги, системы,
каналы, таймауты, компенсации). Анализ — структурный: правила работают
над свойствами графа, а не над именами кейсов. Новые ситуации не требуют
нового кода — они автоматически покрываются комбинацией правил.

Без внешних зависимостей: только стандартная библиотека Python 3.11+.
"""
from __future__ import annotations
import re
from invariant_catalog import universal_invariant_probes, invariant_catalog_stats

SYNC_CHANNELS = {'search', 'cdn', 'mongodb', 'vector_db', 'grpc', 'service_mesh', 'api_gateway', 'db', 'graphql', 'vault', 'esb', 'dynamodb', 'redis_cache', 'read_replica', 'db_sharding', 'memcached', 'rest', 'auth_oidc', 'odata', 'redis_lock', 'soap'}
BROKER_CHANNELS = {'ibm_mq', 'redis_streams', 'rabbitmq', 'gcp_pubsub', 'queue', 'activemq', 'redis_queue', 'mqtt', 'sns_sqs', 'nats', 'kafka', 'pulsar', 'azure_service_bus'}
ASYNC_CHANNELS = BROKER_CHANNELS | {'callback', 'batch', 'clickhouse', 'lakehouse', 'spark', 'cdc', 'cassandra', 'sftp', 'workflow_engine', 'data_lake', 'data_warehouse', 'etl', 'airflow', 'sse', 'object_storage', 'observability', 'file', 'dbt', 'websocket', 'webhook', 'bpm_engine'}
ALL_CHANNELS = SYNC_CHANNELS | ASYNC_CHANNELS

SEVERITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'info': 3}
SEVERITY_RU = {'critical': 'Критично', 'high': 'Высокий риск',
               'medium': 'Средний риск', 'info': 'На заметку'}


CHANNEL_RU = {
    "rest": "REST API — синхронный вызов",
    "graphql": "GraphQL — гибкое чтение/агрегация API",
    "odata": "OData — корпоративный API по сущностям",
    "grpc": "gRPC — быстрый внутренний вызов",
    "soap": "SOAP — старый или внешний контракт",
    "api_gateway": "API Gateway — единый внешний вход",
    "service_mesh": "Service Mesh — управление внутренними вызовами",
    "esb": "ESB — интеграционная шина",
    "db": "БД — основная база данных",
    "read_replica": "Реплика БД — масштабирование чтения",
    "db_sharding": "Шардирование БД — разделение данных",
    "mongodb": "MongoDB — документное хранилище",
    "cassandra": "Cassandra/ScyllaDB — ширококолонковое хранилище",
    "dynamodb": "DynamoDB/Key-Value — хранилище ключ-значение",
    "clickhouse": "ClickHouse — аналитическая колоночная БД",
    "data_warehouse": "Data Warehouse — аналитическое хранилище",
    "data_lake": "Data Lake — озеро данных",
    "lakehouse": "Lakehouse — озеро данных с таблицами",
    "redis_cache": "Redis — кэш для быстрого чтения",
    "memcached": "Memcached — простой временный кэш",
    "redis_lock": "Redis — распределённая блокировка",
    "search": "Поисковый индекс",
    "vector_db": "Векторная БД — семантический поиск",
    "kafka": "Kafka — поток событий",
    "pulsar": "Pulsar — поток событий с отдельным хранением",
    "rabbitmq": "RabbitMQ — очередь задач",
    "activemq": "ActiveMQ/Artemis — корпоративная очередь",
    "ibm_mq": "IBM MQ — enterprise-очередь",
    "nats": "NATS — лёгкая шина сообщений",
    "sns_sqs": "AWS SNS/SQS — облачная очередь/рассылка",
    "azure_service_bus": "Azure Service Bus — облачная очередь/топик",
    "gcp_pubsub": "Google Pub/Sub — облачная шина сообщений",
    "redis_streams": "Redis Streams — поток событий",
    "redis_queue": "Redis — короткая очередь задач",
    "queue": "Очередь сообщений, брокер не выбран",
    "mqtt": "MQTT — сообщения от устройств",
    "webhook": "Входящий веб-вызов",
    "callback": "Обратный вызов",
    "websocket": "WebSocket — двусторонний онлайн-канал",
    "sse": "Server-Sent Events — поток уведомлений",
    "sftp": "SFTP — файловый обмен",
    "file": "Файл",
    "object_storage": "Объектное хранилище",
    "batch": "Пакетная обработка по расписанию",
    "cdc": "CDC — передача изменений из БД",
    "etl": "ETL/ELT — загрузка и преобразование данных",
    "airflow": "Airflow — оркестрация загрузок",
    "spark": "Spark — распределённая обработка больших данных",
    "dbt": "dbt — аналитические модели данных",
    "workflow_engine": "Temporal/Workflow engine — длительный процесс с состояниями",
    "bpm_engine": "Camunda/BPMN — бизнес-процесс и ручные задачи",
    "cdn": "CDN — быстрая выдача статического контента",
    "auth_oidc": "OAuth2/OIDC — единая авторизация",
    "vault": "Vault/KMS — секреты и ключи",
    "observability": "Наблюдаемость — метрики, логи, трассировки",
}

TERM_REPLACEMENTS = (
    ('end-to-end', 'сквозной'),
    ('Application / Payment / Claim aggregate', 'агрегат заявки, платежа и обращения'),
    ('direct', 'прямой финансовый риск'),
    ('стандартную обёртка события', 'стандартную обёртку события'),
    ('стандартная обёртка события', 'стандартная обёртка события'),
    ('примеры тело сообщения', 'примеры тела сообщения'),
    ('повторная обработка и безопасную', 'повторную обработку и безопасную'),
    ('Опишите errorCode, повторяемые, userMessage, technicalMessage и mapping HTTP/gRPC.', 'Опишите код ошибки, признак возможности повтора, сообщение пользователю, техническое сообщение для логов и соответствие HTTP/gRPC-статусам.'),
    ('capacity, backpressure', 'пропускная способность и обратное давление'),
    ('event должен', 'событие должно'),
    ('eventType', 'тип события'),
    ('eventVersion', 'версия события'),
    ('aggregateId', 'идентификатор агрегата'),
    ('occurredAt', 'время возникновения события'),
    ('traceId', 'идентификатор трассировки'),
    ('API/event', 'API или событие'),
    ('HTTP/gRPC', 'HTTP/gRPC'),
    ('non-retryable', 'неповторяемые'),
    ('retryable', 'повторяемые'),
    ('event envelope', 'обёртка события'),
    ('Event envelope', 'Обёртка события'),
    ('consumer lag', 'отставание потребителей'),
    ('DWH', 'аналитическое хранилище'),
    ('SLA', 'требование ко времени ответа'),
    ('core-flow', 'основной поток'),
    ('quality gates', 'контрольные проверки готовности'),
    ('Quality gates', 'Контрольные проверки готовности'),
    ('production', 'промышленный запуск'),
    ('Production', 'Промышленный запуск'),
    ('callback/webhook', 'обратный вызов или входящий веб-вызов'),
    ('webhook/callback', 'входящий веб-вызов или обратный вызов'),
    ('webhook', 'входящий веб-вызов'),
    ('Webhook', 'Входящий веб-вызов'),
    ('callback', 'обратный вызов'),
    ('Callback', 'Обратный вызов'),
    ('retry', 'повторная попытка'),
    ('Retry', 'Повторная попытка'),
    ('DLQ', 'очередь ошибочных сообщений'),
    ('replay', 'повторная обработка'),
    ('Replay', 'Повторная обработка'),
    ('runbook', 'инструкция разбора'),
    ('manual review', 'ручной разбор'),
    ('manual recovery', 'ручное восстановление'),
    ('recovery', 'восстановление'),
    ('backoff', 'увеличивающаяся пауза между повторами'),
    ('jitter', 'случайный разброс паузы'),
    ('circuit breaker', 'предохранитель внешнего вызова'),
    ('Circuit Breaker', 'Предохранитель внешнего вызова'),
    ('fallback', 'запасной сценарий'),
    ('rollback', 'откат'),
    ('cutover', 'переключение'),
    ('dual-run', 'параллельный прогон старого и нового контура'),
    ('canary', 'пробное включение на малой доле'),
    ('feature flag', 'управляемый флаг включения'),
    ('backward compatibility', 'обратная совместимость'),
    ('consumer-driven contract tests', 'контрактные тесты со стороны потребителя'),
    ('contract tests', 'контрактные тесты'),
    ('Schema Registry', 'реестр схем событий'),
    ('Inbox', 'таблица входящих сообщений для дедупликации'),
    ('Outbox', 'таблица исходящих сообщений'),
    ('idempotencyKey', 'ключ идемпотентности'),
    ('business key', 'бизнес-ключ'),
    ('correlationId', 'идентификатор сквозной связи'),
    ('eventId', 'идентификатор события'),
    ('statusVersion', 'версия статуса'),
    ('trackingId', 'идентификатор отслеживания'),
    ('payload', 'тело сообщения'),
    ('Offset/ack', 'смещение чтения и подтверждение обработки'),
    ('offset/ack', 'смещение чтения и подтверждение обработки'),
    ('consumer group', 'группа потребителей'),
    ('partition key', 'ключ партиционирования'),
    ('rate limit', 'лимит запросов'),
    ('routing', 'маршрутизация'),
    ('versioning', 'версионирование'),
    ('watermark', 'контрольная отметка загрузки'),
    ('backfill', 'дозагрузка исторических данных'),
    ('resync', 'повторная синхронизация'),
    ('reindex', 'перестроение индекса'),
    ('lag', 'отставание обработки'),
    ('retention', 'срок хранения'),
    ('quarantine', 'карантин ошибок'),
    ('checksum', 'контрольная сумма'),
    ('recordCount', 'контроль количества записей'),
    ('batchId', 'идентификатор пакета'),
    ('jobId', 'идентификатор задания'),
    ('timestamp/nonce', 'время запроса и одноразовый номер'),
    ('fencing token', 'защитный токен блокировки'),
    ('cache-aside', 'кэширование с чтением из источника при промахе'),
    ('source of truth', 'источник истины'),
    ('cache stampede', 'лавина одновременных обращений к источнику данных'),
    ('Object storage', 'объектное хранилище'),
    ('object storage', 'объектное хранилище'),
    ('fan-out', 'рассылка в несколько веток'),
    ('fan-in', 'сведение нескольких веток'),
    ('join', 'сведение веток'),
    ('Join', 'Сведение веток'),
    ('partial response', 'частичный ответ'),
    ('read-model', 'модель для чтения'),
    ('read-through', 'чтение через кэш'),
    ('parking lot', 'карантинная очередь'),
    ('ack/nack', 'подтверждение или отказ обработки'),
    ('prefetch', 'предварительная выдача сообщений обработчику'),
)


def display_channel(channel):
    return CHANNEL_RU.get(_low(channel), _s(channel) or 'канал не указан')


def humanize_terms(text):
    out = str(text or '')
    for old, new in TERM_REPLACEMENTS:
        out = out.replace(old, new)
    # Небольшая правка падежей после терминологических замен.
    grammar = (
        ('сквозной заявка', 'сквозная заявка'),
        ('до аналитическое хранилище', 'до аналитического хранилища'),
        ('стандартную обёртка события', 'стандартную обёртку события'),
        ('стандартная обёртка события', 'стандартная обёртка события'),
        ('примеры тело сообщения', 'примеры тела сообщения'),
        ('повторная обработка и безопасную', 'повторную обработку и безопасную'),
        ('Для каждого REST, API или событие должно быть', 'Для каждого REST/API или события должны быть'),
        ('пропускная способность и обратное давление и', 'пропускная способность, обратное давление и'),
        ('требование ко времени ответа', 'требование к времени ответа'),
        ('Требование ко времени ответа', 'Требование к времени ответа'),
        ('после исчерпания повторная попытка', 'после исчерпания попыток'),
        ('повторная попытка exhausted', 'попытки исчерпаны'),
        ('повторная обработка должен', 'повторная обработка должна'),
        ('повторная попытка должен', 'повторная попытка должна'),
        ('без таблица исходящих сообщений', 'без таблицы исходящих сообщений'),
        ('без таблица входящих сообщений', 'без таблицы входящих сообщений'),
        ('используется таблица исходящих сообщений', 'используется таблица исходящих сообщений'),
        ('используется таблица входящих сообщений', 'используется таблица входящих сообщений'),
        ('входящий веб-вызов используется таблица входящих сообщений', 'для входящего веб-вызова используется таблица входящих сообщений'),
        ('Входящий входящий веб-вызов', 'Входящий веб-вызов'),
        ('входящий входящий веб-вызов', 'входящий веб-вызов'),
        ('лимит запросовs', 'лимиты запросов'),
        ('Лимит запросовs', 'Лимиты запросов'),
        ('повторная обработка должен', 'повторная обработка должна'),
        ('Повторная обработка должен', 'Повторная обработка должна'),
        ('повторная попытка, который', 'повторная попытка, которая'),
        ('каждый повторная попытка', 'каждая повторная попытка'),
        ('Каждый повторная попытка', 'Каждая повторная попытка'),
        ('таблица входящих сообщений для дедупликации table', 'таблица входящих сообщений для дедупликации'),
        ('увеличивающаяся пауза между повторами', 'увеличивающаяся пауза между повторными попытками'),
        ('повторная обработка-процедура', 'процедура повторной обработки'),
        ('требование к времени ответа доставки', 'целевое время доставки'),
        ('требование к времени ответа партнёра', 'целевое время ответа партнёра'),
        ('требование к времени ответа/таймаут', 'целевое время ответа и таймаут'),
    )
    for old, new in grammar:
        out = out.replace(old, new)
    return out


# ---------------------------------------------------------------- utilities
def _s(x):
    return str(x or '').strip()


def _low(x):
    return _s(x).lower()


def _b(x):
    return _low(x) in ('yes', 'true', '1', 'да', 'on', 'blocking')


def _int(x, default=0):
    try:
        return int(float(str(x).strip()))
    except (TypeError, ValueError):
        return default


def split_csv(x):
    return [i.strip() for i in _s(x).replace('\n', ',').split(',') if i.strip()]


def parse_deps(raw):
    """depends_on как int | список | строка 'a,b' -> список order'ов родителей (без 0).

    Несколько родителей = настоящий fan-in (join): шаг ждёт несколько ветвей.
    Обратная совместимость: одиночное число работает как раньше."""
    items = raw if isinstance(raw, (list, tuple)) else (
        split_csv(raw) if isinstance(raw, str) else [raw])
    out, seen = [], set()
    for it in items:
        v = _int(it, 0)
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def parse_fields(raw):
    """'name:type|required|unique|indexed|sensitive' через запятую."""
    out = []
    for item in split_csv(raw):
        parts = [p.strip() for p in item.split('|')]
        name_type = parts[0].split(':')
        name = name_type[0].strip()
        if not name:
            continue
        ftype = name_type[1].strip().lower() if len(name_type) > 1 else 'string'
        flags = {p.lower() for p in parts[1:]}
        out.append({'name': name, 'type': ftype,
                    'required': 'required' in flags, 'unique': 'unique' in flags,
                    'indexed': 'indexed' in flags, 'sensitive': 'sensitive' in flags})
    return out


# ---------------------------------------------------------------- graph
def normalize(payload):
    """JSON конструктора -> нормализованная модель процесса."""
    meta_in = payload.get('meta') or {}
    meta = {
        'name': _s(meta_in.get('name')) or 'Без названия',
        'entity': _s(meta_in.get('entity')) or 'Entity',
        'goal': _s(meta_in.get('goal')),
        'description': _s(meta_in.get('description')),
        'lookup_keys': _s(meta_in.get('lookup_keys')),
        'constraints': _s(meta_in.get('constraints')),
        'customer_visible': (_b(meta_in.get('customer_visible')) or _low(meta_in.get('customer_visible')) in ('yes', 'mixed', 'да')),
        'money': _low(meta_in.get('money')) or 'no',            # no|indirect|direct
        'regulatory': _b(meta_in.get('regulatory')),
        'sla_ms': _int(meta_in.get('sla_ms'), 0),               # 0 = асинхронно/не задано
        'read_freq': _low(meta_in.get('read_freq')) or 'medium',  # low|medium|high|very_high
        'ordering': _low(meta_in.get('ordering')) or 'no',      # no|per_entity|global
        'statuses': split_csv(meta_in.get('statuses')),
        'fields': parse_fields(meta_in.get('fields')),
        'load_rps': _int(meta_in.get('load_rps'), 0),
        'peak_factor': max(1, _int(meta_in.get('peak_factor'), 1)),
        'multi_tenant': _b(meta_in.get('multi_tenant')),
        'replacing_legacy': _b(meta_in.get('replacing_legacy')),
    }
    meta['peak_rps'] = meta['load_rps'] * meta['peak_factor']

    systems = {}
    for s in payload.get('systems') or []:
        name = _s(s.get('name'))
        if not name:
            continue
        systems[name] = {
            'name': name,
            'role': _low(s.get('role')) or 'internal',  # internal|external|broker|db|legacy|analytics
            'owner': _s(s.get('owner')),
            'criticality': _low(s.get('criticality')) or 'medium',
            'stability': _low(s.get('stability')) or 'unknown',  # stable|unstable|limited|unknown
            'rate_limit_rps': _int(s.get('rate_limit_rps'), 0),
        }

    steps = []
    for i, st in enumerate(payload.get('steps') or [], 1):
        name = _s(st.get('name'))
        if not name:
            continue
        system = _s(st.get('system')) or '—'
        if system not in systems:
            systems[system] = {'name': system, 'role': 'internal', 'owner': '',
                               'criticality': 'medium', 'stability': 'unknown',
                               'rate_limit_rps': 0}
        channel = _low(st.get('channel'))
        if channel not in ALL_CHANNELS:
            channel = 'rest'
        order = _int(st.get('order'), i)
        deps = parse_deps(st.get('depends_on'))
        steps.append({
            'order': order,
            'name': name,
            'system': system,
            'channel': channel,
            'sync': channel in SYNC_CHANNELS,
            'blocking': _b(st.get('blocking')),
            'timeout_ms': _int(st.get('timeout_ms'), 0),
            'retry': _low(st.get('retry')) or 'none',           # none|auto|manual
            'idempotency': _low(st.get('idempotency')) or 'none',  # none|key|natural
            'compensation': _s(st.get('compensation')),
            'writes_entity': _b(st.get('writes_entity')),
            'depends_on': deps[0] if deps else 0,   # основной родитель (совместимость)
            'deps': deps,                           # все родители (fan-in)
            'data_in': _s(st.get('data_in')),
            'data_out': _s(st.get('data_out')),
            'source_system': _s(st.get('source_system')),
            'target_system': _s(st.get('target_system')),
            'stack_reason': _s(st.get('stack_reason')),
            'stack_override': _b(st.get('stack_override')) or _b(st.get('stack_overridden')),
        })
    steps.sort(key=lambda x: x['order'])
    return {'meta': meta, 'systems': systems, 'steps': steps}


def build_graph(model):
    """Добавляет производные структурные свойства. Граф — DAG: у шага может быть
    несколько родителей (fan-in/join). Латентность join'а = max по ветвям."""
    steps, systems, meta = model['steps'], model['systems'], model['meta']
    by_order = {s['order']: s for s in steps}
    children = {}
    for s in steps:
        for d in (s['deps'] or [0]):           # пустые deps -> виртуальный корень 0
            children.setdefault(d, []).append(s)
    for s in steps:
        s['children'] = [c['order'] for c in children.get(s['order'], [])]
        s['external'] = systems[s['system']]['role'] == 'external'
        s['is_join'] = len([d for d in s['deps'] if d in by_order]) >= 2

    def blocking_parents(s):
        return [by_order[d] for d in s['deps'] if d in by_order and by_order[d]['blocking']]

    # Критический путь по латентности на блокирующем подграфе, считая от корня.
    # Шаг на синхронном пути ответа, если он блокирующий и достижим по блокирующим
    # рёбрам от корня (deps пусты). Латентность join'а = max по ветвям + свой таймаут.
    lat, parent_choice = {}, {}

    def latency(o, stack):
        if o in lat:
            return lat[o]
        if o in stack:                          # цикл — обрываем
            return None
        s = by_order[o]
        if not s['blocking']:
            lat[o] = None
            return None
        bp = blocking_parents(s)
        best, best_p = None, None
        for p in bp:
            lp = latency(p['order'], stack | {o})
            if lp is not None and (best is None or lp > best):
                best, best_p = lp, p['order']
        if best is None and s['deps'] and not bp:
            # все родители существуют, но не блокирующие -> шаг за async-границей,
            # вне синхронного пути ответа
            if any(d in by_order for d in s['deps']):
                lat[o] = None
                return None
        val = s['timeout_ms'] + (best or 0)
        lat[o], parent_choice[o] = val, best_p
        return val

    for s in steps:
        latency(s['order'], frozenset())

    end = max((o for o in lat if lat[o] is not None),
              key=lambda o: (lat[o], len(by_order[o]['deps']), o), default=None)
    critical = []
    cur = end
    guard = set()
    while cur is not None and cur not in guard:
        guard.add(cur)
        critical.append(by_order[cur])
        cur = parent_choice.get(cur)
    critical.reverse()

    # Синхронная цепочка: макс. подряд идущих sync+blocking шагов по всему DAG.
    srun, sparent = {}, {}

    def sync_run(o, stack):
        if o in srun:
            return srun[o]
        if o in stack:
            return 0
        s = by_order[o]
        if not (s['sync'] and s['blocking']):
            srun[o] = 0
            return 0
        best, best_p = 0, None
        for p in blocking_parents(s):
            if p['sync']:
                r = sync_run(p['order'], stack | {o})
                if r > best:
                    best, best_p = r, p['order']
        srun[o], sparent[o] = 1 + best, best_p
        return srun[o]

    for s in steps:
        sync_run(s['order'], frozenset())
    sync_end = max(srun, key=lambda o: (srun[o], o), default=None)
    sync_depth = srun.get(sync_end, 0) if sync_end is not None else 0
    sync_chain_path, cur, guard = [], sync_end, set()
    while sync_depth and cur is not None and cur not in guard:
        guard.add(cur)
        sync_chain_path.append(by_order[cur])
        cur = sparent.get(cur)
    sync_chain_path.reverse()

    model['graph'] = {
        'critical_path': critical,
        'critical_budget_ms': sum(s['timeout_ms'] for s in critical),
        'sync_depth': sync_depth,
        'sync_chain_path': sync_chain_path,
        'writers': sorted({s['system'] for s in steps if s['writes_entity']}),
        'async_steps': [s for s in steps if not s['sync']],
        'external_blocking': [s for s in steps if s['external'] and s['blocking']],
        'joins': [s for s in steps if s['is_join']],
        'by_order': by_order,
        'children': children,
    }
    return model


def _find_cycle(model):
    """Возвращает узлы цикла зависимостей (len>=2) или None. depends_on —
    единственный родитель, так что цикл — петля в функциональном графе."""
    parent = {s['order']: s['depends_on'] for s in model['steps']}
    for start in parent:
        seen, cur = [], start
        while cur and cur in parent:
            if cur in seen:
                cycle = seen[seen.index(cur):] + [cur]
                return cycle if len(set(cycle)) >= 2 else None
            seen.append(cur)
            cur = parent[cur]
    return None


def validate(model):
    errors = []
    if not model['steps']:
        errors.append('Добавьте хотя бы один шаг процесса.')
    orders = {x['order'] for x in model['steps']}
    seen = set()
    for s in model['steps']:
        if s['order'] in seen:
            errors.append(f"Дублируется порядковый номер шага {s['order']}.")
        seen.add(s['order'])
        for d in s['deps']:
            if d not in orders:
                errors.append(f"Шаг «{s['name']}»: зависимость от несуществующего шага {d}.")
        if s['depends_on'] == s['order'] or s['order'] in s['deps']:
            errors.append(f"Шаг «{s['name']}» зависит сам от себя.")
    cyc = _find_cycle(model)
    if cyc:
        errors.append('Циклическая зависимость шагов: ' + ' → '.join(str(o) for o in cyc) + '.')
    return errors


# ---------------------------------------------------------------- rules
# Каждое правило — функция над графом, возвращающая список находок.
# Находка: {severity, title, where, why, fix}. Правила структурные и
# композируются: любой новый «кейс» — это просто новая комбинация находок.
RULES = []


def rule(rid, category):
    def deco(fn):
        RULES.append({'id': rid, 'category': category, 'fn': fn})
        return fn
    return deco


def F(severity, title, where, why, fix):
    return {'severity': severity, 'title': title, 'where': where, 'why': why, 'fix': fix}


@rule('sync_chain_depth', 'Надёжность')
def r_sync_chain(model):
    g, meta = model['graph'], model['meta']
    if g['sync_depth'] < 3:
        return []
    names = ' → '.join(s['name'] for s in g['sync_chain_path'])
    sev = 'critical' if (meta['customer_visible'] and any(s['external'] for s in g['sync_chain_path'])) else 'high'
    return [F(sev, f"В процессе есть слишком длинная синхронная цепочка: {g['sync_depth']} блокирующих шага подряд.",
              names,
              'Каждое синхронное звено увеличивает вероятность отказа и добавляет задержку к общему времени ответа; '
              'если откажет любое звено, весь пользовательский или системный запрос завершится ошибкой.',
              'Разорвите цепочку: после первого подтверждённого шага переводите дальнейшую обработку в события или очередь, '
              'а клиенту возвращайте trackingId и понятную статусную модель процесса.')]


@rule('external_blocking', 'Надёжность')
def r_external_blocking(model):
    out = []
    meta = model['meta']
    for s in model['graph']['external_blocking']:
        sev = 'critical' if (meta['customer_visible'] and 0 < meta['sla_ms'] <= 1000) else 'high'
        out.append(F(sev, 'Процесс блокируется на вызове внешней системы.',
                     f"Шаг {s['order']} «{s['name']}» → {s['system']}",
                     'Внешняя система находится вне вашего контроля: её деградация напрямую ухудшает ваш SLA '
                     'и может исчерпать пул рабочих потоков.',
                     'Настройте timeout, circuit breaker и fallback-ответ; если бизнес-сценарий позволяет, переведите шаг '
                     'в асинхронную обработку через очередь с компенсацией.'))
    return out


@rule('retry_without_idempotency', 'Целостность данных')
def r_retry_idem(model):
    out = []
    money = model['meta']['money'] == 'direct'
    for s in model['steps']:
        if s['retry'] != 'none' and s['idempotency'] == 'none' and (s['writes_entity'] or money):
            sev = 'critical' if money else 'high'
            why = ('Повтор без ключа идемпотентности может создать дубли бизнес-операции'
                   + ('; для денег это double-spend/двойное списание.' if money else '.'))
            out.append(F(sev, 'Повторная обработка настроена без идемпотентности.',
                         f"Шаг {s['order']} «{s['name']}»", why,
                         'Добавьте idempotencyKey с уникальным индексом в БД или используйте устойчивый natural key; '
                         'consumer должен обрабатывать повторную доставку без изменения результата второй раз.'))
    return out


@rule('money_controls', 'Финансовая безопасность')
def r_money(model):
    meta, steps = model['meta'], model['steps']
    if meta['money'] != 'direct':
        return []
    out = []
    writers = model['graph']['writers']
    if len(writers) > 1:
        out.append(F('critical', 'Финансовую сущность изменяют несколько систем одновременно.',
                     ', '.join(writers),
                     'Несколько писателей баланса или лимита без единого владельца данных — '
                     'это прямой путь к расхождениям, двойному списанию и сложным инцидентам.',
                     'Назначьте единственного писателя для счёта или шарда и ведите append-only ledger; '
                     'остальные системы должны отправлять команды, а не менять финансовое состояние напрямую.'))
    if not any(s['idempotency'] != 'none' for s in steps if s['writes_entity']):
        out.append(F('critical', 'Финансовая запись выполняется без защиты от повторного применения.',
                     'Шаги, пишущие сущность',
                     'При сетевых повторах одна и та же бизнес-операция может быть применена дважды.',
                     'Используйте operationId с уникальным индексом и ledger с проводками вместо прямого update баланса.'))
    return out


@rule('async_without_recovery', 'Надёжность')
def r_async_recovery(model):
    out = []
    for s in model['graph']['async_steps']:
        if s['channel'] in BROKER_CHANNELS \
                and s['retry'] == 'none' and not s['compensation']:
            out.append(F('high', 'Асинхронный шаг не имеет retry, DLQ или компенсации.',
                         f"Шаг {s['order']} «{s['name']}» ({s['channel']})",
                         'Если обработка сообщения завершится ошибкой, сообщение может быть потеряно без заметного сигнала, '
                         'а процесс останется в промежуточном статусе.',
                         'Добавьте retry с backoff, затем DLQ или карантин, алерт и ручной разбор; '
                         'также обязательно предусмотрите replay после исправления причины ошибки.'))
    return out


@rule('poison_retry', 'Надёжность')
def r_poison_retry(model):
    out = []
    for s in model['steps']:
        blob = _low(s['compensation']) + ' ' + _low(s['data_out'])
        has_dlq = bool(re.search(r'dlq|карантин|лимит|max|попыт', blob))
        if s['retry'] == 'auto' and not s['sync'] and not has_dlq:
            out.append(F('medium', 'Retry настроен без лимита попыток и DLQ.',
                         f"Шаг {s['order']} «{s['name']}»",
                         '«Ядовитое» сообщение будет снова и снова возвращаться в очередь: '
                         'это создаст бесконечный цикл ошибок, лишнюю нагрузку на CPU и переполнение очереди.',
                         'Добавьте счётчик попыток и экспоненциальный backoff; после заданного числа попыток отправляйте сообщение в '
                         'DLQ или карантин с алертом и описанной процедурой replay.'))
    return out


@rule('inbound_security', 'Безопасность')
def r_inbound_security(model):
    out = []
    for s in model['steps']:
        if s['channel'] in ('webhook', 'callback'):
            blob = _low(s['name']) + ' ' + _low(s['data_in'])
            verified = bool(re.search(r'подпис|sign|hmac|jwt|mtls', blob))
            sev = 'info' if verified else 'high'
            why = ('Входящий webhook является публичной точкой входа: без проверки подписи любой внешний отправитель '
                   'может подделать бизнес-событие обычным POST-запросом.')
            fix = ('Проверяйте HMAC или подпись провайдера до любой бизнес-обработки; '
                   'секрет храните в защищённом хранилище и предусмотрите его ротацию.')
            if verified:
                why = 'Подпись проверяется, поэтому этот контроль нужно явно зафиксировать в требованиях и тестах.'
                fix = 'Добавьте негативный тест: запрос с неверной подписью отклоняется до запуска бизнес-логики.'
            out.append(F(sev, 'Входящий webhook должен проходить проверку подлинности.',
                         f"Шаг {s['order']} «{s['name']}»", why, fix))
    return out


@rule('saga_without_compensation', 'Целостность данных')
def r_saga(model):
    steps = model['steps']
    writing = [s for s in steps if s['writes_entity']]
    multi_system_write = len({s['system'] for s in writing}) >= 2
    if multi_system_write and not any(s['compensation'] for s in steps):
        return [F('high', 'Распределённая запись выполняется без компенсаций.',
                  ', '.join(sorted({s['system'] for s in writing})),
                  'Запись выполняется в нескольких системах; если сбой произойдёт в середине цепочки, данные разойдутся, '
                  'а понятного механизма отката не будет.',
                  'Используйте Saga: для каждого пишущего шага должна быть компенсация или политика '
                  '«retry → compensation → manual recovery»; статусная модель должна фиксировать прогресс процесса.')]
    return []


@rule('sla_budget', 'Производительность')
def r_sla_budget(model):
    meta, g = model['meta'], model['graph']
    if not meta['sla_ms'] or not g['critical_path']:
        return []
    budget = g['critical_budget_ms']
    if budget > meta['sla_ms']:
        chain_txt = ' + '.join(f"{s['timeout_ms']}мс ({s['name']})"
                               for s in g['critical_path'] if s['timeout_ms'])
        return [F('critical', 'Бюджет таймаутов превышает заявленный SLA.',
                  chain_txt or 'критический путь',
                  f"Сумма таймаутов критического пути {budget} мс > SLA {meta['sla_ms']} мс: "
                  'в худшем случае система физически не успеет ответить вовремя.',
                  'Сократите таймауты отдельных звеньев, распараллельте независимые шаги или переведите '
                  'хвост цепочки в асинхронную обработку с trackingId.')]
    return []


@rule('missing_timeouts', 'Надёжность')
def r_missing_timeouts(model):
    bad = [s for s in model['steps'] if s['blocking'] and s['sync'] and not s['timeout_ms']]
    if not bad:
        return []
    names = ', '.join(f"{s['order']} «{s['name']}»" for s in bad)
    return [F('medium', 'В блокирующих шагах не задан timeout.', names,
              'Без timeout зависший вызов бесконечно удерживает поток и создаёт каскад ожиданий.',
              'Задайте timeout каждому блокирующему вызову и распределите бюджет времени от SLA сверху вниз.')]


def _is_consumption(model, s):
    """Шаг с каналом kafka/queue, чей родитель — брокер, это потребление, не публикация."""
    return any(model['systems'].get(p['system'], {}).get('role') == 'broker'
               for p in (model['graph']['by_order'].get(d) for d in s['deps'])
               if p)


@rule('dual_write', 'Целостность данных')
def r_dual_write(model):
    # Одна система и пишет сущность, и публикует событие — нужен outbox.
    by_system = {}
    for s in model['steps']:
        by_system.setdefault(s['system'], []).append(s)
    out = []
    for sysname, ss in by_system.items():
        writes = any(x['writes_entity'] for x in ss)
        publishes = [x for x in ss if x['channel'] in BROKER_CHANNELS
                     and not _is_consumption(model, x)]
        mentions_outbox = any('outbox' in _low(x['compensation']) + _low(x['data_out']) for x in ss)
        if writes and publishes and not mentions_outbox:
            out.append(F('high', 'Система одновременно пишет в БД и публикует событие без Outbox.',
                         f"{sysname}: " + ', '.join(f"«{x['name']}»" for x in publishes),
                         'Запись в БД и публикация события являются двумя несвязанными операциями: '
                         'при сбое между ними событие может потеряться или, наоборот, появиться без записи в БД.',
                         'Используйте Transactional Outbox: событие записывается в той же транзакции, что и агрегат, '
                         'а отдельный publisher вычитывает outbox и публикует событие с retry.'))
    return out


@rule('callback_inbox', 'Целостность данных')
def r_callback(model):
    out = []
    for s in model['steps']:
        if s['channel'] in ('webhook', 'callback') and s['idempotency'] == 'none':
            out.append(F('high', 'Webhook или callback принимается без дедупликации.',
                         f"Шаг {s['order']} «{s['name']}»",
                         'Провайдеры доставляют callback повторно по модели at-least-once: '
                         'без Inbox один и тот же платёж или ответ может быть обработан дважды.',
                         'Добавьте Inbox-таблицу с уникальным providerEventId; обработку запускайте только '
                         'после успешной вставки ключа дедупликации.'))
    return out


@rule('slow_channel_in_fast_path', 'Производительность')
def r_slow_channel(model):
    meta = model['meta']
    out = []
    for s in model['steps']:
        if s['channel'] in ('file', 'batch') and s['blocking'] \
                and (meta['customer_visible'] or (0 < meta['sla_ms'] < 60000)):
            out.append(F('high', 'Файловый или batch-канал находится в быстром пути процесса.',
                         f"Шаг {s['order']} «{s['name']}»",
                         'Файловый обмен обычно измеряется минутами или часами; он несовместим с клиентским '
                         'ожиданием и секундным SLA.',
                         'Вынесите этот шаг из критического пути, сделав его non-blocking, либо замените '
                         'его на API или событие; файл оставьте только для отчётности и сверок.'))
    return out


@rule('analytics_in_core', 'Производительность')
def r_analytics_core(model):
    out = []
    for s in model['steps']:
        role = model['systems'][s['system']]['role']
        looks_dwh = role == 'analytics' or re.search(r'dwh|анали|витрин', _low(s['system']))
        if looks_dwh and s['blocking']:
            out.append(F('high', 'DWH или аналитика находятся в операционном core-flow.',
                         f"Шаг {s['order']} «{s['name']}» → {s['system']}",
                         'Аналитическое хранилище обычно не обеспечивает операционный SLA: его деградация '
                         'не должна останавливать основной бизнес-процесс.',
                         'Сделайте шаг non-blocking: используйте CDC, ETL или событие после фиксации результата в операционной системе.'))
    return out


@rule('regulatory_audit', 'Комплаенс')
def r_regulatory(model):
    meta = model['meta']
    if not meta['regulatory']:
        return []
    blob = ' '.join(_low(s['name']) + ' ' + _low(s['data_out']) for s in model['steps'])
    has_audit = bool(re.search(r'аудит|audit|журнал|evidence|лог операций', blob))
    if has_audit:
        return []
    return [F('high', 'В регуляторном процессе не описан аудиторский след.',
              'Весь процесс',
              'Юридически значимые шаги требуют доказуемой истории: кто, что, когда и '
              'на каком основании выполнил.',
              'Ведите append-only журнал операций с retention-политикой и сохраняйте evidence на каждый '
              'значимый переход статуса.')]


@rule('ordering', 'Целостность данных')
def r_ordering(model):
    meta = model['meta']
    kafka_steps = [s for s in model['steps'] if s['channel'] in BROKER_CHANNELS]
    if meta['ordering'] == 'per_entity' and kafka_steps:
        mentioned = any(re.search(r'key|ключ|partition', _low(s['data_in'])) for s in kafka_steps)
        if not mentioned:
            return [F('medium', 'Для порядка событий в рамках сущности не задан ключ партиционирования.',
                      ', '.join(f"«{s['name']}»" for s in kafka_steps),
                      'Без partition key события одной сущности могут разойтись по разным партициям '
                      'и быть обработаны в неправильном порядке.',
                      'Партиционируйте события по entityId и явно укажите этот ключ во входных данных шага.')]
    if meta['ordering'] == 'global':
        return [F('high', 'Заявлен глобальный строгий порядок событий.',
                  'Весь процесс',
                  'Глобальный порядок резко ограничивает параллелизм и масштабирование; почти всегда '
                  'достаточно порядка в рамках одной бизнес-сущности.',
                  'Пересмотрите требование до per-entity ordering; если это невозможно, используйте одну партицию или однопоточного '
                  'писателя и явно зафиксируйте потолок пропускной способности.')]
    return []


@rule('multiple_writers', 'Целостность данных')
def r_multi_writers(model):
    writers = model['graph']['writers']
    if len(writers) >= 2 and model['meta']['money'] != 'direct':  # для денег своё критичное правило
        return [F('high', 'Основную сущность изменяют несколько систем.',
                  ', '.join(writers),
                  'Без единого владельца записи появятся конфликты версий, потерянные обновления и спорные состояния.',
                  'Назначьте систему-владельца; остальные системы должны отправлять команды или события через её API.')]
    return []


@rule('fanout_sync', 'Архитектура')
def r_fanout(model):
    out = []
    for s in model['steps']:
        kids = [model['graph']['by_order'][k] for k in s['children']]
        sync_kids = [k for k in kids if k['sync'] and k['blocking']]
        if len(sync_kids) >= 3:
            out.append(F('medium', 'Источник синхронно вызывает несколько потребителей.',
                         f"Шаг {s['order']} «{s['name']}» → {len(sync_kids)} вызовов",
                         'Один источник синхронно оповещает многих потребителей: добавление нового потребителя '
                         'требует доработки источника, а отказ любого потребителя замедляет весь сценарий.',
                         'Публикуйте одно событие через Outbox, а потребители пусть подписываются на него самостоятельно.'))
    return out


@rule('unstable_dependency', 'Надёжность')
def r_unstable(model):
    out = []
    for s in model['steps']:
        st = model['systems'][s['system']]['stability']
        if st == 'unstable' and s['blocking']:
            out.append(F('high', 'Процесс блокируется на нестабильной системе.',
                         f"Шаг {s['order']} «{s['name']}» → {s['system']}",
                         'Система заявлена как нестабильная, поэтому её таймауты и деградация станут вашими проблемами.',
                         'Добавьте circuit breaker, bulkhead с отдельным пулом и сценарий деградации: можно показать '
                         'последний известный результат или поставить задачу в очередь.'))
        if st == 'limited':
            out.append(F('medium', 'У зависимости есть rate limit.',
                         f"Шаг {s['order']} «{s['name']}» → {s['system']}",
                         'Лимиты провайдера могут превратить пик нагрузки в шторм ошибок 429.',
                         'Добавьте клиентский rate limiter, очередь выравнивания и backoff с jitter.'))
    return out


@rule('stream_consumer_controls', 'Потоковая обработка')
def r_stream_consumer(model):
    meta = model['meta']
    out = []
    for s in model['steps']:
        if s['channel'] in BROKER_CHANNELS and _is_consumption(model, s):
            selective = bool(re.search(r'фильтр|filter|селектив|общ', _low(s['data_in'])))
            heavy = meta['peak_rps'] >= 1000
            if selective or heavy:
                extra = (' Потребляется доля общего потока — фильтрация на consumer '
                         'требует мощности на весь входящий трафик.' if selective else '')
                out.append(F('medium', 'Для потокового потребителя не описаны обязательные контроли.',
                             f"Шаг {s['order']} «{s['name']}»",
                             'Высоконагруженное чтение из брокера без явных контролей опасно: '
                             'lag может расти незаметно, а перегрузка будет ронять потребителя.' + extra,
                             'Добавьте метрику consumer lag и алерт; настройте backpressure или ограничение '
                             'параллелизма; sink должен быть идемпотентным; offset нужно коммитить только после обработки; '
                             'если читается общий topic, добавьте filter ratio как отдельную метрику.'))
    return out


@rule('stream_ingestion', 'Потоковая обработка')
def r_stream_ingestion(model):
    meta = model['meta']
    kafka_async = [s for s in model['steps'] if s['channel'] in BROKER_CHANNELS and not s['blocking']]
    if meta['peak_rps'] >= 5000 and kafka_async:
        return [F('high', 'Высоконагруженный поток не имеет контролей ingestion.',
                  f"Пик {meta['peak_rps']} RPS: " +
                  ', '.join(f"«{s['name']}»" for s in kafka_async[:3]),
                  'На таком потоке неизбежны out-of-order события, опоздавшие события, '
                  'горячие партиции и всплески нагрузки, которые потребитель может не обработать вовремя.',
                  'Используйте партиционирование по ключу и контроль горячих партиций; учитывайте event-time '
                  'и watermark с политикой late events; настройте backpressure и алертинг на лаг '
                  'и пропускную способность.')]
    return []


@rule('multi_tenant_fairness', 'Архитектура')
def r_multi_tenant(model):
    meta = model['meta']
    has_queue = any(s['channel'] in BROKER_CHANNELS for s in model['steps'])
    if meta['multi_tenant'] and has_queue:
        return [F('high', 'В multi-tenant потоке не предусмотрена изоляция нагрузки.',
                  'Общая очередь/topic',
                  'Один крупный tenant может занять общий пул потребителей и создать lag '
                  'для всех остальных клиентов, то есть возникнет эффект noisy neighbor.',
                  'Добавьте tenant-квоты и fair scheduling; партиционируйте данные по tenantId; '
                  'для крупных tenant выделите отдельные пулы и отслеживайте lag per tenant.')]
    return []


@rule('sensitive_data_policy', 'Комплаенс')
def r_sensitive_data(model):
    meta = model['meta']
    if not any(f['sensitive'] for f in meta['fields']):
        return []
    blob = _low(meta['goal']) + ' ' + ' '.join(
        _low(s['name']) + ' ' + _low(s['data_out']) for s in model['steps'])
    has_policy = bool(re.search(r'retention|хранени|удален|маскир|анонимиз|erasure', blob))
    if has_policy:
        return []
    fields = ', '.join(f['name'] for f in meta['fields'] if f['sensitive'])
    return [F('medium', 'Для чувствительных данных не описана политика жизненного цикла.',
              f'Поля: {fields}',
              'ПДн и чувствительные поля могут разойтись по логам, событиям и копиям данных; '
              'без политики хранения и удаления это создаёт юридический и операционный риск.',
              'Опишите retention-политику и процедуру удаления по запросу; включите маскирование '
              'в логах и событиях; ограничьте доступ; не включайте такие поля в payload '
              'событий без явной необходимости.')]


@rule('cdc_projection_controls', 'Целостность данных')
def r_cdc_projection(model):
    out = []
    for s in model['steps']:
        if s['channel'] == 'cdc':
            out.append(F('medium', 'Для CDC-потока не описаны обязательные контроли.',
                         f"Шаг {s['order']} «{s['name']}» ({s['system']})",
                         'CDC может незаметно сломаться на пропусках позиций, удалениях '
                         'и эволюции схемы источника, из-за чего проекция тихо расходится с источником истины.',
                         'Используйте LSN или watermark с контролем пропусков (gap detection); добавьте обработку '
                         'delete-событий, политику эволюции схемы, идемпотентную проекцию, '
                         'регулярную reconciliation-сверку и replay за период.'))
    return out


@rule('migration_cutover', 'Архитектура')
def r_migration(model):
    if not model['meta']['replacing_legacy']:
        return []
    return [F('high', 'Замена legacy-системы описана без плана переключения.',
              'Весь процесс',
              'Миграция — это не просто «включили новое»: без parallel run и плана отката '
              'первый серьёзный дефект нового контура может остановить бизнес.',
              'Используйте strangler-подход: parallel run со сверкой старого и нового контура, поэтапное '
              'переключение трафика по процентам или сегментам, критерии cutover и '
              'план отката с сохранением данных, накопленных в новом контуре.')]


@rule('capacity_vs_limit', 'Производительность')
def r_capacity(model):
    meta = model['meta']
    out = []
    if not meta['peak_rps']:
        return out
    hit = set()
    for s in model['steps']:
        sysd = model['systems'][s['system']]
        limit = sysd['rate_limit_rps']
        if limit and meta['peak_rps'] > limit and s['system'] not in hit:
            hit.add(s['system'])
            out.append(F('critical', 'Пиковая нагрузка превышает rate limit зависимости',
                         f"{s['system']}: пик {meta['peak_rps']} RPS > лимит {limit} RPS",
                         'В пик каждый запрос сверх лимита получит 429/отказ — '
                         'это шторм ошибок ровно в момент максимума бизнеса.',
                         'Очередь выравнивания нагрузки перед зависимостью; клиентский '
                         'rate limiter; backoff с jitter; договориться о повышении лимита '
                         'или деградация (кэш/отложенная проверка).'))
    return out


@rule('status_model', 'Наблюдаемость')
def r_status_model(model):
    meta = model['meta']
    long_async = len(model['steps']) >= 4 and model['graph']['async_steps']
    if long_async and not meta['statuses']:
        return [F('medium', 'Длинный асинхронный процесс без статусной модели',
                  'Весь процесс',
                  'Ни клиент, ни поддержка не смогут ответить «где сейчас заявка» — '
                  'каждая задержка превратится в инцидент.',
                  'Явная статусная модель + GET /status по trackingId; финальные статусы зафиксировать.')]
    return []


@rule('spof', 'Архитектура')
def r_spof(model):
    counts = {}
    for s in model['graph']['critical_path']:
        counts[s['system']] = counts.get(s['system'], 0) + 1
    out = []
    for sysname, n in counts.items():
        crit = model['systems'][sysname]['criticality'] in ('high', 'critical', 'mission')
        if n >= 2 and crit:
            out.append(F('info', 'Концентрация критического пути в одной системе',
                         f'{sysname}: {n} блокирующих шага',
                         'Система — единая точка отказа сценария.',
                         'Проверить её HA/DR-план; рассмотреть деградацию сценария при её отказе.'))
    return out


@rule('timeout_inversion', 'Надёжность')
def r_timeout_inversion(model):
    """Дочерний таймаут >= родительского: родитель сдастся раньше ответа ребёнка."""
    out, byo = [], model['graph']['by_order']
    for s in model['steps']:
        if not (s['blocking'] and s['sync'] and s['timeout_ms']):
            continue
        for d in s['deps']:
            p = byo.get(d)
            if (p and p['blocking'] and p['sync'] and p['timeout_ms']
                    and s['timeout_ms'] >= p['timeout_ms']):
                sev = 'high' if s['writes_entity'] else 'medium'
                out.append(F(sev, 'Дочерний вызов может ждать дольше, чем родительский шаг.',
                             f"{p['order']} «{p['name']}» ({p['timeout_ms']}мс) → "
                             f"{s['order']} «{s['name']}» ({s['timeout_ms']}мс)",
                             'Родительский шаг завершится по таймауту раньше, чем ответит дочерний вызов; '
                             'в результате выполненная работа будет потрачена впустую' +
                             (', а запись может «осиротеть»: она есть в БД дочерней системы, но родитель уже считает операцию отказавшей.'
                              if s['writes_entity'] else '.'),
                             'Таймауты должны строго убывать вниз по цепочке: дочерний timeout должен быть меньше родительского с учётом '
                             'сетевых накладных; общий бюджет времени распределяйте от SLA сверху вниз.'))
                break
    return out


@rule('retry_amplification', 'Надёжность')
def r_retry_amplification(model):
    """Несколько авто-retry подряд в синхронной цепочке перемножают попытки."""
    risky = []
    for s in model['graph']['critical_path']:
        blob = _low(s['data_in']) + ' ' + _low(s['data_out']) + ' ' + _low(s['compensation'])
        breaker = bool(re.search(r'breaker|circuit|предохранит|разрыв.*цеп', blob))
        if s['sync'] and s['blocking'] and s['retry'] == 'auto' and not breaker:
            risky.append(s)
    if len(risky) >= 2:
        return [F('high', 'Повторы в синхронной цепочке усиливают друг друга.',
                  ' → '.join(f"«{s['name']}»" for s in risky),
                  'Несколько звеньев с auto-retry друг за другом перемножают количество попыток (N×M×…): '
                  'при деградации это создаёт retry-шторм и thundering herd в самый плохой момент.',
                  'Задайте единый бюджет повторов на весь запрос (global deadline), circuit breaker на каждом '
                  'звене и экспоненциальный backoff с jitter; не повторяйте вызовы, которые уже не успеют уложиться в SLA.')]
    return []


@rule('read_your_writes', 'Целостность данных')
def r_read_your_writes(model):
    """Клиентский сценарий читает синхронно сразу после асинхронной записи."""
    if not model['meta']['customer_visible']:
        return []
    children = model['graph']['children']

    def has_blocking_desc(order, seen):
        if order in seen:
            return False
        seen.add(order)
        for c in children.get(order, []):
            if c['blocking'] or has_blocking_desc(c['order'], seen):
                return True
        return False

    out = []
    for s in model['steps']:
        if not s['sync'] and s['writes_entity'] and has_blocking_desc(s['order'], set()):
            out.append(F('medium', 'Клиент читает результат сразу после асинхронной записи.',
                         f"Шаг {s['order']} «{s['name']}» пишет асинхронно, далее синхронный шаг",
                         'В одном клиентском сценарии запись выполняется асинхронно, а чтение — синхронно: '
                         'клиент может не увидеть только что сделанное изменение из-за окна консистентности.',
                         'Либо подтверждайте запись синхронно до ответа, либо используйте optimistic UI и статус «в обработке»; '
                         'также можно читать из той же модели или реплики, куда была выполнена запись.'))
    return out


@rule('blocking_in_async_handler', 'Надёжность')
def r_blocking_in_async(model):
    """Обработчик очереди/вебхука синхронно блокируется на внешнем вызове."""
    out, byo = [], model['graph']['by_order']
    for s in model['steps']:
        handler = _is_consumption(model, s) or s['channel'] in ('webhook', 'callback')
        if not handler:
            continue
        for k in s['children']:
            c = byo[k]
            if c['blocking'] and c['sync'] and c['external']:
                out.append(F('medium', 'Асинхронный обработчик блокируется на внешнем вызове.',
                             f"{s['order']} «{s['name']}» → {c['order']} «{c['name']}» ({c['system']})",
                             'Потребитель очереди или webhook синхронно ждёт внешнюю систему: её задержка '
                             'накапливает consumer lag и съедает таймаут доставки, поэтому выигрыш от асинхронности теряется.',
                             'Вынесите внешний вызов в отдельный шаг или очередь; добавьте timeout и circuit breaker; '
                             'дообработка должна быть идемпотентной, чтобы повторная доставка не дублировала внешний вызов.'))
    return out


@rule('no_correlation_id', 'Наблюдаемость')
def r_correlation(model):
    """Распределённый асинхронный процесс без сквозного идентификатора."""
    steps, meta = model['steps'], model['meta']
    systems = {s['system'] for s in steps}
    if len(steps) < 3 or len(systems) < 2 or not model['graph']['async_steps']:
        return []
    blob = _low(meta['goal']) + ' ' + ' '.join(
        _low(s['name']) + ' ' + _low(s['data_in']) + ' ' + _low(s['data_out']) for s in steps)
    if re.search(r'correlat|корреляц|trace|трейс|traceparent|request[_-]?id|x-request|\bspan\b', blob):
        return []
    return [F('medium', 'Распределённый процесс не имеет сквозного correlationId.',
              'Весь процесс',
              'Запрос проходит через несколько систем и асинхронных шагов; без сквозного идентификатора '
              'инцидент невозможно собрать по логам разных систем, поэтому расследование будет идти вслепую.',
              'Пробрасывайте correlationId или traceId через все шаги и payload событий (W3C traceparent); '
              'логируйте его на каждом переходе и связывайте с trackingId бизнес-процесса.')]


@rule('unbounded_growth', 'Эксплуатация')
def r_unbounded_growth(model):
    """Outbox/Inbox/Ledger и журналы растут вечно без политики архивации."""
    steps, meta = model['steps'], model['meta']
    has_outbox = any(s['channel'] in BROKER_CHANNELS and not _is_consumption(model, s) for s in steps)
    has_inbox = any(s['channel'] in ('webhook', 'callback') for s in steps)
    has_ledger = meta['money'] == 'direct'
    if not (has_outbox or has_inbox or has_ledger):
        return []
    blob = _low(meta['goal']) + ' ' + ' '.join(
        _low(s['name']) + ' ' + _low(s['data_out']) + ' ' + _low(s['compensation']) for s in steps)
    if re.search(r'архив|archive|retention|очистк|cleanup|партиц|partition|\bttl\b|удален', blob):
        return []
    tables = ([t for t, on in (('outbox', has_outbox), ('inbox', has_inbox),
                               ('ledger', has_ledger)) if on])
    return [F('info', 'Для служебных таблиц не описана политика роста и очистки.',
              ', '.join(tables) + ' + журнал шагов',
              'Эти таблицы пополняются на каждое событие; без архивации и партиционирования '
              'они со временем ухудшат latency запросов и существенно раздуют БД.',
              'Добавьте партиционирование по времени, архивацию или перенос в холодное хранилище, а также очистку '
              'опубликованных outbox-записей; контролируйте размер таблиц и время запросов к ним.')]


@rule('fanin_partial_failure', 'Надёжность')
def r_fanin_partial(model):
    """Join, синхронно ждущий несколько ветвей (внешних/async), без политики
    частичного отказа: одна медленная/упавшая ветвь валит весь агрегат."""
    out, byo = [], model['graph']['by_order']
    for s in model['graph']['joins']:
        if not s['blocking']:
            continue
        branches = [byo[d] for d in s['deps'] if d in byo]
        risky = [b for b in branches if b['external'] or not b['sync']]
        blob = (_low(s['name']) + ' ' + _low(s['data_in']) + ' ' +
                _low(s['data_out']) + ' ' + _low(s['compensation']))
        policy = bool(re.search(r'partial|части|fallback|деград|best.?effort|optional|'
                                r'тайм.?аут.*ветв', blob))
        if risky and not policy:
            out.append(F('high', 'Агрегация ветвей выполняется без политики частичного отказа.',
                         f"Шаг {s['order']} «{s['name']}» ждёт {len(branches)} ветвей: "
                         + ', '.join(b['system'] for b in branches),
                         'Join синхронно ждёт несколько ветвей, среди которых есть внешние или асинхронные зависимости: '
                         'одна медленная или упавшая ветвь может заблокировать или уронить весь агрегат '
                         'поскольку латентность определяется самой медленной ветвью.',
                         'Задайте timeout на каждую ветвь и partial response: отдавайте собранные данные и помечайте '
                         'недостающие блоки; используйте деградацию вместо полного отказа и кэш последних значений ветвей.'))
    return out


@rule('contract_versioning', 'Целостность данных')
def r_contract_versioning(model):
    """Событие публикуется и потребляется разными системами без схемы/версии."""
    steps = model['steps']
    publishes = [s for s in steps if s['channel'] in BROKER_CHANNELS
                 and not _is_consumption(model, s)]
    consumes = [s for s in steps if s['channel'] in BROKER_CHANNELS
                and _is_consumption(model, s)]
    if not (publishes and consumes):
        return []
    blob = ' '.join(_low(s['name']) + ' ' + _low(s['data_in']) + ' ' + _low(s['data_out'])
                    for s in steps)
    if re.search(r'схем|schema|version|версион|avro|protobuf|registry|контракт|contract', blob):
        return []
    return [F('medium', 'Событийный контракт не имеет версии и зафиксированной схемы.',
              ', '.join(f"«{s['name']}»" for s in publishes[:3]),
              'События передаются между разными системами, но схема и версия не зафиксированы: '
              'любое изменение payload может незаметно сломать потребителей.',
              'Используйте Schema Registry (Avro, Protobuf или JSON Schema) с правилами совместимости; '
              'добавьте версионирование событий и контрактные тесты producer↔consumer.')]


@rule('hot_read_no_cache', 'Производительность')
def r_hot_read(model):
    """Горячее чтение синхронно бьёт в источник на критическом пути без кэша/проекции."""
    meta = model['meta']
    if meta['read_freq'] not in ('high', 'very_high'):
        return []
    if not (meta['customer_visible'] or 0 < meta['sla_ms'] <= 1000):
        return []
    for s in model['graph']['critical_path']:
        role = model['systems'][s['system']]['role']
        if (s['blocking'] and s['sync'] and not s['writes_entity']
                and (s['external'] or role in ('db', 'legacy'))):
            blob = _low(s['name']) + ' ' + _low(s['data_in']) + ' ' + _low(s['data_out'])
            if not re.search(r'кэш|cache|projection|проекци|read.?model|материализ|cdn', blob):
                return [F('medium', 'Горячее чтение идёт в источник без кэша или проекции.',
                          f"Шаг {s['order']} «{s['name']}» → {s['system']}",
                          'Частое чтение синхронно обращается к источнику на критическом пути: '
                          'его нагрузка и latency становятся вашими, а сам источник превращается в узкое место.',
                          'Добавьте кэш с TTL и инвалидацией или подготовленную проекцию (read-model/CQRS); '
                          'для статических данных используйте CDN, а в источник обращайтесь только при промахе кэша.')]
    return []




@rule('event_core_fields', 'Контракт')
def r_event_core_fields(model):
    """События между сервисами без обязательного конверта: eventId, occurredAt,
    eventType/version, correlationId и aggregateId. Это не заменяет schema registry,
    а ловит базовую пригодность события к эксплуатации."""
    steps = model['steps']
    publishes = [s for s in steps if s['channel'] in BROKER_CHANNELS
                 and not _is_consumption(model, s)]
    if not publishes:
        return []
    blob = ' '.join(_low(s['name']) + ' ' + _low(s['data_in']) + ' ' +
                    _low(s['data_out']) + ' ' + _low(s['compensation']) for s in steps)
    required = {
        'eventId': r'event.?id|идентификатор события|id события|event_id',
        'eventType': r'event.?type|тип события|event_type',
        'eventVersion': r'event.?version|верси[яи].*событ|schema.?version|event_version',
        'occurredAt': r'occurred.?at|created.?at|event.?time|время события|произош',
        'aggregateId': r'aggregate.?id|entity.?id|application.?id|order.?id|document.?id|operation.?id|id сущности',
    }
    missing = [name for name, rx in required.items() if not re.search(rx, blob)]
    if missing:
        return [F('medium', 'Событие не содержит обязательную event envelope.',
                  ', '.join(f'«{s["name"]}»' for s in publishes[:3]),
                  'Событие можно доставить, но его сложно дедуплицировать, трассировать, версионировать '
                  'и восстанавливать после инцидента: не хватает ' + ', '.join(missing) + '.',
                  'Зафиксируйте единый event envelope: eventId, eventType, eventVersion, '
                  'aggregateId или entityId, correlationId/traceId, occurredAt, producer и payload.')] 
    return []


@rule('async_reconciliation_missing', 'Целостность данных')
def r_async_reconciliation(model):
    """Для денег, регуляторики и длинных клиентских async-процессов нужна сверка,
    иначе DLQ/retry не гарантируют бизнесовую полноту результата."""
    meta = model['meta']
    if not model['graph']['async_steps']:
        return []
    important = meta['money'] == 'direct' or meta['regulatory'] or meta['customer_visible']
    if not important:
        return []
    blob = _model_blob(model)
    if re.search(r'reconciliation|recon|сверк|контроль полнот|балансиров|ежедневн.*свер', blob):
        return []
    sev = 'high' if meta['money'] == 'direct' or meta['regulatory'] else 'medium'
    return [F(sev, 'Важный асинхронный процесс не имеет reconciliation-сверки.',
              'Весь процесс',
              'Retry и DLQ закрывают технические сбои, но не доказывают, что все бизнес-сущности '
              'дошли до финального состояния и что банк, партнёр или витрина не разошлись по данным.',
              'Добавьте регулярную сверку источника истины с потребителями: expected vs actual, '
              'отчёт расхождений, автоматическое довосстановление там, где это безопасно, и ручной разбор.')] 


@rule('observability_missing', 'Наблюдаемость')
def r_observability_missing(model):
    """Распределённая интеграция без явных метрик/алертов — плохо эксплуатируется."""
    steps = model['steps']
    distributed = len({s['system'] for s in steps}) >= 2 and len(steps) >= 2
    risky_async = bool(model['graph']['async_steps'])
    external = bool(model['graph']['external_blocking'])
    if not (distributed and (risky_async or external)):
        return []
    blob = _model_blob(model)
    if re.search(r'метрик|metric|alert|алерт|монитор|dashboard|дашборд|lag|trace|трейс', blob):
        return []
    return [F('medium', 'Для интеграции не описана модель наблюдаемости.',
              'Весь процесс',
              'Даже корректная архитектура станет неуправляемой в production, если нельзя быстро увидеть, '
              'где застряла сущность, растёт ли lag, сколько сообщений находится в DLQ и какой внешний вызов деградирует.',
              'Добавьте технические и бизнес-метрики: latency по шагам, success/error rate, consumer lag, '
              'DLQ count, retry count, status aging, traces по correlationId и алерты по SLO.')] 


@rule('api_error_contract', 'Контракт')
def r_api_error_contract(model):
    """Клиентский синхронный REST/gRPC-flow без явной модели ошибок."""
    meta = model['meta']
    if not meta['customer_visible']:
        return []
    sync_api = [s for s in model['steps'] if s['blocking'] and s['sync']
                and s['channel'] in ('rest', 'grpc', 'soap')]
    if not sync_api:
        return []
    blob = _model_blob(model)
    if re.search(r'error.?code|код ошиб|problem\+json|ошибк|валидац|4xx|5xx|grpc status', blob):
        return []
    return [F('info', 'Для клиентского API не зафиксирована модель ошибок.',
              ', '.join(f'«{s["name"]}»' for s in sync_api[:3]),
              'Без контракта ошибок фронт, клиент и поддержка будут по-разному трактовать отказы, '
              'timeout, дубли и промежуточные состояния.',
              'Опишите errorCode, userMessage, technicalMessage для логов, retryable, '
              'correlationId, mapping 4xx/5xx/gRPC status и примеры ошибок.')] 


@rule('no_owner_for_critical_system', 'Эксплуатация')
def r_no_owner_for_critical_system(model):
    out = []
    for name, s in model['systems'].items():
        used = any(st['system'] == name for st in model['steps'])
        if not used:
            continue
        if s['criticality'] in ('high', 'critical', 'mission') and not _s(s.get('owner')):
            out.append(F('info', 'Для критичной системы не указан владелец.',
                         name,
                         'При инциденте будет непонятно, кто отвечает за SLA, контракт, лимиты, '
                         'replay и согласование изменений.',
                         'Зафиксируйте владельца системы или команды, канал поддержки, SLO и порядок эскалации.'))
    return out



# ---------------------------------------------------------------- semantic data-key rules
def _field_names(model):
    return {_low(f.get('name')): f for f in model['meta'].get('fields', [])}


def _has_field_like(model, pattern):
    return any(re.search(pattern, _low(f.get('name'))) for f in model['meta'].get('fields', []))


def _lookup_blob(model):
    meta = model['meta']
    return ' '.join([
        _low(meta.get('lookup_keys')), _low(meta.get('description')), _low(meta.get('constraints')),
        ' '.join(_low(s.get('data_in')) + ' ' + _low(s.get('data_out')) + ' ' + _low(s.get('name'))
                 for s in model.get('steps', [])),
    ])


@rule('ambiguous_composite_business_key', 'Данные и идемпотентность')
def r_ambiguous_composite_business_key(model):
    """Ловит класс ошибок: один технический/операционный идентификатор повторно
    используется в разных типах операций или направлениях, а поиск/unique key строится
    только по нему. Типичный пример: universal dispatcher/dokatчик отправляет запросы
    в систему А и систему Б с одним operUid; поиск только по operUid склеит разные записи."""
    fields = model['meta'].get('fields', [])
    blob = _model_blob(model) + ' ' + _lookup_blob(model)
    has_oper_uid = _has_field_like(model, r'oper.?u?id|operation.?u?id|операц.*id|опер.?юид|operuid|op_uid')
    has_type = _has_field_like(model, r'operation.?type|op.?type|тип.*операц|тип.*запрос|target.?system|destination|направлен') \
        or re.search(r'operation.?type|тип.*операц|систем[уы]\s*[abаб]|систем[аы]\s*а|систем[аы]\s*б|target.?system|destination', blob)
    if not has_oper_uid:
        return []

    lookup_mentions_oper = re.search(r'по\s+oper.?u?id|по\s+опер.?юид|lookup.*oper.?u?id|search.*oper.?u?id|find.*oper.?u?id|поиск.*oper.?u?id|поиск.*опер', _lookup_blob(model))
    lookup_mentions_type = re.search(r'operation.?type|op.?type|тип.*операц|тип.*запрос|target.?system|destination', _low(model['meta'].get('lookup_keys'))) \
        or re.search(r'\(\s*oper.?u?id\s*,\s*(operation.?type|op.?type|target.?system|destination)', _lookup_blob(model))
    oper_unique_alone = any(re.search(r'oper.?u?id|operation.?u?id|опер.?юид|operuid', _low(f.get('name'))) and f.get('unique') for f in fields)

    universal_context = re.search(r'универсальн|докатчик|dispatcher|router|роут|адаптер|шлюз|system\s*a|system\s*b|систем[аы]\s*а|систем[аы]\s*б', blob)
    multiple_targets = len({s['system'] for s in model['steps'] if model['systems'].get(s['system'], {}).get('role') in ('external','internal','legacy')}) >= 3

    risky = has_type and (lookup_mentions_oper or oper_unique_alone or universal_context or multiple_targets) and not lookup_mentions_type
    if not risky:
        return []
    return [F('high', 'Идентификатор операции используется без уточняющего типа операции.',
              'Поля и поиск по операции',
              'Один operUid или operationId может быть одинаковым для разных направлений, типов операций или целевых систем. '
              'Если искать, обновлять или дедуплицировать запись только по этому идентификатору, разные записи процесса могут склеиться: '
              'например запрос в систему А и запрос в систему Б будут считаться одной операцией.',
              'Зафиксируйте область уникальности ключа. Обычно нужен составной ключ и уникальный индекс: '
              '(operUid, operationType), а для универсального маршрутизатора часто ещё targetSystem/sourceSystem или processId. '
              'Все поиски, update, dedup, Inbox/Outbox и replay должны использовать тот же составной ключ, а не один operUid.')] 


@rule('missing_key_scope_for_shared_dispatcher', 'Данные и идемпотентность')
def r_missing_key_scope_for_shared_dispatcher(model):
    blob = _model_blob(model) + ' ' + _lookup_blob(model)
    looks_shared_dispatcher = re.search(r'универсальн|докатчик|dispatcher|router|адаптер|шлюз|общ[а-я]* сервис', blob)
    has_operation_id = re.search(r'oper.?u?id|operation.?id|request.?id|опер.?юид|идентификатор операции', blob)
    has_scope = re.search(r'operation.?type|op.?type|тип.*операц|target.?system|destination|source.?system|scope|област[ьи].*уникальн', blob)
    if looks_shared_dispatcher and has_operation_id and not has_scope:
        return [F('medium', 'Для универсального сервиса не описана область уникальности операционного идентификатора.',
                  'Описание процесса и ключи поиска',
                  'Универсальный сервис обычно обслуживает несколько направлений и типов операций. Один и тот же operationId может быть допустим '
                  'в разных подоперациях одного бизнес-процесса, поэтому без scope нельзя безопасно искать, обновлять и переигрывать записи.',
                  'Добавьте в модель данных явный scope: operationType, targetSystem, sourceSystem, tenantId или processId. '
                  'Опишите, какие поля входят в business key, idempotency key и ключ поиска для каждой операции.')] 
    return []



@rule('generic_identifier_scope_ambiguity', 'Данные и идемпотентность')
def r_generic_identifier_scope_ambiguity(model):
    """Обобщение кейса operUid: любой технический id опасен, если его область
    уникальности не определена, а сервис используется в нескольких направлениях,
    tenant'ах, типах операций или системах."""
    meta = model['meta']
    lookup = _low(meta.get('lookup_keys'))
    if not lookup:
        return []
    # Если пользователь уже явно указал scope в ключе, правило не шумит.
    scoped = re.search(r'operation.?type|op.?type|target.?system|source.?system|tenant.?id|process.?id|scope|тип|направлен|система|контур', lookup)
    if scoped:
        return []
    id_like = re.search(r'\b(request.?id|operation.?id|oper.?u?id|document.?id|message.?id|external.?id|provider.?id|заявк.*id|операц.*id|идентификатор)\b', lookup)
    if not id_like:
        return []
    blob = _model_blob(model)
    systems = {s['system'] for s in model['steps'] if model['systems'].get(s['system'], {}).get('role') in ('external', 'internal', 'legacy')}
    multi_scope_context = (
        meta.get('multi_tenant')
        or len(systems) >= 3
        or bool(re.search(r'универсальн|докатчик|dispatcher|router|адаптер|шлюз|нескольк.*систем|разн.*тип|разн.*направлен|tenant|мультитенант|system\s*a|system\s*b|систем[аы]\s*а|систем[аы]\s*б', blob))
    )
    if not multi_scope_context:
        return []
    return [F('medium', 'У идентификатора не зафиксирована область уникальности.',
              'Ключи поиска и обновления',
              'Один и тот же идентификатор может быть уникален только внутри конкретного типа операции, целевой системы, tenant, процесса или источника. '
              'Если использовать его как глобальный ключ, разные записи могут перезаписать друг друга, replay может восстановить не ту операцию, а дедупликация может ошибочно отфильтровать корректное событие.',
              'Для каждого идентификатора укажите scope уникальности. Проверьте, что SELECT, UPDATE, UPSERT, уникальные индексы, Inbox, Outbox и replay используют одинаковый составной ключ: например requestId + operationType + targetSystem + tenantId или processId.')] 



def _key_scope_analysis(model):
    """Единая проверка области уникальности ключей.

    Важно не считать ключ корректным только потому, что рядом в описании есть
    operationType/targetSystem. Проверяется именно lookup_keys: тот ключ,
    которым будут искать, обновлять, дедуплицировать и делать replay.
    """
    meta = model['meta']
    lookup = _low(meta.get('lookup_keys'))
    blob = _model_blob(model)
    fields_blob = ' '.join(_low(f.get('name')) for f in meta.get('fields', []))
    systems = {s['system'] for s in model['steps'] if model['systems'].get(s['system'], {}).get('role') in ('external', 'internal', 'legacy')}
    id_like = bool(re.search(r'\b(request.?id|operation.?id|oper.?u?id|document.?id|message.?id|external.?id|provider.?id|payment.?id|order.?id|заявк.*id|операц.*id|идентификатор)\b', lookup))
    lookup_has_scope = bool(re.search(r'operation.?type|op.?type|target.?system|source.?system|tenant.?id|provider.?code|process.?id|document.?type|scope|тип|направлен|система|контур|провайдер|tenant', lookup))
    scope_available = bool(re.search(r'operation.?type|op.?type|target.?system|source.?system|tenant.?id|provider.?code|process.?id|document.?type|тип.*операц|целев.*систем|источник|tenant|мультитенант', blob + ' ' + fields_blob))
    multi_scope_context = bool(
        meta.get('multi_tenant')
        or len(systems) >= 3
        or re.search(r'универсальн|докатчик|dispatcher|router|адаптер|шлюз|нескольк.*систем|разн.*тип|разн.*направлен|tenant|мультитенант|system\s*a|system\s*b|систем[аы]\s*а|систем[аы]\s*б|multi.?tenant|provider|провайдер', blob)
    )
    # Риск возникает, когда lookup есть и похож на одиночный технический id,
    # а контекст подсказывает, что scope нужен, но в самом lookup он отсутствует.
    needs_scope = bool(id_like and multi_scope_context and not lookup_has_scope)
    return {
        'lookup': lookup,
        'id_like': id_like,
        'lookup_has_scope': lookup_has_scope,
        'scope_available': scope_available,
        'multi_scope_context': multi_scope_context,
        'needs_scope': needs_scope,
    }

# ---------------------------------------------------------------- completeness / gates / alternatives
def _model_blob(model):
    meta = model['meta']
    return ' '.join([
        _low(meta.get('name')), _low(meta.get('entity')), _low(meta.get('goal')),
        _low(meta.get('description')), _low(meta.get('lookup_keys')), _low(meta.get('constraints')),
        ' '.join(_low(f.get('name')) for f in meta.get('fields', [])),
        ' '.join(_low(s.get('name')) + ' ' + _low(s.get('data_in')) + ' ' +
                 _low(s.get('data_out')) + ' ' + _low(s.get('compensation'))
                 for s in model.get('steps', [])),
    ])


def _has(model, pattern):
    return bool(re.search(pattern, _model_blob(model)))


def completeness_check(model):
    """Что ещё нужно уточнить, чтобы рекомендация была не гаданием.

    Это отдельный слой от рисков: отсутствие вводной не всегда ошибка архитектуры,
    но без неё нельзя уверенно проектировать production-решение."""
    meta, steps, g = model['meta'], model['steps'], model['graph']
    missing = []

    def add(priority, area, question, why, how='Уточнить и зафиксировать в карточке решения/ADR.'):
        missing.append({'priority': priority, 'area': area, 'question': question,
                        'why': why, 'how': how})

    async_steps = g['async_steps']
    kafka_or_queue = [s for s in steps if s['channel'] in BROKER_CHANNELS]
    external_steps = [s for s in steps if s['external']]
    writes = [s for s in steps if s['writes_entity']]
    distributed = len({s['system'] for s in steps}) >= 2

    if not meta['goal']:
        add('high', 'Бизнес', 'Какая бизнес-цель и что считается успешным финалом процесса?',
            'Без цели невозможно отличить обязательный шаг от необязательной дообработки.')
    if not meta['fields']:
        add('medium', 'Данные', 'Какие ключевые поля сущности, уникальные ключи и чувствительные данные?',
            'Без полей нельзя проверить идемпотентность, индексы, ПДн и контракт.')
    if writes and not any(f.get('unique') for f in meta['fields']):
        add('medium', 'Данные', 'Какой natural/business key или operationId уникально определяет операцию?',
            'Без уникального ключа сложно гарантировать dedup и повторную обработку без дублей.',
            'Добавить idempotencyKey/operationId/requestId с UNIQUE-индексом или natural key.')
    if _has_field_like(model, r'oper.?u?id|operation.?u?id|опер.?юид|operuid') and not meta.get('lookup_keys'):
        add('high', 'Ключи поиска', 'По каким полям система ищет, обновляет и дедуплицирует операцию?',
            'Операционный идентификатор может быть не глобально уникальным. Если не указать область уникальности, можно случайно склеить разные подоперации одного процесса.',
            'Зафиксируйте business key, idempotency key и lookup key. Для универсальных сервисов часто нужен составной ключ: operUid + operationType + targetSystem.')
    if _has_field_like(model, r'oper.?u?id|operation.?u?id|опер.?юид|operuid') and _has_field_like(model, r'operation.?type|op.?type|тип.*операц|target.?system|destination'):
        lk = _low(meta.get('lookup_keys'))
        if lk and re.search(r'oper.?u?id|опер.?юид|operuid', lk) and not re.search(r'operation.?type|op.?type|тип.*операц|target.?system|destination', lk):
            add('high', 'Ключи поиска', 'Почему поиск указан только по operUid, если есть разные типы операций или направления?',
                'В таком виде записи разных operationType могут пересекаться и обновляться как одна запись.',
                'Используйте составной lookup key: operUid + operationType; при маршрутизации в разные системы добавьте targetSystem/sourceSystem.')
    if async_steps and not meta['statuses']:
        add('high', 'Статусы', 'Какие статусы процесса и какие из них финальные?',
            'Асинхронная цепочка без статусов непрозрачна для поддержки и бизнеса.',
            'Задать статусы CREATED/ACCEPTED/PROCESSING/SUCCESS/REJECTED/FAILED/NEEDS_MANUAL_REVIEW или доменную модель.')
    if distributed and not _has(model, r'correlat|корреляц|trace|трейс|tracking|tracking.?id|traceparent'):
        add('high', 'Трассировка', 'Какой сквозной correlationId/trackingId проходит через все системы?',
            'Без него нельзя расследовать инциденты по распределённой цепочке.')
    if kafka_or_queue:
        if not _has(model, r'dlq|карантин|dead.?letter'):
            add('high', 'Надёжность', 'Куда попадает сообщение после исчерпания retry?',
                'Без DLQ/карантина poison message может потеряться или бесконечно крутиться.')
        if not _has(model, r'replay|переигр|повторн.*обработ|ручн.*запуск'):
            add('high', 'Восстановление', 'Как выполнить replay после исправления ошибки?',
                'DLQ сама по себе не восстанавливает бизнес-процесс.')
        if not _has(model, r'schema|схем|contract|контракт|version|верси|avro|protobuf|json schema'):
            add('high', 'Контракт', 'Где зафиксирована схема события и правила совместимости?',
                'Изменение payload может незаметно сломать потребителей.')
        if meta['ordering'] == 'no':
            add('medium', 'Порядок', 'Нужен ли порядок событий хотя бы в рамках одной сущности?',
                'Многие статусы/операции нельзя применять в произвольном порядке.')
        if not _has(model, r'retention|хранени|ttl|archive|архив|очистк|cleanup'):
            add('medium', 'Эксплуатация', 'Какой retention у топиков, outbox/inbox и журналов?',
                'Без политики хранения растёт стоимость и ухудшается восстановление/аудит.')
    if external_steps:
        if any(not model['systems'][s['system']].get('rate_limit_rps') for s in external_steps):
            add('medium', 'Внешние системы', 'Какие rate limits у внешних систем и что делать при 429/лимите?',
                'Без лимитов нельзя оценить пиковую нагрузку и backpressure.')
        if not _has(model, r'fallback|деград|circuit|breaker|bulkhead|кэш|cache'):
            add('medium', 'Отказоустойчивость', 'Какая деградация допустима при отказе внешней системы?',
                'Иначе отказ партнёра становится отказом вашего сценария.')
    if meta['sla_ms'] == 0 and any(s['blocking'] for s in steps):
        add('medium', 'SLA', 'Какой целевой SLA/таймаут для пользовательского или системного ответа?',
            'Без SLA невозможно распределить бюджет таймаутов и понять, где нужна async-граница.')
    if meta['load_rps'] == 0 and (kafka_or_queue or external_steps or len(steps) >= 4):
        add('medium', 'Нагрузка', 'Какая средняя и пиковая нагрузка, размер события и допустимый лаг?',
            'Без нагрузки нельзя выбрать партиционирование, пул потребителей, БД и лимиты.')
    if (meta['money'] == 'direct' or meta['regulatory']) and not _has(model, r'аудит|audit|evidence|журнал'):
        add('high', 'Комплаенс', 'Как фиксируется аудиторский след юридически значимых шагов?',
            'Для денег/регуляторики нужен доказуемый журнал переходов и решений.')
    if (meta['money'] == 'direct' or meta['regulatory'] or async_steps) and not _has(model, r'reconciliation|recon|сверк'):
        add('medium', 'Сверка', 'Как сверяются расхождения между источником истины и потребителями?',
            'Техническая доставка не гарантирует бизнесовую полноту и согласованность.')
    if not any(_s(s.get('owner')) for s in model['systems'].values()):
        add('info', 'Владение', 'Кто владельцы систем, контрактов и алертов?',
            'Без владельцев неясны ответственность и эскалация.')

    weights = {'high': 12, 'medium': 6, 'info': 2}
    lost = min(70, sum(weights.get(i['priority'], 0) for i in missing))
    score_pct = max(30, 100 - lost) if missing else 100
    confidence = 'высокая' if score_pct >= 85 else 'средняя' if score_pct >= 65 else 'низкая'
    return {'score_pct': score_pct, 'confidence': confidence, 'missing': missing,
            'summary': f'Полнота вводных: {score_pct}%. Надёжность рекомендаций: {confidence}.'}


def architecture_checklist(model, findings, patterns, completeness):
    fired = {f['rule'] for f in findings}
    pids = {p['id'] for p in patterns}
    meta, steps, g = model['meta'], model['steps'], model['graph']
    items = []

    def status(ok=None, fail_rule=None, warn_when=False, unknown_when=False):
        if fail_rule and fail_rule in fired:
            return 'fail'
        if ok is True:
            return 'ok'
        if warn_when:
            return 'warn'
        if unknown_when:
            return 'unknown'
        return 'ok' if ok else 'unknown'

    def add(area, title, st, check, evidence, fix, critical=False):
        items.append({'area': area, 'title': title, 'status': st, 'check': check,
                      'evidence': evidence, 'fix': fix, 'critical': critical})

    async_steps = g['async_steps']
    kafka_or_queue = [s for s in steps if s['channel'] in BROKER_CHANNELS]
    external = bool(g['external_blocking'])
    distributed = len({s['system'] for s in steps}) >= 2
    has_dlq = _has(model, r'dlq|карантин|dead.?letter')
    has_replay = _has(model, r'replay|переигр|повторн.*обработ|ручн.*запуск')
    has_schema = _has(model, r'schema|схем|contract|контракт|version|верси|avro|protobuf|json schema')
    has_corr = _has(model, r'correlat|корреляц|trace|трейс|tracking|traceparent')
    has_metrics = _has(model, r'метрик|metric|alert|алерт|монитор|dashboard|дашборд|lag|dlq')
    has_recon = _has(model, r'reconciliation|recon|сверк')
    has_audit = _has(model, r'аудит|audit|evidence|журнал')
    has_error_model = _has(model, r'error.?code|код ошиб|problem\+json|ошибк|валидац|4xx|5xx|grpc status')
    key_scope = _key_scope_analysis(model)
    key_scope_rules = {'ambiguous_composite_business_key', 'generic_identifier_scope_ambiguity', 'missing_key_scope_for_shared_dispatcher'}
    key_scope_status = 'fail' if (key_scope_rules & fired or key_scope['needs_scope']) else (
        'unknown' if not key_scope['lookup'] else ('warn' if key_scope['id_like'] and key_scope['multi_scope_context'] and not key_scope['scope_available'] else 'ok')
    )

    add('Контракт', 'Для каждого события или API зафиксирована единая схема и версия.',
        status(ok=not kafka_or_queue or has_schema, fail_rule='contract_versioning', unknown_when=bool(kafka_or_queue)),
        'Для каждого REST, API или event должен быть владелец, версия, правила совместимости и примеры payload.',
        'Событийные шаги есть.' if kafka_or_queue else 'Событийных контрактов нет.',
        'Используйте Schema Registry, JSON Schema, Avro или Protobuf и добавьте consumer-driven contract tests.', True)
    add('Контракт', 'Каждое событие содержит стандартную event envelope.',
        status(ok=not kafka_or_queue or 'event_core_fields' not in fired, fail_rule='event_core_fields', unknown_when=bool(kafka_or_queue)),
        'Событие должно позволять дедупликацию, трассировку, replay и безопасную эволюцию схемы.',
        'Kafka/queue используется.' if kafka_or_queue else 'Очередей нет.',
        'Стандартизируйте обязательную обёртку события: eventId, eventType, eventVersion, aggregateId, occurredAt и correlationId.', True)
    add('Контракт', 'Для клиентского API описана модель ошибок.',
        status(ok=not meta['customer_visible'] or has_error_model, fail_rule='api_error_contract', warn_when=meta['customer_visible']),
        'Фронт, клиент и поддержка должны одинаково понимать retryable и non-retryable ошибки, статусы и correlationId.',
        'Клиентский сценарий: да.' if meta['customer_visible'] else 'Не клиентский сценарий.',
        'Опишите errorCode, retryable, userMessage, technicalMessage и mapping HTTP/gRPC.', False)
    add('Данные', 'Ключ поиска и ключ идемпотентности имеют правильную область уникальности.',
        key_scope_status,
        'Если один технический идентификатор используется в разных типах операций, tenant, провайдерах или целевых системах, поиск, update, dedup и replay должны учитывать эту область уникальности.',
        'Ключ поиска: ' + (meta.get('lookup_keys') or 'не указан.') + (
            '; в контексте есть несколько областей уникальности.' if key_scope['multi_scope_context'] else '.'),
        'Опишите составной ключ и используйте его одинаково в SELECT, UPDATE, UPSERT, UNIQUE-индексе, Inbox, Outbox и replay. Примеры: requestId + operationType + targetSystem + tenantId; operUid + operationType + targetSystem; providerEventId + providerCode.', True)

    add('Надёжность', 'Для каждого блокирующего вызова задан timeout.',
        status(ok='missing_timeouts' not in fired, fail_rule='missing_timeouts'),
        'Ни один рабочий поток не должен ждать внешний или внутренний вызов бесконечно.',
        'Блокирующих шагов: ' + str(sum(1 for s in steps if s['blocking'])),
        'Задайте timeout на каждом шаге и общий deadline, рассчитанный от SLA.', True)
    add('Надёжность', 'Retry не создаёт дубли бизнес-операций.',
        status(ok='retry_without_idempotency' not in fired, fail_rule='retry_without_idempotency'),
        'Каждый retry, который может привести к записи, должен иметь idempotencyKey или natural key.',
        'Retry-шагов: ' + str(sum(1 for s in steps if s['retry'] != 'none')),
        'Используйте operationId или idempotencyKey с unique index; для входящих событий добавьте Inbox.', True)
    add('Надёжность', 'Для асинхронной обработки задан лимит попыток и DLQ или карантин.',
        status(ok=not async_steps or has_dlq, fail_rule='async_without_recovery', warn_when=bool(async_steps and not has_dlq)),
        'Poison message не должен теряться и не должен бесконечно возвращаться в обработку.',
        'Async-шагов: ' + str(len(async_steps)),
        'Настройте backoff, max attempts, DLQ, алерт и владельца ручного разбора.', True)
    add('Надёжность', 'После исправления ошибки есть понятная replay-процедура.',
        'ok' if not async_steps or has_replay else 'unknown',
        'Команда должна понимать, как безопасно переиграть DLQ, период или конкретную сущность.',
        'Replay упомянут.' if has_replay else 'Replay не указан.',
        'Опишите ручной и пакетный replay, требования к идемпотентности и права доступа на запуск.', True)
    add('Надёжность', 'Для внешних блокирующих вызовов описаны circuit breaker и деградация.',
        status(ok=not external or 'circuit_breaker' in pids or _has(model, r'circuit|breaker|fallback|деград'),
               fail_rule='external_blocking', warn_when=external),
        'Отказ партнёра не должен бесконтрольно приводить к отказу всего сценария.',
        'Есть внешние блокирующие вызовы.' if external else 'Внешних блокирующих вызовов нет.',
        'Добавьте timeout, circuit breaker, fallback, bulkhead и очередь выравнивания нагрузки.', True)

    add('Целостность', 'При записи в БД и публикации события используется Outbox.',
        status(ok='dual_write' not in fired, fail_rule='dual_write'),
        'Событие не должно теряться и не должно появляться без соответствующей записи в БД.',
        'Паттерн outbox рекомендован.' if 'outbox' in pids else 'Явного dual write может не быть.',
        'Записывайте Transactional Outbox в одной транзакции с изменением агрегата.', True)
    add('Целостность', 'Для входящих событий и webhook используется Inbox или дедупликация.',
        status(ok='callback_inbox' not in fired and 'retry_without_idempotency' not in fired,
               fail_rule='callback_inbox', warn_when=bool(async_steps)),
        'Повторная доставка не должна менять состояние второй раз.',
        'At-least-once каналы есть.' if async_steps else 'At-least-once каналов нет.',
        'Используйте Inbox table с уникальным eventId и коммитьте offset только после успешной обработки.', True)
    add('Целостность', 'У основной сущности есть владелец и единственный писатель.',
        status(ok=len(g['writers']) <= 1, fail_rule='multiple_writers', warn_when=len(g['writers']) == 0),
        'Должно быть понятно, какая система имеет право менять состояние основной сущности.',
        'Писатели: ' + (', '.join(g['writers']) if g['writers'] else 'не указаны'),
        'Назначьте system of record; остальные системы должны отправлять команды или события.', True)
    add('Целостность', 'Требование к порядку событий и ключу партиционирования явно зафиксировано.',
        status(ok='ordering' not in fired, fail_rule='ordering', unknown_when=bool(kafka_or_queue and meta['ordering'] == 'no')),
        'Если порядок важен, события одной сущности должны попадать в одну партицию.',
        f'Требование к порядку: {meta["ordering"]}.',
        'Уточните требование к порядку; для per-entity ordering используйте partition key = entityId.', False)
    add('Целостность', 'Для процесса предусмотрена reconciliation-сверка.',
        status(ok=has_recon or not (meta['money'] == 'direct' or meta['regulatory'] or async_steps),
               fail_rule='async_reconciliation_missing', warn_when=bool(async_steps)),
        'Должен быть способ доказать полноту обработки и восстановить найденные расхождения.',
        'Сверка упомянута.' if has_recon else 'Сверка не указана.',
        'Реализуйте expected/actual сверку, отчёт расхождений, безопасное авто-восстановление и ручной разбор.', True)

    add('Наблюдаемость', 'CorrelationId или traceId проходит через всю цепочку.',
        status(ok=has_corr or not distributed, fail_rule='no_correlation_id', warn_when=distributed),
        'Инцидент должен собираться по логам всех систем без ручного угадывания связей.',
        'Распределённых систем: ' + str(len({s['system'] for s in steps})),
        'Передавайте W3C traceparent или correlationId в запросах, событиях и логах.', True)
    add('Наблюдаемость', 'Для процесса настроены метрики, алерты и дашборды.',
        status(ok=has_metrics, fail_rule='observability_missing', warn_when=distributed or async_steps or external),
        'Для процесса должны быть SLO и метрики latency, error rate, lag, DLQ и status aging.',
        'Метрики упомянуты.' if has_metrics else 'Метрики не указаны.',
        'Добавьте бизнесовые и технические метрики, алерты и владельцев реакции.', True)
    add('Наблюдаемость', 'Для процесса описана статусная модель и история переходов.',
        status(ok=bool(meta['statuses']), fail_rule='status_model', warn_when=bool(async_steps)),
        'Поддержка должна видеть, где застряла сущность и почему это произошло.',
        'Статусы: ' + (', '.join(meta['statuses']) if meta['statuses'] else 'не заданы'),
        'Опишите статусы, status_history или step_log, а также финальные и промежуточные состояния.', False)

    add('Безопасность', 'Webhook или callback проходит проверку подписи.',
        status(ok='inbound_security' not in fired, fail_rule='inbound_security'),
        'Внешний вход нельзя подделать простым POST-запросом.',
        'Webhook/callback есть.' if any(s['channel'] in ('webhook','callback') for s in steps) else 'Webhook/callback нет.',
        'Используйте HMAC, JWT или mTLS, replay-window и ротацию секретов.', True)
    add('Безопасность', 'Для ПДн и чувствительных полей описаны маскирование и retention.',
        status(ok='sensitive_data_policy' not in fired, fail_rule='sensitive_data_policy'),
        'ПДн не должны попадать в логи, события и DWH без явной политики.',
        'Sensitive fields: ' + ', '.join(f['name'] for f in meta['fields'] if f.get('sensitive')),
        'Минимизируйте payload, маскируйте логи, настройте TTL или удаление и роли доступа.', True)

    add('Производительность', 'Заявленный SLA сходится с критическим путём.',
        status(ok='sla_budget' not in fired, fail_rule='sla_budget', unknown_when=meta['sla_ms'] == 0),
        'Сумма таймаутов и ожидаемая latency не должны превышать обещанный SLA.',
        f'Бюджет: {g["critical_budget_ms"]} мс, SLA: {meta["sla_ms"] or "не задан"}.',
        'Разорвите цепочку, распараллельте независимые шаги, добавьте кэш или уменьшите timeout.', True)
    add('Производительность', 'Для нагрузки описаны capacity, backpressure и consumer lag.',
        status(ok='capacity_vs_limit' not in fired and 'stream_ingestion' not in fired,
               fail_rule='capacity_vs_limit', warn_when=bool(kafka_or_queue or meta['peak_rps'])),
        'Пиковая нагрузка не должна ронять партнёра, брокер, consumer или БД.',
        f'Пик RPS: {meta["peak_rps"]}.',
        'Проведите нагрузочный тест, задайте лимиты, backpressure, партиции и алерты на consumer lag.', True)

    add('Эксплуатация', 'Для служебных таблиц и топиков задан retention и архивирование.',
        status(ok='unbounded_growth' not in fired, fail_rule='unbounded_growth', warn_when=bool(kafka_or_queue)),
        'Outbox, Inbox, ledger и логи не должны расти бесконечно.',
        'Есть служебные таблицы/топики.' if kafka_or_queue or meta['money'] == 'direct' else 'Служебный поток минимален.',
        'Добавьте партиционирование, TTL, архив, cleanup job и мониторинг размера.', False)
    add('Внедрение', 'Для внедрения описаны cutover, rollback и feature flag.',
        status(ok='migration_cutover' not in fired, fail_rule='migration_cutover', unknown_when=meta['replacing_legacy']),
        'У команды должен быть безопасный план включения и отката.',
        'Замена legacy: да.' if meta['replacing_legacy'] else 'Не миграционный сценарий.',
        'Опишите parallel run, сверку, поэтапное включение и критерии отката.', False)

    counters = {k: sum(1 for i in items if i['status'] == k) for k in ('fail','warn','unknown','ok')}
    return {'items': items, 'counters': counters}


def quality_gates(model, findings, checklist, completeness):
    areas = {
        'Контракт': ['Контракт'],
        'Надёжность': ['Надёжность'],
        'Целостность данных': ['Целостность'],
        'Наблюдаемость': ['Наблюдаемость'],
        'Безопасность': ['Безопасность'],
        'Производительность': ['Производительность'],
        'Эксплуатация и внедрение': ['Эксплуатация', 'Внедрение'],
    }
    gates = []
    for gate, area_names in areas.items():
        items = [i for i in checklist['items'] if i['area'] in area_names]
        fail = [i for i in items if i['status'] == 'fail' and i['critical']]
        warn = [i for i in items if i['status'] in ('warn','unknown')]
        if fail:
            st = 'fail'
            verdict = 'не проходит'
        elif warn:
            st = 'warn'
            verdict = 'условно'
        else:
            st = 'pass'
            verdict = 'проходит'
        gates.append({'name': gate, 'status': st, 'verdict': verdict,
                      'fail': [i['title'] for i in fail],
                      'warn': [i['title'] for i in warn[:5]],
                      'summary': f'{gate}: {verdict}'})

    overall = 'fail' if any(g['status'] == 'fail' for g in gates) else \
              'warn' if any(g['status'] == 'warn' for g in gates) else 'pass'
    return {'overall': overall, 'gates': gates,
            'readiness': 'production-ready' if overall == 'pass' else
                         'нужны доработки перед production' if overall == 'warn' else
                         'нельзя выпускать без закрытия блокеров'}


def architecture_alternatives(model, findings, patterns, gates):
    meta = model['meta']
    fired = {f['rule'] for f in findings}
    pids = {p['id'] for p in patterns}
    async_flow = bool(model['graph']['async_steps'])
    kafka = any(s['channel'] in ('kafka','queue') for s in model['steps'])
    external = bool(model['graph']['external_blocking'])
    important = meta['money'] == 'direct' or meta['regulatory']

    def base_controls(level):
        controls = []
        if kafka or async_flow:
            controls += ['Добавьте eventId и сделайте consumer идемпотентным.', 'Настройте DLQ с алертом и владельцем разбора.', 'Опишите ручной replay после исправления ошибки.',
                         'Зафиксируйте контракт события с версией и правилами совместимости.']
        if 'outbox' in pids or 'dual_write' in fired:
            controls.append('Добавьте Transactional Outbox на стороне producer.')
        if external:
            controls += ['Настройте timeout и circuit breaker для внешней системы.', 'Опишите fallback или деградацию при отказе внешней системы.']
        if meta['customer_visible'] and async_flow:
            controls += ['Возвращайте trackingId и предоставьте GET /status для проверки прогресса.', 'Сохраняйте историю статусов процесса.']
        if important:
            controls += ['Ведите append-only audit/evidence для юридически значимых шагов.', 'Настройте регулярную reconciliation-сверку.']
        if level in ('balanced', 'target'):
            controls += ['Добавьте метрики latency, error rate, lag, DLQ и status aging.', 'Добавьте contract tests между producer и consumer.',
                         'Проведите нагрузочный тест на пиковом профиле.']
        if level == 'target':
            controls += ['Внедрите schema registry с compatibility rules.', 'Автоматизируйте replay по периоду или конкретной сущности.',
                         'Подготовьте SLO-дашборд и runbook инцидентов.', 'Добавьте chaos/failure-тесты для критичных зависимостей.']
        # stable order and dedup
        out = []
        for c in controls:
            if c not in out:
                out.append(c)
        return out

    high_titles = [f['title'] for f in group_findings(findings)
                   if f['severity'] in ('critical','high')][:6]
    return [
        {'id': 'minimal', 'name': 'Вариант A — минимально допустимый фикс',
         'when': 'срок короткий и нельзя сильно менять архитектуру.',
         'cost': 'низкая', 'reliability': 'средняя', 'risk': 'средний или высокий, если оставить блокеры',
         'changes': base_controls('minimal') or ['Зафиксируйте контракт и добавьте тесты happy path и negative path.'],
         'must_close': high_titles,
         'not_enough': 'Не считать целевым решением: это набор страховок, чтобы не выпускать опасный поток.'},
        {'id': 'balanced', 'name': 'Вариант B — production-компромисс',
         'when': 'нужен рабочий production-вариант для типовой корпоративной интеграции.',
         'cost': 'средняя', 'reliability': 'высокая', 'risk': 'низкий, если закрыты quality gates',
         'changes': base_controls('balanced'),
         'must_close': high_titles,
         'not_enough': 'Можно выпускать после прохождения quality gates и регрессионных тестов.'},
        {'id': 'target', 'name': 'Вариант C — целевая архитектура',
         'when': 'поток критичен, регуляторен, денежный или станет платформенным.',
         'cost': 'высокая', 'reliability': 'очень высокая', 'risk': 'низкий, но выше стоимость сопровождения',
         'changes': base_controls('target'),
         'must_close': high_titles,
         'not_enough': 'Требует дисциплины эксплуатации: владельцы, runbook, SLO и регулярные сверки.'},
    ]


def project_artifacts(model, findings, patterns, gates):
    meta = model['meta']
    high = [f for f in findings if f['severity'] in ('critical', 'high')]
    dor = ['Бизнес-цель и финальные статусы согласованы.',
           'Источник истины и владелец основной сущности определены.',
           'Контракты API и events описаны с примерами и версиями.',
           'SLA, нагрузка, пиковый профиль и rate limits зафиксированы.',
           'Ошибочные сценарии и ручное восстановление согласованы.']
    dod = ['Все critical и high находки закрыты или приняты в ADR как осознанный риск.',
           'Идемпотентность и обработка дублей покрыты автотестами.',
           'DLQ, replay и runbook проверены на тестовом контуре.',
           'Метрики, алерты и correlationId видны в логах/трейсах.',
           'Контрактные тесты producer↔consumer проходят в CI.',
           'Нагрузочный тест подтверждает SLA и допустимый lag.']
    if meta['regulatory'] or meta['money'] == 'direct':
        dod += ['Аудиторский журнал append-only проверен.', 'Reconciliation-сверка даёт отчёт расхождений.']
    monitoring = ['Измеряйте latency p50, p95 и p99 по каждому блокирующему шагу.',
                  'Измеряйте error rate и timeout rate по внешним вызовам.',
                  'Отслеживайте consumer lag и queue depth.', 'Отслеживайте DLQ count и возраст самого старого сообщения.',
                  'Отслеживайте retry count и retry exhaustion.', 'Отслеживайте status aging: сколько сущностей зависло в промежуточном статусе.',
                  'Отслеживайте outbox unpublished count и возраст самой старой неопубликованной записи.', 'Отслеживайте reconciliation mismatches.']
    event_contract = {
        'eventId': 'UUID, уникальный идентификатор события',
        'eventType': 'доменный тип события',
        'eventVersion': 'версия схемы',
        'aggregateId': f'идентификатор сущности {meta["entity"]}',
        'correlationId': 'сквозная трассировка процесса',
        'occurredAt': 'момент бизнес-события',
        'producer': 'система-источник',
        'payload': 'только необходимые доменные поля без лишних ПДн',
    }
    high_groups = [f for f in group_findings(findings) if f['severity'] in ('critical', 'high')]
    return {'definition_of_ready': dor, 'definition_of_done': dod,
            'monitoring': monitoring, 'event_contract_skeleton': event_contract,
            'adr_minimum': [f'Закрыть риск или явно принять его в ADR: {f["title"]}' for f in high_groups]}


def run_rules(model):
    findings = []
    for r in RULES:
        for f in r['fn'](model):
            f['rule'] = r['id']
            f['category'] = r['category']
            findings.append(f)
    findings.sort(key=lambda f: SEVERITY_ORDER[f['severity']])
    return findings


def group_findings(findings, max_items_preview=12):
    """Группирует однотипные находки в один класс риска.

    Зачем это нужно: в сложных процессах одно правило может сработать на
    10-30 шагах. Если печатать каждую находку отдельно, отчёт становится
    нечитаемым, хотя архитектурная проблема одна и та же. Группировка
    сохраняет все затронутые места, но объяснение и рекомендация выводятся
    один раз.
    """
    buckets = {}
    order = []
    for f in findings:
        key = (f.get('severity'), f.get('rule'), f.get('category'),
               f.get('title'), f.get('why'), f.get('fix'))
        if key not in buckets:
            buckets[key] = {
                'severity': f.get('severity'),
                'rule': f.get('rule'),
                'category': f.get('category'),
                'title': f.get('title'),
                'why': f.get('why'),
                'fix': f.get('fix'),
                'items': [],
            }
            order.append(key)
        buckets[key]['items'].append({'where': f.get('where', ''),
                                      'title': f.get('title', ''),
                                      'severity': f.get('severity', '')})

    groups = []
    for key in order:
        g = buckets[key]
        count = len(g['items'])
        wheres = [i['where'] for i in g['items'] if i.get('where')]
        unique_wheres = []
        seen = set()
        for w in wheres:
            if w not in seen:
                seen.add(w)
                unique_wheres.append(w)
        g['count'] = count
        g['affected'] = unique_wheres
        if count == 1:
            g['where'] = unique_wheres[0] if unique_wheres else '—'
            g['where_summary'] = g['where']
        else:
            preview = '; '.join(unique_wheres[:max_items_preview])
            tail = '' if len(unique_wheres) <= max_items_preview else f'; ещё {len(unique_wheres) - max_items_preview}'
            g['where'] = f'Затронуто мест: {count}'
            g['where_summary'] = f'Затронуто мест: {count}. {preview}{tail}'
        groups.append(g)

    groups.sort(key=lambda g: (SEVERITY_ORDER.get(g['severity'], 99), g['rule'] or '', g['title'] or ''))
    return groups


# ---------------------------------------------------------------- patterns
def recommend_patterns(model, findings):
    """Рекомендуемые паттерны выводятся из структуры графа и находок."""
    fired = {f['rule'] for f in findings}
    meta, g = model['meta'], model['graph']
    pats = []

    def add(pid, name, why, controls):
        pats.append({'id': pid, 'name': name, 'why': why, 'controls': controls})

    if 'ambiguous_composite_business_key' in fired or 'missing_key_scope_for_shared_dispatcher' in fired:
        add('composite_business_key', 'Составной business key для операции',
            'Защищает универсальные сервисы от склейки разных подопераций по одному техническому идентификатору.',
            ['business key = operUid + operationType + targetSystem/sourceSystem при необходимости',
             'единый ключ в SELECT/UPDATE/UPSERT, Inbox, Outbox, replay и аудит-логе',
             'UNIQUE-индекс и регрессионный тест на одинаковый operUid для разных operationType'])
    if 'dual_write' in fired or any(s['channel'] in BROKER_CHANNELS for s in model['steps']):
        add('outbox', 'Transactional Outbox',
            'Гарантирует, что событие публикуется тогда и только тогда, когда зафиксирована запись в БД.',
            ['outbox-таблица в транзакции записи', 'publisher с retry и метрикой лага',
             'очистка/архив outbox'])
    if g['async_steps']:
        add('dlq_replay', 'Retry → DLQ → Replay',
            'Асинхронные шаги обязаны переживать сбои потребителя без потери сообщений.',
            ['retry с экспоненциальным backoff и лимитом попыток', 'DLQ/карантин с алертом',
             'персистентность брокера/очереди (переживает рестарт)',
             'процедура replay после починки'])
        add('idempotent_consumer', 'Идемпотентный потребитель',
            'At-least-once доставка означает дубли; потребитель обязан их гасить.',
            ['ключ дедупликации (eventId)', 'уникальный индекс/Inbox', 'commit offset после обработки'])
    if meta['customer_visible'] and g['async_steps']:
        add('tracking', 'TrackingId + статусная модель',
            'Клиент получает мгновенное подтверждение и наблюдаемый прогресс вместо ожидания всей цепочки.',
            ['trackingId в ответе приёма', 'GET /status', 'финальные статусы и таймаут процесса'])
    if g['external_blocking'] or 'unstable_dependency' in fired:
        add('circuit_breaker', 'Circuit Breaker + деградация',
            'Изолирует ваш сервис от деградации внешних зависимостей.',
            ['таймаут на вызов', 'breaker с half-open', 'fallback: stale-ответ или очередь'])
    if g['joins']:
        add('partial_response', 'Aggregator + partial response',
            'Сборка из нескольких ветвей должна переживать отказ или задержку отдельной ветви.',
            ['таймаут на каждую ветвь', 'partial response с пометкой недостающего',
             'деградация вместо полного отказа', 'кэш последних значений ветвей'])
    if meta['money'] == 'direct':
        add('ledger', 'Append-only Ledger + единый писатель',
            'Финансовое состояние — это журнал проводок, а не перезаписываемый баланс.',
            ['single writer per account', 'operationId-идемпотентность',
             'reconciliation-сверка', 'процедура ручной корректировки'])
    writing_systems = {s['system'] for s in model['steps'] if s['writes_entity']}
    if len(writing_systems) >= 2 or any(s['compensation'] for s in model['steps']):
        many = len([s for s in model['steps'] if s['blocking']]) >= 4
        add('saga', 'Saga (оркестрация)' if many else 'Saga (хореография)',
            'Распределённая операция требует управляемых компенсаций вместо распределённых транзакций.',
            ['компенсация на каждый пишущий шаг', 'политика retry → compensation → manual',
             'таймаут всего процесса'])
    if meta['read_freq'] == 'very_high' and len(model['systems']) >= 3:
        add('read_model', 'Read-model / API Composition',
            'Горячее чтение нельзя вешать на цепочку исходных систем — нужна подготовленная проекция.',
            ['проекция обновляется событиями', 'freshness/«данные на момент»',
             'partial response при отказе источника'])
    if any(model['systems'][s['system']]['role'] == 'analytics' or
           re.search(r'dwh|анали', _low(s['system'])) for s in model['steps']):
        add('cdc_etl', 'CDC/ETL в аналитический контур',
            'Аналитика питается изменениями данных, не участвуя в операционном пути.',
            ['CDC или инкрементальный экспорт', 'reconciliation-сверка полноты', 'replay за период'])
    return pats


# ---------------------------------------------------------------- scoring
def score(findings, finding_groups=None):
    """Оценка строится по классам рисков, а не по каждому повтору.

    Если однотипная ошибка повторилась в 20 шагах, это всё ещё серьёзно,
    но это один архитектурный класс проблемы с большим охватом, а не
    двадцать разных проблем. Поэтому базовый штраф идёт за группу, а
    дополнительные затронутые места дают ограниченный штраф.
    """
    groups = finding_groups or group_findings(findings)
    base_penalty = {'critical': 2.5, 'high': 1.2, 'medium': 0.5, 'info': 0.0}
    extra_step = {'critical': 0.18, 'high': 0.10, 'medium': 0.04, 'info': 0.0}
    extra_cap = {'critical': 0.9, 'high': 0.5, 'medium': 0.25, 'info': 0.0}
    total = 0.0
    for g in groups:
        sev = g['severity']
        total += base_penalty.get(sev, 0.0)
        total += min(extra_cap.get(sev, 0.0), max(0, g.get('count', 1) - 1) * extra_step.get(sev, 0.0))
    val = max(0.0, round(10.0 - total, 1))
    crit = sum(1 for f in findings if f['severity'] == 'critical')
    critical_groups = sum(1 for g in groups if g['severity'] == 'critical')
    if crit:
        verdict, color = 'НЕ ГОТОВО: есть блокирующие риски', 'red'
    elif val >= 8:
        verdict, color = 'ГОТОВО к проектированию с контролями', 'green'
    elif val >= 5:
        verdict, color = 'УСЛОВНО ГОТОВО: закрыть высокие риски', 'yellow'
    else:
        verdict, color = 'НЕ ГОТОВО: слишком много рисков', 'red'
    return {'score': val, 'verdict': verdict, 'color': color,
            'counts': {k: sum(1 for f in findings if f['severity'] == k)
                       for k in ('critical', 'high', 'medium', 'info')},
            'group_counts': {k: sum(1 for g in groups if g['severity'] == k)
                             for k in ('critical', 'high', 'medium', 'info')},
            'critical_groups': critical_groups}


# ---------------------------------------------------------------- db schema
def db_schema(model, patterns):
    meta = model['meta']
    pids = {p['id'] for p in patterns}
    entity = re.sub(r'\W+', '_', meta['entity']).strip('_').lower() or 'entity'
    tables = []

    cols = ['id uuid PRIMARY KEY DEFAULT gen_random_uuid()']
    indexes = []
    for f in meta['fields']:
        sql_type = {'uuid': 'uuid', 'int': 'integer', 'decimal': 'numeric(18,2)',
                    'bool': 'boolean', 'date': 'date', 'datetime': 'timestamptz',
                    'json': 'jsonb'}.get(f['type'], 'text')
        col = f"{f['name']} {sql_type}"
        if f['required']:
            col += ' NOT NULL'
        if f['unique']:
            col += ' UNIQUE'
        cols.append(col)
        if f['indexed']:
            indexes.append(f"CREATE INDEX idx_{entity}_{f['name']} ON {entity} ({f['name']});")
    field_names = {_low(f['name']): f['name'] for f in meta['fields']}
    oper_col = next((v for k, v in field_names.items() if re.search(r'oper.?u?id|operation.?u?id|опер.?юид|operuid', k)), None)
    type_col = next((v for k, v in field_names.items() if re.search(r'operation.?type|op.?type|тип.*операц|target.?system|destination', k)), None)
    lk = _low(meta.get('lookup_keys'))
    target_col = next((v for k, v in field_names.items() if re.search(r'target.?system|destination|целевая.*систем|получател', k)), None)
    if oper_col and type_col:
        key_cols = [oper_col, type_col]
        if target_col and re.search(r'target.?system|destination|систем[аы]\s*а|систем[аы]\s*б|универсальн|докатчик|dispatcher', _model_blob(model)):
            key_cols.append(target_col)
        indexes.append(f"CREATE UNIQUE INDEX ux_{entity}_operation_scope ON {entity} (" + ', '.join(key_cols) + ");")
    cols += ['status text NOT NULL', 'created_at timestamptz NOT NULL DEFAULT now()',
             'updated_at timestamptz NOT NULL DEFAULT now()']
    tables.append((entity, cols, indexes))

    tables.append((f'{entity}_step_log',
                   ['id bigserial PRIMARY KEY', f'{entity}_id uuid NOT NULL',
                    'step text NOT NULL', 'status text NOT NULL', 'details jsonb',
                    'occurred_at timestamptz NOT NULL DEFAULT now()'],
                   [f'CREATE INDEX idx_{entity}_step_log_ref ON {entity}_step_log ({entity}_id);']))
    if 'outbox' in pids:
        tables.append(('outbox',
                       ['id bigserial PRIMARY KEY', 'aggregate_id uuid NOT NULL',
                        'event_type text NOT NULL', 'payload jsonb NOT NULL',
                        'created_at timestamptz NOT NULL DEFAULT now()',
                        'published_at timestamptz'],
                       ['CREATE INDEX idx_outbox_unpublished ON outbox (id) WHERE published_at IS NULL;']))
    if any(s['channel'] in ('webhook', 'callback') for s in model['steps']):
        tables.append(('inbox',
                       ['provider_event_id text PRIMARY KEY', 'received_at timestamptz NOT NULL DEFAULT now()',
                        'payload jsonb NOT NULL', 'processed_at timestamptz'], []))
    if 'ledger' in pids:
        tables.append(('ledger',
                       ['id bigserial PRIMARY KEY', 'account_id uuid NOT NULL',
                        'operation_id text NOT NULL UNIQUE', 'amount numeric(18,2) NOT NULL',
                        'kind text NOT NULL', 'created_at timestamptz NOT NULL DEFAULT now()'],
                       ['CREATE INDEX idx_ledger_account ON ledger (account_id);']))

    ddl = []
    for name, cols_, idx in tables:
        ddl.append(f"CREATE TABLE {name} (\n  " + ',\n  '.join(cols_) + '\n);')
        ddl += idx
    return {'tables': [t[0] for t in tables], 'ddl': '\n\n'.join(ddl)}


# ---------------------------------------------------------------- diagrams
def _mid(name):
    return re.sub(r'\W+', '_', name) or 'X'


def mermaid_flow(model):
    lines = ['flowchart LR', '  U([Инициатор])']
    seen = set()
    for s in model['steps']:
        sid = _mid(s['system'])
        if sid not in seen:
            seen.add(sid)
            role = model['systems'][s['system']]['role']
            shape = ('[("%s")]' if role == 'db' else '{{"%s"}}' if role == 'broker'
                     else '[/"%s"/]' if role == 'external' else '["%s"]')
            lines.append(f'  {sid}{shape % s["system"]}')
    for s in model['steps']:
        srcs = [_mid(model['graph']['by_order'][d]['system'])
                for d in s['deps'] if d in model['graph']['by_order']] or ['U']
        style = '-->' if s['blocking'] else '-.->'
        for src in srcs:
            lines.append(f'  {src} {style}|{s["order"]}. {display_channel(s["channel"])}| {_mid(s["system"])}')
    return '\n'.join(lines)


def mermaid_sequence(model):
    lines = ['sequenceDiagram', '  participant U as Инициатор']
    seen = []
    for s in model['steps']:
        if s['system'] not in seen:
            seen.append(s['system'])
            lines.append(f'  participant {_mid(s["system"])} as {s["system"]}')
    for s in model['steps']:
        srcs = [_mid(model['graph']['by_order'][d]['system'])
                for d in s['deps'] if d in model['graph']['by_order']] or ['U']
        arrow = '->>' if s['blocking'] else '--)'
        for src in srcs:
            lines.append(f'  {src}{arrow}{_mid(s["system"])}: {s["order"]}. {humanize_terms(s["name"])} [{display_channel(s["channel"])}]')
    return '\n'.join(lines)


# ---------------------------------------------------------------- tests gen
def test_checklist(model, findings, patterns):
    items = ['Happy path: процесс проходит все шаги до финального статуса.']
    for s in model['steps']:
        if s['blocking']:
            items.append(f"Отказ шага {s['order']} «{s['name']}»: таймаут/5xx — процесс не зависает, "
                         f"статус и алерт корректны.")
    for f in group_findings(findings):
        if f['severity'] in ('critical', 'high'):
            suffix = f" Затронуто мест: {f.get('count')}." if f.get('count', 1) > 1 else ''
            items.append(f"Регресс на «{f['title']}»: {f['fix'].rstrip('.')}.{suffix}")
    pids = {p['id'] for p in patterns}
    if 'idempotent_consumer' in pids:
        items.append('Дубль события/запроса с тем же ключом обрабатывается ровно один раз.')
    if 'dlq_replay' in pids:
        items.append('Ядовитое сообщение уходит в DLQ после N попыток; replay восстанавливает обработку.')
    if 'ledger' in pids:
        items.append('Reconciliation: сумма проводок ledger сходится с агрегатом баланса.')
    # дедупликация с сохранением порядка
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out





# ---------------------------------------------------------------- detail discovery / anti-forgetting radar
def _probe(status, area, title, question, why, how, examples=None):
    return {
        'status': status, 'area': area, 'title': title,
        'question': question, 'why': why, 'how': how,
        'examples': examples or []
    }


def detail_radar(model, findings, patterns, completeness):
    """Слой против забывания мелких, но критичных деталей.

    Rule-engine ловит явные структурные дефекты. Radar работает шире: он
    строит матрицу инвариантов и уточняющих вопросов по каждому классу
    интеграционных рисков. Поэтому модель не требует бесконечно добавлять
    частные кейсы: частные ошибки проявляются как нарушение инварианта
    идентичности, контракта, статуса, восстановления, конкуренции, безопасности
    или эксплуатации.
    """
    meta, steps, g = model['meta'], model['steps'], model['graph']
    fired = {f.get('rule') for f in findings}
    pids = {p.get('id') for p in patterns}
    missing_q = ' '.join(_low(i.get('question')) for i in (completeness or {}).get('missing', []))
    blob = _model_blob(model)

    probes = []
    def add(status, area, title, question, why, how, examples=None):
        probes.append(_probe(status, area, title, question, why, how, examples))

    has_async = bool(g['async_steps'])
    has_external = bool(g['external_blocking']) or any(model['systems'].get(s['system'], {}).get('role') == 'external' for s in steps)
    has_writes = any(s['writes_entity'] for s in steps)
    has_events = any(s['channel'] in ('kafka', 'queue', 'webhook', 'callback') for s in steps)
    has_multi_system = len({s['system'] for s in steps}) >= 2
    has_money_or_reg = meta['money'] == 'direct' or meta['regulatory']
    lookup = _low(meta.get('lookup_keys'))

    # 1. Идентичность и ключи
    key_scope = _key_scope_analysis(model)
    key_status = 'fail' if ({'ambiguous_composite_business_key', 'generic_identifier_scope_ambiguity', 'missing_key_scope_for_shared_dispatcher'} & fired or key_scope['needs_scope']) else ('unknown' if not lookup else 'ok')
    add(key_status, 'Идентичность и ключи', 'Область уникальности каждого идентификатора должна быть явной.',
        'Какие поля однозначно определяют бизнес-операцию, подоперацию, внешний запрос, событие, replay и запись в БД?',
        'Большая часть тонких ошибок возникает не из-за протокола, а из-за неверного ключа поиска: одинаковый id в разных типах операций, tenant, системах или подоперациях начинает склеивать разные записи.',
        'Для каждого id зафиксируйте scope: global, per-process, per-operationType, per-targetSystem, per-tenant или per-provider. Затем проверьте одинаковость ключа в SELECT, UPDATE, UPSERT, UNIQUE, Inbox, Outbox, DLQ и replay.',
        ['operUid + operationType + targetSystem', 'providerEventId + providerCode', 'requestId + sourceSystem + tenantId'])

    add('fail' if 'retry_without_idempotency' in fired else ('warn' if any(s['retry'] != 'none' for s in steps) else 'ok'),
        'Идентичность и ключи', 'Повторная обработка должна использовать тот же ключ, что и бизнес-операция.',
        'Одинаковый ли ключ используется для идемпотентности, дедупликации входящих сообщений, повторного запуска и поиска существующей операции?',
        'Если idempotency key отличается от ключа поиска или уникального индекса, повтор может не создать дубль технически, но восстановить или обновить не ту бизнес-запись.',
        'Составьте таблицу соответствия: businessKey, idempotencyKey, lookupKey, uniqueIndex, replayKey. Несовпадения должны быть явно обоснованы.')

    # 2. Контракт и семантика данных
    add('fail' if {'event_core_fields', 'contract_versioning'} & fired else ('warn' if has_events else 'ok'),
        'Контракт', 'Контракт должен описывать не только поля, но и их смысл.',
        'Для каждого поля указаны обязательность, формат, источник, владелец, допустимые значения, backward compatibility и правила изменения?',
        'Сервис может формально принимать JSON, но ломаться на изменении enum, nullable-поля, даты, валюты или статуса.',
        'Добавьте schema/version, examples, required/optional, enum lifecycle, compatibility rules, contract tests producer↔consumer.',
        ['eventVersion', 'occurredAt с timezone', 'statusReason', 'currency/amount precision'])

    add('unknown' if has_events and not re.search(r'occurred.?at|timezone|utc|врем[яе].*зон|timestamp', blob) else 'ok',
        'Контракт', 'Время события должно быть однозначным.',
        'Где фиксируется время факта, время публикации, время обработки и timezone?',
        'Ошибки с временем редко видны на happy path, но ломают SLA, сверки, регуляторные отчёты, повторную обработку и расследование инцидентов.',
        'Разделите occurredAt, producedAt, processedAt. Используйте UTC/offset и явно опишите, какое поле используется для сортировки, SLA и отчётности.')

    # 3. Статусы и сценарии
    add('fail' if 'status_model' in fired else ('unknown' if has_async and not meta.get('statuses') else 'ok'),
        'Статусы и сценарии', 'Процесс должен иметь явную статусную модель.',
        'Какие статусы промежуточные, какие финальные, какие ошибочные, а из каких разрешён повтор?',
        'Без статусов поддержка не понимает, где застряла заявка, а разработка не знает, какой результат должен быть у альтернативных сценариев.',
        'Опишите state machine: allowed transitions, terminal statuses, retryable statuses, manual review, cancellation, timeout и reconciliation statuses.')

    add('warn' if g['joins'] or has_external or has_async else 'ok',
        'Статусы и сценарии', 'У каждого альтернативного сценария должен быть ожидаемый результат.',
        'Что происходит при частичном успехе, отказе внешней системы, дубле, out-of-order событии, ручном исправлении и отмене процесса?',
        'Если альтернативы не описаны, команда реализует только happy path, а ошибки начнут всплывать на тестировании или в production.',
        'Для каждого шага заведите минимум: success, validation error, timeout, retry exhausted, duplicate, stale/out-of-order, manual correction.')

    # 4. Целостность и конкуренция
    add('fail' if {'multiple_writers', 'money_controls'} & fired else ('warn' if has_writes and len(g['writers']) > 1 else 'ok'),
        'Целостность данных', 'У каждой бизнес-сущности должен быть владелец и единственный писатель.',
        'Кто имеет право менять основную сущность, а кто только отправляет команду или читает проекцию?',
        'Несколько писателей создают гонки, потерянные обновления и расхождения между сервисами.',
        'Назначьте system of record. Для остальных систем используйте команды, события, read-model или reconciliation.')

    add('unknown' if has_writes and not re.search(r'version|revision|optimistic|lock|блокиров|верси[яи] записи|etag', blob) else 'ok',
        'Целостность данных', 'Нужно проверить потерянные обновления и конкурентные изменения.',
        'Есть ли version/revision/optimistic locking для обновления одной записи несколькими запросами или обработчиками?',
        'Даже при правильном ключе два обработчика могут одновременно прочитать старое состояние и перезаписать результат друг друга.',
        'Для изменяемых записей добавьте version/revision, optimistic locking, compare-and-set или сериализацию команд на уровне владельца сущности.')

    # 5. Ошибки, восстановление и эксплуатация
    add('fail' if {'async_without_recovery', 'poison_retry'} & fired else ('warn' if has_async else 'ok'),
        'Восстановление', 'Для каждой ошибки должен быть понятный маршрут восстановления.',
        'После исчерпания retry куда попадает запись, кто получает алерт, как выполняется replay и как понять, что процесс восстановился?',
        'DLQ без runbook и replay — это не восстановление, а склад ошибок.',
        'Опишите max attempts, DLQ/quarantine, ownership, alert, replay command, idempotent replay, reconciliation после replay.')

    add('fail' if 'async_reconciliation_missing' in fired else ('warn' if has_money_or_reg or has_async else 'ok'),
        'Восстановление', 'Техническая доставка должна проверяться бизнесовой сверкой.',
        'Как система доказывает, что все сущности дошли до финального состояния и данные не разошлись между источником и потребителями?',
        'At-least-once доставка не гарантирует бизнесовую полноту. Сообщение могло попасть в DLQ, быть пропущено, обработаться частично или устареть.',
        'Добавьте reconciliation: expected vs actual, отчёт расхождений, автоматическое довосстановление, ручной разбор и аудит исправлений.')

    # 6. Порядок, дедупликация и out-of-order
    add('fail' if 'ordering' in fired else ('warn' if meta.get('ordering') in ('per_entity', 'global') or has_events else 'ok'),
        'Порядок и конкуренция', 'Порядок событий должен быть задан только там, где он действительно нужен.',
        'Нужно ли обрабатывать события строго по сущности, глобально или порядок вообще не важен?',
        'Лишнее требование глобального порядка убивает масштабирование, а отсутствие per-entity ordering ломает статусные переходы.',
        'Опишите partition key, stale-event policy, sequence/version, обработку out-of-order и правила игнорирования устаревших событий.')

    add('unknown' if has_events and not re.search(r'duplicate|дубл|dedup|inbox|идемпот|повтор', blob) else 'ok',
        'Порядок и конкуренция', 'Дубли и устаревшие события должны быть частью сценария.',
        'Что происходит, если одно и то же событие пришло дважды, пришло после финального статуса или пришло старее текущей версии сущности?',
        'На реальных брокерах и webhook дубли — нормальное поведение, а не исключение.',
        'Добавьте Inbox/dedup, sequence/version check, terminal-state guard и тесты duplicate/stale/out-of-order.')

    # 7. Безопасность и ПДн
    sensitive = meta.get('regulatory') or any(f.get('sensitive') for f in meta.get('fields', [])) or re.search(r'пдн|паспорт|телефон|email|personal|sensitive|персональн', blob)
    add('fail' if sensitive and not re.search(r'mask|маскир|шифр|encrypt|retention|ttl|обезлич|персональн.*данн', blob) else ('warn' if sensitive else 'ok'),
        'Безопасность', 'Чувствительные данные должны иметь правила хранения и отображения.',
        'Какие поля являются ПДн/секретами, где они логируются, как маскируются, сколько хранятся и кто имеет доступ?',
        'Интеграция часто случайно уносит ПДн в логи, DLQ, outbox, аналитические витрины и тестовые стенды.',
        'Опишите классификацию полей, маскирование логов, encryption at rest/in transit, retention, права доступа, очистку DLQ и запрет чувствительных данных в технических ошибках.')

    # 8. Наблюдаемость и поддержка
    add('fail' if {'no_correlation_id', 'observability_missing'} & fired else ('warn' if has_multi_system else 'ok'),
        'Наблюдаемость', 'У поддержки должен быть способ найти весь процесс по одному идентификатору.',
        'По какому trackingId/correlationId оператор, аналитик или разработчик найдёт все шаги, события, внешние вызовы и ошибки?',
        'Без сквозной трассировки даже правильный процесс невозможно поддерживать в incident mode.',
        'Пробросьте correlationId/traceId, заведите status history, business metrics, technical metrics, dashboard, alert rules и runbook.')

    # 9. Миграция и совместимость
    add('warn' if meta.get('replacing_legacy') and not re.search(r'cutover|rollback|dual.?run|миграц|откат|совместим|shadow', blob) else 'ok',
        'Внедрение', 'Для изменения существующей интеграции нужен план перехода.',
        'Как будет выполнен cutover, что происходит со старыми сообщениями, как откатиться и как проверяется совместимость?',
        'Даже хорошая целевая архитектура может сломать production при переходе без dual-run, rollback и миграции незавершённых процессов.',
        'Опишите feature flag, dual-run/shadow, backfill, миграцию старых статусов, rollback criteria, freeze window и совместимость контрактов.')

    # Универсальный каталог инвариантов v7.1. Он добавляет не частные кейсы,
    # а широкий набор системных проверок по всем применимым областям.
    existing = {(p.get('area'), p.get('title')) for p in probes}
    for inv in universal_invariant_probes(model, findings, patterns, completeness):
        key = (inv.get('area'), inv.get('title'))
        if key not in existing:
            probes.append(inv)
            existing.add(key)

    # Сводка: сколько пунктов требуют внимания.
    counters = {'fail': 0, 'warn': 0, 'unknown': 0, 'ok': 0}
    for p in probes:
        counters[p['status']] = counters.get(p['status'], 0) + 1
    stats = invariant_catalog_stats(model)
    summary = (f"Матрица деталей: применимо инвариантов из каталога v7.1 — {stats.get('applicable', 0)} из {stats.get('total', 0)}; "
               f"блокируют выпуск — {counters.get('fail',0)}, требуют внимания — {counters.get('warn',0)}, "
               f"нужно уточнить — {counters.get('unknown',0)}, уже выглядит закрытым — {counters.get('ok',0)}.")
    return {'summary': summary, 'counters': counters, 'catalog_stats': stats, 'probes': probes}



def _step_failure_handling(step, system_role='internal'):
    """Возвращает конкретную обработку ошибок для шага по типу канала.

    Цель — не повторять шаблон «опишите retry/DLQ/компенсацию» на каждом шаге,
    а дать разработчику основу поведения именно для REST, Kafka, webhook, DB,
    file/batch и CDC.
    """
    ch = step['channel']
    writes = step.get('writes_entity')
    retry = step.get('retry') != 'none'
    idem = step.get('idempotency') != 'none'
    prefix = []
    if system_role == 'external' or step.get('external'):
        prefix.append('Если зависимость вернула timeout, 5xx или 429, завершить ожидание по заданному timeout, записать техническую причину и не держать поток бесконечно.')
    if ch in ('rest','graphql','odata','soap','grpc','api_gateway','service_mesh','esb','auth_oidc','vault'):
        parts = prefix or ['Если вызов завершился timeout, 5xx или сетевой ошибкой, процесс должен перейти в явный технический статус, а не зависнуть без результата.']
        if ch == 'soap':
            parts.append('Для SOAP/WSDL фиксируйте XSD, SOAP Fault mapping, версионирование и совместимость с legacy-клиентами.')
        if ch == 'api_gateway':
            parts.append('Для API Gateway нужны auth, rate limit, routing, versioning, request size limits и единая модель ошибок.')
        if ch == 'esb':
            parts.append('Для ESB нужны правила маршрутизации, трансформации сообщений, идемпотентность и ownership схем.')
        parts.append('Повторять вызов можно только при подтверждённой идемпотентности; иначе нужна ручная проверка или компенсация.')
        if system_role == 'external' or step.get('external'):
            parts.append('Для внешней системы нужны circuit breaker, backoff с jitter, лимит параллелизма и сценарий деградации или отложенной обработки.')
        else:
            parts.append('Для 4xx/валидационной ошибки нужен доменный отказ; для 5xx — техническая ошибка с возможностью безопасного повтора.')
        if writes:
            parts.append('Если шаг меняет бизнес-сущность, запись результата и статус шага должны быть атомарными или защищены идемпотентным ключом.')
        return ' '.join(parts)
    if ch in BROKER_CHANNELS:
        parts = [
            'Если сообщение не прошло валидацию схемы или бизнес-обработку, consumer выполняет ограниченный retry с backoff.',
            'Offset/ack фиксируется только после успешного применения бизнес-изменения.',
            'После исчерпания попыток сообщение уходит в DLQ/parking lot/карантин с причиной ошибки и correlationId.',
            'Replay из DLQ должен использовать тот же idempotency/business key, что и обычная обработка.'
        ]
        if ch == 'kafka':
            parts.append('Для Kafka отдельно фиксируйте topic, partition key, consumer group, retention и replay-runbook.')
        elif ch == 'rabbitmq':
            parts.append('Для RabbitMQ отдельно фиксируйте exchange, routing key, queue, prefetch, ack/nack, TTL и DLX.')
        elif ch.startswith('redis'):
            parts.append('Для Redis Streams/queue отдельно фиксируйте consumer group, pending entries, TTL/trim policy и риск потери данных при неверной persistence-настройке.')
        if not idem:
            parts.append('Перед реализацией нужно добавить идемпотентность, иначе повторная доставка может создать дубль или перезаписать не ту запись.')
        return ' '.join(parts)
    if ch in ('webhook', 'callback'):
        return ('Входящий callback нужно проверить по подписи, timestamp/nonce и допустимому окну времени. '
                'Дубликат callback обрабатывается через Inbox/dedup и не меняет состояние повторно. '
                'Неизвестный, просроченный или неподписанный callback отклоняется и логируется без раскрытия ПДн. '
                'Бизнес-ошибка переводит процесс в согласованный статус ожидания, отказа или ручного разбора.')
    if ch in ('redis_cache', 'redis_lock'):
        if ch == 'redis_cache':
            return ('Redis cache должен быть только ускорителем чтения, а не источником истины. Нужны TTL, invalidation/cache-aside, защита от cache stampede и fallback к БД.')
        return ('Redis lock требует TTL, fencing token и безопасного release. Без fencing token задержанный процесс может продолжить запись после истечения lock.')
    if ch == 'search':
        return ('Поисковый индекс должен обновляться асинхронно через outbox/indexer; нужны reindex, alias switch, контроль lag и fallback при отставании индекса.')
    if ch == 'db':
        parts = [
            'При ошибке записи транзакция должна откатиться целиком.',
            'Для повторного запуска используется UNIQUE-индекс или optimistic locking, чтобы не создать дубль.',
            'Конфликт версии или уникальности должен обрабатываться как известный сценарий: вернуть существующий результат, повторить чтение или отправить на ручную сверку.'
        ]
        if writes:
            parts.append('История статусов или step_log должна показать, на каком изменении остановился процесс.')
        return ' '.join(parts)
    if ch in ('file','batch','sftp','object_storage','etl','airflow','spark','dbt','clickhouse','data_warehouse','data_lake','lakehouse'):
        return ('Для файла или batch-нaгрузки нужны checksum/control totals, batchId, журнал принятых строк и карантин ошибок. '
                'Повторная загрузка того же batchId не должна применять строки повторно. '
                'Частично обработанный batch должен иметь resume/reprocess-процедуру и отчёт по принятым, отклонённым и спорным записям.')
    if ch == 'cdc':
        return ('Для CDC нужно контролировать offset/LSN, lag, schema drift и повторную доставку изменений. '
                'Применение изменений должно быть идемпотентным по ключу источника и версии события. '
                'При отставании или ошибке парсинга поток переводится в контролируемый replay/resync, а не ломает core-flow.')
    return 'Нужно явно описать поведение при ошибке для этого шага: какой статус выставляется, кто владелец разбора, как выполняется безопасный повтор и как исключается дубль.'


# ---------------------------------------------------------------- scenario generation
def development_scenario(model, findings, patterns):
    """Строит основу сценария для дальнейшей разработки: основной поток,
    альтернативные ветки, ошибки, восстановление и acceptance criteria.

    Это не LLM: сценарий выводится из графа, каналов, статусов, паттернов и
    найденных рисков. Поэтому он повторяемый и пригоден как черновик ТЗ/US.
    """
    meta, steps, g = model['meta'], model['steps'], model['graph']
    pids = {p['id'] for p in patterns}
    fired = {f['rule'] for f in findings}
    statuses = meta.get('statuses') or ['CREATED', 'ACCEPTED', 'PROCESSING', 'COMPLETED', 'REJECTED', 'FAILED']

    main_flow = []
    for s in steps:
        deps = ', '.join(str(d) for d in s.get('deps') or []) or 'старт процесса'
        effect = 'меняет состояние основной сущности' if s['writes_entity'] else 'не меняет основную сущность'
        wait = 'шаг блокирующий: следующий шаг ждёт результат' if s['blocking'] else 'шаг асинхронный: процесс продолжается через событие/очередь'
        main_flow.append({
            'order': s['order'],
            'title': f"{s['system']}: {humanize_terms(s['name'])}",
            'actor': s['system'],
            'channel': s['channel'],
            'channel_label': display_channel(s['channel']),
            'depends_on': deps,
            'what_happens': f"Система «{s['system']}» выполняет действие «{humanize_terms(s['name'])}». Способ взаимодействия: {display_channel(s['channel'])}.",
            'stack_reason': s.get('stack_reason') or '',
            'source_system': s.get('source_system') or '',
            'target_system': s.get('target_system') or '',
            'result': f"Результат шага фиксируется в статусе процесса или в журнале шагов; {effect}.",
            'controls': [wait] + ([f"таймаут: {s['timeout_ms']} мс"] if s['timeout_ms'] else [])
                        + ([f"повторная попытка: {'автоматически' if s['retry']=='auto' else 'вручную'}"] if s['retry'] != 'none' else [])
                        + ([f"идемпотентность: {'по ключу' if s['idempotency']=='key' else 'по бизнес-ключу'}"] if s['idempotency'] != 'none' else []),
            'failure_handling': s['compensation'] or _step_failure_handling(s, model['systems'].get(s['system'], {}).get('role', 'internal')),
        })

    alternatives = []
    def add_alt(name, trigger, steps_, result, controls):
        alternatives.append({'name': name, 'trigger': trigger, 'steps': steps_, 'result': result, 'controls': controls})

    if g['async_steps']:
        add_alt('Асинхронное принятие заявки без ожидания финального результата',
                'Хвост процесса занимает больше допустимого времени ответа или зависит от внешних систем.',
                ['Система принимает запрос и создаёт trackingId.', 'Клиенту или вызывающей системе возвращается подтверждение приёма.',
                 'Дальнейшая обработка идёт через событие/очередь.', 'Статус процесса обновляется после каждого значимого шага.'],
                'Пользователь или потребитель видит промежуточный статус, а не зависший запрос.',
                ['trackingId обязателен', 'GET /status или событие статуса', 'финальные статусы должны быть согласованы'])
    if any(s['retry'] != 'none' for s in steps) or 'idempotent_consumer' in pids:
        add_alt('Повторная доставка или повторный запрос',
                'Сеть оборвалась, producer отправил событие повторно или consumer переобработал сообщение.',
                ['Система получает тот же idempotencyKey/eventId/business key.', 'Выполняется попытка вставки ключа в Inbox или поиск существующей операции.',
                 'Если ключ уже обработан, система возвращает прежний результат без повторного изменения бизнес-состояния.'],
                'Повтор не создаёт дубль операции, документа, проводки или статуса.',
                ['UNIQUE-индекс на ключ идемпотентности', 'commit offset только после успешной обработки', 'тест дубля обязателен'])
    if 'composite_business_key' in pids or 'ambiguous_composite_business_key' in fired:
        add_alt('Одинаковый operUid для разных типов операций',
                'Один универсальный сервис отправляет несколько подопераций в разные целевые системы в рамках одного процесса.',
                ['Сервис получает две записи с одинаковым operUid, но разным operationType или targetSystem.',
                 'Поиск, upsert, dedup и replay выполняются по составному ключу, а не только по operUid.',
                 'Каждая подоперация получает собственный статус и отдельную запись в журнале шагов.'],
                'Запрос в систему А и запрос в систему Б не склеиваются и не перезаписывают друг друга.',
                ['UNIQUE(operUid, operationType) или UNIQUE(operUid, operationType, targetSystem)',
                 'все SELECT/UPDATE используют тот же составной ключ', 'регрессионный тест на одинаковый operUid обязателен'])
    if g['external_blocking']:
        add_alt('Внешняя система недоступна или отвечает медленно',
                'Внешняя зависимость вернула timeout, 5xx, 429 или стала нестабильной.',
                ['Вызов завершается по timeout, а не висит бесконечно.', 'Circuit breaker ограничивает новые попытки.',
                 'Если операция критична, она переводится в статус ожидания или ручного разбора.', 'Если данные необязательны, используется fallback или partial response.'],
                'Отказ партнёра не приводит к каскадному отказу всего процесса.',
                ['timeout на каждый внешний вызов', 'circuit breaker', 'fallback/очередь/ручной разбор', 'алерт владельцу зависимости'])
    if any(s['channel'] in ('kafka','queue') for s in steps):
        add_alt('Ошибка обработки сообщения',
                'Consumer получил сообщение, но бизнес-обработка завершилась ошибкой.',
                ['Consumer выполняет ограниченный retry с backoff.', 'После исчерпания попыток сообщение попадает в DLQ или карантин.',
                 'Создаётся алерт и задача на разбор.', 'После исправления причины выполняется replay.'],
                'Сообщение не теряется и не крутится бесконечно.',
                ['max attempts', 'DLQ/карантин', 'runbook replay', 'идемпотентность replay'])
    if meta['regulatory'] or meta['money'] == 'direct' or g['async_steps']:
        add_alt('Расхождение данных между источником истины и потребителем',
                'Техническая доставка прошла не полностью, replay был пропущен или потребитель отстал.',
                ['Reconciliation job сравнивает expected и actual состояния.', 'Найденные расхождения попадают в отчёт.',
                 'Безопасные расхождения восстанавливаются автоматически.', 'Опасные расхождения уходят на ручной разбор.'],
                'Бизнес видит не только техническую доставку, но и фактическую полноту процесса.',
                ['регулярная сверка', 'отчёт расхождений', 'owner ручного разбора', 'аудит исправлений'])

    error_flows = []
    for f in group_findings(findings):
        if f['severity'] not in ('critical', 'high'):
            continue
        error_flows.append({
            'name': f['title'],
            'where': f.get('where_summary') or f.get('where') or 'Весь процесс',
            'failure': f['why'],
            'expected_handling': f['fix'],
            'affected_count': f.get('count', 1),
        })
        if len(error_flows) >= 12:
            break

    dev_tasks = [
        'Зафиксировать основной happy path и финальные статусы процесса.',
        'Описать альтернативные сценарии и ошибки из этого раздела в постановке или в use case.',
        'Для каждого шага определить владельца, контракт, timeout, retry, идемпотентность и восстановление.',
        'Добавить таблицу журнала шагов/status history, чтобы поддержка видела, где остановился процесс.',
    ]
    if 'composite_business_key' in pids or 'ambiguous_composite_business_key' in fired:
        dev_tasks.append('Проверить все места поиска по operUid и заменить одиночный поиск на составной ключ operUid + operationType + targetSystem/sourceSystem там, где это требуется.')
    if g['async_steps']:
        dev_tasks.append('Описать DLQ, replay и правила повторной обработки для каждого асинхронного шага.')
    if g['external_blocking']:
        dev_tasks.append('Описать деградацию при отказе внешних систем: timeout, circuit breaker, fallback и ручной разбор.')

    acceptance = [
        'Happy path проходит от первого шага до финального статуса без ручного вмешательства.',
        'Каждый отказ из error-flow переводит процесс в понятный статус и оставляет запись в журнале.',
        'Повторный запрос или повторное событие не создаёт дубль бизнес-операции.',
        'По correlationId/trackingId можно найти все шаги одного процесса в логах и БД.',
    ]
    if 'composite_business_key' in pids or 'ambiguous_composite_business_key' in fired:
        acceptance.append('Две записи с одинаковым operUid и разным operationType/targetSystem сохраняются и ищутся как разные операции.')

    return {
        'statuses': statuses,
        'main_flow': main_flow,
        'alternative_flows': alternatives,
        'error_flows': error_flows,
        'development_tasks': dev_tasks,
        'acceptance_criteria': acceptance,
    }

# ---------------------------------------------------------------- analyze
def analyze(payload):
    model = build_graph(normalize(payload))
    errors = validate(model)
    if errors:
        return {'ok': False, 'errors': errors}
    findings = run_rules(model)
    finding_groups = group_findings(findings)
    patterns = recommend_patterns(model, findings)
    verdict = score(findings, finding_groups)
    schema = db_schema(model, patterns)
    completeness = completeness_check(model)
    checklist = architecture_checklist(model, findings, patterns, completeness)
    gates = quality_gates(model, findings, checklist, completeness)
    alternatives = architecture_alternatives(model, findings, patterns, gates)
    artifacts = project_artifacts(model, findings, patterns, gates)
    scenario = development_scenario(model, findings, patterns)
    radar = detail_radar(model, findings, patterns, completeness)
    return {
        'ok': True,
        'model': model,
        'findings': findings,
        'finding_groups': finding_groups,
        'patterns': patterns,
        'verdict': verdict,
        'schema': schema,
        'diagrams': {'flow': mermaid_flow(model), 'sequence': mermaid_sequence(model)},
        'completeness': completeness,
        'checklist': checklist,
        'quality_gates': gates,
        'alternatives': alternatives,
        'artifacts': artifacts,
        'scenario': scenario,
        'detail_radar': radar,
        'tests': test_checklist(model, findings, patterns),
    }
