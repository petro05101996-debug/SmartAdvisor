#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Бенчмарк покрытия сложных кейсов.

15 классов сложных интеграционных ситуаций (взяты из реальных кейс-паков v5
и типовых production-задач). Кейс засчитан, если движок выдал ВСЕ ключевые
выводы (правила rule:* и/или паттерны pat:*). Запуск: python bench.py
"""
from engine import analyze


def step(order, name, system, channel='rest', blocking='yes', timeout=0,
         retry='none', idem='none', comp='', writes='no', dep=0, din='', dout=''):
    return {'order': order, 'name': name, 'system': system, 'channel': channel,
            'blocking': blocking, 'timeout_ms': timeout, 'retry': retry,
            'idempotency': idem, 'compensation': comp, 'writes_entity': writes,
            'depends_on': dep, 'data_in': din, 'data_out': dout}


CASES = [
 ('Финансовая E2E-сага (кредитная заявка)',
  {'meta': {'name': 'x', 'entity': 'Loan', 'money': 'direct', 'customer_visible': 'yes',
            'sla_ms': 1000},
   'systems': [{'name': 'Скоринг', 'role': 'external'}],
   'steps': [step(1, 'создать', 'Заявки', timeout=300, writes='yes'),
             step(2, 'скоринг', 'Скоринг', dep=1, timeout=5000, retry='auto'),
             step(3, 'провести', 'Биллинг', dep=2, timeout=500, writes='yes')]},
  {'rule:money_controls', 'rule:sla_budget', 'rule:saga_without_compensation',
   'pat:ledger', 'pat:saga'}),

 ('Платёжный webhook от PSP',
  {'meta': {'name': 'x', 'entity': 'Payment', 'money': 'direct'},
   'steps': [step(1, 'принять callback', 'API', channel='webhook', blocking='no',
                  retry='auto', writes='yes')]},
  {'rule:callback_inbox', 'rule:inbound_security', 'pat:idempotent_consumer'}),

 ('Enrichment-publisher: запись + публикация события',
  {'meta': {'name': 'x', 'entity': 'Order'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
             step(2, 'обогатить и опубликовать', 'Заказы', channel='kafka',
                  dep=1, retry='auto')]},
  {'rule:dual_write', 'pat:outbox'}),

 ('DWH/offload в core-flow',
  {'meta': {'name': 'x', 'entity': 'Order'},
   'systems': [{'name': 'DWH', 'role': 'analytics'}],
   'steps': [step(1, 'оформить', 'Заказы', timeout=300, writes='yes', idem='key'),
             step(2, 'выгрузить в DWH', 'DWH', dep=1, timeout=2000)]},
  {'rule:analytics_in_core', 'pat:cdc_etl'}),

 ('Legacy-файлообмен в клиентском пути',
  {'meta': {'name': 'x', 'entity': 'Order', 'customer_visible': 'yes', 'sla_ms': 3000},
   'steps': [step(1, 'оформить', 'Сайт', timeout=300, idem='key'),
             step(2, 'передать файлом в 1С', '1С', channel='file', dep=1)]},
  {'rule:slow_channel_in_fast_path'}),

 ('Shared Kafka topic / selective consumer (highload)',
  {'meta': {'name': 'x', 'entity': 'Event', 'load_rps': 3000, 'peak_factor': 5},
   'systems': [{'name': 'Общий topic', 'role': 'broker'}],
   'steps': [step(1, 'читать общий topic', 'Общий topic', channel='kafka',
                  blocking='no', retry='auto', din='фильтр: нужно ~2% событий'),
             step(2, 'обработать и записать', 'Сервис', channel='kafka', blocking='no',
                  dep=1, retry='auto', writes='yes')]},
  {'rule:stream_consumer_controls', 'pat:idempotent_consumer'}),

 ('Highload stream ingestion (телеметрия)',
  {'meta': {'name': 'x', 'entity': 'Metric', 'load_rps': 20000, 'peak_factor': 10},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'принять поток', 'Ingest', channel='kafka', blocking='no',
                  retry='auto', comp='DLQ после 5 попыток'),
             step(2, 'агрегировать', 'Stream-процессор', channel='kafka', blocking='no',
                  dep=1, retry='auto', comp='DLQ', writes='yes', idem='key')]},
  {'rule:stream_ingestion'}),

 ('Active-active запись финансового баланса',
  {'meta': {'name': 'x', 'entity': 'Balance', 'money': 'direct'},
   'steps': [step(1, 'списание в ДЦ-1', 'Биллинг-A', writes='yes', idem='key', timeout=200),
             step(2, 'списание в ДЦ-2', 'Биллинг-B', writes='yes', idem='key',
                  timeout=200, dep=1, comp='сверка')]},
  {'rule:money_controls', 'pat:ledger'}),

 ('Multi-tenant: один крупный tenant забивает пул',
  {'meta': {'name': 'x', 'entity': 'Job', 'multi_tenant': 'yes',
            'load_rps': 2000, 'peak_factor': 5},
   'systems': [{'name': 'Очередь', 'role': 'broker'}],
   'steps': [step(1, 'поставить задачу', 'Очередь', channel='queue', blocking='no',
                  retry='auto', comp='DLQ'),
             step(2, 'обработать', 'Воркеры', channel='queue', blocking='no',
                  dep=1, retry='auto', comp='DLQ', idem='key')]},
  {'rule:multi_tenant_fairness'}),

 ('ПДн: чувствительные данные без политики хранения',
  {'meta': {'name': 'x', 'entity': 'Client', 'regulatory': 'yes',
            'fields': 'passport:string|required|sensitive, phone:string|sensitive'},
   'steps': [step(1, 'сохранить анкету', 'CRM', writes='yes', idem='key', timeout=300),
             step(2, 'записать аудит', 'Журнал', dep=1, timeout=100)]},
  {'rule:sensitive_data_policy'}),

 ('Customer 360 / BFF: горячий read из 4 источников',
  {'meta': {'name': 'x', 'entity': 'Customer360', 'customer_visible': 'yes',
            'read_freq': 'very_high', 'sla_ms': 300},
   'systems': [{'name': 'Лояльность', 'role': 'external'}],
   'steps': [step(1, 'собрать карточку', 'BFF', timeout=50),
             step(2, 'профиль', 'CRM', dep=1, timeout=100),
             step(3, 'баланс', 'Биллинг', dep=1, timeout=100),
             step(4, 'бонусы', 'Лояльность', dep=1, timeout=200),
             step(5, 'заказы', 'Заказы', dep=1, timeout=100)]},
  {'rule:fanout_sync', 'pat:read_model'}),

 ('CDC-модернизация legacy (source read-only)',
  {'meta': {'name': 'x', 'entity': 'Account'},
   'systems': [{'name': 'Legacy-АБС', 'role': 'legacy'}],
   'steps': [step(1, 'читать изменения CDC', 'Legacy-АБС', channel='cdc',
                  blocking='no', retry='auto', comp='DLQ'),
             step(2, 'строить проекцию', 'Проекция', channel='queue', blocking='no',
                  dep=1, retry='auto', comp='DLQ', writes='yes', idem='key')]},
  {'rule:cdc_projection_controls'}),

 ('Миграция / strangler: замена старой системы',
  {'meta': {'name': 'x', 'entity': 'Order', 'replacing_legacy': 'yes'},
   'systems': [{'name': 'Старый контур', 'role': 'legacy'}],
   'steps': [step(1, 'писать в новый сервис', 'Новый сервис', writes='yes',
                  idem='key', timeout=300)]},
  {'rule:migration_cutover'}),

 ('Строгий порядок событий per-entity',
  {'meta': {'name': 'x', 'entity': 'Order', 'ordering': 'per_entity'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'публиковать статусы', 'Kafka', channel='kafka', blocking='no',
                  retry='auto', comp='DLQ')]},
  {'rule:ordering'}),

 ('Пиковая нагрузка на партнёра с rate limit',
  {'meta': {'name': 'x', 'entity': 'Check', 'load_rps': 800, 'peak_factor': 5},
   'systems': [{'name': 'Партнёр', 'role': 'external', 'stability': 'limited',
                'rate_limit_rps': 100}],
   'steps': [step(1, 'проверка у партнёра', 'Партнёр', timeout=500, retry='auto',
                  idem='key')]},
  {'rule:unstable_dependency', 'rule:capacity_vs_limit'}),

 # --- v6.1: классы рисков, которые ранее не покрывались движком ---
 ('Инверсия таймаутов: ребёнок ждёт дольше родителя',
  {'meta': {'name': 'x', 'entity': 'Order', 'sla_ms': 1000},
   'steps': [step(1, 'шлюз', 'GW', timeout=300),
             step(2, 'провести в биллинге', 'Биллинг', dep=1, timeout=800, writes='yes')]},
  {'rule:timeout_inversion'}),

 ('Каскадное усиление retry: два внешних звена с авто-повтором',
  {'meta': {'name': 'x', 'entity': 'Order', 'customer_visible': 'yes', 'sla_ms': 2000},
   'systems': [{'name': 'A', 'role': 'external'}, {'name': 'B', 'role': 'external'}],
   'steps': [step(1, 'вызов A', 'A', timeout=500, retry='auto'),
             step(2, 'вызов B', 'B', dep=1, timeout=500, retry='auto')]},
  {'rule:retry_amplification', 'rule:external_blocking', 'pat:circuit_breaker'}),

 ('Read-your-writes: async запись, затем синхронное чтение в UI',
  {'meta': {'name': 'x', 'entity': 'Order', 'customer_visible': 'yes'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'записать асинхронно', 'Заказы', channel='kafka', blocking='no',
                  writes='yes', retry='auto', comp='DLQ'),
             step(2, 'показать карточку клиенту', 'BFF', dep=1, timeout=200)]},
  {'rule:read_your_writes'}),

 ('Блокирующий внешний вызов внутри обработчика очереди',
  {'meta': {'name': 'x', 'entity': 'Job'},
   'systems': [{'name': 'Очередь', 'role': 'broker'}, {'name': 'Партнёр', 'role': 'external'}],
   'steps': [step(1, 'поставить', 'Очередь', channel='queue', timeout=50),
             step(2, 'воркер', 'Воркер', channel='queue', blocking='no', dep=1,
                  retry='auto', comp='DLQ', idem='key'),
             step(3, 'синхронно дёрнуть партнёра', 'Партнёр', dep=2, timeout=3000)]},
  {'rule:blocking_in_async_handler'}),

 ('Распределённый процесс без сквозного correlationId',
  {'meta': {'name': 'x', 'entity': 'Order'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'создать', 'Заказы', writes='yes', idem='key', timeout=200),
             step(2, 'оплатить', 'Платежи', dep=1, timeout=300),
             step(3, 'уведомить', 'Kafka', channel='kafka', blocking='no', dep=2,
                  retry='auto', comp='DLQ')]},
  {'rule:no_correlation_id'}),

 ('Параллельный fan-out: тяжёлая ветка скрыта за SLA (latency critical path)',
  {'meta': {'name': 'x', 'entity': 'Page', 'customer_visible': 'yes', 'sla_ms': 500},
   'steps': [step(1, 'собрать страницу', 'BFF', timeout=50),
             step(2, 'быстрый блок 1', 'S2', dep=1, timeout=80),
             step(3, 'быстрый блок 2', 'S3', dep=1, timeout=80),
             step(4, 'медленный отчёт', 'S4', dep=1, timeout=900)]},
  {'rule:sla_budget'}),

 # --- v6.2: fan-in/join (DAG) и новые классы рисков ---
 ('Customer 360 fan-in: агрегация из источников без partial response',
  {'meta': {'name': 'x', 'entity': 'Customer360', 'customer_visible': 'yes',
            'read_freq': 'very_high', 'sla_ms': 400},
   'systems': [{'name': 'Лояльность', 'role': 'external'}],
   'steps': [step(1, 'старт', 'BFF', timeout=30),
             step(2, 'профиль', 'CRM', dep=1, timeout=100),
             step(3, 'баланс', 'Биллинг', dep=1, timeout=100),
             step(4, 'бонусы', 'Лояльность', dep=1, timeout=300),
             {'order': 5, 'name': 'собрать карточку', 'system': 'BFF', 'channel': 'rest',
              'blocking': 'yes', 'timeout_ms': 20, 'depends_on': [2, 3, 4]}]},
  {'rule:fanin_partial_failure', 'pat:partial_response'}),

 ('Fan-in: медленная ветвь определяет SLA (нужен DAG, не дерево)',
  {'meta': {'name': 'x', 'entity': 'Page', 'customer_visible': 'yes', 'sla_ms': 300},
   'systems': [{'name': 'Отчёты', 'role': 'external'}],
   'steps': [step(1, 'старт', 'BFF', timeout=30),
             step(2, 'быстрый блок', 'S2', dep=1, timeout=80),
             {'order': 3, 'name': 'медленный отчёт', 'system': 'Отчёты', 'channel': 'rest',
              'blocking': 'yes', 'timeout_ms': 900, 'depends_on': 1},
             {'order': 4, 'name': 'собрать', 'system': 'BFF', 'channel': 'rest',
              'blocking': 'yes', 'timeout_ms': 20, 'depends_on': [2, 3]}]},
  {'rule:sla_budget', 'rule:fanin_partial_failure'}),

 ('Producer↔Consumer без версионирования контракта',
  {'meta': {'name': 'x', 'entity': 'Order'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'сохранить', 'Заказы', writes='yes', idem='key', timeout=200),
             step(2, 'в Kafka', 'Kafka', channel='kafka', dep=1, retry='auto', comp='outbox'),
             step(3, 'потребить', 'CRM', channel='kafka', blocking='no', dep=2,
                  retry='auto', comp='DLQ', idem='key')]},
  {'rule:contract_versioning'}),

 ('Горячее чтение из источника без кэша на критическом пути',
  {'meta': {'name': 'x', 'entity': 'Catalog', 'customer_visible': 'yes',
            'read_freq': 'very_high', 'sla_ms': 300},
   'systems': [{'name': 'Каталог-сервис', 'role': 'external'}],
   'steps': [step(1, 'получить карточку товара', 'Каталог-сервис', timeout=200)]},
  {'rule:hot_read_no_cache'}),
 # --- v6.3: product-quality слой, чек-листы и gates ---
 ('Event envelope отсутствует: нельзя трассировать и replay',
  {'meta': {'name': 'x', 'entity': 'Application'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'сохранить заявку', 'Банк', writes='yes', idem='key', timeout=100),
             step(2, 'опубликовать статус', 'Kafka', channel='kafka', blocking='no',
                  dep=1, retry='auto', comp='outbox DLQ'),
             step(3, 'прочитать статус', 'CRM', channel='kafka', blocking='no',
                  dep=2, retry='auto', comp='DLQ', idem='key')]},
  {'rule:event_core_fields'}),

 ('Регуляторный async-процесс без сверки',
  {'meta': {'name': 'x', 'entity': 'Document', 'regulatory': 'yes',
            'statuses': 'CREATED, SENT, DONE'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'принять документ', 'Банк', writes='yes', idem='key', timeout=100),
             step(2, 'отправить в топик', 'Kafka', channel='kafka', blocking='no',
                  dep=1, retry='auto', comp='DLQ replay')]},
  {'rule:async_reconciliation_missing'}),

 ('Распределённая интеграция без наблюдаемости',
  {'meta': {'name': 'x', 'entity': 'Application'},
   'systems': [{'name': 'Kafka', 'role': 'broker'}],
   'steps': [step(1, 'создать заявку', 'Банк', writes='yes', idem='key', timeout=100),
             step(2, 'статус в топик', 'Kafka', channel='kafka', blocking='no',
                  dep=1, retry='auto', comp='DLQ replay')]},
  {'rule:observability_missing'}),

 ('Клиентский REST без модели ошибок',
  {'meta': {'name': 'x', 'entity': 'Order', 'customer_visible': 'yes'},
   'steps': [step(1, 'создать заказ', 'API', timeout=300, writes='yes', idem='key')]},
  {'rule:api_error_contract'}),

 ('Критичная система без владельца',
  {'meta': {'name': 'x', 'entity': 'Order'},
   'systems': [{'name': 'Биллинг', 'role': 'internal', 'criticality': 'critical'}],
   'steps': [step(1, 'провести операцию', 'Биллинг', timeout=200, writes='yes', idem='key')]},
  {'rule:no_owner_for_critical_system'}),

 # --- v6.7: сценарный слой и ошибки области уникальности ключа ---
 ('Универсальный докатчик: одинаковый operUid для разных operationType',
  {'meta': {'name': 'x', 'entity': 'DispatchOperation',
            'goal': 'универсальный докатчик отправляет запросы в систему А и систему Б; поиск выполняется по operUid',
            'fields': 'operUid:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed',
            'lookup_keys': 'operUid'},
   'systems': [{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
   'steps': [step(1, 'отправить в систему А', 'Система А', timeout=500, retry='auto', idem='key'),
             step(2, 'отправить в систему Б с тем же operUid', 'Система Б', timeout=500, retry='auto', idem='key', dep=1)]},
  {'rule:ambiguous_composite_business_key', 'pat:composite_business_key'}),

 # --- v6.8: anti-forgetting radar и обобщённые ошибки scope id ---
 ('Общий адаптер: requestId без scope в нескольких направлениях',
  {'meta': {'name': 'x', 'entity': 'ExternalRequest',
            'goal': 'общий адаптер используется для нескольких систем; один requestId может повториться в разных направлениях',
            'lookup_keys': 'requestId'},
   'systems': [{'name': 'Система А', 'role': 'external'}, {'name': 'Система Б', 'role': 'external'}],
   'steps': [step(1, 'запрос в А', 'Система А', timeout=500, retry='auto', idem='key'),
             step(2, 'запрос в Б', 'Система Б', timeout=500, retry='auto', idem='key', dep=1)]},
  {'rule:generic_identifier_scope_ambiguity'})

]


def main():
    passed = 0
    for title, payload, expected in CASES:
        res = analyze(payload)
        got = {f'rule:{f["rule"]}' for f in res.get('findings', [])} | \
              {f'pat:{p["id"]}' for p in res.get('patterns', [])}
        missing = expected - got
        ok = not missing
        passed += ok
        mark = 'HIT ' if ok else 'MISS'
        print(f'  {mark} {title}')
        if missing:
            print(f'        не хватает: {", ".join(sorted(missing))}')
    pct = round(100 * passed / len(CASES))
    print(f'\nПокрытие: {passed}/{len(CASES)} = {pct}%')
    return pct


if __name__ == '__main__':
    main()
