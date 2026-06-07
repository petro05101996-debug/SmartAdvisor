#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Интеграционный инструктор v5.0.9 RU — production form coverage, guided UX
# Детерминированный rule-engine без LLM для проектирования сложных интеграций.
# Запуск: python integration_architect_pro.py
# Открыть: http://127.0.0.1:8110
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from html import escape
from pathlib import Path
from datetime import datetime
import sqlite3, uuid, json, re, zipfile, io, os

PORT = int(os.environ.get('PORT', '8110'))
HOST = os.environ.get('HOST', '0.0.0.0')
MAX_POST_BYTES = int(os.environ.get('MAX_POST_BYTES', str(2 * 1024 * 1024)))
APP_DIR = Path('.integration_architect_pro')
APP_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / 'architect.sqlite3'
OUT_DIR = Path('generated_integration_architect_reports')
OUT_DIR.mkdir(exist_ok=True)

QUESTIONS = [
('task','1. Тип задачи и контекст',[
 ('project_name','Название проекта','text','',None),
 ('task_type','Что проектируем?','select','e2e_chain',[
   ('new_from_scratch','Новая интеграция с нуля'),('add_to_existing','Дополнительная интеграция в существующий production-процесс'),
   ('e2e_chain','Сложная E2E-цепочка интеграций'),('replace_legacy','Замена старой интеграции'),('legacy_integration','Legacy-интеграция'),
   ('dwh_analytics','DWH/аналитика'),('external_partner','Интеграция внешнего партнёра'),('data_migration','Миграция данных'),
   ('event_domain','Событийная модель домена'),('problem_audit','Аудит проблемной интеграции'),('audit_existing_solution','Проверить существующее интеграционное решение')]),
 ('business_goal','Бизнес-цель','textarea','',None),
 ('criticality','Критичность','select','high',[('low','Низкая'),('medium','Средняя'),('high','Высокая'),('mission','Mission critical')])
]),
('business','1A. Бизнес-контекст и пользовательский сценарий',[
 ('business_situations','Типовые бизнес-ситуации','multi','application_or_order_creation,client_status_screen,external_api_dependency',[('client_status_screen','Клиентский экран статуса/результата'),('financial_operation','Финансовая операция/деньги'),('application_or_order_creation','Оформление заявки/заказа'),('multi_step_business_process','Многошаговый бизнес-процесс'),('highload_read','Частое чтение / горячий экран'),('highload_write_stream','Поток событий / highload-запись'),('reference_data','Справочники/мастер-данные'),('legacy_integration','Legacy/старый контур'),('dwh_reporting','DWH/отчётность'),('notification_flow','Уведомления'),('webhook_callback','Webhook/callback'),('external_api_dependency','Внешнее API/партнёр'),('data_synchronization','Синхронизация данных'),('distributed_transaction_saga','Распределённая операция с компенсациями'),('regulatory_process','Юридически/регуляторно значимый процесс'),('personal_data_exchange','ПДн/чувствительные данные'),('multi_source_aggregation','Агрегация из нескольких источников'),('customer_360','Карточка клиента 360 / Customer 360'),('api_composition','BFF/API composition для экрана'),('read_model','Read-model / только чтение'),('batch_processing','Batch/job/массовая обработка'),('near_real_time_decision','Near real-time решение'),('data_enrichment','Проверка/обогащение данных'),('one_source_many_consumers','Один источник — много потребителей'),('many_sources_one_consumer','Много источников — один потребитель'),('shared_topic_selective_consumer','Читать общий Kafka topic и фильтровать нужные события'),('peak_load_process','Пиковая нагрузка'),('unstable_external_provider','Нестабильный внешний поставщик'),('async_heavy_processing','Долгая обработка в фоне'),('exactly_once_required','Нужно практически ровно один раз'),('strict_ordering_required','Нужен строгий порядок'),('long_running_process','Долгий процесс'),('migration_or_strangler','Миграция/замена системы'),('existing_solution_audit','Проверка текущего решения')]),
 ('user_action','Что делает пользователь/инициатор','text','Клиент отправляет заявку и смотрит статус обработки',None),
 ('customer_visible','Результат видит клиент?','select','yes',[('yes','Да, клиентский сценарий'),('no','Нет, внутренний процесс'),('mixed','Частично')]),
 ('money_impact','Есть влияние на деньги/баланс/лимит?','select','no',[('no','Нет'),('indirect','Косвенно'),('yes','Да, напрямую')]),
 ('regulatory_impact','Есть юридический/регуляторный риск?','select','no',[('no','Нет'),('yes','Да'),('unknown','Неизвестно')]),
 ('read_frequency','Как часто читают результат','select','high',[('low','Редко'),('medium','Иногда'),('high','Часто'),('very_high','Очень часто / горячий экран')]),
 ('change_frequency','Как часто меняются данные','select','medium',[('rare','Редко'),('daily','Несколько раз в день'),('medium','Несколько раз в час'),('high','Часто'),('realtime','Почти в реальном времени')]),
 ('response_time_expectation','Ожидание по скорости для пользователя','select','under_1s',[('under_100ms','До 100 мс'),('under_300ms','До 300 мс'),('under_1s','До 1 сек'),('under_3s','До 3 сек'),('async_ok','Можно асинхронно')]),
 ('freshness_requirement','Допустимое устаревание данных','select','up_to_1m',[('strict','Нужны строго актуальные данные'),('up_to_5s','Можно до 5 секунд'),('up_to_1m','Можно до 1 минуты'),('up_to_15m','Можно до 15 минут'),('up_to_1h','Можно до 1 часа'),('daily','Достаточно данных за день')]),
 ('business_priority','Что важнее','select','balanced',[('speed','Быстрый ответ важнее небольшой задержки актуальности'),('freshness','Актуальность важнее скорости'),('balanced','Нужен баланс'),('unknown','Неизвестно')]),
 ('stale_data_impact','Что будет, если данные устареют','select','support',[('none','Почти ничего'),('support','Клиент/оператор будет путаться, нагрузка на поддержку'),('financial','Возможна финансовая ошибка'),('legal','Юридический/регуляторный риск')]),
 ('unavailable_behavior','Что делать при недоступности источника','select','show_stale',[('show_error','Показать ошибку'),('show_stale','Показать последний известный результат'),('queue_for_later','Поставить задачу в очередь'),('partial_response','Показать частичный ответ'),('block_process','Заблокировать процесс'),('manual_review','Передать в ручную обработку')]),
 ('external_dependency_stability','Стабильность внешних зависимостей','select','unknown',[('stable','Стабильные'),('unstable','Нестабильные/часто тормозят'),('limited','Есть лимиты/rate limit'),('unknown','Неизвестно')])
]),
('load','2. Нагрузка, SLA и консистентность',[
 ('load_profile','Профиль нагрузки','select','highload',[('low','Низкая нагрузка'),('medium','Средняя'),('highload','Highload'),('bursty','Пиковая/неровная'),('unknown','Неизвестно')]),
 ('rps','Ожидаемый RPS/TPS','text','500',None),
 ('peak_factor','Пиковый коэффициент','select','5',[('1','Нет пиков'),('2','x2'),('5','x5'),('10','x10+'),('unknown','Неизвестно')]),
 ('latency_sla','SLA ответа/результата','select','async_minutes',[('subsecond','<1 сек'),('seconds','1-5 сек'),('async_minutes','Асинхронно, минуты'),('hours','Часы'),('daily','Batch/day')]),
 ('consistency','Консистентность','select','eventual_ok',[('strong','Строгая консистентность'),('business_exactly_once','Exactly-once на бизнес-уровне'),('eventual_ok','Eventual consistency допустима'),('best_effort','Best effort')])
]),
('existing','3. Существующий процесс и ограничения',[
 ('existing_state','Состояние процесса','select','production',[('none','Процесса нет'),('partial','Частично есть'),('production','Работает в production'),('legacy','Только legacy'),('unknown','Неизвестно')]),
 ('change_policy','Что можно менять?','multi','add_api,add_event,add_outbox,add_status',[('no_changes','Нельзя менять вообще'),('read_only','Только читать'),('add_api','Добавить API'),('add_event','Добавить событие'),('add_outbox','Добавить Outbox'),('add_status','Добавить статус'),('change_db','Менять БД'),('change_core','Менять core flow'),('add_cdc','Добавить CDC')]),
 ('constraint_profile','Режим проектирования','select','balanced',[('ideal','Эталонная целевая архитектура'),('balanced','Баланс: надёжность + стоимость'),('pragmatic','Компромисс под ограничения'),('minimal_safe','Минимально безопасная доработка')]),
 ('budget_pressure','Бюджет/стоимость изменений','select','medium',[('low','Бюджет не является проблемой'),('medium','Бюджет ограничен'),('high','Сильно ограничен'),('extreme','Почти нет бюджета')]),
 ('deadline_pressure','Сроки','select','normal',[('normal','Обычные'),('tight','Сжатые'),('urgent','Очень срочно / production pain')]),
 ('new_service_policy','Можно ли добавлять новый сервис/микросервис','select','allowed',[('allowed','Можно'),('reuse_existing_runtime','Нельзя новый сервис, но можно job/модуль в существующем контуре'),('platform_only','Только через существующую платформенную команду/адаптер'),('forbidden','Нельзя')]),
 ('new_infra_policy','Можно ли добавлять новую инфраструктуру','select','existing_only',[('allowed','Можно'),('existing_only','Только уже имеющаяся инфраструктура'),('forbidden','Нельзя')]),
 ('source_change_policy','Можно ли менять source-систему','select','minimal_table_only',[('allowed','Можно менять код/БД'),('minimal_table_only','Только минимально: таблица/статус/outbox'),('api_only','Только API/контракт'),('read_only','Только читать'),('forbidden','Нельзя')]),
 ('risk_appetite','Допустимый остаточный риск','select','medium',[('low','Низкий: почти production-safe'),('medium','Средний: допускаются контролируемые риски'),('high','Высокий: временный компромисс допустим')]),
 ('compromise_comment','Ограничения/компромиссы словами','textarea','Например: новый сервис слишком дорогой; source менять нельзя; Kafka уже есть только в другом контуре; сроки 2 недели; нужен безопасный минимум.',None),
 ('existing_capabilities','Что уже есть?','multi','rest_api,status_model,audit,monitoring',[('rest_api','REST API'),('soap','SOAP'),('kafka','Kafka topic'),('queue','Очередь'),('outbox','Outbox'),('inbox','Inbox'),('batch','Batch export'),('cdc','CDC'),('dwh','DWH feed'),('status_model','Статусы'),('audit','Аудит'),('dlq','DLQ'),('monitoring','Мониторинг')]),
 ('compatibility','Совместимость','select','no_breaking',[('none','Не требуется'),('backward','Обратная совместимость'),('parallel','Parallel run'),('no_breaking','Нельзя ломать текущих потребителей'),('versioned','Версионирование контрактов')])
]),
('topology','4. Топология и управление цепочкой',[
 ('orchestration','Кто управляет цепочкой?','select','orchestrator',[('single','Один сервис'),('orchestrator','Orchestrator / Process Manager'),('choreography','Choreography через события'),('hybrid','Гибрид'),('bpm','BPM/workflow engine'),('external','Внешняя система'),('unknown','Не определено')]),
 ('chain_depth','Глубина/уровни цепочки','select','multi_level',[('single_level','Один уровень'),('multi_level','Многоуровневая цепочка'),('fanout','Fan-out: много параллельных подписчиков'),('fanout_fanin','Fan-out/Fan-in'),('unknown','Неизвестно')]),
 ('step_count','Количество шагов','select','8_plus',[('1','1'),('2_3','2-3'),('4_7','4-7'),('8_plus','8+'),('unknown','Неизвестно')]),
 ('failure_policy','Ошибка в середине цепочки','select','retry_compensate_manual',[('stop','Остановить'),('retry','Retry'),('compensate','Компенсация'),('partial','Частичный успех'),('manual','Manual recovery'),('ignore_non_critical','Игнорировать не критичный шаг'),('retry_compensate_manual','Retry → compensation → manual recovery')]),
 ('result_model','Как инициатор узнаёт результат?','select','tracking',[('sync','Синхронный финальный ответ'),('tracking','TrackingId + GET status'),('callback','Callback/Webhook'),('notification','Уведомление'),('report','Отчёт/витрина'),('not_needed','Не требуется')])
]),
('systems','5. Матрица систем',[
 ('source_system','Система-владелец операции','text','Сервис заявок',None),
 ('systems_matrix','Системы: name | role | owner | criticality | channel | blocking | sla','textarea','''Сервис скоринга | скоринг заявки | Команда рисков | critical | queue,rest | blocking | 5s
CRM | карточка клиента | Команда CRM | important | event,rest | non_blocking | 30s
Сервис уведомлений | уведомление клиента | Команда коммуникаций | non_critical | event | non_blocking | 1m
DWH | аналитика | Команда данных | important | cdc,etl | non_blocking | 15m''',None)
]),
('steps','6. Матрица шагов процесса',[
 ('main_entity','Основная сущность','text','LoanApplication',None),
 ('process_steps','Шаги: level | order | parent | step | system | channel | input | output | timeout | retry | compensation | blocking | owner','textarea','''0 | 1 | root | Создать заявку | Сервис заявок | rest | clientId,amount,termMonths,purpose | applicationId,status | 2s | no | none | blocking | Продуктовая команда
1 | 2 | 1 | Отправить на скоринг | Сервис скоринга | queue/rest | applicationId,clientData | decision,score | 5s | yes | mark SCORING_ERROR | blocking | Команда рисков
1 | 3 | 1 | Опубликовать статус | Брокер событий | kafka | applicationId,status | eventId | 1s | yes | retry outbox | blocking | Платформенная команда
2 | 4 | 3 | Обновить CRM | CRM | event | applicationId,status | crmStatus | 30s | yes | DLQ/manual | non_blocking | Команда CRM
2 | 5 | 3 | Уведомить клиента | Сервис уведомлений | event | applicationId,status | notificationId | 1m | yes | DLQ/manual | non_blocking | Команда коммуникаций
2 | 6 | 3 | Выгрузить в DWH | DWH | cdc/etl | application data | dwh record | 15m | yes | replay/reconciliation | non_blocking | Команда данных''',None),
 ('statuses','Статусы','textarea','CREATED, VALIDATED, SENT_TO_SCORING, APPROVED, REJECTED, SCORING_ERROR, CRM_UPDATED, NOTIFICATION_SENT, DWH_EXPORTED',None),
 ('final_statuses','Финальные бизнес-статусы','text','APPROVED, REJECTED, SCORING_ERROR',None)
]),
('data','7. Данные и БД',[
 ('fields','Поля: name:type|required|unique|indexed|sensitive','textarea','clientId:uuid|required|indexed|sensitive, amount:decimal|required, termMonths:int|required, purpose:string|required, idempotencyKey:string|unique, decision:string, rejectionReason:string, score:int',None),
 ('source_of_truth','Источник истины','select','own_db',[('own_db','Наша БД'),('external','Внешняя система'),('event_log','Event log'),('dwh','DWH'),('mixed','Разные источники'),('unclear','Не определён')]),
 ('ownership','Владение данными','select','field_level',[('single','Один владелец'),('field_level','По полям'),('multiple_writers','Несколько пишущих'),('external','Внешний владелец'),('unclear','Не определено')]),
 ('data_volume','Рост данных','select','large',[('small','<10ГБ/год'),('medium','10-100ГБ/год'),('large','100ГБ-1ТБ/год'),('very_large','>1ТБ/год')]),
 ('history','История','select','status_audit_attempts',[('none','Не нужна'),('status','Статусы'),('audit','Аудит'),('status_audit','Статусы + аудит'),('status_audit_attempts','Статусы + аудит + попытки'),('event_sourcing','Event Sourcing')]),
 ('retention','Retention','select','3_years',[('not_defined','Не определён'),('90_days','90 дней'),('1_year','1 год'),('3_years','3 года'),('5_years','5 лет'),('forever','Бессрочно')]),
 ('event_payload_intent','Что должен получить потребитель события','select','domain_fact',[('domain_fact','Факт изменения сущности'),('enriched_event','Одно обогащённое событие'),('snapshot_export','Готовый экспортный снапшот'),('unknown','Неизвестно')]),
 ('enrichment_required','Обогащение данных для события','select','none',[('none','Не требуется'),('optional','Опционально/справочно'),('required','Обязательно для публикации'),('critical','Критично юридически/финансово')]),
 ('enrichment_owner_service','Сервис-владелец дополнительных данных','text','',None),
 ('enrichment_consistency','Консистентность обогащения','select','unknown',[('as_of_change','Данные на момент изменения сущности'),('current_at_publish','Данные на момент публикации'),('best_effort','Best effort'),('unknown','Не определено')]),
 ('webhook_signature_required','Webhook: проверка подписи','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')]),
 ('webhook_raw_body_preserved','Webhook: raw body сохраняется для проверки подписи','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')]),
 ('webhook_timestamp_tolerance','Webhook: timestamp tolerance / защита от replay','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')]),
 ('webhook_secret_rotation','Webhook: ротация секрета','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')]),
 ('webhook_ack_sla_ms','Webhook: SLA быстрого ACK, мс','text','3000',None),
 ('webhook_provider_retry_policy_known','Webhook: известна политика retry провайдера','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')]),
 ('webhook_reconciliation_available','Webhook: доступна сверка с provider API','select','unknown',[('yes','Да'),('no','Нет'),('unknown','Неизвестно')])
]),
('delivery','8. Доставка, порядок, ошибки',[
 ('delivery','Гарантия доставки','select','business_exactly_once',[('best_effort','Best effort'),('at_least_once','At-least-once'),('business_exactly_once','Exactly-once на бизнес-уровне'),('strict','Строгая транзакционность')]),
 ('ordering','Порядок сообщений','select','per_entity',[('no','Не нужен'),('per_entity','По сущности'),('global','Глобальный'),('unknown','Неизвестно')]),
 ('replay','Replay','select','short',[('no','Нет'),('short','Короткий'),('long','Долгий'),('rebuild','Восстановление состояния'),('audit','Аудит')]),
 ('error_matrix','Ошибки: error | where | blocking | retry | after_retry | owner','textarea','''validation_error | API | blocking | no | reject request | Продуктовая команда
scoring_timeout | Сервис скоринга | blocking | yes | SCORING_ERROR + manual task | Команда рисков
crm_error | CRM | non_blocking | yes | DLQ/manual | Команда CRM
notification_error | Сервис уведомлений | non_blocking | yes | DLQ | Команда коммуникаций
dwh_export_error | DWH | non_blocking | yes | replay/reconciliation | Команда данных''',None),
 ('manual_recovery','Manual recovery','select','yes',[('no','Не нужно'),('yes','Нужно'),('critical','Только критичные')])
]),
('channels','9. Каналы и legacy',[
 ('allowed_channels','Допустимые каналы','multi','rest,kafka,queue,webhook,cdc,etl',[('rest','REST'),('grpc','gRPC'),('graphql','GraphQL/BFF'),('kafka','Kafka'),('queue','Queue'),('webhook','Webhook'),('sftp','SFTP/Object Storage'),('soap','SOAP'),('cdc','CDC'),('etl','ETL/ELT')]),
 ('forbidden_channels','Запрещённые каналы','multi','direct_db_write',[('direct_db_write','Прямая запись в чужую БД'),('direct_db_read','Прямое чтение чужой БД'),('new_infra','Новая инфраструктура'),('async','Асинхронщина'),('file','Файлы'),('public_api','Публичный API')]),
 ('legacy','Legacy-ограничения','select','none',[('none','Нет'),('soap_only','Только SOAP'),('file_only','Только файлы'),('db_replica_only','Только read replica'),('no_changes','Систему нельзя менять')]),
 ('dwh','DWH/аналитика','select','near_realtime',[('no','Нет'),('batch','Batch'),('near_realtime','Near-real-time'),('regulatory','Регуляторная отчётность')]),
 ('kafka_topology','Kafka-топология для события','select','multi_topic_ok',[('no_kafka','Kafka не используется'),('single_topic_only','Только один Kafka topic/контур'),('raw_enriched_topics','Можно raw + enriched topics'),('multi_topic_ok','Можно несколько топиков'),('unknown','Не определено')]),
 ('source_has_kafka_infra','Kafka-инфраструктура есть в source-сервисе?','select','unknown',[('yes','Да'),('no','Нет'),('adapter_only','Можно только внешний publisher/adapter'),('unknown','Неизвестно')]),
 ('enrichment_channel','Как получать данные обогащения','select','none',[('none','Не требуется'),('rest','REST-сервис'),('local_snapshot','Локальный snapshot в source'),('event','Событие/CDC от владельца данных'),('manual','Ручной ввод/оператор'),('unknown','Не определено')])
]),
('audit','10. Аудит текущего решения',[
 ('audit_depth','Глубина аудита','select','normal',[('quick','Быстрый аудит'),('normal','Нормальный аудит'),('deep','Глубокий аудит')]),
 ('current_solution_description','Краткое описание текущего решения','textarea','Фронтенд вызывает API заказов; API заказов синхронно вызывает Scoring; сохраняет статус в БД; публикует событие в Kafka; consumer обновляет CRM и уведомления; DWH забирает данные через CDC.',None),
 ('current_systems_matrix','Текущие системы: system_id | name | type | owner | criticality | can_change | source_of_truth','textarea','''frontend | Фронтенд | frontend | Продуктовая команда | important | yes | no
order_api | API заказов | service | Продуктовая команда | critical | yes | yes
scoring | Сервис скоринга | service | Команда рисков | critical | no | no
kafka | Kafka | broker | Платформенная команда | critical | limited | no
crm | CRM | external_system | Команда CRM | important | limited | no
dwh | DWH | analytics | Команда данных | important | no | no''',None),
 ('current_integration_matrix','Текущие связи: from | to | channel | mode | blocking | data | timeout | retry | retry_limit | dlq | idempotency | auth | owner','textarea','''frontend | order_api | REST | sync | yes | application_request | 3s | no | 0 | no | yes | user_token | Продуктовая команда
order_api | scoring | REST | sync | yes | application_data | 5s | yes | 3 | no | no | mTLS | Команда рисков
order_api | kafka | Kafka | async | no | ApplicationStatusChanged | n/a | yes | 10 | no | no | service_auth | Платформенная команда
kafka_consumer | crm | REST | async | no | application_status | 10s | yes | 3 | no | no | service_auth | Команда CRM
order_db | dwh | CDC | async | no | application_data | 15m | yes | 5 | no | yes | service_auth | Команда данных''',None),
 ('current_process_steps','Текущие шаги: level | parent | order | step | system | target | channel | blocking | success_status | error_status | compensation | manual_recovery','textarea','''1 | root | 1 | Создать заявку | frontend | order_api | REST | yes | CREATED | VALIDATION_ERROR | none | no
1 | root | 2 | Выполнить скоринг | order_api | scoring | REST | yes | APPROVED/REJECTED | SCORING_ERROR | mark_error | yes
1 | root | 3 | Опубликовать статус event | order_api | kafka | Kafka | no | EVENT_SENT | EVENT_LOST | retry | yes
2 | 3 | 4 | Обновить CRM | kafka_consumer | crm | REST | no | CRM_UPDATED | CRM_ERROR | dlq/manual | yes
2 | 3 | 5 | Выгрузить в DWH | order_db | dwh | CDC | no | DWH_EXPORTED | DWH_ERROR | reconciliation | yes''',None),
 ('current_error_matrix','Текущие ошибки: error | where | type | blocking | retry | after_retry | dlq | owner | alert','textarea','''scoring_timeout | scoring | technical | yes | yes | manual_task | no | Команда рисков | yes
kafka_publish_error | order_api | technical | no | yes | log_only | no | Платформенная команда | no
crm_error | crm | technical | no | yes | log_only | no | Команда CRM | no
dwh_lag | dwh | data | no | yes | reconciliation | no | Команда данных | yes''',None),
 ('current_problem_matrix','Наблюдаемые проблемы: problem | where | frequency | impact | current_workaround','textarea','''stuck_status | scoring | daily | заявки зависают в обработке | support ticket
duplicates | crm | weekly | дубли статусов в CRM | manual cleanup
lost_event | order_api_to_kafka | monthly | DWH/CRM не видят часть изменений | manual reload
slow_response | frontend | daily | плохой UX при долгом скоринге | retry by user''',None),
 ('current_controls','Какие контроли уже есть?','multi','timeout,retry,monitoring',[('timeout','Timeout'),('retry','Retry'),('retry_backoff','Retry backoff'),('dlq','DLQ'),('outbox','Outbox'),('inbox','Inbox/idempotency'),('correlation_id','CorrelationId'),('tracing','Tracing'),('business_metrics','Business metrics'),('schema_registry','Schema Registry'),('contract_tests','Contract tests'),('rate_limit','Rate limit'),('circuit_breaker','Circuit breaker'),('reconciliation','Reconciliation'),('manual_recovery','Manual recovery dashboard')]),
 ('change_budget','Бюджет изменений','select','medium',[('minimal','Только минимальные правки'),('medium','Можно добавлять таблицы/контроли'),('large','Можно менять процесс'),('full_rebuild','Можно перепроектировать полностью')]),
 ('allowed_refactoring','Допустимый уровень рефакторинга','select','add_tables_controls',[('settings_only','Только настройки'),('contracts','Контракты и настройки'),('add_tables_controls','Добавлять таблицы/контроли'),('add_broker_queue','Добавлять очередь/Kafka'),('change_process','Менять процесс'),('full_rebuild','Полная переработка')])
]),

('target_integrations','11. Целевая матрица интеграций',[
 ('target_integration_matrix','Целевые связи: from | to | channel | mode | trigger | data | contract | timeout | retry | retry_limit | dlq | idempotency | auth | rate_limit | owner','textarea',"""API/Process Manager | Scoring | REST | sync | application_created | scoring_request | POST /score/v1/decision | 3s | yes/backoff | 3 | no | idempotencyKey | mTLS/JWT | 100 rps | Команда рисков
API/Process Manager | Kafka | Kafka | async | status_changed | status_event | ApplicationStatusChanged.v1 | 1s | yes | 10 | yes | eventId | SASL/mTLS | по квоте topic | Платформа
Kafka Consumer | CRM | REST | async | status_event | crm_update | PUT /crm/v1/application-status | 5s | yes/backoff | 5 | yes | eventId+aggregateVersion | mTLS | 50 rps | CRM team""",None),
 ('process_flow_matrix','Переходы процесса: step_id | parent_id | condition | action | system | success_next | failure_next | timeout_next | compensation | manual_recovery','textarea',"""S1 | root | request accepted | создать заявку и status=NEW | API | S2 | E_VALIDATION | E_TIMEOUT | none | no
S2 | S1 | scoring required | вызвать скоринг | Process Manager | S3 | E_SCORING | E_TIMEOUT | set ERROR/RETRY | yes
S3 | S2 | approved | опубликовать событие статуса | Publisher | END | E_PUBLISH | E_RETRY | retry/dlq | yes""",None)
]),
('contracts_rules','12. Контракты и бизнес-правила',[
 ('contract_matrix','Контракты: type | name | producer | consumer | endpoint_or_topic | method_or_key | required_fields | optional_fields | errors | version | compatibility','textarea',"""API | CreateApplication | Frontend | API | /application/v1/create | POST | clientId,amount,term,idempotencyKey | comment | 400,409,422,500 | v1 | backward
EVENT | ApplicationStatusChanged | API/Publisher | CRM,DWH | application.status.changed.v1 | aggregateId | eventId,aggregateId,status,aggregateVersion,occurredAt | reason,source | schema_validation_error | v1 | backward
API | EnrichContract | Publisher | Enrichment Service | /enrichment/v1/contracts/{id} | GET | contractId,asOfVersion | customerSegment | 404,429,500 | v1 | backward""",None),
 ('business_rules_matrix','Бизнес-правила: rule_id | condition | action | affected_step | owner | error_if_failed','textarea',"""BR1 | сумма > лимита | отправить на ручную проверку | S2 | Бизнес-владелец | MANUAL_REVIEW_REQUIRED
BR2 | договор закрыт | не публиковать событие обновления | S3 | Договорный сервис | CONTRACT_CLOSED
BR3 | пришло старое событие version ниже текущей | игнорировать и записать аудит | Consumer | Target owner | OUTDATED_EVENT""",None)
]),
('capacity_ops','13. Capacity, наблюдаемость и эксплуатация',[
 ('capacity_matrix','Capacity: flow | avg_rps | peak_rps | avg_payload_kb | max_payload_kb | events_per_day | useful_filter_ratio | partitions | consumers | db_write_tps | max_lag | replay_volume | backfill_window | external_rate_limit','textarea',"""status_events | 500 | 2500 | 5 | 50 | 10000000 | 100% | 12 | 6 | 300 | 60s | 1 day | 24h | none
shared_topic_filter | 2000 | 10000 | 8 | 100 | 50000000 | 0.2% | 24 | 12 | 50 | 300s | 6h | 12h | target API 100 rps""",None),
 ('observability_matrix','Наблюдаемость: metric | where | threshold | alert | owner | dashboard','textarea',"""consumer_lag | Kafka consumer group | > 10000 events or > 5m | yes | Platform | Kafka dashboard
dlq_size | DLQ topic | > 100 messages | yes | Consumer owner | DLQ dashboard
stuck_status_count | Process Manager | > 0 for 15m | yes | Backend | Operations dashboard
reconciliation_diff | DWH reconciliation | > 0 critical records | yes | Data team | DWH quality dashboard""",None)
]),
('quality_rollout','14. Rollout, миграция, качество данных',[
 ('rollout_migration_matrix','Внедрение/миграция: phase | scope | strategy | rollback | backfill | parallel_compare | go_no_go | owner','textarea',"""P1 | один consumer/один тип события | feature toggle | выключить consumer, оставить старый поток | no | compare counts | errors < 1%, lag < 1m | Backend
P2 | все потребители | phased rollout | откат toggle + replay | last 24h | compare statuses | no lost events, no duplicates | Platform
P3 | DWH витрина | parallel run | вернуться на старую витрину | 30 days | row count + checksum | diff=0 critical | Data team""",None),
 ('data_quality_lineage_matrix','Качество/lineage: data_object | source | target | check | frequency | evidence | owner','textarea',"""ApplicationStatus | Order DB | Kafka/CRM/DWH | count by status + checksum by aggregateId | hourly | reconciliation_runs | Data owner
ContractEvent | Contract Service | Target Service | aggregateVersion monotonic, required fields not null | each batch/event | validation log | Contract team
CustomerCard | CRM+ABS+KYC | BFF Read Model | freshness per block, partial response flag | realtime | dashboard | App team""",None)
]),
('security','15. Безопасность и внедрение',[
 ('sensitivity','Чувствительность данных','select','pii',[('public','Публичные'),('internal','Внутренние'),('pii','ПДн'),('financial','Финансовая/коммерческая тайна'),('high','Критичные')]),
 ('auth','Авторизация','select','service_and_user',[('none','Не определена'),('service','Service-to-service'),('user','Пользовательская'),('service_and_user','Пользовательская + service-to-service'),('partner','Партнёрская')]),
 ('availability','Доступность','select','ha',[('basic','Базовая'),('ha','HA'),('multi_az','Multi-AZ'),('dr','DR')]),
 ('observability','Наблюдаемость','select','full',[('basic','Логи'),('standard','Логи + метрики + алерты'),('full','Логи + метрики + трейсы + бизнес-аудит'),('regulated','Полный audit/security monitoring')]),
 ('report_audience','Для кого сформировать отчёт','select','analyst',[('business','Для бизнеса'),('analyst','Для системного аналитика'),('developer','Для разработчика'),('architect','Для архитектора'),('all','Полный отчёт для всех')]),
 ('payload_kb','Средний размер сообщения, KB','text','5',None),
 ('retention_days','Retention событий/истории, дней','text','30',None),
 ('target_lag_seconds','Допустимый lag/задержка обработки, секунд','text','60',None),
 ('rollout','Выкат','select','phased',[('big_bang','Big bang'),('phased','Поэтапно'),('feature_toggle','Feature toggle'),('parallel','Parallel run'),('canary','Canary')]),
 ('testing','Тестирование','select','full',[('basic','Unit'),('integration','Integration'),('contract','Contract'),('full','Unit + integration + contract + e2e + load'),('regulated','Full + security + failover')])
])]

# ---------- persistence ----------
def init_db():
    con=sqlite3.connect(DB_PATH); cur=con.cursor()
    cur.execute('create table if not exists projects(id text primary key,name text,created_at text,updated_at text)')
    cur.execute('create table if not exists runs(id text primary key,project_id text,version int,form text,result text,markdown text,score int,recommended text,created_at text)')
    con.commit(); con.close()

def save_run(form,result):
    init_db(); con=sqlite3.connect(DB_PATH); cur=con.cursor(); now=datetime.now().isoformat(timespec='seconds')
    pid=form.get('project_id') or str(uuid.uuid4()); name=form.get('project_name') or 'Без названия'
    cur.execute('select id from projects where id=?',(pid,)); exists=cur.fetchone()
    if exists:
        cur.execute('select coalesce(max(version),0)+1 from runs where project_id=?',(pid,)); ver=cur.fetchone()[0]
        cur.execute('update projects set name=?,updated_at=? where id=?',(name,now,pid))
    else:
        ver=1; cur.execute('insert into projects values(?,?,?,?)',(pid,name,now,now))
    rid=str(uuid.uuid4())
    cur.execute('insert into runs values(?,?,?,?,?,?,?,?,?)',(rid,pid,ver,json.dumps(form,ensure_ascii=False),json.dumps({k:v for k,v in result.items() if k!='markdown'},ensure_ascii=False,default=list),result['markdown'],result['readiness']['score'],ru_label(result['recommended']['name']),now))
    con.commit(); con.close(); return pid,rid,ver

def list_runs(limit=10):
    init_db(); con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; cur=con.cursor()
    cur.execute('select r.id,r.version,p.name,r.score,r.recommended,r.created_at from runs r join projects p on p.id=r.project_id order by r.created_at desc limit ?',(limit,))
    rows=[dict(r) for r in cur.fetchall()]; con.close(); return rows

def get_run(rid):
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; cur=con.cursor(); cur.execute('select * from runs where id=?',(rid,)); row=cur.fetchone(); con.close(); return dict(row) if row else None

# ---------- helpers ----------
def split_csv(x): return [i.strip() for i in (x or '').replace('\n',',').split(',') if i.strip()]
def snake(x):
    x=re.sub(r'([a-z0-9])([A-Z])',r'\1_\2',(x or '').strip())
    x=re.sub(r'[^a-zA-Z0-9]+','_',x); return re.sub(r'_+','_',x).strip('_').lower() or 'field'
def norm_type(t):
    return {'str':'text','string':'text','text':'text','uuid':'uuid','int':'integer','integer':'integer','long':'bigint','decimal':'numeric(18,2)','money':'numeric(18,2)','bool':'boolean','boolean':'boolean','date':'date','datetime':'timestamp','timestamp':'timestamp','json':'jsonb','jsonb':'jsonb'}.get((t or '').lower().strip(),'text')
def parse_fields(raw):
    out=[]; seen={}
    for item in split_csv(raw):
        parts=[p.strip() for p in item.split('|')]; first=parts[0]
        name,typ=(first.split(':',1)+['string'])[:2] if ':' in first else (first,'string')
        flags=set(p.lower() for p in parts[1:]); key=snake(name)
        f={'name':key,'original':name,'type':norm_type(typ),'required':'required' in flags or 'not_null' in flags,'unique':'unique' in flags,'indexed':'indexed' in flags or 'index' in flags,'sensitive':'sensitive' in flags or 'pii' in flags}
        if key in seen:
            for b in ['required','unique','indexed','sensitive']: seen[key][b]=seen[key][b] or f[b]
        else: seen[key]=f; out.append(f)
    return out
def parse_matrix(raw, cols):
    rows=[]
    normalized_cols=[c.strip().lower() for c in cols]
    ru_header_tokens={
        'name','role','owner','criticality','channel','blocking','sla','level','order','parent','step','system','input','output','timeout','retry','compensation',
        'error','where','after_retry','from','to','mode','data','retry_limit','dlq','idempotency','auth','system_id','type','can_change','source_of_truth',
        'target','success_status','error_status','manual_recovery','trigger','contract','rate_limit','step_id','parent_id','condition','action','success_next','failure_next','timeout_next','rule_id','affected_step','avg_rps','peak_rps','avg_payload_kb','max_payload_kb','events_per_day','useful_filter_ratio','partitions','consumers','db_write_tps','max_lag','replay_volume','backfill_window','external_rate_limit','metric','threshold','alert','dashboard','phase','scope','strategy','rollback','backfill','parallel_compare','go_no_go','data_object','check','frequency','evidence',
        'название','роль','владелец','критичность','канал','блокирующий','шаг','система','вход','выход','таймаут','повтор','компенсация','ошибка','где'
    }
    for line in (raw or '').splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        vals=[v.strip() for v in line.split('|')]
        normalized_vals=[v.strip().lower() for v in vals]
        # UX-friendly: пользователь часто копирует подсказку вместе с заголовком таблицы.
        # Заголовок не должен попадать в модель как реальный шаг/система и ломать parent/reference checks.
        if normalized_vals[:len(normalized_cols)] == normalized_cols[:len(normalized_vals)]:
            continue
        header_like=sum(1 for v in normalized_vals if v in ru_header_tokens)
        if vals and header_like >= max(2, min(4, len(vals))):
            continue
        rows.append({c:(vals[i] if i<len(vals) else '') for i,c in enumerate(cols)})
    return rows
def allowed(form, ch): return ch in form.get('allowed_channels',[]) and ch not in form.get('forbidden_channels',[])
def bullet(items): return '\n'.join('- '+str(x) for x in (items or ['Не указано']))+'\n'
def numbered(items): return '\n'.join(f'{i}. {x}' for i,x in enumerate((items or ['Не указано']),1))+'\n'



# ---------- user-facing terminology helpers ----------
TERM_EXPLANATIONS_RU = [
    ('async', 'асинхронно/в фоне'),
    ('sync', 'синхронно/с ожиданием ответа'),
    ('recovery', 'восстановление после ошибки'),
    ('policy', 'правило обработки'),
    ('status', 'состояние процесса'),
    ('CRM', 'система работы с клиентами'),
    ('DB', 'база данных'),
    ('Mermaid', 'текстовое описание диаграммы'),
    ('happy path', 'успешный основной сценарий'),
    ('hot screen', 'часто открываемый экран'),
    ('late data', 'данные, пришедшие с задержкой'),
    ('REST API', 'синхронный HTTP-вызов сервиса'),
    ('OpenAPI', 'описание REST-контракта'),
    ('AsyncAPI', 'описание событийного контракта'),
    ('API Gateway', 'единая входная точка для API'),
    ('BFF', 'backend для конкретного экрана/клиента'),
    ('REST', 'синхронный HTTP-вызов'),
    ('HTTP', 'протокол веб-вызова'),
    ('gRPC', 'быстрый бинарный межсервисный вызов'),
    ('API', 'интерфейс вызова сервиса'),
    ('Kafka', 'брокер событий/поток сообщений'),
    ('RabbitMQ', 'очередь сообщений'),
    ('queue', 'очередь для фоновой обработки'),
    ('topic', 'канал событий в брокере'),
    ('producer', 'сервис, который публикует событие'),
    ('consumer', 'сервис, который читает событие'),
    ('event', 'событие о факте изменения'),
    ('eventId', 'уникальный идентификатор события'),
    ('correlationId', 'идентификатор для связи запросов в цепочке'),
    ('trackingId', 'идентификатор для проверки статуса'),
    ('idempotencyKey', 'ключ защиты от дублей операции'),
    ('idempotency', 'защита от повторного выполнения'),
    ('payload', 'тело запроса/сообщения с данными'),
    ('schema', 'структура данных/контракта'),
    ('source of truth', 'главный источник правильных данных'),
    ('source', 'система-источник'),
    ('target', 'система-получатель'),
    ('worker', 'фоновый обработчик'),
    ('callback', 'обратный вызов от внешней системы'),
    ('webhook', 'входящий callback по HTTP'),
    ('retry storm', 'лавина повторных попыток'),
    ('retry', 'повторная попытка'),
    ('timeout', 'лимит ожидания ответа'),
    ('deadline', 'общий лимит времени на цепочку'),
    ('fallback', 'запасной путь при сбое'),
    ('backoff', 'увеличение паузы между повторами'),
    ('jitter', 'случайная добавка к паузе retry'),
    ('circuit breaker', 'защита от вызова падающей зависимости'),
    ('bulkhead', 'изоляция ресурсов от каскадного сбоя'),
    ('DLQ', 'очередь проблемных сообщений'),
    ('replay', 'повторное проигрывание событий'),
    ('reprocess', 'повторная обработка после ошибки'),
    ('reconciliation', 'сверка данных между системами'),
    ('compensation', 'компенсирующее действие/откат'),
    ('manual recovery', 'ручное восстановление'),
    ('fan-out', 'одно событие уходит многим получателям'),
    ('fan-in', 'сбор ответа из нескольких источников'),
    ('fork', 'разделение процесса на ветки'),
    ('join', 'объединение веток процесса'),
    ('DWH', 'хранилище данных для аналитики'),
    ('CDC', 'чтение изменений из БД'),
    ('batch', 'пакетная обработка по расписанию'),
    ('ETL', 'загрузка и преобразование данных'),
    ('ELT', 'загрузка данных с преобразованием в хранилище'),
    ('SFTP', 'безопасная передача файлов'),
    ('Saga', 'долгий процесс с компенсациями'),
    ('CQRS', 'разделение записи и чтения'),
    ('Outbox', 'таблица надёжной публикации событий'),
    ('Inbox', 'учёт обработанных входящих событий'),
    ('read model', 'модель данных для быстрого чтения'),
    ('state machine', 'модель статусов и переходов'),
    ('BPM', 'движок бизнес-процессов'),
    ('workflow', 'управляемый процесс шагов'),
    ('highload', 'высокая нагрузка'),
    ('rollback', 'откат изменений'),
    ('feature toggle', 'переключатель включения функции'),
    ('canary', 'пилотное включение на малую долю трафика'),
    ('monitoring', 'наблюдение за метриками'),
    ('alert', 'сигнал о проблеме'),
    ('dashboard', 'экран метрик'),
    ('audit', 'журнал значимых действий'),
    ('lineage', 'происхождение и путь данных'),
    ('late data', 'данные, пришедшие с задержкой'),
    ('partial response', 'частичный ответ'),
    ('SLA', 'договорённый уровень сервиса'),
    ('SLO', 'целевой уровень сервиса'),
    ('p99', '99-й перцентиль времени ответа'),
    ('owner', 'ответственный владелец'),
]

def explain_english_terms_ru_text(s):
    """Add short Russian explanations after English technical terms in user-facing text."""
    if not s:
        return s
    out = str(s)
    # Do not touch fenced code blocks; diagrams and examples should stay valid.
    parts = re.split(r'(```.*?```)', out, flags=re.S)
    def repl_segment(seg):
        for term, meaning in TERM_EXPLANATIONS_RU:
            pattern = r'(?<![A-Za-z0-9_/.-])' + re.escape(term) + r'(?![A-Za-z0-9_/-])'
            def _repl(m):
                end = m.end()
                # Already explained: "term (...)".
                if seg[end:end+2] == ' (':
                    return m.group(0)
                return f"{m.group(0)} ({meaning})"
            seg = re.sub(pattern, _repl, seg)
        return seg
    return ''.join(part if part.startswith('```') else repl_segment(part) for part in parts)

def explain_english_terms_ru_html_fragment(s):
    """Add explanations to visible HTML fragments without modifying tags/attributes."""
    if not s:
        return s
    parts = re.split(r'(<[^>]+>)', str(s))
    return ''.join(part if part.startswith('<') else explain_english_terms_ru_text(part) for part in parts)

def terminology_glossary_html():
    items = [
        ('worker', 'фоновый обработчик'),
        ('callback / webhook', 'обратный вызов от внешней системы'),
        ('retry', 'повторная попытка'),
        ('DLQ', 'очередь проблемных сообщений'),
        ('Kafka', 'брокер событий'),
        ('DWH', 'хранилище аналитических данных'),
        ('idempotencyKey', 'ключ защиты от дублей'),
        ('correlationId', 'идентификатор связи запросов'),
        ('trackingId', 'идентификатор проверки статуса'),
        ('fan-out / fan-in', 'разветвление / сбор из нескольких источников'),
        ('reconciliation', 'сверка данных'),
        ('compensation', 'компенсирующий откат'),
    ]
    chips=''.join(f"<span class='term-chip'><b>{escape(k)}</b> ({escape(v)})</span>" for k,v in items)
    return "<div class='term-glossary'><b>Подсказка по английским терминам:</b><div class='term-chip-row'>" + chips + "</div></div>"


# ---------- guided process graph / readable report helpers ----------
def safe_json_loads(raw, default=None):
    try:
        if not raw: return default
        return json.loads(raw)
    except Exception:
        return default

def extract_process_graph(form, ctx=None):
    """Return a normalized process graph built by the guided UI or inferred from process_steps.
    The graph model is intentionally generic: it supports sequential, parallel, conditional,
    cyclic, fan-out/fan-in, wait callback/event, compensation and reprocess paths.
    """
    raw = safe_json_loads(form.get('process_graph_json'), None)
    if isinstance(raw, dict) and raw.get('nodes'):
        nodes = raw.get('nodes') or []
        edges = raw.get('edges') or []
    else:
        steps = list((ctx or {}).get('steps') or [])
        nodes=[]; edges=[]
        for i, st in enumerate(steps, 1):
            action = st.get('step') or st.get('action') or f'Шаг {i}'
            node_type = 'rest_call'
            ch = str(st.get('channel','')).lower()
            low = (str(action)+' '+str(st.get('compensation',''))).lower()
            if 'kafka' in ch or 'event' in low: node_type='publish_event' if 'publish' in low or 'публи' in low else 'consume_event'
            if 'webhook' in ch or 'callback' in low: node_type='wait_callback'
            if 'dwh' in ch or 'cdc' in ch: node_type='dwh_export'
            if any(x in low for x in ['retry','повтор']): node_type='retry_loop'
            if any(x in low for x in ['reconciliation','сверк']): node_type='reconciliation'
            nodes.append({'id':f'S{i}','title':action,'type':node_type,'system_id':st.get('system') or 'System','channel':st.get('channel') or 'Unknown','user_waits':st.get('blocking')=='blocking','retry_policy':st.get('retry') or '', 'error_behavior': st.get('compensation') or '', 'status_after_success': st.get('output') or '', 'status_after_error':'ERROR','owner':st.get('owner') or ''})
            if i>1:
                edges.append({'from_node_id':f'S{i-1}','to_node_id':f'S{i}','condition':'success','transition_type':'success','is_blocking':st.get('blocking')=='blocking'})
    # Normalize common fields
    nn=[]
    for i,n in enumerate(nodes,1):
        if not isinstance(n, dict): continue
        nn.append({
          'id': str(n.get('id') or f'S{i}'),
          'title': str(n.get('title') or n.get('action') or f'Шаг {i}'),
          'type': str(n.get('type') or 'step'),
          'system_id': str(n.get('system_id') or n.get('system') or n.get('actor') or 'System'),
          'target_system_id': str(n.get('target_system_id') or n.get('target') or ''),
          'channel': str(n.get('channel') or 'Unknown'),
          'user_waits': bool(n.get('user_waits')) or str(n.get('wait','')).lower() in ['да','yes','true','blocking'],
          'retry_policy': str(n.get('retry_policy') or n.get('retry') or ''),
          'error_behavior': str(n.get('error_behavior') or n.get('error') or ''),
          'status_after_success': str(n.get('status_after_success') or n.get('success_status') or ''),
          'status_after_error': str(n.get('status_after_error') or n.get('error_status') or ''),
          'idempotency_required': bool(n.get('idempotency_required')) or 'idempot' in str(n.get('dedup','')).lower() or 'dedup' in str(n.get('dedup','')).lower(),
          'audit_required': bool(n.get('audit_required')),
          'owner': str(n.get('owner') or ''),
          'sla': str(n.get('sla') or n.get('timeout') or ''),
          'risk_level': str(n.get('risk_level') or ''),
        })
    ee=[]
    for e in edges:
        if not isinstance(e, dict): continue
        ee.append({
          'from_node_id': str(e.get('from_node_id') or e.get('from') or ''),
          'to_node_id': str(e.get('to_node_id') or e.get('to') or ''),
          'condition': str(e.get('condition') or ''),
          'transition_type': str(e.get('transition_type') or e.get('type') or 'success'),
          'is_blocking': bool(e.get('is_blocking')),
        })
    return {'nodes':nn,'edges':ee,'meta': safe_json_loads(form.get('process_graph_meta'), {}) or {}}

def graph_capabilities(graph):
    nodes = graph.get('nodes') or []
    edges = graph.get('edges') or []
    types = {str(n.get('type','')).lower() for n in nodes}
    edge_types = {str(e.get('transition_type','')).lower() for e in edges}
    titles = ' '.join(n.get('title','') for n in nodes).lower()
    caps={
      'sequential': len(nodes) >= 2,
      'parallel': bool(types & {'parallel','parallel_start','parallel_join'} or edge_types & {'parallel_start','parallel_join'} or any(x in titles for x in ['параллел','parallel','fan-out','fanout'])),
      'conditional': bool(edge_types & {'business_error','technical_error','timeout','fallback'} or any(x in titles for x in ['если ', 'услов', 'approved', 'rejected', 'timeout'])),
      'loops': bool(types & {'retry_loop','polling_loop','reconciliation'} or edge_types & {'retry','reprocess'} or any(x in titles for x in ['retry','повтор','polling','reconciliation','сверк','цикл'])),
      'fanout': bool(types & {'fan_out','publish_event'} and len([n for n in nodes if 'consumer' in n.get('title','').lower() or 'consumer' in n.get('system_id','').lower()])>1 or 'fan-out' in titles or 'много потреб' in titles),
      'fanin': bool(types & {'fan_in','aggregation'} or any(x in titles for x in ['fan-in','агрегац','нескольких источников','abs','kyc'])),
      'wait': bool(types & {'wait_event','wait_callback'} or any(x in titles for x in ['wait','callback','webhook','ждём','ожид'])),
      'compensation': bool(types & {'compensation'} or edge_types & {'compensation'} or any(x in titles for x in ['compensation','компенс','откат','резерв'])),
      'manual': bool(types & {'manual_task'} or any(x in titles for x in ['manual','ручн'])),
      'reprocess': bool(types & {'reprocess'} or edge_types & {'reprocess'} or any(x in titles for x in ['dlq','reprocess','переобработ'])),
    }
    return caps

def human_node_type(tp):
    m={
      'api_request':'принять запрос', 'validation':'проверить данные', 'persist_operation':'сохранить операцию', 'rest_call':'вызвать сервис',
      'publish_event':'опубликовать событие', 'consume_event':'обработать событие', 'queue_task':'поставить задачу в очередь',
      'webhook_receive':'принять webhook', 'wait_event':'дождаться события', 'wait_callback':'дождаться callback/webhook',
      'manual_task':'ручная проверка/восстановление', 'dwh_export':'выгрузка в DWH', 'notification':'уведомление', 'enrichment':'обогащение данных',
      'decision':'решение/ветвление', 'retry_loop':'цикл retry', 'polling_loop':'цикл polling', 'reconciliation':'сверка/reconciliation',
      'compensation':'компенсация/откат', 'reprocess':'повторная обработка', 'end_success':'успешный финал', 'end_failure':'ошибочный финал'
    }
    return m.get(str(tp), str(tp or 'шаг процесса'))


def graph_mermaid_flow(graph):
    """Build a readable flowchart from the guided process graph for the main report."""
    nodes = graph.get('nodes') or []
    edges = graph.get('edges') or []
    if not nodes:
        return ''
    def mid(x):
        return re.sub(r'[^A-Za-z0-9_]', '_', str(x or 'N')) or 'N'
    def label(x, limit=60):
        val = re.sub(r'[\[\]{}<>|`]', ' ', str(x or '')).strip()
        return (val[:limit] + '…') if len(val) > limit else val
    out = ['flowchart LR']
    for n in nodes:
        nid = mid(n.get('id'))
        title = label(n.get('title') or human_node_type(n.get('type')))
        tp = n.get('type') or 'step'
        system = label(n.get('system_id') or 'System', 32)
        text = f"{title}<br/><small>{system} · {human_node_type(tp)}</small>"
        if tp in ['retry_loop','polling_loop','reconciliation']:
            out.append(f'  {nid}{{"{text}"}}')
        elif tp in ['parallel_start','parallel_join','fan_in','decision']:
            out.append(f'  {nid}{{"{text}"}}')
        elif tp in ['compensation','manual_task','reprocess']:
            out.append(f'  {nid}[["{text}"]]')
        else:
            out.append(f'  {nid}["{text}"]')
    if edges:
        for e in edges:
            a, b = mid(e.get('from_node_id')), mid(e.get('to_node_id'))
            if not a or not b: continue
            et = label(e.get('transition_type') or e.get('condition') or 'next', 24)
            out.append(f'  {a} -->|{et}| {b}')
    else:
        for i in range(len(nodes)-1):
            out.append(f"  {mid(nodes[i].get('id'))} -->|success| {mid(nodes[i+1].get('id'))}")
    return '\n'.join(out)

def readable_report_intro(form, ctx, traits, rec, anti, ready, advanced=None):
    """Human-first report front matter.

    This section is intentionally written as a practical architectural explanation,
    not as a dump of patterns. It must answer: what to do, why, constraints,
    risks, and next steps in normal Russian.
    """
    graph = extract_process_graph(form, ctx)
    caps = graph_capabilities(graph)
    nodes = graph.get('nodes') or []
    blockers = [a for a in (anti or []) if a.get('severity') in ['critical','high']]
    gate = 'RED' if any(a.get('severity')=='critical' for a in blockers) else ('YELLOW' if blockers or ready.get('gaps') else 'GREEN')
    if gate == 'RED':
        status_text = 'Нельзя отдавать в разработку как готовое решение: сначала нужно закрыть блокирующие вопросы.'
    elif gate == 'YELLOW':
        status_text = 'Можно обсуждать как предварительное решение, но перед разработкой нужно зафиксировать риски и закрыть ключевые вопросы.'
    else:
        status_text = 'Можно переходить к детальному проектированию после архитектурного ревью.'
    who_waits = 'клиент или пользователь' if str(form.get('customer_visible')) in ['yes','mixed'] else 'внутренний сервис или фоновый процесс'
    money = str(form.get('money_impact')) in ['yes','direct','indirect']
    goal = str(form.get('business_goal') or 'нужно связать несколько систем безопасно и наблюдаемо').strip().rstrip('.')
    rec_name = ru_label(rec.get('name',''))

    def yes(v): return 'да' if v else 'нет'
    def sentence_list(items):
        items=[x.strip() for x in items if str(x).strip()]
        if not items: return 'не выявлено'
        if len(items)==1: return items[0]
        return '; '.join(items[:-1]) + '; ' + items[-1]

    next_actions=[]
    if blockers:
        for a in blockers[:3]:
            title=str(a.get('title','блокирующий вопрос')).strip()
            fix=str(a.get('fix','нужно согласовать решение')).strip()
            next_actions.append(f"Закрыть: {title}. Что сделать: {fix}")
    else:
        next_actions.append('Зафиксировать выбранную цепочку, статусы, владельцев ошибок и контракты в ADR.')
    if caps['parallel']:
        next_actions.append('Для параллельных веток решить: какие ветки критичные, какие можно выполнять как side-flow, нужно ли ждать завершения всех веток.')
    if caps['loops']:
        next_actions.append('Для циклов задать лимиты: максимальное число попыток или максимальное время ожидания, владелец восстановления и алерт зависания.')
    if caps['wait']:
        next_actions.append('Для ожидания callback/webhook указать correlation key, timeout ожидания и действие, если callback не пришёл.')
    if money:
        next_actions.append('Для операций с деньгами/лимитами добавить идемпотентность, таблицу операции, аудит и сверку расхождений.')

    core_risks=[]
    if caps['parallel']: core_risks.append('параллельные ветки могут сломать основной процесс, если не указать правило ожидания и обработку ошибки')
    if caps['loops']: core_risks.append('циклы retry/polling могут стать бесконечными или создать лишнюю нагрузку без лимитов')
    if caps['fanin']: core_risks.append('агрегация из нескольких источников может зависнуть без общего deadline и partial-response правила')
    if caps['wait']: core_risks.append('callback/webhook может не прийти, прийти повторно или прийти слишком поздно')
    if caps['compensation']: core_risks.append('компенсация может не сработать, поэтому нужен владелец и ручной сценарий восстановления')
    if money: core_risks.append('повтор запроса или retry может создать дубль финансовой операции без idempotency')
    if not core_risks: core_risks.append('цепочка может потерять статус, создать дубль или зависнуть на внешней зависимости')

    lines=[]
    lines.append('## 0. Читаемый вывод\n')
    lines.append('### Что проектируем\n')
    lines.append(f"Проектируется интеграционный процесс: {goal}. Результат ожидает {who_waits}. Базовый архитектурный подход: **{rec_name}**.\n")
    lines.append('### Что делать\n')
    lines.append('Нужно собрать процесс как управляемую цепочку: принять запрос или событие, сохранить состояние операции, выполнить шаги в нужном порядке, отдельно обработать параллельные ветки, явно описать ошибки, повторы, ручное восстановление и финальные статусы. Пользователь должен видеть не набор терминов, а понятный путь: что происходит сначала, что потом, где ветвление, где ожидание и где завершение.\n')
    lines.append('### Почему именно так\n')
    lines.append('Такой подход нужен, потому что интеграция ломается не только на “упал сервис”. Реальные проблемы возникают, когда внешний сервис долго отвечает, событие приходит повторно, callback не приходит, одна параллельная ветка падает, а другая уже выполнилась, или операция зависает между статусами. Поэтому каждый критичный шаг должен иметь статус, owner, timeout, retry/recovery policy и проверяемый результат.\n')
    lines.append('### Главные ограничения и риски\n')
    lines.append(bullet(core_risks))
    lines.append('### Можно ли идти в разработку\n')
    lines.append(f"**Статус:** {gate}. {status_text}\n")
    lines.append('### Следующий практический шаг\n')
    lines.append(bullet(next_actions[:7]))

    if blockers:
        lines.append('### Блокирующие вопросы\n')
        for a in blockers[:6]:
            lines.append(f"- **{a.get('title','Блокирующий вопрос')}**. Почему важно: {a.get('why','без этого решение может быть ненадёжным')}. Что сделать: {a.get('fix','согласовать решение и зафиксировать в ADR')}.\n")

    lines.append('## 1. Что система поняла из ввода\n')
    lines.extend([
        f"- Тип задачи: {form.get('task_type')}\n",
        f"- Бизнес-цель: {goal}\n",
        f"- Участников процесса: {len((ctx or {}).get('systems') or [])}\n",
        f"- Шагов в построенной цепочке: {len(nodes)}\n",
        f"- Пользователь ждёт результат: {yes(str(form.get('customer_visible')) in ['yes','mixed'])}\n",
        f"- Есть деньги/лимиты/регуляторика: {yes(money or form.get('regulatory_impact') in ['yes','unknown'])}\n",
        f"- Source-систему можно менять: {form.get('source_change_policy')}\n",
        f"- Есть последовательные шаги: {yes(caps['sequential'])}\n",
        f"- Параллельные ветки: {yes(caps['parallel'])}\n",
        f"- Есть условные переходы: {yes(caps['conditional'])}\n",
        f"- Циклы/retry/polling/reconciliation: {yes(caps['loops'])}\n",
        f"- Есть fan-out: {yes(caps['fanout'])}\n",
        f"- Есть fan-in/агрегация: {yes(caps['fanin'])}\n",
        f"- Wait event/callback: {yes(caps['wait'])}\n",
        f"- Compensation/manual/reprocess: {yes(caps['compensation'] or caps['manual'] or caps['reprocess'])}\n",
        f"- Готовность требований: {min(ready.get('score',0), 70) if blockers else ready.get('score',0)}%\n",
    ])
    lines.append('Вывод: система рассматривает это как процесс с состоянием, а не как набор независимых вызовов. Поэтому отчёт ниже объясняет цепочку, переходы, риски и ограничения по шагам.\n')

    lines.append('## 2. Построенная цепочка процесса\n')
    if nodes:
        lines.append('Ниже описан поток выполнения. Это не просто карточки: каждый шаг должен иметь вход, выход, переход к следующему шагу и поведение при ошибке.\n')
        for i, n in enumerate(nodes, 1):
            controls=[]
            reasons=[]
            nt=n.get('type')
            if n.get('user_waits'):
                controls.append('timeout budget')
                reasons.append('пользователь не должен ждать бесконечно')
            if n.get('idempotency_required') or 'retry' in str(n.get('retry_policy','')).lower():
                controls.append('idempotency/deduplication')
                reasons.append('повтор не должен создать дубль')
            if nt == 'publish_event':
                controls.append('outbox или эквивалент')
                reasons.append('сохранение операции и отправка события не должны расходиться')
            if nt == 'consume_event':
                controls.append('inbox, DLQ, reprocess')
                reasons.append('событие может прийти повторно или сломать consumer')
            if nt in ['retry_loop','polling_loop','reconciliation']:
                controls.append('лимит цикла и alert зависания')
                reasons.append('цикл не должен стать бесконечным')
            if nt in ['wait_event','wait_callback']:
                controls.append('correlation key и timeout ожидания')
                reasons.append('callback может не прийти или прийти повторно')
            if nt == 'compensation':
                controls.append('owner компенсации и сценарий ошибки')
                reasons.append('откат тоже может завершиться ошибкой')
            if not controls:
                controls.append('status, owner, error policy')
                reasons.append('должно быть понятно, где находится процесс и кто чинит ошибку')
            lines.append(f"{i}. **{n.get('title') or human_node_type(nt)}**\n")
            lines.append(f"   - Кто выполняет: {n.get('system_id') or 'не указано'}\n")
            lines.append(f"   - Тип шага: {human_node_type(nt)}\n")
            lines.append(f"   - Канал: {n.get('channel') or 'не указан'}\n")
            lines.append(f"   - Пользователь ждёт: {'да' if n.get('user_waits') else 'нет'}\n")
            lines.append(f"   - Что обязательно контролировать: {', '.join(controls)}\n")
            lines.append(f"   - Почему: {sentence_list(reasons)}.\n")
    else:
        lines.append('Цепочка ещё не построена. Перед разработкой нужно собрать шаги в конструкторе: старт, последовательность, ветвления, ошибки, циклы и финальные статусы.\n')

    diagram = graph_mermaid_flow(graph)
    if diagram:
        lines.append('## 2A. Схема потоков и переходов\n')
        lines.append('```mermaid\n' + diagram + '\n```\n')
        lines.append('Схема показывает не отдельные карточки, а поток. Как читать схему: стрелки показывают порядок и тип перехода. Подпись на стрелке означает условие перехода: success, timeout, retry, compensation, parallel/fork или другой сценарий. Если на схеме есть ромб или цикл, у него должны быть лимиты, условия выхода и владелец восстановления.\n')

    lines.append('## 3. Сложные участки цепочки\n')
    complex_lines=[]
    if caps['parallel']:
        complex_lines.append('Параллельные ветки: нужно решить, какие ветки критичные, нужно ли ждать все ветки, и что делать, если одна ветка упала. Некритичные DWH/notification-ветки не должны ломать основной клиентский процесс.')
    if caps['loops']:
        complex_lines.append('Циклы retry/polling/reconciliation: у каждого цикла должны быть max attempts или max duration, статус, owner и alert при зависании. Бесконечный цикл запрещён.')
    if caps['fanout']:
        complex_lines.append('Fan-out: один producer отправляет событие нескольким consumer-ам. Каждый consumer должен иметь собственную дедупликацию, DLQ/reprocess и мониторинг, чтобы сбой одного consumer-а не ломал остальных.')
    if caps['fanin']:
        complex_lines.append('Fan-in: процесс ждёт данные из нескольких источников. Нужны per-source timeout, общий deadline, правило partial response и маркер свежести данных.')
    if caps['wait']:
        complex_lines.append('Ожидание события/callback: нужен correlation key, eventId/idempotency, timeout ожидания и отдельный сценарий, если callback не пришёл.')
    if caps['compensation']:
        complex_lines.append('Компенсация: нужно указать, что именно откатывается, кто владелец, как пишется audit и что делать, если компенсация сама завершилась ошибкой.')
    if caps['manual']:
        complex_lines.append('Ручное восстановление: должен быть owner, SLA, список действий оператора и понятный статус для зависшего процесса.')
    if not complex_lines:
        complex_lines.append('Сложные участки не указаны явно. Если в реальном процессе есть параллельность, циклы, callback или ручное восстановление, их нужно добавить в конструкторе, иначе отчёт будет неполным.')
    lines.append(bullet(complex_lines))

    lines.append('## 4. Паттерны по шагам, а не набор терминов\n')
    action_lines=[]
    for n in nodes[:14]:
        nt=n.get('type')
        title=n.get('title') or human_node_type(nt)
        if nt in ['persist_operation','api_request','validation']:
            action_lines.append(f"**{title}**: сохранить операцию/заявку и проверить idempotency. Почему: повторный запрос, timeout или повторное нажатие не должны создать дубль. Ограничение: нужен уникальный ключ операции и понятная политика повторного ответа.")
        elif nt in ['rest_call','enrichment']:
            action_lines.append(f"**{title}**: задать timeout, retry limit, backoff и fallback/manual recovery. Почему: внешний сервис может тормозить, падать или вернуть лимит. Ограничение: retry без лимита может перегрузить зависимость.")
        elif nt=='publish_event':
            action_lines.append(f"**{title}**: целевой вариант — outbox или эквивалентная надёжная публикация. Если source нельзя менять, использовать CDC/polling/adapter + reconciliation и явно принять остаточный риск. Почему: операция может сохраниться, а событие не уйти.")
        elif nt=='consume_event':
            action_lines.append(f"**{title}**: добавить inbox/deduplication, DLQ и reprocess. Почему: событие может прийти повторно или быть невалидным. Ограничение: DLQ без owner и reprocess — это просто склад ошибок.")
        elif nt in ['retry_loop','polling_loop']:
            action_lines.append(f"**{title}**: задать max attempts/max duration, backoff, статус ожидания и alert. Почему: цикл должен завершиться успехом, ошибкой или ручным восстановлением, а не висеть бесконечно.")
        elif nt=='reconciliation':
            action_lines.append(f"**{title}**: определить source, target, ключ сверки, частоту и действие при расхождении. Почему: reconciliation нужен, чтобы находить потерянные/разошедшиеся изменения.")
        elif nt in ['wait_event','wait_callback','webhook_receive']:
            action_lines.append(f"**{title}**: использовать correlation key, eventId/idempotency, timeout ожидания и проверку подписи для webhook. Почему: callback может прийти повторно, поздно или не прийти вообще.")
        elif nt=='compensation':
            action_lines.append(f"**{title}**: описать условие запуска, действие отката, owner и поведение при compensation_failed. Почему: если компенсация не сработает, процесс останется в опасном промежуточном состоянии.")
        elif nt in ['dwh_export','notification']:
            action_lines.append(f"**{title}**: сделать как side-flow, если это не критично для клиента. Почему: DWH/уведомления обычно не должны блокировать основной бизнес-процесс. Ограничение: нужна отдельная ошибка ветки и мониторинг.")
    if not action_lines:
        action_lines.append('Сначала построить цепочку в конструкторе. Без шагов нельзя честно ответить, где нужны idempotency, outbox, inbox, retry, compensation и reconciliation.')
    lines.append(bullet(action_lines))

    lines.append('## 5. Что нельзя делать\n')
    dont=[
        'Не строить длинную синхронную цепочку из трёх и более внешних вызовов для клиентского сценария без trackingId/status API.',
        'Не делать retry команд без idempotency/operationId/unique constraint.',
        'Не использовать cache/read model как источник финального финансового решения.',
        'Не делать direct DB write между сервисами без отдельного accepted risk и плана отказа от этого решения.',
        'Не называть workaround production-ready решением.',
    ]
    if caps['loops']: dont.append('Не делать бесконечные retry/polling/reconciliation циклы без лимитов и owner.')
    if caps['parallel']: dont.append('Не делать параллельные ветки без правила ожидания, критичности и поведения при падении одной ветки.')
    if caps['fanin']: dont.append('Не делать fan-in без общего deadline и partial/degraded policy.')
    if caps['wait']: dont.append('Не ждать webhook/callback бесконечно без timeout и reconciliation.')
    if caps['compensation']: dont.append('Не делать compensation без owner и сценария ошибки самой компенсации.')
    lines.append(bullet(dont))

    lines.append('## 6. MVP простыми действиями\n')
    mvp=[
        '**Сохранить операцию до внешних вызовов.** Зачем: операция не должна потеряться при сбое зависимости. Acceptance: при timeout запись остаётся в БД со статусом WAITING_RETRY или ERROR.',
        '**Добавить idempotency и correlationId.** Зачем: повтор запроса или события не создаёт дубль и легко трассируется. Acceptance: повтор с тем же ключом возвращает тот же результат или текущий статус.',
        '**Сделать понятные статусы и GET status/read model.** Зачем: пользователь или оператор должен понимать, где находится процесс. Acceptance: есть статус, last_updated и причина ошибки.',
        '**Описать ошибки каждого внешнего шага.** Зачем: timeout, 5xx, validation_error и rate_limit требуют разного поведения. Acceptance: для каждой ошибки есть retry/no retry, owner и действие после исчерпания попыток.',
    ]
    if caps['parallel']: mvp.append('**Параллельные ветки.** Для каждой ветки указать critical/non-critical, join policy, branch status и error policy.')
    if caps['loops']: mvp.append('**Циклы.** Для каждого retry/polling/reconciliation цикла указать max attempts/max duration, статус, stuck alert и manual recovery.')
    if caps['wait']: mvp.append('**Ожидание callback/event.** Указать correlation key, timeout и missing-callback handling.')
    if caps['compensation']: mvp.append('**Компенсация.** Указать, что компенсируется, кто owner и что делать при compensation_failed.')
    lines.append(bullet(mvp))

    lines.append('## 7. Ограничения и компромиссы\n')
    compromise=[]
    if str(form.get('source_change_policy')) in ['minimal_table_only','read_only','none','minimal'] or traits.get('source_read_only') or traits.get('no_changes'):
        compromise.append('Source-систему нельзя или почти нельзя менять. Поэтому outbox/state machine внутри source нельзя предлагать как прямой MVP. Целевой вариант можно оставить как phase 2, а v1 должен использовать adapter/CDC/polling/read-only projection + reconciliation с явно принятым остаточным риском.')
    if traits.get('new_infra_forbidden') or form.get('new_infra_policy') in ['existing_only','forbidden']:
        compromise.append('Новая инфраструктура ограничена. Если нужна async-обработка, нужно либо использовать существующую Kafka/очередь, либо явно оформить REST-only compromise с меньшими гарантиями восстановления.')
    if blockers:
        compromise.append('Есть блокирующие вопросы, поэтому проценты готовности нельзя трактовать как “всё готово”. Это предварительная оценка для обсуждения, а не разрешение на разработку.')
    if not compromise:
        compromise.append('Критичных компромиссов из ввода не выявлено, но перед production всё равно нужны contract tests, load test, security review, runbook и rollback plan.')
    lines.append(bullet(compromise))

    lines.append('## 8. Что уточнить до разработки\n')
    questions=[]
    if caps['parallel']: questions.append('Какие параллельные ветки критичны для бизнес-результата, а какие можно выполнять отдельно и не блокировать клиента?')
    if caps['loops']: questions.append('Сколько раз и как долго можно повторять retry/polling, прежде чем перевести процесс в manual recovery?')
    if caps['fanin']: questions.append('Можно ли вернуть partial response, если один из источников fan-in не ответил вовремя?')
    if caps['wait']: questions.append('Сколько можно ждать callback/webhook и что считать terminal timeout?')
    if caps['compensation']: questions.append('Кто владелец компенсации и что делать, если компенсация завершилась ошибкой?')
    if traits.get('event_needed') and not (form.get('kafka_topology') or form.get('allowed_channels')):
        questions.append('Какой async-механизм разрешён: Kafka, RabbitMQ/queue или только REST-only compromise?')
    if not questions: questions.append('Подтвердить owners, SLA, error model, idempotency scope, retention и правила rollback/replay.')
    lines.append(bullet(questions))
    return ''.join(lines) + '\n---\n'

def to_bool_blocking(x): return 'false' if str(x).strip().lower()=='non_blocking' else 'true'
def safe_int(x,default=0):
    try: return int(re.sub(r'\D','',str(x)) or default)
    except Exception: return default


RU_LABELS = {
    'Architecture decision blocked: недостаточно данных': 'Решение заблокировано: недостаточно данных',
    'Architecture decision blocked: выберите способ управления цепочкой': 'Решение заблокировано: нужно выбрать способ управления цепочкой',
    'Non-invasive Existing Process Extension': 'Неинвазивное расширение существующего процесса',
    'Event Choreography': 'Событийная хореография',
    'Fan-out/Fan-in Orchestrated Process': 'Оркестрируемый процесс с параллельными ветками и агрегацией',
    'Orchestrated E2E Process': 'Оркестрируемая E2E-цепочка',
    'Backward-compatible Extension with Events': 'Обратно совместимое расширение через события',
    'Batch/File Integration': 'Пакетная/файловая интеграция',
    'SOAP Legacy Adapter Integration': 'Интеграция legacy через SOAP-адаптер',
    'Data Pipeline / DWH': 'Контур данных / DWH',
    'Queue-based Worker Flow': 'Асинхронный worker-flow через очередь',
    'Basic API + DB': 'Базовая API-интеграция с БД',
    'API Gateway / Edge': 'API Gateway / входной слой',
    'REST API + OpenAPI': 'REST API + OpenAPI',
    'Kafka/Event Streaming': 'Kafka / поток событий',
    'Integration Publisher / Event Enrichment': 'Integration Publisher / обогащение события',
    'Outbox + REST Enrichment Publisher': 'Outbox + REST-обогащение перед Kafka',
    'Message Queue / Workers': 'Очередь сообщений / workers',
    'Webhook/Callback': 'Webhook / callback',
    'Batch/File/SFTP': 'Пакетный/файловый обмен / SFTP',
    'SOAP Legacy Adapter': 'SOAP legacy-адаптер',
    'CDC': 'CDC / чтение изменений',
    'ETL/ELT': 'ETL/ELT',
    'Transactional Outbox': 'Transactional Outbox',
    'Inbox / Idempotent Consumer': 'Inbox / идемпотентный consumer',
    'Saga / Process Manager': 'Saga / менеджер процесса',
    'Workflow/BPM Engine': 'Workflow/BPM-движок',
    'CQRS / Read Models': 'CQRS / read-модели',
    'PostgreSQL OLTP': 'PostgreSQL OLTP',
    'Event Sourcing': 'Event Sourcing',
    'Highload Controls': 'Контроли highload',
    'REST/API integration': 'REST/API-интеграция',
    'Synchronous chain': 'Синхронная цепочка',
    'Event streaming': 'Поток событий',
    'Queue/worker flow': 'Очередь / worker-flow',
    'CDC/Data replication': 'CDC / репликация данных',
    'DWH/ETL pipeline': 'DWH/ETL-контур',
    'File exchange': 'Файловый обмен',
    'SOAP/legacy': 'SOAP/legacy',
    'E2E process': 'E2E-процесс',
    'Fan-in/join': 'Fan-in / join-агрегация',
    'Fan-out': 'Fan-out / параллельные ветки',
    'Inbox/idempotent consumer': 'Inbox / идемпотентный consumer',
    'Cache / Fast Read Path': 'Кэш / быстрый контур чтения',
    'Fallback / Graceful Degradation': 'Fallback / управляемая деградация',
    'Business-driven Read Model': 'Read model из бизнес-требований',
    'Client-facing Status Read Model': 'Клиентская read-модель статуса',
    'Financial Operation State Machine': 'Финансовая операция / машина состояний',
    'Async Job / Heavy Processing Flow': 'Фоновая обработка / async job',
    'Data Synchronization / Source-of-Truth Sync': 'Синхронизация данных / source-of-truth sync',
    'Migration / Strangler Fig': 'Миграция / Strangler Fig',
    'Near Real-time Decision Flow': 'Near real-time decision flow',
    'Reference Data API + Versioned Cache': 'Справочник / versioned cache',
    'External API Adapter with Resilience': 'Adapter внешнего API с resilience',
    'BFF/API Composition with Partial Response': 'BFF / API composition с partial response',
    'Webhook Intake + Inbox Processing': 'Приём webhook через Inbox',
    'Fast Read / Cached Read Model': 'Быстрое чтение / кэшируемая read-model',
    'Privacy / Data Erasure Orchestration Pipeline': 'Privacy / оркестрация удаления ПДн',
    'CDC Legacy Modernization / Operational Projection': 'CDC modernization / операционная проекция',
}

SCORE_LABELS = {
    'reliability':'Надёжность','consistency':'Согласованность данных','scalability':'Масштабируемость',
    'observability':'Наблюдаемость','security':'Безопасность','maintainability':'Сопровождаемость',
    'operations':'Эксплуатация','model':'Качество модели описания','operational_readiness':'Операционная готовность','overall':'Итоговая оценка'
}

BUSINESS_SITUATION_ALIASES = {
    'customer_360':'multi_source_aggregation','customer_360_card':'multi_source_aggregation','client_360':'multi_source_aggregation',
    'customer_card':'multi_source_aggregation','client_profile':'multi_source_aggregation','api_composition':'multi_source_aggregation',
    'bff':'multi_source_aggregation','hot_screen':'highload_read','sync_screen':'highload_read','read_model':'highload_read',
    'migration':'migration_or_strangler','legacy_migration':'migration_or_strangler','modernization':'migration_or_strangler','strangler':'migration_or_strangler',
    'saga':'distributed_transaction_saga','distributed_transaction':'distributed_transaction_saga','long_running_business_process':'long_running_process',
    'shared_kafka_topic':'shared_topic_selective_consumer','filter_kafka_topic':'shared_topic_selective_consumer','selective_consumer':'shared_topic_selective_consumer',
    'single_topic_filtering':'shared_topic_selective_consumer','common_topic_filter':'shared_topic_selective_consumer',
    'regulatory_change':'regulatory_process','schema_change':'regulatory_process','dwh_retention':'dwh_reporting','storage_growth':'dwh_reporting',
    'gdpr_erasure':'privacy_erasure','data_erasure':'privacy_erasure','privacy_erasure':'privacy_erasure','right_to_be_forgotten':'privacy_erasure',
    'cdc_modernization':'cdc_legacy_modernization','operational_cdc':'cdc_legacy_modernization','legacy_cdc':'cdc_legacy_modernization'
}
CONSTRAINT_ALIASES = {
    'cannot_change_source':'source_change_forbidden','source_cannot_be_changed':'source_change_forbidden','source_change_forbidden':'source_change_forbidden',
    'no_new_topic':'new_topic_forbidden','cannot_create_topic':'new_topic_forbidden','new_topic_forbidden':'new_topic_forbidden',
    'limited_infra':'infrastructure_limited','infra_limited':'infrastructure_limited','no_kafka_in_source':'source_has_no_broker_infra',
    'source_has_no_broker_infra':'source_has_no_broker_infra','new_service_too_expensive':'new_service_too_expensive','cannot_add_service':'new_service_too_expensive'
}

def _as_list(v):
    if isinstance(v, list): return [str(x).strip() for x in v if str(x).strip()]
    return split_csv(v)

def normalize_form(f):
    """Normalize form-only/CLI/API input so real users may use business words, not exact enum values."""
    f=dict(f or {})
    situations=[]
    for x in _as_list(f.get('business_situations', [])):
        y=BUSINESS_SITUATION_ALIASES.get(str(x).strip().lower(), str(x).strip())
        if y and y not in situations: situations.append(y)
    text=' '.join(str(f.get(k,'')) for k in ['business_goal','user_action','compromise_comment','project_name']).lower()
    kw_map=[
        (['customer 360','карточка клиента','витрина клиента','client 360'],'multi_source_aggregation'),
        (['общий kafka','общий топик','shared kafka','shared topic','single topic','один topic','один топик','фильтр kafka','фильтрация kafka'],'shared_topic_selective_consumer'),
        (['нельзя менять source','source менять нельзя','источник менять нельзя','нельзя менять источник'],'source_change_forbidden'),
        (['нельзя новый топик','нельзя создать topic','отдельный topic запрещ','отдельный топик запрещ'],'new_topic_forbidden'),
        (['нет kafka','нет кафка','source без kafka','исходном нет kafka'],'source_has_no_broker_infra'),
        (['обогат','enrichment','дообогат'],'data_enrichment'),
        (['webhook','callback','вебхук'],'webhook_callback'),
        (['strangler','legacy replacement','замена legacy','миграция системы','миграция сервиса'],'migration_or_strangler'),
        (['цб','регулятор','регуляторн','изменил модель','схема изменилась','изменение модели','несколько целей займа','цель займа','backward compatibility','schema version','schemaversion','migration','consumer impact'],'regulatory_process'),
        (['dwh','двх','витрина данных','раздувается бд','терабайт','retention','archive','архив','watermark','offload','реплика','разгрузить prod','продовая база распухает'],'dwh_reporting'),
        (['gdpr','персональн','пдн','удаление данных','стереть данные','право на удаление','right to be forgotten','erasure','legal hold','retention exception'],'privacy_erasure'),
        (['iot','telemetry','телеметр','датчик','device','100k devices','stream processing','realtime alert','out-of-order','hot partition'],'highload_stream_ingestion'),
        (['active-active','active active','multi-region write','multiregion write','split-brain','split brain','double spend','двойное списание','две региона','2 региона'],'active_active_financial_write'),
        (['multi-tenant','multitenant','tenant','noisy neighbor','шумный сосед','крупный tenant','общий consumer pool'],'multi_tenant_noisy_neighbor'),
        (['cdc','wal','lsn','debezium','change data capture','снимать изменения','операционные события','read model','проекция','нельзя менять legacy','legacy core нельзя менять'],'cdc_legacy_modernization'),
        (['200 мс','200ms','subsecond','bounded latency','decision за','решение за','fraud decision','precomputed features','fallback decision'],'near_real_time_decision'),
    ]
    constraints=set(_as_list(f.get('forbidden_channels', [])))
    for keys,val in kw_map:
        if any(k in text for k in keys):
            if val in CONSTRAINT_ALIASES.values():
                constraints.add(val)
            elif val not in situations:
                situations.append(val)
    # Remove false-positive privacy situations caused by negated GDPR/erasure wording or non-privacy receipts.
    if 'privacy_erasure' in situations and not privacy_erasure_signal(f):
        situations=[x for x in situations if x!='privacy_erasure']
    # A single existing Kafka topic is not automatically a selective-consumer case.
    # It is selective-consumer only when we read/filter FROM that topic; if we publish an enriched event TO it,
    # the top-level class must be enrichment publisher/export.
    if 'shared_topic_selective_consumer' in situations and kafka_destination_enrichment_signal(f):
        situations=[x for x in situations if x!='shared_topic_selective_consumer']
    if 'shared_topic_selective_consumer' in situations:
        f.setdefault('kafka_topology','single_topic_only')
        if not f.get('kafka_topology') or f.get('kafka_topology')=='multi_topic_ok': f['kafka_topology']='single_topic_only'
        if 'kafka' not in _as_list(f.get('allowed_channels', [])):
            f['allowed_channels']=_as_list(f.get('allowed_channels', []))+['kafka']
        if 'highload_write_stream' not in situations: situations.append('highload_write_stream')
        if 'data_synchronization' not in situations: situations.append('data_synchronization')
        constraints.add('new_topic_forbidden')
    if 'source_change_forbidden' in constraints:
        f['source_change_policy']='forbidden'
    if 'new_topic_forbidden' in constraints:
        if f.get('kafka_topology') in ['', 'multi_topic_ok', None]: f['kafka_topology']='single_topic_only'
    if 'source_has_no_broker_infra' in constraints:
        f['source_has_kafka_infra']='no'
    if 'new_service_too_expensive' in constraints and f.get('new_service_policy')=='allowed':
        f['new_service_policy']='reuse_existing_runtime'
    f['business_situations']=situations
    f['forbidden_channels']=sorted(constraints | set(_as_list(f.get('forbidden_channels', []))))
    # Business-first constructor submits business_case/steps plus lightweight chips; expand them into the same facets
    # that the legacy rule engine and specialized packs already understand.
    if f.get('business_case') or f.get('business_steps_json') or f.get('business_process_json'):
        f = build_scenario_facets_from_business(f)
    return f

def ru_label(x):
    return RU_LABELS.get(str(x), str(x))
def ru_list(items):
    return [ru_label(x) for x in (items or [])]

def regulatory_schema_signal(f):
    """True when regulatory wording is about changing data/API schema/model, not just regulatory reporting."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    keywords=[
        'изменил модель','изменение модели','модель данных','схема изменилась','schema change','schema_change',
        'schema version','schemaversion','schema_version','backward compatibility','обратн', 'совместим',
        'consumer impact','контракт потреб', 'миграц', 'migration', 'backfill',
        'несколько целей займа','цель займа','цели займа','loan purpose', 'nullable', 'mapping'
    ]
    return any(k in text for k in keywords)


def privacy_erasure_signal(f):
    """Detect privacy/right-to-erasure workflows with context, not single words.
    receipt/evidence/retention are valid words in POS, IoT, payments and delivery acknowledgements.
    They become privacy signals only with explicit erasure/DSAR/legal-hold wording.
    """
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix','error_matrix']).lower()
    negative_context=[
        'pos receipt','sales receipt','payment receipt','command receipt','delivery receipt','read receipt',
        'iot','firmware','telemetry','loyalty','points','purchase receipt','кассовый чек','чек покупки',
        'подтверждение доставки команды','подтверждение доставки','квитанция платежа','платёжная квитанция'
    ]
    strong=[
        'gdpr','right to be forgotten','data erasure','privacy deletion','delete personal data',
        'удаление пдн','удалить пдн','персональные данные удалить','право на удаление','стереть персональные',
        'subject request','dsar','субъект персональных данных'
    ]
    erasure_words=['erasure','erase','deletion','delete','удалени','удалить','стереть']
    privacy_words=['personal data','privacy','пдн','персональн','subject request','dsar','consent','согласие']
    legal_words=['legal hold','retention exception','исключение retention','исключение хранения','подтверждение удаления','erasure receipt','evidence of deletion']
    negation_phrases=[
        'no gdpr erasure','no data erasure','no privacy deletion','not privacy deletion','not a privacy deletion',
        'not erasure request','not a data erasure','not gdpr','not dsar','without gdpr','без gdpr',
        'не gdpr','не удаление пдн','не запрос на удаление','не privacy','не dsar',
        'receipt is acknowledgement','receipt means acknowledgement','acknowledgement not erasure'
    ]
    if any(k in text for k in negation_phrases):
        return False
    if any(k in text for k in strong):
        return True
    if any(k in text for k in negative_context) and not any(k in text for k in strong + legal_words):
        return False
    contextual = any(a in text for a in erasure_words) and any(b in text for b in privacy_words)
    legal_context = any(k in text for k in legal_words) and any(a in text for a in erasure_words + privacy_words)
    return bool(contextual or legal_context)



def shared_topic_consumer_signal(f):
    """True only when the existing Kafka topic is the source to read/filter, not just the destination to publish into."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix','current_solution_description']).lower()
    producer_terms=['publish to','send to','write to','produce to','публиковать в','отправить в','записать в','сформировать событие','publish enriched','enriched event to','final event to','destination topic','target topic']
    consumer_terms=['consume from','read from','читать из','вычитать из','консьюмер','consumer','filter from','фильтр','фильтрац','отбирать из','selective consumer','shared topic as source','общий топик как источник']
    shared_terms=['shared topic','common topic','общий топик','общий kafka','single topic','один топик','only existing kafka topic','единственный топик']
    if any(p in text for p in producer_terms) and not any(c in text for c in consumer_terms):
        return False
    return any(st in text for st in shared_terms) and any(c in text for c in consumer_terms)

def kafka_destination_enrichment_signal(f):
    """Producer-side/enrichment case: build/publish an event to Kafka, possibly into the only existing topic."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix','current_solution_description']).lower()
    needs_event=any(x in text for x in ['publish','produce','send','публиковать','отправить','сформировать событие','kafka','topic','топик'])
    enrich=any(x in text for x in ['enrich','enriched','enrichment','обогат','дообогат','rest enrichment','rest-сервис'])
    source_change=any(x in text for x in ['contract changes','изменения договор','обновления договор','source service','исходный сервис','source has no kafka','no kafka infrastructure','нет kafka'])
    return needs_event and enrich and source_change and not shared_topic_consumer_signal(f)

def bff_readonly_composition_signal(f):
    """Detect read-only Customer 360/BFF/API composition.
    This must win over weak keyword matches such as a source system named Loyalty.
    """
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix','current_solution_description']).lower()
    situations=set(_as_list(f.get('business_situations', [])))
    bff_words=['customer 360','client 360','карточка клиента','витрина клиента','bff','api composition','partial response','частичный ответ','freshness label','freshness labels','per-source cache','по блокам','read-only','только чтение','read model','read-model']
    return bool(situations & {'multi_source_aggregation','customer_360','api_composition','many_sources_one_consumer','read_model'}) or any(x in text for x in bff_words)


def loyalty_ledger_signal(f):
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix','current_solution_description']).lower()
    loyalty=any(x in text for x in ['loyalty','points','reward points','баллы','лояльност','бонус'])
    if not loyalty:
        return False
    # Loyalty as a read-only block in Customer 360 is not a ledger. Ledger requires mutation of points/balance.
    readonly_source_context=any(x in text for x in [
        'loyalty block','source block','read only','read-only','только чтение','как источник','источник данных',
        'customer 360','client 360','карточка клиента','partial response','api composition','bff'
    ])
    explicit_not_ledger=any(x in text for x in [
        'not points balance mutation','not balance mutation','not ledger','не ledger','не леджер',
        'не начисление','не списание','без начисления','без списания','только отображение','только показать'
    ])
    mutation_terms=any(x in text for x in [
        'accrue','accrual','debit','credit','spend points','earn points','points delta','pointsdelta',
        'начисл','списан','сгорание баллов','изменить баланс','изменение баланса','баланс меняется',
        'ledger entry','проводк','операция баллов','operationid','operation_id','source_transaction_id',
        'refund','reversal','возврат','отмена операции'
    ])
    pos_receipt_terms=any(x in text for x in ['pos','purchase receipt','sales receipt','касс','чек покупки','receipt events','retail purchase'])
    if (readonly_source_context or bff_readonly_composition_signal(f)) and not mutation_terms and not pos_receipt_terms:
        return False
    if explicit_not_ledger and not mutation_terms and not pos_receipt_terms:
        return False
    strong_ledger_context = any(x in text for x in ['ledger','баланс','points balance','баланс баллов','проводк','source_transaction_id','receipt','pos','касс','чек покупки','refund','reversal'])
    wide_event_choreography = f.get('task_type')=='event_domain' and f.get('orchestration')=='choreography' and f.get('chain_depth') in ['fanout','fanout_fanin']
    if wide_event_choreography and not strong_ledger_context:
        return False
    return (mutation_terms and strong_ledger_context) or (pos_receipt_terms and any(x in text for x in ['points','баллы','лояльност','бонус']))

def file_exchange_signal(f):
    """Detect SFTP/file/batch import/export as a top-level integration class."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    file_terms=['sftp','ftp','file import','file export','csv','xml file','object storage','nightly file','manifest','checksum','batch file','файл','файлов','ночная загрузка','реестр','контрольная сумма']
    batch_terms=['batch','nightly','ежедневн','ночн','регламентн','job']
    online_terms=['webhook','callback','real-time decision','subsecond','online api','bff']
    return bool(any(x in text for x in file_terms) or (any(x in text for x in batch_terms) and f.get('latency_sla') in ['daily','hours'])) and not any(x in text for x in online_terms)


def dwh_data_lake_signal(f):
    """Detect analytical/DWH/Data Lake pipelines even when CDC is the ingestion mechanism."""
    # Do not scan default matrices: they often contain demo DWH rows and would turn every case into DWH.
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','current_solution_description','compromise_comment']).lower()
    if any(x in text for x in ['not dwh','not dwh/offload','не dwh','не двх','это не dwh','это не dwh/offload','не отчётность']):
        return False
    terms=['dwh','двх','data lake','data warehouse','lakehouse','datamart','витрина данных','schema drift','lineage','data quality','raw zone','bronze','silver','gold','watermark','backfill','cold storage','retention/archive']
    explicit_business = 'dwh_reporting' in _as_list(f.get('business_situations',[])) or f.get('task_type')=='dwh_analytics'
    return explicit_business or any(x in text for x in terms)


def cdc_modernization_signal(f):
    """Detect non-invasive legacy modernization via CDC/WAL/LSN into operational streams/projections."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    explicit_cdc_text = any(k in text for k in ['cdc','wal','lsn','debezium','change data capture','снимать изменения','журнал изменений'])
    has_cdc_word = explicit_cdc_text or ('cdc' in _as_list(f.get('existing_capabilities',[])) and f.get('source_change_policy') in ['read_only','forbidden'])
    operational_goal = any(k in text for k in ['kafka','event stream','операционн','read model','проекц','projection','изменения договор','contract changes','near-real-time','near realtime'])
    not_analytics_only = not dwh_data_lake_signal(f) and not any(k in text for k in ['витрина отчётности','регуляторная витрина','analytics only','только аналитик'])
    source_locked = f.get('source_change_policy') in ['read_only','forbidden'] or any(k in text for k in ['нельзя менять legacy','legacy core нельзя менять','source менять нельзя','источник менять нельзя','read-only'])
    explicit_not_migration = not any(k in text for k in ['strangler','замена legacy','заменить legacy','migration / strangler','feature flags','shadow compare'])
    return bool(has_cdc_word and operational_goal and not_analytics_only and explicit_not_migration and source_locked and not kafka_destination_enrichment_signal(f))


def near_realtime_strong_signal(f):
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    return (f.get('latency_sla') in ['milliseconds','subsecond'] or f.get('response_time_expectation')=='under_1s' or any(k in text for k in ['200ms','200 мс','subsecond','bounded latency','за 200','fraud decision','fallback decision','precomputed features']))


def highload_stream_ingestion_signal(f):
    """Detect telemetry/event ingestion where stream processing/alerting is the top-level, while DWH is only a downstream consumer."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    active=set(_as_list(f.get('business_situations',[])))
    stream_terms=['iot','telemetry','телеметр','датчик','device','devices','sensor','stream processing','realtime alert','real-time alert','алерт','out-of-order','out of order','hot partition','partition key','100k','100 000']
    return ('highload_stream_ingestion' in active) or (any(x in text for x in stream_terms) and (f.get('load_profile') in ['highload','bursty'] or safe_int(f.get('rps'),0)>=300 or any(x in text for x in ['100k','100 000','тысяч'])))

def active_active_financial_write_signal(f):
    """Detect dangerous active-active/multi-region writes for balances/financial state."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    active=set(_as_list(f.get('business_situations',[])))
    active_active=any(x in text for x in ['active-active','active active','multi-region write','multiregion write','split-brain','split brain','две региона','2 региона','два региона','double spend','двойное списание']) or 'active_active_financial_write' in active
    financial=(f.get('money_impact')=='yes' or f.get('sensitivity')=='financial' or any(x in text for x in ['balance','баланс','счёт','счет','ledger','деньги','payment','платёж','платеж','лимит']))
    return bool(active_active and financial)

def multi_tenant_noisy_neighbor_signal(f):
    """Detect SaaS/B2B shared consumer pool where one tenant can starve others."""
    text=' '.join(str(f.get(k,'')) for k in ['project_name','business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower()
    active=set(_as_list(f.get('business_situations',[])))
    terms=['multi-tenant','multitenant','tenant','tenantid','tenant_id','noisy neighbor','шумный сосед','крупный tenant','общий consumer pool','общий пул consumer','200 tenants']
    return 'multi_tenant_noisy_neighbor' in active or any(x in text for x in terms)


# ---------- operation kind / reliability key policy ----------
def infer_operation_kind(f, c, t):
    """Classify the dominant flow before applying blockers.
    This prevents generic event/command rules from firing on read-only BFF,
    DWH/batch, regulatory schema-change and migration cases.
    """
    active=set(t.get('business_situations',set()) or [])
    explicit_core = (f.get('task_type')=='e2e_chain' or bool(active & {'application_or_order_creation','multi_step_business_process','distributed_transaction_saga','long_running_process','financial_operation','exactly_once_required'}))
    if t.get('shared_topic_selective') or 'shared_topic_selective_consumer' in active:
        return 'kafka_event_consumer'
    if privacy_erasure_signal(f) or 'privacy_erasure' in active:
        return 'privacy_erasure_pipeline'
    # Edge/file/analytical classes must win over generic CDC when CDC is only a transport layer,
    # but business-impact classes (migration/regulatory/core E2E) still win over DWH/file layers.
    if 'webhook_callback' in active or f.get('result_model')=='callback':
        return 'webhook_event_intake'
    if f.get('task_type')=='data_migration' or 'migration_or_strangler' in active or f.get('task_type')=='replace_legacy':
        return 'migration'
    if regulatory_schema_signal(f) and (t.get('regulatory_impact') or 'regulatory_process' in active):
        return 'regulatory_schema_change'
    if f.get('legacy')=='file_only':
        return 'batch_file_exchange'
    if highload_stream_ingestion_signal(f):
        return 'highload_stream_ingestion'
    if dwh_data_lake_signal(f) and not explicit_core:
        return 'dwh_offload'
    if file_exchange_signal(f) or (t.get('file_needed') and 'batch_processing' in active):
        return 'batch_file_exchange'
    if ('near_real_time_decision' in active and near_realtime_strong_signal(f)):
        return 'near_real_time_decision'
    if (cdc_modernization_signal(f) or 'cdc_legacy_modernization' in active) and not ({'shared_topic_selective_consumer','migration_or_strangler'} & active):
        return 'cdc_legacy_modernization'
    if ('multi_source_aggregation' in active or 'customer_360' in active or 'api_composition' in active or 'many_sources_one_consumer' in active or 'read_model' in active or bff_readonly_composition_signal(f)):
        if not explicit_core:
            return 'bff_composition'
    if t.get('direct_money_impact') or 'financial_operation' in active or f.get('delivery')=='business_exactly_once':
        return 'financial_command'
    if t.get('enrichment_needed') and t.get('event_needed'):
        return 'kafka_event_publisher'
    if t.get('partner') or t.get('unstable_external') or 'external_api_dependency' in active:
        if not explicit_core and not t.get('chain'):
            return 'external_partner_adapter'
    if t.get('event_needed'):
        return 'kafka_event_publisher'
    if f.get('result_model')=='sync' and not (t.get('event_needed') or t.get('queue_needed') or t.get('money_impact')):
        return 'query_readonly'
    return 'command_create_update' if t.get('chain') or t.get('queue_needed') else 'query_readonly'


SIMPLE_GOALS = [
    'Спроектировать новую интеграцию',
    'Проверить существующее решение',
    'Разобрать сложный кейс',
]
SIMPLE_SITUATIONS = [
    'Один сервис вызывает другой и ждёт ответ',
    'Нужно принять запрос сейчас, а обработать позже',
    'Нужно отправить событие об изменении данных',
    'Нужно обогатить данные перед отправкой',
    'Внешняя система ответит позже callback-ом',
    'Нужно собрать статус из нескольких систем',
    'Нужно передать данные в DWH/отчётность',
    'Есть legacy-система или файлы',
    'Kafka одна, consumer фильтрует только нужные события',
    'Не знаю, помогите выбрать',
]
SIMPLE_STEPS = ['Что делаем?', 'Какая ситуация?', 'Простые вопросы', 'Я понял задачу так', 'Схема', 'Отчёт']

CASE_DEFAULT_TITLES = {
    'sync_rest': 'Интеграция Service A → Service B',
    'async_worker': 'Асинхронная обработка Service 1 → Service 2 → Service 3',
    'event_kafka': 'Событийная интеграция через Kafka',
    'enrichment_kafka': 'Интеграция с обогащением данных перед отправкой',
    'callback': 'Интеграция с отложенным ответом через callback',
    'dwh': 'Выгрузка данных в DWH/отчётность',
    'legacy_file': 'Интеграция с legacy-системой через файл',
    'status_aggregation': 'Сбор статуса из нескольких систем',
    'audit': 'Проверка существующего интеграционного решения',
}

CASE_SCHEMAS = {
    'sync_rest': 'Service A → REST API → Service B',
    'async_worker': 'Service 1 → Service 2 API → integration_task DB → Worker → Service 3',
    'event_kafka': 'Source Service → Business DB → Outbox → Publisher → Kafka → Consumer → Inbox → Target DB',
    'callback': 'Internal Service → External API → Callback API → Status DB',
    'dwh': 'Source System → Export/CDC → Staging → DWH → Reconciliation',
    'legacy_file': 'Legacy System → File Export → Validation/Checksum → Quarantine → Target System',
    'status_aggregation': 'Client/UI → BFF/API Composition → Service A / Service B / Service C → Cache/Read Model',
    'enrichment_kafka': 'Source Service → Minimal Event / Outbox → Kafka → Enrichment Worker / Adapter → Target Service',
    'audit': 'Current Solution → Risk Review → Target Improvements → Developer Handoff',
}

CANONICAL_CASE_SCHEMAS = {
    'async_worker': 'Client/UI → Application API → integration_task DB → Worker → Target Service → Status DB',
    'saga_state_machine': 'Initiator → Process Coordinator → Process State DB → Step Services → Compensation / Manual Recovery',
    'event_kafka': 'Source Service → Business DB → Outbox → Publisher → Event Stream → Consumer → Inbox → Target Service',
    'shared_topic_selective_consumer': 'Shared Event Stream → Selective Consumer → Filter → Inbox/Dedup Sink → Target Service → DLQ/Reprocess',
    'enrichment_before_kafka': 'Source Service → Source-owned Outbox → Integration Publisher → REST Enrichment API → Event Stream → Consumer',
    'webhook_intake': 'External/Internal Request → External Provider → Callback API → Inbox → Async Worker → Status DB',
    'bff_api_composition': 'Client/UI → BFF/API Composition → Source Services → Cache/Read Model → Partial Response',
    'dwh_pipeline': 'Source System → CDC/Export → Staging → Data Quality → DWH/Reporting → Reconciliation',
    'batch_file_exchange': 'Legacy System → File Export → Manifest/Checksum → Staging → Validation → Quarantine/Target',
    'contract_required_field_missing': 'Contract Source → Compatibility Check → Consumer Contract Tests → Runtime Validation → Rollout',
    'active_active_financial_write': 'Region API → Operation State Machine → Single Writer/Ledger → Replication/Read Model → Reconciliation',
    'privacy_erasure_pipeline': 'Erasure Request API → Policy/Legal Hold Check → Per-System Erasure Tasks → Receipts → Audit/Reconciliation',
    'highload_stream_ingestion': 'Producers → Event Stream Partitions → Stream Processing → Idempotent Sink → Alerting/Consumers → DWH Downstream',
    'multi_tenant_noisy_neighbor': 'Shared Stream → Tenant-aware Consumer Pool → Per-tenant Quotas → Isolated Sink/Inbox → Lag Metrics',
    'strangler_migration': 'Client/System → Facade → New Service + Legacy → Shadow Compare → Feature Flag Cutover → Rollback/Reconciliation',
    'existing_solution_audit': 'Current Solution → Risk Review → Keep/Fix Decisions → Phased Remediation → Regression Tests',
}

def custom_schema_from_form(form):
    """Return user-built chain schema from no-text constructor payload if present."""
    form = form or {}
    raw = form.get('custom_chain_json') or ''
    if raw:
        try:
            data = json.loads(raw)
            schema = (data or {}).get('schema')
            if schema:
                return str(schema)
        except Exception:
            pass
    raw_graph = form.get('process_graph_json') or ''
    if raw_graph:
        try:
            data = json.loads(raw_graph)
            schema = (data or {}).get('schema')
            if schema:
                return str(schema)
        except Exception:
            pass
    goal = str(form.get('business_goal') or '')
    prefix = 'Пользователь собрал цепочку:'
    if prefix in goal:
        return goal.split(prefix, 1)[1].strip()
    return ''

def ordered_business_steps_from_form(form):
    """Return business-first steps sorted by explicit order/array position."""
    form = form or {}
    raw = form.get('business_steps_json') or ''
    steps = []
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                steps = data
        except Exception:
            steps = []
    if not steps:
        raw_process = form.get('business_process_json') or ''
        try:
            data = json.loads(raw_process) if raw_process else {}
            if isinstance(data, dict) and isinstance(data.get('steps'), list):
                steps = data.get('steps') or []
        except Exception:
            steps = []
    normalized = []
    for i, item in enumerate(steps):
        if not isinstance(item, dict):
            continue
        actor = str(item.get('actorLabel') or item.get('actor') or 'Система')
        action = str(item.get('action') or 'выполняет шаг')
        obj = str(item.get('object') or '').strip()
        try:
            order = int(item.get('order') or (i + 1))
        except Exception:
            order = i + 1
        normalized.append({'order': order, 'actorLabel': actor, 'action': action, 'object': obj})
    normalized.sort(key=lambda x: x.get('order') or 0)
    for i, item in enumerate(normalized, 1):
        item['order'] = i
    return normalized

def ordered_business_process_text(form):
    steps = ordered_business_steps_from_form(form)
    if steps:
        return '\n'.join(f"{s['order']}. {s['actorLabel']} {s['action'].lower()}{(' — ' + s['object']) if s.get('object') else ''}." for s in steps)
    process_json = str((form or {}).get('business_process_json') or '')
    if process_json:
        try:
            data = json.loads(process_json)
            if isinstance(data, dict) and data.get('schema'):
                return str(data.get('schema'))
        except Exception:
            pass
    return (form.get('business_goal') or '').strip() if form else ''

def business_order_warnings_from_form(form):
    form = form or {}
    warnings = []
    for raw_key in ['business_process_json', 'auto_generated_technical_chain_json', 'process_graph_json']:
        raw = form.get(raw_key) or ''
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get('warnings'), list):
                warnings.extend(str(x) for x in data.get('warnings') if str(x).strip())
        except Exception:
            pass
    steps = ordered_business_steps_from_form(form)
    actions = [f"{s.get('actorLabel','')} {s.get('action','')} {s.get('object','')}".lower() for s in steps]
    def idx(fragment):
        fragment = fragment.lower()
        for i, text in enumerate(actions):
            if fragment in text:
                return i
        return -1
    transfer, check = idx('передаёт данные дальше'), idx('проверяет данные')
    if transfer >= 0 and check >= 0 and transfer < check:
        warnings.append('Данные передаются до проверки. Проверьте, допустимо ли это.')
    upd, later = idx('обновляет статус'), idx('получает ответ позже')
    if upd >= 0 and later >= 0 and upd < later:
        warnings.append('Статус обновляется до получения финального ответа. Возможно, нужен промежуточный статус.')
    comp, manual, status = idx('компенсирует'), idx('ручной разбор'), idx('статус')
    if comp >= 0 and manual < 0 and status < 0:
        warnings.append('Есть компенсация, но не указан ручной разбор или статусная модель.')
    report, finish = idx('отчётность'), idx('завершает процесс')
    if report >= 0 and finish >= 0 and report < finish:
        warnings.append('Данные уходят в отчётность до завершения процесса. Нужен признак актуальности/финальности.')
    if idx('получает ответ позже') >= 0 and str(form.get('simple_q_status') or 'Да') == 'Нет':
        warnings.append('Есть отложенный ответ, но статус процесса не нужен. Проверьте, как пользователь узнает результат.')
    # stable unique preserving order
    out = []
    for w in warnings:
        if w and w not in out:
            out.append(w)
    return out


def _json_list_field(form, key):
    raw = (form or {}).get(key, [])
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    if isinstance(raw, str) and raw.strip().startswith('['):
        try:
            data=json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
        except Exception:
            pass
    return _as_list(raw)

def business_constraints_from_form(form):
    form=form or {}
    values=[]
    values.extend(_json_list_field(form, 'business_constraints_json'))
    values.extend(_json_list_field(form, 'constraint_flags'))
    values.extend(_as_list(form.get('forbidden_channels', [])))
    out=[]
    alias={'source_locked':'source_change_forbidden','no_new_topic':'new_topic_forbidden','no_new_service':'new_service_too_expensive'}
    for v in values:
        v=str(v).strip()
        v=alias.get(v, v)
        if v and v not in out:
            out.append(v)
    return out

def validate_actor_action_pairs(form):
    warnings=[]
    for s in ordered_business_steps_from_form(form):
        actor=str(s.get('actorLabel') or '').lower()
        action=str(s.get('action') or '').lower()
        if any(x in actor for x in ['клиент','пользователь']):
            if 'принимает заявку' in action:
                warnings.append('Клиент обычно создаёт/отправляет заявку, а принимает её внутренняя система.')
            if 'проверяет данные' in action:
                warnings.append('Проверку обычно выполняет система или сотрудник.')
            if 'обновляет статус' in action:
                warnings.append('Статус процесса обычно обновляет система.')
        if 'внешняя система' in actor and 'принимает заявку' in action:
            warnings.append('Если внешняя система принимает заявку, уточните, кто владелец процесса и статуса.')
    out=[]
    for w in warnings:
        if w not in out: out.append(w)
    return out

def build_scenario_facets_from_business(form):
    """Server-side twin of JS buildScenarioFacetsFromBusiness: business input -> legacy engine facets."""
    form=dict(form or {})
    situations=list(_as_list(form.get('business_situations', [])))
    def add(*xs):
        for x in xs:
            if x and x not in situations: situations.append(x)
    constraints=set(business_constraints_from_form(form))
    bcase=str(form.get('business_case') or '').strip()
    timing=str(form.get('business_result_timing') or form.get('simple_q_immediate') or '')
    result=str(form.get('business_result_type') or '')
    obj=str(form.get('business_object') or '')
    risk=str(form.get('business_criticality') or form.get('simple_q_risk') or '')
    steps=ordered_business_steps_from_form(form)
    step_text=' '.join([f"{x.get('actorLabel','')} {x.get('action','')} {x.get('object','')}" for x in steps] + [str(form.get('business_goal') or ''), str(form.get('quick_description') or '')]).lower()
    actor_text=' '.join(s.get('actorLabel','') for s in steps).lower()
    if bcase=='application_creation' or 'созда' in step_text and 'заяв' in step_text:
        add('application_or_order_creation')
        form.setdefault('operation_kind','command_create_update')
        if 'позже' in timing.lower() or 'позже' in step_text:
            add('multi_step_business_process','async_heavy_processing','long_running_process')
            form.setdefault('result_model','tracking')
    if bcase=='data_change_distribution' or 'несколько получателей' in actor_text or 'many_consumers' in constraints:
        add('data_synchronization','one_source_many_consumers')
        form['operation_kind']='event_publish'; form.setdefault('result_model','notification')
        form['allowed_channels']=sorted(set(_as_list(form.get('allowed_channels', [])))|{'kafka','queue'})
        if 'new_topic_forbidden' in constraints:
            add('shared_topic_selective_consumer'); form['kafka_topology']='single_topic_only'
        if 'highload' in constraints:
            add('highload_write_stream','peak_load_process')
    if bcase=='data_enrichment' or 'дополняет' in step_text or 'обогащ' in step_text or 'справоч' in obj.lower():
        add('data_enrichment','event_enrichment_before_publish')
        form['operation_kind']='event_enrichment'
        if 'source_change_forbidden' in constraints or 'source_locked' in constraints:
            add('source_lacks_kafka'); form['source_change_policy']='minimal_table_only'
    if bcase=='external_check' and ('позже' in timing.lower() or 'ответит позже' in timing.lower()) or 'получает ответ позже' in step_text or 'callback_webhook' in constraints:
        add('external_api_dependency','webhook_callback')
        form['result_model']='callback'; form['task_type']='external_partner'
        if 'unstable_external' in constraints: add('unstable_external_provider')
    if bcase=='status_screen' or 'несколько систем' in actor_text or 'собирает статус' in step_text or 'many_sources' in constraints:
        add('client_status_screen','multi_source_aggregation','api_composition','read_model')
        form['operation_kind']='bff_composition'; form['partial_response_ok']='yes'
        if 'highload' in constraints: add('highload_read')
    if bcase=='reporting' or 'отчёт' in step_text or 'отчет' in step_text:
        add('dwh_reporting','batch_processing')
        form['operation_kind']='dwh_offload'; form['task_type']='dwh_analytics'; form['replay']='yes'; form['retention']='required'
    if bcase=='legacy_file' or 'файл' in obj.lower() or 'файл' in step_text or 'старая система' in actor_text:
        add('legacy_integration','batch_processing')
        form['operation_kind']='batch_file_exchange'
    if bcase=='audit':
        add('existing_solution_audit'); form['task_type']='audit_existing_solution'
    if bcase=='long_process' or 'compensation' in constraints or 'компенс' in step_text or 'откат' in step_text:
        add('long_running_process','distributed_transaction_saga','multi_step_business_process','manual_recovery_required')
        form['orchestration']='orchestrator'; form['result_model']='tracking'
    if 'contract_change' in constraints or 'required_field' in constraints or any(x in step_text for x in ['контракт','обязательное поле','ошибка маппинга','duplicate response']):
        add('contract_breaking_change','contract_required_field_missing'); form['task_type']='contract_change'
    if 'money' in constraints or 'деньг' in risk.lower() or form.get('money_impact')=='yes':
        add('financial_operation'); form['money_impact']='yes'
    if 'regulatory' in constraints or 'pii' in constraints:
        if 'regulatory' in constraints: add('regulatory_process'); form['regulatory_impact']='yes'
        if 'pii' in constraints: add('personal_data_exchange'); form['sensitivity']='personal'
    if ('money' in constraints or form.get('money_impact')=='yes') and 'highload' in constraints and 'active_active' in constraints:
        add('active_active_financial_write','financial_operation','exactly_once_required'); form['delivery']='business_exactly_once'; form['consistency']='strong_on_write'
    if 'privacy_erasure' in constraints or (('pii' in constraints or 'regulatory' in constraints) and any(x in step_text for x in ['удал','исправ'])):
        add('privacy_erasure','personal_data_exchange','regulatory_process')
    if 'highload' in constraints and ('event_publish'==form.get('operation_kind') or 'event' in step_text or 'событ' in step_text):
        add('highload_stream_ingestion','highload_write_stream'); form['load_profile']='highload'
    if 'multi_tenant' in constraints:
        add('multi_tenant_noisy_neighbor','shared_topic_selective_consumer')
    if 'migration' in constraints:
        add('migration_or_strangler','legacy_integration'); form['task_type']='replace_legacy'
    if 'replay' in constraints: form['replay']='yes'
    if 'Потерять данные' in risk or 'Получить дубль' in risk or 'exactly_once' in constraints:
        form['delivery']='business_exactly_once'
    form['step_count']=form.get('step_count') or str(len(steps) or '')
    form['chain_depth']=form.get('chain_depth') or ('multi_level' if len(steps)>=4 else 'single_level')
    form['business_situations']=situations
    form['forbidden_channels']=sorted(set(_as_list(form.get('forbidden_channels', []))) | {c for c in constraints if c in ['new_topic_forbidden','source_change_forbidden','new_service_too_expensive']})
    actor_warnings=validate_actor_action_pairs(form)
    if actor_warnings:
        existing=business_order_warnings_from_form(form)
        try:
            raw=json.loads(form.get('business_process_json') or '{}')
            if isinstance(raw, dict):
                raw['warnings'] = list(dict.fromkeys((raw.get('warnings') or []) + actor_warnings))
                form['business_process_json']=json.dumps(raw, ensure_ascii=False)
        except Exception:
            pass
    return form

def specialized_case_from_form(form, base_case_type=None):
    f=build_scenario_facets_from_business(form)
    active=set(_as_list(f.get('business_situations', [])))
    constraints=set(business_constraints_from_form(f)) | set(_as_list(f.get('forbidden_channels', [])))
    if 'active_active_financial_write' in active: return 'active_active_financial_write'
    if 'privacy_erasure' in active: return 'privacy_erasure_pipeline'
    if 'multi_tenant_noisy_neighbor' in active: return 'multi_tenant_noisy_neighbor'
    if 'migration_or_strangler' in active: return 'strangler_migration'
    if 'contract_required_field_missing' in active or 'contract_breaking_change' in active: return 'contract_required_field_missing'
    if 'shared_topic_selective_consumer' in active or 'new_topic_forbidden' in constraints and 'one_source_many_consumers' in active: return 'shared_topic_selective_consumer'
    if 'event_enrichment_before_publish' in active or 'data_enrichment' in active and (base_case_type=='enrichment_kafka' or f.get('operation_kind')=='event_enrichment'): return 'enrichment_before_kafka'
    if 'webhook_callback' in active: return 'webhook_intake'
    if 'distributed_transaction_saga' in active or 'long_running_process' in active and 'multi_step_business_process' in active: return 'saga_state_machine'
    if 'client_status_screen' in active or 'multi_source_aggregation' in active or 'api_composition' in active: return 'bff_api_composition'
    if 'highload_stream_ingestion' in active: return 'highload_stream_ingestion'
    if 'dwh_reporting' in active: return 'dwh_pipeline'
    if 'legacy_integration' in active and 'batch_processing' in active: return 'batch_file_exchange'
    if 'existing_solution_audit' in active: return 'existing_solution_audit'
    return base_case_type or detect_case_type(f)

def build_canonical_schema_for_case(case_type, case_classes=None, business_steps=None, constraints=None):
    return CANONICAL_CASE_SCHEMAS.get(case_type) or CASE_SCHEMAS.get(case_type) or CASE_SCHEMAS['sync_rest']

def case_specific_handoff(case_class, base_case_type=None):
    m={
      'async_worker':['POST endpoint contract','202 Accepted + trackingId','GET /status contract','integration_task DDL','status model','idempotency unique constraint','worker retry policy','manual recovery procedure','stuck task monitoring','тесты duplicate/timeout/retry/status'],
      'event_kafka':['event schema','outbox DDL','publisher rules','partition/key strategy','consumer inbox DDL','DLQ/reprocess','schema compatibility tests','lag metrics'],
      'shared_topic_selective_consumer':['filtering rules','discard rate metric','consumer lag','per-message decision log','DLQ/reprocess','idempotent sink'],
      'enrichment_before_kafka':['source-owned fact contract','Integration Publisher rules','REST enrichment API contract','dataAsOf/freshness policy','enrichmentConsistency rules','FAILED/reprocess procedure','event ownership decision'],
      'webhook_intake':['external request contract','callback endpoint contract','auth/signature validation','raw body preservation','inbox DDL','idempotent callback transition','timeout/polling fallback'],
      'saga_state_machine':['process state model','step status matrix','compensation matrix','compensation_failed process','manual recovery owner','audit trail','partial success tests'],
      'bff_api_composition':['BFF contract','per-source timeout policy','partial response contract','freshness marker/dataAsOf','cache/read model rules','read-your-writes policy'],
      'dwh_pipeline':['export/CDC contract','watermark','staging DDL','data quality rules','reconciliation rules','backfill procedure','retention/archive policy'],
      'batch_file_exchange':['file format','manifest/checksum','file registry DDL','validation rules','quarantine process','reprocessing procedure','ack/error file contract'],
      'contract_required_field_missing':['OpenAPI/AsyncAPI diff','required fields matrix','consumer-driven contract tests','examples success/duplicate/error','compatibility policy','rollout/migration plan'],
      'privacy_erasure_pipeline':['erasure request contract','legal hold decision matrix','per-system erasure receipt','audit log','retention exceptions','reconciliation report'],
      'active_active_financial_write':['operation ledger','single writer decision','idempotency key','reconciliation','split-brain handling','manual correction procedure'],
      'multi_tenant_noisy_neighbor':['tenantId key','per-tenant quotas','per-tenant lag metrics','consumer pool isolation','noisy neighbor alerts'],
      'strangler_migration':['facade contract','parallel run plan','shadow compare report','feature flags','rollback plan','reconciliation rules'],
      'highload_stream_ingestion':['partitioning/key strategy','backpressure policy','lag metrics','replay procedure','out-of-order handling','stream processing contract'],
      'existing_solution_audit':['risk register','what to keep','mandatory fixes','blockers','phased remediation plan','current-solution regression tests'],
    }
    return m.get(case_class) or m.get(base_case_type or '', required_items_for_case(base_case_type or 'sync_rest'))

def case_class_narrative(case_class, base_case_type, form):
    active=', '.join(_as_list((form or {}).get('business_situations', []))[:8])
    labels={
      'saga_state_machine':'long-running process / saga state machine',
      'shared_topic_selective_consumer':'shared topic filtering / selective consumer',
      'enrichment_before_kafka':'REST enrichment before Kafka / Integration Publisher',
      'webhook_intake':'webhook/callback intake',
      'bff_api_composition':'BFF/API Composition fan-in',
      'dwh_pipeline':'DWH pipeline / operational offload',
      'batch_file_exchange':'legacy batch/file exchange',
      'contract_required_field_missing':'contract-first required field change',
      'active_active_financial_write':'active-active financial write guard',
      'privacy_erasure_pipeline':'privacy erasure / legal hold pipeline',
      'multi_tenant_noisy_neighbor':'multi-tenant noisy-neighbor stream',
      'strangler_migration':'migration / strangler',
      'highload_stream_ingestion':'highload stream ingestion',
      'existing_solution_audit':'existing solution audit',
    }
    label=labels.get(case_class, case_class)
    reason=active or 'business-first признаки и ограничения'
    return f'Базовый case_type: {base_case_type}. Распознанный сложный кейс: {case_class} ({label}). Почему: {reason}. Это меняет решение: схема, must-have, риски и handoff выбираются по специализированному кейсу, а не по generic-шаблону.'


def specialized_case_summary(specialized_case, base_case_type, form):
    summaries={
        'saga_state_machine':'Базово это async-процесс, но из-за многошаговости, денег/договоров и компенсации это не просто worker, а управляемая state machine. Поэтому нужны Process State DB, статусы шагов, retry per step, compensation_failed и manual recovery.',
        'shared_topic_selective_consumer':'Так как новый поток/topic запрещён или один поток читают разные потребители, используется общий поток и selective consumer. Поэтому нужны filtering rules, discard rate, consumer lag, per-message decision log, DLQ/reprocess и идемпотентный sink.',
        'enrichment_before_kafka':'Так как перед публикацией нужны дополнительные данные, а source менять нельзя/дорого, нужен source-owned outbox и Integration Publisher/enrichment adapter с REST Enrichment API, dataAsOf, freshness и enrichmentConsistency.',
        'webhook_intake':'Так как внешний провайдер отвечает позже, основной запрос нельзя считать синхронным. Нужны Callback API, quick ack, signature validation, raw body preservation, Inbox и idempotent callback transition с timeout/polling fallback.',
        'bff_api_composition':'Это не запись, а fan-in/read path для экрана. Поэтому нужны BFF/API Composition, per-source timeout, partial response, freshness marker/dataAsOf, cache/read model и read-your-writes policy.',
        'dwh_pipeline':'Это отчётный/offload-контур, который не должен блокировать operational flow. Поэтому нужны CDC/export, watermark, staging, data quality, lineage, reconciliation, backfill и retention/archive.',
        'batch_file_exchange':'Это legacy batch/file exchange, поэтому нужны file_id, manifest/checksum, batch_id, file registry, staging validation, quarantine, ack/error file и reprocessing.',
        'contract_required_field_missing':'Это contract-first изменение, а не проектирование с нуля. Поэтому source of truth — OpenAPI/AsyncAPI, required fields gate, consumer-driven contract tests, compatibility policy и rollout/migration plan.',
        'active_active_financial_write':'Финансовая запись в нескольких регионах не может быть обычным event/async. Нужны single writer или ledger, idempotency key, strong write decision, reconciliation, split-brain handling и защита от double spend.',
        'privacy_erasure_pipeline':'Удаление/исправление ПДн — regulatory workflow. Нужны erasure request id, legal hold decision, per-system erasure tasks, receipts, retention exceptions, audit и reconciliation.',
        'highload_stream_ingestion':'Highload stream ingestion требует проектирования потока: partitioning/key strategy, backpressure, lag monitoring, replay, out-of-order handling, idempotent sink и downstream DWH только как потребитель.',
        'multi_tenant_noisy_neighbor':'В общем потоке много tenants, значит нужен tenantId key, per-tenant quotas, lag isolation, consumer pool isolation и noisy-neighbor monitoring, иначе один tenant создаст lag всем.',
        'strangler_migration':'Это migration/strangler, поэтому нужна facade, parallel run, shadow compare, feature flags, rollback и reconciliation, а не одномоментная замена legacy.',
        'existing_solution_audit':'Это аудит текущего решения: надо выделить что оставить, что исправить обязательно, blockers, phased remediation и regression tests для существующей схемы.',
    }
    return summaries.get(specialized_case) or case_summary(form, base_case_type)

def risks_for_specialized_case(specialized_case, base_case_type=None, form=None):
    m={
        'saga_state_machine':[
            ('partial success без модели состояний','часть шагов выполнена, но владелец восстановления непонятен','Process State DB, step status matrix, compensation_failed и manual recovery owner'),
            ('компенсация не сработала','деньги/резервы/договоры остаются в подвешенном состоянии','compensation matrix, audit trail и ручной recovery queue'),
        ],
        'shared_topic_selective_consumer':[
            ('неявная фильтрация общего потока','consumer молча отбрасывает нужные/лишние события','filtering rules, discard rate metric и per-message decision log'),
            ('consumer lag и DLQ без владельца','общий topic создаёт задержки и повторную обработку','consumer lag alerting, DLQ/reprocess и idempotent sink'),
        ],
        'enrichment_before_kafka':[
            ('устаревшее enrichment-значение','событие публикуется с неверной свежестью данных','dataAsOf, freshness SLA и enrichmentConsistency'),
            ('REST enrichment недоступен','publisher зависает или теряет событие','FAILED/reprocess, retry budget и owner события'),
        ],
        'webhook_intake':[
            ('поддельный или повторный callback','статус меняется чужим/дублирующим сообщением','signature validation, raw body preservation, Inbox и idempotent callback transition'),
            ('callback не пришёл','процесс зависает без финального статуса','timeout ожидания, polling fallback и reconciliation'),
        ],
        'bff_api_composition':[
            ('один источник валит весь экран','пользователь не видит даже доступные данные','per-source timeout, fallback и partial response'),
            ('непонятная свежесть блоков','экран показывает устаревшие данные как финальные','freshness marker/dataAsOf, cache/read model и projection lag'),
        ],
        'dwh_pipeline':[
            ('потеря полноты выгрузки','отчёт строится на неполных данных','watermark, staging quality checks и reconciliation'),
            ('невозможен backfill','ошибку в DWH нельзя восстановить','lineage, replay/backfill и retention/archive policy'),
        ],
        'batch_file_exchange':[
            ('файл обработан частично/повторно','данные загружаются дублями или теряются','manifest/checksum, batch_id и file registry'),
            ('грязные записи попали в target','legacy-ошибка ломает целевую систему','validation, quarantine, ack/error file и reprocessing'),
        ],
        'contract_required_field_missing':[
            ('breaking change проходит в runtime','consumer падает из-за required field/mapping','OpenAPI/AsyncAPI diff, required fields gate и consumer-driven contract tests'),
            ('несовместимый rollout','часть consumers получает новую схему раньше готовности','compatibility policy, examples и migration plan'),
        ],
        'active_active_financial_write':[
            ('split-brain финансовой записи','два региона одновременно меняют один баланс','single writer/ledger, conflict policy и reconciliation'),
            ('double spend при retry','повтор команды меняет баланс второй раз','idempotency key, operation ledger и manual correction procedure'),
        ],
        'privacy_erasure_pipeline':[
            ('удаление вопреки legal hold','регуляторный/юридический инцидент','legal hold decision matrix и retention exceptions'),
            ('нет доказательства удаления','невозможно подтвердить исполнение запроса субъекта','per-system erasure receipt, audit log и reconciliation report'),
        ],
        'multi_tenant_noisy_neighbor':[
            ('noisy neighbor','крупный tenant создаёт lag для остальных','tenantId key, per-tenant quotas и consumer pool isolation'),
            ('общие метрики скрывают проблему tenant','SLA одного клиента нарушается незаметно','per-tenant lag metrics и alerts'),
        ],
        'strangler_migration':[
            ('big-bang cutover','новый контур нельзя безопасно откатить','facade, feature flags и rollback plan'),
            ('расхождения legacy/new незаметны','данные расходятся в parallel run','shadow compare и reconciliation rules'),
        ],
        'highload_stream_ingestion':[
            ('hot partition/backpressure','поток копит lag и теряет SLA','partitioning/key strategy, backpressure и lag alerts'),
            ('out-of-order replay ломает sink','повторная обработка меняет результат','out-of-order handling, replay procedure и idempotent sink'),
        ],
    }
    return m.get(specialized_case) or risks_for_case(base_case_type or 'sync_rest')

def merge_readiness(business_readiness, legacy_readiness=None, blockers=None):
    b=dict(business_readiness or {})
    l=dict(legacy_readiness or {})
    blockers=list(blockers or [])
    bs=int(b.get('score', 100) or 0)
    ls=int(l.get('score', bs) or bs)
    score=min(bs, ls) if blockers or l else bs
    if blockers:
        score=min(score, 60)
    status='RED' if score < 40 else ('YELLOW' if score < 70 else 'GREEN')
    b['score']=score; b['status']=status; b['blockers']=blockers or b.get('blockers', [])
    return b

def _case_text(form, keys):
    values=[]
    for k in keys:
        v=(form or {}).get(k, '')
        if isinstance(v, (list, tuple, set)):
            values.extend(str(x) for x in v)
        else:
            values.append(str(v))
    return ' '.join(values).lower()


def _detect_from_text(text):
    text=(text or '').lower()
    if any(x in text for x in ['обогат', 'enrich', 'дополнить']) and any(x in text for x in ['kafka', 'событие', 'event', 'топик', 'topic']):
        return 'enrichment_kafka'
    if 'consumer фильтрует' in text or 'фильтрует только нужные' in text or 'общий kafka topic' in text:
        return 'event_kafka'
    if any(x in text for x in ['callback', 'коллбек', 'ответит позже', 'внешняя система ответит']):
        return 'callback'
    if any(x in text for x in ['legacy', 'легаси', 'файл', 'file', 'sftp', 'checksum']):
        return 'legacy_file'
    if any(x in text for x in ['собрать статус', 'статус из нескольких', 'api composition', 'bff', 'read model', 'read-model']):
        return 'status_aggregation'
    if any(x in text for x in ['dwh', 'отчетность', 'отчётность', 'витрина', 'хранилище']):
        return 'dwh'
    if any(x in text for x in ['worker', 'воркер', 'асинхрон', 'позже', 'сохранить задачу', 'tracking', 'trackingid', 'обработать позже']):
        return 'async_worker'
    if any(x in text for x in ['kafka', 'событие', 'event', 'топик', 'topic', 'outbox']):
        return 'event_kafka'
    if any(x in text for x in ['проверить существующее', 'аудит', 'текущее решение']):
        return 'audit'
    return ''


def detect_case_type(form, ctx=None, res=None):
    """Detect case type from explicit simple wizard answers first, then free text.

    Old demo defaults and generated technical markdown are intentionally ignored here.
    """
    situation_map={
        'sync_rest':'sync_rest', 'async_worker':'async_worker', 'event_kafka':'event_kafka',
        'enrichment_kafka':'enrichment_kafka', 'callback':'callback', 'dwh':'dwh',
        'legacy_file':'legacy_file', 'shared_topic':'event_kafka', 'status_aggregation':'status_aggregation',
    }
    simple_situation=str((form or {}).get('simple_situation','')).strip()
    if simple_situation in situation_map:
        return situation_map[simple_situation]

    quick_text=_case_text(form, ['quick_description','quick_goal','simple_q_payload','simple_q_immediate','simple_q_error','simple_q_status'])
    detected=_detect_from_text(quick_text)
    if detected:
        return detected

    task_type=str((form or {}).get('task_type','')).lower()
    if task_type == 'audit_existing_solution': return 'audit'
    if task_type in ['dwh_analytics','data_migration']: return 'dwh'
    if task_type in ['event_domain']: return 'event_kafka'
    if task_type in ['external_partner'] and 'callback' in quick_text: return 'callback'

    matrix_text=_case_text(form, ['systems_matrix','process_steps','target_integration_matrix','contract_matrix','error_matrix','process_flow_matrix','current_solution_description'])
    detected=_detect_from_text(matrix_text)
    if detected:
        return detected

    fallback=_case_text(form, ['business_goal','preset_name'])
    return _detect_from_text(fallback) or 'sync_rest'

def required_items_for_case(case_type):
    return {
        'sync_rest': ['REST-контракт', 'timeout', 'error mapping', 'correlationId', 'валидация входных данных', 'contract tests', 'логирование'],
        'async_worker': ['trackingId', 'integration_task DB', 'статусы NEW / IN_PROGRESS / RETRY / SUCCESS / FAILED', 'idempotencyKey', 'correlationId', 'Worker', 'retry limit', 'manual recovery', 'monitoring stuck tasks', 'GET /status или аналог проверки статуса'],
        'event_kafka': ['transactional outbox', 'eventId', 'aggregateId', 'occurredAt', 'version', 'publisher', 'Kafka topic', 'consumer', 'inbox/idempotency', 'retry', 'DLQ/manual recovery', 'schema validation', 'consumer lag'],
        'enrichment_kafka': ['Обогащать в source', 'Публиковать минимальное событие и обогащать у consumer', 'Enrichment-worker', 'Adapter/orchestrator', 'минимальное событие', 'контроль свежести данных', 'retry REST-обогащения', 'fallback при недоступности enrichment-сервиса', 'outbox/inbox при Kafka', 'компромиссы по связности и стоимости'],
        'callback': ['requestId/trackingId', 'callback endpoint', 'проверка подписи/авторизации', 'idempotency callback', 'status DB', 'timeout ожидания', 'polling fallback', 'audit'],
        'dwh': ['batch/CDC mode', 'watermark', 'deduplication', 'reconciliation', 'data quality checks', 'lineage', 'reload/backfill', 'контроль полноты'],
        'legacy_file': ['file_id', 'checksum', 'batch_id', 'file registry', 'validation', 'quarantine', 'reprocessing', 'manual recovery'],
        'status_aggregation': ['BFF/API Composition contract', 'таймауты к Service A / Service B / Service C', 'частичный ответ', 'Cache/Read Model', 'freshness marker', 'correlationId', 'fallback для недоступной системы', 'метрики latency/error по каждому источнику'],
        'audit': ['текущая схема', 'risk register', 'найденные риски', 'критичность рисков', 'варианты исправления', 'варианты улучшения', 'компромиссы', 'что оставить как есть', 'что исправить обязательно'],
    }.get(case_type, [])

def _meaningful_answer(value):
    v=str(value or '').strip().lower()
    return bool(v) and v not in {'unknown','не знаю','пока не знаю','not_defined','none','unclear',''}


def simple_readiness(form, ctx=None):
    form=form or {}
    goal_ok=_meaningful_answer(form.get('simple_goal') or form.get('quick_goal')) or _meaningful_answer(form.get('business_goal') or form.get('quick_description'))
    situation_ok=_meaningful_answer(form.get('simple_situation')) or _detect_from_text(_case_text(form, ['business_goal','quick_description','process_steps','target_integration_matrix'])) != ''
    systems_ok=_meaningful_answer(form.get('simple_q_systems')) or _meaningful_answer(form.get('systems_matrix')) or bool((ctx or {}).get('systems'))
    has_process=_meaningful_answer(form.get('process_steps')) or _meaningful_answer(form.get('target_integration_matrix'))
    immediate_ok=_meaningful_answer(form.get('simple_q_immediate')) or (has_process and _meaningful_answer(form.get('result_model')))
    payload_ok=_meaningful_answer(form.get('simple_q_payload')) or _meaningful_answer(form.get('fields')) or _meaningful_answer(form.get('main_entity'))
    risk_ok=_meaningful_answer(form.get('simple_q_risk')) or _meaningful_answer(form.get('error_matrix'))
    error_ok=_meaningful_answer(form.get('simple_q_error')) or _meaningful_answer(form.get('error_matrix')) or (has_process and any(x in str(form.get('process_steps','')).lower() for x in ['retry','manual','dlq','ошиб']))
    status_ok=_meaningful_answer(form.get('simple_q_status')) or _meaningful_answer(form.get('statuses')) or (has_process and _meaningful_answer(form.get('result_model')))
    checks=[
        ('цель интеграции', goal_ok),
        ('ситуация', situation_ok),
        ('участвующие системы', systems_ok),
        ('ожидаемый ответ сразу или позже', immediate_ok),
        ('что передаём', payload_ok),
        ('главный риск', risk_ok),
        ('обработка ошибок', error_ok),
        ('нужен ли статус процесса', status_ok),
    ]
    done=[name for name,ok in checks if ok]
    missing=[name for name,ok in checks if not ok]
    score=round(len(done)/len(checks)*100)
    if score <= 40:
        return {'score': score, 'level': 'draft', 'button': 'Сформировать черновик', 'warning': 'Недостаточно данных для архитектурного вывода', 'missing': missing}
    if score < 70:
        return {'score': score, 'level': 'preliminary', 'button': 'Сформировать предварительный отчёт', 'warning': 'Отчёт предварительный. Перед разработкой нужно уточнить открытые вопросы.', 'missing': missing + ['точные SLA/таймауты', 'владельцы ручного разбора', 'лимиты retry', 'объём нагрузки']}
    return {'score': score, 'level': 'full', 'button': 'Сформировать полный отчёт', 'warning': '', 'missing': missing or ['нет критичных неизвестных']}


def technical_details_for_case(case_type):
    details={
        'sync_rest': ['REST-контракт', 'HTTP method/path', 'request/response schema', 'timeout', 'error mapping', 'correlationId', 'idempotencyKey только для небезопасных повторов', 'валидация входных данных', 'contract testing', 'логирование'],
        'async_worker': ['trackingId', 'integration_task DB', 'Worker', 'статусы NEW / IN_PROGRESS / RETRY / SUCCESS / FAILED', 'idempotencyKey', 'correlationId', 'retry policy', 'manual recovery', 'GET /status', 'monitoring stuck tasks'],
        'event_kafka': ['transactional Outbox', 'Publisher', 'Kafka topic', 'eventId', 'aggregateId', 'occurredAt', 'version', 'Consumer', 'Inbox/idempotency', 'retry topic', 'DLQ/manual recovery', 'schema validation', 'consumer lag'],
        'enrichment_kafka': ['минимальное событие', 'enrichment-worker/adaptor', 'REST enrichment timeout/retry', 'fallback', 'контроль свежести данных', 'outbox/inbox при Kafka', 'компромиссы source vs consumer enrichment'],
        'callback': ['requestId/trackingId', 'External API ack', 'callback endpoint', 'signature/auth validation', 'idempotency callback', 'Status DB', 'timeout ожидания', 'polling fallback', 'audit log'],
        'dwh': ['batch/CDC mode', 'watermark', 'staging', 'deduplication', 'reconciliation', 'data quality checks', 'lineage', 'reload/backfill', 'контроль полноты'],
        'legacy_file': ['file_id', 'checksum', 'batch_id', 'file registry', 'file schema validation', 'quarantine', 'reprocessing', 'manual recovery', 'ack/receipt file', 'audit log'],
        'status_aggregation': ['BFF/API Composition', 'parallel calls', 'per-dependency timeout', 'partial response policy', 'Cache/Read Model', 'freshness marker', 'fallback', 'correlationId', 'latency/error metrics'],
        'audit': ['текущая схема', 'risk register', 'severity', 'варианты улучшения', 'компромиссы', 'что оставить как есть', 'обязательные исправления'],
    }
    return details.get(case_type, details['sync_rest'])

def case_summary(form, case_type):
    schema=custom_schema_from_form(form) or CASE_SCHEMAS.get(case_type, CASE_SCHEMAS['sync_rest'])
    if case_type == 'async_worker':
        return ('Service 1 отправляет запрос в Service 2. Service 2 принимает запрос, сохраняет задачу и возвращает trackingId. Worker внутри Service 2 читает integration_task DB и асинхронно вызывает Service 3. Результат не нужно возвращать сразу. Главные риски: дубли, потеря задачи, недоступность Service 3, зависшие статусы.')
    if case_type == 'event_kafka':
        return ('Source Service фиксирует бизнес-изменение в Business DB, сохраняет событие в transactional Outbox и Publisher отправляет его в Kafka. Consumer читает событие, проверяет inbox/idempotency и обновляет Target DB. Главные риски: потеря события, дубли, несовместимая схема, рост consumer lag.')
    if case_type == 'enrichment_kafka':
        return ('Перед публикацией/потреблением события нужно добавить данные из другого сервиса. Базовый поток: Source Service публикует минимальное событие через Outbox в Kafka, а Enrichment Worker или Adapter получает недостающие данные и передаёт результат в Target Service. Главные риски: связность с сервисом обогащения, свежесть данных, недоступность REST-обогащения, стоимость изменений в Source.')
    if case_type == 'callback':
        return ('Internal Service отправляет запрос во External API и сохраняет requestId/trackingId в Status DB. Внешняя система отвечает позже на Callback API. Callback проверяется по подписи/авторизации, обрабатывается идемпотентно и обновляет статус.')
    if case_type == 'dwh':
        return ('Source System передаёт данные в отчётный контур через Export/CDC, Staging принимает и проверяет набор, DWH строит витрины, а Reconciliation контролирует полноту и расхождения.')
    if case_type == 'legacy_file':
        return ('Legacy System выгружает файл, интеграционный слой регистрирует file_id/batch_id, проверяет checksum и структуру, валидные записи передаёт в Target System, а ошибки кладёт в quarantine с возможностью reprocessing/manual recovery.')
    if case_type == 'status_aggregation':
        return ('Client/UI запрашивает статус в BFF/API Composition. BFF параллельно обращается к Service A, Service B и Service C, применяет таймауты и fallback, возвращает агрегированный статус и при необходимости использует Cache/Read Model с отметкой свежести.')
    return ('Service A вызывает REST API Service B и ждёт ответ сразу. Главные риски: timeout, некорректная обработка ошибок, повтор запроса после timeout и отсутствие correlationId для расследования одной операции.')

def schema_blocks(case_type, schema=None):
    names=[x.strip() for x in (schema or CASE_SCHEMAS.get(case_type, CASE_SCHEMAS['sync_rest'])).split('→')]
    lines=[]
    for name in names:
        lines.append(f'- **{name}**: делает свою часть потока; принимает вход предыдущего блока; отдаёт результат следующему блоку; при ошибке фиксирует ошибку с correlationId и переводит поток в retry/error/manual recovery по правилам кейса.')
    if case_type in ['async_worker','event_kafka','enrichment_kafka','callback','legacy_file','status_aggregation']:
        lines.append('- **Ошибка/retry/manual recovery/status**: для сложного потока отдельно описываются повтор, ошибка, ручной разбор и получение статуса; для callback/polling фиксируется таймаут ожидания.')
    return '\n'.join(lines)

def concrete_process(case_type):
    if case_type == 'async_worker':
        return ['Service 1 вызывает Service 2 API и передаёт idempotencyKey/correlationId.', 'Service 2 валидирует запрос, создаёт запись integration_task DB со статусом NEW и возвращает trackingId.', 'Worker берёт задачу, переводит её в IN_PROGRESS и вызывает Service 3.', 'При успехе задача получает SUCCESS, а GET /status возвращает финальный результат.', 'Если Service 3 недоступен, Worker переводит задачу в RETRY и повторяет с лимитом попыток.', 'После превышения лимита задача получает FAILED и попадает в manual recovery.']
    if case_type == 'event_kafka':
        return ['Source Service сохраняет бизнес-изменение и запись Outbox в одной транзакции.', 'Publisher читает Outbox и публикует событие с eventId, aggregateId, occurredAt и version в Kafka topic.', 'Consumer читает Kafka topic, проверяет inbox/idempotency и схему события.', 'При успехе Target DB обновляется один раз даже при повторной доставке.', 'При временной ошибке выполняется retry.', 'После исчерпания попыток событие уходит в DLQ/manual recovery; отслеживаются consumer lag и schema validation errors.']
    if case_type == 'callback':
        return ['Internal Service отправляет запрос во External API и сохраняет requestId/trackingId.', 'External API принимает запрос и отвечает техническим ack.', 'Callback API принимает отложенный ответ.', 'Callback проверяет подпись/авторизацию и idempotency callback.', 'Status DB обновляется при успехе.', 'Если callback не пришёл до timeout ожидания, включается polling fallback или ручная проверка.']
    if case_type == 'dwh':
        return ['Source System выбирает batch/CDC режим.', 'Export/CDC передаёт данные по watermark.', 'Staging выполняет deduplication и data quality checks.', 'DWH строит слой отчётности.', 'Reconciliation сравнивает полноту и контрольные суммы.', 'При расхождении выполняется reload/backfill и ручной разбор качества данных.']
    if case_type == 'enrichment_kafka':
        return ['Source Service публикует минимальное событие или передаёт данные в adapter/orchestrator.', 'Kafka доставляет событие потребителям.', 'Enrichment Worker/Adapter получает недостающие данные через REST-обогащение.', 'Target Service получает обогащённый результат.', 'Если enrichment-сервис недоступен, применяется retry REST-обогащения или fallback.', 'Команда выбирает место обогащения с учётом связности, стоимости, свежести данных и влияния на Source.']
    if case_type == 'legacy_file':
        return ['Legacy System формирует File Export и присваивает batch_id/file_id.', 'Интеграционный слой принимает файл и проверяет checksum.', 'Validation проверяет формат, обязательные поля и дубли.', 'Валидные записи передаются в Target System.', 'Ошибочные строки или файлы попадают в Quarantine.', 'Оператор запускает reprocessing/manual recovery после исправления причины.']
    if case_type == 'status_aggregation':
        return ['Client/UI вызывает BFF/API Composition за статусом.', 'BFF параллельно вызывает Service A, Service B и Service C с отдельными timeout.', 'BFF нормализует ответы в единую status model.', 'Если источник недоступен, применяется partial response/fallback.', 'Cache/Read Model хранит последний известный статус с freshness marker.', 'Метрики показывают latency/error rate по каждому источнику и общую свежесть ответа.']
    return ['Service A вызывает REST API Service B.', 'Service B валидирует входные данные.', 'Service B выполняет операцию и возвращает синхронный ответ.', 'При успехе Service A получает результат сразу.', 'При timeout Service A может повторить запрос, поэтому Service B должен корректно обработать повтор.', 'Ошибки мапятся в понятные коды, correlationId попадает во все логи.']

def risks_for_case(case_type):
    base={
        'sync_rest': [('Повтор после timeout','Service B может создать дубль','Service B принимает idempotencyKey для небезопасных операций или возвращает существующий результат по business key.'),('Долгое ожидание','Пользователь или upstream зависает','Задать timeout и error mapping; долгие операции переводить в async_worker.'),('Нельзя расследовать инцидент','Логи разных сервисов не связываются','correlationId передаётся от Service A до Service B и пишется во все логи.')],
        'async_worker': [('Потеря задачи','Запрос принят, но обработка не стартует','Создавать integration_task DB в транзакции и мониторить stuck tasks.'),('Дубли','Повторный запрос создаёт вторую задачу','idempotencyKey возвращает существующий trackingId.'),('Service 3 недоступен','Задача зависает','Worker переводит задачу в RETRY, затем FAILED и manual recovery.')],
        'event_kafka': [('Потеря события','Target DB не узнает об изменении','Business DB и transactional outbox сохраняются в одной транзакции.'),('Дубли доставки','Consumer выполнит действие дважды','eventId/aggregateId/version и inbox/idempotency.'),('Consumer не успевает','Растёт задержка','Алерты на consumer lag, throughput, processing time.')],
        'enrichment_kafka': [('Сервис обогащения недоступен','Событие не обогащается','retry REST-обогащения, fallback и manual recovery.'),('Данные устарели','Target получает неверный контекст','Контроль свежести данных и явное occurredAt/sourceUpdatedAt.'),('Source менять дорого','Проект затягивается','Рассмотреть minimal event + enrichment-worker или adapter/orchestrator.')],
        'callback': [('Callback повторился','Статус обновляется несколько раз','idempotency callback по requestId/trackingId.'),('Callback подделан','Появится ложный результат','Проверка подписи/авторизации.'),('Callback не пришёл','Процесс завис','timeout ожидания, polling fallback и audit.')],
        'dwh': [('Неполная выгрузка','Отчётность врёт','watermark, контроль полноты и reconciliation.'),('Дубли','Метрики завышены','deduplication по business key/batch id.'),('Плохое качество данных','Витрина некорректна','data quality checks, lineage, reload/backfill.')],
        'legacy_file': [('Файл повреждён','Target System получит неполные или битые данные','Проверять checksum, file registry и помещать файл в quarantine.'),('Дубли файла или строк','Операции задвоятся','Использовать file_id, batch_id и deduplication registry.'),('Ошибка не переобработана','Данные застрянут между legacy и target','Нужны reprocessing, manual recovery и audit log.')],
        'status_aggregation': [('Один источник тормозит','Весь экран статуса зависает','Задать per-dependency timeout и partial response policy.'),('Показан устаревший статус','Пользователь принимает неверное решение','Возвращать freshness marker и использовать Cache/Read Model по явным правилам.'),('Непонятно где сбой','Команда не видит проблемный источник','Метрики latency/error по Service A/B/C и correlationId на весь запрос.')],
    }
    return base.get(case_type, base['sync_rest'])

def enrichment_options_md():
    rows=[
        ('Обогащать в source','низкая внешняя связность downstream, высокая связность source','дороже, если Source менять дорого','свежие данные на момент публикации','Source зависит от enrichment-сервиса','проще downstream, сложнее Source','сильное'),
        ('Публиковать минимальное событие и обогащать у consumer','Source независимее, consumer знает больше','дешевле для Source','свежесть на момент чтения consumer','каждый consumer решает retry сам','сложнее при многих consumer','низкое'),
        ('Enrichment-worker','связность вынесена в отдельный компонент','средняя','можно контролировать freshness','централизованные retry/fallback','нужна эксплуатация worker','умеренное'),
        ('Adapter/orchestrator','связность локализована в адаптере','средняя/высокая','контролируется в оркестраторе','хорошо для сложных правил','сложнее разработка и мониторинг','минимальное'),
    ]
    md=['### Варианты обогащения и компромиссы\n','| Вариант | Связность | Стоимость внедрения | Свежесть данных | Отказоустойчивость | Сложность эксплуатации | Влияние на source |','|---|---|---|---|---|---|---|']
    md += [f'| {a} | {b} | {c} | {d} | {e} | {f} | {g} |' for a,b,c,d,e,f,g in rows]
    return '\n'.join(md)+'\n'

def kafka_filtering_note(form):
    vals=[]
    for v in (form or {}).values():
        if isinstance(v, (list, tuple, set)):
            vals.extend(str(x).lower() for x in v)
        else:
            vals.append(str(v).lower())
    text=' '.join(vals)
    is_shared = str((form or {}).get('simple_situation','')) == 'shared_topic'
    if not is_shared and 'фильтр' not in text and 'filter' not in text and 'общий kafka topic' not in text and 'общий топик' not in text and 'no_new_topic' not in text and 'shared topic' not in text:
        return ''
    return ('\n### Kafka topic один, фильтрация у consumer\n'
            '- Фильтрация на consumer допустима, если общий объём чтения приемлемый и лишние события не ломают SLA.\n'
            '- Риски: лишнее чтение, рост consumer lag, лишняя стоимость обработки, сложнее capacity planning.\n'
            '- Отдельный topic стоит рассмотреть как вариант, но это не обязательное требование для старта.\n'
            '- Метрики: lag, throughput, discard rate, processing time.\n'
            '- Выносить фильтрацию раньше нужно, когда discard rate слишком высокий, lag растёт, обработка дорогая или появляются разные требования по безопасности/retention.\n')


def saga_compensation_note(form, case_type):
    raw=[]
    for v in (form or {}).values():
        if isinstance(v, (list, tuple, set)):
            raw.extend(str(x).lower() for x in v)
        else:
            raw.append(str(v).lower())
    text=' '.join(raw)
    needs_saga = any(x in text for x in ['compensation','компенсац','откат','distributed_transaction_saga','частичный успех'])
    needs_saga = needs_saga or (case_type in {'async_worker','event_kafka','enrichment_kafka'} and any(x in text for x in ['деньги','баланс','договор','регуляторика','несколько потребителей','many_consumers']))
    if not needs_saga:
        return ''
    return ('\n### Долгий многошаговый процесс / компенсации\n'
            '- Если часть шагов уже выполнена, а следующий шаг упал, нельзя оставлять процесс в неопределённом состоянии. Нужна статусная модель процесса.\n'
            '- Для каждого критичного шага нужно указать: успешный статус, ошибочный статус, retry limit, owner и что делать после исчерпания retry.\n'
            '- Если нужен откат, компенсация должна быть явным шагом: что откатываем, кто владелец, как аудируется, что делать при compensation_failed.\n'
            '- Для ручного восстановления нужна очередь manual recovery с причиной, владельцем, временем создания и финальным решением.\n'
            '- Минимальные тесты: сбой после частичного успеха, повтор команды, упавшая компенсация, ручное восстановление, проверка статуса процесса.\n')

def build_human_markdown(form, ctx, case_type, readiness, old_markdown=''):
    simple=simple_readiness(form, ctx)
    use_simple_gate = bool(readiness.get('_use_simple_readiness', True))
    preserved_score = readiness.get('score', simple.get('score', 0))
    if use_simple_gate:
        previous_status = readiness.get('status')
        previous_blockers = readiness.get('blockers') or []
        readiness.update(simple)
        readiness['score'] = min(simple.get('score', preserved_score), preserved_score)
        if previous_status:
            readiness['status'] = previous_status
        if previous_blockers:
            readiness['blockers'] = previous_blockers
    if use_simple_gate and simple['score'] <= 40:
        missing='\n'.join(f'- {x}' for x in simple['missing'])
        return f"# Отчёт по интеграционному решению\n\nНедостаточно данных для архитектурного вывода.\n\nРешение заблокировано: недостаточно входных данных.\n\n### 0. Предпроектная проверка\nПока данных мало — можно сформировать только черновик. Для полного отчёта нужно заполнить ключевые вопросы.\n\n## Что нужно уточнить\n{missing}\n"
    if (form or {}).get('_explicit_business_first') != 'yes' and old_markdown:
        return old_markdown
    specialized_case=(ctx or {}).get('specialized_case') or specialized_case_from_form(form, case_type)
    title=(form.get('project_name') or '').strip() or CASE_DEFAULT_TITLES.get(case_type, CASE_DEFAULT_TITLES['sync_rest'])
    custom_schema = custom_schema_from_form(form)
    canonical_schema = build_canonical_schema_for_case(specialized_case, None, None, business_constraints_from_form(form))
    schema = custom_schema or canonical_schema or CASE_SCHEMAS.get(case_type, CASE_SCHEMAS['sync_rest'])
    checklist=case_specific_handoff(specialized_case, case_type)
    ordered_steps_text = ordered_business_process_text(form)
    ordered_steps = ordered_business_steps_from_form(form)
    order_warnings = list(dict.fromkeys(business_order_warnings_from_form(form) + validate_actor_action_pairs(form)))
    process=([f"{s['actorLabel']} {s['action'].lower()}{(' — ' + s['object']) if s.get('object') else ''}" for s in ordered_steps] or concrete_process(case_type))
    risks=risks_for_specialized_case(specialized_case, case_type, form)
    warning=(simple.get('warning')+'\n\n') if simple.get('warning') else ''
    business_goal=(form.get('business_goal') or '').strip()
    business_process = ordered_steps_text or business_goal or case_summary(form, case_type)
    explanation = specialized_case_summary(specialized_case, case_type, form)
    md=[f'# Отчёт по интеграционному решению\n\n',
        '## 1. Бизнес-процесс\n',
        f'{warning}{business_process}\n\n**Готовность требований:** {readiness.get("score", simple.get("score", 0))}% ({readiness.get("status", "GREEN")}).\n',
        '\n## 2. Класс сложного кейса\n', case_class_narrative(specialized_case, case_type, form)+'\n',
        '\n## 3. Схема взаимодействия\n', f'**{schema}**\n\n', schema_blocks(specialized_case, schema)+'\n',
        '\n## 4. Почему выбрана такая техническая схема\n', f'{explanation}\n',
        (f'Порядок бизнес-шагов учтён: {business_process.replace(chr(10), " → ")}\n' if ordered_steps else ''),
        ''.join(f'Обратите внимание: {w}\n' for w in order_warnings),
        f'- Главный риск: {risks[0][0]} — {risks[0][1]}.\n',
        f'- Обязательно реализовать: {checklist[0] if checklist else "контракты и наблюдаемость"}.\n',
        '\n## 5. Пошаговый процесс\n', numbered(process),
        '\n## 6. Что обязательно реализовать\n', bullet(checklist),
        '\n## 7. Главные риски\n', '| Риск | Что будет | Как закрыть |\n|---|---|---|\n', ''.join(f'| {a} | {b} | {c} |\n' for a,b,c in risks), ''.join(f'| Риск бизнес-шага | {w} | Уточнить порядок/владельца с бизнес-владельцем и добавить статус/проверку. |\n' for w in order_warnings),
        '\n## 8. Ограничения и компромиссы\n', bullet((_as_list(form.get('forbidden_channels', [])) + business_constraints_from_form(form)) or ['нет явных ограничений']),
        '\n## 9. Что отдать разработке\n', bullet(checklist),
        '\n## 10. Что нужно уточнить\n', bullet((simple.get('missing') or ['нет критичных неизвестных']) + order_warnings),
        '\n## 11. Тест-кейсы\n', bullet(case_specific_handoff(specialized_case, case_type)[-4:] + ['happy path', 'timeout', 'duplicate/retry', 'manual recovery']),
        '\n## 12. ADR\n', f'- Context: требуется {title}.\n- Decision: использовать {schema}.\n- Alternatives: generic {case_type}, синхронная цепочка, adapter/orchestrator, событийный поток там, где это оправдано.\n- Consequences: нужны case-specific контракты, правила повторов, владельцы ошибок, мониторинг и тесты.\n',
        '\n<details class="expert-details">\n<summary>Показать технические детали</summary>\n\n', bullet(technical_details_for_case(case_type)), '\n</details>\n']
    if case_type == 'enrichment_kafka': md.append(enrichment_options_md())
    md.append(kafka_filtering_note(form))
    md.append(saga_compensation_note(form, case_type))
    if old_markdown and str(form.get('report_detail','')) == 'expert':
        cleaned=re.sub(r'Решение заблокировано[^\n]*\n?', '', old_markdown)
        cleaned=re.sub(r'Готовность[^\n]*0%[^\n]*\n?', '', cleaned)
        md.append('\n<details class="expert-details">\n<summary>Диагностическое приложение (не основной вывод)</summary>\n\n')
        md.append(cleaned)
        md.append('\n</details>\n')
    return ''.join(md)

def required_reliability_key(kind):
    mapping={
        'financial_command':'Idempotency-Key / operation_id + unique constraint',
        'command_create_update':'Idempotency-Key или business request key для небезопасных повторов',
        'webhook_event_intake':'provider_event_id / delivery_id + signature/raw_body + Inbox',
        'kafka_event_consumer':'event_id + aggregate_id/version + consumer Inbox/idempotent sink',
        'kafka_event_publisher':'outbox_id/source_event_id/aggregate_version + publisher retry state',
        'batch_file_exchange':'file_id + checksum + batch_id + registry',
        'dwh_offload':'watermark/offset/snapshot_id + reconciliation checksum',
        'migration':'migration_run_id + source_record_id + checksum + reconciliation',
        'regulatory_schema_change':'schema_version/change_id + backward compatibility matrix + migration_run_id',
        'privacy_erasure_pipeline':'erasure_request_id + subject_id + legal_hold_decision_id + per_system_receipt_id',
        'cdc_legacy_modernization':'source_lsn/watermark + source_table + aggregate_id + projection_version',
        'near_real_time_decision':'decision_id + request_id + feature_snapshot_id + model/rules_version',
        'highload_stream_ingestion':'event_id + device_id/tenant_id + event_time + sequence/watermark + partition key',
        'bff_composition':'correlation_id/request_id; idempotency не blocker для read-only запроса',
        'external_partner_adapter':'partner_request_id + idempotency key для write/command, correlation_id для query',
        'query_readonly':'correlation_id/request_id; idempotency не blocker для read-only запроса',
    }
    return mapping.get(kind,'business key + correlation_id')

# ---------- engine ----------
class Engine:
    def generate(self, form):
        # Robust API entry: merge caller data with neutral UI defaults.
        # This protects CLI/tests/external callers from KeyError and prevents hidden demo data.
        _original_form = form or {}
        _explicit_business_first = (any(k in _original_form for k in ['business_case','business_process_json','business_actors_json','business_steps_json','business_constraints_json']) or _original_form.get('ux_mode') == 'business_first_constructor' or (not _original_form.get('ux_mode') and _original_form.get('simple_situation') and _original_form.get('process_graph_json')))
        base = defaults()
        base.update(_original_form)
        form = normalize_form(base)
        if _explicit_business_first:
            form['_explicit_business_first'] = 'yes'
        form.setdefault('preset_name','')
        if form.get('task_type') == 'audit_existing_solution':
            audit_res = SolutionAuditor().audit(form)
            audit_res['case_type'] = 'audit'
            audit_res['case_schema'] = CASE_SCHEMAS.get('audit')
            audit_res['case_checklist'] = required_items_for_case('audit')
            audit_res['form'] = form
            needed = ['### Что проверяем', '### Что делать', '### Почему именно так', '### Главные ограничения и риски']
            if any(x not in audit_res.get('markdown','') for x in needed):
                audit_res['markdown'] += (
                    '\n\n### Что проверяем\n'
                    'Текущую схему, риски доставки, дубли, восстановление и владельцев ошибок.\n\n'
                    '### Что делать\n'
                    'Закрыть критичные риски, добавить контракты, retry/manual recovery, наблюдаемость и тесты.\n\n'
                    '### Почему именно так\n'
                    'Аудит должен сохранить рабочие части решения и исправить только обязательные пробелы.\n\n'
                    '### Главные ограничения и риски\n'
                    'Потери данных, дубли, log-only ошибки, отсутствие владельца восстановления и неполная наблюдаемость.\n'
                )
            if '## Что отдать разработке' not in audit_res.get('markdown',''):
                audit_res['markdown'] += (
                    '\n\n## Что отдать разработке\n'
                    '- risk register с критичностью рисков\n'
                    '- список обязательных исправлений\n'
                    '- варианты улучшения и компромиссы\n'
                    '- тест-кейсы на дубли, потери, таймауты и восстановление\n'
                    '- ADR по выбранному плану исправления\n'
                )
            return audit_res
        ctx={
          'fields':parse_fields(form.get('fields','')),
          'systems':parse_matrix(form.get('systems_matrix',''),['name','role','owner','criticality','channel','blocking','sla']),
          'steps':parse_matrix(form.get('process_steps',''),['level','order','parent','step','system','channel','input','output','timeout','retry','compensation','blocking','owner']),
          'errors':parse_matrix(form.get('error_matrix',''),['error','where','blocking','retry','after_retry','owner']),
          'target_integrations':parse_matrix(form.get('target_integration_matrix',''),['from','to','channel','mode','trigger','data','contract','timeout','retry','retry_limit','dlq','idempotency','auth','rate_limit','owner']),
          'process_flow':parse_matrix(form.get('process_flow_matrix',''),['step_id','parent_id','condition','action','system','success_next','failure_next','timeout_next','compensation','manual_recovery']),
          'contracts_declared':parse_matrix(form.get('contract_matrix',''),['type','name','producer','consumer','endpoint_or_topic','method_or_key','required_fields','optional_fields','errors','version','compatibility']),
          'business_rules':parse_matrix(form.get('business_rules_matrix',''),['rule_id','condition','action','affected_step','owner','error_if_failed']),
          'capacity_declared':parse_matrix(form.get('capacity_matrix',''),['flow','avg_rps','peak_rps','avg_payload_kb','max_payload_kb','events_per_day','useful_filter_ratio','partitions','consumers','db_write_tps','max_lag','replay_volume','backfill_window','external_rate_limit']),
          'observability_declared':parse_matrix(form.get('observability_matrix',''),['metric','where','threshold','alert','owner','dashboard']),
          'rollout_declared':parse_matrix(form.get('rollout_migration_matrix',''),['phase','scope','strategy','rollback','backfill','parallel_compare','go_no_go','owner']),
          'data_quality_lineage':parse_matrix(form.get('data_quality_lineage_matrix',''),['data_object','source','target','check','frequency','evidence','owner']),
          'statuses':split_csv(form.get('statuses','')), 'final_statuses':split_csv(form.get('final_statuses','')), 'wizard_production_gate':form.get('wizard_production_gate')}
        traits=self.classify(form,ctx)
        business=self.business_model(form,ctx,traits)
        ctx['business']=business
        ctx['input_quality']=self.input_quality(form,ctx,traits)
        patterns=self.patterns(form,ctx,traits)
        case_classes=self.detect_case_classes(form,ctx,traits)
        ctx['case_classes']=case_classes
        anti_pre=self.anti_patterns(form,ctx,traits,patterns,{'pattern_ids':[],'name':'not_selected'})
        variants=self.variants(form,ctx,traits,patterns,anti_pre)
        variants=self.apply_case_class_ranking(form,ctx,traits,variants,case_classes)
        recommended=variants[0]
        anti=self.anti_patterns(form,ctx,traits,patterns,recommended)
        production_gate=self.production_gate(form,ctx,traits,anti,recommended,case_classes)
        db=self.database(form,ctx,traits,recommended)
        contracts=self.contracts(form,ctx,traits,recommended)
        scenarios=self.scenarios(form,ctx,traits,recommended)
        diagrams=self.diagrams(form,ctx,traits,recommended)
        lifecycle=self.lifecycle(form,ctx,traits,recommended,anti)
        specialized=self.specialized_case_pack(form,ctx,traits,recommended,patterns,anti,db,contracts,scenarios,lifecycle)
        composite=self.composite_architecture(form,ctx,traits,recommended,patterns,anti)
        readiness=self.readiness(form,ctx,traits,anti,recommended)
        advanced=self.advanced_product_sections(form,ctx,traits,recommended,patterns,anti,composite,db,contracts,scenarios,diagrams,lifecycle,readiness)
        advanced['specialized_cases']=specialized
        structured=self.structured_result(form,ctx,traits,recommended,patterns,anti,case_classes,production_gate,advanced,lifecycle)
        md=self.markdown(form,ctx,traits,patterns,variants,recommended,anti,db,contracts,scenarios,diagrams,lifecycle,readiness,composite,advanced)
        # Human/default reports must not append technical specialist packs after the readable ending.
        # Keep them only in expert/full technical export.
        if str(form.get('report_detail','')) == 'expert':
            md += self.specialized_cases_markdown(specialized)
        md = explain_english_terms_ru_text(md)
        case_type = detect_case_type(form, ctx, {'markdown': md})
        specialized_case = specialized_case_from_form(form, case_type)
        ctx['case_type'] = case_type
        ctx['specialized_case'] = specialized_case
        custom_case_schema = custom_schema_from_form(form)
        canonical_case_schema = build_canonical_schema_for_case(specialized_case or case_type)
        selected_case_schema = custom_case_schema or canonical_case_schema or CASE_SCHEMAS.get(case_type, CASE_SCHEMAS['sync_rest'])
        case_checklist = case_specific_handoff(specialized_case, case_type)
        _simple_ready = simple_readiness(form, ctx)
        _substantial_model = any(str(form.get(k, '')).strip() for k in ['systems_matrix','process_steps','fields','target_integration_matrix','current_solution_description','current_systems_matrix','current_process_steps'])
        _explicit_simple = any(str(form.get(k, '')).strip() for k in ['simple_situation','simple_goal','simple_q_systems','simple_q_immediate','simple_q_payload','simple_q_risk','simple_q_error','simple_q_status','quick_description'])
        _use_simple_readiness = _explicit_simple or not _substantial_model
        readiness['_use_simple_readiness'] = _use_simple_readiness
        if _use_simple_readiness:
            _engine_score = readiness.get('score', _simple_ready.get('score', 0))
            readiness.update(_simple_ready)
            readiness['score'] = _simple_ready.get('score', _engine_score)
            readiness['_use_simple_readiness'] = True
        readiness = merge_readiness(readiness, None, [a.get('title') for a in anti if a.get('severity') == 'critical'])
        md = build_human_markdown(form, ctx, case_type, readiness, md)
        return {'form':form,'ctx':ctx,'traits':traits,'patterns':patterns,'case_classes':case_classes,'specialized_case':specialized_case,'case_type':case_type,'case_schema':selected_case_schema,'case_checklist':case_checklist,'production_gate':production_gate,'wizard_production_gate':form.get('wizard_production_gate'),'structured_result':structured,'variants':variants,'recommended':recommended,'anti_patterns':anti,'db':db,'contracts':contracts,'scenarios':scenarios,'diagrams':diagrams,'lifecycle':lifecycle,'readiness':readiness,'composite_architecture':composite,'advanced':advanced,'specialized_cases':specialized,'markdown':md}

    def specialized_case_pack(self,f,c,t,recommended,patterns,anti,db,contracts,scenarios,lifecycle):
        """Усиленный слой распознавания сложных интеграционных ситуаций.

        Этот слой нужен не вместо основного ранжирования, а поверх него: если вход похож на
        конкретную боль проектирования, результат обязан содержать адресный русский блок,
        а не только общий вариант «E2E-цепочка».
        """
        active=set(f.get('business_situations') or [])
        text_blob=' '.join([
            str(f.get('preset_name','')), str(f.get('business_goal','')), str(f.get('short_description','')),
            str(f.get('systems_matrix','')), str(f.get('process_steps','')), str(f.get('target_integration_matrix',''))
        ]).lower()
        allowed=set(f.get('allowed_channels') or [])
        forbidden=set(f.get('forbidden_channels') or [])
        controls=set(f.get('current_controls') or [])
        change=set(f.get('change_policy') or [])
        packs=[]

        def has(*tokens):
            return any(tok in active or tok.lower() in text_blob for tok in tokens)

        def add_pattern(pid,name,score,why,controls=None,controls_list=None,risks=None):
            controls_list = controls if controls is not None else (controls_list or [])
            risks = risks or []
            if not any(p.get('id')==pid for p in patterns):
                patterns.append({'id':pid,'name':name,'score':score,'why':why,'controls':controls_list,'risks':risks})
            if name not in recommended.setdefault('patterns',[]):
                recommended['patterns'].insert(0,name)
            if pid not in recommended.setdefault('pattern_ids',[]):
                recommended['pattern_ids'].insert(0,pid)

        def add_risk(rid,title,severity,why,fix,where='specialized_case'):
            if not any(a.get('id')==rid for a in anti):
                anti.append({'id':rid,'title':title,'severity':severity,'why':why,'fix':fix,'where':where})

        def add_pack(case_id,title,trigger,decision,controls_req,risks_req,tests_req,pattern=None,risk=None):
            packs.append({'id':case_id,'title':title,'trigger':trigger,'decision':decision,'controls':controls_req,'risks':risks_req,'tests':tests_req})
            if pattern:
                add_pattern(**pattern)
            if risk:
                add_risk(**risk)

        # 1. REST enrichment before Kafka
        if has('event_enrichment_before_publish','rest_enrich_before_kafka','обогащ', 'enrichment') or (('kafka' in allowed or 'kafka' in text_blob) and ('enrich' in text_blob or 'обогащ' in text_blob)):
            add_pack(
                'event_enrichment_before_kafka',
                'REST-обогащение перед публикацией в Kafka',
                'Source фиксирует бизнес-факт, но финальное событие должно быть дополнено данными из другого REST-сервиса.',
                [
                    'Факт изменения остаётся во владении source-сервиса.',
                    'Минимальный безопасный v1: source-owned outbox/integration table со статусами NEW/ENRICHING/PUBLISHED/FAILED.',
                    'Technical Integration Publisher читает pending-записи, вызывает REST enrichment, публикует только финальный enriched event.',
                    'Enrichment-сервис владеет только дополнительными атрибутами, но не становится владельцем события.',
                    'При ошибке REST enrichment событие не теряется: retry, FAILED, manual reprocess и reconciliation обязательны.'
                ],
                ['outbox/integration table','sourceEventId','aggregateId','aggregateVersion','eventId','correlationId','enrichmentConsistency','dataAsOf','retry/backoff','FAILED/reprocess','DLQ или quarantine','stuck alerts'],
                ['Перенос ownership события в enrichment-сервис.','Потеря события между commit и publish.','Публикация raw event без обязательного enrichment.','Устаревшие enrichment-данные без dataAsOf/consistency rule.'],
                ['REST enrichment недоступен: outbox остаётся FAILED/RETRY, Kafka не получает неполный event.','Повтор publisher не создаёт дубль благодаря eventId/sourceEventId.','Потребитель отвергает старую aggregateVersion.'],
                pattern={'pid':'integration_publisher','name':'Integration Publisher / REST Enrichment before Kafka','score':95,'why':['Собирает финальный payload без переноса ownership события.'],'controls':['source-owned outbox/integration table','REST enrichment timeout','retry/backoff','FAILED/reprocess','sourceEventId','aggregateVersion','enrichmentConsistency'],'risks':['Публикация задерживается до enrichment; нужен explicit freshness/dataAsOf.']},
                risk={'rid':'enrichment_ownership_guard','title':'REST-обогащение перед Kafka требует явного ownership и recovery','severity':'critical','why':'Без outbox/integration state событие можно потерять или ошибочно передать ownership enrichment-сервису.','fix':'Зафиксировать source-owned outbox/integration table, publisher, consistency rule, retry/FAILED/reprocess и DLQ/quarantine.'}
            )

        # 2. Missing required contract field / contract-first
        if has('contract_required_field_missing','missing_required_contract_field','contract_breaking_change','required field','обязательн') or f.get('task_type')=='contract_change':
            add_pack(
                'contract_required_field_missing',
                'Проверка обязательных полей и совместимости контракта',
                'Есть риск, что сервис не вернёт/не примет обязательное поле или изменит контракт несовместимо.',
                ['Контракт является источником истины: OpenAPI/AsyncAPI/schema registry обновляется до разработки.','Для required-полей нужны positive/negative contract tests.','Duplicate response должен иметь тот же обязательный shape, что и обычный успешный ответ, либо явно отдельный documented response.','Любое удаление/переименование required-поля — breaking change с миграционным окном.'],
                ['OpenAPI/AsyncAPI','consumer-driven contract tests','schema validation в runtime','examples для success/duplicate/error','compatibility policy','CI contract gate'],
                ['QA не ловит отсутствие required-поля.','Consumer падает на редком статусе duplicate/conflict.','Версия контракта меняется без миграции.'],
                ['Duplicate response содержит все required-поля.','Old consumer работает с новой схемой.','Consumer получает payload без required-поля и тест падает до production.'],
                pattern={'pid':'contract_tests','name':'Contract-first + Consumer-driven Contract Tests','score':94,'why':['Защищает обязательные поля, duplicate responses и обратную совместимость.'],'controls':['OpenAPI/AsyncAPI','schema validation','required fields gate','consumer examples','compatibility checks'],'risks':['Без contract gate ошибка может уйти в production даже при зелёных unit-тестах.']},
                risk={'rid':'missing_required_contract_field','title':'Обязательное поле контракта может отсутствовать в редкой ветке ответа','severity':'critical','why':'Особенно опасны duplicate/conflict/error ветки, которые редко проверяются вручную.','fix':'Добавить contract tests на все ветки ответа и runtime schema validation.'}
            )

        # 3. Long sync chain and dependency failures
        if has('sync_chain_timeout_budget','sync_chain','retry_storm','external_api_dependency','rate_limit') or (f.get('result_model')=='sync' and (f.get('chain_depth') in ['multi_level','fanout','fanout_fanin'] or f.get('step_count') in ['4_7','8_plus'])):
            add_pack(
                'sync_chain_resilience',
                'Синхронная цепочка, внешняя зависимость и retry storm',
                'Несколько блокирующих REST-вызовов или нестабильная внешняя зависимость могут дать каскадные timeout и лавину повторов.',
                ['Задать общий timeout budget цепочки и отдельный timeout на каждую зависимость.','Поставить circuit breaker, bulkhead, retry budget, exponential backoff + jitter.','Не повторять бесконечно non-idempotent операции.','Для длинных операций рассмотреть async acceptance + status tracking вместо ожидания всего результата.','Для BFF/fan-out разрешить partial response и freshness markers.'],
                ['timeout budget','circuit breaker','bulkhead','retry budget','exponential backoff + jitter','rate limit','fallback/degradation','idempotency key','correlationId/tracing'],
                ['Retry storm добивает зависимость.','p99 latency всей цепочки становится суммой худших зависимостей.','Пользователь получает 500 вместо понятного статуса ожидания.'],
                ['Dependency 500/timeout: circuit breaker открывается, запрос деградирует.','Retry ограничен budget и jitter.','Корреляция проходит через все сервисы.'],
                pattern={'pid':'circuit_breaker','name':'Timeout Budget + Circuit Breaker + Graceful Degradation','score':93,'why':['Защищает синхронную цепочку от каскадных отказов и retry storm.'],'controls':['per-hop timeout','global deadline','circuit breaker','bulkhead','fallback','retry budget','jitter'],'risks':['Без budget даже корректные retry могут положить зависимость.']}
            )

        # 4. Saga / long-running process / partial success
        if has('distributed_transaction_saga','long_running_process','partial_success','manual_recovery_required','human_in_the_loop') or (f.get('orchestration') in ['orchestrator','bpm'] and f.get('step_count') in ['4_7','8_plus']):
            add_pack(
                'saga_state_machine',
                'Долгий процесс, Saga и partial success',
                'Процесс нельзя держать в одном синхронном запросе: нужны состояния, компенсации и ручное восстановление.',
                ['Ввести process state machine с business/technical statuses.','Для каждого шага указать owner, timeout, retry, compensation и terminal statuses.','Partial success должен быть отдельным осознанным состоянием, а не “ошибкой где-то в логах”.','Manual recovery — часть дизайна, а не аварийная импровизация.'],
                ['orchestrator или choreography decision','status model','compensation rules','manual recovery queue','audit','reconciliation','status API','correlationId'],
                ['Деньги/резервы/заявки остаются в подвешенном состоянии.','Невозможно объяснить пользователю, где процесс.','Операторы чинят руками без audit.'],
                ['Шаг N упал после успеха N-1: статус partial/manual_review и компенсация корректны.','Повтор не создаёт дубль.','Операторское исправление аудируется.'],
                pattern={'pid':'saga','name':'Saga / Process State Machine','score':92,'why':['Даёт управляемые статусы, retry, компенсации и recovery для долгого процесса.'],'controls':['state machine','compensation','manual recovery','status API','audit','reconciliation'],'risks':['Saga сложнее простого REST, но честно отражает distributed transaction.']}
            )

        # 5. CQRS/read model/cache/status screen
        if has('cqrs_read_model_required','client_status_screen','read_after_write','cache_invalidation','api_composition','fast_and_fresh') or f.get('task_type')=='read_model':
            add_pack(
                'cqrs_read_model',
                'Экран чтения, статус пользователя, CQRS/read model и cache invalidation',
                'Экрану нужны быстрые данные из нескольких источников или асинхронного процесса.',
                ['Если экран должен быть быстрым — построить read model/projection или BFF с partial response.','Если данные могут устаревать — явно показывать freshness marker/dataAsOf.','Cache требует TTL, invalidation event и degraded mode.','Read-after-write закрывается статусом “обновляется”, read-your-writes token или чтением у владельца факта.'],
                ['CQRS/read model','projection lag metric','rebuild/replay','cache TTL','invalidation event','freshness marker','partial response','fallback'],
                ['Пользователь видит старый статус без объяснения.','BFF падает от одной медленной зависимости.','Кэш не инвалидируется и показывает неверные данные.'],
                ['Projection отстаёт: UI показывает dataAsOf/обновляется.','Одна зависимость BFF недоступна: partial response без падения всего экрана.','Cache invalidation event обновляет проекцию.'],
                pattern={'pid':'cqrs','name':'CQRS / Read Model with Freshness Marker','score':91,'why':['Отделяет быстрый пользовательский read path от сложного write/process path.'],'controls':['projection lag','rebuild/replay','freshness marker','cache TTL','invalidation','partial response'],'risks':['Eventual consistency надо явно объяснить бизнесу и пользователю.']}
            )

        # 6. Active-active financial write / ledger / money precision
        if has('active_active_financial_write','multi_region_active_active','ledger_required','money_precision') or ('active-active' in text_blob and 'финанс' in text_blob):
            add_pack(
                'financial_consistency_guard',
                'Финансовая операция, active-active запись, ledger, суммы и округление',
                'Финансовые изменения требуют доказанной модели консистентности, точности сумм и аудита.',
                ['Для денег предпочтителен immutable ledger: reversal вместо удаления/перезаписи.','Active-active write допустим только с доказанной стратегией conflict resolution; безопаснее single writer per aggregate/region leader.','Суммы хранятся decimal/minor units, всегда с currency code и rounding policy.','Любой retry должен давать business exactly once effect через idempotency/business key.'],
                ['ledger entries','single writer per aggregate','business idempotency key','decimal/minor units','currency code','rounding policy','audit trail','reconciliation'],
                ['Split-brain меняет баланс в двух регионах.','float/округление создаёт расхождения.','Повтор списания без idempotency.'],
                ['Одновременная запись в двух регионах блокируется или разрешается по documented conflict policy.','Повтор команды возвращает прежний результат.','Сверка ledger vs projection сходится.'],
                pattern={'pid':'financial_ledger','name':'Financial Ledger + Single Writer / Active-active Guard','score':96,'why':['Защищает денежный эффект, active-active конфликты, валюты и округление.'],'controls':['immutable ledger','single writer','idempotency','currency code','decimal','rounding policy','reconciliation'],'risks':['Два мастера без conflict policy недопустимы для финансового эффекта.']},
                risk={'rid':'active_active_financial_write','title':'Active-active финансовая запись без доказанной стратегии консистентности','severity':'critical','why':'Два региона/мастера могут одновременно изменить один финансовый aggregate.','fix':'Ввести single writer per aggregate, region leader, immutable ledger, conflict policy и reconciliation.'}
            )

        # 7. Eventual consistency business-facing
        if has('business_eventual_consistency','eventual_consistency_business') or (f.get('consistency')=='eventual' and has('client_status_screen','data_synchronization')):
            add_pack(
                'business_eventual_consistency',
                'Eventual consistency, понятная бизнесу и пользователю',
                'Техническая задержка синхронизации должна быть видна в UX, SLA и отчёте.',
                ['Не обещать мгновенную свежесть, если архитектура eventual consistent.','Зафиксировать max lag/freshness SLA и показать dataAsOf.','Добавить пользовательский статус “обновляется/ожидает синхронизации”.','Периодическая reconciliation закрывает расхождения.'],
                ['max lag SLO','freshness marker','status “обновляется”','reconciliation','lag alerts','business wording'],
                ['Бизнес считает данные мгновенными и принимает неверные решения.','Пользователь видит старый статус без пояснения.'],
                ['При lag UI показывает dataAsOf.','Нарушение max lag даёт alert.','Сверка выявляет и исправляет mismatch.'],
                pattern={'pid':'business_eventual_consistency','name':'Business-facing Eventual Consistency Contract','score':88,'why':['Переводит техническую eventual consistency в понятный SLA, статусы и UX.'],'controls':['freshness SLA','dataAsOf','lag alerts','status text','reconciliation'],'risks':['Без явного SLA eventual consistency воспринимается как баг.']}
            )

        # 8. Timezone/business dates
        if has('timezone_business_date','timezone_dates','clock_skew') or 'utc' in text_blob or 'businessdate' in text_blob:
            add_pack(
                'timezone_business_date',
                'Время, UTC, business date и порядок событий',
                'Разные системы могут использовать разные часовые пояса и timestamps.',
                ['Хранить техническое время в UTC.','Разделять occurredAt, receivedAt, processedAt, publishedAt и businessDate.','Для порядка использовать aggregateVersion/sequence, а не часы разных систем.','Для polling делать overlap window и deduplication.'],
                ['UTC timestamps','businessDate','occurredAt/processedAt/publishedAt','aggregateVersion','overlap window','clock skew tolerance'],
                ['Событие обрабатывается “из будущего” или “из прошлого”.','Polling пропускает изменение из-за рассинхрона часов.','Отчёт за бизнес-день расходится с фактическим временем.'],
                ['Clock skew ±5 минут не теряет изменения.','Старое событие с меньшей version не применяется.','Business date считается по правилам домена.'],
                pattern={'pid':'timezone_business_date','name':'UTC + Business Date + Version Ordering','score':86,'why':['Убирает неоднозначность времени и порядка при интеграции систем.'],'controls':['UTC','businessDate','occurredAt','processedAt','aggregateVersion','overlap dedup'],'risks':['Нельзя полагаться только на local timestamp разных систем.']}
            )

        # 9. Direct DB access, ownership, multi-tenant, SLA, environment, glossary, mapping, pagination
        if has('direct_db_write','direct_db_read','multi_tenant','missing_ownership','unclear_sla','environment_mismatch','glossary_mismatch','data_mapping_required','api_pagination'):
            add_pack(
                'governance_data_contracts',
                'Ownership, прямой доступ к БД, tenant isolation, SLA и data contracts',
                'Интеграция требует не только транспорта, но и явных владельцев, границ данных и правил эксплуатации.',
                ['Запретить прямую запись в чужую БД без ADR и временного статуса.','Для прямого чтения использовать API/read replica/projection, а не физическую схему владельца.','Для multi-tenant добавить tenantId в ключи, rate limit и isolation checks.','SLA/SLO фиксировать как p95/p99 latency, max lag, freshness, RTO/RPO.','Для терминов и трансформаций завести glossary/mapping owner.','Для API pagination использовать cursor/resume token и snapshot/consistency rule.'],
                ['ADR для исключений','owner matrix/RACI','tenant isolation','SLA/SLO','glossary','mapping table','cursor pagination','environment config/secrets'],
                ['Сервис ломается при миграции чужой таблицы.','Tenant data leak.','Никто не владеет инцидентом.','Пагинация пропускает изменённые записи.'],
                ['Прямая запись в чужую БД запрещена contract gate.','Tenant A не видит данные tenant B.','Pagination resume после сбоя не теряет записи.'],
                pattern={'pid':'governance_contracts','name':'Ownership Matrix + Data Contract Governance','score':84,'why':['Закрывает эксплуатационные и организационные риски интеграции.'],'controls':['RACI','ADR','tenantId','SLA/SLO','glossary','mapping','cursor pagination'],'risks':['Без owner matrix даже хорошая схема плохо сопровождается.']}
            )

        # 10. Transport choice, command/event, snapshot/delta, CDC/polling/file
        if has('transport_choice_unclear','command_event_confusion','snapshot_delta_choice','cdc_legacy_modernization','polling_required','file_integration','legacy_batch') or f.get('legacy') in ['file_only','db_replica_only']:
            add_pack(
                'transport_semantics',
                'Выбор транспорта и семантики: REST/Kafka/Rabbit/File/CDC/Polling',
                'Нужно отделить command от event, snapshot от delta и выбрать канал по свойствам задачи, а не по моде.',
                ['Command — просьба выполнить действие; event — факт, который уже произошёл.','Kafka подходит для event log, replay и нескольких consumer groups.','RabbitMQ/queue подходит для work distribution/command queue/routing.','CDC/polling/file — компромиссы legacy, для них нужны watermark/checkpoint/dedup/replay.','Snapshot event удобен для восстановления состояния, delta — легче, но требовательнее к ordering.'],
                ['transport decision record','command/event naming','snapshot/delta rule','watermark/checkpoint','dedup','file checksum/atomic upload','CDC lag/schema handling'],
                ['Команды попадают в event topic и размывают ownership.','Polling пропускает изменения.','File обработан частично или повторно.'],
                ['Повторный file не создаёт дубль.','Polling с overlap не пропускает запись.','Consumer может replay snapshot/delta по documented rule.'],
                pattern={'pid':'transport_semantics','name':'Transport Semantics Decision: Command/Event/Snapshot/CDC/Polling','score':85,'why':['Помогает выбрать канал и не смешать разные семантики интеграции.'],'controls':['ADR','naming','watermark','checkpoint','dedup','replay','schema handling'],'risks':['Неверная семантика канала сложнее исправляется, чем технический баг.']}
            )

        # Базовое имя recommended architecture не переименовываем.
        # Старые регрессионные тесты и пользовательские отчёты опираются на стабильные названия
        # вроде Orchestrated E2E Process / Data Pipeline / DWH. Специализированный смысл
        # добавляется отдельным блоком 17B и паттернами, а не заменой core-classifier.

        return packs

    def specialized_cases_markdown(self,packs):
        if not packs:
            return ''
        md=['\n\n## 17B. Специализированные сложные кейсы, распознанные моделью\n']
        md.append('Этот раздел добавлен, чтобы результат не сводился к общему “E2E”. Здесь перечислены конкретные архитектурные боли, которые модель увидела во входных данных.\n')
        for p in packs:
            md.append(f"\n### {p['title']}\n")
            md.append(f"**Почему сработало:** {p['trigger']}\n\n")
            md.append('**Решение:**\n'+bullet(p['decision']))
            md.append('\n**Обязательные контроли:**\n'+bullet(p['controls']))
            md.append('\n**Основные риски:**\n'+bullet(p['risks']))
            md.append('\n**Тесты, которые нужно заложить:**\n'+bullet(p['tests']))
        return ''.join(md)+'\n'

    def classify(self,f,c):
        steps=c['steps']; systems=c['systems']; channels=' '.join([s.get('channel','') for s in steps+systems]).lower()
        rps=safe_int(f.get('rps'),0); peak=safe_int(f.get('peak_factor'),1)
        highload=f['load_profile'] in ['highload','bursty'] or rps>=300 or peak>=5
        no_changes='no_changes' in f['change_policy'] or f['legacy']=='no_changes' or f.get('source_change_policy')=='forbidden'
        new_service_forbidden=f.get('new_service_policy') in ['reuse_existing_runtime','platform_only','forbidden']
        # existing_only is a normal enterprise constraint, not by itself a "dangerous compromise".
        # Treat it as a hard blocker only when new infrastructure is explicitly forbidden.
        new_infra_forbidden=f.get('new_infra_policy') == 'forbidden' or 'new_infra' in f.get('forbidden_channels',[])
        source_minimal_only=f.get('source_change_policy') in ['minimal_table_only','api_only','read_only']
        source_read_only=f.get('source_change_policy') in ['read_only','forbidden'] or 'read_only' in f.get('change_policy',[])
        source_can_add_minimal_outbox=(('add_outbox' in f.get('change_policy',[]) or 'outbox' in f.get('existing_capabilities',[])) or (f.get('source_change_policy') in ['allowed','minimal_table_only'] and 'add_event' not in f.get('change_policy',[]))) and not source_read_only
        compromise_mode=f.get('constraint_profile') in ['pragmatic','minimal_safe'] or f.get('budget_pressure') in ['high','extreme'] or f.get('deadline_pressure') in ['tight','urgent'] or new_service_forbidden or new_infra_forbidden or source_minimal_only or source_read_only
        existing=f['task_type'] in ['add_to_existing','replace_legacy','problem_audit'] or f['existing_state'] in ['production','legacy','partial']
        chain=f['task_type']=='e2e_chain' or f['step_count'] in ['4_7','8_plus'] or len(steps)>=4
        active_situations=set(f.get('business_situations',[]) if isinstance(f.get('business_situations'),list) else split_csv(f.get('business_situations','')))
        enrichment_intent=f.get('event_payload_intent') in ['enriched_event','snapshot_export']
        enrichment_needed=f.get('enrichment_required') in ['optional','required','critical'] or 'data_enrichment' in active_situations or enrichment_intent
        rest_enrichment=f.get('enrichment_channel')=='rest' or ('rest' in channels and enrichment_needed)
        single_kafka=f.get('kafka_topology')=='single_topic_only'
        source_no_kafka=f.get('source_has_kafka_infra') in ['no','adapter_only']
        event_owner_conflict=enrichment_needed and single_kafka and source_no_kafka and f.get('event_payload_intent') in ['enriched_event','snapshot_export']
        event_keywords = {'one_source_many_consumers','highload_write_stream','event_domain','data_synchronization','notification_flow'}
        explicit_event_intent = (
            ('kafka' in f.get('allowed_channels',[]) and (f.get('result_model') in ['notification','tracking','callback'] or bool(active_situations & event_keywords) or 'add_event' in f.get('change_policy',[]) or 'add_outbox' in f.get('change_policy',[])))
            or ('queue' in f.get('allowed_channels',[]) and f.get('result_model') in ['notification','tracking','callback'])
            or f.get('task_type') == 'event_domain'
        )
        # Dominant operation type is used by ranking, blockers and report wording.
        operation_kind = infer_operation_kind(f, c, {**locals(), 'business_situations': active_situations})
        reliability_key = required_reliability_key(operation_kind)
        return {
          'operation_kind':operation_kind,'reliability_key':reliability_key,
          'highload_stream_ingestion': highload_stream_ingestion_signal(f),
          'active_active_financial_write': active_active_financial_write_signal(f),
          'multi_tenant_noisy_neighbor': multi_tenant_noisy_neighbor_signal(f),
          'highload':highload,'lowload':f['load_profile']=='low','bursty':f['load_profile']=='bursty' or peak>=5,'rps':rps,'peak':peak,
          'existing':existing,'no_changes':no_changes,'can_change_core':'change_core' in f['change_policy'],'can_add_outbox':source_can_add_minimal_outbox,
          'can_add_event':'add_event' in f['change_policy'] or 'kafka' in f['existing_capabilities'],'can_add_cdc':'add_cdc' in f['change_policy'] or f['legacy']=='db_replica_only',
          'compromise_mode':compromise_mode,'new_service_forbidden':new_service_forbidden,'new_infra_forbidden':new_infra_forbidden,
          'source_minimal_only':source_minimal_only,'source_read_only':source_read_only,'source_can_add_minimal_outbox':source_can_add_minimal_outbox,
          'risk_appetite_high':f.get('risk_appetite')=='high','risk_appetite_low':f.get('risk_appetite')=='low',
          'chain':chain,'multi_level':f['chain_depth'] in ['multi_level','fanout','fanout_fanin'] or any(s.get('level','0') not in ['','0','1'] for s in steps),
          'fanout':f['chain_depth'] in ['fanout','fanout_fanin'] or sum(1 for s in steps if s.get('parent')=='3')>=2,
          'unknown_orchestration': chain and f['orchestration']=='unknown' and bool(active_situations.intersection({'application_or_order_creation','multi_step_business_process','distributed_transaction_saga','long_running_process'})) and not bool(active_situations.intersection({'webhook_callback','legacy_batch','api_composition','customer_360','read_model'})) and not enrichment_needed, 'choreography':f['orchestration']=='choreography', 'orchestrated':f['orchestration'] in ['orchestrator','hybrid','bpm'] or (enrichment_needed and f['orchestration']=='unknown'), 'bpm':f['orchestration']=='bpm' or f['step_count']=='8_plus',
          'sync':f['result_model']=='sync' or f['latency_sla'] in ['subsecond','seconds'], 'async':f['result_model'] in ['tracking','callback','notification'] or chain,
          'event_needed':explicit_event_intent or 'event' in channels or 'kafka' in channels or f['orchestration'] in ['choreography','hybrid'] or f.get('kafka_topology') in ['single_topic_only','raw_enriched_topics'], 'queue_needed':'queue' in f.get('allowed_channels',[]) or 'queue' in channels or (chain and f['failure_policy'] in ['retry','retry_compensate_manual']) or rest_enrichment,
          'file_needed':f['legacy']=='file_only' or 'sftp' in channels or 'file' in channels, 'soap_needed':f['legacy']=='soap_only' or 'soap' in channels,
          'cdc_needed':f['dwh']=='near_realtime' or f['legacy']=='db_replica_only' or 'cdc' in channels, 'etl_needed':f['dwh'] in ['batch','regulatory'] or 'etl' in channels,
          'dwh':f['task_type']=='dwh_analytics' or f['dwh']!='no' or 'dwh_reporting' in active_situations or dwh_data_lake_signal(f),
          'legacy':f['task_type'] in ['legacy_integration','replace_legacy'] or f['legacy']!='none', 'partner':f['task_type']=='external_partner' or f['auth']=='partner',
          'saga': chain and f['orchestration'] in ['orchestrator','hybrid','bpm'] and f['failure_policy'] in ['compensate','retry_compensate_manual','manual'],
          'outbox_needed': f['delivery'] in ['at_least_once','business_exactly_once'] and (explicit_event_intent or 'kafka' in channels or 'event' in channels or chain) and not no_changes,
          'inbox_needed': f['delivery'] in ['at_least_once','business_exactly_once'] or any(e.get('retry')=='yes' for e in c['errors']),
          'dedupe': f['delivery'] in ['at_least_once','business_exactly_once'] or any(e.get('retry')=='yes' for e in c['errors']),
          'strict_order':f['ordering'] in ['per_entity','global'], 'global_order':f['ordering']=='global', 'replay':f['replay'] in ['short','long','rebuild','audit'],
          'event_sourcing':f['history']=='event_sourcing' or f['source_of_truth']=='event_log' or f['replay'] in ['rebuild','audit'],
          'large_data':f['data_volume'] in ['large','very_large'] or highload, 'very_large':f['data_volume']=='very_large',
          'sensitive':f['sensitivity'] in ['pii','financial','high'] or any(x.get('sensitive') for x in c['fields']), 'regulated':f['sensitivity'] in ['financial','high'] or f['dwh']=='regulatory' or f['observability']=='regulated',
          'ha':f['availability'] in ['ha','multi_az','dr'], 'dr':f['availability']=='dr', 'many_systems':len(systems)>=3,
          'blocking_chain_len':sum(1 for s in steps if s.get('blocking')=='blocking'),
          'customer_visible':f.get('customer_visible') in ['yes','mixed'],
          'money_impact':f.get('money_impact') in ['yes','indirect'],
          'direct_money_impact':f.get('money_impact')=='yes',
          'regulatory_impact':f.get('regulatory_impact')=='yes',
          'read_heavy':f.get('read_frequency') in ['high','very_high'],
          'very_read_heavy':f.get('read_frequency')=='very_high',
          'write_heavy_business':f.get('change_frequency') in ['high','realtime'],
          'strict_freshness':f.get('freshness_requirement')=='strict' or f.get('business_priority')=='freshness',
          'stale_allowed':f.get('freshness_requirement') in ['up_to_5s','up_to_1m','up_to_15m','up_to_1h','daily'],
          'stale_dangerous':f.get('stale_data_impact') in ['financial','legal'],
          'prefer_speed':f.get('business_priority')=='speed' or f.get('response_time_expectation') in ['under_100ms','under_300ms'],
          'can_show_stale':f.get('unavailable_behavior')=='show_stale',
          'partial_response_ok':f.get('unavailable_behavior')=='partial_response',
          'queue_for_later':f.get('unavailable_behavior')=='queue_for_later',
          'unstable_external':f.get('external_dependency_stability') in ['unstable','limited'],
          'enrichment_needed':enrichment_needed, 'enrichment_intent':enrichment_intent, 'rest_enrichment':rest_enrichment,
          'single_kafka_only':single_kafka, 'raw_enriched_allowed':f.get('kafka_topology')=='raw_enriched_topics', 'source_lacks_kafka':source_no_kafka,
          'enrichment_required':f.get('enrichment_required') in ['required','critical'], 'enrichment_critical':f.get('enrichment_required')=='critical',
          'enrichment_consistency_unknown':enrichment_needed and f.get('enrichment_consistency')=='unknown',
          'event_owner_conflict':event_owner_conflict,
          'single_kafka_only': single_kafka, 'source_lacks_kafka': source_no_kafka,
          'shared_topic_selective': (('shared_topic_selective_consumer' in active_situations) or shared_topic_consumer_signal(f) or (single_kafka and not kafka_destination_enrichment_signal(f) and ('highload_write_stream' in active_situations or 'new_topic_forbidden' in f.get('forbidden_channels',[])))),
          'new_topic_forbidden': 'new_topic_forbidden' in f.get('forbidden_channels',[]),
          'business_situations':active_situations}

    def input_quality(self,f,c,t):
        """Жёсткая проверка: можно ли вообще проектировать на этих входных данных.
        Не смешивать с оценкой выбранного паттерна: это confidence/readiness входа.
        """
        gaps=[]
        hard=[]
        business_situations=t.get('business_situations') or set()
        def empty(x): return not str(f.get(x,'')).strip()
        if empty('business_goal') and not business_situations and empty('user_action') and not (c.get('systems') and c.get('steps')):
            hard.append('Не описана бизнес-цель: какую бизнес-проблему решает интеграция.')
        if not business_situations and not (t['customer_visible'] or t['money_impact'] or t['dwh'] or t['legacy'] or t['chain']) and not (str(f.get('business_goal','')).strip() and c.get('systems')):
            hard.append('Не выбрана и не распознана бизнес-ситуация: экран, операция, DWH, webhook, legacy, миграция и т.д.')
        if not c.get('systems') and empty('source_system') and not (t.get('file_needed') or file_exchange_signal(f) or 'batch_processing' in business_situations or 'near_real_time_decision' in business_situations or 'dwh_reporting' in business_situations or 'privacy_erasure' in business_situations or 'highload_stream_ingestion' in business_situations or 'active_active_financial_write' in business_situations or 'multi_tenant_noisy_neighbor' in business_situations or highload_stream_ingestion_signal(f) or active_active_financial_write_signal(f) or multi_tenant_noisy_neighbor_signal(f) or near_realtime_strong_signal(f)):
            hard.append('Не описаны системы-участники или хотя бы система-инициатор.')
        special_without_steps = bool(business_situations & {'shared_topic_selective_consumer','migration_or_strangler','multi_source_aggregation','dwh_reporting','regulatory_process','webhook_callback','batch_processing','data_enrichment','near_real_time_decision','privacy_erasure','legacy_integration','external_api_dependency','highload_stream_ingestion','active_active_financial_write','multi_tenant_noisy_neighbor'})
        if not c.get('steps') and f.get('task_type') not in ['new_from_scratch'] and not special_without_steps:
            hard.append('Для выбранного типа задачи не описаны шаги/цепочка процесса.')
        if f.get('load_profile')=='unknown' and not str(f.get('rps','')).strip():
            gaps.append('Не указана нагрузка: low/medium/highload или RPS/TPS.')
        if f.get('source_of_truth')=='unclear': gaps.append('Не определён source of truth.')
        if f.get('ownership')=='unclear': gaps.append('Не определено владение данными.')
        if t.get('unknown_orchestration'): hard.append('Для сложной цепочки не выбран способ управления: orchestrator/choreography/hybrid/BPM.')
        if t['customer_visible'] and not c.get('statuses') and f.get('result_model') in ['tracking','notification']:
            gaps.append('Клиентский сценарий требует понятной статусной модели и last_updated.')
        if t['direct_money_impact'] and f.get('delivery') not in ['business_exactly_once','at_least_once','strict']:
            gaps.append('Для финансовой операции не выбран безопасный delivery/idempotency режим.')
        score=100-len(hard)*25-len(gaps)*8
        return {'blocked': bool(hard) or score < 35, 'hard_gaps': hard, 'soft_gaps': gaps, 'score': max(0,min(100,score))}

    def business_model(self,f,c,t):
        active=set(t.get('business_situations') or [])
        # Autodetect scenarios from stable business signals.
        if t['customer_visible'] and ('status' in (f.get('user_action','')+' '+f.get('business_goal','')).lower() or f.get('result_model')=='tracking'):
            active.add('client_status_screen')
        if t['direct_money_impact']:
            active.add('financial_operation'); active.add('exactly_once_required')
        if t['regulatory_impact'] or t['regulated']:
            active.add('regulatory_process')
        if t['read_heavy']:
            active.add('highload_read')
        if t['highload'] and (t['event_needed'] or t['queue_needed']):
            active.add('highload_write_stream')
        if t['chain']:
            active.add('multi_step_business_process')
        if t['saga']:
            active.add('distributed_transaction_saga')
        if t['dwh']:
            active.add('dwh_reporting')
        if t['legacy']:
            active.add('legacy_integration')
        if t['partner'] or t['unstable_external']:
            active.add('external_api_dependency')
        if t['fanout']:
            active.add('one_source_many_consumers')
        if t['strict_order']:
            active.add('strict_ordering_required')
        if t['sensitive']:
            active.add('personal_data_exchange')
        if t['bursty']:
            active.add('peak_load_process')
        if f.get('unavailable_behavior') in ['queue_for_later','manual_review'] or f.get('response_time_expectation')=='async_ok':
            active.add('async_heavy_processing')

        derived=[]; controls=[]; conflicts=[]; questions=[]; pattern_boosts=set()
        def req(x):
            if x not in derived: derived.append(x)
        def ctrl(x):
            if x not in controls: controls.append(x)
        if 'application_or_order_creation' in active:
            req('Создание заявки/заказа должно сначала надёжно принять команду, сохранить бизнес-операцию и вернуть понятный идентификатор.')
            ctrl('Сразу возвращать application/order id; внешние обогащения переводить в статусы процесса.')
        if 'client_status_screen' in active:
            req('Клиенту нужен быстрый и понятный статус, а не зависание экрана.')
            req('Нужны status history, last_updated и человекочитаемые промежуточные статусы.')
            pattern_boosts.update(['read_model_business','cache','fallback'])
            ctrl('Показывать время последнего обновления и статус "обновляется".')
        if 'highload_read' in active:
            if t['stale_allowed'] and not t['stale_dangerous']:
                req('Данные часто читаются; допустим быстрый контур чтения с контролируемым устареванием.')
                pattern_boosts.update(['cache','read_model_business','cqrs'])
                ctrl('TTL/invalidation/cache stampede protection/cache warmup.')
            elif t['strict_freshness']:
                req('Частое чтение требует оптимизации без потери актуальности: индексы, read-through с коротким TTL или replica/read model с read-your-writes.')
                pattern_boosts.update(['read_model_business'])
        if 'highload_write_stream' in active:
            req('Поток событий/highload-запись требует буферизации, партиционирования, backpressure, DLQ/retry topic и мониторинга lag.')
            pattern_boosts.update(['queue','scaling'])
        if 'shared_topic_selective_consumer' in active or t.get('shared_topic_selective'):
            active.add('shared_topic_selective_consumer')
            req('Общий Kafka topic с малой долей нужных событий — это selective consumption, а не outbox-кейс: надо считать filtered ratio, lag, poll/fetch, commit policy и нагрузку на БД.')
            req('Если отдельный topic/source-change запрещены, фильтрация на стороне consumer допустима как компромисс при capacity plan и мониторинге lag.')
            pattern_boosts.update(['kafka','inbox','scaling'])
            ctrl('Commit offset только после успешной обработки нужных событий; ненужные события можно пропускать без записи, но метриками считать filtered/accepted ratio.')
            ctrl('Для accepted-событий обязательны идемпотентная запись в sink, DLQ/quarantine для poison events и replay/reprocess policy.')
        if 'financial_operation' in active or 'exactly_once_required' in active:
            req('Для денег нужен practically-once: idempotency key, operation table, unique constraints, audit, reconciliation.')
            pattern_boosts.update(['postgres','inbox','outbox'])
            ctrl('Кэш не должен использоваться для финального финансового решения.')
        if 'reference_data' in active:
            req('Справочники требуют source of truth, версионирования значений, TTL/инвалидации и даты начала действия.')
            pattern_boosts.update(['cache','read_model_business'])
        if 'webhook_callback' in active:
            req('Callback/webhook нужно принимать идемпотентно: signature validation, external_event_id, inbox, async processing, replay.')
            pattern_boosts.update(['webhook','inbox','queue','fallback'])
            ctrl('ACK должен подтверждать приём, а не финальную бизнес-обработку, если обработка асинхронная.')
        if 'migration_strangler' in active:
            active.add('migration_or_strangler')
        if 'api_composition' in active or 'customer_360' in active:
            active.add('multi_source_aggregation'); active.add('many_sources_one_consumer')
            req('Экран собирает данные из нескольких источников; нужны timeout per source, partial response и подписи свежести по каждому блоку.')
            pattern_boosts.update(['fallback','cache','read_model_business'])
            ctrl('Не превращать BFF в монолитный процессор бизнес-логики; держать правила агрегации у клиентского сценария.')
        if 'data_synchronization' in active:
            req('Синхронизация данных требует явного source of truth, версии записи, delta/snapshot sync и reconciliation.')
            pattern_boosts.update(['cdc','etl','inbox'])
        if 'multi_source_aggregation' in active or 'many_sources_one_consumer' in active:
            req('Агрегация из нескольких источников требует правил приоритета источников, partial response, timeout per source и last_updated по блокам.')
            pattern_boosts.update(['read_model_business','fallback','cache'])
        if 'batch_processing' in active:
            req('Batch/job требует chunking, checkpoint, restartability, retry failed chunks, dead-letter table и итоговую сверку.')
            pattern_boosts.update(['etl','queue'])
        if 'near_real_time_decision' in active:
            req('Near real-time решение требует низкой задержки, precomputed features/cache, fallback decision и backpressure.')
            pattern_boosts.update(['cache','queue','scaling'])
        if 'data_enrichment' in active or t.get('enrichment_needed'):
            req('Проверки/обогащение нужно делить на обязательные и отложенные; для недоступных проверок нужен timeout/fallback/manual review.')
            pattern_boosts.update(['queue','fallback'])
            if t.get('event_needed'):
                req('Если Kafka должна получить уже обогащённое событие, владелец исходной сущности остаётся владельцем факта изменения, а обогащение выполняет integration publisher/adapter после outbox.')
                req('Нужно явно разделить business owner события, technical publisher и owner дополнительных данных.')
                pattern_boosts.update(['outbox','kafka','integration_publisher'])
                ctrl('REST-обогащение нельзя делать в транзакции изменения сущности; при сбое enrichment запись остаётся в retry/failed/reprocess.')
                ctrl('В событии обязательны aggregateId/entityId, aggregateVersion, eventId, occurredAt, publishedAt, correlationId и source/outbox event id.')
            if t.get('single_kafka_only'):
                req('При одном Kafka topic нельзя полагаться на raw→enriched pipeline; нужно delayed publish финального события через pending outbox или честно менять тип события на snapshot/export prepared.')
            if t.get('source_lacks_kafka'):
                req('Отсутствие Kafka-инфраструктуры в source-сервисе не переносит ownership события; допустим внешний publisher/adapter, читающий outbox/integration table source-сервиса.')
            if t.get('enrichment_consistency_unknown'):
                questions.append('Дополнительные данные должны соответствовать моменту изменения сущности, моменту публикации события или допускается best effort?')
        if 'notification_flow' in active:
            req('Уведомления должны быть побочным асинхронным потоком с дедупликацией, шаблонами, retry/DLQ и статусом доставки.')
            pattern_boosts.update(['queue','inbox'])
        if 'long_running_process' in active:
            req('Долгий процесс требует дедлайнов этапов, timeout scheduler, escalation, manual task queue и audit history.')
            pattern_boosts.update(['saga','queue'])
        if 'migration_or_strangler' in active:
            req('Миграция/замена системы требует parallel run, feature flags, shadow compare, reconciliation и rollback plan.')
            pattern_boosts.update(['cdc','fallback'])
        if 'multi_step_business_process' in active:
            req('Нужен владелец процесса, state machine, таймауты, retry policy и manual recovery.')
            pattern_boosts.update(['saga','queue','outbox','inbox'])
        if 'distributed_transaction_saga' in active:
            req('Для частичного успеха нужны компенсации по шагам и правила, что делать при сбое компенсации.')
            pattern_boosts.add('saga')
        if 'external_api_dependency' in active or 'unstable_external_provider' in active:
            req('Внешнюю нестабильность нужно изолировать: timeout, retry with backoff, circuit breaker, rate limit, fallback.')
            pattern_boosts.update(['fallback','queue'])
            ctrl('Не держать пользовательский поток на медленном внешнем API без таймаута и деградации.')
        if 'dwh_reporting' in active:
            req('DWH/отчётность не должны блокировать core/client flow; нужны quality checks, lineage, incremental load и reconciliation.')
            pattern_boosts.update(['cdc','etl'])
        if 'personal_data_exchange' in active:
            req('ПДн/чувствительные данные требуют минимизации, маскирования логов, шифрования и аудита доступа.')
        if 'strict_ordering_required' in active:
            req('Нужны aggregate_id/partition key, sequence/version и обработка out-of-order событий.')
        if 'peak_load_process' in active:
            req('Пиковую нагрузку нужно сглаживать через rate limit/backpressure/queue/cache prewarm/autoscaling.')
            pattern_boosts.add('scaling')
        field_names_lower={str(x.get('name','')).lower() for x in c.get('fields',[])}
        has_snapshot_markers=bool(field_names_lower & {'dataasof','data_as_of','dataversion','data_version','sourceeventid','source_event_id','updatedat','updated_at','aggregateversion','aggregate_version'})
        current_at_publish_acceptable = f.get('enrichment_consistency')=='current_at_publish' and f.get('event_payload_intent') in ['snapshot_export','thin_event'] and has_snapshot_markers
        if t.get('enrichment_critical') and (f.get('enrichment_consistency')=='best_effort' or (f.get('enrichment_consistency')=='current_at_publish' and not current_at_publish_acceptable)):
            conflicts.append('Критичное enrichment нельзя безоговорочно брать current/best-effort: нужен snapshot, versioned API или явная юридическая оговорка consistency level.')
        if t['prefer_speed'] and t['strict_freshness'] and (t['unstable_external'] or t['chain']):
            conflicts.append('Конфликт: требуется очень быстрый ответ и строгая актуальность, но есть цепочка/внешняя зависимость. Нужно ослабить скорость, ослабить freshness или разделить экран на последний известный статус + фоновое обновление.')
        if t['stale_dangerous'] and 'cache' in pattern_boosts:
            conflicts.append('Осторожно с кэшем: устаревшие данные могут привести к финансовым/юридическим последствиям. Нужен короткий TTL, маркировка freshness или запрет кэша для финального решения.')
        if not derived:
            questions.append('Выберите хотя бы одну бизнес-ситуацию или уточните: кто использует результат, как быстро нужен ответ и что будет при ошибке.')
        for q in ['Какой максимальный допустимый возраст данных на клиентском экране?', 'Что хуже для бизнеса: медленный ответ или слегка устаревший результат?', 'Можно ли показать частичный/последний известный результат при сбое источника?']:
            if q not in questions: questions.append(q)
        return {'active_scenarios':sorted(active),'derived_requirements':derived,'recommended_controls':controls,'pattern_boosts':sorted(pattern_boosts),'conflicts':conflicts,'questions':questions}

    def add_pattern(self,p,id,name,score,why,controls,risks):
        if score>0: p.append({'id':id,'name':name,'score':score,'why':why,'controls':controls,'risks':risks})
    def patterns(self,f,c,t):
        p=[]
        boosts=set(c.get('business',{}).get('pattern_boosts',[]))
        self.add_pattern(p,'gateway','API Gateway / Edge',45 if t['partner'] or t['sync'] else 20,['Единый вход, auth, rate limit, routing.'],['auth','rate limit','WAF','routing','request validation'],['Gateway не должен содержать бизнес-логику.'])
        self.add_pattern(p,'rest','REST API + OpenAPI',50 if allowed(f,'rest') and (t['sync'] or f['result_model']=='tracking') else 10 if allowed(f,'rest') else 0,['Команды и получение статусов.'],['OpenAPI','idempotency','timeouts','error model','versioning'],['Не строить длинную sync-цепочку.'])
        self.add_pattern(p,'kafka','Kafka/Event Streaming',70 if allowed(f,'kafka') and (t['event_needed'] or t['replay'] or t['fanout'] or t['highload'] or t.get('shared_topic_selective')) else 0,['События, replay, fan-out, highload.'],['schema registry','partition key','consumer groups','DLQ/retry topics','lag monitoring'],['Нужны идемпотентные consumer-ы.'])
        self.add_pattern(p,'selective_consumer','Selective Kafka Consumer',82 if t.get('shared_topic_selective') else 0,['Consumer читает общий topic и отбирает только нужные события по key/header/body.'],['filter_ratio','consumer_lag','poll_fetch_tuning','idempotent_sink','offset_after_processing','poison_quarantine'],['Если нужных событий очень мало, bottleneck может быть не БД, а чтение/десериализация/фильтрация всего topic.'])
        self.add_pattern(p,'queue','Message Queue / Workers',60 if allowed(f,'queue') and (t['queue_needed'] or t['async']) else 0,['Долгие задачи, retry, backpressure.'],['ack/nack','retry backoff','DLQ','visibility timeout','worker pool'],['Не event log для долгого replay.'])
        self.add_pattern(p,'webhook','Webhook/Callback',65 if 'webhook' in boosts else 45 if allowed(f,'webhook') and f['result_model']=='callback' else 0,['Асинхронный ответ внешнему инициатору.'],['signature','replay protection','retry contract','callback audit'],['Внешние callback-и ненадёжны.'])
        self.add_pattern(p,'file','Batch/File/SFTP',70 if allowed(f,'sftp') and t['file_needed'] else 0,['Legacy/file-only/batch.'],['manifest','checksum','registry','quarantine','error report','reprocessing'],['Не online real-time.'])
        self.add_pattern(p,'soap','SOAP Legacy Adapter',70 if allowed(f,'soap') and t['soap_needed'] else 0,['SOAP-only legacy.'],['adapter','WSDL/XSD','mapping','circuit breaker'],['Изолировать legacy-модель.'])
        self.add_pattern(p,'cdc','CDC',65 if allowed(f,'cdc') and (t['cdc_needed'] or (t['no_changes'] and t['existing'])) else 0,['Near-real-time чтение изменений без вмешательства.'],['offsets','schema evolution','delete handling','dedupe','monitoring'],['CDC не command API.'])
        self.add_pattern(p,'etl','ETL/ELT',60 if allowed(f,'etl') and t['dwh'] else 0,['DWH/отчётность/batch.'],['lineage','quality checks','reconciliation','incremental load'],['Не блокировать core flow.'])
        self.add_pattern(p,'outbox','Transactional Outbox',75 if (t['outbox_needed'] or t.get('enrichment_needed')) and (not t['existing'] or t['can_add_outbox'] or t.get('source_lacks_kafka')) else 0,['Атомарно сохранить данные и событие.'],['outbox table','publisher','retry','stuck alerts'],['Требует изменения транзакционного контура.'])
        self.add_pattern(p,'integration_publisher','Integration Publisher / Event Enrichment',78 if t.get('enrichment_needed') and t.get('event_needed') else 0,['Технический publisher читает outbox/integration table, обогащает payload через владельца дополнительных данных и публикует событие без переноса ownership.'],['pending outbox','REST timeout','retry/backoff','failed/reprocess status','sourceEventId','aggregateVersion','consistency marker'],['REST-обогащение может задержать публикацию; нужна политика при сбое и согласованная свежесть enrichment-данных.'])
        self.add_pattern(p,'inbox','Inbox / Idempotent Consumer',70 if t['inbox_needed'] else 0,['Защита от дублей.'],['message registry','payload hash','unique keys','retention'],['Нужен retention.'])
        self.add_pattern(p,'saga','Saga / Process Manager',80 if t['saga'] else 0,['Многошаговый управляемый процесс.'],['state machine','шаги процесса','attempts','timeouts','compensation','manual recovery'],['Без компенсаций не работает.'])
        self.add_pattern(p,'bpm','Workflow/BPM Engine',65 if t['bpm'] else 0,['8+ шагов, human tasks или сложный workflow.'],['process definition','human tasks','timeouts','audit'],['Может быть избыточен.'])
        self.add_pattern(p,'cqrs','CQRS / Read Models',55 if 'cqrs' in boosts else 45 if t['fanout'] or f['ownership']=='field_level' or t['highload'] else 0,['Разные модели чтения/записи, highload/fan-out.'],['projections','rebuild','eventual consistency'],['Усложняет систему.'])
        self.add_pattern(p,'read_model_business','Business-driven Read Model',70 if 'read_model_business' in boosts else 0,['Из бизнес-контекста следует отдельный быстрый контур чтения/статусов.'],['projection table','last_updated','rebuild','read-your-writes rule','freshness marker'],['Нужно явно объяснять пользователю свежесть данных.'])
        self.add_pattern(p,'cache','Cache / Fast Read Path',68 if 'cache' in boosts else 0,['Частое чтение, допустимое устаревание и/или горячий клиентский экран.'],['TTL','invalidation','cache stampede protection','warmup','stale marker'],['Не использовать кэш для финального финансового/юридического решения.'])
        self.add_pattern(p,'fallback','Fallback / Graceful Degradation',60 if 'fallback' in boosts or t['can_show_stale'] or t['partial_response_ok'] else 0,['Бизнес допускает последний известный/частичный результат или есть нестабильные зависимости.'],['stale response policy','partial response','circuit breaker','degraded status','manual review'],['Fallback должен быть явно виден пользователю/оператору.'])
        self.add_pattern(p,'postgres','PostgreSQL OLTP',60,['Транзакционное хранилище.'],['constraints','indexes','migrations','backup','partitioning'],['Не shared DB между сервисами.'])
        self.add_pattern(p,'event_sourcing','Event Sourcing',75 if t['event_sourcing'] else 0,['Event log как source of truth.'],['event store','snapshots','versioning','projection rebuild'],['Сложность выше, применять только при необходимости.'])
        if t['highload']:
            self.add_pattern(p,'scaling','Highload Controls',70,['Высокая/пиковая нагрузка.'],['rate limit','backpressure','autoscaling','partitioning','connection pools','load tests','capacity plan'],['Без capacity plan решение рискованно.'])
        return sorted(p,key=lambda x:x['score'],reverse=True)

    def make_variant(self,name,pids,base,why,complexity,latency,reliability,risks,ids,blocked=False):
        used=[x for x in pids if x in ids and ids[x]['score']>=10]
        raw_score=base+(sum(ids[x]['score'] for x in used)//max(1,len(used)))
        score=min(100, raw_score)
        if blocked:
            raw_score=5; score=5
        return {'name':name,'pattern_ids':used,'patterns':[ids[x]['name'] for x in used],'score':score,'raw_score':raw_score,'why':why,'complexity':complexity,'latency':latency,'reliability':reliability,'risks':risks,'blocked':blocked}
    def variants(self,f,c,t,pats,anti_pre):
        ids={p['id']:p for p in pats}; out=[]
        active=set(c.get('business',{}).get('active_scenarios',[]))
        iq=c.get('input_quality',{})
        if iq.get('blocked'):
            reasons=iq.get('hard_gaps') or iq.get('soft_gaps') or ['Недостаточно данных для выбора архитектуры.']
            return [self.make_variant('Architecture decision blocked: недостаточно данных',['rest','postgres'],0,reasons,'Не определена','Не определена','Не определена',['Заполнить минимальный бизнес-контекст, системы, шаги, SLA/source of truth.'],ids,True)]
        if t['unknown_orchestration']:
            return [self.make_variant('Architecture decision blocked: выберите способ управления цепочкой',['rest','cache','postgres'],0,['Для сложной цепочки нельзя корректно выбрать архитектуру без orchestration/choreography/BPM.'],'Не определена','Не определена','Не определена',['Сначала выбрать владельца процесса и модель управления цепочкой.'],ids,True)]
        if (t['no_changes'] or t.get('source_read_only')) and not t.get('file_needed'):
            out.append(self.make_variant('Non-invasive Existing Process Extension',['cdc','etl','file','soap','postgres','scaling'],80,['Production/source flow менять нельзя, поэтому допустимы read-only/CDC/file/adapter подходы или явно рискованный export/snapshot compromise.'],'Средняя','batch/near-real-time','Средняя/высокая',['Нельзя гарантировать атомарную связь бизнес-изменения и публикации события из read-only канала; нужен ADR с residual risk.'],ids))
        if t['choreography']:
            out.append(self.make_variant('Event Choreography',['kafka','outbox','inbox','cqrs','postgres','scaling'],75,['Пользователь выбрал choreography: системы реагируют на события без центрального orchestrator.'],'Высокая','Асинхронная','Высокая',['Сложнее E2E tracing и recovery; нужна сильная observability.'],ids))
        if t.get('shared_topic_selective'):
            out.append(self.make_variant('Shared Topic Selective Consumer + Idempotent Sink',['kafka','selective_consumer','inbox','postgres','scaling','fallback'],88,['Есть общий Kafka topic, отдельный topic/source-change невозможны или нежелательны; нужно безопасно читать весь поток, фильтровать нужные события и писать только accepted subset в БД.'],'Средняя','Async; зависит от lag и размера общего topic','Высокая при capacity plan + idempotent sink + DLQ/quarantine',['Это компромисс, а не идеал: лучше иметь выделенный topic/producer-side routing, но если это запрещено — компенсировать lag monitoring, filter ratio, batch writes и replay plan.'],ids))
        if privacy_erasure_signal(f) or 'privacy_erasure' in active:
            out.append(self.make_variant('Privacy / Data Erasure Orchestration Pipeline',['rest','queue','saga','inbox','postgres','fallback','scaling'],91,['Запрос на удаление/стирание ПДн — это отдельный privacy workflow: нужно найти данные во всех системах, проверить legal hold/retention exceptions, разослать команды удаления, собрать receipts/evidence и обработать исключения.'],'Высокая','Async с трекингом статуса','Высокая при evidence registry + audit + re-drive',['Нельзя трактовать как обычную синхронизацию: есть юридические исключения, доказательство исполнения и ручная эскалация.'],ids))
        if cdc_modernization_signal(f) or 'cdc_legacy_modernization' in active:
            out.append(self.make_variant('CDC Legacy Modernization / Operational Projection',['cdc','kafka','inbox','read_model_business','postgres','fallback','scaling'],89,['Legacy/source менять нельзя, но нужны операционные события или read-model: безопасный каркас — CDC/WAL/LSN, watermark/gap detection, schema evolution, idempotent projection и replay.'],'Средняя/высокая','Near-real-time по CDC lag','Средняя/высокая при reconciliation + replay',['CDC не является command API и не доказывает бизнес-намерение; для доменных событий нужно честно указать семантику snapshot/projection.'],ids))
        if t.get('event_needed') and not t['chain'] and not t.get('enrichment_needed') and not t['no_changes'] and not t.get('shared_topic_selective'):
            out.append(self.make_variant('Event-driven + Transactional Outbox',['rest','outbox','kafka','inbox','postgres','scaling'],83,['Есть запись бизнес-сущности и доставка события другим потребителям: главный риск — dual-write DB↔broker, поэтому нужен Transactional Outbox, publisher и идемпотентные consumers.'],'Средняя','Async/eventual consistency','Высокая при outbox+inbox+DLQ+replay',['Outbox не заменяет бизнес-state-machine, если процесс многошаговый; нужен aggregateId, eventId, aggregateVersion и мониторинг stuck events.'],ids))
        if f['chain_depth']=='fanout_fanin' and t['orchestrated'] and not t['no_changes']:
            out.append(self.make_variant('Fan-out/Fan-in Orchestrated Process',['gateway','rest','saga','outbox','inbox','kafka','queue','cqrs','read_model_business','cache','fallback','postgres','scaling'],88,['Цепочка содержит параллельные ветки и последующую агрегацию; нужен управляющий процесс, join/barrier, таймауты веток и partial-failure policy.'],'Очень высокая','Acceptance быстро, итог async','Высокая при явных join/timeout/reconciliation правилах',['Сложность агрегации результатов веток; нужен barrier timeout и правила partial success.'],ids))
        if t['chain'] and t['orchestrated'] and not t['no_changes']:
            out.append(self.make_variant('Orchestrated E2E Process',['gateway','rest','saga','bpm','outbox','inbox','kafka','queue','read_model_business','fallback','postgres','scaling'],75,['Многоуровневая цепочка требует владельца процесса, статусов, retry, compensation и manual recovery.'],'Высокая','Acceptance быстро, итог async','Высокая',['State machine complexity; нужны компенсации по шагам.'],ids))

        if t.get('enrichment_needed') and t.get('event_needed') and t.get('compromise_mode') and t.get('source_can_add_minimal_outbox') and t.get('new_service_forbidden'):
            why=['Компромисс под ограничения: новый сервис/микросервис дорогой или запрещён, но минимальное изменение source допустимо. Поэтому source фиксирует бизнес-факт и pending outbox, а publisher реализуется как job/module в существующем runtime или платформенный adapter, без переноса ownership.']
            if t.get('single_kafka_only'):
                why.append('При одном Kafka topic публикуется только финальный enriched payload; raw-факт остаётся во внутреннем outbox до enrichment.')
            out.append(self.make_variant('Compromise: Source Outbox + Embedded/Platform Publisher',['rest','outbox','integration_publisher','kafka','inbox','fallback','postgres','scaling'],76,why,'Средняя','Delayed publish; без нового микросервиса','Средняя/высокая при строгих контролях',['Компромисс дешевле целевого отдельного publisher-сервиса, но повышает coupling и эксплуатационную сложность существующего runtime.', 'Нельзя убирать минимальные контроли: idempotency, retry/backoff, FAILED/reprocess, correlationId, aggregateVersion.'],ids))
        if t.get('enrichment_needed') and t.get('event_needed') and t.get('compromise_mode') and t.get('source_read_only'):
            why=['Жёсткий компромисс: source менять нельзя, поэтому надёжный source-owned outbox недоступен. Допустим только read-only/CDC/polling подход, который должен быть честно оформлен как рискованный export/snapshot, а не как полноценное доменное событие владельца.']
            out.append(self.make_variant('Compromise: CDC/Polling + Enrichment Export',['cdc','rest','integration_publisher','kafka','inbox','fallback','postgres','scaling'],61,why,'Средняя/высокая','Near-real-time или batch','Средняя',['Нельзя гарантировать атомарную связь commit source → enrichment → Kafka publish.', 'Нужны reconciliation, gap detection, watermark/offset, manual replay; event name лучше EntitySnapshotPrepared/ExportReady, не EntityUpdated.'],ids))

        if t.get('enrichment_needed') and t.get('event_needed') and t.get('raw_enriched_allowed') and not t['no_changes']:
            why=['Kafka-топология допускает отдельные raw и enriched события: source-сервис публикует/фиксирует raw-факт изменения, enrichment processor формирует enriched-событие для потребителя.']
            if t.get('source_lacks_kafka'):
                why.append('Если Kafka нет в source-сервисе, raw-факт всё равно должен рождаться из source outbox/integration table, а технический publisher может быть внешним.')
            out.append(self.make_variant('Raw + Enriched Event Pipeline',['rest','outbox','integration_publisher','kafka','inbox','fallback','postgres','scaling'],84,why,'Высокая','Raw быстро, enriched после обогащения','Высокая при outbox+retry+versioning',['Нужно два контракта события и согласованная семантика: raw domain fact и enriched snapshot/export.', 'Потребители должны понимать, какое событие использовать.'],ids))
        if t.get('enrichment_needed') and t.get('event_needed') and not t['no_changes']:
            why=['Потребителю нужно финальное событие с дополнительными данными; факт изменения должен рождаться у владельца сущности, а REST-обогащение выполняется после commit в integration publisher.']
            if t.get('single_kafka_only'):
                why.append('Так как Kafka topic/контур один, raw→enriched топики не используются: outbox держит pending-событие до успешного enrichment и публикует только финальный payload.')
            if t.get('source_lacks_kafka'):
                why.append('Kafka-инфраструктура отсутствует в source-сервисе, поэтому нужен внешний technical publisher/adapter, но не перенос business ownership в сервис с частью данных.')
            out.append(self.make_variant('Outbox + REST Enrichment Publisher',['rest','outbox','integration_publisher','kafka','inbox','fallback','postgres','scaling'],82,why,'Средняя/высокая','Публикация delayed до enrichment','Высокая при outbox+retry+versioning',['Если enrichment REST недоступен, событие задерживается; нужны retry, failed/reprocess и алертинг.', 'Нужно согласовать consistency: enrichment as-of-change, current-at-publish или best-effort.'],ids))
        if regulatory_schema_signal(f) and ('regulatory_process' in t.get('business_situations',set()) or t.get('regulatory_impact')) and not t.get('direct_money_impact'):
            reg_base = 88 if t.get('operation_kind')=='regulatory_schema_change' else 72
            out.append(self.make_variant('Regulatory Data Model Change Impact Analysis',['rest','postgres','etl','cdc','fallback','scaling'],reg_base,['Регуляторное изменение — это прежде всего impact-analysis модели данных, контрактов, БД, DWH, обратной совместимости, backfill и тестов потребителей; file/Outbox/DWH являются слоями реализации, а не главным ответом.'],'Средняя/высокая','Зависит от rollout/backfill','Высокая при versioning + migration + reconciliation',['Нужно явно описать старую и новую модель, mapping, nullable/default rules, schemaVersion, consumer compatibility, migration/backfill и исторические данные.'],ids))
        if t['existing'] and not t['no_changes']:
            out.append(self.make_variant('Backward-compatible Extension with Events',['rest','outbox','kafka','inbox','read_model_business','fallback','postgres','scaling'],60,['Добавление интеграции в production без поломки текущих потребителей.'],'Средняя','Async для новых потребителей','Высокая',['Нужны версии контрактов, parallel run и миграция статусов.'],ids))
        if t['file_needed']:
            out.append(self.make_variant('Batch/File Integration',['file','postgres','scaling'],65,['File-only/регламентный обмен.'],'Средняя','Высокая задержка','Высокая при manifest/checksum/quarantine',['Частичные ошибки и повторная обработка.'],ids))
        if t['soap_needed']:
            out.append(self.make_variant('SOAP Legacy Adapter Integration',['soap','rest','postgres','scaling'],68,['SOAP-only legacy изолируется adapter layer и переводится в единую доменную модель.'],'Средняя','Sync/async через adapter','Средняя/высокая',['SOAP fault mapping, circuit breaker, version mismatch.'],ids))
        if t.get('highload_stream_ingestion') or t.get('operation_kind')=='highload_stream_ingestion':
            out.append(self.make_variant('Highload Stream Ingestion / Stream Processing',['gateway','kafka','queue','inbox','read_model_business','fallback','postgres','scaling'],86,['Поток телеметрии/событий в highload: главный каркас — ingestion, partitioning, backpressure, out-of-order handling, stream processing/alerting; DWH/Data Lake является downstream-потребителем, а не top-level решением.'],'Высокая','Realtime/near-real-time','Высокая при partition key + idempotent sink + replay',['Нужны partition key, watermark/event_time, handling late events, hot partition controls, lag metrics и DLQ/quarantine.'],ids))
        if t['dwh']:
            dwh_base = 84 if t.get('operation_kind')=='dwh_offload' else 58
            out.append(self.make_variant('Data Pipeline / DWH',['cdc','etl','postgres','scaling'],dwh_base,['Аналитика, регуляторная отчётность или near-real-time DWH/offload; главный смысл — retention, watermark/offset, lineage, quality checks и reconciliation, а не просто transport batch/file.'],'Средняя','Batch/near-real-time','Высокая для аналитики',['Нужны reconciliation, lineage, data quality, retention/archive и backfill.'],ids))
        active=set(c.get('business',{}).get('active_scenarios',[]))
        explicit_financial_variant = ('financial_operation' in t.get('business_situations',set()) or f.get('delivery')=='business_exactly_once' and not (f.get('result_model')=='callback' and not t.get('chain')))
        if explicit_financial_variant and ('financial_operation' in active or 'exactly_once_required' in active):
            financial_pids=['gateway','rest','postgres','outbox','inbox','saga','fallback','scaling']
            if 'webhook_callback' in active:
                financial_pids.insert(2,'webhook'); financial_pids.insert(6,'queue')
            out.append(self.make_variant('Financial Operation State Machine',financial_pids,76,['Операция влияет на деньги/баланс/лимит: нужна таблица операции, idempotency key, уникальные ограничения, audit и reconciliation.'],'Средняя/высокая','Sync acceptance или async completion','Высокая при operation state machine и reconciliation',['Нельзя принимать финальное финансовое решение из кэша; повторы должны возвращать тот же результат.'],ids))
        if loyalty_ledger_signal(f):
            out.append(self.make_variant('Financial/Loyalty Ledger State Machine',['gateway','rest','postgres','inbox','outbox','kafka','fallback','scaling'],83,['POS/покупка/баллы требуют ledger-подхода: каждая операция начисления/списания фиксируется отдельной записью, повтор возвращает тот же результат, баланс выводится из проводок или контролируемой проекции.'],'Средняя','Async или sync acceptance','Высокая при unique operation id + ledger entries + reconciliation',['Нельзя считать чек/receipt privacy evidence; это бизнес-транзакция. Нужны reversal/refund policy и сверка с POS.'],ids))
        if ('async_heavy_processing' in active or ('batch_processing' in active and not t['dwh'])) and 'webhook_callback' not in active:
            out.append(self.make_variant('Async Job / Heavy Processing Flow',['gateway','rest','queue','inbox','fallback','postgres','scaling'],68,['Пользовательскому потоку нельзя ждать тяжёлую обработку: нужен task_id/job_id, worker, status table, retry failed chunks.'],'Средняя','Acceptance быстро, результат async','Средняя/высокая',['Нужны restartability, дедупликация задач, срок хранения результата и экран статуса.'],ids))
        if 'data_synchronization' in active or ('many_sources_one_consumer' in active and not t['chain']):
            out.append(self.make_variant('Data Synchronization / Source-of-Truth Sync',['cdc','etl','kafka','inbox','postgres','scaling'],67,['Нужно синхронизировать состояние между системами: source of truth, версии, delta/snapshot, conflict resolution и reconciliation.'],'Средняя/высокая','Batch/near-real-time','Высокая для копий данных',['Нужно описать правила конфликтов и deleted-события/удаления.'],ids))
        if 'migration_or_strangler' in active:
            out.append(self.make_variant('Migration / Strangler Fig',['gateway','rest','cdc','etl','fallback','postgres','scaling'],69,['Замена системы без остановки бизнеса: adapter, parallel run, feature flags, shadow compare, reconciliation, rollback.'],'Высокая','Пошаговое переключение','Средняя/высокая',['Dual-write опасен без сверки; нужен план отката и сравнение результатов.'],ids))
        if 'near_real_time_decision' in active:
            out.append(self.make_variant('Near Real-time Decision Flow',['gateway','rest','kafka','queue','cache','fallback','postgres','scaling'],71,['Нужно быстро принять решение при потоке данных: precomputed features/cache, bounded latency, backpressure и fallback decision.'],'Высокая','Миллисекунды/секунды','Средняя/высокая',['Нужно определить, можно ли принять решение без части данных и как обрабатывать деградацию.'],ids))
        if 'webhook_callback' in active:
            out.append(self.make_variant('Webhook Intake + Inbox Processing',['gateway','webhook','rest','inbox','queue','kafka','fallback','postgres','scaling'],72,['Бизнес-сценарий callback/webhook требует быстрый ACK, проверку подписи, идемпотентный приём и асинхронную обработку.'],'Средняя','ACK быстро, обработка async','Высокая при Inbox/DLQ/replay',['Callback может прийти дважды, поздно или не по порядку; нужна reconciliation.'],ids))
        if ('highload_read' in active or 'client_status_screen' in active) and not t['chain']:
            out.append(self.make_variant('Fast Read / Cached Read Model',['gateway','rest','cqrs','read_model_business','cache','fallback','postgres','scaling'],70,['Бизнес требует быстрый контур чтения/статусов с контролируемой свежестью и деградацией при сбое источника.'],'Средняя','<100-300ms при прогретом контуре','Средняя/высокая',['Нужно явно управлять TTL, invalidation, cache stampede и read-your-writes.'],ids))
        if 'multi_source_aggregation' in active or 'many_sources_one_consumer' in active:
            out.append(self.make_variant('BFF/API Composition with Partial Response',['gateway','rest','fallback','read_model_business','cache','postgres','scaling'],66,['Экран/потребитель собирает данные из нескольких источников; нужны timeout per source, partial response и правила свежести по блокам.'],'Средняя/высокая','Sync с таймаутами или read model','Средняя',['Без partial policy один медленный источник ломает весь экран.'],ids))
        if 'reference_data' in active:
            out.append(self.make_variant('Reference Data API + Versioned Cache',['rest','read_model_business','cache','postgres','scaling'],75,['Справочники редко меняются и часто читаются; нужны версии, даты действия и контролируемая инвалидация.'],'Низкая/средняя','Быстро','Высокая',['Нужно управлять версией справочника и совместимостью значений.'],ids))
        if 'external_api_dependency' in active and not t['chain']:
            out.append(self.make_variant('External API Adapter with Resilience',['gateway','rest','queue','fallback','postgres','scaling'],62,['Внешнюю зависимость нужно изолировать adapter-слоем с timeout, retry/backoff, circuit breaker и rate limit.'],'Средняя','Sync или async по SLA','Средняя/высокая',['Повтор запроса должен быть безопасным; нужны лимиты и аудит вызовов.'],ids))
        if t['queue_needed'] and not t['chain']:
            out.append(self.make_variant('Queue-based Worker Flow',['rest','queue','inbox','fallback','postgres','scaling'],50,['Асинхронные задачи и retry без полноценного event stream.'],'Средняя','Async','Средняя/высокая',['Нет долгого replay как в Kafka.'],ids))
        if not out:
            out.append(self.make_variant('Basic API + DB',['rest','postgres'],30,['Базовая несложная интеграция.'],'Низкая','Sync','Средняя',['Мало контроля сложных ошибок.'],ids))
        # apply penalties
        for v in out:
            if t['highload'] and 'scaling' not in v['pattern_ids']: v['score']-=20; v['risks'].append('Highload без scaling controls.')
            if t['no_changes'] and any(x in v['pattern_ids'] for x in ['outbox','saga']): v['score']-=60; v['risks'].append('Вариант требует изменений production flow.')
            if t.get('new_service_forbidden') and 'integration_publisher' in v['pattern_ids'] and not v['name'].startswith('Compromise'):
                v['score']-=22; v['risks'].append('Ограничение: новый сервис нежелателен/запрещён; нужен embedded job, platform adapter или отдельное согласование стоимости.')
            if t.get('new_infra_forbidden') and 'kafka' in v['pattern_ids'] and 'kafka' not in f.get('existing_capabilities',[]) and f.get('kafka_topology')!='no_kafka':
                v['score']-=18; v['risks'].append('Ограничение: новая инфраструктура запрещена; использовать только существующий Kafka/queue контур или выбрать read-only/batch компромисс.')
            if t.get('source_read_only') and 'outbox' in v['pattern_ids'] and not v['name'].startswith('Compromise: CDC'):
                v['score']-=45; v['risks'].append('Ограничение: source read-only/forbidden, outbox в source недоступен без пересогласования.')
            if t.get('risk_appetite_low') and v['name'].startswith('Compromise: CDC'):
                v['score']-=25; v['risks'].append('Risk appetite низкий: CDC/polling компромисс не должен идти в production без явного исключения и reconciliation.')
            if t['choreography'] and v['name'].startswith('Orchestrated'): v['score']-=80
            if f['orchestration']=='orchestrator' and v['name']=='Event Choreography': v['score']-=35
            if f['legacy']=='file_only' and not v['name'].startswith('Batch/File'):
                v['score']-=45; v['risks'].append('Legacy file-only: online/orchestrated вариант невозможен без adapter или изменения legacy.')
            active_core_scenarios = {'application_or_order_creation','distributed_transaction_saga','financial_operation','long_running_process'}
            explicit_core = bool(active & active_core_scenarios) or ('multi_step_business_process' in t.get('business_situations',set()))
            complex_core = (t['chain'] and explicit_core and (t['orchestrated'] or f['chain_depth']=='fanout_fanin'))
            primary_core_names = {'Fan-out/Fan-in Orchestrated Process','Orchestrated E2E Process','Financial Operation State Machine','Migration / Strangler Fig','Event Choreography','Non-invasive Existing Process Extension'}
            if f['legacy']=='soap_only' and 'soap' not in v['pattern_ids'] and v['name'] not in ['SOAP Legacy Adapter Integration']:
                if complex_core and v['name'] in primary_core_names:
                    v['score']-=5; v['risks'].append('SOAP-only legacy должен быть оформлен как отдельный adapter layer внутри общей архитектуры, а не как главный вариант.')
                else:
                    v['score']-=30; v['risks'].append('SOAP-only legacy требует SOAP adapter.')
            priority=0
            if kafka_destination_enrichment_signal(f) and v['name'] in ['Outbox + REST Enrichment Publisher','Compromise: CDC/Polling + Enrichment Export']:
                priority += (300 if (t.get('source_read_only') and v['name']=='Compromise: CDC/Polling + Enrichment Export') else (260 if not (t.get('chain') and f.get('step_count') in ['4_7','8_plus']) else 35))
            if loyalty_ledger_signal(f) and v['name']=='Financial/Loyalty Ledger State Machine':
                priority += 260
            if t.get('shared_topic_selective') and not kafka_destination_enrichment_signal(f) and v['name']=='Shared Topic Selective Consumer + Idempotent Sink': priority+=170
            if t.get('shared_topic_selective') and v['name']=='Event-driven + Transactional Outbox':
                v['score']=min(v['score'],70); priority-=80; v['risks'].append('В shared-topic/filtering кейсе Outbox — не главный ответ; нужен selective consumer/capacity/backpressure слой.')
            if (t['file_needed'] or file_exchange_signal(f) or t.get('operation_kind')=='batch_file_exchange') and t.get('operation_kind')!='dwh_offload' and v['name']=='Batch/File Integration': priority+=(116 if (f.get('legacy')=='file_only' or f.get('task_type')=='legacy_integration' or file_exchange_signal(f)) else 35)
            if t.get('soap_needed') and v['name']=='SOAP Legacy Adapter Integration':
                priority += 55
                v['score']=max(v.get('score',0),76)
            if t['no_changes'] and t['existing'] and v['name']=='Non-invasive Existing Process Extension': priority+=85
            if t['choreography'] and v['name']=='Event Choreography': priority+=80
            if f['chain_depth']=='fanout_fanin' and v['name']=='Fan-out/Fan-in Orchestrated Process':
                explicit_multi_step = 'multi_step_business_process' in t.get('business_situations',set())
                priority += (12 if ('multi_source_aggregation' in active or 'many_sources_one_consumer' in active) and not explicit_multi_step else 95)
            if t['chain'] and t['orchestrated'] and v['name']=='Orchestrated E2E Process': priority+=(75 if explicit_core else 15)
            if ('financial_operation' in active or 'exactly_once_required' in active) and v['name']=='Financial Operation State Machine':
                explicit_financial = ('financial_operation' in t.get('business_situations',set()) or 'exactly_once_required' in t.get('business_situations',set()) or f.get('delivery')=='business_exactly_once')
                # Если это широкий E2E-процесс на 8+ шагов/multi-level, financial state machine
                # является обязательным внутренним контуром контроля денег/идемпотентности,
                # но не должна подменять Orchestrated E2E/Fan-out-Fan-in как top-level архитектуру.
                wide_orchestrated_core = complex_core and f.get('step_count')=='8_plus' and f.get('chain_depth') in ['multi_level','fanout','fanout_fanin']
                priority += (35 if f['chain_depth']=='fanout_fanin' else (55 if wide_orchestrated_core else (105 if explicit_financial else 25)))
                if wide_orchestrated_core:
                    v['risks'].append('Financial state machine нужен как слой контроля финансовой операции внутри E2E/Saga, но верхнеуровнево процессом должен управлять Orchestrated E2E/Fan-out-Fan-in.')
            if t.get('enrichment_needed') and t.get('event_needed') and v['name']=='Raw + Enriched Event Pipeline':
                priority += 120 if t.get('raw_enriched_allowed') else 0
            if t.get('enrichment_needed') and t.get('event_needed') and v['name']=='Compromise: Source Outbox + Embedded/Platform Publisher':
                priority += (55 if complex_core else (135 if t.get('new_service_forbidden') and t.get('source_can_add_minimal_outbox') else 70))
            if t.get('enrichment_needed') and t.get('event_needed') and v['name']=='Compromise: CDC/Polling + Enrichment Export':
                priority += 125 if t.get('source_read_only') else 40
            if t.get('enrichment_needed') and t.get('event_needed') and v['name']=='Outbox + REST Enrichment Publisher':
                base_enrich_priority = 110 if (t.get('single_kafka_only') or (t.get('source_lacks_kafka') and not t.get('raw_enriched_allowed')) or (f.get('event_payload_intent') in ['enriched_event','snapshot_export'] and not t.get('raw_enriched_allowed'))) else 80
                priority += (25 if complex_core else base_enrich_priority)
            if privacy_erasure_signal(f) and v['name']=='Privacy / Data Erasure Orchestration Pipeline': priority+=230
            if (cdc_modernization_signal(f) or 'cdc_legacy_modernization' in active) and not ({'shared_topic_selective_consumer','migration_or_strangler'} & active) and v['name']=='CDC Legacy Modernization / Operational Projection': priority+=240
            if t.get('operation_kind')=='near_real_time_decision' and v['name']=='Near Real-time Decision Flow': priority+=220
            if t.get('operation_kind')=='highload_stream_ingestion' and v['name']=='Highload Stream Ingestion / Stream Processing': priority+=240
            if t.get('operation_kind')=='highload_stream_ingestion' and v['name']=='Data Pipeline / DWH':
                v['score']=min(v.get('score',0),60); priority-=120; v['risks'].append('DWH/Data Lake — downstream-потребитель; top-level для telemetry/highload должен быть stream ingestion/processing.')
            if 'migration_or_strangler' in active and v['name']=='Migration / Strangler Fig': priority+=165
            if 'migration_or_strangler' in active and v['name']=='SOAP Legacy Adapter Integration':
                v['score']=min(v['score'],66); priority-=110; v['risks'].append('SOAP adapter — это anti-corruption/legacy layer внутри Strangler migration, а не top-level стратегия миграции.')
            if 'data_synchronization' in active and 'migration_or_strangler' not in active and v['name']=='Data Synchronization / Source-of-Truth Sync': priority+=(85 if not complex_core else 25)
            if 'near_real_time_decision' in active and v['name']=='Near Real-time Decision Flow': priority+=(80 if not complex_core else 20)
            if ('async_heavy_processing' in active or 'batch_processing' in active) and v['name']=='Async Job / Heavy Processing Flow': priority+=(75 if not complex_core else 18)
            if 'webhook_callback' in active and v['name']=='Webhook Intake + Inbox Processing':
                priority+=(190 if not complex_core else 15)
                if not complex_core: v['score']=max(v.get('score',0),90)
            if ('dwh_reporting' in active or t['dwh']) and not t['chain'] and v['name']=='Data Pipeline / DWH': priority+=(98 if f.get('task_type')=='dwh_analytics' else 74)
            if ('highload_read' in active or 'client_status_screen' in active) and v['name']=='Fast Read / Cached Read Model': priority += (30 if 'reference_data' in active else 70)
            if 'reference_data' in active and v['name']=='Reference Data API + Versioned Cache': priority+=88
            if ('multi_source_aggregation' in active or 'many_sources_one_consumer' in active) and v['name']=='BFF/API Composition with Partial Response': priority += (180 if t.get('operation_kind')=='bff_composition' else (20 if 'data_synchronization' in active or complex_core else 120))
            if t.get('operation_kind')=='external_partner_adapter' and v['name']=='External API Adapter with Resilience': priority += 125
            if t.get('operation_kind')=='dwh_offload' and not complex_core and v['name']=='Data Pipeline / DWH': priority += 130
            if t.get('operation_kind')=='regulatory_schema_change' and not complex_core and v['name']=='Regulatory Data Model Change Impact Analysis': priority += 180

            # Слойные решения не должны становиться top-level, если они являются частью большого E2E/core-flow.
            layer_only_when_core = {
                'SOAP Legacy Adapter Integration': 'Legacy/SOAP adapter — это слой external/legacy adapters внутри E2E, а не главный вариант процесса.',
                'Data Pipeline / DWH': 'DWH/ETL — это слой data/reporting, он не должен подменять core-flow.',
                'Webhook Intake + Inbox Processing': 'Webhook/callback — это слой intake для внешнего результата, а не главный вариант E2E-процесса.',
                'Fast Read / Cached Read Model': 'Read model/cache — это слой чтения/статусов, а не главный вариант бизнес-операции.',
                'External API Adapter with Resilience': 'External API adapter — это интеграционный слой, а не главный вариант сложного процесса.',
                'Reference Data API + Versioned Cache': 'Reference data/cache — это справочный слой, а не главный вариант сложного процесса.',
                'Async Job / Heavy Processing Flow': 'Async job — это слой фоновой обработки, если в кейсе есть более широкий E2E/core-flow.',
                'Data Synchronization / Source-of-Truth Sync': 'Data sync — это слой синхронизации данных, если есть управляемый бизнес-процесс.',
                'Near Real-time Decision Flow': 'Near real-time decision — это слой принятия решения внутри более широкого процесса.',
                'BFF/API Composition with Partial Response': 'BFF/composition — это слой чтения/экрана, если кейс является E2E-процессом.',
                'Outbox + REST Enrichment Publisher': 'Enrichment publisher — это integration layer внутри более широкой Saga, если есть управляемый бизнес-процесс.'
            }
            if complex_core and v['name'] in layer_only_when_core and not (t.get('operation_kind')=='bff_composition' and v['name']=='BFF/API Composition with Partial Response'):
                v['score']=min(v['score'],72)
                priority-=80
                v['risks'].append(layer_only_when_core[v['name']])

            # Enrichment/publisher-компромисс может быть top-level только для задачи доставки события.
            # В широком E2E/core-flow он является integration layer внутри Saga/Fan-out/Fan-in,
            # иначе инструмент ошибочно заменяет архитектуру процесса техническим publisher-слоем.
            strong_core_flow = (
                t['chain'] and (
                    bool(active & {'application_or_order_creation','distributed_transaction_saga','financial_operation','long_running_process'})
                    or (f.get('chain_depth')=='fanout_fanin' and f.get('step_count')=='8_plus')
                )
            )
            enrichment_layer_names = {
                'Compromise: Source Outbox + Embedded/Platform Publisher',
                'Compromise: CDC/Polling + Enrichment Export',
                'Outbox + REST Enrichment Publisher',
                'Raw + Enriched Event Pipeline'
            }
            if strong_core_flow and v['name'] in enrichment_layer_names:
                v['score']=min(v['score'],72)
                priority-=90
                v['risks'].append('Enrichment/publisher — это слой доставки события внутри E2E/Saga/Fan-out архитектуры, а не главный вариант бизнес-процесса.')
            # DWH/webhook/legacy также не должны подменять финансовую операцию без длинной цепочки.
            if ('financial_operation' in active or 'exactly_once_required' in active) and v['name'] in ['SOAP Legacy Adapter Integration','Data Pipeline / DWH','Webhook Intake + Inbox Processing','Fast Read / Cached Read Model','External API Adapter with Resilience']:
                v['score']=min(v['score'],70)
                priority-=45
                v['risks'].append('Финансовая/ровно-один-раз операция должна быть главным контуром; этот вариант допустим только как слой.')
            v['score']=max(0,min(100,v['score']))
            v['_priority']=priority
        return sorted(out,key=lambda x:(x.get('_priority',0),x['score']),reverse=True)

    def detect_case_classes(self,f,c,t):
        active=set(c.get('business',{}).get('active_scenarios',[])) | set(t.get('business_situations',set()))
        classes=[]
        def add(cid,title,score,why,top,controls=None):
            classes.append({'id':cid,'title':title,'score':score,'why':why,'top_level':top,'required_controls':controls or []})
        # Hard business context overrides: these must stay above generic transport layers.
        # Regulatory schema/model change and DWH/offload are business problem classes; file/batch is only an implementation channel.
        regulatory_schema_like = regulatory_schema_signal(f) and ('regulatory_process' in active or t.get('regulatory_impact'))
        dwh_offload_like = (t.get('operation_kind')=='dwh_offload' or ((dwh_data_lake_signal(f) or f.get('task_type')=='dwh_analytics' or 'dwh_reporting' in active) and not t.get('chain') and f.get('legacy')!='file_only'))
        if privacy_erasure_signal(f) or 'privacy_erasure' in active:
            add('privacy_erasure_pipeline','Privacy / data erasure workflow',118,'Запрос на удаление ПДн — это юридически значимый распределённый workflow, а не обычная синхронизация: нужны discovery/lineage, legal hold, per-system commands, evidence и exception handling.','Privacy / Data Erasure Orchestration Pipeline',['data_discovery_lineage','identity_validation','legal_hold_check','retention_exception_policy','per_system_erase_command','receipt_evidence_registry','audit','re_drive','manual_escalation'])
        if (cdc_modernization_signal(f) or 'cdc_legacy_modernization' in active) and t.get('operation_kind') not in ['dwh_offload','near_real_time_decision'] and not ({'shared_topic_selective_consumer','migration_or_strangler'} & active) and not (t.get('chain') and f.get('step_count') in ['4_7','8_plus']):
            add('cdc_legacy_modernization','CDC legacy modernization / operational projection',116,'Legacy/source менять нельзя; цель — операционный поток изменений/read-model через CDC/WAL/LSN, а не DWH/offload.','CDC Legacy Modernization / Operational Projection',['source_lsn_or_watermark','gap_detection','schema_evolution','delete_handling','idempotent_projection','projection_version','consumer_lag','replay_plan','reconciliation'])
        if kafka_destination_enrichment_signal(f) or (t.get('enrichment_needed') and t.get('event_needed') and not t.get('shared_topic_selective')):
            add('data_enrichment_pipeline','Event enrichment publisher / export',(113 if not (t.get('chain') and f.get('step_count') in ['4_7','8_plus']) else 66),'Нужно сформировать и опубликовать enriched event; главный каркас — ownership факта изменения, outbox/integration table или честный CDC/polling export, REST enrichment и managed publish/reprocess. Это не selective consumer.','Outbox + REST Enrichment Publisher' if not t.get('source_read_only') else 'Compromise: CDC/Polling + Enrichment Export',['source_of_truth','event_owner','outbox_or_watermark','rest_enrichment_timeout','data_as_of','publisher_retry_state','reprocess','reconciliation','residual_risk_adr'])
        if (t.get('shared_topic_selective') or 'shared_topic_selective_consumer' in active) and not kafka_destination_enrichment_signal(f):
            add('shared_topic_selective_consumer','Shared Kafka topic / selective consumer',101,'Нужна выборочная обработка общего topic при запрете отдельного topic/source-change; главный каркас — consumer filtering + capacity/backpressure + idempotent sink, а не publisher/outbox.','Shared Topic Selective Consumer + Idempotent Sink',['filter_ratio','consumer_lag','partition_strategy','idempotent_sink','offset_after_processing','dlq_quarantine','batch_write','replay_plan'])
        if t.get('highload_stream_ingestion') or t.get('operation_kind')=='highload_stream_ingestion':
            add('highload_stream_ingestion','Highload stream ingestion / processing',117,'Телеметрия/массовый поток событий с realtime alerting и out-of-order рисками: главный класс — ingestion + stream processing + backpressure; DWH/Data Lake только downstream layer.','Highload Stream Ingestion / Stream Processing',['partition_key','event_id','event_time_watermark','late_event_policy','hot_partition_detection','backpressure','stream_alerting','dlq_quarantine','consumer_lag','replay_plan'])
        if t.get('active_active_financial_write'):
            add('active_active_financial_write','Active-active financial write risk',120,'Active-active запись финансового баланса/лимита опасна из-за split-brain/double-spend; это не GREEN без single-writer/ledger/consensus стратегии.','Financial Operation State Machine',['single_writer_per_account_or_shard','append_only_ledger','operation_id_idempotency','double_spend_prevention','conflict_resolution_or_consensus','reconciliation','manual_correction','dr_failover_policy'])
        if t.get('multi_tenant_noisy_neighbor'):
            add('multi_tenant_noisy_neighbor','Multi-tenant noisy-neighbor risk',114,'Один крупный tenant может забить общий consumer pool и создать lag для остальных; нужны tenant isolation, quotas/fair scheduling и метрики lag per tenant.','Shared Topic Selective Consumer + Idempotent Sink',['tenant_id_partitioning','tenant_quotas','separate_consumer_pools_for_large_tenants','fair_scheduling','backpressure','lag_per_tenant_metrics','capacity_guardrails'])
        # Read-only Customer 360/BFF is a business class, not a weak keyword match.
        # It is evaluated before Loyalty ledger so a source named Loyalty cannot hijack the recommendation.
        direct_situations=set(f.get('business_situations',[]) if isinstance(f.get('business_situations'),list) else split_csv(f.get('business_situations','')))
        bff_like_early=('multi_source_aggregation' in active or 'customer_360' in active or 'api_composition' in active or 'read_model' in active or 'many_sources_one_consumer' in active or bff_readonly_composition_signal(f))
        explicit_core_early=(f.get('task_type')=='e2e_chain' or t.get('chain') and f.get('step_count') in ['4_7','8_plus'] or bool(direct_situations & {'application_or_order_creation','multi_step_business_process','distributed_transaction_saga','long_running_process','financial_operation','exactly_once_required'}))
        if bff_like_early and (not explicit_core_early or t.get('operation_kind')=='bff_composition'):
            bff_score_early = 119 if t.get('operation_kind')=='bff_composition' else 110
            add('bff_api_composition','BFF / API composition',bff_score_early,'Read-only экран/Customer 360 собирает блоки из разных источников. Главные риски — timeout per source, partial response, freshness labels и cache/degradation policy; это не ledger и не Saga.','BFF/API Composition with Partial Response',['timeout_per_source','partial_response','freshness_per_block','fallback','cache_policy','per_source_error_model','correlation_id'])
        if loyalty_ledger_signal(f):
            add('business_ledger','Financial/Loyalty ledger state machine',111,'Баллы/баланс/начисления по POS-чекам — это ledger/state-machine с practically-once обработкой, а не privacy или generic E2E.','Financial/Loyalty Ledger State Machine',['source_transaction_id','operation_id','idempotency_key','unique_constraint','balance_delta','ledger_entry','reversal_policy','audit','reconciliation'])
        if (t.get('no_changes') or t.get('source_read_only')) and not t.get('file_needed') and not ('migration_or_strangler' in active or f.get('task_type')=='replace_legacy') and not t.get('shared_topic_selective'):
            add('non_invasive_extension','Non-invasive extension of existing/source flow',109,'Source/core flow нельзя менять; главный каркас должен быть read-only/CDC/file/adapter или честный compromise, а не invasive Saga/Outbox.','Non-invasive Existing Process Extension',['read_only_boundary','cdc_or_file_export','local_projection','reconciliation','residual_risk_adr'])
        if (t.get('file_needed') or file_exchange_signal(f) or t.get('operation_kind')=='batch_file_exchange') and not regulatory_schema_like and not dwh_offload_like:
            add('batch_file_exchange','Batch/File/SFTP exchange',112,'Файловый/SFTP/batch обмен требует manifest, checksum, staging, quarantine, restartability, ack/error file и reconciliation; это не ordinary external API adapter.','Batch/File Integration',['manifest','checksum','file_registry','staging','quarantine','ack_or_error_file','reprocessing','reconciliation'])
        if regulatory_schema_like and not ('financial_operation' in active or t.get('direct_money_impact')):
            reg_score = 112 if t.get('operation_kind')=='regulatory_schema_change' and not (f.get('task_type')=='e2e_chain' and t.get('chain')) else 96
            add('regulatory_schema_change','Regulatory / schema impact',reg_score,'Регуляторное изменение затрагивает модель данных, API/события, БД, DWH, совместимость потребителей и backfill; batch/file/DWH — только слои реализации.','Regulatory Data Model Change Impact Analysis',['impact_analysis','schemaVersion','data_model_versioning','api_backward_compatibility','db_migration','backfill','consumer_contract_tests','dwh_lineage','audit'])
        if dwh_offload_like and not regulatory_schema_like and not any(x['id'] in ['non_invasive_extension','batch_file_exchange'] for x in classes):
            add('dwh_pipeline','DWH / analytical pipeline',108,'Главная задача — разгрузка prod/DWH/отчётность: retention/archive, watermark/offset, staging, data quality, lineage, reconciliation и backfill. Это выше, чем простой batch/file transport.','Data Pipeline / DWH',['cdc_or_etl','watermark_or_offset','snapshot_id','lineage','quality_checks','retention_archive','reconciliation','backfill'])
        if 'migration_or_strangler' in active or f.get('task_type')=='replace_legacy':
            add('strangler_migration','Legacy replacement / strangler',100,'Legacy нельзя переписать big bang; нужен фасад, parallel run, shadow compare, feature flags и rollback.','Migration / Strangler Fig',['facade','feature_flags','parallel_run','shadow_compare','rollback','reconciliation'])
        bff_like=('multi_source_aggregation' in active or 'customer_360' in active or 'api_composition' in active or 'many_sources_one_consumer' in active)
        direct_situations=set(f.get('business_situations',[]) if isinstance(f.get('business_situations'),list) else split_csv(f.get('business_situations','')))
        explicit_core=(f.get('task_type')=='e2e_chain' or t.get('chain') and f.get('step_count') in ['4_7','8_plus'] or bool(direct_situations & {'application_or_order_creation','multi_step_business_process','distributed_transaction_saga','long_running_process','financial_operation','exactly_once_required'}))
        if bff_like and (not explicit_core or t.get('operation_kind')=='bff_composition') and not any(x['id']=='bff_api_composition' for x in classes):
            bff_score = 106 if t.get('operation_kind')=='bff_composition' else 96
            add('bff_api_composition','BFF / API composition',bff_score,'Экран/потребитель собирает блоки из разных источников и должен переживать частичную недоступность.','BFF/API Composition with Partial Response',['timeout_per_source','partial_response','freshness_per_block','fallback','cache_policy'])
        if ('highload_read' in active or 'client_status_screen' in active) and not explicit_core and not bff_like:
            add('read_model_cqrs','Fast read / cached read model',95,'Главная задача — быстро показать статус/данные чтения с контролируемой свежестью.','Fast Read / Cached Read Model',['read_model','ttl','freshness_marker','cache_invalidation','read_your_writes_policy'])
        if ('financial_operation' in direct_situations or 'exactly_once_required' in direct_situations or t.get('direct_money_impact')):
            wide_core = t.get('chain') and (f.get('chain_depth') in ['fanout_fanin'] or f.get('step_count')=='8_plus' or bool(direct_situations & {'distributed_transaction_saga','multi_step_business_process','application_or_order_creation'}))
            financial_score = 78 if wide_core else 97
            add('financial_state_machine','Financial operation state machine',financial_score,'Операция влияет на деньги/лимиты/регуляторику; главным контуром должна быть operation state machine с idempotency, audit и reconciliation.','Financial Operation State Machine',['operation_table','idempotency_key','unique_constraints','audit','reconciliation','manual_review'])
        if ('async_heavy_processing' in direct_situations or ('batch_processing' in direct_situations and not t.get('dwh'))):
            add('async_job_flow','Async job / heavy processing',96,'Пользовательский поток должен быстро принять задачу, а тяжёлая обработка должна идти в worker/job flow.','Async Job / Heavy Processing Flow',['job_id','queue','worker','retry_failed_chunks','dlq','status_table'])
        if (t.get('saga') or (t.get('chain') and explicit_core)) and t.get('operation_kind')!='bff_composition':
            add('saga_orchestration','Saga / long-running E2E process',94,'Процесс состоит из нескольких систем/шагов; нужен владелец процесса, статусы, retry, compensation/manual recovery.','Orchestrated E2E Process',['process_state','step_statuses','timeouts','retry_dlq','compensation','manual_recovery'])
        # Enrichment is top-level only when the task is really about event delivery, not a wide E2E business process.
        if t.get('enrichment_needed') and t.get('event_needed'):
            enrich_score = 93 if not explicit_core else 72
            add('data_enrichment_pipeline','Event enrichment before publish',enrich_score,'Потребителю нужно событие с дополнительными данными; owner факта изменения и technical publisher должны быть разделены.','Outbox + REST Enrichment Publisher',['source_outbox_or_cdc','enrichment_consistency','retry_failed_reprocess','sourceEventId','aggregateVersion'])
        if 'webhook_callback' in active or f.get('result_model')=='callback':
            # If the incoming integration model is callback/webhook, webhook intake is the top-level edge architecture;
            # financial state machine may remain an internal state-transition layer.
            webhook_score = 118 if f.get('result_model')=='callback' else (114 if not explicit_core else 108)
            add('webhook_intake','Webhook / callback intake',webhook_score,'Внешний callback должен быстро подтверждаться, проверяться по подписи и обрабатываться асинхронно через Inbox.','Webhook Intake + Inbox Processing',['signature_raw_body','inbox','quick_ack','async_worker','idempotent_transition','reconciliation'])
        dual_write = (t.get('event_needed') and not t.get('enrichment_needed') and not t.get('chain') and not ('webhook_callback' in active or f.get('result_model')=='callback') and (('one_source_many_consumers' in active) or ('highload_write_stream' in active) or 'add_event' in f.get('change_policy',[]) or 'add_outbox' in f.get('change_policy',[]) or 'kafka' in f.get('allowed_channels',[])))
        if dual_write:
            add('dual_write_db_broker','DB + broker dual-write',93,'Нужно атомарно связать изменение бизнес-сущности и публикацию события в Kafka/очередь.','Event-driven + Transactional Outbox',['outbox','publisher','idempotent_consumer','dlq','replay','lag_monitoring'])
        if 'near_real_time_decision' in direct_situations:
            nr_score = 115 if near_realtime_strong_signal(f) else 96
            add('near_real_time_decision','Near real-time decision flow',nr_score,'Нужно быстро принять решение при потоке данных; нужны bounded latency, precomputed features/cache, backpressure и fallback decision.','Near Real-time Decision Flow',['bounded_latency','feature_snapshot_id','rules_or_model_version','precomputed_cache','backpressure','fallback_decision','audit','metrics'])
        if (t.get('partner') or t.get('unstable_external') or 'external_api_dependency' in active) and not explicit_core and not ('webhook_callback' in active or f.get('result_model')=='callback') and not ('highload_read' in active or 'client_status_screen' in active or 'multi_source_aggregation' in active):
            add('external_partner_adapter','External partner/API adapter',97,'Нестабильное/лимитированное внешнее API должно быть изолировано adapter-слоем: timeout budget, retry/backoff, circuit breaker, rate limit, status tracking, fallback/manual review и reconciliation.','External API Adapter with Resilience',['timeout_budget','retry_backoff','circuit_breaker','rate_limit','bulkhead','partner_request_id','status_tracking','manual_review','reconciliation'])
        if (t.get('dwh') or 'dwh_reporting' in active or f.get('task_type')=='dwh_analytics') and not any(x['id']=='dwh_pipeline' for x in classes) and not any(x['id']=='regulatory_schema_change' for x in classes):
            score = 98 if (f.get('task_type')=='dwh_analytics' or t.get('operation_kind')=='dwh_offload') and not explicit_core else 58
            add('dwh_pipeline','DWH / analytical pipeline',score,'Отчётность и аналитика должны быть неблокирующим контуром с lineage, retention, watermark/offset и reconciliation; это не command/event idempotency case.','Data Pipeline / DWH',['cdc_or_etl','watermark_or_offset','lineage','quality_checks','retention','reconciliation'])
        if regulatory_schema_signal(f) and ('regulatory_process' in direct_situations or t.get('regulatory_impact')) and not t.get('direct_money_impact') and not any(x['id']=='regulatory_schema_change' for x in classes):
            reg_score = 105 if (f.get('task_type')!='dwh_analytics' and not explicit_core and t.get('operation_kind')=='regulatory_schema_change') else 60
            add('regulatory_schema_change','Regulatory / schema impact',reg_score,'Регуляторные изменения затрагивают модель данных, контракты, отчётность, совместимость и тесты; это top-level impact-analysis, а события/Outbox/DWH являются слоями внедрения.','Regulatory Data Model Change Impact Analysis',['impact_analysis','schemaVersion','data_model_versioning','api_backward_compatibility','db_migration','backfill','consumer_contract_tests','dwh_lineage','audit'])
        if not classes:
            add('basic_sync_api','Basic sync/API integration',40,'По заполненным данным не найден специальный сложный класс; используйте базовый API-подход с таймаутами и контрактами.','Basic API + DB',['openapi','timeouts','error_model','logging'])
        classes=sorted(classes,key=lambda x:x['score'],reverse=True)
        return classes[:5]

    def apply_case_class_ranking(self,f,c,t,variants,case_classes):
        if not variants or not case_classes:
            return variants
        primary=case_classes[0]['id']
        top_by_class={
            'non_invasive_extension':['Non-invasive Existing Process Extension'],
            'privacy_erasure_pipeline':['Privacy / Data Erasure Orchestration Pipeline','Orchestrated E2E Process'],
            'business_ledger':['Financial/Loyalty Ledger State Machine','Financial Operation State Machine'],
            'cdc_legacy_modernization':['CDC Legacy Modernization / Operational Projection','Non-invasive Existing Process Extension','Migration / Strangler Fig'],
            'webhook_intake':['Webhook Intake + Inbox Processing'],
            'data_enrichment_pipeline':['Outbox + REST Enrichment Publisher','Raw + Enriched Event Pipeline','Compromise: Source Outbox + Embedded/Platform Publisher','Compromise: CDC/Polling + Enrichment Export'],
            'dual_write_db_broker':['Event-driven + Transactional Outbox','Event Choreography','Backward-compatible Extension with Events'],
            'saga_orchestration':['Fan-out/Fan-in Orchestrated Process','Orchestrated E2E Process'],
            'financial_state_machine':['Financial Operation State Machine'],
            'async_job_flow':['Async Job / Heavy Processing Flow'],
            'near_real_time_decision':['Near Real-time Decision Flow','Event Choreography'],
            'strangler_migration':['Migration / Strangler Fig','SOAP Legacy Adapter Integration'],
            'bff_api_composition':['BFF/API Composition with Partial Response','Fast Read / Cached Read Model'],
            'read_model_cqrs':['Fast Read / Cached Read Model'],
            'dwh_pipeline':['Data Pipeline / DWH'],
            'batch_file_exchange':['Batch/File Integration'],
            'regulatory_schema_change':['Regulatory Data Model Change Impact Analysis','Backward-compatible Extension with Events','Data Synchronization / Source-of-Truth Sync','Migration / Strangler Fig'],
            'shared_topic_selective_consumer':['Shared Topic Selective Consumer + Idempotent Sink'],
            'external_partner_adapter':['External API Adapter with Resilience','Queue-based Worker Flow'],
            'basic_sync_api':['Basic API + DB','External API Adapter with Resilience']
        }
        layer_only={'Fast Read / Cached Read Model','Data Pipeline / DWH','External API Adapter with Resilience','SOAP Legacy Adapter Integration','Reference Data API + Versioned Cache','BFF/API Composition with Partial Response','Webhook Intake + Inbox Processing'}
        allowed=set(top_by_class.get(primary,[]))
        for v in variants:
            v['case_class_role']='candidate_top_level' if v['name'] in allowed else 'supporting_layer_or_alternative'
            v['case_class_reason']=case_classes[0].get('why')
            if v['name'] in allowed:
                v['_priority']=v.get('_priority',0)+160
                v['score']=min(100,v.get('score',0)+8)
                v.setdefault('why',[]).append('Выбранный класс кейса требует именно этот top-level каркас: '+case_classes[0].get('title',''))
            elif primary in ['dual_write_db_broker','saga_orchestration','data_enrichment_pipeline','webhook_intake','non_invasive_extension','batch_file_exchange','strangler_migration','privacy_erasure_pipeline','cdc_legacy_modernization','near_real_time_decision'] and v['name'] in layer_only:
                v['_priority']=v.get('_priority',0)-140
                v['score']=min(v.get('score',0),68)
                v.setdefault('risks',[]).append('Это полезный внутренний слой, но не главный архитектурный каркас для класса кейса '+primary+'.')
        sorted_variants=sorted(variants,key=lambda x:(x.get('_priority',0),x.get('score',0)),reverse=True)
        if primary=='saga_orchestration':
            idx=next((i for i,v in enumerate(sorted_variants) if v.get('name')=='Compromise: Source Outbox + Embedded/Platform Publisher'),None)
            if idx is not None and idx>3:
                item=sorted_variants.pop(idx)
                sorted_variants.insert(min(3,len(sorted_variants)), item)
        return sorted_variants

    def architecture_roles(self,rec,patterns,case_classes):
        pids=set(rec.get('pattern_ids',[]))
        layers=[]
        controls=[]
        if case_classes:
            top_controls = case_classes[0].get('required_controls',[])
            layers.append({'name':'Top-level architecture','purpose':case_classes[0].get('top_level') or rec.get('name'),'controls':top_controls})
            controls += top_controls
        mapping=[
            ('outbox','Transactional Outbox','Атомарная фиксация бизнес-изменения и pending-события'),('integration_publisher','Integration Publisher','Обогащение/публикация после commit без переноса ownership'),('inbox','Inbox / idempotent consumer','Дедупликация входящих событий и безопасный retry'),('kafka','Event stream','Fan-out, replay, асинхронная доставка'),('selective_consumer','Selective Kafka consumer','Фильтрация общего topic, контроль lag/filter ratio и безопасная запись в sink'),('queue','Worker queue','Backpressure, retry, тяжёлая обработка'),('saga','Process state machine','Статусы, компенсации, manual recovery'),('read_model_business','Read model','Быстрое чтение/клиентский статус'),('cache','Cache','Ускорение чтения с TTL/freshness policy'),('cdc','CDC','Read-only/near-real-time extraction'),('etl','ETL/ELT','DWH/аналитика, lineage/reconciliation'),('webhook','Webhook edge','Проверка подписи, быстрый ACK'),('file','Batch/File exchange','Manifest, checksum, staging/quarantine, ack/error files'),('fallback','Resilience/fallback','Timeout, circuit breaker, degradation'),('privacy','Privacy controls','Legal hold, erasure evidence, audit')]
        for pid,name,purpose in mapping:
            if pid in pids:
                layers.append({'name':name,'purpose':purpose,'controls':[]})
        for p in patterns:
            if p.get('id') in pids:
                controls += p.get('controls',[])[:4]
        seen=[]
        for x in controls:
            if x not in seen: seen.append(x)
        return {'top_level':rec.get('name'),'layers':layers,'required_controls':seen[:24]}

    def production_gate(self,f,c,t,anti,rec,case_classes):
        critical=[a for a in anti if a.get('severity')=='critical']
        high=[a for a in anti if a.get('severity')=='high']
        blockers=[]
        if critical: blockers += [a['title'] for a in critical[:6]]
        if high and (t.get('direct_money_impact') or t.get('regulatory_impact')): blockers += [a['title'] for a in high[:4]]
        if 'webhook_intake' in [x['id'] for x in case_classes] and (f.get('webhook_signature_required')!='yes' or f.get('webhook_raw_body_preserved')!='yes'):
            blockers.append('Webhook security не подтверждён: signature/raw body должны быть yes для production.')
        if case_classes and case_classes[0]['id']=='shared_topic_selective_consumer':
            if 'selective_consumer' not in rec.get('pattern_ids',[]): blockers.append('Shared-topic кейс выбран без selective-consumer каркаса.')
            if f.get('delivery') in ['best_effort'] and t.get('highload'): blockers.append('Highload selective consumer без at-least-once/idempotent sink режима.')
            if f.get('replay')=='no': blockers.append('Shared-topic selective consumer без replay/reprocess policy.')
        if t.get('active_active_financial_write'):
            blockers.append('Active-active финансовая запись: нужен single-writer/ledger/consensus/reconciliation до разработки.')
        if t.get('multi_tenant_noisy_neighbor') and not any('tenant' in str(x).lower() for x in (case_classes[0].get('required_controls',[]) if case_classes else [])):
            blockers.append('Multi-tenant noisy-neighbor риск: нужна стратегия изоляции tenants и lag per tenant.')
        if t.get('event_needed') and 'outbox' not in rec.get('pattern_ids',[]) and case_classes and case_classes[0]['id'] in ['dual_write_db_broker','data_enrichment_pipeline']:
            blockers.append('Event-driven case без Outbox/CDC safety contour.')
        if t.get('chain') and not c.get('statuses') and case_classes and case_classes[0]['id']=='saga_orchestration':
            blockers.append('Saga/E2E без бизнес-статусов и истории статусов.')
        if not blockers and high:
            blockers += [a['title'] for a in high[:4]]
        if not blockers and rec.get('score',0)<70:
            blockers.append('Низкая оценка выбранного варианта: требуется архитектурное ревью и уточнение требований.')
        if blockers:
            webhook_security_blocker = any('Webhook security' in b for b in blockers) and (t.get('direct_money_impact') or f.get('sensitivity')=='financial' or f.get('security_boundary')=='external')
            level='RED' if critical or len(blockers)>=2 or webhook_security_blocker else ('YELLOW' if high or rec.get('score',0)<70 else 'AMBER')
        else:
            level='GREEN'
        text={
            'RED':'Нельзя отдавать в разработку как production-решение: есть блокирующие риски.',
            'AMBER':'Можно делать spike/предпроект, но не production-разработку без закрытия блокеров.',
            'YELLOW':'Можно идти в MVP/разработку только с зафиксированными рисками и архитектурным ревью.',
            'GREEN':'Можно отдавать в разработку после обычного ревью и фиксации ADR.'
        }[level]
        return {'level':level,'text':text,'blocking_gaps':blockers,'required_before_dev':blockers[:8] or ['Зафиксировать ADR, владельцев, SLA, error matrix и тесты.'],'required_before_prod':['SLO/alerts/runbook','load test','replay/recovery drill','contract tests','security review','rollback plan']}

    def structured_result(self,f,c,t,rec,patterns,anti,case_classes,gate,advanced,life):
        roles=self.architecture_roles(rec,patterns,case_classes)
        return {
            'case_class':case_classes[0]['id'] if case_classes else 'unknown',
            'case_classes':case_classes,
            'gate':gate,
            'top_level_architecture':roles['top_level'],
            'internal_layers':roles['layers'],
            'required_controls':roles['required_controls'],
            'anti_patterns':anti,
            'mvp_scope':(advanced or {}).get('mvp',[]),
            'production_scope':(advanced or {}).get('production',[]),
            'acceptance_criteria':(life or {}).get('acceptance',[]),
            'test_scenarios':(life or {}).get('tests',[]),
            'adr':(advanced or {}).get('adr',{})
        }

    def anti_patterns(self,f,c,t,pats,rec):
        a=[]
        def add(id,title,severity,why,fix): a.append({'id':id,'title':title,'severity':severity,'why':why,'fix':fix})
        iq=c.get('input_quality',{})
        for i,gap in enumerate(iq.get('hard_gaps',[]),1):
            add(f'input_blocker_{i}','Недостаточно данных для проектирования','critical',gap,'Заполнить минимум входных данных до выбора архитектуры.')
        for i,conflict in enumerate(c.get('business',{}).get('conflicts',[]),1):
            add(f'business_conflict_{i}','Конфликт бизнес-требований','high',conflict,'Согласовать компромисс: скорость vs актуальность vs доступность; зафиксировать в ADR.')
        explicit_compromise = (
            f.get('constraint_profile') in ['pragmatic','minimal_safe']
            or f.get('budget_pressure') in ['high','extreme']
            or f.get('deadline_pressure') in ['tight','urgent']
            or f.get('new_service_policy') in ['reuse_existing_runtime','platform_only','forbidden']
            or f.get('new_infra_policy') == 'forbidden'
            or f.get('source_change_policy') in ['api_only','read_only','forbidden']
        )
        if explicit_compromise and not str(f.get('compromise_comment','')).strip():
            add('compromise_without_rationale','Компромиссный режим без явного обоснования','medium','Выбраны ограничения по бюджету/срокам/стеку, но не описано, почему нельзя целевое решение.','Заполнить поле “Ограничения/компромиссы словами” и зафиксировать это в ADR как trade-off.')
        if t.get('new_service_forbidden') and 'integration_publisher' in rec.get('pattern_ids',[]) and not rec.get('name','').startswith('Compromise'):
            add('new_service_forbidden_but_required','Решение требует нового publisher-сервиса, но новый сервис ограничен','high','Целевой паттерн может быть слишком дорогим/невозможным в текущем стеке.','Выбрать compromise-реализацию: embedded job в существующем runtime, платформенный adapter или поэтапный rollout с временным риском.')
        if t.get('source_read_only') and t.get('enrichment_required') and t.get('event_needed'):
            add('source_read_only_enriched_event_risk','Source нельзя менять, но нужно enriched event','critical','Без source-owned outbox/CDC невозможно получить такую же гарантию, как при атомарной фиксации факта изменения и события.','Либо согласовать минимальный outbox/CDC в source, либо честно оформить snapshot/export с reconciliation и residual risk.')
        if t.get('new_infra_forbidden') and f.get('kafka_topology')!='no_kafka' and 'kafka' not in f.get('existing_capabilities',[]) and 'kafka' in rec.get('pattern_ids',[]):
            add('new_infra_forbidden_but_kafka_needed','Нужна Kafka/очередь, но новая инфраструктура запрещена','high','Архитектура зависит от инфраструктуры, которой нельзя добавить.','Использовать существующий Kafka-контур, платформенный publisher, batch/file fallback или пересогласовать ограничение как blocker.')
        if t.get('direct_money_impact') and (t.get('stale_allowed') or 'cache' in rec.get('pattern_ids',[])):
            add('money_cache_final_decision_forbidden','Деньги + кэш/устаревание','medium','Кэш или устаревшая read-model недопустимы для финального финансового решения.','Разрешить кэш только для read-only статуса/справочника с last_updated; финальное решение читать из transactional operation/source of truth.')
        if t.get('regulatory_impact') and not t.get('strict_freshness'):
            add('regulatory_freshness_not_fixed','Регуляторный процесс без строгой фиксации свежести','high','Для юридически значимого процесса нужно явно зафиксировать допустимый возраст данных и источник правды.','Добавить ADR: freshness SLA, lineage, audit, reconciliation, кто отвечает за устаревшие данные.')
        status_like = f.get('result_model') in ['tracking','notification','callback'] or 'status' in (str(f.get('business_goal',''))+' '+str(f.get('user_action',''))).lower()
        if t.get('customer_visible') and status_like and not c.get('statuses'):
            add('customer_visible_without_status_model','Клиентский процесс без статусов','high','Клиент увидит неопределённое состояние, поддержка получит ручные обращения.','Добавить business statuses, status history, last_updated, owner каждого технического статуса.')
        event_requested = (not t.get('file_needed')) and ('one_source_many_consumers' in t.get('business_situations',set()) or 'highload_write_stream' in t.get('business_situations',set()) or f.get('event_payload_intent') in ['enriched_event','snapshot_export'] or 'add_event' in f.get('change_policy',[]))
        broker_forbidden = ('kafka' in f.get('forbidden_channels',[]) or 'async' in f.get('forbidden_channels',[]) or f.get('kafka_topology')=='no_kafka') and not any(ch in f.get('allowed_channels',[]) for ch in ['kafka','queue'])
        if event_requested and broker_forbidden:
            add('event_target_but_broker_forbidden','Требуется событийная доставка, но broker/queue запрещены формой','critical','Пользователь выбрал сценарий с событиями/потребителями, но одновременно запретил Kafka/очередь. Такое решение нельзя считать спроектированным.','Либо разрешить Kafka/queue/existing broker, либо сменить целевую модель на REST polling/file export и зафиксировать потерю event semantics в ADR.')
        direct_db_explicit = 'direct_db_write' in f.get('allowed_channels',[]) or any('direct db write' in str(x).lower() or 'прямая запись' in str(x).lower() for x in [f.get('business_goal',''), f.get('current_solution_description',''), f.get('systems_matrix',''), f.get('process_steps','')])
        direct_db_guard_relevant = t.get('operation_kind') not in {'query_readonly','bff_composition','dwh_offload','batch_file_exchange','regulatory_schema_change'} and not t.get('shared_topic_selective')
        if direct_db_explicit:
            add('direct_db_write','Прямая запись в чужую БД явно присутствует','high','Ломает ownership/source of truth и делает интеграцию хрупкой.','Убрать direct DB write: использовать API/event/outbox/CDC/adapter или явно доказать, что это собственная projection/sink БД.')
        elif direct_db_guard_relevant and 'direct_db_write' not in f.get('forbidden_channels',[]):
            add('direct_db_write_policy_not_fixed','Не зафиксирован запрет прямой записи в чужую БД','medium','Для интеграции с чужими системами важно явно закрыть обход ownership через БД.','В форме отметить запрет direct_db_write; исключение — только собственная projection/sink БД с отдельным owner.')
        if t['global_order']: add('global_order','Глобальный порядок сообщений','high','Дорогой и редко оправдан.','Проверить, достаточно ли порядка по entityId/aggregateId.')
        if t['unknown_orchestration']: add('unknown_orchestration','Не выбран способ управления цепочкой','critical','Нельзя корректно спроектировать recovery и owner процесса.','Выбрать orchestrator/choreography/hybrid/BPM.')
        bff_partial_context = (('multi_source_aggregation' in t.get('business_situations',set()) or 'many_sources_one_consumer' in t.get('business_situations',set())) and t.get('partial_response_ok'))
        if t['chain'] and t['sync'] and t['blocking_chain_len']>=3:
            if bff_partial_context:
                add('sync_chain_bff_partial','BFF fan-out требует timeout/degradation budget','medium','Для BFF/API Composition fan-out не является blocker сам по себе, если есть timeout per source, partial response, freshness markers, circuit breaker/bulkhead и tracing.','Зафиксировать timeout budget, per-block fallback, partial schema, freshness markers, circuit breaker/bulkhead и correlationId.')
            else:
                add('sync_chain','Синхронная цепочка из нескольких блокирующих систем','critical','Риск каскадных timeout и плохой доступности.','Сделать async acceptance + status tracking/queue/orchestrator.')
        if t['saga']:
            bad=[]
            for s in c['steps']:
                if s.get('blocking')=='blocking' and s.get('order') not in ['1',''] and s.get('compensation','').lower() in ['','none','нет']:
                    bad.append(s.get('step'))
            if bad: add('saga_no_compensation','Saga без компенсаций на блокирующих шагах','critical','Сбой оставит процесс в неопределённом состоянии.','Описать compensation/manual recovery для: '+', '.join(bad))
        reliability_key_aliases={
            'idempotencykey','idempotency_key','requestid','request_id','eventid','event_id',
            'externaleventid','external_event_id','providereventid','provider_event_id','stripeeventid','stripe_event_id',
            'webhookeventid','webhook_event_id','callbackid','callback_id','deliveryid','delivery_id','messageid','message_id',
            'operationid','operation_id','sourceoperationid','source_operation_id','batchid','batch_id','fileid','file_id',
            'checksum','watermark','offset','snapshotid','snapshot_id','migrationrunid','migration_run_id',
            'schemaversion','schema_version','sourceeventid','source_event_id','aggregateversion','aggregate_version',
            'correlationid','correlation_id','commandid','command_id'
        }
        reliability_names={str(x.get('name','')).lower() for x in c['fields'] if x.get('unique') or str(x.get('name','')).lower() in reliability_key_aliases}
        has_reliability_key=any(('idempotency' in n or n in reliability_key_aliases) for n in reliability_names)
        read_only_kinds={'query_readonly','bff_composition'}
        watermark_kinds={'dwh_offload','migration','regulatory_schema_change','batch_file_exchange'}
        strict_key_kinds={'financial_command','command_create_update','webhook_event_intake','kafka_event_consumer','kafka_event_publisher'}
        if t['dedupe'] and not has_reliability_key and t.get('operation_kind') in strict_key_kinds:
            add('no_idempotency','Нет контекстного ключа надёжности для '+t.get('operation_kind','flow'),'critical','Повторы/ретраи могут создать дубли или потерять связь с исходным фактом.','Добавить: '+t.get('reliability_key', required_reliability_key(t.get('operation_kind','')))+'.')
        if t['dedupe'] and not has_reliability_key and t.get('operation_kind') in watermark_kinds:
            add('no_context_reliability_key','Нет watermark/batch/migration ключа для '+t.get('operation_kind','flow'),'medium','Для batch/DWH/migration нужен не generic Idempotency-Key, а ключ запуска/среза/offset и сверка.','Добавить: '+t.get('reliability_key', required_reliability_key(t.get('operation_kind','')))+'.')
        if t.get('shared_topic_selective'):
            if f.get('kafka_topology')!='single_topic_only': add('shared_topic_topology_unclear','Shared-topic кейс без явной single_topic_only топологии','medium','Для фильтрации общего topic нужно явно зафиксировать, что отдельный topic недоступен/не выбран.','Указать kafka_topology=single_topic_only или согласовать отдельный topic как target-вариант.')
            if 'new_topic_forbidden' not in f.get('forbidden_channels',[]): add('shared_topic_no_constraint','Не зафиксирован запрет отдельного topic','medium','Если отдельный topic возможен, архитектурно лучше route/filter на стороне producer или выделенный topic.','Зафиксировать constraint или сравнить target-вариант с отдельным topic.')
            if f.get('delivery')=='best_effort': add('selective_consumer_best_effort','Selective consumer в best-effort режиме','high','При сбое consumer/DB можно потерять accepted события или получить неуправляемые дубли.','Использовать at_least_once + idempotent sink + offset commit after successful processing + DLQ/quarantine.')
        if t.get('event_owner_conflict'):
            add('event_ownership_vs_kafka_infra','Ownership события смешан с наличием Kafka-инфраструктуры','high','Сервис с частью данных и Kafka не должен публиковать ContractUpdated/EntityUpdated как владелец факта изменения, если он не владеет сущностью.','Оставить business owner у source-сервиса; добавить outbox/integration table и внешний technical publisher/adapter. Если публикует сервис обогащения, назвать событие SnapshotPrepared/ExportReady и сослаться на sourceEventId.')
        if t.get('rest_enrichment') and t.get('enrichment_required') and t.get('event_needed') and 'outbox' not in rec.get('pattern_ids',[]) and 'cdc' not in rec.get('pattern_ids',[]):
            add('required_rest_enrichment_without_outbox','Обязательное REST-обогащение перед Kafka без Outbox/CDC safety contour','critical','При падении enrichment REST можно потерять или навсегда задержать событие без управляемого retry/reprocess.','Добавить pending outbox/integration table со статусами NEW/ENRICHING/PUBLISHED/FAILED либо CDC/polling export с watermark/reconciliation и явным residual risk.')
        if t.get('rest_enrichment') and t.get('enrichment_required') and t.get('event_needed') and t.get('existing') and not t.get('can_add_outbox') and not t.get('can_add_cdc'):
            add('enrichment_requires_change_but_outbox_not_allowed','Enrichment перед Kafka требует Outbox/CDC, но изменение source не разрешено','critical','Без outbox/integration table или CDC невозможно надёжно связать факт изменения договора, REST enrichment и Kafka publish.','Согласовать минимальное изменение source: outbox/integration table; если нельзя — использовать CDC/polling с явным риском или изменить требование к событию.')
        if t.get('enrichment_needed') and f.get('enrichment_consistency')=='unknown':
            add('enrichment_consistency_not_defined','Не определена свежесть enrichment-данных','high','Непонятно, должны ли дополнительные данные соответствовать моменту изменения сущности или моменту публикации события.','Зафиксировать AS_OF_CHANGE / CURRENT_AT_PUBLISH / BEST_EFFORT; для критичных данных нужен snapshot или versioned API.')
        if t.get('enrichment_critical') and f.get('enrichment_consistency')=='best_effort':
            add('critical_enrichment_best_effort','Критичное enrichment как best-effort','critical','Для юридически/финансово значимых данных best-effort может исказить смысл события.','Использовать локальный snapshot, versioned REST API или as-of-time contract.')
        if t.get('enrichment_critical') and f.get('enrichment_consistency')=='current_at_publish':
            field_names_lower={str(x.get('name','')).lower() for x in c.get('fields',[])}
            has_snapshot_markers=bool(field_names_lower & {'dataasof','data_as_of','dataversion','data_version','sourceeventid','source_event_id','updatedat','updated_at','aggregateversion','aggregate_version'})
            if f.get('event_payload_intent') in ['snapshot_export','thin_event'] and has_snapshot_markers:
                add('critical_enrichment_current_at_publish','Критичное enrichment как current-at-publish','high','Для snapshot/export/thin-event это допустимый компромисс, если контракт явно содержит marker свежести и sourceEventId/version, но риск рассинхрона всё равно нужно зафиксировать.','Оставить dataAsOf/dataVersion/sourceEventId/aggregateVersion в контракте, добавить reconciliation и правила reprocess.')
            else:
                add('critical_enrichment_current_at_publish','Критичное enrichment как current-at-publish','high','Current-at-publish допустим только если событие является snapshot/export/thin-event и содержит dataAsOf/dataVersion/sourceEventId.','Зафиксировать в контракте: это snapshot/export/thin-event, добавить dataAsOf/dataVersion/sourceEventId и reconciliation; иначе использовать as_of_change.')
        if t['no_changes'] and any(x in rec.get('pattern_ids',[]) for x in ['outbox','saga']): add('no_changes_conflict','Выбранный вариант требует изменения core flow','critical','Outbox/Saga требуют изменения контура.','Выбрать CDC/ETL/file/read-only adapter.')
        if t['dwh'] and any('dwh' in s.get('system','').lower() and s.get('blocking')=='blocking' for s in c['steps']): add('dwh_blocks','DWH блокирует клиентский процесс','high','Аналитика не должна ломать happy path.','Сделать DWH non-blocking через CDC/ETL/replay.')
        if t.get('active_active_financial_write'):
            add('active_active_financial_write','Active-active финансовая запись без доказанной стратегии консистентности','critical','При split-brain или параллельной записи по одному балансу возможны double-spend, потеря проводки или расхождение баланса.','До разработки зафиксировать single writer per account/shard или append-only ledger + consensus/conflict resolution, idempotency operationId, reconciliation и manual correction.')
        if t.get('multi_tenant_noisy_neighbor'):
            add('multi_tenant_noisy_neighbor','Multi-tenant noisy neighbor не изолирован','high','Один крупный tenant может забить общий consumer pool/partitions и создать lag/деградацию для остальных клиентов.','Добавить tenant quotas, partitioning by tenant/entity, отдельные consumer pools для крупных tenants, fair scheduling/backpressure и lag metrics per tenant.')
        if privacy_erasure_signal(f) and any(x in ' '.join(str(f.get(k,'')) for k in ['business_goal','user_action','compromise_comment','fields','process_steps','systems_matrix']).lower() for x in ['legal hold','retention exception','нельзя удалить','нельзя физически удалить','обязательное хранение']):
            add('privacy_legal_hold_exception','Privacy deletion пересекается с legal hold/retention exception','high','Не все данные можно физически удалить: часть должна быть удержана по юридическому основанию, но доступ и использование должны быть ограничены.','Разделить physical deletion, anonymization/pseudonymization и retention exception; вести реестр исключений, evidence per system и audit trail.')
        if t.get('highload_stream_ingestion'):
            if f.get('ordering')=='global': add('stream_global_order','Stream ingestion с глобальным порядком','critical','Глобальный порядок в telemetry/highload ломает throughput и создаёт bottleneck.','Использовать порядок по deviceId/entityId/tenantId, watermark/event_time и late-event policy.')
            if f.get('replay')=='no': add('stream_no_replay','Highload stream ingestion без replay/reprocess','high','Без replay нельзя восстановиться после bug, consumer lag, poison messages или поздних событий.','Добавить offset/watermark, replay window, DLQ/quarantine и reprocess runbook.')
        if t['highload']:
            if f['ordering']=='global': add('highload_global_order','Highload + глобальный порядок','critical','Глобальный порядок ограничивает throughput.','Партиционировать по aggregateId и сохранить порядок внутри ключа.')
            if f['latency_sla'] in ['subsecond','seconds'] and t['chain']: add('highload_low_latency_chain','Highload + низкая latency + цепочка','high','Сложно обеспечить без деградации.','Вернуть accepted/trackingId, обработку вынести async.')
        if t['sensitive'] and f['auth']=='none': add('no_auth_sensitive','Нет авторизации при чувствительных данных','critical','ИБ/юридический риск.','Определить auth, RBAC/ABAC, audit, masking.')
        webhook_like = ('webhook_callback' in t.get('business_situations',set())) or ('webhook' in ' '.join([x.get('channel','') for x in c.get('systems',[])+c.get('steps',[])]).lower())
        if webhook_like and (t.get('direct_money_impact') or t.get('sensitive') or f.get('security_boundary') in ['external','mixed']):
            field_names = {str(x.get('name','')).lower() for x in c.get('fields',[])}
            has_signature_field = any(('signature' in n or 'sig' == n or 'hmac' in n or 'rawbody' in n or 'raw_body' in n or 'timestamp' in n) for n in field_names)
            signature_ok = f.get('webhook_signature_required')=='yes' or has_signature_field
            raw_body_ok = f.get('webhook_raw_body_preserved')=='yes' or any(('rawbody' in n or 'raw_body' in n) for n in field_names)
            if not signature_ok or not raw_body_ok:
                add('webhook_signature_not_defined','Webhook без подтверждённой подписи/raw body','medium','Для внешнего webhook, особенно финансового, недостаточно dedupe: нужно доказать подлинность события и защититься от подмены payload.','Добавить явные поля формы webhook_signature_required=yes и webhook_raw_body_preserved=yes; проверять HMAC/signature header по raw body, timestamp tolerance, secret rotation и отказ 4xx при неверной подписи до записи в Inbox.')
            if f.get('webhook_timestamp_tolerance') in ['no','unknown']:
                add('webhook_replay_protection_not_defined','Webhook без timestamp tolerance/replay protection','medium','Даже подписанный payload можно повторно отправить в пределах уязвимого окна, если нет timestamp tolerance и dedupe.','Зафиксировать допустимое окно timestamp, eventId dedupe и политику provider retry.')
            if f.get('webhook_reconciliation_available') in ['no','unknown'] and (t.get('direct_money_impact') or f.get('money_impact')=='yes'):
                add('webhook_reconciliation_missing','Финансовый webhook без сверки с provider API','medium','Webhook может потеряться, прийти поздно или не по порядку; без reconciliation нельзя доказать итоговое состояние.','Добавить периодическую сверку по provider API/ledger и manual recovery для расхождений.')
        retention_relevant = (t['dwh'] or 'dwh_reporting' in t.get('business_situations',set()) or f.get('history') in ['events','snapshot','status_audit_attempts'] or f.get('replay') in ['yes','rebuild'] or privacy_erasure_signal(f))
        if t['large_data'] and retention_relevant and f['retention']=='not_defined':
            retention_scope = 'DWH/archive' if (t.get('operation_kind')=='dwh_offload' or t.get('dwh')) else ('outbox/inbox/DLQ/replay/audit' if (t.get('event_needed') or t.get('inbox_needed')) else 'history/audit')
            add('no_retention',f'Не задан retention для {retention_scope}','high','Без срока хранения и archive/partition policy служебные таблицы, история или аналитический контур будут расти бесконечно.','Задать срок хранения отдельно для business history, outbox/inbox, DLQ/quarantine, audit и DWH/archive; указать partition/archive job.')
        for s in c['systems']:
            if not s.get('owner'): add('no_system_owner','У системы не указан owner','medium',f'Нет владельца для {s.get("name")}.','Заполнить owner в матрице систем.')
        for s in c['steps']:
            if s.get('retry')=='yes' and not s.get('owner'): add('retry_no_owner','Retry/DLQ без владельца','high',f'Шаг {s.get("step")} требует owner для разбора.','Указать owner и after_retry policy.')
            if s.get('retry')=='yes' and not s.get('compensation'): add('retry_no_after','Retry без after-retry/compensation','high',f'Шаг {s.get("step")} не описывает финальное действие.','Описать DLQ/manual/compensation/reject.')
        step_orders=[x.get('order') for x in c['steps'] if x.get('order')]
        if len(step_orders)!=len(set(step_orders)): add('duplicate_step_order','Дублируются номера шагов','high','Невозможно однозначно построить последовательность процесса.','Сделать order уникальным либо добавить отдельный branchId.')
        known=set(step_orders)|{'root',''}
        for st in c['steps']:
            for parent in [p.strip() for p in st.get('parent','').split(',') if p.strip()]:
                if parent not in known:
                    add('broken_parent_reference','Некорректная ссылка на parent step','high',f'Шаг {st.get("step")} ссылается на parent={parent}, которого нет.','Исправить parent в матрице шагов; для корня использовать root.')
        if f['chain_depth']=='fanout_fanin' and not any(',' in x.get('parent','') for x in c['steps']):
            add('fanout_without_join','Fan-out/Fan-in без явного join-шага','medium','Указан fan-out/fan-in, но в шагах нет агрегации нескольких parent.','Добавить join/aggregation step с parent вида 2,3 или описать partial success policy.')
        if t['event_needed'] and not any(p['id'] in ['kafka','queue'] for p in pats): add('event_without_broker','Нужны события/очереди, но broker/queue не выбран','high','Событийный сценарий не обеспечен инфраструктурой.','Разрешить Kafka/event broker/queue или изменить channel.')
        return a

    def database(self,f,c,t,rec):
        pids=set(rec.get('pattern_ids',[])); ent=snake(f['main_entity']); tables=[]
        target_only=t['no_changes'] and t['existing'] and rec['name'].startswith('Non-invasive')
        base=[]
        reserved={'status':'text not null','version':'integer not null default 1','correlation_id':'text','created_at':'timestamp not null default now()','updated_at':'timestamp not null default now()','archived_at':'timestamp'}
        def add_field(name, spec):
            if not name: return
            if name in [x[0] for x in base]: return
            base.append((name, spec))
        add_field('id','uuid primary key')
        for fld in c['fields']:
            name=fld['name']
            if name=='id':
                continue
            if name in reserved:
                # Системные поля ниже добавляются единообразно, чтобы в DDL не было дублей.
                continue
            add_field(name,fld['type']+(' not null' if fld['required'] else ''))
        if t['dedupe'] and 'idempotency_key' not in [x[0] for x in base] and not target_only:
            add_field('idempotency_key','text')
        for name,spec in reserved.items():
            add_field(name,spec)
        idx=['(status)','(created_at)','(correlation_id)']+[f"({x['name']})" for x in c['fields'] if x['indexed']]+[f"unique({x['name']})" for x in c['fields'] if x['unique']]
        if t['dedupe'] and not target_only: idx.append('unique(idempotency_key) where idempotency_key is not null')
        purpose='Основная бизнес-сущность' if not target_only else 'Локальная read/projection copy, не меняет source system'
        tables.append({'name':ent,'purpose':purpose,'fields':base,'indexes':idx})
        if f['history']!='none' and not (target_only and f['history']=='status'):
            tables.append({'name':ent+'_status_history','purpose':'История статусов','fields':[('id','uuid primary key'),(ent+'_id','uuid not null'),('old_status','text'),('new_status','text not null'),('reason','text'),('changed_by','text'),('changed_at','timestamp not null default now()')],'indexes':[f'({ent}_id, changed_at)','(new_status, changed_at)']})
        if f['history'] in ['audit','status_audit','status_audit_attempts','event_sourcing'] or t['regulated']:
            tables.append({'name':'audit_log','purpose':'Аудит и security-события','fields':[('id','uuid primary key'),('correlation_id','text'),('actor','text'),('action','text not null'),('entity_type','text'),('entity_id','text'),('result','text'),('metadata','jsonb'),('created_at','timestamp not null default now()')],'indexes':['(correlation_id)','(entity_type, entity_id)','(created_at)']})
        if ('saga' in pids or 'bpm' in pids) and not target_only:
            tables.append({'name':'process_steps','purpose':'Состояние каждого шага многоуровневого процесса','fields':[('id','uuid primary key'),('process_id','uuid not null'),('entity_id','uuid not null'),('level','integer not null default 0'),('parent_step_id','uuid'),('step_order','integer not null'),('step_name','text not null'),('target_system','text'),('status','text not null'),('blocking','boolean not null default true'),('owner','text'),('started_at','timestamp'),('finished_at','timestamp'),('last_error','text')],'indexes':['(process_id, level, step_order)','(parent_step_id)','(entity_id)','(status)','(target_system, status)']})
            tables.append({'name':'integration_attempts','purpose':'Попытки вызовов внешних систем, retry, DLQ и диагностика','fields':[('id','uuid primary key'),('step_id','uuid'),('entity_id','uuid not null'),('target_system','text not null'),('operation','text not null'),('request_payload','jsonb'),('response_payload','jsonb'),('status','text not null'),('attempt_number','integer not null default 1'),('next_retry_at','timestamp'),('last_error_code','text'),('last_error_message','text'),('created_at','timestamp not null default now()'),('updated_at','timestamp not null default now()')],'indexes':['(entity_id)','(target_system, status)','(next_retry_at)','(created_at)']})
            tables.append({'name':'manual_recovery_tasks','purpose':'Задачи ручного разбора после исчерпания retry/compensation','fields':[('id','uuid primary key'),('entity_id','uuid not null'),('step_id','uuid'),('owner','text not null'),('reason','text not null'),('status','text not null'),('created_at','timestamp not null default now()'),('resolved_at','timestamp')],'indexes':['(owner,status)','(entity_id)','(created_at)']})
        if 'outbox' in pids and not target_only:
            outbox_fields=[('id','uuid primary key'),('aggregate_type','text not null'),('aggregate_id','uuid not null'),('aggregate_version','integer'),('event_type','text not null'),('event_version','integer not null default 1'),('payload','jsonb not null'),('status','text not null default \'NEW\''),('retry_count','integer not null default 0'),('next_retry_at','timestamp'),('last_error','text'),('correlation_id','text'),('created_at','timestamp not null default now()'),('sent_at','timestamp')]
            if t.get('enrichment_needed'):
                outbox_fields += [('enrichment_status','text not null default \'NOT_REQUIRED\''),('enrichment_consistency','text'),('source_event_id','uuid'),('enriched_payload','jsonb')]
            tables.append({'name':'outbox_events','purpose':'Надёжная публикация событий после commit; при enrichment хранит pending-событие до успешного обогащения','fields':outbox_fields,'indexes':['(status, created_at)','(aggregate_id, aggregate_version)','(event_type, created_at)','(next_retry_at)']})
        if 'integration_publisher' in pids and not target_only:
            tables.append({'name':'event_enrichment_attempts','purpose':'Попытки REST-обогащения перед публикацией события в Kafka','fields':[('id','uuid primary key'),('outbox_event_id','uuid not null'),('aggregate_id','uuid not null'),('aggregate_version','integer'),('enrichment_service','text not null'),('request_payload','jsonb'),('response_payload','jsonb'),('status','text not null'),('attempt_number','integer not null default 1'),('started_at','timestamp not null default now()'),('finished_at','timestamp'),('next_retry_at','timestamp'),('last_error_code','text'),('last_error_message','text')],'indexes':['(outbox_event_id)','(aggregate_id, aggregate_version)','(status, next_retry_at)','(enrichment_service, started_at)']})
        if 'inbox' in pids:
            tables.append({'name':'inbox_messages','purpose':'Дедупликация входящих сообщений','fields':[('message_id','text not null'),('consumer_name','text not null'),('payload_hash','text'),('status','text not null'),('processed_at','timestamp not null default now()'),('primary key','(message_id, consumer_name)')],'indexes':['(processed_at)','(status)']})
        if 'file' in pids:
            tables.append({'name':'file_registry','purpose':'Учёт файлов, checksum, quarantine, reprocessing','fields':[('file_id','text primary key'),('file_name','text not null'),('schema_version','text'),('checksum','text not null'),('status','text not null'),('records_total','integer'),('records_success','integer'),('records_failed','integer'),('received_at','timestamp not null default now()'),('processed_at','timestamp')],'indexes':['unique(checksum)','(status, received_at)']})
        if 'etl' in pids or 'cdc' in pids or t['dwh']:
            tables.append({'name':'reconciliation_runs','purpose':'Сверка batch/CDC/DWH загрузок','fields':[('id','uuid primary key'),('source_name','text not null'),('target_name','text not null'),('load_id','text'),('records_source','integer'),('records_target','integer'),('checksum_source','text'),('checksum_target','text'),('status','text not null'),('created_at','timestamp not null default now()')],'indexes':['(source_name,target_name,created_at)','(status)']})
        if 'event_sourcing' in pids:
            tables.append({'name':'event_store','purpose':'Неизменяемый журнал доменных событий','fields':[('event_id','uuid primary key'),('aggregate_id','uuid not null'),('aggregate_type','text not null'),('event_type','text not null'),('event_version','integer not null'),('sequence_number','bigint not null'),('payload','jsonb not null'),('metadata','jsonb'),('occurred_at','timestamp not null default now()')],'indexes':['unique(aggregate_id, sequence_number)','(event_type, occurred_at)','(occurred_at)']})
        return {'storage':self.storage(f,t,pids),'tables':tables,'ddl':self.ddl(tables,t,c),'partitioning':self.partitioning(t),'retention':[f"Retention: {f['retention']}.",'Outbox/inbox/integration_attempts имеют отдельный retention.','Audit/security срок согласовать с ИБ/юристами.'],'target_only':target_only}

    def storage(self,f,t,pids):
        s=['PostgreSQL OLTP']
        if t['highload']: s+=['Read replicas where needed','Connection pooling','Partitioned hot tables']
        if 'kafka' in pids: s.append('Kafka/Брокер событий')
        if 'queue' in pids: s.append('Queue for workers/retry')
        if 'integration_publisher' in pids: s.append('Integration Publisher / enrichment attempt storage')
        if t['dwh']: s.append('DWH/Data Lake')
        if t['large_data']: s.append('Archive/Object storage for cold data')
        return s
    def partitioning(self,t):
        if t['very_large'] or t['highload']: return ['Partition audit/history/outbox/inbox/integration_attempts/event_enrichment_attempts by created_at.','Use aggregateId/entityId as Kafka partition key.','Capacity plan: broker partitions, DB indexes, connection pools, worker concurrency.']
        if t['large_data']: return ['Consider monthly partitions for audit/history/integration_attempts.','Prepare archive jobs before production.']
        return ['Partitioning can be postponed but growth strategy must exist.']
    def ddl(self,tables,t,c):
        lines=['-- Draft SQL DDL. Требует DBA/security review.','-- Статусы: '+', '.join(c.get('statuses',[])),'']
        for tab in tables:
            lines += [f"-- {tab['purpose']}",f"create table {tab['name']} ("]
            fs=[]
            for name,spec in tab['fields']: fs.append(f"    primary key {spec}" if name=='primary key' else f"    {name} {spec}")
            lines.append(',\n'.join(fs)); lines.append(');')
            for i,idx in enumerate(tab.get('indexes',[]),1):
                if idx.startswith('unique(') and ' where ' not in idx: lines.append(f"create unique index ux_{tab['name']}_{i} on {tab['name']}({idx[7:-1]});")
                elif idx.startswith('unique') and ' where ' in idx:
                    cols=idx.split(' where ')[0].replace('unique','').strip(); where=idx.split(' where ')[1]
                    lines.append(f"create unique index ux_{tab['name']}_{i} on {tab['name']}{cols} where {where};")
                else: lines.append(f"create index idx_{tab['name']}_{i} on {tab['name']}{idx};")
            lines.append('')
        if t['highload']: lines.append('-- Highload: validate indexes with EXPLAIN, avoid unbounded scans, tune pool sizes and batch sizes.')
        return '\n'.join(lines)

    def contracts(self,f,c,t,rec):
        pids=set(rec.get('pattern_ids',[])); ent=snake(f['main_entity'])
        con={'api':[],'events':[],'queue':[],'selective_consumer':[],'enrichment':[],'files':[],'cdc':[],'dwh':[],'soap':[],'security':[],'privacy':[],'decision':[]}
        if 'rest' in pids or 'gateway' in pids:
            con['api']=[f'POST /api/v1/{ent} — создать/запустить процесс',f'GET /api/v1/{ent}/{{id}} — текущее состояние',f'GET /api/v1/{ent}/{{id}}/steps — состояние шагов',f'POST /api/v1/{ent}/{{id}}/retry — контролируемый retry','Headers: X-Request-Id, Correlation-Id, Idempotency-Key','Errors: validation_error, duplicate_request, conflict, rate_limited, technical_error','SLA/timeout/rate limit must be specified per endpoint']
        if 'kafka' in pids or 'outbox' in pids:
            con['events']=['Envelope: eventId,eventType,eventVersion,producer,occurredAt,publishedAt,correlationId,causationId,aggregateId,aggregateVersion','Partition key: aggregateId/entityId','Events: EntityCreated, EntityUpdated/EntityStatusChanged, ProcessStepCompleted, ProcessStepFailed','Schema evolution: backward-compatible by default','Consumer contract: idempotent, handles duplicates, handles out-of-order inside allowed window']
            if t.get('enrichment_needed'):
                con['events'] += ['For enriched events: sourceEventId/outboxEventId, enrichmentConsistency, enrichmentStatus, enrichmentGeneratedAt','If publisher is not source service: producer = integration-publisher, businessOwner/sourceSystem must identify source-of-truth service','For one Kafka topic: publish only final enriched payload or use honest event name EntitySnapshotPrepared/EntityExportReady']
        if 'integration_publisher' in pids:
            con['enrichment']=['REST enrichment contract: POST /internal/enrichment/resolve with aggregateId, aggregateVersion, sourceEventId, occurredAt, correlationId','Timeout, retry/backoff, circuit breaker and rate limit are mandatory','Response must include dataVersion or dataAsOf when available','Consistency rule must be fixed: AS_OF_CHANGE, CURRENT_AT_PUBLISH or BEST_EFFORT','On enrichment failure: outbox remains NEW/ENRICHING/FAILED, no silent drop; manual reprocess supported']
        if 'queue' in pids:
            con['queue']=['Message envelope: messageId,correlationId,attempt,createdAt,payload','Retry policy: max attempts + exponential backoff + jitter','DLQ policy: owner, SLA, replay rules','Visibility timeout greater than max processing time']
        if 'webhook' in pids or rec.get('name')=='Webhook Intake + Inbox Processing':
            con['security'] += ['Webhook signature header + rawBody must be preserved before parsing','Webhook timestamp tolerance / replay protection window','Webhook secret rotation and provider retry policy','Inbox key: provider_event_id/delivery_id + payload hash; reconciliation with provider API for money/regulated flows']
        if 'selective_consumer' in pids:
            con['selective_consumer']=['Input topic: shared topic name, partitions, retention, schema versions','Filter contract: field/key/header used for selection, accepted values, null/unknown policy','Metrics: consumed_total, filtered_out_total, accepted_total, filter_ratio, consumer_lag, db_write_latency, poison_count','Commit policy: commit offsets only after accepted event is safely written or intentionally skipped by deterministic filter','Sink contract: unique eventId/businessKey, upsert/insert policy, batch size, retry/DLQ/quarantine and replay window']
        if 'file' in pids:
            con['files']=['File naming: <producer>_<schemaVersion>_<timestamp>_<fileId>.csv/jsonl/xml','Manifest: fileId,schemaVersion,recordsCount,checksum,createdAt,producer','Encoding/delimiter/schema must be fixed','Error report: rowNumber,fieldName,errorCode,errorDescription','Duplicate policy: fileId + checksum','Partial success and reprocessing rules']
        if 'cdc' in pids:
            con['cdc']=['Source tables and columns whitelist','CDC contains operation,before/after,timestamp,source offset','Handle deletes, schema drift, duplicates and reordering','CDC is read-only integration, not command API','Operational CDC: LSN/watermark, gap detection, projection_version and replay plan']
        if rec.get('name')=='Privacy / Data Erasure Orchestration Pipeline' or t.get('operation_kind')=='privacy_erasure_pipeline':
            con['privacy']=['Identity validation and subject matching rules','Legal hold / retention exception decision before erase','Per-system erase command contract and timeout','Receipt/evidence registry per target system','Exception handling, re-drive and manual escalation','Audit trail for request, decision, command, receipt and final closure']
        if rec.get('name')=='Near Real-time Decision Flow' or t.get('operation_kind')=='near_real_time_decision':
            con['decision']=['decisionId/requestId/correlationId','feature_snapshot_id and feature freshness SLA','rules/model version used for decision','bounded latency budget per dependency','fallback decision policy','audit of input snapshot and final outcome']
        if 'etl' in pids or t['dwh']:
            con['dwh']=['Staging with load_id/batch_id/snapshot_id','Watermark/offset policy for incremental load','Data quality: record count, checksum, required fields, referential checks','Reconciliation report','Late arriving data and backfill policy','Retention/archive policy for prod offload and DWH storage growth','PII minimization/masking for analytics']
        if 'soap' in pids:
            con['soap']=['WSDL/XSD isolated in adapter','SOAP fault mapping to unified error model','Timeout + circuit breaker','Domain mapping layer']
        con['security']=['Auth scopes/roles per endpoint/topic/file/feed','Sensitive fields masked in logs','mTLS/TLS for service channels','Audit event for access/change'] + con.get('security',[])
        return con

    def scenarios(self,f,c,t,rec):
        pids=set(rec.get('pattern_ids',[])); main=[]
        if rec.get('blocked'):
            return {'main':['Проектирование заблокировано: нужно выбрать модель управления цепочкой.'],'alternatives':{},'error_path':['Заполнить orchestration и владельца процесса.'],'compensation_path':[]}
        main.append('Инициатор отправляет команду или событие старта.')
        if 'gateway' in pids: main.append('API Gateway применяет auth, rate limit, request validation.')
        if 'rest' in pids: main.append('API выполняет validation, idempotency check и возвращает result/trackingId.')
        main.append(f"{f['source_system']} сохраняет состояние {f['main_entity']}.")
        if 'outbox' in pids: main.append('В той же транзакции создаётся outbox event с aggregateId/aggregateVersion/sourceEventId.')
        if 'integration_publisher' in pids:
            main.append('Integration Publisher читает pending outbox после commit; business ownership события остаётся у source-сервиса.')
            if t.get('rest_enrichment'):
                main.append('Publisher вызывает REST-сервис обогащения с timeout/retry/circuit breaker и получает дополнительные данные.')
            main.append('После успешного enrichment publisher публикует финальное событие в Kafka; при одном topic raw-событие отдельно не публикуется.')
        if 'saga' in pids or 'bpm' in pids: main.append('Process Manager (управляющий процессом компонент) создаёт многоуровневую историю шагов и управляет переходами.')
        for s in c['steps']:
            level='  '*safe_int(s.get('level'),0); main.append(f"{level}Шаг {s.get('order')}: {s.get('step')} → {s.get('system')} через {s.get('channel')} ({s.get('blocking')}).")
        if 'selective_consumer' in pids:
            main.append('Consumer читает общий Kafka topic, применяет детерминированный фильтр по key/header/body и считает filtered/accepted ratio.')
            main.append('Ненужные события пропускаются без записи; нужные события пишутся в sink идемпотентно, после чего фиксируется offset.')
            main.append('Poison/invalid accepted events уходят в quarantine/DLQ с owner, alert и reprocess policy.')
        if 'kafka' in pids and 'selective_consumer' not in pids: main.append('Доменные/экспортные события публикуются в broker; подписчики обрабатывают их идемпотентно и проверяют aggregateVersion.')
        if 'etl' in pids or 'cdc' in pids: main.append('DWH/аналитика получает данные асинхронно и не блокирует клиентский процесс.')
        main.append('Финальный статус фиксируется в entity/status_history/audit_log.')
        alt={}
        for e in c['errors']:
            alt[e.get('error') or 'Ошибка']=[f"Где: {e.get('where')}",f"Блокирует: {e.get('blocking')}",f"Retry: {e.get('retry')}",f"После retry: {e.get('after_retry')}",f"Owner: {e.get('owner')}"]
        error_path=['Техническая ошибка фиксируется в integration_attempts/event_enrichment_attempts.','Если retry=yes — выполняется retry with exponential backoff + jitter.','При ошибке REST enrichment исходное изменение не откатывается; outbox остаётся в NEW/ENRICHING/FAILED до retry или ручного reprocess.','После исчерпания retry сообщение уходит в DLQ/FAILED или создаётся manual_recovery_task.','Алерт уходит владельцу шага и дежурной команде.']
        comp=['Process Manager определяет последний успешный блокирующий шаг.','Для каждого выполненного шага запускает compensation, если она указана.','Если compensation невозможна — создаёт manual recovery task и переводит процесс в технический статус.'] if 'saga' in pids else []
        return {'main':main,'alternatives':alt,'error_path':error_path,'compensation_path':comp}

    def diagrams(self,f,c,t,rec):
        pids=set(rec.get('pattern_ids',[])); src=f['source_system']
        comp=['flowchart LR','I[Initiator]']
        if 'gateway' in pids: comp+=['G[API Gateway]','I --> G',f'G --> S[{src}]']
        else: comp += [f'S[{src}]','I --> S']
        comp += ['S --> DB[(Primary DB)]']
        if 'saga' in pids or 'bpm' in pids: comp += ['S --> PM[Process Manager]','PM --> PS[(process_steps)]']
        if 'outbox' in pids: comp += ['DB --> O[Outbox]']
        if 'integration_publisher' in pids: comp += ['O --> IP[Integration Publisher]','IP --> ER[Enrichment REST Service]','ER --> IP']
        if 'kafka' in pids: comp += ['IP --> K[(Брокер событий)]' if 'integration_publisher' in pids else 'O --> K[(Брокер событий)]']
        if 'queue' in pids: comp += ['S --> Q[(Queue)]','Q --> W[Workers]']
        for i,sys in enumerate(c['systems'],1):
            node=f'T{i}[{sys.get("name")}]'; ch=sys.get('channel','')
            if 'kafka' in pids and ('event' in ch or 'kafka' in ch): comp.append(f'K --> {node}')
            elif 'queue' in pids and 'queue' in ch: comp.append(f'W --> {node}')
            elif 'etl' in pids and 'dwh' in sys.get('name','').lower(): comp.append(f'DB --> ETL[ETL/ELT] --> {node}')
            elif 'cdc' in pids and 'dwh' in sys.get('name','').lower(): comp.append(f'DB --> CDC[CDC] --> {node}')
            else: comp.append(f'S --> {node}')
        comp += ['S --> OBS[(Logs/Metrics/Traces/Audit)]']
        happy=['sequenceDiagram','participant I as Initiator']
        if 'gateway' in pids: happy.append('participant G as API Gateway')
        happy += [f'participant S as {src}','participant DB as Primary DB']
        if 'saga' in pids or 'bpm' in pids: happy.append('participant PM as Process Manager')
        if 'kafka' in pids: happy.append('participant K as Брокер событий')
        if 'queue' in pids: happy.append('participant Q as Queue')
        sys_map={}
        for i,sys in enumerate(c['systems'][:8],1):
            sys_map[sys.get('name')]=f'T{i}'
            happy.append(f'participant T{i} as {sys.get("name")}')
        happy += ['I->>S: command/request' if 'gateway' not in pids else 'I->>G: request\nG->>S: routed request','S->>S: auth + validation + idempotency','S->>DB: save entity/status']
        if 'outbox' in pids: happy.append('S->>DB: save outbox event in same transaction')
        happy.append('DB-->>S: commit ok')
        if 'saga' in pids or 'bpm' in pids:
            happy.append('S->>PM: start process')
            for i,s in enumerate(c['steps'][:8],1):
                target=sys_map.get(s.get('system')) or 'S'
                happy.append(f'PM->>{target}: step {s.get("order")} {s.get("step")}')
                happy.append(f'{target}-->>PM: result/status')
        if 'integration_publisher' in pids:
            happy+=['S->>DB: outbox status NEW after commit','participant IP as Integration Publisher','participant ER as Enrichment REST','IP->>DB: poll pending outbox','IP->>ER: REST enrichment','ER-->>IP: enriched data','IP->>K: publish final enriched event','IP->>DB: mark PUBLISHED','K-->>T1: deliver event']
        elif 'kafka' in pids: happy+=['S->>K: publish status/domain event','K-->>T1: deliver event']
        happy.append('S-->>I: trackingId/status/result')
        error=['sequenceDiagram','participant W as Worker/PM','participant T as Target System','participant DB as DB','participant DLQ as DLQ/Manual Recovery','W->>T: call step','T--xW: timeout/5xx','W->>DB: save failed attempt','W->>W: retry with backoff','W->>DLQ: after retry exhausted','DLQ-->>W: manual/replay decision']
        compdiag=['sequenceDiagram','participant PM as Process Manager','participant S1 as Successful Step','participant C as Compensation','participant M as Manual Task','PM->>PM: detect failed blocking step','PM->>C: run compensation for completed steps','C-->>PM: compensation result','alt compensation failed','PM->>M: create manual recovery task','end']
        return {'component':'\n'.join(comp),'happy':'\n'.join(happy),'error':'\n'.join(error),'compensation':'\n'.join(compdiag)}

    def composite_architecture(self,f,c,t,rec,patterns,anti):
        """Собирает сложное решение как композицию слоёв, а не как один winner-pattern."""
        pids=set(rec.get('pattern_ids',[])); active=set(c.get('business',{}).get('active_scenarios',[]))
        layers=[]
        def add(layer, decision, components, controls, risks=None):
            layers.append({'layer':layer,'decision':decision,'components':components,'controls':controls,'risks':risks or []})
        if rec.get('blocked'):
            add('0. Предпроектная проверка','Проектирование заблокировано до уточнения входных данных',[],c.get('input_quality',{}).get('hard_gaps',[])+c.get('input_quality',{}).get('soft_gaps',[]))
            return {'summary':'Недостаточно данных для составной архитектуры.','layers':layers,'cross_cutting':[]}
        add('1. Входной контур','Принять команду/запрос безопасно и быстро', ['API Gateway' if 'gateway' in pids else 'Service API', 'Idempotency validation', 'Request validation'], ['Auth/RBAC', 'rate limit', 'correlationId', 'единая error model'])
        if t['chain'] or 'saga' in pids or 'bpm' in pids:
            add('2. Core process','Управляемая state machine/Saga для многошаговой цепочки', ['Process Manager', 'process_steps', 'status_history'], ['timeout per step', 'retry policy', 'compensation', 'manual recovery'], ['Без owner процесса Saga превратится в distributed mess.'])
        else:
            add('2. Core operation','Простая операция в source-of-truth сервисе', ['Primary DB', 'domain service'], ['transaction boundary', 'unique constraints', 'audit'])
        if 'outbox' in pids or 'kafka' in pids or 'queue' in pids:
            add('3. Async/events','Отвязать тяжёлые/побочные интеграции от пользовательского потока', ['Transactional Outbox' if 'outbox' in pids else 'producer', 'Kafka/Queue' if ('kafka' in pids or 'queue' in pids) else 'async worker', 'Inbox/idempotent consumers' if 'inbox' in pids else 'consumers'], ['partition key', 'DLQ/retry topic', 'consumer lag alerts', 'replay policy'])
        if 'integration_publisher' in pids:
            add('3A. Event enrichment before Kafka','Собрать финальный payload без переноса ownership события', ['Source outbox/integration table', 'Integration Publisher', 'REST enrichment adapter', 'Kafka final topic'], ['sourceEventId', 'aggregateVersion', 'enrichmentConsistency', 'retry/backoff/circuit breaker', 'FAILED/manual reprocess'], ['Публикация задерживается до enrichment; нужно согласовать freshness и поведение при недоступности REST.'])
        if 'external_api_dependency' in active or t['partner'] or 'fallback' in pids:
            add('4. External adapters','Изолировать внешние API и legacy от core-flow', ['Adapter layer', 'client registry', 'attempt log'], ['timeout', 'retry with backoff+jitter', 'circuit breaker', 'rate limit', 'fallback/manual review'])
        if 'client_status_screen' in active or 'highload_read' in active or 'read_model_business' in pids or 'cache' in pids:
            add('5. Read path','Отдельный быстрый контур чтения/статуса', ['Read model/projection', 'Cache where allowed', 'GET status API'], ['last_updated', 'freshness label', 'read-your-writes rule', 'TTL/invalidation/cache stampede protection'], ['Кэш не использовать для финального финансового решения.'] if t['direct_money_impact'] else [])
        if t['dwh'] or 'dwh_reporting' in active or 'etl' in pids or 'cdc' in pids:
            add('6. Data/DWH','Аналитика и отчётность не блокируют core/client flow', ['CDC/ETL', 'staging', 'DWH/Data Lake'], ['lineage', 'quality checks', 'reconciliation', 'backfill/replay', 'late events policy'])
        if t['sensitive'] or t['regulated'] or t['regulatory_impact']:
            add('7. Security/privacy','Защита данных встроена в интеграцию', ['AuthN/AuthZ', 'audit log', 'secrets management'], ['TLS/mTLS', 'masking logs', 'field minimization', 'encryption where needed', 'retention'])
        add('8. Observability/SRE','Эксплуатационная готовность', ['logs', 'metrics', 'traces', 'business dashboard'], ['latency/error rate/availability SLI', 'DLQ size', 'retry rate', 'consumer lag', 'stuck process age', 'external dependency health'])
        cross=['API lifecycle: versioning, backward compatibility, deprecation policy, pagination/filtering/sorting where needed, rate limits, unified error model.',
               'Data contracts: schema versioning, compatibility mode, deleted/late/out-of-order events, reprocessing window.',
               'Capacity planning: RPS/TPS, payload size, partitions/consumers/workers, DB pool/indexes, retention, write amplification.']
        if t.get('enrichment_needed'):
            cross.insert(2, 'Enrichment contracts: owner of source event, owner of enrichment data, consistency level, failure/retry/reprocess policy.')
        return {'summary':'Целевая архитектура должна рассматриваться как композиция слоёв, а не как один паттерн.', 'layers':layers, 'cross_cutting':cross}

    def lifecycle(self,f,c,t,rec,anti):
        pids=set(rec.get('pattern_ids',[]))
        backlog=['Утвердить owner процесса и систем.','Утвердить source of truth и владение полями.','Утвердить статусную модель и финальные статусы.','Согласовать API/event/file/CDC/DWH contracts.','API lifecycle: versioning, backward compatibility, deprecation policy, pagination/filtering/sorting, rate limits, unified error model.','Data governance: schema versioning, compatibility mode, late/out-of-order/deleted events, lineage, quality checks, reprocessing window.','Capacity plan: RPS/TPS, payload size, partitions/consumers/workers, DB pool/indexes, retention, write amplification.','SRE/SLI: latency, error rate, availability, consumer lag, DLQ size, retry rate, stuck process age, external dependency health.','Security/privacy: masking logs, RBAC/service auth, secrets, retention, minimization, encryption where needed.','Реализовать миграции БД и индексы.','Добавить correlationId/requestId во все каналы.','Настроить logs/metrics/traces/audit.','Подготовить integration/contract/e2e tests.']
        if t.get('compromise_mode'): backlog += ['Зафиксировать ADR trade-off: почему целевой вариант невозможен сейчас, какой риск принимаем, кто owner риска, когда пересматриваем.', 'Разделить delivery на Safe MVP и Phase 2 hardening; запретить “временные” решения без даты пересмотра.']
        if 'scaling' in pids: backlog += ['Подготовить capacity plan: RPS, partitions, workers, DB pool, indexes.','Провести load/stress/soak tests.','Настроить backpressure/rate limits/autoscaling.']
        if 'saga' in pids: backlog += ['Реализовать Process Manager/Saga.','Описать compensation для каждого блокирующего шага.','Реализовать manual recovery dashboard.']
        if 'outbox' in pids: backlog += ['Реализовать Outbox Publisher и stuck alerts.']
        if 'integration_publisher' in pids:
            if t.get('new_service_forbidden'):
                backlog += ['Реализовать publisher как embedded scheduled job/module или platform adapter; явно описать, почему не создаём новый сервис в v1.', 'Ограничить coupling: отдельные таблицы, отдельные метрики, feature toggle, retry/reprocess endpoint/runbook.']
            backlog += ['Реализовать Integration Publisher: poll outbox, REST enrichment, publish final Kafka event, mark PUBLISHED/FAILED.', 'Зафиксировать ownership: source-сервис владеет фактом изменения; enrichment-сервис владеет только дополнительными данными; publisher технический.', 'Зафиксировать consistency rule enrichment: AS_OF_CHANGE / CURRENT_AT_PUBLISH / BEST_EFFORT.']
        if 'inbox' in pids: backlog += ['Реализовать Inbox/idempotent consumer и retention.']
        if 'kafka' in pids: backlog += ['Описать topic strategy, partition key, schema registry, DLQ/retry topics.']
        if t.get('single_kafka_only'): backlog += ['Для single Kafka topic зафиксировать: raw-событие не публикуется отдельно, outbox ждёт enrichment, в Kafka уходит только финальный event/snapshot.']
        if 'etl' in pids or 'cdc' in pids: backlog += ['Реализовать reconciliation, data quality checks, backfill/replay.']
        if anti: backlog += ['Закрыть critical/high anti-patterns до production.']
        tests=['Unit tests бизнес-правил.','Integration tests DB/external clients.','Contract tests API/events/files.','E2E happy path and negative paths.']
        if 'scaling' in pids or f['testing'] in ['full','regulated']: tests += ['Load tests.','Stress tests.','Soak tests.','Failover tests.','DLQ/retry/replay tests.']
        if t['sensitive']: tests += ['Security tests.','Masking logs verification.','Audit trail verification.']
        rollout={'phased':['Phase 1: contracts + DB + observability.','Phase 2: async/outbox/inbox.','Phase 3: consumers/DWH.','Phase 4: production readiness review.'],'parallel':['Запустить parallel run.','Сравнивать результаты.','Устранить расхождения.','Переключить трафик.'],'feature_toggle':['Включать по feature toggle.','Постепенно расширять охват.','Rollback toggle.'],'canary':['Canary на малую долю.','Сравнить с baseline.','Расширять при нормальных метриках.'],'big_bang':['Окно внедрения.','Миграции.','Smoke tests.','Rollback plan.']}.get(f['rollout'],[])
        adr=[{'title':f'ADR-001: {rec["name"]}','decision':f'Использовать {ru_label(rec["name"])}.','consequences':'Требуются владельцы, контракты, monitoring и recovery.'},{'title':'ADR-002: Source of truth','decision':f'Source of truth: {f["source_of_truth"]}; direct DB write запрещён.','consequences':'Изменения только через согласованный доменный контракт.'},{'title':'ADR-003: Failure policy','decision':f'Failure policy: {f["failure_policy"]}.','consequences':'Каждый шаг должен иметь retry/compensation/manual recovery.'}]
        acceptance=['Happy path выполняется.','Повтор не создаёт дубль.','Каждый шаг имеет status, owner, timeout, retry/after_retry.','DWH/analytics не блокирует клиентский процесс.','Контракты версионируются и имеют compatibility policy.','API имеет версионирование, error model, rate limits, idempotency rules для POST/команд.','Логи не содержат чувствительные данные.','Метрики и алерты покрывают API, DB, broker, DLQ, outbox, stuck steps, lag, retry rate и external dependency health.']
        if 'integration_publisher' in pids: acceptance += ['При недоступности REST enrichment событие не теряется: outbox остаётся в retry/FAILED и доступен reprocess.', 'Потребитель получает aggregateVersion и не применяет старое событие поверх нового.', 'В событии есть enrichmentConsistency/sourceEventId/businessOwner.']
        if 'scaling' in pids: acceptance += ['Проведён load/stress test на целевой RPS и peak factor.','Есть backpressure/rate limit/autoscaling policy.']
        return {'backlog':backlog,'tests':tests,'rollout':rollout,'adr':adr,'acceptance':acceptance}

    def constraints_tradeoffs(self,f,t,rec,anti):
        constraints=[]
        if f.get('constraint_profile') in ['pragmatic','minimal_safe']:
            constraints.append('Выбран режим проектирования с компромиссами: рекомендация должна разделять целевое решение и безопасный минимум.')
        if f.get('budget_pressure') in ['high','extreme']:
            constraints.append('Бюджет сильно ограничен: предпочтительны изменения в существующем контуре и поэтапный rollout.')
        if f.get('deadline_pressure') in ['tight','urgent']:
            constraints.append('Сроки сжаты: нужен MVP-slice, feature toggle/parallel run и отложенный hardening.')
        if t.get('new_service_forbidden'):
            constraints.append('Новый сервис/микросервис ограничен: publisher/orchestrator желательно реализовывать как module/job/platform adapter или выносить в phase 2.')
        if t.get('new_infra_forbidden'):
            constraints.append('Новая инфраструктура ограничена: использовать существующие REST/Kafka/queue/CDC контуры или честно фиксировать blocker.')
        if t.get('source_read_only'):
            constraints.append('Source-систему нельзя менять: outbox/state-machine в source недоступны без пересогласования.')
        elif t.get('source_minimal_only'):
            constraints.append('Source можно менять только минимально: допустимы таблица/status/outbox/API-contract, но не глубокий refactoring core-flow.')
        if str(f.get('compromise_comment','')).strip():
            constraints.append('Пояснение пользователя: '+str(f.get('compromise_comment')).strip())

        non_negotiable=['correlationId/requestId во всех каналах','timeouts на sync/REST вызовах','owner и alert для каждой ошибки','идемпотентность при retry/async','логирование без ПДн/секретов']
        if t.get('event_needed'): non_negotiable += ['schema/versioning события','DLQ/retry/reprocess policy для broker/consumer']
        if t.get('enrichment_needed'): non_negotiable += ['businessOwner/sourceSystem в событии','enrichmentConsistency/dataAsOf','FAILED/reprocess для enrichment']
        if t.get('direct_money_impact') or f.get('delivery') in ['business_exactly_once','strict']: non_negotiable += ['operation table/idempotency key/unique constraint','audit + reconciliation']

        feasible=[]; target=[]; residual=[]; phase2=[]
        target.append('Целевой вариант: архитектура без искусственных ограничений — отдельные границы ответственности, outbox/inbox, dedicated publisher/orchestrator при необходимости, полная observability.')
        if t.get('enrichment_needed') and t.get('event_needed'):
            if t.get('source_can_add_minimal_outbox') and t.get('new_service_forbidden'):
                feasible += ['Реальный v1: source-owned outbox/integration table + publisher как scheduled job/module в существующем runtime или platform adapter.', 'Kafka получает финальное enriched event; ownership события остаётся у source, enrichment-сервис владеет только дополнительными полями.']
                residual += ['Coupling с существующим runtime выше, чем у отдельного сервиса; масштабирование и deploy publisher-а сложнее.', 'При росте нагрузки publisher лучше вынести в отдельный сервис/worker pool.']
                phase2 += ['Вынести embedded publisher в отдельный сервис/worker, если появятся нагрузка, разные команды владения или независимый deploy.']
            elif t.get('source_read_only'):
                feasible += ['Реальный v1: CDC/polling/read-only export + enrichment + publish snapshot/export event, а не полноценный domain event.', 'Обязательно: watermark/offset, gap detection, reconciliation, manual reload/replay.']
                residual += ['Нет атомарной гарантии commit source → event; возможны задержки, пропуски при ошибке polling/CDC и расхождения freshness.', 'Название события должно быть честным: EntitySnapshotPrepared/ExportReady, не EntityUpdated от имени source.']
                phase2 += ['Пересогласовать минимальный outbox/source integration table для перехода от export-события к source-owned domain event.']
            else:
                feasible += ['Реальный v1 совпадает с целевым минимумом: source outbox + technical publisher + REST enrichment после commit + Kafka publish.']
        else:
            if t.get('new_service_forbidden') and (t.get('chain') or t.get('orchestrated')):
                feasible += ['Реальный v1: не строить новый orchestrator-сервис сразу; начать со status table/process_steps в текущем owner-сервисе и явных retry/manual recovery.']
                residual += ['Сложный процесс временно остаётся ближе к модульному монолиту/embedded orchestration; нужна дисциплина ownership и observability.']
                phase2 += ['Выделить Process Manager/BPM, если появятся независимые команды, 8+ шагов, human tasks или частые изменения процесса.']
            elif t.get('new_infra_forbidden'):
                feasible += ['Реальный v1: использовать существующие каналы и усилить контроли — idempotency, timeout, retry limit, reconciliation, monitoring.']
                residual += ['Без подходящего broker/queue часть асинхронности может быть batch/best-effort; это нужно явно принять бизнесом.']
            else:
                feasible += ['Ограничения не блокируют целевое решение; можно идти по production-ready варианту поэтапно.']
        if not feasible: feasible=['Ограничения не распознаны как блокирующие; использовать рекомендованный вариант, но зафиксировать cost/risk в ADR.']
        if not residual: residual=['Остаточный риск низкий/средний при выполнении non-negotiable controls и тестов.']
        if not phase2: phase2=['После MVP провести production readiness review и решить, нужен ли вынос в отдельный сервис/инфраструктуру.']
        return {'constraints':constraints or ['Явных ограничений по стоимости/стеку не задано.'], 'non_negotiable':non_negotiable, 'feasible_v1':feasible, 'target':target, 'residual_risks':residual, 'phase2':phase2}


    def compromise_matrix(self,f,t,rec,anti):
        """Three realistic options so the tool behaves like a senior SA, not a pattern dictionary."""
        base_controls=['correlationId','idempotency/replay where retries exist','timeouts + retry limits','owner + alert','monitoring + runbook','ADR with accepted residual risk']
        ideal=['Использовать целевой top-level паттерн: '+ru_label(rec.get('name',''))+'.','Разделить ownership: source of truth, technical publisher/adapter, consumer/target, operations owner.','Сразу заложить production controls: Outbox/Inbox или эквивалент, DLQ/quarantine, replay, observability, contract tests.']
        compromise=['Оставить существующие ограничения стека/бюджета, но добавить минимально безопасные контроли: '+', '.join(base_controls)+'.','Не переименовывать компромисс в “идеальную архитектуру”: явно указать residual risk и дату пересмотра.']
        temporary=['Допустим только как временный workaround: manual/reconciliation path, ограниченный scope, feature flag/kill switch, ежедневный контроль расхождений.','Запрещено скрывать отсутствие ключевых гарантий: если нет atomics/replay/idempotency — это должно быть blocker или accepted risk.']
        if t.get('operation_kind')=='batch_file_exchange':
            ideal += ['Dedicated file gateway/staging с manifest/checksum, schemaVersion, quarantine, ack/error file и restartable import.']
            compromise += ['Если есть только SFTP: добавить file_registry, checksum unique, staging tables, частичный reject-report и reprocess по file_id.']
            temporary += ['Не грузить файл напрямую в боевые таблицы без staging/quarantine и повторяемого import-run.']
        if t.get('operation_kind')=='webhook_event_intake':
            ideal += ['Webhook edge: signature/raw-body, quick ACK, Inbox, async worker, reconciliation API, provider retry contract.']
            compromise += ['Если provider retry неизвестен: хранить raw event, delivery_id/payload_hash, делать periodic reconciliation и manual replay.']
            temporary += ['Не делать долгую бизнес-обработку до ACK и не полагаться на один callback без сверки.']
        if t.get('operation_kind')=='dwh_offload':
            ideal += ['DWH/Data Lake pipeline: landing/staging, CDC/ETL as ingestion layer, schema drift policy, lineage, data quality gates, backfill.']
            compromise += ['Если можно только CDC: явно оформить CDC как механизм ingestion, а не как бизнес top-level; добавить watermark, gap detection и reconciliation.']
            temporary += ['Не блокировать core-flow отчётностью и не хранить бесконечно raw payload в OLTP.']
        if t.get('enrichment_needed') and t.get('event_needed'):
            ideal += ['Source-owned outbox + technical publisher + REST enrichment after commit + event version/sourceEventId/dataAsOf.']
            compromise += ['Если source менять нельзя: честный snapshot/export event через CDC/polling + reconciliation, не domain EntityUpdated.']
            temporary += ['Не отдавать publish ownership сервису, где “просто есть Kafka”, без явного source ownership и контроля расхождений.']
        return [
            {'option':'A. Архитектурно правильный вариант','when':'Когда можно менять нужные компоненты и есть бюджет на production controls.','decision':ideal,'risk':'Ниже, но дороже/дольше.'},
            {'option':'B. Безопасный компромисс','when':'Когда стек/сроки/бюджет ограничены.','decision':compromise,'risk':'Средний; допустим только с ADR, monitoring и планом phase 2.'},
            {'option':'C. Временный workaround','when':'Только для короткого периода или emergency.','decision':temporary,'risk':'Высокий; нужен срок жизни, owner, rollback и ручная сверка.'},
        ]

    def advanced_product_sections(self,f,c,t,rec,patterns,anti,composite,db,contracts,scenarios,diagrams,life,ready=None):
        """Product-grade sections: quality gate, MVP/Production, ADR, diagrams, capacity-lite, templates and stakeholder views."""
        pids={p['id'] for p in patterns if p.get('score',0)>=30}
        gaps=list(c.get('input_quality',{}).get('hard_gaps',[]))+list(c.get('input_quality',{}).get('soft_gaps',[]))
        critical_questions=[]
        def addq(cond, q):
            if cond and q not in critical_questions: critical_questions.append(q)
        addq(f.get('source_of_truth')=='unclear','Кто является source of truth по основной сущности и по каждому критичному полю?')
        addq(f.get('ownership')=='unclear','Какая команда владеет процессом, данными, SLA и ручным восстановлением?')
        addq(t.get('chain') and f.get('orchestration')=='unknown','Кто управляет состоянием цепочки: Process Manager, choreography, BPM или внешняя система?')
        addq(t.get('customer_visible') and not c.get('statuses'),'Какая статусная модель видна клиенту: промежуточные, финальные, ошибочные статусы и last_updated?')
        dedupe_fields={x.get('name','').lower() for x in c.get('fields',[]) if x.get('unique') or 'idempotency' in x.get('name','').lower() or x.get('name','').lower() in ['requestid','request_id','external_event_id','operationid','operation_id']}
        has_dedupe=bool(dedupe_fields) or f.get('delivery') in ['business_exactly_once','strict'] or t.get('dedupe')
        addq(t.get('direct_money_impact') and not has_dedupe,'Какой idempotency key, уникальные ограничения и правила повторного запроса для финансовой операции?')
        addq(t.get('direct_money_impact') and has_dedupe,'Idempotency/unique key указан, но нужно уточнить TTL, scope, replay same response policy и конфликтные повторные запросы.')
        addq(t.get('unstable_external'),'Что делать при таймауте/лимите/падении внешней системы: retry, очередь, fallback, manual review?')
        addq(t.get('dwh'),'Какая допустимая задержка DWH, как делаем reconciliation, backfill, lineage и data quality?')
        addq(t.get('strict_order'),'Какой ключ порядка, sequence/version, и что делать со старыми/out-of-order событиями?')
        addq(t.get('highload'),'Какие target RPS/TPS, peak, payload size, retention, допустимый lag, DB write rate и лимиты внешних API?')
        addq(t.get('active_active_financial_write'),'Как предотвращаем split-brain/double-spend: single writer per account, ledger, consensus/conflict resolution, reconciliation?')
        addq(t.get('multi_tenant_noisy_neighbor'),'Как изолируем tenants: quota, partitioning, fair scheduling, separate pools и lag per tenant?')
        addq(t.get('highload_stream_ingestion'),'Какой partition key, event_time/watermark, late-event policy, hot partition control и replay window для stream ingestion?')
        addq(t.get('enrichment_needed'),'Кто business owner события, кто technical publisher, кто owner enrichment-данных?')
        addq(t.get('enrichment_needed'),'Обогащение обязательно или можно публиковать partial payload; что делаем при таймауте enrichment REST?')
        addq(t.get('enrichment_consistency_unknown'),'Enrichment-данные нужны на момент изменения сущности, на момент публикации или best effort?')
        addq(t.get('single_kafka_only') and t.get('enrichment_needed'),'Если Kafka topic один, допускается ли delayed publish финального события из outbox до успешного enrichment?')
        addq(t.get('source_lacks_kafka') and t.get('event_needed'),'Можно ли добавить outbox/integration table в source-сервис или разрешён только CDC/polling?')
        addq(t.get('sensitive'),'Какие поля являются ПДн/секретами, где маскирование, шифрование, retention и аудит доступа?')
        addq(t.get('compromise_mode'),'Какие ограничения являются жёсткими, а какие можно пересогласовать: новый сервис, новая инфраструктура, изменение source, сроки, бюджет?')
        addq(t.get('compromise_mode'),'Какой остаточный риск бизнес готов принять временно, и какой deadline для перехода к целевому варианту?')

        op=t.get('operation_kind')
        addq(True, 'Что является главным результатом: команда/операция, событие, read-model, batch file, webhook intake, DWH pipeline или migration?')
        addq(op=='batch_file_exchange','Какой manifest/checksum/ack-file/error-file, staging/quarantine и правила reprocess для каждого файла?')
        addq(op=='webhook_event_intake','Какой external_event_id/delivery_id, signature/raw-body validation, quick ACK SLA, provider retry policy и reconciliation API?')
        addq(op=='dwh_offload','CDC здесь top-level цель или только ingestion layer для DWH/Data Lake; какие zones, schema drift policy, lineage и data quality gates?')
        addq(op=='cdc_legacy_modernization','CDC отражает бизнес-событие или технический snapshot; как называем события, чтобы не врать потребителям?')
        readiness_gate='blocked' if c.get('input_quality',{}).get('blocked') else 'risky' if len(gaps)>=5 or any(a.get('severity')=='critical' for a in anti) else 'ready'
        gate_text={'blocked':'Нельзя выдавать финальное архитектурное решение: сначала закрыть блокирующие пробелы.','risky':'Можно сформировать предварительный дизайн, но перед разработкой нужно закрыть открытые вопросы.','ready':'Данных достаточно для предварительного ADR и обсуждения с архитектором.'}[readiness_gate]
        tradeoffs=self.constraints_tradeoffs(f,t,rec,anti)

        mvp=['Зафиксировать входной контракт и error model.','Добавить correlationId/requestId во все вызовы.','Сохранить операцию/заявку до внешних вызовов.','Настроить timeout и ограниченный retry с backoff.','Логировать технические и бизнес-ошибки без ПДн.']
        prod=['Полная наблюдаемость: latency/error rate/availability, traces, stuck process age, DLQ/retry rate.','Runbook и manual recovery для зависших операций.','Contract/e2e/load/failover tests.','Security/privacy review: masking, service auth, secrets, retention.']
        if 'saga' in pids or t.get('orchestrated'):
            mvp+=['Минимальная state machine с финальными и ошибочными статусами.']
            prod+=['Process Manager/Saga с таймерами, compensation, manual recovery dashboard.']
        if 'outbox' in pids or t.get('event_needed'):
            mvp+=['Transactional Outbox для публикации критичных событий.']
            prod+=['Outbox publisher со stuck alerts, replay и мониторингом publish lag.']
        if 'inbox' in pids or t.get('inbox_needed'):
            mvp+=['Inbox/deduplication для входящих событий/callback.']
            prod+=['Retention, replay и DLQ для Inbox/consumers.']
        if 'kafka' in pids or t.get('event_needed'):
            prod+=['Topic strategy, partition key, schema registry, compatibility mode, retry topics/DLQ.']
        if 'integration_publisher' in pids or t.get('enrichment_needed'):
            mvp+=['Outbox/integration table со статусами NEW/ENRICHING/PUBLISHED/FAILED для событий, требующих enrichment.']
            mvp+=['REST enrichment adapter с timeout и ограниченным retry вне транзакции изменения сущности.']
            prod+=['Integration Publisher с circuit breaker, retry/backoff/jitter, reprocess, stuck alerts и метриками enrichment latency/error rate.']
            prod+=['Версионность: aggregateVersion/sourceEventId/enrichmentConsistency/dataVersion/asOf в событии и проверка старых событий потребителем.']
        if t.get('customer_visible'):
            mvp+=['GET status + понятные статусы для клиента.']
            prod+=['Status read model/cache с last_updated/freshness label и fallback stale-data только для чтения.']
        if t.get('dwh'):
            mvp+=['Non-blocking выгрузка в DWH; core-flow не ждёт отчётность.']
            prod+=['CDC/ETL со staging, data quality checks, reconciliation, lineage, backfill и late-events policy.']
        if t.get('legacy'):
            mvp+=['Adapter/ACL вокруг legacy; прямые зависимости из core минимизировать.']
            prod+=['Rate limit/circuit breaker, quarantine для файлов, checksum/manifest и reconciliation.']
        if t.get('direct_money_impact'):
            mvp+=['Idempotency key + operation table + unique constraints.']
            prod+=['Audit trail, reconciliation, practically-once controls и ручной разбор расхождений.']

        rejected=[]
        def rej(cond,name,why):
            if cond: rejected.append({'name':name,'why':why})
        rej(t.get('chain') and rec.get('name')!='Basic API + DB','Чистая синхронная REST-цепочка','Длинная/многоуровневая цепочка нестабильна, плохо восстанавливается и усиливает latency внешних систем.')
        rej(t.get('dwh') and (t.get('chain') or t.get('customer_visible')),'DWH как часть core-flow','Отчётность не должна блокировать клиентский или финансовый процесс.')
        rej(t.get('direct_money_impact'),'Кэш как источник финального решения','Устаревшие данные могут привести к финансовой ошибке; кэш допустим только для read-only представлений/статусов.')
        rej(t.get('webhook_callback') or 'webhook_callback' in t.get('business_situations',set()),'Callback без Inbox/idempotency','Callback может прийти дважды, позже или не в порядке; нужна дедупликация и replay.')
        rej(t.get('legacy'),'Прямой вызов legacy из клиентского запроса','Legacy часто медленный/нестабильный; нужен adapter, timeout, circuit breaker и деградация.')
        rej(t.get('enrichment_needed') and t.get('event_needed'),'Публикация события сервисом, где просто есть Kafka','Kafka-инфраструктура не определяет владельца бизнес-события; сервис с частью данных не должен публиковать EntityUpdated как владелец изменения.')
        rej(t.get('rest_enrichment') and t.get('event_needed'),'REST enrichment внутри транзакции изменения сущности','Сбой enrichment-сервиса не должен откатывать или блокировать бизнес-факт изменения; enrichment нужен после commit через outbox/publisher.')
        rej(t.get('single_kafka_only') and t.get('enrichment_needed'),'Raw→enriched через два Kafka topic','Ограничение: Kafka topic/контур один; нужно delayed publish финального события или другой честный event type.')

        rps=safe_int(f.get('rps'),0); peak=safe_int(f.get('peak_factor'),1); payload=max(1,safe_int(f.get('payload_kb'),5)); retention=max(1,safe_int(f.get('retention_days'),30)); lag=max(1,safe_int(f.get('target_lag_seconds'),60))
        peak_rps=rps*peak if rps else 0
        mbps=round(peak_rps*payload/1024,2) if peak_rps else 0
        daily_gb=round((rps*payload*86400)/(1024*1024),2) if rps else 0
        rec_partitions=0
        rec_partitions_range='0'
        if peak_rps:
            base_partitions=max(3, min(96, (peak_rps//750)+1))
            if t.get('strict_order'): base_partitions=max(base_partitions, 6)
            rec_partitions=base_partitions
            rec_partitions_range=f'{base_partitions}–{min(192, base_partitions*2)}'
        capacity={
          'peak_rps':peak_rps,'payload_kb':payload,'traffic_mbps':mbps,'daily_gb':daily_gb,'retention_days':retention,'lag_seconds':lag,'recommended_partitions':rec_partitions,'recommended_partitions_range':rec_partitions_range,
          'notes':['Это не sizing, а стартовая гипотеза для нагрузочного теста; финальное число partitions/workers считается по latency, consumer lag, DB write amplification, лимитам downstream и storage.']}
        if peak_rps>=1000: capacity['notes']+=['Нужны backpressure, rate limit, отдельный capacity plan для consumers/workers и БД.']
        if t.get('strict_order'): capacity['notes']+=['Partition key должен совпадать с aggregate/entity id, иначе порядок статусов не гарантируется.']
        if daily_gb>50: capacity['notes']+=['Проверьте retention, storage cost, compaction/archiving и write amplification.']
        if t.get('dwh'): capacity['notes']+=['Для DWH считать batch window, late events, backfill throughput и reconciliation window.']
        if t.get('enrichment_needed'): capacity['notes']+=['Для enrichment считать не только Kafka throughput, но и REST RPS/latency/error rate, retry storm и размер очереди pending outbox.']
        if not capacity['notes']: capacity['notes']=['Нагрузка выглядит умеренной; всё равно нужны лимиты, pool sizes и базовые нагрузочные тесты.']

        context_diagram=self.extra_context_diagram(f,c,t)
        event_diagram=self.extra_event_diagram(f,c,t)
        data_diagram=self.extra_data_diagram(f,c,t)
        failure_diagram=self.extra_failure_diagram(f,c,t)

        current_vs_target=[]
        caps=set(f.get('existing_capabilities',[]) if isinstance(f.get('existing_capabilities'),list) else split_csv(f.get('existing_capabilities','')))
        expected={'outbox':'Transactional Outbox','inbox':'Inbox/idempotency','dlq':'DLQ','monitoring':'Monitoring/metrics','audit':'Audit','status_model':'Status model','kafka':'Broker/event stream'}
        for cap,label in expected.items():
            needed=(cap in ['monitoring','audit']) or (cap=='outbox' and ('outbox' in pids or t.get('event_needed'))) or (cap=='inbox' and t.get('inbox_needed')) or (cap=='dlq' and (t.get('event_needed') or t.get('queue_needed'))) or (cap=='status_model' and t.get('customer_visible')) or (cap=='kafka' and t.get('event_needed'))
            if needed and cap not in caps: current_vs_target.append(f'Добавить {label}.')
        if not current_vs_target: current_vs_target=['Критичных разрывов между текущими capabilities и целевым контуром по заполненным данным не найдено.']

        if rec.get('blocked'):
            adr={
              'title':f'ADR-DRAFT: Предпроектная проверка для {f.get("project_name") or "процесса"}',
              'context':[f'Бизнес-цель: {f.get("business_goal") or "не указана"}', 'Входные данные недостаточны для выбора архитектуры.', f'Готовность требований: {(ready or {}).get("score", c.get("input_quality",{}).get("score",0))}%.'],
              'decision':['Архитектурное решение не утверждать до закрытия блокирующих вопросов.', 'Сначала заполнить business goal, systems, steps, source of truth, ownership, load/SLA и error handling.', 'После уточнения повторно сформировать ADR.'],
              'alternatives':['Альтернативы не сравнивались: недостаточно входных данных.'],
              'consequences':['Нельзя передавать решение в разработку как финальное.', 'Следующий шаг — уточнение требований и повторная генерация отчёта.']}
        else:
            adr={
              'title':f'ADR-001: Интеграционный подход для {f.get("project_name") or "процесса"}',
              'context':[f'Бизнес-цель: {f.get("business_goal") or "не указана"}', f'Основная рекомендация: {ru_label(rec.get("name"))}.', f'Готовность требований: {(ready or {}).get("score", c.get("input_quality",{}).get("score",0))}%.'],
              'decision':[f'Использовать {ru_label(rec.get("name"))} как главную архитектуру.', 'Частные паттерны оформлять как внутренние слои, а не как конкурирующие top-level решения.', 'Для критичных операций использовать idempotency, state tracking, audit и recovery.'] + (['Для shared Kafka topic: не подменять кейс Outbox-ом; главный контур — selective consumer, capacity/backpressure, idempotent sink, DLQ/quarantine, lag/filter metrics и replay plan.'] if t.get('shared_topic_selective') else []) + (['Для enrichment-before-Kafka: source-сервис владеет фактом изменения, integration publisher технически обогащает и публикует, REST enrichment выполняется после commit/outbox, а consistency level фиксируется в контракте.'] if t.get('enrichment_needed') else []),
              'alternatives':[f'{x["name"]}: отклонено/ограничено — {x["why"]}' for x in rejected] or ['Альтернативы не выявлены по заполненным данным.'],
              'consequences':['Потребуется ownership процесса, контракты, тесты, SRE-метрики и runbook.', 'Решение должно пройти архитектурное ревью перед production.']}

        audience=f.get('report_audience','analyst')
        stakeholder={
          'business':['Зачем: снизить потери, зависания и ручную поддержку за счёт понятного статуса, recovery и контролируемой деградации.','Главный риск: неполные требования по SLA/свежести/source of truth.'],
          'analyst':['Описать статусы, error matrix, source of truth, контракты, owner/SLA, retry/replay и acceptance criteria.','Проверить открытые вопросы из quality gate до передачи в разработку.'],
          'developer':['Реализовать API contracts, operation table/state machine, outbox/inbox/DLQ, idempotency, migrations, indexes, metrics.','Не логировать ПДн; добавить correlationId и contract tests.'],
          'architect':['Проверить top-level подход, границы bounded contexts, consistency trade-offs, resilience, scaling и migration/rollout.','Утвердить ADR и ключевые NFR.']}
        if audience!='all': stakeholder={'selected_'+audience:stakeholder.get(audience,stakeholder['analyst'])}

        templates=['REST request-response integration','REST + external API adapter','Kafka event publication with Outbox','Kafka consumer + Postgres idempotent sink','Shared topic selective consumer','Webhook intake + Inbox','Batch/File/SFTP exchange','SFTP reconciliation','Saga orchestration / process manager','BFF/API Composition / Customer 360','Status screen with cache/read model','DWH offloading and retention','CDC replication','Legacy strangler migration','Reference/master-data synchronization','Regulatory data model change','Current solution review / audit','Queue-based async worker','Near real-time decision flow']
        if t.get('enrichment_needed'):
            templates.insert(3, 'Event enrichment before Kafka publish')
            templates.insert(4, 'Single Kafka topic + REST enrichment')

        impact_analysis=[]
        if t.get('regulatory_impact') or 'regulatory_process' in t.get('business_situations',set()) or f.get('task_type') in ['add_to_existing','data_migration']:
            impact_analysis += [
              'DB/model: проверить cardinality 1→N, новые таблицы/JSON/array, индексы, constraints, миграцию и rollback.',
              'API contracts: versioning, backward compatibility, mapping старого поля в новую структуру, error codes для legacy clients.',
              'Events/Kafka: eventVersion, schema compatibility, required/optional fields, consumer impact и DLQ для несовместимых сообщений.',
              'DWH/reports: staging, backfill, reconciliation, lineage, historical correction и влияние на регуляторную отчётность.',
              'UI/validation: как пользователь вводит несколько значений, обязательность, справочники, отображение старых записей.',
              'Legacy consumers: inventory потребителей, phased rollout, parallel run, feature flag и дата отключения старого контракта.',
              'Testing: migration tests, contract tests, regression на старые данные, e2e тесты отчётности и negative cases.'
            ]
        if t.get('dwh') and (t.get('very_large') or 'отч' in str(f.get('business_goal','')).lower() or 'raw' in str(f.get('business_goal','')).lower() or 'payload' in str(f.get('business_goal','')).lower()):
            impact_analysis += [
              'Storage/retention: raw payload не держать бесконечно в prod OLTP; вынести в object/cold storage, в БД оставить metadata/status/archiveUri.',
              'Purge/archive: partition drop или scheduled purge после DWH ack/retention; отдельный контроль ошибок выгрузки.',
              'Reconciliation: batch_id/load_id, record counts, checksum, retry/backfill и отчёт о расхождениях.'
            ]
        if not impact_analysis:
            impact_analysis=['Специальный impact-analysis не требуется по выбранным формам; достаточно обычных contract/error/rollout checks.']

        return {'quality_gate':{'status':readiness_gate,'text':gate_text,'gaps':gaps,'critical_questions':critical_questions},'tradeoffs':tradeoffs,'compromise_matrix':self.compromise_matrix(f,t,rec,anti),'mvp':mvp,'production':prod,'rejected_alternatives':rejected,'capacity':capacity,'extra_diagrams':{'context':context_diagram,'event_flow':event_diagram,'data_flow':data_diagram,'failure_flow':failure_diagram},'current_vs_target':current_vs_target,'impact_analysis':impact_analysis,'adr':adr,'stakeholder_reports':stakeholder,'templates':templates}

    def extra_context_diagram(self,f,c,t):
        systems=[x for x in c.get('systems',[])[:10]]
        lines=['flowchart LR','  User[User/Initiator] --> API[API / Entry Point]','  API --> PM[Process Manager / State Machine]']
        if not systems:
            systems=[{'name':f.get('source_system') or 'Source','blocking':'blocking','channel':'rest'},{'name':'Target','blocking':'blocking','channel':'rest'}]
        for i,sys in enumerate(systems):
            name=sys.get('name') or sys.get('system') or f'System {i+1}'
            node=f'S{i}'
            safe=re.sub(r'[^a-zA-Z0-9_а-яА-Я ]','',str(name))[:40] or f'System {i+1}'
            blocking=str(sys.get('blocking','')).lower()
            channel=str(sys.get('channel','')).lower()
            if 'dwh' in safe.lower() or 'analytic' in channel or sys.get('role','').lower() in ['dwh','analytics','reporting']:
                lines.append(f'  PM -. non-blocking analytics .-> {node}[{safe}]')
            elif blocking in ['non_blocking','async','no','false'] or channel in ['kafka','queue','cdc','etl','event']:
                lines.append(f'  PM -. async/non-blocking .-> {node}[{safe}]')
            else:
                lines.append(f'  PM --> {node}[{safe}]')
        if t.get('dwh') and not any('dwh' in (x.get('name','') or '').lower() for x in systems):
            lines.append('  PM -. CDC/ETL non-blocking .-> DWH[DWH / Reporting]')
        if t.get('customer_visible'):
            lines.append('  PM --> Status[Status Read Model]')
            lines.append('  Status --> User')
        return '\n'.join(lines)

    def extra_event_diagram(self,f,c,t):
        if t.get('enrichment_needed') and t.get('event_needed'):
            lines=['sequenceDiagram','  participant Source as Source Service / Owner','  participant DB as Source DB','  participant Outbox as Outbox','  participant Pub as Integration Publisher','  participant Enrich as Enrichment REST Service','  participant Broker as Kafka single topic','  participant Consumer as Target Consumer']
            lines+=['  Source->>DB: update entity + increment aggregateVersion','  Source->>Outbox: insert pending event in same transaction','  Pub->>Outbox: poll NEW event','  Pub->>Enrich: REST resolve(aggregateId, aggregateVersion, sourceEventId)','  alt enrichment success','    Enrich-->>Pub: enrichment data + dataVersion/asOf','    Pub->>Broker: publish final enriched event','    Pub->>Outbox: mark PUBLISHED','    Broker->>Consumer: deliver event','    Consumer->>Consumer: idempotency + aggregateVersion check','  else timeout/error','    Pub->>Outbox: retry later / FAILED / manual reprocess','  end']
            return '\n'.join(lines)
        lines=['sequenceDiagram','  participant Core as Core/Process Manager','  participant Outbox as Outbox','  participant Broker as Broker/Queue','  participant Consumer as Consumer/Inbox','  participant DLQ as DLQ']
        lines+=['  Core->>Outbox: save event in same transaction','  Outbox->>Broker: publish event','  Broker->>Consumer: deliver event','  Consumer->>Consumer: dedupe/idempotency check','  alt processing failed','    Consumer->>DLQ: move poison message','  else success','    Consumer-->>Broker: ack','  end']
        return '\n'.join(lines)

    def extra_data_diagram(self,f,c,t):
        lines=['flowchart TD','  Source[(Source of Truth)] --> Core[(Operational DB)]','  Core --> Audit[(Audit/Status History)]']
        if t.get('customer_visible') or t.get('read_heavy'): lines+=['  Core --> Projection[(Read Model)]','  Projection --> Cache[(Cache)]','  Cache --> UI[Client/UI]']
        if t.get('dwh'): lines+=['  Core -. CDC/ETL .-> Staging[(DWH Staging)]','  Staging --> Quality[Quality Checks]','  Quality --> DWH[(DWH/Data Mart)]']
        return '\n'.join(lines)

    def extra_failure_diagram(self,f,c,t):
        return '\n'.join(['sequenceDiagram','  participant Caller','  participant API','  participant Core','  participant External','  participant Ops as Manual Recovery','  Caller->>API: request with correlationId/idempotencyKey','  API->>Core: persist operation + status','  Core->>External: call with timeout','  alt timeout/error','    Core->>Core: retry with backoff','    Core->>Ops: create manual task if retries exhausted','    Core-->>Caller: trackingId + status PROCESSING/ERROR','  else success','    Core-->>Caller: result/status','  end'])

    def readiness(self,f,c,t,anti,rec):
        gaps=[]
        for k in ['project_name','task_type','business_goal','source_system','main_entity','fields','process_steps','systems_matrix']:
            if not str(f.get(k,'')).strip(): gaps.append('Не заполнено обязательное поле: '+k)
        if t['unknown_orchestration']: gaps.append('Не выбран способ управления цепочкой.')
        if f['source_of_truth']=='unclear': gaps.append('Не определён source of truth.')
        if f['ownership']=='unclear': gaps.append('Не определено владение данными.')
        if t['highload'] and (not f.get('rps') or f['peak_factor']=='unknown'): gaps.append('Для highload не заполнены RPS/peak factor.')
        for s in c['systems']:
            if not s.get('owner'): gaps.append('В матрице систем не указан owner: '+s.get('name','?'))
            if not s.get('sla'): gaps.append('В матрице систем не указан SLA: '+s.get('name','?'))
        for s in c['steps']:
            for col in ['owner','timeout','retry','blocking','channel']:
                if not s.get(col): gaps.append(f'В шаге {s.get("step","?")} не заполнено {col}.')
        orders=[x.get('order') for x in c['steps'] if x.get('order')]
        known=set(orders)|{'root',''}
        if len(orders)!=len(set(orders)): gaps.append('В матрице шагов дублируются order.')
        for st in c['steps']:
            for parent in [p.strip() for p in st.get('parent','').split(',') if p.strip()]:
                if parent not in known: gaps.append(f'Шаг {st.get("step","?")} ссылается на несуществующий parent={parent}.')
        if f['chain_depth']=='fanout_fanin' and not any(',' in x.get('parent','') for x in c['steps']): gaps.append('Для fan-out/fan-in не указан join-шаг с несколькими parent.')
        critical=sum(1 for a in anti if a['severity']=='critical'); high=sum(1 for a in anti if a['severity']=='high'); med=sum(1 for a in anti if a['severity']=='medium')
        iq=c.get('input_quality',{})
        for g in iq.get('hard_gaps',[]):
            if g not in gaps: gaps.insert(0,g)
        for g in iq.get('soft_gaps',[]):
            if g not in gaps: gaps.append(g)
        score=100-len(gaps)*5-critical*18-high*8-med*3
        confidence=min(score, iq.get('score',100))
        if rec.get('blocked'):
            score=min(score,45); confidence=min(confidence,35)
        level='high' if confidence>=75 else 'medium' if confidence>=55 else 'low'
        return {'score':max(0,min(100,score)),'confidence':max(0,min(100,confidence)),'confidence_level':level,'gaps':gaps}

    def markdown(self,f,c,t,patterns,variants,rec,anti,db,contracts,scenarios,diagrams,life,ready,composite=None,advanced=None):
        md=[f"# Архитектурное решение по интеграции: {f['project_name'] or 'Интеграционный сценарий'}\n",f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",'---\n']
        human_intro = readable_report_intro(f, c, t, rec, anti, ready, advanced)
        # По умолчанию пользователь получает короткий, связный отчёт без сырой технической простыни.
        # Полный старый отчёт с матрицами/DDL доступен только при report_detail=expert.
        if str(f.get('report_detail','')) == 'human':
            md.append(human_intro)
            md += ['## 9. Тест-кейсы для проверки\n']
            
            if isinstance(scenarios, list):
                scenario_items = scenarios
            elif isinstance(scenarios, dict):
                scenario_items = []
                for v in scenarios.values():
                    if isinstance(v, list):
                        scenario_items.extend(v)
                    elif isinstance(v, dict):
                        scenario_items.append(v)
                    elif v:
                        scenario_items.append(str(v))
            else:
                scenario_items = []
            for item in (scenario_items or [])[:10]:
                if isinstance(item, dict):
                    md.append(f"- **{item.get('name','Сценарий')}**: {item.get('steps') or item.get('expected') or item.get('why','проверить основной и ошибочный путь')}\n")
                else:
                    md.append(f"- {item}\n")
            if not scenarios:
                md += [bullet(['Happy path: процесс проходит от старта до финального статуса.', 'Timeout внешней системы: появляется retry/status/manual recovery, а пользователь не зависает.', 'Повтор запроса/события: дубль не создаётся благодаря idempotency/eventId.', 'Параллельная/DWH/notification ветка не ломает основной клиентский процесс.', 'Rollback/feature toggle позволяет безопасно отключить новую цепочку.'])]
            md += ['## 10. Краткий ADR\n', '### Контекст\n', f"{f.get('business_goal') or 'Нужно связать системы и сделать процесс наблюдаемым.'}\n", '### Решение\n', f"Базовый подход: {ru_label(rec.get('name',''))}. Цепочка строится как управляемый процесс со статусами, обработкой ошибок и понятным восстановлением.\n", '### Последствия\n', 'Появятся явные статусы, владельцы ошибок, retry/recovery правила, контракты и тесты. Это добавляет дисциплину в проектирование, но снижает риск дублей, потерь и зависших операций.\n']
            md += ['## 11. Expert appendix скрыт\n', 'Сырые матрицы, DDL и полный технический экспорт не показываются в обычном отчёте. Откройте экспертный режим и выберите полный отчёт, если они нужны архитектору или разработчику.\n']
            return '\n'.join(md)
        md.append(human_intro)
        blocking=[a for a in anti if a.get('severity') in ['critical','high']]
        effective_ready = min(ready.get('score',0), 70) if blocking else ready.get('score',0)
        simple_lines=[f"Проектировать: {ru_label(rec['name'])}."]
        # Do not dump pattern names here: the readable report above already explains controls per step.
        if t.get('customer_visible'):
            simple_lines.append('Сначала быстро принять запрос и вернуть понятный trackingId/status, а не держать пользователя на всей цепочке.')
        if t.get('money_impact'):
            simple_lines.append('Для денег/лимитов обязательны operation table, idempotency key, audit и reconciliation.')
        if t.get('event_needed'):
            simple_lines.append('Для событий нужны надёжная публикация, дедупликация consumer-а, DLQ/reprocess и мониторинг lag.')
        if advanced and advanced.get('mvp'):
            simple_lines.append('MVP: '+str(advanced.get('mvp')[0]))
        if advanced and advanced.get('production'):
            simple_lines.append('Production: '+str(advanced.get('production')[0]))
        blocking=[a for a in anti if a.get('severity') in ['critical','high']]
        if blocking:
            simple_lines.append('Сначала исправить: '+ '; '.join(a.get('title','') for a in blocking[:3])+'.')
        md += ['## 0. Финальное решение в 5 строк для новичка\n', bullet(simple_lines)]
        display_score = rec.get('score', 0)
        score_text = f"{display_score}%" if not blocking else f"предварительная ({display_score}%), но есть blocker — не считать готовым решением"
        readiness_text = f"{effective_ready}%" if not blocking else f"{effective_ready}% максимум из-за blocker-ов; исходная полнота данных {ready.get('score',0)}%"
        md += ['## 1. Резюме\n',f"**Тип задачи:** {f['task_type']}\n",f"**Нагрузка:** {f['load_profile']}, RPS/TPS={f['rps']}, peak={f['peak_factor']}\n",f"**Рекомендованный вариант:** {ru_label(rec['name'])}\n",f"**Оценка варианта:** {score_text}\n",f"**Готовность требований:** {readiness_text}\n"]
        if ready['gaps']: md += ['### Пробелы\n',bullet(ready['gaps'])]
        md += ['## 1A. Введённые матрицы полного описания процесса\n']
        matrix_summary=[]
        for label,key in [('Целевые связи','target_integrations'),('Переходы процесса','process_flow'),('Контракты','contracts_declared'),('Бизнес-правила','business_rules'),('Capacity','capacity_declared'),('Observability','observability_declared'),('Rollout/migration','rollout_declared'),('Data quality/lineage','data_quality_lineage')]:
            matrix_summary.append(f'{label}: {len(c.get(key,[]))} строк')
        md += [bullet(matrix_summary)]
        if c.get('target_integrations'):
            md += ['### Целевые связи\n']
            for row in c.get('target_integrations')[:12]: md.append('- '+ ' → '.join([row.get('from','?'), row.get('to','?')]) + f"; channel={row.get('channel','')}; contract={row.get('contract','')}; retry={row.get('retry','')}; dlq={row.get('dlq','')}; idempotency={row.get('idempotency','')}\n")
        if c.get('business_rules'):
            md += ['### Бизнес-правила\n']
            for row in c.get('business_rules')[:12]: md.append(f"- {row.get('rule_id','')}: if {row.get('condition','')} → {row.get('action','')} [{row.get('affected_step','')}]\n")
        if advanced:
            qg=advanced.get('quality_gate',{})
            qg_status = qg.get('status')
            qg_text = qg.get('text')
            if blocking and qg_status == 'ready':
                qg_status = 'conditional'
                qg_text = 'Данных достаточно для предварительного ADR, но есть blocker: решение нельзя считать готовым без закрытия рисков.'
            md += ['## 2. Quality gate требований\n',f"**Статус:** {qg_status} — {qg_text}\n"]
            if qg.get('critical_questions'): md += ['### Критично уточнить\n',numbered(qg.get('critical_questions'))]
            if qg.get('gaps'): md += ['### Пробелы входных данных\n',bullet(qg.get('gaps'))]
            tr=advanced.get('tradeoffs',{})
            md += ['## 2A. Ограничения, компромиссы и реалистичный вариант\n']
            md += ['### Жёсткие ограничения\n',bullet(tr.get('constraints'))]
            md += ['### Реалистичный v1 при ограничениях\n',bullet(tr.get('feasible_v1'))]
            md += ['### Целевой вариант без ограничений\n',bullet(tr.get('target'))]
            md += ['### Остаточные риски компромисса\n',bullet(tr.get('residual_risks'))]
            md += ['### Что нельзя выкидывать даже в компромиссе\n',bullet(tr.get('non_negotiable'))]
            md += ['### Phase 2 / долг по архитектуре\n',bullet(tr.get('phase2'))]
            md += ['## 2B. Матрица вариантов: правильно / компромисс / workaround\n']
            for row in advanced.get('compromise_matrix',[]):
                md += [f"### {row.get('option')}\n", f"Когда: {row.get('when')}\n", 'Что делать:\n', bullet(row.get('decision')), f"Риск: {row.get('risk')}\n"]
            md += ['## 3. Главная архитектура и внутренние слои\n',f"**Главная архитектура:** {ru_label(rec['name'])}\n"]
            if composite:
                def render_layer(layer):
                    if isinstance(layer, dict):
                        title = layer.get('layer') or layer.get('name') or 'Слой архитектуры'
                        decision = layer.get('decision') or layer.get('purpose') or ''
                        md.append(f"### {title}\n")
                        if decision: md.append(f"{decision}\n")
                        if layer.get('components'): md.extend(['Компоненты:\n', bullet(layer.get('components'))])
                        if layer.get('patterns'): md.extend(['Паттерны:\n', bullet(layer.get('patterns'))])
                        if layer.get('controls'): md.extend(['Контроли:\n', bullet(layer.get('controls'))])
                        if layer.get('risks'): md.extend(['Риски:\n', bullet(layer.get('risks'))])
                    else:
                        md.append(f"- {layer}\n")
                if isinstance(composite, list):
                    for layer in composite: render_layer(layer)
                elif isinstance(composite, dict):
                    if composite.get('summary'):
                        md += ['### Кратко\n', bullet([composite.get('summary')])]
                    if composite.get('layers'):
                        md.append('### Слои\n')
                        for layer in composite.get('layers'):
                            render_layer(layer)
                    if composite.get('cross_cutting'):
                        md += ['### Сквозные требования\n', bullet(composite.get('cross_cutting'))]
            md += ['## 4. MVP-вариант\n',bullet(advanced.get('mvp')),'## 5. Production-вариант\n',bullet(advanced.get('production'))]
            md += ['## 5A. Impact analysis / что ещё затронет изменение\n', bullet(advanced.get('impact_analysis'))]
            md += ['## 6. Почему не выбраны опасные альтернативы\n']
            if advanced.get('rejected_alternatives'):
                for x in advanced.get('rejected_alternatives'): md.append(f"- **{x['name']}** — {x['why']}\n")
            else: md.append('Опасные альтернативы по заполненным данным не выявлены.\n')
            cap=advanced.get('capacity',{})
            md += ['## 7. Capacity planning lite\n',f"- Peak RPS/TPS: {cap.get('peak_rps')}\n- Payload: {cap.get('payload_kb')} KB\n- Поток: ~{cap.get('traffic_mbps')} MB/s\n- Дневной объём: ~{cap.get('daily_gb')} GB/day\n- Retention: {cap.get('retention_days')} days\n- Рекомендуемый стартовый минимум partitions/workers: {cap.get('recommended_partitions')}\n- Стартовый диапазон для теста: {cap.get('recommended_partitions_range', cap.get('recommended_partitions'))}\n",'### Capacity notes\n',bullet(cap.get('notes'))]
            md += ['## 8. Проверка текущего состояния против целевого\n',bullet(advanced.get('current_vs_target'))]
            md += ['## 9. Отчёты для ролей\n']
            for role,items in advanced.get('stakeholder_reports',{}).items(): md += [f"### {role}\n",bullet(items)]
            md += ['## 10. ADR export\n']
            adr=advanced.get('adr',{})
            md += [f"### {adr.get('title')}\n",'#### Контекст\n',bullet(adr.get('context')),'#### Решение\n',bullet(adr.get('decision')),'#### Альтернативы\n',bullet(adr.get('alternatives')),'#### Последствия\n',bullet(adr.get('consequences'))]
            md += ['## 11. Дополнительные диаграммы\n']
            for title,key in [('Context diagram','context'),('Event flow','event_flow'),('Data flow','data_flow'),('Failure flow','failure_flow')]:
                md += [f"### {title}\n",'```mermaid\n',advanced.get('extra_diagrams',{}).get(key,''),'\n```\n']
            md += ['## 12. Библиотека похожих шаблонов\n',bullet(advanced.get('templates'))]
        pg=self.production_gate(f,c,t,anti,rec,c.get('case_classes',[]))
        md += ['## 12A. Production gate / можно ли отдавать в разработку\n',f"**Статус:** {pg.get('level')} — {pg.get('text')}\n",'### Закрыть до разработки\n',bullet(pg.get('required_before_dev')),'### Закрыть до production\n',bullet(pg.get('required_before_prod'))]
        self_check=['source of truth выбран: '+str(bool(f.get('source_of_truth'))),'owner процесса/систем указан: '+str(any(x.get('owner') for x in c.get('systems',[]))),'консистентность указана: '+str(bool(f.get('consistency'))),'failure handling указан: '+str(bool(f.get('failure_policy'))),'контекстный ключ надёжности проверен: '+str(t.get('reliability_key')),'observability указана: '+str(bool(f.get('observability'))),'security/auth указаны: '+str(bool(f.get('auth'))),'rollback/replay указаны: '+str(bool(f.get('rollout') and f.get('replay'))),'contracts сгенерированы: API/Event/File/CDC/DWH по выбранным паттернам','test cases сформированы: '+str(bool(life.get('tests')))]
        md += ['## 12B. Self-check результата\n',bullet(self_check)]
        md += ['## 13. Архитектурные варианты\n']
        for i,v in enumerate(variants,1):
            variant_score = f"{v['score']}%" if not blocking else f"предварительная ({v['score']}%), зависит от закрытия blocker-ов"
            md += [f"### Вариант {i}. {ru_label(v['name'])}\n",f"- Оценка: {variant_score}\n",f"- Сложность: {v['complexity']}\n",f"- Задержка: {v['latency']}\n",f"- Надёжность: {v['reliability']}\n",'- Паттерны:\n',bullet(ru_list(v['patterns'])),'- Почему:\n',bullet(v['why']),'- Риски:\n',bullet(v['risks'])]
        md += ['## 14. Выбранные паттерны и контроли\n']
        for p in [x for x in patterns if x['score']>=30]: md += [f"### {ru_label(p['name'])} — оценка {p['score']}\n",'- Почему:\n',bullet(p['why']),'- Контроли:\n',bullet(p['controls']),'- Риски:\n',bullet(p['risks'])]
        md += ['## 15. Anti-pattern checker\n']
        if not anti: md.append('Критичных anti-patterns не обнаружено.\n')
        for a in anti: md.append(f"- **{a['severity'].upper()} — {a['title']}**: {a['why']} Исправление: {a['fix']}\n")
        md += ['## 16. Матрица систем\n']
        for s in c['systems']: md.append(f"- **{s.get('name')}** — role: {s.get('role')}; owner: {s.get('owner')}; criticality: {s.get('criticality')}; channel: {s.get('channel')}; blocking: {s.get('blocking')}; SLA: {s.get('sla')}\n")
        md += ['## 17. Многоуровневая матрица шагов\n']
        for s in c['steps']: md.append(f"- level {s.get('level')} / order {s.get('order')} / parent {s.get('parent')}: **{s.get('step')}** → {s.get('system')} via {s.get('channel')}; timeout={s.get('timeout')}; retry={s.get('retry')}; compensation={s.get('compensation')}; owner={s.get('owner')}\n")
        md.append(service_chain_markdown(c, db))
        for title,key in [('## 18. Компонентная диаграмма','component'),('## 19. Последовательность основного сценария','happy'),('## 20. Последовательность ошибки / retry / DLQ','error'),('## 21. Последовательность компенсации','compensation')]: md += [title+'\n','```mermaid\n',diagrams[key],'\n```\n']
        md += ['## 22. Основной сценарий\n',numbered(scenarios['main']),'## 23. Альтернативные сценарии и ошибки\n']
        for title,steps in scenarios['alternatives'].items(): md += [f"### {title}\n",numbered(steps)]
        md += ['### Общий путь обработки ошибки\n',numbered(scenarios['error_path'])]
        if scenarios['compensation_path']: md += ['### Путь компенсации\n',numbered(scenarios['compensation_path'])]
        md += ['## 24. Контракты\n']
        for k,items in contracts.items(): md += [f"### {k.upper()}\n",bullet(items)]
        md += ['## 25. БД и хранение\n','### Storage\n',bullet(db['storage']),'### Таблицы\n']
        if db.get('target_only'): md.append('**Важно:** сценарий неинвазивный; таблицы описывают локальную проекцию/целевой контур, а не изменение source system.\n')
        for tab in db['tables']:
            md += [f"#### {tab['name']}\n",f"Назначение: {tab['purpose']}\n",'Поля:\n',bullet([f"{n} {s}" for n,s in tab['fields']]),'Индексы:\n',bullet(tab.get('indexes',[]))]
        md += ['### Partitioning / capacity\n',bullet(db['partitioning']),'### Retention\n',bullet(db['retention']),'## 26. Draft SQL DDL\n','```sql\n',db['ddl'],'\n```\n']
        md += ['## 27. Бэклог\n',bullet(life['backlog']),'## 28. ADR\n']
        if rec.get('blocked'):
            md += ['Архитектурный ADR не формируется: входные данные недостаточны. Используйте ADR-DRAFT из раздела 10 как список вопросов.\n']
        else:
            for a in life['adr']: md += [f"### {a['title']}\n",f"- Решение: {a['decision']}\n",f"- Последствия: {a['consequences']}\n"]
        md += ['## 29. Стратегия тестирования\n',bullet(life['tests']),'## 30. План внедрения\n',bullet(life['rollout']),'## 31. Критерии приёмки\n',bullet(life['acceptance'])]
        return '\n'.join(md)


# ---------- audit existing solution ----------
class SolutionAuditor:
    """Аудит существующей интеграционной архитектуры без LLM.
    Входы приводятся к Integration Graph: systems + integrations + steps + errors + problems.
    """
    def audit(self, f):
        graph = self.build_graph(f)
        patterns = self.detect_patterns(graph, f)
        findings = self.findings(graph, f, patterns)
        scores = self.scores(graph, findings, f)
        improvements = self.improvements(graph, findings, scores, f)
        diagrams = self.audit_diagrams(graph, patterns)
        readiness = self.audit_readiness(graph, findings, f)
        verdict = self.verdict(scores['overall'])
        target = self.target_architecture(graph, findings, f, patterns)
        md = self.markdown(f, graph, patterns, findings, scores, improvements, diagrams, readiness, verdict, target)
        recommended = {'name': f"Вердикт аудита: {verdict['level']} / {scores['overall']}%", 'patterns': [p['name'] for p in patterns], 'pattern_ids': [p['id'] for p in patterns], 'score': scores['overall']}
        variants = [
            {'name':'Минимальные правки', 'score': improvements['minimal_score'], 'complexity':'Низкая', 'patterns':[], 'pattern_ids':[], 'why':['Быстро снижает ключевые production-риски.'], 'latency':'Без изменения flow', 'reliability':'Средняя', 'risks':['Не устраняет архитектурные причины полностью.']},
            {'name':'Production-ready доработка', 'score': improvements['production_score'], 'complexity':'Средняя', 'patterns':[], 'pattern_ids':[], 'why':['Добавляет недостающие контроли надёжности и эксплуатации.'], 'latency':'Обычно без ухудшения', 'reliability':'Высокая', 'risks':['Нужны изменения БД/контрактов/эксплуатации.']},
            {'name':'Целевая архитектура', 'score': improvements['target_score'], 'complexity':'Высокая', 'patterns':[], 'pattern_ids':[], 'why':['Устраняет системные ограничения текущего решения.'], 'latency':'Оптимизируется под требования', 'reliability':'Высокая', 'risks':['Нужна миграция и parallel run.']},
        ]
        return {'ctx':graph, 'traits':{}, 'patterns':patterns, 'variants':variants, 'recommended':recommended, 'anti_patterns':findings, 'db':{}, 'contracts':{}, 'scenarios':{}, 'diagrams':diagrams, 'lifecycle':improvements, 'readiness':readiness, 'markdown':md}

    def yes(self, x): return str(x).strip().lower() in ['yes','y','true','да','1','blocking']
    def no(self, x): return str(x).strip().lower() in ['no','n','false','нет','0','']

    def build_graph(self, f):
        # Audit mode may be called directly with only task_type. Keep a deterministic demo graph for smoke/regression,
        # but do not leak this demo data into ordinary architecture generation defaults.
        if not str(f.get('current_systems_matrix','')).strip() and not str(f.get('current_integration_matrix','')).strip():
            f=dict(f)
            f.setdefault('current_controls', ['timeout','retry','monitoring'])
            f['current_systems_matrix']='''order_api | Order API | service | Product | critical | limited | yes
scoring | Scoring | external_system | Risk | critical | limited | no
crm | CRM | external_system | CRM | important | limited | no
dwh | DWH | analytics | Data | important | no | no'''
            f['current_integration_matrix']='''frontend | order_api | REST | sync | yes | application_request | 3s | no | 0 | no | yes | user_token | Product
order_api | scoring | REST | sync | yes | application_data | 5s | yes | 3 | no | no | mTLS | Risk
order_api | kafka | Kafka | async | no | ApplicationStatusChanged | n/a | yes | 10 | no | no | service_auth | Platform
kafka_consumer | crm | REST | async | no | application_status | 10s | yes | 3 | no | no | service_auth | CRM
order_db | dwh | CDC | async | no | application_data | 15m | yes | 5 | no | yes | service_auth | Data'''
            f['current_process_steps']='''1 | root | 1 | Создать заявку | frontend | order_api | REST | yes | CREATED | VALIDATION_ERROR | none | no
1 | root | 2 | Выполнить скоринг | order_api | scoring | REST | yes | APPROVED/REJECTED | SCORING_ERROR | mark_error | yes
1 | root | 3 | Опубликовать статус event | order_api | kafka | Kafka | no | EVENT_SENT | EVENT_LOST | retry | yes
2 | 3 | 4 | Обновить CRM | kafka_consumer | crm | REST | no | CRM_UPDATED | CRM_ERROR | dlq/manual | yes
2 | 3 | 5 | Выгрузить в DWH | order_db | dwh | CDC | no | DWH_EXPORTED | DWH_ERROR | reconciliation | yes'''
            f['current_error_matrix']='''scoring_timeout | scoring | technical | yes | yes | manual_task | no | Risk | yes
kafka_publish_error | order_api | technical | no | yes | log_only | no | Platform | no
crm_error | crm | technical | no | yes | log_only | no | CRM | no
dwh_lag | dwh | data | no | yes | reconciliation | no | Data | yes'''
            f['current_problem_matrix']='''stuck_status | scoring | daily | заявки зависают в обработке | support ticket
duplicates | crm | weekly | дубли статусов в CRM | manual cleanup
lost_event | order_api_to_kafka | monthly | DWH/CRM не видят часть изменений | manual reload
slow_response | frontend | daily | плохой UX при долгом скоринге | retry by user'''
        systems = parse_matrix(f.get('current_systems_matrix',''), ['system_id','name','type','owner','criticality','can_change','source_of_truth','owned_entity'])
        integrations = parse_matrix(f.get('current_integration_matrix',''), ['from','to','channel','mode','blocking','data','timeout','retry','retry_limit','dlq','idempotency','auth','owner','evidence'])
        steps = parse_matrix(f.get('current_process_steps',''), ['level','parent','order','step','system','target','channel','blocking','success_status','error_status','compensation','manual_recovery'])
        errors = parse_matrix(f.get('current_error_matrix',''), ['error','where','type','blocking','retry','after_retry','dlq','owner','alert'])
        problems = parse_matrix(f.get('current_problem_matrix',''), ['problem','where','frequency','impact','current_workaround'])
        controls = set(f.get('current_controls', []))
        sys_ids = {s.get('system_id') for s in systems if s.get('system_id')}
        return {'systems':systems, 'integrations':integrations, 'steps':steps, 'errors':errors, 'problems':problems, 'controls':controls, 'system_ids':sys_ids}

    def detect_patterns(self, g, f):
        channels = ' '.join(i.get('channel','') for i in g['integrations'] + g['steps']).lower()
        pats=[]
        def add(id,name,why): pats.append({'id':id,'name':name,'why':why})
        if 'rest' in channels or 'http' in channels: add('rest_sync','REST/API integration','Есть REST/HTTP связи.')
        if any(i.get('mode','').lower()=='sync' for i in g['integrations']): add('sync_chain','Synchronous chain','Есть синхронные вызовы.')
        if 'kafka' in channels or 'event' in channels: add('event_streaming','Event streaming','Есть события/Kafka/event channel.')
        if 'queue' in channels or 'rabbit' in channels or 'sqs' in channels: add('queue_worker','Queue/worker flow','Есть очереди/worker flow.')
        if 'cdc' in channels: add('cdc','CDC/Data replication','Есть CDC поток.')
        if 'etl' in channels or 'dwh' in channels: add('dwh_pipeline','DWH/ETL pipeline','Есть аналитический контур.')
        if 'sftp' in channels or 'file' in channels: add('file_exchange','File exchange','Есть файловый обмен.')
        if 'soap' in channels: add('soap_legacy','SOAP/legacy','Есть SOAP/legacy связь.')
        parents=[s.get('parent') for s in g['steps']]
        if len(g['steps'])>=4: add('e2e_process','E2E process','Есть несколько бизнес-шагов.')
        if any(',' in p for p in parents): add('fan_in','Fan-in/join','Есть join/fan-in шаг.')
        parent_counts={}
        for p in parents: parent_counts[p]=parent_counts.get(p,0)+1
        if any(v>=2 and k not in ['','root','-'] for k,v in parent_counts.items()): add('fan_out','Fan-out','Есть несколько дочерних шагов от одного parent.')
        if 'outbox' in g['controls']: add('outbox','Transactional Outbox','Указан Outbox.')
        if 'inbox' in g['controls']: add('inbox','Inbox/idempotent consumer','Указан Inbox/idempotency.')
        return pats

    def findings(self, g, f, patterns):
        out=[]
        def add(id,title,severity,category,where,why,fix): out.append({'id':id,'title':title,'severity':severity,'category':category,'where':where,'why':why,'fix':fix})
        controls=g['controls']; ints=g['integrations']; steps=g['steps']; errors=g['errors']; systems=g['systems']
        system_ids=g['system_ids']
        # graph quality
        for i in ints:
            infra_aliases={'db','database','postgres','oracle','kafka','broker','rabbit','rabbitmq','queue','sqs','dwh','data_lake','etl','cdc'}
            if i.get('from') and i.get('from') not in system_ids and i.get('from') not in infra_aliases:
                add('unknown_source','Связь с неизвестной source-системой','medium','model',i.get('from'), 'В матрице связей есть source, которого нет в матрице систем.', 'Добавить систему или явно описать технический узел/адаптер в матрице систем.')
            if i.get('to') and i.get('to') not in system_ids and i.get('to') not in infra_aliases:
                add('unknown_target','Связь с неизвестной target-системой','medium','model',i.get('to'), 'В матрице связей есть target, которого нет в матрице систем.', 'Добавить систему или явно описать технический узел/адаптер в матрице систем.')
        orders=[s.get('order') for s in steps if s.get('order')]
        if len(orders)!=len(set(orders)): add('duplicate_step_order','Дубли order в шагах','high','model','process_steps','Невозможно однозначно восстановить последовательность процесса.','Сделать order уникальным или явно описать parallel branch.')
        order_set=set(orders)
        for s in steps:
            p=s.get('parent')
            if p and p not in ['root','-','']:
                for pp in [x.strip() for x in p.split(',')]:
                    if pp not in order_set:
                        add('broken_parent_reference','Некорректная parent-ссылка','high','model',s.get('step'),f'parent={pp} не ссылается на существующий order.','Исправить parent/order в матрице шагов.')
        # reliability
        if any(i.get('channel','').lower() in ['kafka','event'] and self.no(i.get('dlq')) for i in ints):
            add('event_without_dlq','Event/Kafka связь без DLQ','high','reliability','event stream','При ошибке consumer-а сообщения могут зависать или теряться без явного recovery.', 'Добавить retry topic/DLQ, owner и dashboard.')
        if any(self.yes(i.get('retry')) and self.no(i.get('dlq')) and self.no(i.get('idempotency')) for i in ints):
            add('retry_without_dlq_idempotency','Retry без DLQ и idempotency','critical','reliability','integration matrix','Retry может создавать дубли, а после исчерпания попыток нет управляемого recovery.', 'Добавить idempotency key, retry limit, DLQ/manual recovery.')
        if any(i.get('channel','').lower() in ['kafka','event'] for i in ints) and 'outbox' not in controls:
            add('db_event_without_outbox','Публикация события без Outbox','critical','consistency','DB + event publish','Если бизнес-данные сохранены, а событие не ушло, downstream потеряет изменение.', 'Добавить Transactional Outbox или CDC from outbox/source table.')
        if any(i.get('mode','').lower()=='async' and self.no(i.get('idempotency')) for i in ints):
            add('async_without_idempotency','Async consumer без idempotency','high','consistency','async consumers','At-least-once доставка почти всегда означает повторы.', 'Добавить Inbox/message registry/business idempotency key.')
        if any(i.get('timeout','').strip().lower() in ['','n/a','none'] and i.get('mode','').lower()=='sync' and i.get('channel','').lower() not in ['sql','db','database'] for i in ints):
            add('sync_without_timeout','Синхронная связь без timeout','critical','reliability','sync API','Без timeout возможны зависания потоков и каскадная деградация.', 'Задать timeout, circuit breaker и fallback/error status.')
        sync_blocking=sum(1 for i in ints if i.get('mode','').lower()=='sync' and self.yes(i.get('blocking')))
        if sync_blocking>=3:
            add('long_sync_chain','Длинная синхронная blocking-цепочка','critical','scalability','sync chain','Latency и доступность становятся произведением доступности всех систем.', 'Вернуть trackingId быстро, дальше queue/orchestrator/status polling.')
        # consistency/data ownership
        writers=[s for s in systems if str(s.get('source_of_truth','')).lower() in ['yes','true','да','1']]
        entity_owners={}
        for w in writers:
            ent=(w.get('owned_entity') or 'общая сущность').strip().lower()
            entity_owners.setdefault(ent,[]).append(w)
        conflicts={ent:ws for ent,ws in entity_owners.items() if len(ws)>1}
        if conflicts:
            where=', '.join(f'{ent}: '+','.join(x.get('system_id','') for x in ws) for ent,ws in conflicts.items())
            add('multiple_sources_of_truth','Несколько source of truth для одной сущности','critical','consistency',where,'Несколько владельцев истины для одной сущности создают конфликты данных.', 'Назначить один SoT по сущности или описать field-level ownership.')
        if any(i.get('channel','').lower() in ['sql','db','direct_db_write'] for i in ints):
            add('direct_db_access','Прямой DB access между системами','high','consistency','DB access','Ломает инкапсуляцию данных и контракт владения.', 'Заменить на API/event/CDC read-only.')
        # observability
        if 'correlation_id' not in controls:
            add('no_correlation_id','Нет CorrelationId','high','observability','all flow','Трудно расследовать E2E ошибки.', 'Протащить CorrelationId через API/events/logs.')
        if 'tracing' not in controls and sync_blocking>=2:
            add('no_tracing_for_chain','Нет tracing для цепочки','medium','observability','sync/e2e','Сложно понять, где latency и ошибка.', 'Добавить distributed tracing.')
        if 'business_metrics' not in controls:
            add('no_business_metrics','Нет бизнес-метрик процесса','medium','observability','process','Технические логи не показывают зависшие заявки и SLA процесса.', 'Добавить метрики по статусам, stuck processes, DLQ, retry exhaustion.')
        if any(e.get('after_retry','').lower() in ['log_only','logs','только лог'] for e in errors):
            add('log_only_error_handling','Ошибка после retry уходит только в лог','high','operations','error handling','Логи не являются recovery-механизмом.', 'Добавить DLQ/manual task/alert и owner.')
        if any(self.no(e.get('owner')) for e in errors):
            add('error_without_owner','Ошибка без owner','high','operations','error matrix','Без владельца ошибка не будет стабильно разбираться.', 'Назначить owner для каждого класса ошибок.')
        # contracts/security/highload
        if 'contract_tests' not in controls:
            add('no_contract_tests','Нет contract tests','medium','maintainability','contracts','Изменения API/events могут ломать потребителей.', 'Добавить OpenAPI/AsyncAPI + contract tests.')
        if any(i.get('channel','').lower() in ['kafka','event'] for i in ints) and 'schema_registry' not in controls:
            add('no_schema_registry','События без schema registry/versioning','high','maintainability','events','Риск несовместимых изменений event payload.', 'Добавить schema registry или строгие versioned schemas.')
        rps=safe_int(f.get('rps'),0); peak=safe_int(f.get('peak_factor'),1)
        if rps>=300 or peak>=5 or f.get('load_profile') in ['highload','bursty']:
            if 'rate_limit' not in controls: add('highload_no_rate_limit','Highload без rate limit','high','scalability','edge/services','Пики могут перегрузить downstream.', 'Добавить rate limits/backpressure/quotas.')
            if 'circuit_breaker' not in controls: add('highload_no_circuit_breaker','Highload без circuit breaker','high','reliability','external calls','Нестабильная система может вызвать каскадный отказ.', 'Добавить circuit breaker/bulkheads/fallback.')
        if f.get('sensitivity') in ['pii','financial','high']:
            if any(i.get('auth','').strip().lower() in ['','none','no'] for i in ints):
                add('sensitive_without_auth','Есть чувствительные данные и связь без auth','critical','security','integration matrix','Риск несанкционированного доступа.', 'Определить auth/mTLS/token scopes для каждой связи.')
        # known problems amplify
        for p in g['problems']:
            name=p.get('problem','').lower()
            sev='high' if p.get('frequency','').lower() in ['daily','ежедневно','часто'] else 'medium'
            if any(x in name for x in ['lost','потер','lost_event']):
                add('observed_lost_events','Уже наблюдается потеря событий','critical','production_problem',p.get('where'),p.get('impact'),'Приоритетно внедрить outbox/CDC/replay/reconciliation.')
            elif any(x in name for x in ['duplicate','дубли']):
                add('observed_duplicates','Уже наблюдаются дубли','high','production_problem',p.get('where'),p.get('impact'),'Добавить idempotency/inbox/unique business key.')
            elif any(x in name for x in ['stuck','завис']):
                add('observed_stuck_status','Уже наблюдаются зависшие статусы','high','production_problem',p.get('where'),p.get('impact'),'Добавить явную историю шагов процесса, stuck alerts, manual recovery.')
        return out

    def scores(self, g, findings, f):
        weights={'critical':18,'high':10,'medium':5,'low':2}
        cats=['reliability','consistency','scalability','observability','security','maintainability','operations','model']
        scores={}
        for cat in cats:
            penalty=sum(weights.get(x['severity'],3) for x in findings if x['category']==cat)
            scores[cat]=max(0,100-penalty)
        controls=g.get('controls', set())
        if f.get('sensitivity') in ['pii','financial','high'] and not any(i.get('auth','').strip() for i in g.get('integrations', [])):
            scores['security']=min(scores['security'],60)
        if f.get('sensitivity') in ['pii','financial','high'] and not {'correlation_id','tracing'}.intersection(controls):
            scores['observability']=min(scores['observability'],65)
        if 'business_metrics' not in controls:
            scores['observability']=min(scores['observability'],75)
        ids={x.get('id') for x in findings}
        critical_count=sum(1 for x in findings if x.get('severity')=='critical')
        high_count=sum(1 for x in findings if x.get('severity')=='high')
        if ids.intersection({'db_event_without_outbox','observed_lost_events'}):
            scores['consistency']=min(scores['consistency'],50)
            scores['reliability']=min(scores['reliability'],60)
        if ids.intersection({'async_without_idempotency','observed_duplicates'}):
            scores['reliability']=min(scores['reliability'],60)
            scores['consistency']=min(scores['consistency'],60)
        if ids.intersection({'observed_stuck_status','log_only_error_handling'}):
            scores['operations']=min(scores['operations'],55)
            scores['operational_readiness']=min(scores.get('operational_readiness',100),50)
        if ids.intersection({'no_correlation_id','no_business_metrics'}):
            scores['observability']=min(scores['observability'],60)
        if critical_count:
            scores['reliability']=min(scores['reliability'],55)
            scores['operations']=min(scores['operations'],55)
        prod_penalty=sum(weights.get(x['severity'],3) for x in findings if x['category']=='production_problem')
        scores['operational_readiness']=max(0, min(scores.get('operational_readiness',100), scores['operations'], scores['observability']) - prod_penalty//2)
        main_cats=['reliability','consistency','scalability','observability','security','maintainability','operational_readiness']
        scores['overall']=max(0, round(sum(scores[c] for c in main_cats)/len(main_cats) - prod_penalty//4))
        # Hard caps: audit verdict must not be GREEN when critical/high production risks exist.
        critical_count=sum(1 for x in findings if x.get('severity')=='critical')
        high_count=sum(1 for x in findings if x.get('severity')=='high')
        if critical_count:
            scores['overall']=min(scores['overall'], 55 if critical_count>=2 else 59)
        elif high_count>=3:
            scores['overall']=min(scores['overall'], 69)
        elif high_count:
            scores['overall']=min(scores['overall'], 79)
        return scores

    def verdict(self, score):
        if score>=80: return {'level':'GREEN','text':'решение выглядит устойчивым, нужны точечные улучшения'}
        if score>=60: return {'level':'YELLOW','text':'решение можно использовать, но есть production-риски'}
        return {'level':'RED','text':'решение рискованно для production, нужны доработки'}

    def improvements(self, g, findings, scores, f):
        minimal=[]; production=[]; target=[]
        ids={x['id'] for x in findings}
        def add(lst, item):
            if item not in lst: lst.append(item)
        if 'sync_without_timeout' in ids: add(minimal,'Задать timeout для всех sync-вызовов.')
        if 'no_correlation_id' in ids: add(minimal,'Протащить CorrelationId через API/events/logs.')
        if 'retry_without_dlq_idempotency' in ids or 'event_without_dlq' in ids: add(minimal,'Добавить retry limit, DLQ/retry topic, owner и alert.')
        if 'log_only_error_handling' in ids: add(minimal,'Заменить log-only after_retry на DLQ/manual task/alert.')
        if 'highload_no_rate_limit' in ids: add(minimal,'Добавить rate limit/backpressure на входе и перед downstream.')
        if 'highload_no_circuit_breaker' in ids: add(minimal,'Добавить circuit breaker/bulkhead для внешних и нестабильных вызовов.')
        if not minimal: minimal=['Зафиксировать текущие контракты и владельцев ошибок.', 'Добавить недостающие SLA/timeout/owner в матрицу.']

        if 'db_event_without_outbox' in ids: add(production,'Внедрить Transactional Outbox + publisher + stuck-event monitoring.')
        if 'async_without_idempotency' in ids or 'observed_duplicates' in ids: add(production,'Внедрить Inbox/idempotent consumer и unique business keys.')
        if 'observed_stuck_status' in ids: add(production,'Добавить process_steps, integration_attempts, stuck-status alerts и manual recovery dashboard.')
        if 'no_schema_registry' in ids: add(production,'Ввести schema registry/versioned event schemas.')
        if 'no_contract_tests' in ids: add(production,'Добавить OpenAPI/AsyncAPI и consumer-driven contract tests.')
        if 'observed_lost_events' in ids: add(production,'Добавить replay/reconciliation flow для потерянных событий.')
        if not production: production=['Добавить эксплуатационные метрики, contract tests и recovery runbook.']

        if 'long_sync_chain' in ids: add(target,'Перевести online flow в async acceptance: API возвращает trackingId, далее Process Manager/Queue/Saga.')
        if 'multiple_sources_of_truth' in ids: add(target,'Переразделить ownership: один source of truth или field-level ownership с событиями изменений.')
        if 'direct_db_access' in ids: add(target,'Убрать прямой DB access: заменить на API/events/CDC read-only.')
        if any(x in ids for x in ['db_event_without_outbox','async_without_idempotency','observed_stuck_status']): add(target,'Целевая архитектура: Orchestrator/Saga + Outbox + Inbox + process_steps + integration_attempts.')
        if f.get('dwh')!='no': add(target,'DWH подключать non-blocking через CDC/ETL с reconciliation и data quality checks.')
        if not target: target=['Сохранить текущий стиль архитектуры, усилить контракты, observability и recovery.']
        return {'minimal':minimal,'production':production,'target':target,'minimal_score':min(100,scores['overall']+12),'production_score':min(100,scores['overall']+25),'target_score':min(100,scores['overall']+35)}

    def target_architecture(self, g, findings, f, patterns):
        ids={x['id'] for x in findings}; out=[]
        if 'long_sync_chain' in ids:
            out += ['API Gateway/Service принимает команду и быстро возвращает trackingId.', 'Дальнейшая обработка уходит в Queue/Process Manager.', 'Клиент получает результат через GET status/callback/notification.']
        if any(x in ids for x in ['db_event_without_outbox','observed_lost_events']):
            out += ['Бизнес-изменение и outbox_event сохраняются в одной транзакции.', 'Publisher публикует событие в Kafka и повторяет при сбоях.', 'Stuck outbox контролируется алертами.']
        if any(x in ids for x in ['async_without_idempotency','observed_duplicates']):
            out += ['Каждый consumer использует Inbox/message registry.', 'Повторные сообщения не выполняют бизнес-операцию повторно.']
        if 'observed_stuck_status' in ids:
            out += ['Process Manager ведёт process_steps и integration_attempts.', 'Manual recovery task создаётся после retry exhaustion.']
        if f.get('dwh')!='no': out += ['DWH получает данные non-blocking через CDC/ETL.', 'Сверка выполняется через reconciliation_runs.']
        return out or ['Текущая архитектура может быть сохранена, если закрыть найденные контроли.']

    def audit_readiness(self, g, findings, f):
        gaps=[]
        if not g['systems']: gaps.append('Не заполнена матрица текущих систем.')
        if not g['integrations']: gaps.append('Не заполнена матрица текущих связей.')
        if f.get('audit_depth') in ['normal','deep'] and not g['steps']: gaps.append('Для normal/deep аудита нужна матрица шагов процесса.')
        if f.get('audit_depth')=='deep' and not g['errors']: gaps.append('Для deep аудита нужна матрица ошибок.')
        if any(x['severity']=='critical' for x in findings): gaps.append('Есть critical findings — решение требует доработки перед production/масштабированием.')
        score=max(0, 100-len(gaps)*12-len([x for x in findings if x['severity']=='critical'])*8-len([x for x in findings if x['severity']=='high'])*3)
        return {'score':score,'gaps':gaps}

    def audit_diagrams(self, g, patterns):
        lines=['flowchart LR']
        for s in g['systems']:
            sid=snake(s.get('system_id') or s.get('name'))
            name=s.get('name') or s.get('system_id')
            typ=s.get('type','system')
            shape='[{}]'
            if typ in ['database','db','analytics']: shape='[({})]'
            elif typ in ['broker','queue']: shape='[{{{}}}]'
            lines.append(f'    {sid}{shape.format(name)}')
        for i in g['integrations']:
            a=snake(i.get('from')); b=snake(i.get('to'))
            label=f"{i.get('channel')}/{i.get('mode')}"
            lines.append(f'    {a} -->|{label}| {b}')
        seq=['sequenceDiagram']
        participants=[]
        for s in g['systems'][:8]:
            sid=snake(s.get('system_id') or s.get('name')); participants.append(sid); seq.append(f'    participant {sid} as {s.get("name") or sid}')
        for i in g['integrations'][:12]:
            a=snake(i.get('from')); b=snake(i.get('to')); arrow='->>' if i.get('mode','').lower()=='sync' else '-->>'
            seq.append(f'    {a}{arrow}{b}: {i.get("channel")} {i.get("data")}')
        return {'component':'\n'.join(lines), 'happy':'\n'.join(seq), 'error':'sequenceDiagram\n    participant S as Service\n    participant T as Target\n    participant D as DLQ/Manual recovery\n    S->>T: call/message\n    T-->>S: timeout/error\n    S->>S: retry with backoff\n    S->>D: after retry exhausted', 'compensation':'sequenceDiagram\n    participant P as Process Manager\n    participant S as Step\n    participant M as Manual recovery\n    S-->>P: failed\n    P->>P: evaluate compensation\n    P->>M: create task if automatic compensation impossible'}

    def markdown(self, f, g, patterns, findings, scores, imp, diagrams, readiness, verdict, target):
        md=[]
        project = f.get('project_name') or 'Текущее интеграционное решение'
        high = [x for x in findings if x.get('severity') in ['critical','high']]
        main_problem = high[0]['title'] if high else 'критичных проблем не найдено, но контроли нужно подтвердить документами и тестами'
        can_dev = 'нет, сначала закрыть critical/high findings' if high else 'можно планировать доработки после проверки контрактов и владельцев'
        next_step = high[0]['fix'] if high else 'зафиксировать текущие контроли, добавить проверочные тесты и оформить ADR по целевому варианту'
        md += [f"# Аудит текущего интеграционного решения: {project}\n", f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n", '---\n']
        md += ['## 0. Читаемый вывод\n']
        md += ['### Что проектируем / проверяем\n', 'Проверяется уже существующая интеграционная цепочка: какие системы связаны, где есть синхронные/асинхронные вызовы, какие контроли заявлены и где возможны потери, дубли, зависшие статусы или ручные исправления.\n']
        md += ['### Что делать\n', f"Сначала разобрать текущую цепочку по шагам, затем закрыть самые опасные места. Главный практический шаг: **{next_step}**.\n"]
        md += ['### Почему именно так\n', 'Аудит текущего решения должен не просто назвать паттерны, а показать, где именно в цепочке возникает риск: при приёме запроса, публикации события, обработке consumer-ом, ошибке внешней системы, DLQ/reprocess или ручном восстановлении.\n']
        md += ['### Главные ограничения и риски\n', f"Основной риск: **{main_problem}**. Если его не закрыть, решение может работать на happy path, но ломаться при retry, дублях, потере события, лаге consumer-а или ручном восстановлении.\n"]
        md += ['### Можно ли идти в разработку\n', f"{can_dev}. Итоговая оценка: **{scores['overall']} / 100**, готовность входных данных: **{readiness['score']}%**.\n"]
        md += ['### Следующий практический шаг\n', f"{next_step}. После этого обновить ADR, тест-кейсы и план rollout/rollback.\n"]
        if str(f.get('report_detail','')) == 'human':
            md += ['## 1. Что система поняла\n', f"- Вердикт: {verdict['level']} — {verdict['text']}\n", f"- Систем описано: {len(g.get('systems', []))}\n", f"- Связей описано: {len(g.get('integrations', []))}\n", f"- Найдено проблем: {len(findings)}\n"]
            md += ['## 2. Текущая цепочка простыми словами\n']
            if g.get('integrations'):
                for idx,i in enumerate(g['integrations'][:12],1):
                    md.append(f"{idx}. **{i.get('from')} → {i.get('to')}**: канал {i.get('channel')}, режим {i.get('mode')}. Что проверить: timeout, retry, idempotency, owner и восстановление при ошибке.\n")
            else:
                md.append('Связи не описаны. Добавьте карточками: кто кого вызывает, канал, sync/async, retry, DLQ, idempotency и owner.\n')
            md += ['## 3. Что исправить первым\n']
            for x in findings[:8]:
                md += [f"### {x['severity'].upper()} — {x['title']}\n", f"Что сделать: {x['fix']}\n", f"Почему: {x['why']}\n"]
            if not findings:
                md.append('Критичных проблем не найдено. Подтвердите это тестами: дубли, timeout, retry, DLQ/reprocess, rollback и отсутствие ПДн в логах.\n')
            md += ['## 4. Что нельзя делать\n', bullet(['Не считать happy path доказательством production-ready.', 'Не делать retry команд без idempotency.', 'Не оставлять DLQ без owner, retention и reprocess policy.', 'Не блокировать клиентский процесс DWH/аналитикой.', 'Не скрывать workaround как целевую архитектуру.'])]
            md += ['## 5. Тест-кейсы\n', bullet(['Повторный запрос/событие не создаёт дубль.', 'Timeout внешней системы приводит к понятному статусу и recovery.', 'Consumer падает до ack — повторная обработка безопасна.', 'DLQ/reprocess не создаёт дубль.', 'Rollback/feature toggle проверены.'])]
            md += ['## 6. Expert appendix скрыт\n', 'Полные матрицы и технический экспорт доступны только в экспертном режиме.\n']
            return '\n'.join(md)
        md += ['## 1. Краткий вывод\n', f"**Вердикт:** {verdict['level']} — {verdict['text']}\n", f"**Итоговая оценка:** {scores['overall']} / 100\n", f"**Готовность входных данных:** {readiness['score']}%\n", '## 1A. Оценки по направлениям\n']
        for k,v in scores.items(): md.append(f'- {SCORE_LABELS.get(k,k)}: {v}/100\n')
        md += ['## 1B. Что система поняла из ввода\n']
        md += [f"- Систем описано: {len(g.get('systems', []))}\n", f"- Связей описано: {len(g.get('integrations', []))}\n", f"- Шагов процесса описано: {len(g.get('steps', []))}\n", f"- Ошибок описано: {len(g.get('errors', []))}\n", f"- Найдено проблем: {len(findings)}\n", f"- Вердикт: {verdict['level']} — {verdict['text']}\n"]
        if readiness['gaps']: md += ['### Что мешает точной оценке\n', bullet(readiness['gaps'])]
        md += ['## 2. Построенная текущая цепочка\n']
        if g.get('integrations'):
            for idx,i in enumerate(g['integrations'],1):
                md.append(f"{idx}. **{i.get('from')} → {i.get('to')}**: канал {i.get('channel')}, режим {i.get('mode')}, blocking={i.get('blocking')}, retry={i.get('retry')}, DLQ={i.get('dlq')}, idempotency={i.get('idempotency')}, timeout={i.get('timeout')}, owner={i.get('owner')}.\n")
        else:
            md.append('Связи не описаны. Для полезного аудита нужно добавить хотя бы связи между системами: кто кого вызывает, канал, sync/async, retry, DLQ, idempotency и owner.\n')
        md += ['## 2A. Схема потоков и переходов\n', 'Схема показывает поток текущего решения, а не набор терминов. По ней нужно проверять, где основной путь, где ошибка, retry, DLQ и компенсация.\n', '```mermaid\n', diagrams.get('component',''), '\n```\n', '### Последовательность happy path\n', '```mermaid\n', diagrams.get('happy',''), '\n```\n']
        md += ['## 3. Что делать по проблемам и почему\n']
        if not findings:
            md.append('Критичных проблем не найдено. Всё равно нужно подтвердить контроли: contract tests, retry/idempotency, monitoring, rollback и owner для ошибок.\n')
        for x in findings:
            md += [f"### {x['severity'].upper()} — {x['title']}\n", f"Где: {x.get('where','не указано')}.\n", f"Что делать: {x['fix']}\n", f"Почему: {x['why']}\n", 'Ограничение: если это нельзя исправить сразу, нужно оформить accepted risk, owner, срок пересмотра и ручной контроль.\n']
        md += ['## 4. Паттерны по местам цепочки, а не набор терминов\n']
        if patterns:
            for ptn in patterns:
                md.append(f"- **{ru_label(ptn['name'])}**: применим там, где в текущей цепочке есть соответствующий риск. Зачем: {ptn['why']}\n")
        else:
            md.append('Паттерны не определены: входных данных недостаточно.\n')
        md += ['## 5. Минимальные правки\n']
        for item in imp['minimal']:
            md += [f"### {item}\n", 'Что сделать: внедрить этот контроль в конкретном месте текущей цепочки и назначить owner.\n', 'Почему: без этого happy path может работать, но сбои будут приводить к дублям, потерям, зависшим статусам или ручным SQL-исправлениям.\n', 'Acceptance criteria: есть тест на сбой, лог/метрика, понятный статус и сценарий восстановления.\n']
        md += ['## 6. Production-ready доработка\n']
        for item in imp['production']:
            md += [f"- Что сделать: {item}\n  Почему: это нужно для эксплуатации, восстановления и безопасного rollout. Риск без этого: команда не увидит деградацию процесса или будет восстанавливать данные вручную.\n"]
        md += ['## 7. Целевая архитектура / лучший вариант\n', bullet(imp['target']), '### Целевой поток\n', bullet(target)]
        md += ['## 8. Ошибки, retry, DLQ и восстановление\n', '```mermaid\n', diagrams.get('error',''), '\n```\n', 'Что проверить: каждая ошибка должна иметь retry limit, owner, алерт, DLQ/manual task или понятный финальный статус.\n']
        md += ['## 9. Компенсация / ручное восстановление\n', '```mermaid\n', diagrams.get('compensation',''), '\n```\n', 'Что проверить: если есть деньги, лимиты, заказ или заявка, компенсация должна иметь owner, audit и сценарий на случай, если компенсация тоже упала.\n']
        md += ['## 10. Что нельзя делать\n', bullet(['Не считать happy path доказательством production-ready.', 'Не делать retry команд без idempotency.', 'Не оставлять DLQ без owner, retention и reprocess policy.', 'Не публиковать критичное событие без outbox/CDC/reconciliation или явно принятого риска.', 'Не блокировать клиентский процесс DWH/аналитикой.', 'Не скрывать workaround как целевую архитектуру.'])]
        md += ['## 11. Что уточнить\n', bullet(readiness.get('gaps') or ['Подтвердить владельцев ошибок, idempotency, rollback, replay/reprocess и метрики эксплуатации.'])]
        md += ['## 12. Тест-кейсы для проверки исправлений\n', bullet(['Happy path текущей цепочки.', 'Повторный запрос/событие не создаёт дубль.', 'Timeout внешней системы приводит к retry/status/manual recovery.', 'Consumer падает до ack — повторная обработка идемпотентна.', 'DLQ/reprocess не создаёт дубль.', 'DWH/аналитика не блокирует клиентский процесс.', 'Rollback/feature toggle проверены.', 'В логах нет ПДн/секретов.'])]
        md += ['## 13. ADR\n', '### Контекст\n', 'Есть текущее интеграционное решение, которое нужно проверить на риски, восстановление, дубли, потерю событий и эксплуатационную готовность.\n', '### Решение\n', 'Исправлять решение поэтапно: сначала минимальные контроли и blockers, затем production-ready доработка, затем целевая архитектура.\n', '### Последствия\n', 'Появятся дополнительные контроли, метрики, тесты и эксплуатационные процедуры, зато решение станет проверяемым и восстанавливаемым.\n']
        md += ['## 14. Expert appendix: матрицы\n', '### Матрица систем\n']
        for s in g['systems']: md.append(f"- {s.get('system_id')} / {s.get('name')}: type={s.get('type')}, owner={s.get('owner')}, criticality={s.get('criticality')}, can_change={s.get('can_change')}, SoT={s.get('source_of_truth')}, owned_entity={s.get('owned_entity','')}\n")
        md += ['### Матрица связей\n']
        for i in g['integrations']: md.append(f"- {i.get('from')} → {i.get('to')}: {i.get('channel')}, {i.get('mode')}, blocking={i.get('blocking')}, retry={i.get('retry')}, dlq={i.get('dlq')}, idempotency={i.get('idempotency')}, timeout={i.get('timeout')}, owner={i.get('owner')}\n")
        md += ['### Уровень подтверждения контролей\n', bullet([f'{ctrl}: заявлено пользователем, требует подтверждения контрактами/DDL/настройками' for ctrl in sorted(g.get('controls', []))] or ['Контроли не указаны.'])]
        return '\n'.join(md)

# ---------- web ----------
HTML="""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>Интеграционный инструктор v5.0.9</title><style>
:root{--bg:#07111f;--panel:#111827;--panel2:#0b1220;--text:#e5e7eb;--muted:#9ca3af;--accent:#22d3ee;--border:#263245}
body{margin:0;background:radial-gradient(circle at top left,#123344 0,#0b1220 38%,#060a12 100%);color:var(--text);font-family:Arial,sans-serif}.wrap{max-width:1280px;margin:0 auto;padding:28px 18px 60px}.card{background:rgba(17,24,39,.94);border:1px solid var(--border);border-radius:18px;padding:22px;margin-bottom:18px;box-shadow:0 18px 50px rgba(0,0,0,.28)}.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:16px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}h1{margin:0 0 10px;font-size:32px}h2{margin:0 0 12px;font-size:21px}h3{margin:22px 0 12px;color:var(--accent);font-size:15px;text-transform:uppercase;letter-spacing:.05em}p,.muted{color:var(--muted);line-height:1.5}label{display:block;color:#cbd5e1;font-size:13px;margin-bottom:6px}input,textarea,select{width:100%;box-sizing:border-box;background:var(--panel2);color:var(--text);border:1px solid var(--border);border-radius:12px;padding:11px 12px}textarea{min-height:112px;resize:vertical}select[multiple]{min-height:120px}.chip-group{display:flex;flex-wrap:wrap;gap:8px}.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);border-radius:999px;background:#0b1220;color:#cbd5e1;padding:8px 10px;font-size:12px;cursor:pointer}.chip input{width:auto}.chip:has(input:checked){border-color:#22d3ee;background:#083344;color:#fff}.warnbox{border:1px solid #854d0e;background:#422006;color:#fde68a;border-radius:14px;padding:12px;margin:12px 0}.dangerbox{border:1px solid #7f1d1d;background:#450a0a;color:#fecaca;border-radius:14px;padding:12px;margin:12px 0}.layer{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:12px;margin:8px 0}.btn{background:linear-gradient(135deg,#06b6d4,#2563eb);color:white;border:0;border-radius:14px;padding:14px 20px;font-weight:700;cursor:pointer;font-size:15px}.btn.secondary{background:#0b1220;border:1px solid var(--border);color:#cbd5e1}.btn.ghost{background:transparent;border:1px solid var(--border);color:#cbd5e1}.pill{display:inline-flex;border:1px solid var(--border);color:#cbd5e1;border-radius:999px;padding:7px 10px;margin:4px;font-size:12px;background:var(--panel2)}.result{white-space:pre-wrap;background:#080d17;border:1px solid var(--border);border-radius:16px;padding:18px;max-height:820px;overflow:auto;line-height:1.45;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px}.score{font-size:42px;font-weight:800;color:var(--accent)}a{color:var(--accent);text-decoration:none}.small{font-size:12px;color:var(--muted)}
.simple-strip{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.simple-step{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:12px}.simple-step b{display:block;color:#fff;margin-bottom:4px}.simple-step span{color:#9ca3af;font-size:12px}.wizard{position:sticky;top:0;z-index:5;background:rgba(7,17,31,.92);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:18px;padding:14px;margin-bottom:16px}.steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.step{border:1px solid var(--border);border-radius:14px;padding:10px 12px;background:var(--panel2);color:#cbd5e1;font-size:13px;cursor:pointer}.step.active{border-color:#22d3ee;background:#083344;color:white}.step.done{border-color:#14532d;color:#bbf7d0}.step b{display:block;font-size:14px}.progress{height:8px;background:#0b1220;border-radius:999px;overflow:hidden;margin-top:12px}.bar{height:100%;width:25%;background:linear-gradient(90deg,#06b6d4,#2563eb);transition:.2s}.mode-help{background:#082f49;border:1px solid #0e7490;color:#dffafe;border-radius:14px;padding:12px 14px;margin-bottom:14px}.mode-help b{color:#fff}.section{background:#0b1220;border:1px solid var(--border);border-radius:16px;margin:12px 0;padding:0}.section summary{cursor:pointer;list-style:none;padding:16px 18px;color:#e5e7eb;font-weight:800;display:flex;gap:10px;align-items:flex-start;justify-content:space-between}.section summary::-webkit-details-marker{display:none}.section summary small{font-weight:400;color:#9ca3af;text-transform:none;letter-spacing:0;max-width:560px;text-align:right}.section .grid{padding:0 18px 18px}.quick{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.quick button{text-align:left}.nav{display:flex;justify-content:space-between;gap:10px;margin-top:18px}.checklist{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.check{border:1px solid var(--border);border-radius:12px;padding:9px 10px;background:#0b1220;font-size:13px}.check.ok{border-color:#14532d;color:#bbf7d0}.check.warn{border-color:#854d0e;color:#fde68a}.beginner-panel{border:1px solid #0e7490;background:linear-gradient(180deg,rgba(8,47,73,.96),rgba(15,23,42,.96));border-radius:18px;padding:18px;margin:16px 0}.beginner-panel h2{margin-bottom:6px}.choice-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.choice-card{border:1px solid var(--border);background:#0b1220;border-radius:16px;padding:13px;cursor:pointer;color:#cbd5e1}.choice-card input{width:auto;margin-right:6px}.choice-card:has(input:checked){border-color:#22d3ee;background:#083344;color:white}.mini-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.form-builder{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.builder-block{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:12px}.builder-block b{display:block;margin-bottom:8px;color:#fff}.hint-card{border:1px dashed #0e7490;background:#082f49;border-radius:14px;padding:12px;color:#dffafe}.textarea-tools{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.field-hint{font-size:12px;color:#93c5fd;margin-top:5px}.simple-only{display:block}.power-mode .simple-only{display:none}.power-toggle{float:right}.section[data-sec='systems'] textarea,.section[data-sec='steps'] textarea,.section[data-sec='delivery'] textarea,.section[data-sec='audit'] textarea{min-height:160px}@media(max-width:900px){.choice-grid,.mini-grid,.form-builder{grid-template-columns:1fr}.power-toggle{float:none;display:block;margin-top:8px}}@media(max-width:900px){.hero,.grid,.quick,.steps,.checklist{grid-template-columns:1fr}.wizard{position:static}}
body:not(.power-mode) .wizard,body:not(.power-mode) .quick,body:not(.power-mode) .checklist,body:not(.power-mode) details.section,body:not(.power-mode) #prevBtn,body:not(.power-mode) #nextBtn{display:none}body:not(.power-mode) #mainForm{max-width:980px;margin-left:auto;margin-right:auto}body:not(.power-mode) .nav{justify-content:center}body:not(.power-mode) #submitBtn{font-size:18px;padding:18px 28px}.power-mode .beginner-panel{display:none}.mode-badge{display:inline-flex;align-items:center;gap:8px;border:1px solid #0e7490;background:#082f49;color:#dffafe;border-radius:999px;padding:8px 12px;font-size:13px}.simple-result-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.simple-result{border:1px solid var(--border);background:#0b1220;border-radius:16px;padding:14px}.simple-result h3{margin-top:0}.todo-list{margin:0;padding-left:18px;line-height:1.5}.report-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}.full-report summary{cursor:pointer;color:#e5e7eb;font-weight:800;padding:14px}.full-report{border:1px solid var(--border);border-radius:16px;background:#0b1220}.full-report .result{border:0;border-top:1px solid var(--border);border-radius:0 0 16px 16px}.advanced-onboarding{display:none;border:1px solid #0e7490;background:linear-gradient(180deg,rgba(8,47,73,.92),rgba(11,18,32,.92));border-radius:18px;padding:16px;margin:14px 0}.power-mode .advanced-onboarding{display:block}.advanced-onboarding h2{margin-bottom:6px}.advanced-rules{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.advanced-rule{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:11px}.advanced-rule b{display:block;color:#fff;margin-bottom:4px}.section-guide{grid-column:1/-1;border:1px dashed #0e7490;background:#082f49;border-radius:14px;padding:12px;color:#dffafe}.section-guide b{color:white}.section-guide ul{margin:8px 0 0 18px;padding:0;line-height:1.45}.power-mode .field{background:rgba(15,23,42,.72);border:1px solid rgba(38,50,69,.85);border-radius:14px;padding:12px}.power-mode .field label{font-size:14px;color:#fff;font-weight:700}.question-tip{font-size:12px;color:#93c5fd;margin:6px 0 0;line-height:1.35}.example-link{display:inline-block;margin-top:6px;color:#67e8f9}.mode-switch-row{display:flex;justify-content:flex-end;margin-bottom:10px}@media(max-width:900px){.advanced-rules{grid-template-columns:1fr}}@media(max-width:900px){.simple-strip,.simple-result-grid{grid-template-columns:1fr}}@media(max-width:900px){.chain-kpis,.chain-grid,.integration-meta{grid-template-columns:1fr}.chain-stage{min-width:86vw;flex-basis:86vw}.chain-stage:not(:last-child)::after{display:none}.chain-track{padding-bottom:4px}}
.ux-dashboard{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}.ux-card{border:1px solid var(--border);border-radius:16px;background:rgba(11,18,32,.78);padding:14px}.ux-card b{color:#fff}.ux-meter{height:10px;background:#0b1220;border:1px solid var(--border);border-radius:999px;overflow:hidden;margin-top:8px}.ux-meter i{display:block;height:100%;width:0;background:linear-gradient(90deg,#22d3ee,#2563eb);transition:.2s}.ux-assistant{display:none;position:sticky;top:92px;z-index:4;border:1px solid #0e7490;background:linear-gradient(180deg,rgba(8,47,73,.96),rgba(11,18,32,.96));border-radius:18px;padding:14px;margin:12px 0}.power-mode .ux-assistant{display:grid;grid-template-columns:1.3fr .7fr;gap:12px}.ux-assistant h3{margin:0 0 8px}.ux-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;justify-content:flex-end}.chain-section-title{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}.chain-subtitle{max-width:760px}.chain-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0}.chain-kpi{background:linear-gradient(180deg,rgba(8,47,73,.92),rgba(11,18,32,.96));border:1px solid rgba(34,211,238,.18);border-radius:16px;padding:14px}.chain-kpi b{display:block;font-size:28px;color:#fff;margin-bottom:4px}.chain-kpi span{font-size:12px;color:#9bdaf2}.chain-hint{border:1px dashed #0e7490;background:#082f49;border-radius:14px;padding:12px;color:#dffafe;margin:12px 0 16px}.chain-viz{border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,rgba(11,18,32,.98),rgba(8,13,23,.98));padding:16px;overflow:hidden}.chain-track{display:flex;gap:14px;overflow-x:auto;padding-bottom:10px;scrollbar-width:thin}.chain-track::-webkit-scrollbar{height:10px}.chain-track::-webkit-scrollbar-thumb{background:#1f3b52;border-radius:999px}.chain-stage{min-width:280px;max-width:320px;position:relative;flex:0 0 300px;border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,rgba(16,24,39,.98),rgba(8,13,23,.98));padding:14px;box-shadow:0 14px 36px rgba(0,0,0,.22)}.chain-stage:not(:last-child)::after{content:'→';position:absolute;right:-17px;top:46%;transform:translateY(-50%);width:30px;height:30px;border-radius:999px;background:#082f49;border:1px solid #0e7490;color:#67e8f9;display:flex;align-items:center;justify-content:center;font-weight:800}.chain-stage-head{display:flex;align-items:flex-start;gap:10px;margin-bottom:10px}.chain-stepno{width:34px;height:34px;flex:0 0 34px;border-radius:12px;background:linear-gradient(135deg,#06b6d4,#2563eb);display:flex;align-items:center;justify-content:center;font-weight:800;color:white}.chain-stage h3{margin:0 0 4px;font-size:18px;color:#fff}.chain-role{font-size:12px;color:#9ca3af;line-height:1.35}.badge-row{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.badge{display:inline-flex;align-items:center;gap:6px;padding:6px 9px;border-radius:999px;font-size:12px;border:1px solid var(--border);background:#0b1220;color:#cbd5e1}.badge.cyan{border-color:#0e7490;color:#cffafe;background:#082f49}.badge.green{border-color:#14532d;color:#bbf7d0;background:#052e16}.badge.amber{border-color:#854d0e;color:#fde68a;background:#422006}.chain-list{margin:10px 0 0;padding-left:18px;color:#dbe6f3;line-height:1.45}.chain-list li{margin:0 0 8px}.chain-list .small{display:block;margin-top:3px}.chain-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;margin-top:16px}.integration-panel,.storage-panel{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:14px}.integration-list{display:grid;gap:10px}.integration-card{border:1px solid #1f3145;border-radius:14px;background:rgba(8,13,23,.92);padding:12px}.integration-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:8px}.integration-route{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.node-pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:#111827;border:1px solid var(--border);font-size:12px;color:#e5e7eb}.route-arrow{color:#67e8f9;font-weight:800}.integration-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.meta-box{border:1px solid #1f3145;border-radius:12px;background:#0f172a;padding:8px 10px}.meta-box b{display:block;color:#fff;font-size:12px;margin-bottom:4px}.storage-list{display:grid;gap:10px}.storage-card{border:1px solid #1f3145;border-radius:14px;background:rgba(8,13,23,.92);padding:12px}.storage-card h4{margin:0 0 8px;color:#fff;font-size:15px}.storage-card ul{margin:0;padding-left:18px;line-height:1.45}.chain-legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.chain-empty{padding:14px;border:1px dashed #0e7490;border-radius:14px;background:#082f49;color:#dffafe}.section-status{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);border-radius:999px;padding:4px 8px;font-size:11px;color:#9ca3af;background:#0b1220;white-space:nowrap}.section-status.ok{border-color:#14532d;color:#bbf7d0}.section-status.warn{border-color:#854d0e;color:#fde68a}.matrix-section .grid{grid-template-columns:1fr}.matrix-section textarea{min-height:220px;font-family:ui-monospace,Menlo,Consolas,monospace}.textarea-tools .mini{font-size:12px;padding:8px 10px;border-radius:10px}.field textarea::placeholder,.field input::placeholder{color:#64748b}.helper-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.beginner-digest{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.digest-item{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:10px}.digest-item b{display:block;color:#fff;margin-bottom:4px}.sticky-submit{position:sticky;bottom:12px;z-index:6;background:rgba(7,17,31,.92);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:18px;padding:12px;margin-top:16px;display:flex;justify-content:space-between;align-items:center;gap:10px}.sticky-submit .small{margin:0}@media(max-width:900px){.ux-dashboard,.power-mode .ux-assistant,.beginner-digest,.chain-kpis,.chain-grid,.integration-meta{grid-template-columns:1fr!important}.ux-assistant{position:static}.chain-viz{overflow:visible;padding:12px}.chain-track{display:grid;grid-template-columns:1fr;overflow:visible;gap:12px}.chain-stage{min-width:0!important;max-width:none!important;width:auto!important;flex:none!important}.chain-stage:not(:last-child)::after{display:none!important}.chain-kpi b{font-size:24px}.integration-panel,.storage-panel,.integration-card,.meta-box,.storage-card{min-width:0}.node-pill,.badge,.meta-box span,.storage-card li,.chain-list li{white-space:normal;overflow-wrap:anywhere;word-break:break-word}.integration-route{min-width:0}.sticky-submit{position:fixed;left:0;right:0;bottom:0;border-radius:14px 14px 0 0;margin:0;align-items:stretch;flex-direction:column;padding:10px calc(10px + env(safe-area-inset-right)) calc(10px + env(safe-area-inset-bottom)) calc(10px + env(safe-area-inset-left))}.ux-actions{justify-content:flex-start}.section summary{display:block}.section summary small{display:block;text-align:left;margin-top:6px}.section-status{margin-top:8px}.wrap{padding:16px 10px 40px}.card{padding:16px}.btn{width:100%}.textarea-tools .btn,.ux-actions .btn{width:auto}}



.mobile-note{display:none}.ultra-panel{border:1px solid #0e7490;background:linear-gradient(180deg,rgba(14,116,144,.20),rgba(11,18,32,.96));border-radius:18px;padding:18px;margin:16px 0}.ultra-panel h2{margin-bottom:6px}.ultra-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.ultra-card{border:1px solid var(--border);background:#0b1220;border-radius:16px;padding:13px;cursor:pointer;color:#cbd5e1}.ultra-card input{width:auto;margin-right:6px}.ultra-card:has(input:checked){border-color:#22d3ee;background:#083344;color:white}.ultra-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:14px}.chain-map{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}.chain-node{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:14px;position:relative}.chain-node h3{margin:0 0 8px;text-transform:none;letter-spacing:0;color:#fff;font-size:16px}.chain-node .role{color:#93c5fd;font-size:12px;margin-bottom:8px}.chain-node ul{margin:8px 0 0 18px;padding:0;line-height:1.45}.chain-node.db{border-style:dashed;border-color:#0e7490}.chain-flow{border:1px solid var(--border);border-radius:16px;background:#080d17;overflow:hidden;margin-top:12px}.chain-row{display:grid;grid-template-columns:1.1fr .65fr 1.1fr 1.6fr;gap:8px;padding:10px 12px;border-top:1px solid var(--border);font-size:13px}.chain-row:first-child{border-top:0}.chain-row b{color:#fff}.chain-row span{color:#9ca3af}.mobile-actions{display:none;position:sticky;bottom:0;z-index:10;background:rgba(7,17,31,.94);backdrop-filter:blur(10px);border-top:1px solid var(--border);padding:10px calc(10px + env(safe-area-inset-right)) calc(10px + env(safe-area-inset-bottom)) calc(10px + env(safe-area-inset-left));gap:8px}.mobile-actions .btn{flex:1;text-align:center;padding:13px 10px}

.custom-builder{border:1px solid #0e7490;border-radius:18px;background:rgba(8,47,73,.35);padding:14px;margin:14px 0}.custom-builder-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}.custom-builder-actions{display:flex;gap:8px;flex-wrap:wrap}.participant-list,.connection-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0}.participant-card,.connection-card{border:1px solid var(--border);border-radius:14px;background:#0b1220;color:#e5e7eb;padding:12px}.participant-card b,.connection-card b{display:block;color:#fff;margin-bottom:6px}.participant-card span,.connection-card span{display:block;color:#9ca3af;font-size:12px;line-height:1.4}.connection-form{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;border:1px dashed #334155;border-radius:14px;padding:12px;margin-top:10px;background:#07111f}.connection-form select,.connection-form button{min-height:44px}.manual-diagram{border:1px solid #334155;border-radius:16px;background:#080d17;padding:12px;margin-top:12px}.manual-edge-list{display:grid;gap:8px;margin-top:10px}.manual-edge{border:1px solid #1e3a8a;border-radius:12px;background:#0b1b33;color:#dbeafe;padding:10px;font-size:13px}.role-palette{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}.role-palette button{border:1px solid var(--border);border-radius:12px;background:#0b1220;color:#e5e7eb;padding:10px;text-align:left}.role-palette button:hover{border-color:#22d3ee;background:#083344}@media(max-width:760px){.participant-list,.connection-list,.connection-form,.role-palette{grid-template-columns:1fr}.custom-builder-head{display:block}.custom-builder-actions .btn{width:100%}}

.business-step-card{border:1px solid var(--border);border-radius:14px;background:#0b1220;color:#e5e7eb;padding:12px;display:grid;grid-template-columns:auto 1fr;gap:8px 12px;align-items:start}.business-step-card .step-number{color:#93c5fd;font-size:12px;font-weight:800}.business-step-card .step-main b{display:block;color:#fff;margin-bottom:4px}.business-step-card .step-main span{display:block;color:#9ca3af;font-size:12px;line-height:1.4}.step-actions{grid-column:1/-1;display:flex;gap:6px;flex-wrap:wrap}.step-actions .mini-action{min-height:34px}.business-step-card.is-editing{border-color:#22d3ee;background:#083344}.quick-business-presets{border:1px dashed #0e7490;border-radius:16px;background:rgba(8,47,73,.25);padding:12px;margin-top:12px}.quick-business-presets h4{margin:0 0 8px}.business-flow-list{display:grid;gap:8px}.business-flow-step{border:1px solid #1e3a8a;border-radius:14px;background:#0b1b33;padding:10px;text-align:center}.business-flow-step b{display:block;color:#fff}.business-flow-step span{display:block;color:#bfdbfe;font-size:12px;margin-top:4px}.business-flow-arrow{text-align:center;color:#22d3ee;font-size:20px;font-weight:800}.warning-list{border:1px solid #f59e0b;background:#451a03;color:#fde68a;border-radius:14px;padding:10px;margin:10px 0}.warning-list b{color:#fff}.warning-list ul{margin:6px 0 0 18px;padding:0}.ordered-business-list{margin:0;padding-left:22px;line-height:1.65}@media(max-width:760px){.business-step-card{grid-template-columns:1fr}.step-actions{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.step-actions .mini-action{width:100%}.business-preset-grid{grid-template-columns:1fr!important}}

/* v6.5 real constructor simplification */
.constructor-help-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}.constructor-help-steps span{border:1px solid rgba(34,211,238,.24);border-radius:14px;background:#082f49;color:#dffafe;padding:10px;font-size:12px}.constructor-help-steps b{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:999px;background:#22d3ee;color:#06121f;margin-right:6px}.quick-chain-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 14px}.quick-chain-card{border:1px solid var(--border);border-radius:14px;background:#0b1220;color:#e5e7eb;text-align:left;padding:12px;cursor:pointer;min-height:88px}.quick-chain-card b{display:block;color:#fff;margin-bottom:6px}.quick-chain-card span{display:block;color:#9ca3af;font-size:12px;line-height:1.35}.quick-chain-card:hover{border-color:#22d3ee;background:#083344}.builder-subhead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:14px}.builder-subhead h4{margin:0}.builder-subhead span{font-size:12px;color:#93c5fd}.participant-card,.connection-card{position:relative}.participant-card .card-actions,.connection-card .card-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.mini-action{border:1px solid #334155;border-radius:10px;background:#07111f;color:#cbd5e1;padding:6px 8px;font-size:12px;cursor:pointer}.mini-action:hover{border-color:#22d3ee;color:#fff}.connection-edit-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}.connection-edit-row select{min-height:38px;padding:8px;border-radius:10px}.selected-link-note{border:1px solid #0e7490;border-radius:12px;background:#082f49;color:#dffafe;padding:10px;margin-top:8px;font-size:12px}.manual-diagram .interaction-diagram{margin-top:6px}.diagram-node{transition:transform .12s ease,border-color .12s ease}.diagram-node:hover{transform:translateY(-2px);border-color:#22d3ee}@media(max-width:760px){.constructor-help-steps,.quick-chain-grid{grid-template-columns:1fr}.connection-edit-row{grid-template-columns:1fr}.builder-subhead{align-items:flex-start;flex-direction:column}}

@media(max-width:760px){body{background:#07111f}.wrap{padding:14px 10px 86px}.mobile-note{display:block}.card,.beginner-panel,.ultra-panel,.wizard,.ux-assistant{border-radius:14px;padding:14px;margin-bottom:12px}h1{font-size:24px;line-height:1.15}h2{font-size:18px}.hero,.grid,.quick,.steps,.checklist,.choice-grid,.mini-grid,.form-builder,.simple-strip,.simple-result-grid,.advanced-rules,.ux-dashboard,.chain-map,.ultra-grid{grid-template-columns:1fr!important}.power-mode .ux-assistant{grid-template-columns:1fr}.ux-actions{justify-content:flex-start}.choice-card,.ultra-card,.builder-block,.simple-step,.simple-result,.chain-node{padding:12px}input,textarea,select{font-size:16px;min-height:44px}textarea{min-height:96px}.chip-group{display:grid;grid-template-columns:1fr;gap:8px}.chip{justify-content:flex-start;min-height:38px}.btn{width:100%;box-sizing:border-box}.nav{display:none}.mobile-actions{display:flex}.mode-switch-row{justify-content:stretch}.power-toggle{width:100%}.section summary{padding:14px;display:block}.section summary small{display:block;text-align:left;margin-top:4px}.section .grid{padding:0 12px 12px}.chain-row{grid-template-columns:1fr;gap:3px}.result{max-height:none;font-size:12px;padding:12px;overflow:auto}.report-actions{display:grid;grid-template-columns:1fr}.report-actions .btn{text-align:center}.beginner-digest{display:grid;grid-template-columns:1fr;gap:8px}.mobile-hide{display:none!important}}
@media(min-width:761px){.beginner-digest{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.digest-item{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:10px}.digest-item b{display:block;color:#fff}}


.start-screen h1{font-size:42px;margin:0 0 10px}.mode-choice-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.mode-choice{display:block;border:1px solid var(--border);border-radius:18px;background:#0b1220;padding:16px;cursor:pointer;min-height:104px}.mode-choice input{margin-right:8px}.mode-choice b{display:block;color:#fff;margin-bottom:8px}.mode-choice span{display:block;color:#9ca3af;font-size:13px;line-height:1.35}.mode-choice.selected,.mode-choice:has(input:checked){border-color:#60a5fa;box-shadow:0 0 0 1px rgba(96,165,250,.35);background:#0b1b33}.primary-row{display:flex;justify-content:flex-end;margin-top:16px}.is-hidden{display:none!important}.mode-header{display:flex;justify-content:space-between;align-items:center;gap:16px}.progress-rail{position:sticky;top:0;z-index:8;display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;background:rgba(7,17,31,.95);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:16px;padding:8px;margin-bottom:14px}.progress-rail span{font-size:12px;color:#9ca3af;background:#0b1220;border-radius:999px;padding:8px;text-align:center}.progress-rail span.active{background:#1d4ed8;color:#fff}.mode-panel{border:1px solid var(--border);border-radius:18px;background:#0b1220;padding:18px;margin-bottom:14px}.mode-panel:not(.active-mode-panel){display:none}.simple-question-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.wizard-step-card{border:1px solid var(--border);border-radius:16px;background:#07111f;padding:14px;margin:12px 0}.mode-choice-grid.compact{grid-template-columns:repeat(3,minmax(0,1fr))}.mode-choice-grid.compact .mode-choice{min-height:auto}.visual-chain{border:1px dashed #334155;border-radius:14px;padding:14px;background:#0f172a;color:#dbeafe;white-space:pre-line;text-align:center}.advanced-card-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.advanced-card{border:1px solid var(--border);border-radius:14px;background:#07111f;padding:14px;color:#fff}.advanced-card span{display:block;margin-top:8px;color:#fbbf24;font-size:12px}.expert-mode .matrix-section,.expert-mode .section{display:none!important}.wizard-mode .matrix-section,.review-mode .matrix-section{display:none}body.quick-mode .ultra-panel,body.quick-mode .beginner-panel,body.wizard-mode .ultra-panel,body.wizard-mode .beginner-panel,body.review-mode .ultra-panel,body.review-mode .beginner-panel,body.advanced-mode .ultra-panel,body.advanced-mode .beginner-panel{display:none!important}body.expert-mode details.section,body.expert-mode details.matrix-section{display:none!important}.review-screen{border-color:#60a5fa}.review-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.review-list div{border:1px solid var(--border);border-radius:14px;background:#07111f;padding:12px}.result-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.result-tab{border:1px solid var(--border);border-radius:999px;background:#0b1220;color:#d1d5db;padding:9px 12px}.production-gate{border:1px solid var(--border);border-radius:16px;padding:14px;background:#07111f;margin:12px 0}.gate-green{border-color:#22c55e}.gate-yellow{border-color:#f59e0b}.gate-red{border-color:#ef4444}
@media(max-width:760px){.start-screen h1{font-size:30px}.mode-choice-grid,.mode-choice-grid.compact,.simple-question-grid,.advanced-card-grid,.review-list,.progress-rail{grid-template-columns:1fr!important}.mode-header{display:block}.primary-row{display:block}.mode-choice{min-height:auto}.progress-rail{position:sticky;top:0}.progress-rail span{text-align:left}.mode-panel{padding:14px}.wizard-step-card{padding:12px}}


.simple-master{border:1px solid rgba(34,211,238,.45);background:linear-gradient(180deg,rgba(8,47,73,.96),rgba(11,18,32,.98));border-radius:22px;padding:20px;margin:0 0 18px;box-shadow:0 18px 50px rgba(0,0,0,.22)}
.simple-master h2{font-size:26px}.simple-master-lead{max-width:900px;color:#cbd5e1}.simple-master-steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:16px 0}.simple-master-step{border:1px solid var(--border);border-radius:14px;background:#07111f;color:#cbd5e1;padding:10px;text-align:left;font-size:13px;min-height:54px}.simple-master-step.is-active{border-color:#22d3ee;background:#083344;color:#fff}.simple-master-step.is-done{border-color:#15803d;color:#bbf7d0}.simple-master-panel{display:none;border:1px solid rgba(38,50,69,.95);border-radius:18px;background:rgba(7,17,31,.72);padding:16px;margin-top:12px}.simple-master-panel.is-active{display:block}.scenario-card-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.scenario-card{min-height:116px;border:1px solid var(--border);background:#0b1220;border-radius:18px;padding:14px;color:#d1d5db;cursor:pointer;text-align:left;display:flex;flex-direction:column;gap:8px}.scenario-card b{color:#fff;font-size:15px}.scenario-card span{color:#9ca3af;font-size:12px;line-height:1.45}.scenario-card:hover,.scenario-card:focus-visible{border-color:#22d3ee;transform:translateY(-1px);outline:0}.scenario-card.is-active{border-color:#22d3ee;background:#083344;box-shadow:0 0 0 2px rgba(34,211,238,.18) inset}.friendly-field-grid,.system-card-grid,.step-card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.friendly-field,.system-builder-card,.process-builder-card{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:12px;min-width:0}.friendly-field label,.system-builder-card label,.process-builder-card label{font-size:13px;font-weight:700;color:#e5e7eb}.builder-actions,.simple-master-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.mini-btn{padding:9px 12px;border-radius:12px;font-size:13px}.expert-matrix-toggle{margin-top:12px}.expert-matrix-collapsed{display:none}.readiness-layout{display:grid;grid-template-columns:.8fr 1fr 1fr;gap:12px;align-items:stretch}.readiness-score{border:1px solid #0e7490;border-radius:18px;background:#082f49;padding:18px;text-align:center}.readiness-score strong{font-size:46px;color:#22d3ee;display:block}.readiness-list{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:14px}.readiness-list ul{margin:0;padding-left:20px;line-height:1.7}.visual-result-chain{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:12px 0}.visual-node{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:14px;min-height:118px}.visual-node b{display:block;color:#fff;margin-bottom:6px}.visual-node span{display:block;color:#9ca3af;font-size:12px;margin-top:4px}.must-checklist{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0}.must-checklist span{border:1px solid #14532d;background:#052e16;color:#bbf7d0;border-radius:999px;padding:8px 10px;font-size:12px}.risk-question-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.result-fold-actions{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}button:disabled,.btn[aria-disabled='true']{opacity:.55;cursor:not-allowed}button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid rgba(34,211,238,.55);outline-offset:2px}.btn:hover{filter:brightness(1.08)}
@media(max-width:1024px){.simple-master-steps,.scenario-card-grid,.must-checklist{grid-template-columns:repeat(2,minmax(0,1fr))}.readiness-layout{grid-template-columns:1fr}.friendly-field-grid,.system-card-grid,.step-card-grid,.risk-question-grid{grid-template-columns:1fr}}
@media(max-width:520px){.wrap{padding:16px 10px 42px}.card,.simple-master{padding:14px;border-radius:16px}.simple-master-steps,.scenario-card-grid,.must-checklist{grid-template-columns:1fr}.builder-actions .btn,.simple-master-actions .btn,.report-actions .btn{width:100%;text-align:center}.sticky-submit{position:static!important}body{overflow-x:hidden}input,textarea,select{font-size:16px}}


.start-action-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.start-action-grid .mode-choice{text-align:left;width:100%}.legacy-wizard-compat{display:none!important;border:1px dashed #334155;border-radius:18px;padding:14px;margin-top:16px;background:#07111f}body.advanced-mode .legacy-wizard-compat,body.expert-mode .legacy-wizard-compat{display:none!important}.simple-mode .expert-only{display:none}.expert-mode .simple-only{display:none}.review-mode .simple-design-only{display:none}body.simple-mode details.section,body.review-mode details.section{display:none}body.expert-mode details.section,body.expert-mode details.matrix-section{display:none!important}@media(max-width:760px){.start-action-grid{grid-template-columns:1fr}.start-action-grid .mode-choice{min-height:auto}}


*{min-width:0}button,input,textarea,select{max-width:100%}.scenario-card,.system-builder-card,.process-builder-card,.visual-node,.readiness-list{overflow-wrap:anywhere}body{overflow-x:hidden}
body.review-mode #progressRail,body.simple-mode .legacy-wizard-compat,body.simple-mode .advanced-mode-panel,body.simple-mode .expert-only,body.simple-mode details.section,body.simple-mode details.matrix-section,body.simple-mode .wizard,body.simple-mode .quick,body.simple-mode .checklist,body.simple-mode .ultra-panel,body.simple-mode .beginner-panel,body.simple-mode .sticky-submit{display:none!important}
.helper-panel{display:none;border:1px dashed #0e7490;background:#082f49;border-radius:16px;padding:14px;margin-top:14px}.helper-panel.is-visible{display:block}.helper-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.helper-result{border:1px solid var(--border);border-radius:14px;background:#0b1220;padding:12px;margin-top:12px}.missing-action{margin-left:8px;padding:6px 9px;border-radius:10px;font-size:12px}.placeholder-warning{display:none;border:1px solid #854d0e;background:#422006;color:#fde68a;border-radius:14px;padding:12px;margin-top:12px}.placeholder-warning.is-visible{display:block}
@media(max-width:760px){.helper-grid{grid-template-columns:1fr}.missing-action{display:block;width:100%;margin:6px 0 0}.simple-master-actions{position:static}}

.complex-builder-toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.complex-graph-preview{border:1px solid var(--border);border-radius:16px;padding:14px;background:rgba(255,255,255,.03);margin:12px 0;overflow-x:auto}.complex-flow-map{display:flex;gap:14px;align-items:stretch;min-width:max-content;padding:8px 4px 14px}.complex-flow-step{display:flex;align-items:center;gap:12px}.complex-flow-node{width:240px;min-height:128px;border:1px solid var(--border);border-radius:16px;padding:12px;background:linear-gradient(180deg,rgba(15,23,42,.98),rgba(8,13,23,.98));box-shadow:0 10px 26px rgba(0,0,0,.18)}.complex-flow-node.parallel{border-color:#2563eb;background:linear-gradient(180deg,rgba(30,64,175,.28),rgba(15,23,42,.98))}.complex-flow-node.loop{border-color:#f59e0b;background:linear-gradient(180deg,rgba(120,53,15,.34),rgba(15,23,42,.98))}.complex-flow-node.wait{border-color:#8b5cf6;background:linear-gradient(180deg,rgba(76,29,149,.32),rgba(15,23,42,.98))}.complex-flow-node.compensation{border-color:#ef4444;background:linear-gradient(180deg,rgba(127,29,29,.32),rgba(15,23,42,.98))}.complex-node-top{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:8px}.complex-node-id{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:30px;border-radius:10px;background:#083344;color:#67e8f9;font-weight:800}.complex-node-kind{font-size:11px;color:#9ca3af;text-align:right}.complex-node-title{font-weight:800;color:#fff;line-height:1.25;margin-bottom:8px;overflow-wrap:anywhere}.complex-node-meta{display:flex;flex-wrap:wrap;gap:6px}.complex-node-meta span{font-size:11px;border:1px solid #1f3145;border-radius:999px;padding:4px 7px;color:#cbd5e1;background:#0b1220;max-width:100%;overflow-wrap:anywhere}.complex-flow-edge{min-width:86px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#67e8f9;font-weight:800}.complex-edge-label{font-size:11px;color:#a7f3d0;border:1px solid #0e7490;background:#082f49;border-radius:999px;padding:4px 8px;margin-bottom:5px;white-space:nowrap}.complex-edge-arrow{font-size:26px;line-height:1}.complex-flow-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}.complex-flow-summary span{border:1px solid #1f3145;border-radius:12px;background:#0b1220;padding:8px 10px;color:#cbd5e1;font-size:12px}.complex-flow-summary b{color:#fff}.process-builder-card .complex-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.complex-warning{border-left:4px solid #f59e0b;padding:10px;border-radius:12px;background:rgba(245,158,11,.10);margin:10px 0}@media(max-width:760px){.process-builder-card .complex-row{grid-template-columns:1fr}.complex-builder-toolbar .btn{width:100%;text-align:center}.complex-graph-preview{overflow-x:visible}.complex-flow-map{min-width:0;display:grid;grid-template-columns:1fr;gap:10px}.complex-flow-step{display:grid;grid-template-columns:1fr;gap:8px}.complex-flow-node{width:auto;min-height:0}.complex-flow-edge{min-width:0;transform:rotate(90deg);height:30px}.complex-edge-label{display:none}.complex-flow-summary{grid-template-columns:1fr}}

/* v5.2: максимально простой основной сценарий */
body:not(.power-mode) #beginnerPanel,body:not(.power-mode) #ultraPanel,body:not(.power-mode) .legacy-wizard-compat,body:not(.power-mode) .advanced-onboarding,body:not(.power-mode) .expert-only{display:none!important}
body:not(.power-mode) .expert-matrix-collapsed{display:none!important}
body:not(.power-mode) #toggleSystemsMatrixBtn,body:not(.power-mode) #toggleStepsMatrixBtn,body:not(.power-mode) #syncSystemsBtn,body:not(.power-mode) #syncStepsBtn{display:none!important}
body:not(.power-mode) .simple-master{border:1px solid #164e63;background:linear-gradient(180deg,rgba(8,47,73,.58),rgba(15,23,42,.96));border-radius:22px;padding:18px;margin:16px 0}
body:not(.power-mode) .simple-master::before{content:'Основной режим: выбирайте карточки и кнопки. Матрицы, контракты и отчёт будут собраны автоматически.';display:block;background:#082f49;border:1px solid #0e7490;color:#dffafe;border-radius:14px;padding:12px 14px;margin-bottom:14px;font-weight:700}
.system-builder-card,.process-builder-card{position:relative;overflow:hidden}.system-builder-card h4,.process-builder-card h4{font-size:15px;color:#fff;margin:0 0 10px}.process-builder-card textarea{min-height:68px}.complex-graph-preview{border:1px solid #1f3a56;border-radius:16px;background:#07111f;padding:12px;margin:12px 0;overflow-x:auto}.complex-flow-track,.complex-flow-map{display:flex;align-items:stretch;gap:0;min-width:max-content}.complex-flow-step{display:flex;align-items:center}.complex-flow-node{min-width:220px;max-width:280px;border:1px solid #334155;border-radius:16px;padding:12px;background:#0f172a;box-shadow:0 8px 24px rgba(0,0,0,.18)}.complex-flow-node.is-risk{border-color:#b45309}.complex-flow-node.is-async{border-color:#0e7490}.complex-flow-node.is-recovery{border-color:#7c3aed}.complex-node-top{display:flex;justify-content:space-between;gap:8px;color:#93c5fd;font-size:11px;text-transform:uppercase}.complex-node-title{color:#fff;font-weight:800;margin-top:6px;line-height:1.25}.complex-node-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;color:#cbd5e1;font-size:11px}.complex-node-meta span{border:1px solid #334155;border-radius:999px;padding:3px 7px;background:#0b1220}.complex-flow-edge{display:flex;align-items:center;gap:8px;margin:0 8px;color:#67e8f9;font-size:12px}.complex-edge-arrow{font-size:24px;color:#22d3ee}.complex-summary,.complex-flow-summary{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.complex-summary span,.complex-flow-summary span{border:1px solid #334155;border-radius:999px;padding:6px 9px;background:#0b1220;color:#cbd5e1;font-size:12px}.complex-warning{border:1px dashed #0e7490;background:#082f49;color:#dffafe;border-radius:14px;padding:10px 12px;margin:8px 0}.complex-builder-toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.friendly-field-grid,.simple-question-grid,.complex-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.complex-row{grid-template-columns:repeat(3,minmax(0,1fr))}.friendly-field,.system-builder-card,.process-builder-card{border:1px solid var(--border);border-radius:16px;background:#0b1220;padding:13px}.scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.scenario-card{border:1px solid var(--border);background:#0b1220;border-radius:16px;padding:14px;text-align:left;color:#cbd5e1}.scenario-card.is-active,.scenario-card:hover{border-color:#22d3ee;background:#083344;color:#fff}.term-glossary{border:1px dashed #0e7490;background:#082f49;color:#dffafe;border-radius:14px;padding:12px;margin:12px 0}.term-chip-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.term-chip{border:1px solid #0e7490;background:#0b1220;border-radius:999px;padding:6px 9px;font-size:12px;color:#dffafe}.term-chip b{color:#fff}.simple-master-step{border:1px solid var(--border);border-radius:14px;background:#0b1220;color:#cbd5e1;padding:10px 12px;display:flex;gap:8px;align-items:center}.simple-master-step.is-active{border-color:#22d3ee;background:#083344;color:#fff}.simple-master-step.is-done{border-color:#14532d;color:#bbf7d0}.simple-master-panel{display:none}.simple-master-panel.is-active{display:block}.simple-master-steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:16px}.readiness-layout{display:grid;grid-template-columns:.7fr 1fr 1fr;gap:12px}.readiness-score{border:1px solid #164e63;border-radius:16px;background:#082f49;padding:16px;text-align:center}.readiness-score strong{font-size:38px;color:#67e8f9;display:block}.placeholder-warning{display:none;border:1px solid #854d0e;background:#422006;color:#fde68a;border-radius:14px;padding:12px;margin:12px 0}.placeholder-warning.is-visible{display:block}
@media(max-width:760px){.simple-master-steps,.friendly-field-grid,.simple-question-grid,.scenario-grid,.readiness-layout,.complex-row{grid-template-columns:1fr}.complex-flow-track,.complex-flow-map{display:block;min-width:0}.complex-flow-step{display:block}.complex-flow-node{max-width:none;min-width:0}.complex-flow-edge{justify-content:center;margin:8px 0}.complex-edge-arrow{transform:rotate(90deg)}}

</style></head><body><div class="wrap">{content}</div></body></html>"""

def defaults():
    d={}
    for _,_,qs in QUESTIONS:
        for qid,_,typ,default,_ in qs: d[qid]=default.split(',') if typ=='multi' else default
    # Нейтральные стартовые значения: демо-примеры включаются только quick presets.
    # Это важно, чтобы простой кейс не наследовал случайно highload/DWH/клиентский статус из демонстрационного сценария.
    d.update({
        'project_name':'', 'task_type':'new_from_scratch', 'business_goal':'', 'business_situations':[], 'user_action':'',
        'criticality':'medium', 'customer_visible':'no', 'money_impact':'no', 'regulatory_impact':'no',
        'read_frequency':'medium', 'change_frequency':'medium', 'response_time_expectation':'under_3s',
        'freshness_requirement':'strict', 'business_priority':'balanced', 'stale_data_impact':'none',
        'unavailable_behavior':'show_error', 'external_dependency_stability':'unknown',
        'load_profile':'unknown', 'rps':'', 'peak_factor':'unknown', 'latency_sla':'seconds', 'consistency':'eventual_ok',
        'existing_state':'none', 'change_policy':[], 'constraint_profile':'balanced', 'budget_pressure':'medium',
        'deadline_pressure':'normal', 'new_service_policy':'allowed', 'new_infra_policy':'existing_only',
        'source_change_policy':'minimal_table_only', 'risk_appetite':'medium', 'compromise_comment':'',
        'existing_capabilities':[], 'compatibility':'none',
        'orchestration':'unknown', 'chain_depth':'unknown', 'step_count':'unknown', 'failure_policy':'retry', 'result_model':'sync',
        'source_system':'', 'main_entity':'', 'source_of_truth':'unclear', 'ownership':'unclear', 'data_volume':'small',
        'history':'none', 'retention':'not_defined', 'event_payload_intent':'domain_fact', 'enrichment_required':'none',
        'enrichment_owner_service':'', 'enrichment_consistency':'unknown',
        'webhook_signature_required':'unknown', 'webhook_raw_body_preserved':'unknown', 'webhook_timestamp_tolerance':'unknown',
        'webhook_secret_rotation':'unknown', 'webhook_ack_sla_ms':'3000', 'webhook_provider_retry_policy_known':'unknown',
        'webhook_reconciliation_available':'unknown',
        'delivery':'best_effort', 'ordering':'unknown', 'replay':'no',
        'manual_recovery':'no', 'allowed_channels':['rest'], 'forbidden_channels':['direct_db_write'], 'legacy':'none', 'dwh':'no',
        'kafka_topology':'multi_topic_ok', 'source_has_kafka_infra':'unknown', 'enrichment_channel':'none',
        'security_boundary':'internal', 'sensitivity':'internal', 'auth':'service', 'availability':'basic', 'observability':'standard',
        'rollout':'bigbang', 'testing':'unit_integration',
        'fields':'', 'systems_matrix':'', 'process_steps':'', 'error_matrix':'', 'statuses':'', 'final_statuses':'',
        'target_integration_matrix':'', 'process_flow_matrix':'', 'contract_matrix':'', 'business_rules_matrix':'',
        'capacity_matrix':'', 'observability_matrix':'', 'rollout_migration_matrix':'', 'data_quality_lineage_matrix':'',
        'current_solution_description':'', 'current_systems_matrix':'', 'current_integration_matrix':'',
        'current_process_steps':'', 'current_error_matrix':'', 'current_problem_matrix':'', 'current_controls':[]
    })
    return d



MATRIX_EXAMPLES = {
    'systems_matrix':'Source Service | владелец данных | Team A | critical | REST/Kafka | blocking | 2s\nTarget Service | получает результат | Team B | important | REST/Kafka | non_blocking | 30s',
    'process_steps':'0 | 1 | root | Принять команду/изменение | Source Service | REST | request | accepted | 2s | no | validation error | blocking | Team A\n1 | 2 | 1 | Передать/обработать результат | Target Service | Kafka/REST | event/request | result | 30s | yes | DLQ/manual | non_blocking | Team B',
    'fields':'entityId:uuid|required|unique|indexed, status:string|required|indexed, updatedAt:datetime|required, idempotencyKey:string|unique, correlationId:string|indexed',
    'error_matrix':'timeout | Target Service | blocking | yes | retry with backoff + status ERROR | Team B\nduplicate | Consumer | non_blocking | no | ignore by idempotencyKey/eventId | Team B',
    'target_integration_matrix':'Source Service | Target Service | Kafka | async | entity.changed | entity payload | EntityChanged.v1 | 30s | yes/backoff | 5 | yes | eventId+aggregateVersion | service auth | 100 rps | Team B',
    'process_flow_matrix':'S1 | root | request accepted | принять запрос | API | S2 | E_VALIDATION | E_TIMEOUT | none | no\nS2 | S1 | data ready | отправить downstream | Producer | S3 | E_DELIVERY | E_TIMEOUT | retry/DLQ | yes\nS3 | S2 | result received | обновить статус | Consumer | END | E_PROCESSING | E_RETRY | manual task | yes',
    'contract_matrix':'EVENT | EntityChanged | Source Service | Target Service | entity.changed.v1 | entityId as key | entityId,status,updatedAt,correlationId | reason,metadata | schema_error,duplicate,timeout | v1 | backward',
    'business_rules_matrix':'BR1 | пришёл дубль по idempotencyKey/eventId | не выполнять бизнес-действие повторно | S2 | Backend owner | DUPLICATE_IGNORED\nBR2 | downstream недоступен после retry | создать DLQ/manual task и статус ошибки | S3 | Operations owner | DELIVERY_FAILED',
    'capacity_matrix':'main_flow | 100 | 500 | 5 | 50 | 1000000 | 100% | 6 | 3 | 100 | 60s | 24h | 24h | уточнить',
    'observability_matrix':'consumer_lag | Kafka consumer | > 10000 events | yes | Platform | Integration dashboard\ndlq_size | DLQ | > 0 for 15m | yes | Operations | Failure dashboard\nstuck_status_count | status table | > 0 for 15m | yes | Support | Operations dashboard',
    'rollout_migration_matrix':'P1 | pilot users | feature toggle | выключить toggle | no | compare counts/statuses | no critical errors | Backend owner\nP2 | full flow | phased rollout | rollback toggle + replay failed period | 24h | compare business metrics | duplicates/losses = 0 | Product/Platform',
    'data_quality_lineage_matrix':'Entity | Source Service | Target Service | required fields not null + status/version consistency | each event | logs/reconciliation | Data owner\nEntityStatus | Target Service | DWH | count by status + checksum by id | hourly/daily | reconciliation report | Data platform',
    'current_systems_matrix':'api | API заявок | service | Product team | critical | yes | application\nkafka | Kafka | broker | Platform | critical | yes | events\ncrm | CRM | external_service | CRM team | important | no | customer_card',
    'current_integration_matrix':'api | kafka | Kafka | async | no | status event | 1s | yes | 3 | no | no | service | Product team\nkafka | crm | Kafka/event | async | no | status event | 30s | yes | 5 | yes | eventId | service | CRM team',
    'current_process_steps':'0 | root | 1 | Создать заявку | frontend | api | REST | yes | CREATED | ERROR | retry | yes\n1 | 1 | 2 | Опубликовать событие | api | kafka | Kafka | no | EVENT_SENT | EVENT_ERROR | DLQ/manual | yes',
    'current_error_matrix':'kafka_publish_error | api | technical | no | yes | log_only | no | Platform | no\ncrm_error | crm | technical | no | yes | dlq/manual | yes | CRM team | yes',
    'current_problem_matrix':'duplicates | crm | weekly | дубли статусов в CRM | manual cleanup\nlost_event | api_to_kafka | monthly | CRM/DWH не видят часть изменений | manual reload'
}

QUESTION_TIPS = {
    'systems_matrix':'Формат: Система | роль | владелец | critical/important | канал | blocking/non_blocking | SLA. Пример: CRM | карточка клиента | CRM team | important | rest | blocking | 3s',
    'process_steps':'Формат: level | order | parent | шаг | система | канал | input | output | timeout | retry | compensation | blocking | owner. Начните с 2-3 главных шагов.',
    'error_matrix':'Формат: ошибка | где | blocking/non_blocking | retry yes/no | что после retry | owner. Минимум: timeout, duplicate, validation error.',
    'fields':'Формат: name:type|required|unique|indexed|sensitive. Минимум: id сущности, status, idempotencyKey/correlationId, updatedAt.',
    'business_goal':'Пишите обычным языком: кто что должен сделать и какой результат получить.',
    'compromise_comment':'Опишите реальные ограничения: сроки, бюджет, нельзя менять source, нет Kafka в нужном сервисе, нельзя новый сервис.',
    'current_systems_matrix':'Опишите текущие системы как есть, даже если связи плохие или временные.',
    'current_integration_matrix':'Опишите текущие связи: кто кого вызывает, какой канал, sync/async, где есть таймауты.',
    'current_problem_matrix':'Перечислите симптомы: дубли, потери, таймауты, ручные исправления, непонятно где упало.',
    'target_integration_matrix':'Главная таблица для проектирования: кто кого вызывает/куда публикует, канал, trigger, contract, timeout, retry, DLQ, idempotency, auth, rate limit, owner.',
    'process_flow_matrix':'Для сложных процессов: step_id, parent_id, condition, success/failure/timeout переходы. Помогает описать ветвления, Saga, fan-out/fan-in.',
    'contract_matrix':'API/event/file contracts: endpoint/topic, обязательные поля, ошибки, версия, backward compatibility.',
    'business_rules_matrix':'Бизнес-условия и действия: if condition → action. Не прячьте правила в тексте шага.',
    'capacity_matrix':'Для Kafka/highload/API/DB: RPS, payload, events/day, filter ratio, partitions, consumers, DB write TPS, lag, replay/backfill.',
    'observability_matrix':'Какие метрики и алерты должны быть: lag, DLQ, stuck statuses, reconciliation diff, owner и dashboard.',
    'rollout_migration_matrix':'Как выкатывать безопасно: phase, scope, strategy, rollback, backfill, parallel compare, go/no-go.',
    'data_quality_lineage_matrix':'Откуда данные идут, куда приходят и как проверяется полнота/качество/lineage.'
}

def q_tip(qid):
    tip = QUESTION_TIPS.get(qid, '')
    return f'<div class="question-tip">Подсказка: {escape(tip)}</div>' if tip else ''

def render_q(q,vals):
    qid,label,typ,default,opts=q; cur=vals.get(qid, default)
    placeholder = MATRIX_EXAMPLES.get(qid, QUESTION_TIPS.get(qid, ''))
    if typ=='text': return f'<div class="field" data-qid="{escape(qid)}"><label>{escape(label)}</label><input type="text" name="{qid}" value="{escape(str(cur))}" placeholder="{escape(str(placeholder))}">{q_tip(qid)}</div>'
    if typ=='textarea':
        is_matrix = qid in MATRIX_EXAMPLES
        tools = ''
        extra = ''
        if is_matrix:
            tools = f'<div class="textarea-tools"><button type="button" class="btn ghost mini" data-fill-example="{escape(qid)}">Вставить пример</button><button type="button" class="btn ghost mini" data-clear-field="{escape(qid)}">Очистить поле</button></div>'
            extra = '<div class="field-hint">Можно нажать “Вставить пример”, затем заменить названия систем и правила под свой процесс. Символ | разделяет колонки.</div>'
        elif qid in ['business_goal','compromise_comment','current_solution_description']:
            extra = '<div class="field-hint">Пишите обычными словами. Термины REST/Kafka/Outbox можно не использовать, если они неизвестны.</div>'
        return f'<div class="field field-textarea" data-qid="{escape(qid)}"><label>{escape(label)}</label><textarea name="{qid}" placeholder="{escape(str(placeholder))}">{escape(str(cur))}</textarea>{tools}{q_tip(qid)}{extra}</div>'
    if typ=='select': return f'<div class="field" data-qid="{escape(qid)}"><label>{escape(label)}</label><select name="{qid}">'+''.join(f'<option value="{escape(v)}" {"selected" if v==cur else ""}>{escape(t)}</option>' for v,t in opts)+'</select>{q_tip(qid)}</div>'
    if typ=='multi':
        cur=cur if isinstance(cur,list) else str(cur).split(',')
        chips=''.join(
            f'<label class="chip"><input type="checkbox" name="{qid}" value="{escape(v)}" {"checked" if v in cur else ""}> {escape(t)}</label>'
            for v,t in opts
        )
        return f'<div class="field" data-qid="{escape(qid)}"><label>{escape(label)}</label><div class="chip-group">{chips}</div><div class="small">Выберите один или несколько вариантов. На телефоне это работает как обычные кнопки.</div>{q_tip(qid)}</div>'
    return ''

SECTION_HINTS = {
    'task': 'Минимум: тип задачи, цель, критичность.',
    'business': 'Бизнес-признаки: клиентский экран, деньги, скорость, свежесть, fallback.',
    'load': 'Минимум: highload/не highload, SLA, консистентность.',
    'existing': 'Только для внедрения в существующий production/legacy-процесс.',
    'topology': 'Кто управляет процессом: orchestrator, choreography, hybrid, BPM.',
    'systems': 'Кто участвует: системы, владельцы, критичность, SLA.',
    'steps': 'Цепочка шагов: можно описывать уровни, parent, fan-out/fan-in.',
    'data': 'БД, source of truth, история, retention.',
    'delivery': 'Ошибки, retry, DLQ, idempotency, replay.',
    'channels': 'Разрешённые каналы и legacy-ограничения.',
    'target_integrations': 'Целевые связи и переходы процесса: база для полноценной интеграционной спецификации.',
    'contracts_rules': 'Контракты и бизнес-правила: API/event schema, ошибки, версии, условия переходов.',
    'capacity_ops': 'Capacity и эксплуатация: RPS, lag, filter ratio, DLQ, алерты, владельцы.',
    'quality_rollout': 'Rollout, migration, backfill, parallel run, качество данных и lineage.',
    'audit': 'Для аудита текущего решения: системы, связи, проблемы, контроли.',
    'security': 'Безопасность, наблюдаемость, rollout, тестирование.'
}

SECTION_GUIDES = {
    'task': ('Смысл блока', ['Выберите тип задачи не идеально точно, а примерно: проектируем новую интеграцию, проверяем старую, подключаем legacy или DWH.', 'Цель пишите обычным языком: “передать договоры в сервис X”, “показать клиенту статус”, “забрать отчёты из БКИ”.', 'Критичность — что будет, если интеграция сломается: неудобство, деньги, клиентская жалоба, регуляторный риск.']),
    'business': ('Как думать', ['Клиентский экран = пользователь ждёт ответ сейчас.', 'Свежесть = насколько допустимы старые данные: секунды, минуты, день.', 'Fallback = что показываем/делаем, если источник недоступен.']),
    'load': ('Без формул', ['Не знаете RPS — оставьте пусто и выберите профиль нагрузки.', 'Highload — не только много запросов, но и жёсткий SLA, пики, очереди, backpressure.', 'Консистентность: можно ли показать/обработать данные не мгновенно, но гарантированно позже.']),
    'existing': ('Компромиссы', ['Здесь фиксируются реальные ограничения: нельзя новый сервис, нельзя менять source, Kafka есть только в другом контуре.', 'Это не слабость проекта, а входные условия для корректного архитектурного решения.', 'Пишите ограничения словами — инструмент учтёт их в MVP/Production вариантах.']),
    'topology': ('Кто рулит процессом', ['Один сервис — простая цепочка.', 'Orchestrator/Process Manager — когда много шагов, статусы, повторы, ручное восстановление.', 'Choreography — когда системы реагируют на события и нет единого управляющего шага.', 'Hybrid — часто самый реалистичный вариант для сложного enterprise.']),
    'systems': ('Участники', ['Каждая строка — одна система: название, роль, владелец, критичность, канал, блокирует ли процесс, SLA.', 'Не знаете владельца — пишите “уточнить”: это лучше, чем молча пропустить.', 'Blocking означает: если система не ответила, основной процесс не может корректно продолжиться.']),
    'steps': ('Процесс как история', ['Пишите шаги как последовательность: кто вызывает, что передаёт, что получает.', 'Parent нужен только для сложных ветвлений; для новичка можно оставить root/номер предыдущего шага.', 'Компенсация — что делаем после ошибки: retry, статус ошибки, DLQ, ручная задача.']),
    'data': ('Данные', ['Source of truth — где “правда” по сущности.', 'Ownership — кто имеет право менять данные.', 'Retention — сколько храним данные/историю/попытки/аудит.', 'Enrichment — нужно ли дополнять событие данными из другого сервиса.']),
    'delivery': ('Надёжность', ['At-least-once означает: сообщение может прийти повторно, значит нужна идемпотентность.', 'Business exactly-once — не магия Kafka, а защита от дублей на уровне бизнес-операции.', 'Replay нужен, если надо переобработать событие/период/витрину.']),
    'channels': ('Каналы', ['Выберите не “что модно”, а что реально разрешено: REST, Kafka, queue, CDC, SFTP, SOAP.', 'Запрещённые каналы важны: инструмент не должен рекомендовать то, что команда не может внедрить.', 'Kafka-топология особенно важна для кейсов raw/enriched event и одного общего topic.']),
    'target_integrations': ('Связи отдельно от шагов', ['Шаг процесса и интеграционная связь — разные вещи: один шаг может включать несколько вызовов, а одна связь может использоваться в разных шагах.', 'Для каждой связи укажите канал, sync/async, contract, retry, DLQ, idempotency, auth и owner.', 'Если не знаете rate limit или owner — пишите “уточнить”, это попадёт в вопросы для ревью.']),
    'contracts_rules': ('Контракты и правила', ['Контракт — это не просто “REST/Kafka”, а endpoint/topic, обязательные поля, ошибки, версия и совместимость.', 'Бизнес-правила пишите отдельными строками: условие → действие → affected step.', 'Это защищает от ситуации, когда техническая схема красивая, а реальные правила потерялись.']),
    'capacity_ops': ('Нагрузка и эксплуатация', ['Для highload/shared Kafka topic обязательно указывайте filter ratio, partitions, consumers, lag и replay volume.', 'Наблюдаемость лучше описывать как конкретные метрики с threshold и owner.', 'Если данные неизвестны — оставьте “уточнить”; gate должен показать, что без этого production нельзя.']),
    'quality_rollout': ('Безопасный запуск', ['Rollout — это как включаем, как откатываем и как понимаем, что можно идти дальше.', 'Для миграций/DWH/Kafka полезны backfill, parallel compare и go/no-go критерии.', 'Lineage и data quality нужны, чтобы доказать полноту и корректность данных.']),
    'audit': ('Проверка текущего решения', ['Опишите как есть, даже если плохо: sync-цепочка, прямое чтение БД, нет retry, нет DLQ.', 'Проблемы пишите фактами: дубли, потери, таймауты, ручные правки, нет трассировки.', 'Инструмент сравнит текущее состояние с целевым и предложит безопасный путь исправления.']),
    'security': ('Финал', ['Безопасность — какие данные и границы доверия.', 'Observability — как поймём, где упало: correlationId, метрики, алерты, трассировка.', 'Rollout/testing — как внедрить без большого взрыва: canary, parallel run, contract tests.'])
}
STEP_MAP_DESIGN = {'task':0,'business':0,'load':0,'topology':1,'systems':1,'steps':1,'existing':2,'data':2,'delivery':2,'channels':2,'target_integrations':2,'contracts_rules':2,'capacity_ops':3,'quality_rollout':3,'security':3}
STEP_MAP_AUDIT = {'task':0,'load':0,'audit':1,'existing':2,'security':2}

def form_page(vals=None):
    vals=vals or defaults(); recent=list_runs()
    recent_html='<h3>Последние генерации</h3>'+''.join(f'<div class="small"><a href="/run?id={escape(r["id"])}">{escape(r["name"])} v{r["version"]} — {r["score"]}% — {escape(r["recommended"])}</a></div>' for r in recent) if recent else ''
    blocks=[]
    for sec_id,title,qs in QUESTIONS:
        hint=SECTION_HINTS.get(sec_id,'')
        d_step=STEP_MAP_DESIGN.get(sec_id,'')
        a_step=STEP_MAP_AUDIT.get(sec_id,'')
        guide_title, guide_items = SECTION_GUIDES.get(sec_id, ('Как заполнить', []))
        guide_html = '<div class="section-guide"><b>'+escape(guide_title)+'</b><ul>'+''.join('<li>'+escape(x)+'</li>' for x in guide_items)+'</ul></div>' if guide_items else ''
        body=guide_html + ''.join(render_q(q,vals) for q in qs)
        blocks.append(f"""<details class='section {'matrix-section' if any(q[0] in MATRIX_EXAMPLES for q in qs) else ''}' data-sec='{escape(sec_id)}' data-design-step='{d_step}' data-audit-step='{a_step}'>
  <summary><span>{escape(title)}</span><small>{escape(hint)}</small></summary>
  <div class='grid'>{body}</div>
</details>""")
    sections=''.join(blocks)
    content_template="""
<section class='start-screen card' id='startScreen'>
  <p class='small mobile-hide'>Business-first integration constructor</p>
  <h1>Конструктор бизнес-процесса</h1>
  <p class='muted'>Опишите процесс обычными выборами. Техническую схему, стек, риски и отчёт система построит сама.</p>
  <div class='start-action-grid' aria-label='Выбор задачи'>
    <button type='button' class='mode-choice selected' data-start-goal='new'><b>Спроектировать процесс</b><span>С нуля: бизнес-процесс → техническая схема → отчёт.</span></button>
    <button type='button' class='mode-choice' data-start-goal='audit'><b>Проверить текущее решение</b><span>Найти риски, потери, дубли, таймауты и слабые места.</span></button>
    <button type='button' class='mode-choice' data-start-goal='complex'><b>Разобрать сложный процесс</b><span>Много шагов, внешний ответ, отчётность, legacy, компенсации или ограничения.</span></button>
  </div>
  <button type='button' class='btn' id='startNoTextBtn'>Начать</button>
  %%RECENT_HTML%%
</section>
<div class='app-shell is-hidden no-text-app' id='appShell'>
<form method='POST' action='/generate' class='card' id='mainForm'>
  <input type='hidden' name='preset_name' value=''>
  <input type='hidden' name='ux_mode' value='business_first_constructor'>
  <input type='hidden' name='report_detail' value='human'>
  <input type='hidden' name='project_name' value=''>
  <input type='hidden' name='business_goal' id='businessGoalHidden' value=''>
  <input type='hidden' name='task_type' id='taskTypeHidden' value='new_from_scratch'>
  <input type='hidden' name='simple_goal' id='simpleGoalHidden' value='new'>
  <input type='hidden' name='simple_situation' id='simpleSituationHidden' value='async_worker'>
  <input type='hidden' name='simple_q_systems' id='simpleQSystemsHidden' value='3'>
  <input type='hidden' name='simple_q_immediate' id='simpleQImmediateHidden' value='Принять сейчас, результат позже'>
  <input type='hidden' name='simple_q_payload' id='simpleQPayloadHidden' value='Заявку / команду'>
  <input type='hidden' name='simple_q_risk' id='simpleQRiskHidden' value='Потерять данные'>
  <input type='hidden' name='simple_q_error' id='simpleQErrorHidden' value='Сохранить и обработать потом'>
  <input type='hidden' name='simple_q_status' id='simpleQStatusHidden' value='Да'>
  <input type='hidden' name='systems_matrix' id='systemsMatrixHidden' value=''>
  <input type='hidden' name='process_steps' id='processStepsHidden' value=''>
  <input type='hidden' name='target_integration_matrix' id='targetIntegrationHidden' value=''>
  <input type='hidden' name='contract_matrix' id='contractMatrixHidden' value=''>
  <input type='hidden' name='error_matrix' id='errorMatrixHidden' value=''>
  <input type='hidden' name='process_graph_json' id='processGraphJson' value=''>
  <input type='hidden' name='process_graph_meta' id='processGraphMeta' value=''>
  <input type='hidden' name='data_storage_choice' id='dataStorageChoiceHidden' value='task_table'>
  <input type='hidden' name='data_storage_role' id='dataStorageRoleHidden' value='process_status'>
  <input type='hidden' name='custom_chain_json' id='customChainJson' value=''>
  <input type='hidden' name='business_case' id='businessCaseHidden' value='application_creation'>
  <input type='hidden' name='business_process_json' id='businessProcessJson' value=''>
  <input type='hidden' name='business_actors_json' id='businessActorsJson' value=''>
  <input type='hidden' name='business_steps_json' id='businessStepsJson' value=''>
  <input type='hidden' name='business_object' id='businessObjectHidden' value='Заявка'>
  <input type='hidden' name='business_result_timing' id='businessResultTimingHidden' value='Нужно принять сейчас, результат получить позже'>
  <input type='hidden' name='business_result_type' id='businessResultTypeHidden' value='Создана заявка'>
  <input type='hidden' name='business_constraints_json' id='businessConstraintsJson' value='[]'>
  <input type='hidden' name='business_criticality' id='businessCriticalityHidden' value='Потерять данные'>
  <input type='hidden' name='business_situations' id='businessSituationsHidden' value=''>
  <input type='hidden' name='operation_kind' id='operationKindHidden' value=''>
  <input type='hidden' name='result_model' id='resultModelHidden' value=''>
  <input type='hidden' name='delivery' id='deliveryHidden' value=''>
  <input type='hidden' name='load_profile' id='loadProfileHidden' value=''>
  <input type='hidden' name='sensitivity' id='sensitivityHidden' value=''>
  <input type='hidden' name='money_impact' id='moneyImpactHidden' value=''>
  <input type='hidden' name='regulatory_impact' id='regulatoryImpactHidden' value=''>
  <input type='hidden' name='source_change_policy' id='sourceChangePolicyHidden' value=''>
  <input type='hidden' name='allowed_channels' id='allowedChannelsHidden' value=''>
  <input type='hidden' name='forbidden_channels' id='forbiddenChannelsHidden' value=''>
  <input type='hidden' name='orchestration' id='orchestrationHidden' value=''>
  <input type='hidden' name='step_count' id='stepCountHidden' value=''>
  <input type='hidden' name='chain_depth' id='chainDepthHidden' value=''>
  <input type='hidden' name='partial_response_ok' id='partialResponseOkHidden' value=''>
  <input type='hidden' name='replay' id='replayHidden' value=''>
  <input type='hidden' name='retention' id='retentionHidden' value=''>
  <input type='hidden' name='current_controls' id='currentControlsHidden' value=''>
  <input type='hidden' name='kafka_topology' id='kafkaTopologyHidden' value=''>
  <input type='hidden' name='consistency' id='consistencyHidden' value=''>
  <input type='hidden' name='auto_generated_technical_chain_json' id='autoGeneratedTechnicalChainJson' value=''>

  <div class='mode-header card no-text-header'>
    <div><span class='mode-badge'>Бизнесовый конструктор</span><h2>Сначала бизнес, потом техника</h2><p class='small'>Пользователь выбирает участников, действия, объект, требования и ограничения. Технический конструктор доступен только как вторичный слой.</p></div>
    <button type='button' class='btn ghost' id='backToStart'>← В начало</button>
  </div>

  <div class='progress-rail simple-progress-rail' id='constructorProgress'>
    <span class='active'>1. Бизнес-ситуация</span><span>2. Бизнес-процесс</span><span>3. Требования</span><span>4. Техническая схема</span><span>5. Проверка</span><span>6. Результат</span>
  </div>

  <section class='constructor-screen is-active' data-constructor-screen='0'>
    <h2>1. Какой бизнес-процесс нужно описать?</h2>
    <p class='small'>Выберите ситуацию обычными словами. На этом экране нет Kafka, DB, Worker, REST, Outbox и других технических терминов.</p>
    <div class='scenario-card-grid business-case-grid' id='situationCards'>
      <button type='button' class='scenario-card is-active' data-business-case='application_creation' data-case='async_worker'><b>Клиент / пользователь создаёт заявку</b><span>Пользователь создаёт заявку, заказ, обращение или запрос, а система принимает и обрабатывает его.</span><small class='covers'>Покрывает: создание заявки, проверку, статусы, фоновую обработку, внешний ответ, ручной разбор.</small></button>
      <button type='button' class='scenario-card' data-business-case='data_change_distribution' data-case='event_kafka'><b>Нужно передать изменение данных другим системам</b><span>В одной системе меняются данные, и другие системы должны об этом узнать.</span><small class='covers'>Покрывает: изменение договора, клиента, статуса, несколько получателей, защиту от потерь и дублей.</small></button>
      <button type='button' class='scenario-card' data-business-case='external_check' data-case='callback'><b>Нужно получить или проверить данные во внешней системе</b><span>Нужно обратиться во внешнюю организацию, сервис партнёра или внешний контур.</span><small class='covers'>Покрывает: внешний вызов, отложенный ответ, повтор запроса, ручной разбор.</small></button>
      <button type='button' class='scenario-card' data-business-case='data_enrichment' data-case='enrichment_kafka'><b>Нужно дополнить данные перед следующим шагом</b><span>Перед передачей или обработкой нужно получить недостающие данные из другой системы.</span><small class='covers'>Покрывает: обогащение данных, выбор места обогащения, недоступность источника, отдельный адаптер.</small></button>
      <button type='button' class='scenario-card' data-business-case='status_screen' data-case='status_aggregation'><b>Нужно показать пользователю итоговый статус</b><span>Экран или сервис должен собрать статус процесса из нескольких источников.</span><small class='covers'>Покрывает: агрегацию статусов, частичный ответ, последний известный статус, отметку свежести данных.</small></button>
      <button type='button' class='scenario-card' data-business-case='reporting' data-case='dwh'><b>Нужно передать данные в отчётность / аналитику</b><span>Данные нужны для отчётов, витрин, аналитики или сверки.</span><small class='covers'>Покрывает: выгрузку, сверку полноты, повторную загрузку, промежуточную зону, качество данных.</small></button>
      <button type='button' class='scenario-card' data-business-case='legacy_file' data-case='legacy_file'><b>Есть старая система или файловый обмен</b><span>Обмен идёт через файл, SFTP, выгрузку или legacy-систему.</span><small class='covers'>Покрывает: файл, контрольную сумму, реестр файлов, карантин ошибок, переобработку.</small></button>
      <button type='button' class='scenario-card' data-business-case='audit' data-case='audit'><b>Нужно проверить текущее решение</b><span>Схема уже есть, но нужно найти риски, слабые места и варианты улучшения.</span><small class='covers'>Покрывает: аудит текущей схемы, дубли, потери, таймауты, восстановление, наблюдаемость.</small></button>
      <button type='button' class='scenario-card' data-business-case='long_process' data-case='async_worker'><b>Долгий многошаговый процесс</b><span>Процесс состоит из нескольких шагов, может завершиться частично и требует восстановления.</span><small class='covers'>Покрывает: статусы, частичный успех, компенсации, ручное восстановление, владельца восстановления.</small></button>
      <button type='button' class='scenario-card' data-business-case='helper' data-case='helper'><b>Не знаю, помогите выбрать</b><span>Система задаст несколько простых вопросов и предложит подходящий вариант.</span><small class='covers'>Покрывает: быстрый выбор ситуации без технических знаний.</small></button>
    </div>
  </section>

  <section class='constructor-screen' data-constructor-screen='1'>
    <h2>2. Соберите бизнес-процесс</h2>
    <p class='small'>Выберите участников, действия, бизнес-объект и результат. Техническая схема строится автоматически.</p>
    <div class='builder-guide'><b>Как заполнить:</b><ol><li>добавьте бизнес-участников;</li><li>добавьте шаги процесса;</li><li>выберите объект, срок результата и итог;</li><li>ниже появится автоматически построенная техническая схема.</li></ol></div>
    <div class='business-actions-row'>
      <button type='button' class='btn secondary' id='addBusinessActorBtn'>+ Добавить участника</button>
      <button type='button' class='btn secondary' id='addBusinessStepBtn'>+ Добавить шаг процесса</button>
      <button type='button' class='btn ghost' id='resetBusinessBtn'>Сбросить бизнес-процесс</button>
    </div>
    <div class='simple-question-grid'>
      <label class='field'><span>Роль нового участника</span><select id='businessActorRole'><option>Клиент / пользователь</option><option>Внутренняя система</option><option>Внешняя организация / партнёр</option><option>Оператор / сотрудник</option><option>Проверяющая система</option><option>Система уведомлений</option><option>Отчётный контур</option><option>Старая система</option><option>Несколько внутренних систем</option><option>Несколько получателей</option><option>Не знаю</option></select></label>
      <label class='field'><span>Участник шага</span><select id='businessStepActorSelect'><option value=''>Система</option></select></label>
      <label class='field'><span>Действие шага</span><select id='businessStepAction'><option>Создаёт заявку / запрос</option><option>Принимает заявку</option><option>Меняет данные</option><option>Фиксирует изменение</option><option>Получает изменение</option><option>Обновляет свои данные</option><option>Получает объект</option><option>Дополняет данные</option><option>Открывает экран</option><option>Собирает статусы</option><option>Возвращает часть статуса</option><option>Видит итоговый статус</option><option>Формирует файл</option><option>Принимает файл</option><option>Проверяет файл</option><option>Загружает валидные данные</option><option>Проверяет данные</option><option>Получает дополнительные данные</option><option>Принимает решение</option><option>Обновляет статус</option><option>Передаёт данные дальше</option><option>Отправляет уведомление</option><option>Ждёт ответ</option><option>Получает ответ позже</option><option>Обрабатывает запрос</option><option>Передаёт в отчётность</option><option>Проверяет полноту</option><option>Строится на проверенных данных</option><option>Отправляет на ручной разбор</option><option>Компенсирует / откатывает шаг</option><option>Завершает процесс</option></select></label>
      <label class='field'><span>Бизнес-объект</span><select id='businessObjectSelect'><option>Заявка</option><option>Заказ</option><option>Договор</option><option>Клиентские данные</option><option>Статус</option><option>Платёж / финансовая операция</option><option>Документ</option><option>Файл</option><option>Справочные данные</option><option>Событие изменения</option><option>Отчётные данные</option><option>Не знаю</option></select></label>
      <label class='field'><span>Когда нужен результат</span><select id='businessTimingSelect'><option>Сразу на экране</option><option>Можно позже</option><option>Нужно принять сейчас, результат получить позже</option><option>Внешняя система ответит позже</option><option>Данные нужны для отчёта</option><option>Не знаю</option></select></label>
      <label class='field'><span>Результат процесса</span><select id='businessResultSelect'><option>Создана заявка</option><option>Обновлён статус</option><option>Данные переданы другой системе</option><option>Получен ответ от внешней системы</option><option>Данные попали в отчётность</option><option>Пользователь увидел итоговый статус</option><option>Ошибка отправлена в ручной разбор</option><option>Процесс завершён частично</option><option>Не знаю</option></select></label>
    </div>
    <div class='quick-business-presets'>
      <h4>Быстро собрать типовой процесс</h4>
      <div class='quick-chain-grid business-preset-grid'>
        <button type='button' class='quick-chain-card' data-business-preset='deferred_application'><b>Заявка с отложенной обработкой</b><span>Клиент создаёт заявку, система проверяет данные, внешний шаг отвечает позже, статус обновляется.</span></button>
        <button type='button' class='quick-chain-card' data-business-preset='data_change_many_systems'><b>Изменение данных для нескольких систем</b><span>Изменение фиксируется и расходится нескольким получателям.</span></button>
        <button type='button' class='quick-chain-card' data-business-preset='enrichment_before_send'><b>Обогащение перед отправкой</b><span>Объект дополняется проверяющей системой перед передачей дальше.</span></button>
        <button type='button' class='quick-chain-card' data-business-preset='status_screen_collection'><b>Сбор статуса на экран</b><span>Экран собирает статусы из нескольких систем и показывает итог.</span></button>
        <button type='button' class='quick-chain-card' data-business-preset='reporting'><b>Отчётность</b><span>Данные уходят в отчётный контур и проверяются перед отчётом.</span></button>
        <button type='button' class='quick-chain-card' data-business-preset='legacy_file'><b>Legacy file</b><span>Файл принимается, проверяется, ошибки уходят в ручной разбор.</span></button>
      </div>
    </div>
    <p class='small' id='businessStepEditHint'></p>
    <div class='builder-subhead'><h4>Бизнес-участники</h4><span id='businessActorCounter'>0 участников</span></div>
    <div class='participant-list' id='businessActorList'></div>
    <div class='builder-subhead'><h4>Шаги бизнес-процесса</h4><span id='businessStepCounter'>0 шагов</span></div>
    <div class='connection-list' id='businessStepList'></div>
    <div class='manual-diagram' id='businessDiagram'></div>
    <div class='simple-result' id='autoTechnicalPreview'></div>
    <div id='businessTechnicalConstructorHost'><details class='case-questions-details technical-constructor-details' id='technicalConstructorDetails'>
      <summary>Показать технический конструктор</summary>
      <p class='small'>Это техническая схема, которую система построила из бизнес-процесса. Её можно поправить, если вы понимаете технические детали.</p>
      <div class='builder-guide'><b>Технический слой:</b><ol><li>добавьте технические блоки;</li><li>соедините “откуда → куда”;</li><li>результат и отчёт возьмут эту схему.</li></ol></div>
      <div class='quick-chain-presets'><button type='button' class='btn secondary' data-chain-preset='async'>API → DB task → Worker</button><button type='button' class='btn secondary' data-chain-preset='kafka'>Outbox → Event Stream → Inbox</button><button type='button' class='btn secondary' data-chain-preset='status'>UI → Aggregator → Sources → Cache</button><button type='button' class='btn secondary' data-chain-preset='legacy'>Legacy → File → Validation</button></div>
      <div class='builder-actions-row'><button type='button' class='btn secondary' id='addParticipantBtn'>+ Добавить участника</button><button type='button' class='btn secondary' id='addConnectionBtn'>+ Добавить связь</button><button type='button' class='btn ghost' id='resetCustomChainBtn'>Сбросить техсхему</button></div>
      <div class='role-palette' id='rolePalette'></div>
      <div class='builder-subhead'><h4>Технические участники</h4><span id='participantCounter'>0 участников</span></div><div class='participant-list' id='participantList'></div>
      <div class='connection-form' id='connectionForm'><label class='field'><span>Откуда</span><select id='connFrom'></select></label><label class='field'><span>Куда</span><select id='connTo'></select></label><label class='field'><span>Тип связи</span><select id='connType'><option>Запрос и быстрый ответ</option><option>Принять сейчас, обработать позже</option><option>Передать событие</option><option>Получить дополнительные данные</option><option>Получить ответ позже</option><option>Передать файл</option><option>Передать данные в отчётность</option><option>Собрать статус</option><option>Проверить текущее решение</option></select></label><label class='field'><span>При ошибке</span><select id='connError'><option>Повторить позже</option><option>Показать ошибку</option><option>Отправить в ручной разбор</option><option>Сохранить и обработать потом</option><option>Остановить процесс</option><option>Не знаю</option></select></label><div id='builderMessage' class='selected-link-note' style='display:none'></div></div>
      <div class='builder-subhead'><h4>Технические связи</h4><span id='connectionCounter'>0 связей</span></div><div class='connection-list' id='connectionList'></div><div class='manual-diagram' id='manualDiagram'></div>
    </details></div>
  </section>

  <section class='constructor-screen' data-constructor-screen='2'>
    <h2>3. Требования и ограничения</h2>
    <p class='small'>Эти ответы влияют на автоматическую техническую схему и рекомендации.</p>
    <div class='simple-question-grid' id='sixQuestions'>
      <label class='field'><span>Сколько участников процесса?</span><select data-map-hidden='simpleQSystemsHidden'><option>2</option><option selected>3</option><option>Больше 3</option><option>Не знаю</option></select></label>
      <label class='field'><span>Когда нужен результат?</span><select data-map-hidden='simpleQImmediateHidden'><option>Сразу</option><option>Можно позже</option><option selected>Принять сейчас, результат позже</option><option>Внешний ответ позже</option><option>Только для отчётности</option><option>Не знаю</option></select></label>
      <label class='field'><span>Что передаём / меняем?</span><select data-map-hidden='simpleQPayloadHidden'><option selected>Заявку / команду</option><option>Изменение данных</option><option>Статус</option><option>Документ / файл</option><option>Финансовые / договорные данные</option><option>Отчётные данные</option><option>Не знаю</option></select></label>
      <label class='field'><span>Что критичнее всего?</span><select data-map-hidden='simpleQRiskHidden'><option selected>Потерять данные</option><option>Получить дубль</option><option>Долго ждать</option><option>Получить устаревшие данные</option><option>Не восстановиться после ошибки</option><option>Всё важно</option><option>Не знаю</option></select></label>
      <label class='field'><span>Что делать при ошибке?</span><select data-map-hidden='simpleQErrorHidden'><option>Повторить позже</option><option>Показать ошибку</option><option selected>Сохранить и обработать потом</option><option>Отправить в ручной разбор</option><option>Компенсировать / откатить</option><option>Не знаю</option></select></label>
      <label class='field'><span>Нужно видеть статус процесса?</span><select data-map-hidden='simpleQStatusHidden'><option selected>Да</option><option>Нет</option><option>Желательно</option><option>Только для сотрудников</option><option>Не знаю</option></select></label>
    </div>
    <details class='case-questions-details' open><summary>Уточнить важное</summary><div id='caseSpecificQuestions' class='simple-question-grid'></div></details>
    <details class='case-questions-details' open><summary>Ограничения</summary><div class='chip-group' id='constraintsBox'>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='source_locked'> Source менять нельзя</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='no_new_service'> Нельзя создавать новый сервис</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='no_new_topic'> Нельзя создавать новый поток</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='highload'> Есть высокая нагрузка / пики</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='regulatory'> Есть регуляторика</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='pii'> Есть персональные данные</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='money'> Есть деньги / балансы / договоры</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='replay'> Нужен replay / backfill</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='manual'> Есть ручной разбор</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='many_consumers'> Есть несколько получателей</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='compensation'> Нужна компенсация / откат</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='unstable_external'> Внешний провайдер нестабилен</label>
      <div class='chip-group-title'>Дополнительные признаки сложного кейса</div>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='contract_change'> Контракт меняется / есть обязательные поля</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='shared_topic'> Один поток читают разные потребители</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='many_sources'> Несколько источников для одного экрана</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='callback_webhook'> Callback/webhook от внешней системы</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='exactly_once'> Нужно почти ровно один раз</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='privacy_erasure'> Удаление/исправление ПДн</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='multi_tenant'> Много клиентов/тенантов</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='active_active'> Active-active / несколько регионов</label>
      <label class='chip'><input type='checkbox' name='constraint_flags' value='migration'> Миграция / замена legacy</label>
    </div></details>
  </section>

  <section class='constructor-screen' data-constructor-screen='3'><h2>4. Система построила техническую схему</h2><div class='simple-result' id='autoSchemeReview'></div><div class='report-actions'><button type='button' class='btn' id='approveAutoScheme'>Всё верно</button><button type='button' class='btn secondary' id='editBusinessProcess'>Изменить бизнес-процесс</button><button type='button' class='btn ghost' id='openTechnicalConstructor'>Показать технический конструктор</button></div><div id='autoTechnicalConstructorHost'></div></section>
  <section class='constructor-screen' data-constructor-screen='4'><h2>5. Я понял задачу так</h2><div class='simple-result' id='understandingPreview'></div><div class='report-actions'><button type='button' class='btn' id='confirmUnderstanding'>Всё верно</button><button type='button' class='btn secondary' id='editAnswers'>Изменить требования</button><button type='button' class='btn ghost' id='openTechnicalConstructorReview'>Показать технический конструктор</button></div><div id='reviewTechnicalConstructorHost'></div></section>
  <section class='constructor-screen' data-constructor-screen='5'><h2>6. Результат</h2><p class='small'>Сначала бизнес-процесс, затем техническая схема, объяснение выбора, must-have, риски и handoff. Полный отчёт ниже.</p><div class='simple-result' id='resultBusinessProcess'></div><div class='simple-result' id='resultWhy'></div><div class='simple-result-grid four-blocks'><div class='simple-result'><h3>Схема взаимодействия</h3><div id='resultSchema'></div></div><div class='simple-result'><h3>Что обязательно сделать</h3><ul class='todo-list' id='resultMust'></ul></div><div class='simple-result'><h3>Главные риски</h3><ul class='todo-list' id='resultRisks'></ul></div><div class='simple-result'><h3>Что отдать разработке</h3><ul class='todo-list' id='resultHandoff'></ul></div></div><details class='expert-details legacy-questions-details'><summary>Показать технические детали</summary>%%SECTIONS%%</details><div class='nav visible-nav'><button class='btn secondary' type='button' id='prevBtn'>← Назад</button><button class='btn' type='submit' id='submitBtn'>Сформировать полный отчёт</button></div></section>
  <div class='nav constructor-nav' id='constructorNav'><button class='btn secondary' type='button' id='constructorPrev'>← Назад</button><button class='btn' type='button' id='constructorNext'>Далее →</button></div>
</form>
</div>
<style>
.no-text-app .constructor-screen{display:none}.no-text-app .constructor-screen.is-active{display:block}.business-case-grid .scenario-card .covers{display:block;margin-top:auto;color:#93c5fd;font-size:12px;line-height:1.45;border-top:1px solid rgba(148,163,184,.18);padding-top:8px}.scenario-card-grid.compact{grid-template-columns:repeat(3,minmax(0,1fr))}.four-blocks{grid-template-columns:repeat(4,minmax(0,1fr))}.case-questions-details{border:1px solid var(--border);border-radius:16px;background:#0b1220;margin:14px 0;padding:0}.case-questions-details summary{cursor:pointer;padding:14px 16px;font-weight:800}.case-questions-details>div{padding:0 16px 16px}.constructor-nav{display:flex}.visible-nav{display:none}.no-text-app.result-screen .visible-nav{display:flex}.no-text-app.result-screen .constructor-nav{display:none}.interaction-diagram{border:1px solid rgba(34,211,238,.24);border-radius:18px;background:linear-gradient(180deg,rgba(8,47,73,.34),rgba(7,17,31,.96));padding:14px;margin:10px 0;overflow-x:auto}.diagram-track{display:flex;align-items:stretch;gap:10px;min-width:max-content}.diagram-node{width:176px;min-height:112px;border:1px solid #334155;border-radius:16px;background:linear-gradient(180deg,#111827,#0b1220);box-shadow:0 10px 28px rgba(0,0,0,.25);padding:12px}.diagram-node-main{border-color:#22d3ee}.diagram-node-db{border-color:#38bdf8;background:linear-gradient(180deg,rgba(14,116,144,.26),#0b1220)}.diagram-node-worker{border-color:#a78bfa;background:linear-gradient(180deg,rgba(76,29,149,.28),#0b1220)}.diagram-node-error{border-color:#f59e0b;background:linear-gradient(180deg,rgba(120,53,15,.30),#0b1220)}.diagram-icon{width:34px;height:34px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:#083344;color:#67e8f9;font-weight:900;margin-bottom:8px}.diagram-title{font-weight:900;color:#fff;font-size:14px}.diagram-role{font-size:12px;color:#9ca3af;margin-top:6px;line-height:1.35}.diagram-edge{display:flex;align-items:center;justify-content:center;min-width:36px;color:#67e8f9;font-size:28px;font-weight:900}.diagram-side{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.diagram-chip{border:1px solid #164e63;background:#082f49;color:#cffafe;border-radius:999px;padding:5px 8px;font-size:11px}.business-actions-row,.builder-actions-row,.quick-chain-presets{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.participant-card,.connection-card,.chain-template-card,.storage-option{border:1px solid var(--border);background:#0b1220;color:#e5e7eb;border-radius:16px;padding:14px;display:flex;flex-direction:column;gap:7px}.participant-card *,.connection-card *,.chain-template-card *,.storage-option *{color:inherit}.role-palette{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}.role-palette button{border:1px solid var(--border);background:#0b1220;color:#e5e7eb;border-radius:14px;padding:10px;text-align:left}.builder-subhead{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px}.connection-edit-row{display:flex;gap:8px;flex-wrap:wrap}.mini-action{border:1px solid var(--border);border-radius:999px;background:#111827;color:#e5e7eb;padding:6px 10px}.business-summary-list{display:grid;gap:8px}.business-summary-list .connection-card b{color:#fff}.result-human-page .simple-result:first-child{grid-column:span 2}@media(max-width:900px){.scenario-card-grid.compact,.four-blocks,.role-palette{grid-template-columns:1fr}.constructor-nav{position:fixed;left:0;right:0;bottom:0;background:#07111f;border-top:1px solid var(--border);padding:10px;z-index:20}.constructor-nav .btn{width:50%}.diagram-track{min-width:0;display:grid;grid-template-columns:1fr}.diagram-node{width:auto;min-height:0}.diagram-edge{min-width:0;transform:rotate(90deg);height:28px}.interaction-diagram{overflow-x:visible}.no-text-app .scenario-card{min-height:142px}}
</style>
<script>
(function(){
const CASES={sync_rest:{title:'Быстрый внешний/внутренний запрос',schema:'Internal Service → External API',task:'new_from_scratch',must:['request timeout','error mapping','correlationId','retry только для безопасных запросов','fallback/manual check'],risks:['timeout внешней зависимости','ошибка партнёра','повтор запроса','нет трассировки'],handoff:['API contract','timeout/error mapping','safe retry rules','fallback/manual check','contract tests'],summary:'Данные нужны сразу, поэтому подходит короткий синхронный запрос с явными timeout и обработкой ошибок.'},async_worker:{title:'Заявка или долгий процесс с обработкой позже',schema:'Client/UI → Service API → integration_task DB → Worker → Target Service → Status DB',task:'e2e_chain',must:['trackingId','status model','idempotencyKey','correlationId','integration_task DB','retry','manual recovery','GET /status','monitoring stuck tasks'],risks:['дубль заявки','потеря задачи','падение обработчика','зависший статус','недоступность целевого сервиса'],handoff:['API contract','task table','status model','retry rules','idempotency rules','worker processing rules','test cases'],summary:'Запрос нужно принять быстро, а обработку можно выполнить позже; поэтому нужен статус, восстановление и контроль зависших задач.'},event_kafka:{title:'Рассылка изменения данных другим системам',schema:'Source Service → Business DB → Outbox → Publisher → Event Stream → Consumer → Inbox → Target Service',task:'event_domain',must:['transactional outbox','eventId','aggregateId','occurredAt','version','publisher','event stream / topic','consumer','inbox/idempotency','retry','DLQ/manual recovery','schema validation','consumer lag'],risks:['потеря события','дубль события','получатель отстаёт','сломанная схема события','нет replay/reprocess'],handoff:['event schema','outbox table','publisher rules','consumer inbox','partition/key strategy','DLQ/reprocess','schema compatibility','test cases'],summary:'Изменение должно быть доставлено надёжно, получателей может быть несколько, дубли должны быть безопасны.'},enrichment_kafka:{title:'Дополнение данных перед следующим шагом',schema:'Source Process → Enrichment Step → Target Step',task:'event_domain',must:['варианты места обогащения','enrichment-worker/adaptor','контроль свежести данных','retry enrichment','fallback','manual recovery','контракт enrichment-запроса'],risks:['источник данных недоступен','данные устарели','дорогие изменения source','лишняя связность'],handoff:['варианты source/worker/adapter/consumer','правила свежести','retry/fallback','контракт обогащения','тесты недоступности'],summary:'Перед продолжением процесса нужны дополнительные данные; надо выбрать место обогащения и сценарий недоступности источника.'},callback:{title:'Внешний ответ позже',schema:'Internal Service → External API → Callback API → Status DB',task:'external_partner',must:['requestId/trackingId','callback endpoint','signature/auth validation','idempotency callback','status DB','timeout ожидания','polling fallback','audit'],risks:['callback не пришёл','callback пришёл повторно','callback подделан','статус завис'],handoff:['external request contract','callback endpoint contract','status model','signature validation','polling fallback','audit log'],summary:'Внешняя система не отдаёт финальный результат сразу, поэтому нужен trackingId, callback и статус ожидания.'},dwh:{title:'Передача данных в отчётность',schema:'Source System → Export/CDC → Staging → DWH/Reporting → Reconciliation',task:'dwh_analytics',must:['batch/CDC mode','watermark','deduplication','reconciliation','data quality checks','lineage','reload/backfill','контроль полноты'],risks:['неполная загрузка','дубли','плохое качество данных','невозможно переиграть данные','нет сверки с source'],handoff:['формат выгрузки','watermark','правила сверки','backfill procedure','data quality checks'],summary:'Данные нужны для отчётного контура, поэтому важны контроль полноты, качество данных и возможность повторной загрузки.'},legacy_file:{title:'Legacy / файловый обмен',schema:'Legacy System → File Export → Validation/Checksum → Quarantine → Target System',task:'legacy_integration',must:['file_id','checksum','batch_id','file registry','validation','quarantine','reprocessing','manual recovery'],risks:['битый файл','дубли файла','ошибочные строки','невозможно переобработать','ручная загрузка без контроля'],handoff:['формат файла','checksum','file registry','quarantine','reprocessing','manual recovery'],summary:'Старая система отдаёт файл; нужны проверка целостности, реестр загрузок, карантин ошибок и переобработка.'},status_aggregation:{title:'Показ итогового статуса',schema:'Client/UI → Status Aggregation → Service A / Service B / Service C → Cache/Read Model',task:'new_from_scratch',must:['BFF/API Composition contract','per-source timeout','partial response','Cache/Read Model','freshness marker','fallback','correlationId','latency/error metrics per source'],risks:['один источник тормозит','часть статуса недоступна','статус устарел','непонятно какой источник сломался'],handoff:['aggregation contract','status model','timeout/fallback policy','cache/read model rules','freshness marker','per-source metrics'],summary:'Статус собирается из нескольких источников, поэтому нужны частичный ответ, таймауты по источникам и отметка свежести.'},audit:{title:'Проверка текущего решения',schema:'Current Solution → Risk Review → Target Improvements → Developer Handoff',task:'audit_existing_solution',must:['текущая схема','найденные риски','критичность рисков','варианты улучшения','компромиссы','что оставить как есть','что исправить обязательно'],risks:['дубли','потери','таймауты','нет идемпотентности','нет восстановления','нет трассировки'],handoff:['risk register','список blockers','варианты исправления','тест-кейсы','ADR по изменениям'],summary:'Нужно проверить текущее решение, найти риски и отделить обязательные исправления от улучшений.'}};
const BUSINESS_TO_CASE={application_creation:'async_worker',data_change_distribution:'event_kafka',external_check:'callback',data_enrichment:'enrichment_kafka',status_screen:'status_aggregation',reporting:'dwh',legacy_file:'legacy_file',audit:'audit',long_process:'async_worker'};
let step=0,current='async_worker',businessCase='application_creation';let businessActors=[],businessSteps=[],activeBusinessStepIndex=-1;let customParticipants=[],customConnections=[];
const app=document.getElementById('appShell'),start=document.getElementById('startScreen');
function esc(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]))}function setHidden(id,v){const e=document.getElementById(id);if(e)e.value=v}function setText(id,v){const e=document.getElementById(id);if(e)e.textContent=v}function setHtml(id,v){const e=document.getElementById(id);if(e)e.innerHTML=v}function bullets(a){return (a||[]).map(x=>'<li>'+esc(x)+'</li>').join('')}function selected(id){const e=document.getElementById(id);return e?e.value:''}
function nodeClass(name){const n=String(name).toLowerCase();if(n.includes('db')||n.includes('outbox')||n.includes('inbox')||n.includes('staging')||n.includes('dwh')||n.includes('cache')||n.includes('state'))return 'diagram-node-db';if(n.includes('worker')||n.includes('publisher')||n.includes('consumer')||n.includes('adapter')||n.includes('aggregation')||n.includes('coordinator'))return 'diagram-node-worker';if(n.includes('manual')||n.includes('recovery')||n.includes('quarantine')||n.includes('callback')||n.includes('compensation'))return 'diagram-node-error';return 'diagram-node-main'}function iconFor(name){const n=String(name).toLowerCase();if(n.includes('db')||n.includes('dwh')||n.includes('cache'))return '▣';if(n.includes('worker')||n.includes('coordinator'))return '⚙';if(n.includes('event')||n.includes('stream'))return '⇄';if(n.includes('file'))return '▤';if(n.includes('callback'))return '↩';return '●'}function diagramHtml(schema){const nodes=String(schema||'').split('→').map(x=>x.trim()).filter(Boolean);return '<div class="interaction-diagram"><div class="diagram-track">'+nodes.map((n,i)=>'<div class="diagram-node '+nodeClass(n)+'"><div class="diagram-icon">'+iconFor(n)+'</div><div class="diagram-title">'+esc(n)+'</div><div class="diagram-role">'+(i===0?'Запускает поток':i===nodes.length-1?'Получает результат':'Обрабатывает и передаёт дальше')+'</div></div>'+(i<nodes.length-1?'<div class="diagram-edge">→</div>':'')).join('')+'</div><div class="diagram-side"><span class="diagram-chip">ошибка/retry</span><span class="diagram-chip">статус</span><span class="diagram-chip">ручной разбор</span></div></div>'}
function updateCase(c){if(c==='helper')c='async_worker';current=CASES[c]?c:'async_worker';const d=CASES[current];setHidden('simpleSituationHidden',current);setHidden('taskTypeHidden',d.task);setHidden('businessGoalHidden',businessGoalText());setHidden('systemsMatrixHidden',matrixSystems(d.schema));setHidden('processStepsHidden',matrixSteps(d.schema));setHidden('targetIntegrationHidden',matrixTarget(d.schema));setHidden('contractMatrixHidden',(current==='event_kafka'||current==='enrichment_kafka')?'EVENT | Contract.v1 | producer | consumer | stream | key | id,correlationId | metadata | validation_error | v1 | backward':'API | Contract.v1 | caller | callee | endpoint | method | id,correlationId | metadata | timeout,error | v1 | backward');setHidden('errorMatrixHidden','timeout | dependency | blocking | yes | retry/manual recovery | TBD\\nduplicate | boundary | non_blocking | no | idempotency | TBD');setHidden('processGraphJson',JSON.stringify({case_type:current,schema:d.schema,nodes:d.schema.split('→').map((x,i)=>({id:'N'+(i+1),title:x.trim()}))}));renderCaseQuestions();renderAll()}
function matrixSystems(schema){return schema.split('→').map((p,i)=>p.trim()+' | '+(i===0?'инициатор/источник':'участник процесса')+' | TBD | important | selected | '+(i===0?'blocking':'non_blocking')+' | уточнить').join('\\n')}function matrixSteps(schema){return schema.split('→').map((p,i)=>'1 | '+(i+1)+' | '+(i?'prev':'root')+' | '+p.trim()+' выполняет шаг процесса | '+p.trim()+' | selected | input | output | уточнить | yes | manual recovery | '+(i===0?'blocking':'non_blocking')+' | TBD').join('\\n')}function matrixTarget(schema){const parts=schema.split('→').map(x=>x.trim());return parts.slice(0,-1).map((p,i)=>p+' | '+parts[i+1]+' | selected | selected | business trigger | payload | Contract.v1 | уточнить | yes | 3 | manual | idempotencyKey+correlationId | service auth | уточнить | TBD').join('\\n')}
function normalizeBusinessSteps(){businessSteps=businessSteps.map((s,i)=>{const actorLabel=s.actorLabel||s.actor||'Система';return Object.assign({},s,{id:s.id||('BS'+Date.now()+Math.random()),order:i+1,actorId:s.actorId||'',actorLabel,actor:actorLabel,action:s.action||'Проверяет данные',object:s.object||selected('businessObjectSelect')||'Заявка',result:s.result||selected('businessResultSelect')||'',timing:s.timing||selected('businessTimingSelect')||'',errorBehavior:s.errorBehavior||selected('simpleQErrorHidden')||''})})}
function syncBusinessActorSelect(){const sel=document.getElementById('businessStepActorSelect');if(!sel)return;const currentVal=sel.value;const opts=businessActors.map(a=>'<option value="'+esc(a.id)+'">'+esc(a.name)+'</option>').join('');sel.innerHTML=opts||'<option value="">Система</option>';if(currentVal && businessActors.some(a=>a.id===currentVal))sel.value=currentVal}
function addBusinessActor(){const role=selected('businessActorRole')||'Внутренняя система';const count=businessActors.filter(a=>a.role===role).length+1;businessActors.push({id:'BA'+Date.now()+Math.random(),role,name:role.replace(' / партнёр','')+(count>1?' '+count:'')});syncBusiness()}
function currentBusinessStepPayload(existing){const sel=document.getElementById('businessStepActorSelect');const actorObj=businessActors.find(a=>a.id===(sel?sel.value:''))||businessActors[0]||{id:'',name:'Система'};return Object.assign({},existing||{}, {id:(existing&&existing.id)||'BS'+Date.now()+Math.random(),actorId:actorObj.id||'',actorLabel:actorObj.name||'Система',actor:actorObj.name||'Система',action:selected('businessStepAction'),object:selected('businessObjectSelect'),result:selected('businessResultSelect'),timing:selected('businessTimingSelect'),errorBehavior:(document.getElementById('simpleQErrorHidden')||{}).value||''})}
function addBusinessStep(){if(activeBusinessStepIndex>=0&&activeBusinessStepIndex<businessSteps.length){businessSteps[activeBusinessStepIndex]=currentBusinessStepPayload(businessSteps[activeBusinessStepIndex]);activeBusinessStepIndex=-1}else{businessSteps.push(currentBusinessStepPayload())}normalizeBusinessSteps();syncBusiness()}
function resetBusiness(){businessActors=[];businessSteps=[];activeBusinessStepIndex=-1;syncBusiness()}
function businessStepText(s){return (s.actorLabel||s.actor||'Система')+' '+String(s.action||'выполняет шаг').toLowerCase()+(s.object?' · объект: '+s.object:'')}
function defaultBusinessProcess(){const map={application_creation:'Клиент создаёт заявку → система принимает → обработка выполняется позже → статус обновляется',data_change_distribution:'В одной системе меняются данные → другие системы должны узнать об изменении',external_check:'Система отправляет запрос внешнему партнёру → получает ответ → обновляет статус',data_enrichment:'Процесс получает данные → дополняет недостающие сведения → передаёт дальше',status_screen:'Пользователь открывает экран → система собирает статусы → показывает итог',reporting:'Система выгружает данные → отчётный контур проверяет полноту → строит отчёт',legacy_file:'Старая система формирует файл → файл проверяется → валидные данные передаются дальше',audit:'Текущее решение описывается → риски проверяются → формируются улучшения',long_process:'Инициатор запускает процесс → выполняются шаги → возможна компенсация → ручное восстановление'};return map[businessCase]||map.application_creation}
function businessSchema(){normalizeBusinessSteps();return businessSteps.length?businessSteps.map(s=>(s.actorLabel||s.actor||'Система')+' '+String(s.action||'выполняет шаг').toLowerCase()).join(' → '):defaultBusinessProcess()}
function businessOrderedListHtml(){normalizeBusinessSteps();return businessSteps.length?'<ol class="ordered-business-list">'+businessSteps.map(s=>'<li>'+esc((s.actorLabel||s.actor||'Система')+' '+String(s.action||'').toLowerCase()+(s.object?' — '+s.object:''))+'</li>').join('')+'</ol>':'<p>'+esc(defaultBusinessProcess())+'</p>'}
function businessFlowHtml(){normalizeBusinessSteps();const steps=businessSteps.length?businessSteps:null;if(!steps)return diagramHtml(defaultBusinessProcess());return '<div class="business-flow-list">'+steps.map((s,i)=>'<div class="business-flow-step"><b>['+esc(s.actorLabel||s.actor||'Система')+']</b><span>'+esc(s.action||'выполняет шаг')+(s.object?' · '+esc(s.object):'')+'</span></div>'+(i<steps.length-1?'<div class="business-flow-arrow">↓</div>':'')).join('')+'</div>'}
function businessGoalText(){return 'Бизнес-процесс по порядку: '+businessSchema()+'. Объект: '+selected('businessObjectSelect')+'. Результат нужен: '+selected('businessTimingSelect')+'. Итог: '+selected('businessResultSelect')+'. Критично: '+(document.getElementById('simpleQRiskHidden')||{}).value+'. Ограничения: '+constraints().join(', ')}
function constraints(){return Array.from(document.querySelectorAll('input[name="constraint_flags"]:checked')).map(x=>x.value)}
function constraintExtras(){const c=constraints();let out=[];if(c.includes('source_locked'))out.push('adapter/orchestrator или минимальное изменение source');if(c.includes('no_new_topic'))out.push('shared topic / consumer filtering','discard rate','processing time','consumer lag');if(c.includes('compensation'))out.push('process state machine','compensation step','compensation_failed','owner восстановления');if(c.includes('highload'))out.push('partitioning/scaling','backpressure','rate limits','load test');if(c.includes('regulatory')||c.includes('pii')||c.includes('money'))out.push('audit trail','access control','masking','retention','change history');if(c.includes('replay'))out.push('replay procedure','backfill window','deduplication','watermark','reconciliation');if(c.includes('many_consumers'))out.push('fan-out / несколько получателей','consumer idempotency','schema compatibility');return out}
function stepIndexIncludes(txt){txt=txt.toLowerCase();return businessSteps.findIndex(s=>(String(s.action)+' '+String(s.actorLabel||s.actor)+' '+String(s.object)).toLowerCase().includes(txt))}
function validateBusinessStepOrder(){normalizeBusinessSteps();const warnings=[];const transfer=stepIndexIncludes('передаёт данные дальше'),check=stepIndexIncludes('проверяет данные');if(transfer>=0&&check>=0&&transfer<check)warnings.push('Данные передаются до проверки. Проверьте, допустимо ли это.');const upd=stepIndexIncludes('обновляет статус'),later=stepIndexIncludes('получает ответ позже');if(upd>=0&&later>=0&&upd<later)warnings.push('Статус обновляется до получения финального ответа. Возможно, нужен промежуточный статус.');const comp=stepIndexIncludes('компенсирует'),manual=stepIndexIncludes('ручной разбор'),status=stepIndexIncludes('статус');if(comp>=0&&manual<0&&status<0)warnings.push('Есть компенсация, но не указан ручной разбор или статусная модель.');const report=stepIndexIncludes('отчётность'),finish=stepIndexIncludes('завершает процесс');if(report>=0&&finish>=0&&report<finish)warnings.push('Данные уходят в отчётность до завершения процесса. Нужен признак актуальности/финальности.');const statusNeed=(document.getElementById('simpleQStatusHidden')||{}).value||'Да';if(later>=0&&statusNeed==='Нет')warnings.push('Есть отложенный ответ, но статус процесса не нужен. Проверьте, как пользователь узнает результат.');const external=businessSteps.findIndex(s=>String(s.actorLabel||s.actor).toLowerCase().includes('внеш'));if(external>=0&&check>=0&&external<check)warnings.push('Проверка данных стоит после внешнего вызова. Это может быть риском: внешняя система получит непроверенные данные.');return warnings}
function warningHtml(w){return w&&w.length?'<div class="warning-list"><b>Риски порядка шагов</b><ul>'+w.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>':''}
function techNodeForStep(s,i){const t=(String(s.action)+' '+String(s.actorLabel||s.actor)).toLowerCase();if(t.includes('клиент')||t.includes('пользователь')||t.includes('открывает экран')||t.includes('создаёт'))return 'Client/UI';if(t.includes('проверяет')||t.includes('валида'))return 'Validation / Check Step';if(t.includes('внеш')||t.includes('ответ позже')||t.includes('обрабатывает запрос'))return 'External Service / Worker';if(t.includes('статус')||t.includes('фиксирует'))return 'Status DB';if(t.includes('отчёт'))return 'DWH / Reporting';if(t.includes('файл')||t.includes('старая'))return i===0?'Legacy System':'File Validation';if(t.includes('несколько')||t.includes('получател'))return 'Event Stream / Consumers';if(t.includes('дополняет')||t.includes('обогащ'))return 'Enrichment Step';return i===0?'Service API':'Service Step'}
function businessTechnicalSchema(defaultSchema){normalizeBusinessSteps();if(!businessSteps.length)return defaultSchema;let nodes=[];businessSteps.forEach((s,i)=>{const n=techNodeForStep(s,i);if(!nodes.length||nodes[nodes.length-1]!==n)nodes.push(n)});if(!nodes.includes('Service API'))nodes.splice(Math.min(1,nodes.length),0,'Service API');return nodes.join(' → ')}
function addUnique(arr,v){if(v&&!arr.includes(v))arr.push(v)}
function validateActorActionPairs(){normalizeBusinessSteps();const warnings=[];businessSteps.forEach(s=>{const actor=String(s.actorLabel||s.actor||'').toLowerCase();const action=String(s.action||'').toLowerCase();if(actor.includes('клиент')||actor.includes('пользователь')){if(action.includes('принимает заявку'))warnings.push('Клиент обычно создаёт/отправляет заявку, а принимает её внутренняя система.');if(action.includes('проверяет данные'))warnings.push('Проверку обычно выполняет система или сотрудник.');if(action.includes('обновляет статус'))warnings.push('Статус процесса обычно обновляет система.')}if(actor.includes('внешняя система')&&action.includes('принимает заявку'))warnings.push('Если внешняя система принимает заявку, уточните, кто владелец процесса и статуса.')});return Array.from(new Set(warnings))}
function buildScenarioFacetsFromBusiness(){normalizeBusinessSteps();const flags=constraints();const situations=[];const facets={business_situations:situations,allowed_channels:[],forbidden_channels:[],current_controls:[]};const timing=selected('businessTimingSelect');const obj=selected('businessObjectSelect');const risk=(document.getElementById('simpleQRiskHidden')||{}).value||'';const txt=(businessSchema()+' '+obj+' '+timing).toLowerCase();const has=f=>flags.includes(f);const add=(...xs)=>xs.forEach(x=>addUnique(situations,x));if(businessCase==='application_creation'){add('application_or_order_creation');facets.operation_kind='command_create_update';if(timing.includes('позже')){add('multi_step_business_process','async_heavy_processing','long_running_process');facets.result_model='tracking'}}if(businessCase==='data_change_distribution'||has('many_consumers')){add('data_synchronization','one_source_many_consumers');facets.operation_kind='event_publish';facets.result_model='notification';facets.allowed_channels=['kafka','queue'];if(has('no_new_topic')||has('shared_topic')){add('shared_topic_selective_consumer');facets.forbidden_channels.push('new_topic_forbidden');facets.kafka_topology='single_topic_only'}if(has('highload'))add('highload_write_stream','peak_load_process')}if(businessCase==='data_enrichment'||txt.includes('дополняет')||txt.includes('справоч')){add('data_enrichment','event_enrichment_before_publish');facets.operation_kind='event_enrichment';if(has('source_locked')){add('source_lacks_kafka');facets.source_change_policy='minimal_table_only'}}if((businessCase==='external_check'&&timing.includes('позже'))||txt.includes('получает ответ позже')||has('callback_webhook')){add('external_api_dependency','webhook_callback');facets.result_model='callback';facets.task_type='external_partner';if(has('unstable_external'))add('unstable_external_provider')}if(businessCase==='status_screen'||has('many_sources')||txt.includes('собирает статус')){add('client_status_screen','multi_source_aggregation','api_composition','read_model');facets.operation_kind='bff_composition';facets.partial_response_ok='yes';if(has('highload'))add('highload_read')}if(businessCase==='reporting'||txt.includes('отчёт')||txt.includes('отчет')){add('dwh_reporting','batch_processing');facets.operation_kind='dwh_offload';facets.task_type='dwh_analytics';facets.replay='yes';facets.retention='required'}if(businessCase==='legacy_file'||txt.includes('файл')||has('migration')){add('legacy_integration','batch_processing');facets.operation_kind='batch_file_exchange'}if(businessCase==='audit'){add('existing_solution_audit');facets.task_type='audit_existing_solution'}if(businessCase==='long_process'||has('compensation')||txt.includes('компенс')||txt.includes('откат')){add('long_running_process','distributed_transaction_saga','multi_step_business_process','manual_recovery_required');facets.orchestration='orchestrator';facets.result_model='tracking'}if(has('contract_change')){add('contract_breaking_change','contract_required_field_missing');facets.task_type='contract_change'}if(has('money')){add('financial_operation');facets.money_impact='yes'}if(has('regulatory')){add('regulatory_process');facets.regulatory_impact='yes'}if(has('pii')){add('personal_data_exchange');facets.sensitivity='personal'}if(has('active_active')&&has('money')&&has('highload')){add('active_active_financial_write','financial_operation','exactly_once_required');facets.delivery='business_exactly_once';facets.consistency='strong_on_write'}if(has('privacy_erasure'))add('privacy_erasure','personal_data_exchange','regulatory_process');if(has('multi_tenant'))add('multi_tenant_noisy_neighbor','shared_topic_selective_consumer');if(has('migration')){add('migration_or_strangler','legacy_integration');facets.task_type='replace_legacy'}if(has('highload')&&(facets.operation_kind==='event_publish'||txt.includes('событ'))){add('highload_stream_ingestion','highload_write_stream');facets.load_profile='highload'}if(has('replay'))facets.replay='yes';if(has('exactly_once')||risk.includes('Потерять данные')||risk.includes('Получить дубль'))facets.delivery='business_exactly_once';facets.step_count=String(businessSteps.length||0);facets.chain_depth=businessSteps.length>=4?'multi_level':'single_level';return facets}
function specializedCaseFromFacets(base,facets){const s=facets.business_situations||[];if(s.includes('active_active_financial_write'))return 'active_active_financial_write';if(s.includes('privacy_erasure'))return 'privacy_erasure_pipeline';if(s.includes('multi_tenant_noisy_neighbor'))return 'multi_tenant_noisy_neighbor';if(s.includes('migration_or_strangler'))return 'strangler_migration';if(s.includes('contract_required_field_missing'))return 'contract_required_field_missing';if(s.includes('shared_topic_selective_consumer'))return 'shared_topic_selective_consumer';if(s.includes('event_enrichment_before_publish'))return 'enrichment_before_kafka';if(s.includes('webhook_callback'))return 'webhook_intake';if(s.includes('distributed_transaction_saga'))return 'saga_state_machine';if(s.includes('client_status_screen')||s.includes('multi_source_aggregation'))return 'bff_api_composition';if(s.includes('highload_stream_ingestion'))return 'highload_stream_ingestion';if(s.includes('dwh_reporting'))return 'dwh_pipeline';if(s.includes('legacy_integration')&&s.includes('batch_processing'))return 'batch_file_exchange';if(s.includes('existing_solution_audit'))return 'existing_solution_audit';return base}
function buildCanonicalSchemaForCase(caseType){const schemas={async_worker:'Client/UI → Application API → integration_task DB → Worker → Target Service → Status DB',saga_state_machine:'Initiator → Process Coordinator → Process State DB → Step Services → Compensation / Manual Recovery',event_kafka:'Source Service → Business DB → Outbox → Publisher → Event Stream → Consumer → Inbox → Target Service',shared_topic_selective_consumer:'Shared Event Stream → Selective Consumer → Filter → Inbox/Dedup Sink → Target Service → DLQ/Reprocess',enrichment_before_kafka:'Source Service → Source-owned Outbox → Integration Publisher → REST Enrichment API → Event Stream → Consumer',webhook_intake:'External/Internal Request → External Provider → Callback API → Inbox → Async Worker → Status DB',bff_api_composition:'Client/UI → BFF/API Composition → Source Services → Cache/Read Model → Partial Response',dwh_pipeline:'Source System → CDC/Export → Staging → Data Quality → DWH/Reporting → Reconciliation',batch_file_exchange:'Legacy System → File Export → Manifest/Checksum → Staging → Validation → Quarantine/Target',contract_required_field_missing:'Contract Source → Compatibility Check → Consumer Contract Tests → Runtime Validation → Rollout',active_active_financial_write:'Region API → Operation State Machine → Single Writer/Ledger → Replication/Read Model → Reconciliation',privacy_erasure_pipeline:'Erasure Request API → Policy/Legal Hold Check → Per-System Erasure Tasks → Receipts → Audit/Reconciliation',highload_stream_ingestion:'Producers → Event Stream Partitions → Stream Processing → Idempotent Sink → Alerting/Consumers → DWH Downstream',multi_tenant_noisy_neighbor:'Shared Stream → Tenant-aware Consumer Pool → Per-tenant Quotas → Isolated Sink/Inbox → Lag Metrics',strangler_migration:'Client/System → Facade → New Service + Legacy → Shadow Compare → Feature Flag Cutover → Rollback/Reconciliation',existing_solution_audit:'Current Solution → Risk Review → Keep/Fix Decisions → Phased Remediation → Regression Tests'};return schemas[caseType]||''}
function syncScenarioFacetHidden(f){setHidden('businessSituationsHidden',(f.business_situations||[]).join(','));setHidden('operationKindHidden',f.operation_kind||'');setHidden('resultModelHidden',f.result_model||'');setHidden('deliveryHidden',f.delivery||'');setHidden('loadProfileHidden',f.load_profile||'');setHidden('sensitivityHidden',f.sensitivity||'');setHidden('moneyImpactHidden',f.money_impact||'');setHidden('regulatoryImpactHidden',f.regulatory_impact||'');setHidden('sourceChangePolicyHidden',f.source_change_policy||'');setHidden('allowedChannelsHidden',(f.allowed_channels||[]).join(','));setHidden('forbiddenChannelsHidden',(f.forbidden_channels||[]).join(','));setHidden('orchestrationHidden',f.orchestration||'');setHidden('stepCountHidden',f.step_count||'');setHidden('chainDepthHidden',f.chain_depth||'');setHidden('partialResponseOkHidden',f.partial_response_ok||'');setHidden('replayHidden',f.replay||'');setHidden('retentionHidden',f.retention||'');setHidden('currentControlsHidden',(f.current_controls||[]).join(','));setHidden('kafkaTopologyHidden',f.kafka_topology||'');setHidden('consistencyHidden',f.consistency||'')}
function buildTechnicalChainFromBusiness(){normalizeBusinessSteps();let c=BUSINESS_TO_CASE[businessCase]||current;const timing=selected('businessTimingSelect');if(businessCase==='external_check' && timing==='Сразу на экране')c='sync_rest';if(businessCase==='external_check' && timing==='Внешняя система ответит позже')c='callback';if(businessCase==='long_process')c='async_worker';if(businessSteps.some(s=>String(s.action).toLowerCase().includes('получает ответ позже'))||timing==='Нужно принять сейчас, результат получить позже')c=(businessCase==='external_check')?'callback':'async_worker';if(businessSteps.some(s=>String(s.actorLabel||s.actor).toLowerCase().includes('несколько получателей')))c='event_kafka';if(businessSteps.some(s=>String(s.action).toLowerCase().includes('дополняет')))c='enrichment_kafka';if(businessSteps.some(s=>String(s.action).toLowerCase().includes('отчёт')))c='dwh';if(businessSteps.some(s=>String(s.object).toLowerCase().includes('файл')))c='legacy_file';const facets=buildScenarioFacetsFromBusiness();syncScenarioFacetHidden(facets);const specialized=specializedCaseFromFacets(c,facets);current=c;const d=CASES[c]||CASES.async_worker;const specializedIsReal=!!(specialized&&specialized!==c);const canonical=buildCanonicalSchemaForCase(specialized);let schema=canonical||d.schema;if(!specializedIsReal){schema=businessTechnicalSchema(schema);}const warnings=Array.from(new Set(validateBusinessStepOrder().concat(validateActorActionPairs())));const processPayload={schema:businessSchema(),case:businessCase,actors:businessActors,steps:businessSteps,warnings,scenario_facets:facets,specialized_case:specialized};setHidden('businessCaseHidden',businessCase);setHidden('businessProcessJson',JSON.stringify(processPayload));setHidden('businessActorsJson',JSON.stringify(businessActors));setHidden('businessStepsJson',JSON.stringify(businessSteps));setHidden('businessObjectHidden',selected('businessObjectSelect'));setHidden('businessResultTimingHidden',timing);setHidden('businessResultTypeHidden',selected('businessResultSelect'));setHidden('businessConstraintsJson',JSON.stringify(constraints()));setHidden('businessCriticalityHidden',(document.getElementById('simpleQRiskHidden')||{}).value||'Потерять данные');setHidden('businessGoalHidden',businessGoalText());setHidden('simpleSituationHidden',c);setHidden('taskTypeHidden',facets.task_type||d.task);setHidden('systemsMatrixHidden',matrixSystems(schema));setHidden('processStepsHidden',matrixSteps(schema));setHidden('targetIntegrationHidden',matrixTarget(schema));setHidden('errorMatrixHidden','timeout | dependency | blocking | yes | retry/manual recovery | TBD\\nduplicate | boundary | non_blocking | no | idempotency | TBD\\norder_warning | business_process | non_blocking | no | '+warnings.join('; ')+' | business owner');setHidden('processGraphJson',JSON.stringify({case_type:c,specialized_case:specialized,business_case:businessCase,business_schema:businessSchema(),schema,nodes:schema.split('→').map((x,i)=>({id:'N'+(i+1),title:x.trim()})),business_steps:businessSteps,constraints:constraints(),scenario_facets:facets,warnings}));setHidden('autoGeneratedTechnicalChainJson',JSON.stringify({case_type:c,specialized_case:specialized,schema,business_schema:businessSchema(),steps:businessSteps,constraints:constraints(),scenario_facets:facets,warnings}));return {case_type:c,specialized_case:specialized,schema,business_schema:businessSchema(),warnings}}
function renderBusinessProcess(){const built=buildTechnicalChainFromBusiness();const w=warningHtml(built.warnings);document.getElementById('businessDiagram').innerHTML='<h4>Бизнес-процесс</h4>'+businessFlowHtml()+w}
function renderBusinessPreview(){const built=buildTechnicalChainFromBusiness();document.getElementById('autoTechnicalPreview').innerHTML='<h4>Автоматически построенная техническая схема</h4>'+diagramHtml(built.schema)+warningHtml(built.warnings)+'<p class="small">Технический конструктор ниже можно открыть и поправить, но это не требуется для обычного заполнения.</p>'}
function moveBusinessStep(index,direction){const next=index+direction;if(next<0||next>=businessSteps.length)return;const tmp=businessSteps[index];businessSteps[index]=businessSteps[next];businessSteps[next]=tmp;normalizeBusinessSteps();syncBusinessProcess();buildTechnicalChainFromBusiness();renderBusinessProcess();renderBusinessPreview();renderAll()}
function editBusinessStep(index){normalizeBusinessSteps();const s=businessSteps[index];if(!s)return;activeBusinessStepIndex=index;syncBusinessActorSelect();const actorSel=document.getElementById('businessStepActorSelect');if(actorSel&&s.actorId)actorSel.value=s.actorId;const action=document.getElementById('businessStepAction'),obj=document.getElementById('businessObjectSelect'),res=document.getElementById('businessResultSelect'),tim=document.getElementById('businessTimingSelect');if(action)action.value=s.action;if(obj)obj.value=s.object;if(res&&s.result)res.value=s.result;if(tim&&s.timing)tim.value=s.timing;syncBusiness()}
function deleteBusinessStep(index){businessSteps.splice(index,1);if(activeBusinessStepIndex===index)activeBusinessStepIndex=-1;normalizeBusinessSteps();syncBusiness()}
function syncBusinessProcess(){normalizeBusinessSteps();buildTechnicalChainFromBusiness()}
const BUSINESS_PRESETS={deferred_application:{case:'application_creation',technical:'async_worker',actors:['Клиент','Внутренняя система','Внешняя система'],steps:[['Клиент','Создаёт заявку / запрос','Заявка'],['Внутренняя система','Принимает заявку','Заявка'],['Внутренняя система','Проверяет данные','Заявка'],['Внешняя система','Обрабатывает запрос','Заявка'],['Внутренняя система','Обновляет статус','Статус']]},data_change_many_systems:{case:'data_change_distribution',technical:'event_kafka',actors:['Внутренняя система','Система','Несколько получателей','Получатели'],steps:[['Внутренняя система','Меняет данные','Клиентские данные'],['Система','Фиксирует изменение','Событие изменения'],['Несколько получателей','Получает изменение','Событие изменения'],['Получатели','Обновляет свои данные','Клиентские данные']]},enrichment_before_send:{case:'data_enrichment',technical:'enrichment_kafka',actors:['Внутренняя система','Проверяющая система'],steps:[['Внутренняя система','Получает объект','Документ'],['Проверяющая система','Дополняет данные','Документ'],['Внутренняя система','Передаёт данные дальше','Документ']]},status_screen_collection:{case:'status_screen',technical:'status_aggregation',actors:['Пользователь','Внутренняя система','Несколько систем'],steps:[['Пользователь','Открывает экран','Статус'],['Внутренняя система','Собирает статусы','Статус'],['Несколько систем','Возвращает часть статуса','Статус'],['Пользователь','Видит итоговый статус','Статус']]},reporting:{case:'reporting',technical:'dwh',actors:['Внутренняя система','Отчётный контур'],steps:[['Внутренняя система','Меняет данные','Отчётные данные'],['Внутренняя система','Передаёт в отчётность','Отчётные данные'],['Отчётный контур','Проверяет полноту','Отчётные данные'],['Отчётный контур','Строится на проверенных данных','Отчётные данные']]},legacy_file:{case:'legacy_file',technical:'legacy_file',actors:['Старая система','Система','Оператор / сотрудник'],steps:[['Старая система','Формирует файл','Файл'],['Система','Принимает файл','Файл'],['Система','Проверяет файл','Файл'],['Оператор / сотрудник','Отправляет на ручной разбор','Файл'],['Система','Загружает валидные данные','Файл']]}};
function applyBusinessPreset(kind){const p=BUSINESS_PRESETS[kind];if(!p)return;businessCase=p.case;current=p.technical;activeBusinessStepIndex=-1;businessActors=p.actors.map((name,i)=>({id:'BA_PRESET_'+kind+'_'+i,role:name,name}));businessSteps=p.steps.map((row,i)=>{const actor=businessActors.find(a=>a.name===row[0])||businessActors[0];return {id:'BS_PRESET_'+kind+'_'+i,order:i+1,actorId:actor.id,actorLabel:actor.name,actor:actor.name,action:row[1],object:row[2],result:selected('businessResultSelect'),timing:selected('businessTimingSelect'),errorBehavior:(document.getElementById('simpleQErrorHidden')||{}).value||''}});document.querySelectorAll('[data-case]').forEach(x=>x.classList.toggle('is-active',(x.dataset.businessCase||'')===businessCase));setHidden('businessCaseHidden',businessCase);syncBusiness()}
function syncBusiness(){normalizeBusinessSteps();syncBusinessActorSelect();setText('businessActorCounter',businessActors.length+' участников');setText('businessStepCounter',businessSteps.length+' шагов');const addBtn=document.getElementById('addBusinessStepBtn'),hint=document.getElementById('businessStepEditHint');if(addBtn)addBtn.textContent=activeBusinessStepIndex>=0?'Сохранить шаг':'+ Добавить шаг процесса';if(hint)hint.textContent=activeBusinessStepIndex>=0?'Редактируется шаг '+(activeBusinessStepIndex+1):'';setHtml('businessActorList',businessActors.length?businessActors.map((a,i)=>'<div class="participant-card"><b>'+esc(a.name)+'</b><span>'+esc(a.role)+'</span><button type="button" class="mini-action" data-del-ba="'+i+'">Удалить</button></div>').join(''):'<div class="participant-card"><b>Пока участников нет</b><span>Нажмите “+ Добавить участника”.</span></div>');setHtml('businessStepList',businessSteps.length?businessSteps.map((s,i)=>'<div class="business-step-card '+(i===activeBusinessStepIndex?'is-editing':'')+'"><div class="step-number">Шаг '+(i+1)+'</div><div class="step-main"><b>'+esc(s.actorLabel||s.actor||'Система')+'</b><span>'+esc((s.action||'')+' · объект: '+(s.object||''))+'</span></div><div class="step-actions"><button type="button" class="mini-action" data-step-up="'+i+'" '+(i===0?'disabled':'')+'>↑</button><button type="button" class="mini-action" data-step-down="'+i+'" '+(i===businessSteps.length-1?'disabled':'')+'>↓</button><button type="button" class="mini-action" data-step-edit="'+i+'">Изменить</button><button type="button" class="mini-action" data-step-delete="'+i+'">Удалить</button></div></div>').join(''):'<div class="connection-card"><b>Пока шагов нет</b><span>Нажмите “+ Добавить шаг процесса”.</span></div>');document.querySelectorAll('[data-del-ba]').forEach(b=>b.onclick=()=>{businessActors.splice(Number(b.dataset.delBa),1);normalizeBusinessSteps();syncBusiness()});document.querySelectorAll('[data-step-delete]').forEach(b=>b.onclick=()=>deleteBusinessStep(Number(b.dataset.stepDelete)));document.querySelectorAll('[data-step-up]').forEach(b=>b.onclick=()=>moveBusinessStep(Number(b.dataset.stepUp),-1));document.querySelectorAll('[data-step-down]').forEach(b=>b.onclick=()=>moveBusinessStep(Number(b.dataset.stepDown),1));document.querySelectorAll('[data-step-edit]').forEach(b=>b.onclick=()=>editBusinessStep(Number(b.dataset.stepEdit)));renderBusinessProcess();renderBusinessPreview();renderAll()}
function renderCaseQuestions(){const box=document.getElementById('caseSpecificQuestions');if(!box)return;const rows={async_worker:[['Нужно вернуть ID для отслеживания?',['Да','Нет','Не знаю']],['Нужны статусы?',['Да','Нет','Не знаю']]],event_kafka:[['Получателей несколько?',['Да','Нет','Не знаю']],['Нужен replay?',['Да','Нет','Не знаю']]],callback:[['Ответ может прийти повторно?',['Да','Нет','Не знаю']],['Что если ответ не пришёл?',['Проверять статус самому','Ручной разбор','Не знаю']]],enrichment_kafka:[['Где лучше дополнять данные?',['В источнике','В отдельном обработчике','У получателя','Не знаю']]],dwh:[['Нужна повторная загрузка?',['Да','Нет','Не знаю']]],legacy_file:[['Что делать с ошибочными строками?',['Карантин','Отклонить файл','Ручной разбор']]],status_aggregation:[['Можно показать частичный статус?',['Да','Нет','Не знаю']]],audit:[['Что беспокоит?',['Дубли','Потери','Таймауты','Непонятно где ошибка']]]}[current]||[];box.innerHTML=rows.map((r,i)=>'<label class="field"><span>'+esc(r[0])+'</span><select data-case-question="'+i+'">'+r[1].map(v=>'<option>'+esc(v)+'</option>').join('')+'</select></label>').join('')||'<p class="small">Дополнительных вопросов нет.</p>'}
const ROLE_CATALOG=[['initiator','Инициатор процесса','Service'],['receiver','Принимающий сервис','Service'],['worker','Обработчик / Worker','Worker'],['db','База данных','DB'],['external','Внешняя система','External System'],['broker','Брокер / очередь','Event Stream'],['event_consumer','Получатель события','Consumer'],['dwh','DWH / отчётность','DWH'],['legacy','Legacy-система','Legacy'],['file_gateway','Файловый шлюз','File Gateway'],['ui','UI / экран','UI'],['bff','BFF / агрегатор','Status Aggregation'],['cache','Cache / Read Model','Cache']];const CONN_TYPES=['Запрос и быстрый ответ','Принять сейчас, обработать позже','Передать событие','Получить дополнительные данные','Получить ответ позже','Передать файл','Передать данные в отчётность','Собрать статус','Проверить текущее решение'];const ERROR_TYPES=['Повторить позже','Показать ошибку','Отправить в ручной разбор','Сохранить и обработать потом','Остановить процесс','Не знаю'];function roleMeta(role){return ROLE_CATALOG.find(r=>r[0]===role)||ROLE_CATALOG[0]}function nextName(role){const base=roleMeta(role)[2];const count=customParticipants.filter(p=>p.base===base).length+1;return base+(count>1?' '+count:'')}function addParticipant(role){const m=roleMeta(role);customParticipants.push({id:'P'+Date.now()+Math.random(),role:m[1],base:m[2],name:nextName(role)});syncCustomChain()}function removeParticipant(id){customParticipants=customParticipants.filter(p=>p.id!==id);customConnections=customConnections.filter(e=>e.from!==id&&e.to!==id);syncCustomChain()}function customName(id){return (customParticipants.find(p=>p.id===id)||{}).name||id}function hasConnection(f,t,ty){return customConnections.some(e=>e.from===f&&e.to===t&&e.type===ty)}function addConnection(){if(customParticipants.length<2)return;const fromEl=document.getElementById('connFrom'),toEl=document.getElementById('connTo'),msg=document.getElementById('builderMessage');const f=(fromEl&&fromEl.value)||customParticipants[0].id;let t=(toEl&&toEl.value)||customParticipants[1].id;const ty=selected('connType')||CONN_TYPES[0],er=selected('connError')||ERROR_TYPES[0];if(f===t)t=(customParticipants.find(p=>p.id!==f)||customParticipants[1]).id;if(hasConnection(f,t,ty)){if(msg){msg.style.display='block';msg.textContent='Такая связь уже есть'}syncCustomChain();return}if(msg){msg.style.display='none';msg.textContent=''}customConnections.push({from:f,to:t,type:ty,error:er});syncCustomChain()}function removeConnection(i){customConnections.splice(i,1);syncCustomChain()}function resetCustomChain(){customParticipants=[];customConnections=[];syncCustomChain()}function customSchema(){if(!customParticipants.length)return '';if(!customConnections.length)return customParticipants.map(p=>p.name).join(' → ');let ids=[];customConnections.forEach(e=>{if(!ids.includes(e.from))ids.push(e.from);if(!ids.includes(e.to))ids.push(e.to)});customParticipants.forEach(p=>{if(!ids.includes(p.id))ids.push(p.id)});return ids.map(customName).join(' → ')}function buildCustomPreset(kind){customParticipants=[];customConnections=[];function p(name,role){const m=roleMeta(role);const o={id:'P'+Math.random(),role:m[1],base:m[2],name};customParticipants.push(o);return o}function e(a,b,type){customConnections.push({from:a.id,to:b.id,type,error:'Повторить позже'})}if(kind==='async'){let a=p('Client/UI','ui'),b=p('Service API','receiver'),c=p('integration_task DB','db'),d=p('Worker','worker'),e1=p('Target Service','receiver');e(a,b,'Запрос и быстрый ответ');e(b,c,'Принять сейчас, обработать позже');e(c,d,'Принять сейчас, обработать позже');e(d,e1,'Запрос и быстрый ответ');current='async_worker'}if(kind==='kafka'){let a=p('Source Service','receiver'),b=p('Outbox','db'),c=p('Event Stream','broker'),d=p('Consumer','event_consumer'),e1=p('Inbox','db');e(a,b,'Передать событие');e(b,c,'Передать событие');e(c,d,'Передать событие');e(d,e1,'Передать событие');current='event_kafka'}if(kind==='status'){let a=p('Client/UI','ui'),b=p('Status Aggregation','bff'),c=p('Service A','receiver'),d=p('Service B','receiver'),e1=p('Cache / Read Model','cache');e(a,b,'Собрать статус');e(b,c,'Собрать статус');e(b,d,'Собрать статус');e(b,e1,'Собрать статус');current='status_aggregation'}if(kind==='legacy'){let a=p('Legacy System','legacy'),b=p('File Export','file_gateway'),c=p('Validation/Checksum','receiver'),d=p('Quarantine','receiver');e(a,b,'Передать файл');e(b,c,'Передать файл');e(c,d,'Передать файл');current='legacy_file'}syncCustomChain();renderAll()}
function renderRolePalette(){const box=document.getElementById('rolePalette');if(!box)return;box.innerHTML=ROLE_CATALOG.map(r=>'<button type="button" data-add-role="'+r[0]+'"><b>'+esc(r[1])+'</b><span>'+esc(r[2])+'</span></button>').join('');box.querySelectorAll('[data-add-role]').forEach(b=>b.onclick=()=>addParticipant(b.dataset.addRole))}function syncCustomChain(){const pl=document.getElementById('participantList'),cl=document.getElementById('connectionList'),cf=document.getElementById('connFrom'),ct=document.getElementById('connTo'),md=document.getElementById('manualDiagram');if(!pl||!cl||!cf||!ct||!md)return;setText('participantCounter',customParticipants.length+' участников');setText('connectionCounter',customConnections.length+' связей');pl.innerHTML=customParticipants.length?customParticipants.map(p=>'<div class="participant-card"><b>'+esc(p.name)+'</b><span>'+esc(p.role)+'</span><button type="button" class="mini-action" data-del-part="'+p.id+'">Удалить</button></div>').join(''):'<div class="participant-card"><b>Пока участников нет</b><span>Откройте роль выше.</span></div>';const opts=customParticipants.map(p=>'<option value="'+p.id+'">'+esc(p.name)+'</option>').join('');cf.innerHTML=opts;ct.innerHTML=opts;cl.innerHTML=customConnections.length?customConnections.map((e,i)=>'<div class="connection-card"><b>'+esc(customName(e.from)+' → '+customName(e.to))+'</b><span>'+esc(e.type+' · ошибка: '+e.error)+'</span><button type="button" class="mini-action" data-del-conn="'+i+'">Удалить связь</button></div>').join(''):'<div class="connection-card"><b>Связей пока нет</b><span>Добавьте минимум двух участников и связь.</span></div>';pl.querySelectorAll('[data-del-part]').forEach(b=>b.onclick=()=>removeParticipant(b.dataset.delPart));cl.querySelectorAll('[data-del-conn]').forEach(b=>b.onclick=()=>removeConnection(Number(b.dataset.delConn)));const schema=customSchema();md.innerHTML=schema?'<h4>Техническая схема, поправленная пользователем</h4>'+diagramHtml(schema):'<p class="small">Техническая схема появится после добавления участников.</p>';setHidden('customChainJson',JSON.stringify({participants:customParticipants,connections:customConnections,schema}));if(schema){setHidden('processGraphJson',JSON.stringify({case_type:current,schema,nodes:customParticipants,edges:customConnections}));setHidden('systemsMatrixHidden',matrixSystems(schema));setHidden('processStepsHidden',matrixSteps(schema));setHidden('targetIntegrationHidden',matrixTarget(schema));setHidden('businessGoalHidden',businessGoalText()+'. Пользователь поправил техническую схему: '+schema)}renderAll()}
function renderAll(){const built=buildTechnicalChainFromBusiness();const d=CASES[current]||CASES.async_worker;const schema=customSchema()||built.schema||d.schema;const extras=constraintExtras();const orderWhy=businessSteps.length?'Так как шаги идут в порядке: '+businessSchema()+', система подбирает техническую цепочку под текущую последовательность.':'бизнесовый ввод преобразован в техническую цепочку';const warnings=built.warnings||[];const why=[orderWhy,'требования и ограничения учтены в must-have','технический конструктор можно открыть и поправить'].concat(warnings.map(w=>'Обратите внимание: '+w));setHtml('autoSchemeReview','<h3>Бизнес-процесс</h3>'+businessFlowHtml()+'<h3>Техническая схема</h3>'+diagramHtml(schema)+'<h3>Почему такая схема</h3><ul class="todo-list">'+bullets(why)+'</ul>'+warningHtml(warnings));setHtml('understandingPreview','<h3>Бизнес-процесс</h3>'+businessOrderedListHtml()+'<h3>Построенная техническая схема</h3>'+diagramHtml(schema)+'<h3>Главные риски</h3><ul class="todo-list">'+bullets(d.risks.concat(extras.slice(0,4)).concat(warnings))+'</ul>');setHtml('resultBusinessProcess','<h3>1. Бизнес-процесс</h3>'+businessOrderedListHtml());setHtml('resultWhy','<h3>3. Почему выбрана такая техническая схема</h3><ul class="todo-list">'+bullets([d.summary].concat(why))+'</ul>');setHtml('resultSchema',diagramHtml(schema));setHtml('resultMust',bullets(d.must.concat(extras)));setHtml('resultRisks',bullets(d.risks.concat(extras).concat(warnings)));setHtml('resultHandoff',bullets(d.handoff.concat(customParticipants.length?['поправленная техническая цепочка участников и связей']:[])))}
function moveTechnicalConstructorTo(hostId){const d=document.getElementById('technicalConstructorDetails'),host=document.getElementById(hostId);if(d&&host&&!host.contains(d))host.appendChild(d);return d}function openTechnicalConstructorAt(hostId){const d=moveTechnicalConstructorTo(hostId);if(d){d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}}function go(n){step=Math.max(0,Math.min(5,n));document.querySelectorAll('.constructor-screen').forEach((e,i)=>e.classList.toggle('is-active',i===step));document.querySelectorAll('#constructorProgress span').forEach((e,i)=>{e.classList.toggle('active',i===step);e.classList.toggle('done',i<step)});if(app)app.classList.toggle('result-screen',step===5);const prev=document.getElementById('constructorPrev'),next=document.getElementById('constructorNext'),nav=document.getElementById('constructorNav');if(prev)prev.style.visibility=step===0?'hidden':'visible';if(next)next.textContent=step===4?'Всё верно':'Далее →';if(nav)nav.style.display=step===5?'none':'flex';if(step===1)moveTechnicalConstructorTo('businessTechnicalConstructorHost');renderAll()}
function on(id,event,handler){const el=document.getElementById(id);if(el)el.addEventListener(event,handler)}function showStart(){if(app)app.classList.add('is-hidden');if(start)start.classList.remove('is-hidden')}function startApp(targetStep=0){if(start)start.classList.add('is-hidden');if(app)app.classList.remove('is-hidden');go(targetStep)}
on('startNoTextBtn','click',()=>startApp(0));on('backToStart','click',showStart);document.querySelectorAll('[data-start-goal]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-start-goal]').forEach(x=>x.classList.remove('selected'));b.classList.add('selected');setHidden('simpleGoalHidden',b.dataset.startGoal);if(b.dataset.startGoal==='audit'){businessCase='audit';updateCase('audit')}startApp(0)});document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-case]').forEach(x=>x.classList.remove('is-active'));b.classList.add('is-active');businessCase=b.dataset.businessCase||'application_creation';setHidden('businessCaseHidden',businessCase);updateCase(BUSINESS_TO_CASE[businessCase]||b.dataset.case);syncBusiness()});on('addBusinessActorBtn','click',addBusinessActor);on('addBusinessStepBtn','click',addBusinessStep);on('resetBusinessBtn','click',resetBusiness);document.querySelectorAll('[data-business-preset]').forEach(b=>b.onclick=()=>applyBusinessPreset(b.dataset.businessPreset));['businessObjectSelect','businessTimingSelect','businessResultSelect','businessStepActorSelect','businessStepAction'].forEach(id=>on(id,'change',syncBusiness));document.querySelectorAll('[data-map-hidden]').forEach(s=>s.onchange=()=>{setHidden(s.dataset.mapHidden,s.value);syncBusiness()});document.querySelectorAll('input[name="constraint_flags"]').forEach(ch=>ch.onchange=syncBusiness);on('openTechnicalConstructor','click',()=>openTechnicalConstructorAt('autoTechnicalConstructorHost'));on('openTechnicalConstructorReview','click',()=>openTechnicalConstructorAt('reviewTechnicalConstructorHost'));on('approveAutoScheme','click',()=>go(4));on('editBusinessProcess','click',()=>go(1));on('addParticipantBtn','click',()=>addParticipant(customParticipants.length===0?'initiator':customParticipants.length===1?'receiver':'worker'));on('addConnectionBtn','click',addConnection);on('resetCustomChainBtn','click',resetCustomChain);document.querySelectorAll('[data-chain-preset]').forEach(b=>b.onclick=()=>buildCustomPreset(b.dataset.chainPreset));on('constructorPrev','click',()=>go(step-1));on('constructorNext','click',()=>go(step+1));on('prevBtn','click',()=>go(4));on('editAnswers','click',()=>go(2));on('confirmUnderstanding','click',()=>go(5));renderRolePalette();syncBusiness();renderCaseQuestions();go(0);
})();
</script>
"""
    content = content_template.replace('%%RECENT_HTML%%', recent_html).replace('%%SECTIONS%%', sections).replace('%%MATRIX_EXAMPLES%%', json.dumps(MATRIX_EXAMPLES, ensure_ascii=False))
    if "<script>" in content:
        before_script, after_script = content.split("<script>", 1)
        content = explain_english_terms_ru_html_fragment(before_script) + "<script>" + after_script
    else:
        content = explain_english_terms_ru_html_fragment(content)
    content = content.replace("<form method='POST' action='/generate' class='card' id='mainForm'>", "<form method='POST' action='/generate' class='card' id='mainForm'>" + terminology_glossary_html(), 1)
    return HTML.replace('{content}', content)


# ---------- progressive wizard mapping layer ----------
UNKNOWN_MARKERS = {'unknown', 'dont_know', 'auto', 'не знаю', 'не знаю / определить автоматически', ''}

CASE_DEFAULTS = {
    'rest_sync': {
        'channels': ['rest'],
        'defaults': ['timeout', 'retry with backoff', 'error mapping', 'circuit breaker', 'fallback', 'correlationId', 'rate limit', 'SLA dependency'],
        'situations': ['api_composition'],
    },
    'kafka_async': {
        'channels': ['kafka'],
        'defaults': ['eventId', 'correlationId', 'idempotency', 'inbox', 'outbox', 'retry', 'DLQ', 'schema compatibility', 'consumer lag monitoring', 'replay strategy', 'contract tests'],
        'situations': ['highload_write_stream', 'one_source_many_consumers'],
    },
    'rest_enrichment_kafka': {
        'channels': ['rest', 'kafka'],
        'defaults': ['outbox до публикации', 'enrichment worker/process manager', 'timeout на enrichment', 'retry/backoff', 'DLQ', 'status table', 'correlationId', 'идемпотентность публикации и обработки', 'стратегия при недоступности enrichment service'],
        'situations': ['data_enrichment', 'highload_write_stream', 'unstable_external_provider'],
    },
    'webhook': {
        'channels': ['webhook', 'rest'],
        'defaults': ['request validation', 'signature validation', 'idempotency', 'retry policy', 'callback status', 'DLQ/manual queue', 'audit log', 'replay/manual resend'],
        'situations': ['webhook_callback', 'external_api_dependency'],
    },
    'dwh': {
        'channels': ['etl', 'sftp'],
        'defaults': ['freshness SLA', 'batch window', 'lineage', 'reconciliation', 'data quality checks', 'duplicate detection', 'late arriving data handling', 'monitoring of load completeness'],
        'situations': ['dwh_reporting', 'batch_processing'],
    },
    'external': {
        'channels': ['rest'],
        'defaults': ['timeout', 'retry limit', 'circuit breaker', 'fallback/degraded mode', 'external SLA risk', 'error mapping', 'monitoring', 'manual recovery'],
        'situations': ['external_api_dependency', 'unstable_external_provider'],
    },
    'service2_async_worker': {
        'channels': ['rest', 'queue'],
        'defaults': ['acceptance response', 'operation/status table', 'DB task/outbox table', 'worker inside service 2', 'idempotencyKey', 'correlationId', 'retry with backoff', 'retry limit', 'manual recovery', 'DLQ/manual queue', 'status update', 'reconciliation', 'stuck task monitoring', 'contract tests'],
        'situations': ['multi_step_business_process', 'external_api_dependency', 'async_heavy_processing'],
    },
    'legacy_file': {
        'channels': ['sftp', 'etl'],
        'defaults': ['file validation', 'duplicate file handling', 'checksum/control totals', 'archive', 'retry/reprocess', 'manual correction', 'reconciliation'],
        'situations': ['legacy_integration', 'batch_processing'],
    },
}

PROCESS_TEMPLATES = {
    'rest': ['Source Service', 'REST', 'Target Service'],
    'kafka': ['Source Service', 'Outbox', 'Kafka', 'Target Consumer'],
    'rest_enrichment_kafka': ['Source Service', 'REST enrichment', 'Outbox', 'Kafka', 'Target Consumer'],
    'webhook': ['External system', 'callback/webhook', 'Our service', 'Inbox/status'],
    'api_composition': ['User', 'API', 'Several services', 'Final status'],
    'service2_async_worker': ['Сервис 1: отправить команду', 'Сервис 2 API: принять и сохранить статус', 'БД сервиса 2: хранить задачу/статус', 'Worker сервиса 2: прочитать нужные записи', 'Worker сервиса 2: асинхронно вызвать сервис 3', 'Сервис 3: принять запрос', 'Сервис 2: обновить статус/создать recovery'],
    'dwh': ['Source Service', 'DWH', 'Reporting'],
    'file': ['File/SFTP', 'Processing', 'Target system'],
    'cdc': ['DB polling/CDC', 'Consumer', 'Target system'],
    'auto': ['Source Service', 'Integration step', 'Target Service'],
}

RISK_MAPPING = {
    'duplicate_event': ['idempotency', 'inbox', 'eventId/idempotencyKey'],
    'lost_event': ['outbox', 'риск потери события', 'тест-кейс на атомарность'],
    'external_timeout': ['timeout', 'retry with backoff', 'circuit breaker', 'fallback/degraded mode', 'DLQ/manual recovery'],
    'partial_processing': ['status table', 'compensation', 'manual recovery'],
    'traceability': ['correlationId', 'traceId', 'structured logs', 'observability'],
    'reconciliation': ['reconciliation', 'data quality checks', 'report completeness checks'],
    'bad_messages': ['DLQ', 'retry limit', 'manual recovery', 'owner of failed messages'],
    'stale_data': ['freshness SLA', 'stale-data label', 'fallback policy'],
    'contract_change': ['contract versioning', 'schema compatibility', 'contract tests'],
    'replay_old_events': ['replay strategy', 'backfill window', 'idempotent replay'],
    'processing_status': ['business statuses', 'status history', 'stuck status monitoring'],
    'manual_errors': ['manual queue', 'runbook', 'error owner'],
}

PRODUCTION_BLOCKING_GAPS = [
    ('idempotency', 'нет idempotency', 'Дубли могут повторно выполнить опасное действие.', 'Риски → дубли или Эксперт → error_matrix/contract_matrix'),
    ('retry limit', 'нет retry limit', 'Бесконечные повторы перегрузят зависимости.', 'Продвинутый → Ошибки и retry'),
    ('DLQ', 'нет DLQ/manual recovery', 'Проблемные сообщения негде разбирать.', 'Продвинутый → Ошибки и retry'),
    ('correlationId', 'нет correlationId', 'Нельзя быстро найти всю цепочку.', 'Риски → трассировка или Контракты'),
    ('monitoring', 'нет мониторинга', 'Команда не увидит деградацию.', 'Продвинутый → Мониторинг'),
    ('contract tests', 'нет contract tests', 'Изменение контракта сломает потребителей.', 'Продвинутый → Контракты'),
    ('rollback', 'нет rollback', 'Нельзя безопасно откатиться.', 'Продвинутый → Rollout'),
    ('replay', 'нет replay', 'Нельзя восстановить пропущенный период.', 'Продвинутый → Rollout'),
    ('owner', 'нет владельца ошибок', 'Ошибки останутся без ответственного.', 'Продвинутый → Ошибки и retry'),
    ('invalid contract', 'нет обработки невалидного контракта', 'Плохие сообщения будут падать непредсказуемо.', 'Продвинутый → Контракты/Ошибки'),
    ('external unavailable', 'нет стратегии при недоступности внешнего сервиса', 'Внешняя зависимость остановит процесс.', 'Ограничения/Риски → внешний сервис'),
    ('reconciliation', 'нет сверки полноты данных для batch/DWH', 'Потери в выгрузке останутся незамеченными.', 'Продвинутый → Мониторинг/DWH'),
    ('duplicate', 'нет контроля дублей', 'Данные могут задвоиться.', 'Риски → событие может прийти дважды'),
]

def _raw_first(raw, name, default=''):
    val = raw.get(name, [default])
    return val[0] if isinstance(val, list) else val

def _raw_many(raw, name):
    val = raw.get(name, [])
    return val if isinstance(val, list) else [val]

def _is_unknown(value):
    return str(value or '').strip().lower() in UNKNOWN_MARKERS

def normalize_wizard_draft(raw):
    """Normalize quick/wizard/advanced card inputs without changing legacy field names."""
    mode = _raw_first(raw, 'ux_mode', 'wizard')
    text = _raw_first(raw, 'quick_description') or _raw_first(raw, 'review_description') or _raw_first(raw, 'business_goal')
    task_type = _raw_first(raw, 'wizard_task_type') or _raw_first(raw, 'quick_goal', 'design_new')
    # Browser submits hidden wizard fields from the same form. In quick/review mode these defaults
    # must not override the user's free-text description, otherwise Kafka cases can be misread as REST.
    template = 'auto' if mode in ['quick', 'review'] else _raw_first(raw, 'wizard_process_template', 'auto')
    source = _raw_first(raw, 'wizard_source_name', 'Source Service') or 'Source Service'
    target = _raw_first(raw, 'wizard_target_name', 'Target Service') or 'Target Service'
    extra = _raw_many(raw, 'wizard_extra_systems') + _raw_many(raw, 'advanced_system_role')
    risk_answers = {k.replace('risk_', ''): _raw_first(raw, k) for k in raw if k.startswith('risk_')}
    constraints = {k.replace('constraint_', ''): _raw_first(raw, k) for k in raw if k.startswith('constraint_')}
    unknowns = []
    for name in ['quick_goal', 'quick_speed', 'quick_broker', 'quick_external', 'quick_load', 'wizard_process_template']:
        if _is_unknown(_raw_first(raw, name)): unknowns.append(name)
    unknowns += [f'risk_{k}' for k, v in risk_answers.items() if _is_unknown(v)]
    unknowns += [f'constraint_{k}' for k, v in constraints.items() if _is_unknown(v)]
    if template == 'auto':
        lower = text.lower()
        broker = _raw_first(raw, 'quick_broker', 'unknown')
        speed = _raw_first(raw, 'quick_speed', 'unknown')
        external = _raw_first(raw, 'quick_external', 'unknown')
        has_kafka = 'kafka' in lower or 'кафк' in lower or broker == 'yes'
        has_rest_enrichment = 'rest' in lower and ('обогат' in lower or 'обогащ' in lower or 'enrich' in lower or 'перед этим' in lower or 'before' in lower)
        if has_kafka and has_rest_enrichment: template = 'rest_enrichment_kafka'
        elif has_kafka: template = 'kafka'
        elif ('сервис 1' in lower and 'сервис 2' in lower and 'сервис 3' in lower and ('микросервис' in lower or 'worker' in lower or 'воркер' in lower or 'бд' in lower or 'db' in lower)): template = 'service2_async_worker'
        elif 'webhook' in lower or 'callback' in lower or 'коллбек' in lower: template = 'webhook'
        elif 'dwh' in lower or 'витрин' in lower or 'раз в день' in lower or speed == 'daily': template = 'dwh'
        elif 'sftp' in lower or 'file' in lower or 'файл' in lower: template = 'file'
        elif external == 'yes': template = 'rest'
        else: template = 'rest'
    return {
        'mode': mode,
        'text': text,
        'task_type': task_type,
        'template': template,
        'source': source,
        'target': target,
        'source_data': _raw_first(raw, 'wizard_source_data', 'данные сущности'),
        'target_data': _raw_first(raw, 'wizard_target_data', 'результат/статус'),
        'target_speed': _raw_first(raw, 'wizard_target_speed', _raw_first(raw, 'quick_speed', 'unknown')),
        'extra_systems': [x for x in extra if x],
        'risk_answers': risk_answers,
        'constraints': constraints,
        'unknowns': sorted(set(unknowns)),
    }

def draft_case_key(draft):
    t = draft.get('template', 'auto')
    if t in ['kafka']: return 'kafka_async'
    if t == 'rest_enrichment_kafka': return 'rest_enrichment_kafka'
    if t == 'service2_async_worker': return 'service2_async_worker'
    if t == 'webhook': return 'webhook'
    if t == 'dwh': return 'dwh'
    if t == 'file': return 'legacy_file'
    if draft.get('task_type') in ['external', 'external_partner']: return 'external'
    return 'rest_sync'

def map_draft_to_internal_fields(draft, base=None):
    """Map progressive UI draft to the existing internal matrices used by Engine.generate."""
    f = dict(base or {})
    key = draft_case_key(draft)
    defaults_for_case = CASE_DEFAULTS.get(key, CASE_DEFAULTS['rest_sync'])
    safe_defaults = list(defaults_for_case['defaults'])
    risk_controls = []
    for risk, answer in draft.get('risk_answers', {}).items():
        if str(answer).lower() in ['yes', 'maybe', 'unknown', 'dont_know', 'auto', 'да', 'возможно', 'не знаю']:
            risk_controls.extend(RISK_MAPPING.get(risk, []))
    all_controls = []
    for item in safe_defaults + risk_controls:
        if item not in all_controls: all_controls.append(item)
    source = draft.get('source') or 'Source Service'
    target = draft.get('target') or 'Target Service'
    chain = PROCESS_TEMPLATES.get(draft.get('template'), PROCESS_TEMPLATES['auto'])
    channel = 'Kafka' if key in ['kafka_async', 'rest_enrichment_kafka'] else ('Webhook' if key == 'webhook' else ('SFTP/ETL' if key in ['dwh', 'legacy_file'] else 'REST'))
    mode = 'async' if key in ['kafka_async', 'rest_enrichment_kafka', 'service2_async_worker', 'webhook', 'dwh', 'legacy_file'] else 'sync'
    f['business_goal'] = draft.get('text') or f.get('business_goal') or f'{source} должен передать {draft.get("source_data", "данные")} в {target}.'
    f['task_type'] = 'audit_existing_solution' if draft.get('mode') == 'review' or draft.get('task_type') in ['check_existing', 'audit_existing_solution'] else f.get('task_type', 'new_from_scratch')
    situations = list(dict.fromkeys((f.get('business_situations') or []) + defaults_for_case.get('situations', [])))
    f['business_situations'] = situations
    f['allowed_channels'] = list(dict.fromkeys(defaults_for_case.get('channels', ['rest'])))
    f['systems_matrix'] = '\n'.join([
        f'{source} | источник данных | TBD | critical | {channel} | {"non_blocking" if mode == "async" else "blocking"} | {draft.get("target_speed", "уточнить")}',
        f'{target} | получатель данных | TBD | important | {channel} | {"non_blocking" if mode == "async" else "blocking"} | {draft.get("target_speed", "уточнить")}',
    ] + [f'{x} | дополнительная система | TBD | important | unknown | non_blocking | уточнить' for x in draft.get('extra_systems', [])])
    f['target_integration_matrix'] = f'{source} | {target} | {channel} | {mode} | business change | {draft.get("target_data", "payload")} | Contract.v1 | {"30s" if mode == "async" else "3s"} | yes/backoff | 3 | {"yes" if mode == "async" else "no"} | eventId+correlationId | service auth | уточнить | TBD'
    f['process_steps'] = '\n'.join([f'{i} | {i+1} | {"root" if i == 0 else i} | {step} | {source if i == 0 else target if i == len(chain)-1 else step} | {channel if step in ["REST", "Kafka", "callback/webhook"] else "internal"} | input | output | {"30s" if mode == "async" else "3s"} | yes | DLQ/manual | {"non_blocking" if mode == "async" else "blocking"} | TBD' for i, step in enumerate(chain)])
    f['contract_matrix'] = f'{"EVENT" if mode == "async" else "API"} | Contract.v1 | {source} | {target} | {"topic.contract.v1" if mode == "async" else "/integration/v1"} | {"entityId as key" if mode == "async" else "POST"} | entityId,eventId,correlationId,idempotencyKey | metadata | validation_error,duplicate,timeout | v1 | backward'
    f['error_matrix'] = '\n'.join([
        'timeout | external/target dependency | blocking | yes | retry with backoff + circuit breaker | TBD',
        'duplicate | consumer/API | non_blocking | no | ignore by idempotencyKey/eventId | TBD',
        'invalid_contract | contract boundary | blocking | no | reject/quarantine + alert owner | TBD',
        'retry_exhausted | integration worker | non_blocking | yes | DLQ/manual recovery | TBD',
    ])
    f['capacity_matrix'] = f'main_flow | уточнить | уточнить | 5 | 50 | уточнить | 100% | 3 | 2 | уточнить | {draft.get("target_speed", "уточнить")} | 24h | 24h | уточнить'
    f['observability_matrix'] = '\n'.join([
        'success_total | integration flow | drop to zero | yes | TBD | Integration dashboard',
        'error_total | integration flow | > 0 for 15m | yes | TBD | Failure dashboard',
        'consumer_lag | Kafka consumer | > 10000 events | yes | Platform | Kafka dashboard' if 'Kafka' in channel else 'external_timeout_rate | REST dependency | > 5% for 15m | yes | TBD | Dependency dashboard',
        'dlq_size | DLQ/manual queue | > 0 for 15m | yes | Operations | Failure dashboard',
    ])
    f['rollout_migration_matrix'] = 'P1 | pilot | feature toggle/canary | rollback toggle | no | compare status/counts | no critical gaps | TBD\nP2 | full rollout | phased rollout | rollback + replay failed period | 24h | compare business metrics | duplicates/losses = 0 | TBD'
    f['process_flow_matrix'] = 'S1 | root | request accepted | принять и провалидировать | API | S2 | E_VALIDATION | E_TIMEOUT | none | no\nS2 | S1 | data ready | передать downstream | Integration | S3 | E_DELIVERY | E_RETRY | retry/DLQ | yes'
    f['business_rules_matrix'] = 'BR1 | пришёл дубль | не выполнять действие повторно | S2 | TBD | DUPLICATE_IGNORED\nBR2 | retry исчерпан | создать manual task/DLQ | S2 | TBD | DELIVERY_FAILED'
    if key == 'service2_async_worker':
        f['task_type'] = 'e2e_chain'
        f['customer_visible'] = 'no'
        f['result_model'] = 'async'
        f['orchestration'] = 'orchestrator'
        f['chain_depth'] = 'multi_level'
        f['source_system'] = 'Сервис 2'
        f['main_entity'] = 'IntegrationRequest'
        f['systems_matrix'] = '\n'.join([
            'Сервис 1 | инициатор запроса | TBD | important | REST | blocking | 3s',
            'Сервис 2 API | принимает команду и хранит статус | TBD | critical | REST/internal | blocking | 3s',
            'БД сервиса 2 | source of truth для задач и статусов | TBD | critical | DB | non_blocking | n/a',
            'Worker сервиса 2 | читает БД и отправляет запрос в сервис 3 | TBD | critical | internal/REST | non_blocking | 30s',
            'Сервис 3 | downstream-получатель запроса | TBD | important | REST/API | non_blocking | 30s',
        ])
        f['target_integration_matrix'] = 'Сервис 1 | Сервис 2 API | REST | sync_acceptance | command | request payload | CreateIntegrationRequest.v1 | 3s | no | 0 | no | idempotencyKey+correlationId | service auth | уточнить | TBD\nWorker сервиса 2 | Сервис 3 | REST/API | async | background task | selected DB records | SendToService3.v1 | 30s | yes/backoff | 3 | yes/manual queue | taskId+correlationId | service auth | уточнить | TBD'
        f['process_steps'] = '\n'.join([
            '0 | 1 | root | Сервис 1 отправляет команду | Сервис 1 | REST | command | accepted/processing | 3s | no | validation error | blocking | TBD',
            '1 | 2 | 1 | Сервис 2 принимает запрос, валидирует и сохраняет задачу/статус | Сервис 2 API | DB transaction | command | TASK_CREATED | 3s | no | error response | blocking | TBD',
            '1 | 3 | 2 | Worker сервиса 2 выбирает из БД задачи и нужные записи | Worker сервиса 2 | DB read | pending task | selected payload | 30s | yes | retry/manual | non_blocking | TBD',
            '1 | 4 | 3 | Worker асинхронно отправляет запрос в сервис 3 | Worker сервиса 2 | REST/API | selected payload | sent/accepted | 30s | yes | retry/DLQ/manual | non_blocking | TBD',
            '1 | 5 | 4 | Сервис 2 обновляет статус отправки и хранит результат попытки | Сервис 2 API/Worker | DB update | attempt result | SENT/FAILED/WAITING_RETRY | 3s | yes | manual recovery | non_blocking | TBD',
        ])
        f['process_flow_matrix'] = '\n'.join([
            'S1 | root | command received | принять запрос от сервиса 1 | Сервис 2 API | S2 | E_VALIDATION | E_TIMEOUT | вернуть понятную ошибку | no',
            'S2 | S1 | command valid | сохранить задачу и статус в БД сервиса 2 | Сервис 2 API | S3 | E_DB | E_TIMEOUT | rollback transaction | no',
            'S3 | S2 | task pending | worker читает нужные записи из БД | Worker сервиса 2 | S4 | E_NO_DATA | E_DB_TIMEOUT | retry/manual review | yes',
            'S4 | S3 | payload ready | асинхронно вызвать сервис 3 | Worker сервиса 2 | S5 | E_CONTRACT | E_TIMEOUT | retry with backoff + manual queue | yes',
            'S5 | S4 | call finished | обновить статус задачи и attempts | Worker сервиса 2 | END | E_STATUS_UPDATE | E_TIMEOUT | reconciliation/manual recovery | yes',
        ])
        f['business_rules_matrix'] = '\n'.join([
            'BR1 | повторный запрос от сервиса 1 с тем же idempotencyKey | не создавать вторую задачу, вернуть текущий статус | S1/S2 | TBD | DUPLICATE_IGNORED',
            'BR2 | worker не нашёл нужные записи в БД | поставить статус DATA_NOT_FOUND и создать manual task | S3 | TBD | DATA_NOT_FOUND',
            'BR3 | сервис 3 недоступен после retry | поставить WAITING_RETRY/FAILED и отправить в manual/DLQ queue | S4 | TBD | DOWNSTREAM_UNAVAILABLE',
        ])
        f['process_graph_json'] = json.dumps({
            'nodes': [
                {'id':'S1','title':'Сервис 1 отправляет запрос','type':'api_request','system_id':'Сервис 1','target_system_id':'Сервис 2 API','channel':'REST','user_waits':True,'status_after_success':'REQUEST_ACCEPTED','status_after_error':'VALIDATION_ERROR','idempotency_required':True,'owner':'TBD'},
                {'id':'S2','title':'Сервис 2 принимает и сохраняет задачу','type':'persist_operation','system_id':'Сервис 2 API','target_system_id':'БД сервиса 2','channel':'DB transaction','user_waits':True,'status_after_success':'TASK_CREATED','status_after_error':'SAVE_ERROR','idempotency_required':True,'audit_required':True,'owner':'TBD'},
                {'id':'S3','title':'Вернуть сервису 1 trackingId/status','type':'api_request','system_id':'Сервис 2 API','target_system_id':'Сервис 1','channel':'REST response','user_waits':True,'status_after_success':'PROCESSING','owner':'TBD'},
                {'id':'S4','title':'Worker сервиса 2 читает нужные записи из БД','type':'queue_task','system_id':'Worker сервиса 2','target_system_id':'БД сервиса 2','channel':'DB read','user_waits':False,'retry_policy':'limited retry','status_after_success':'DATA_SELECTED','status_after_error':'DATA_NOT_FOUND','owner':'TBD'},
                {'id':'S5','title':'Worker асинхронно отправляет запрос в сервис 3','type':'rest_call','system_id':'Worker сервиса 2','target_system_id':'Сервис 3','channel':'REST/API async background','user_waits':False,'retry_policy':'3 attempts + backoff','status_after_success':'SENT_TO_SERVICE_3','status_after_error':'WAITING_RETRY_OR_MANUAL','idempotency_required':True,'owner':'TBD'},
                {'id':'S6','title':'Retry loop при timeout/5xx сервиса 3','type':'retry_loop','system_id':'Worker сервиса 2','target_system_id':'Сервис 3','channel':'timer/retry','user_waits':False,'retry_policy':'max 3 attempts + jitter','status_after_error':'MANUAL_REVIEW_REQUIRED','owner':'TBD'},
                {'id':'S7','title':'Обновить статус и attempts в БД сервиса 2','type':'persist_operation','system_id':'Worker сервиса 2','target_system_id':'БД сервиса 2','channel':'DB update','user_waits':False,'status_after_success':'COMPLETED_OR_WAITING_RETRY','status_after_error':'STATUS_UPDATE_ERROR','audit_required':True,'owner':'TBD'},
                {'id':'S8','title':'Ручное восстановление / reprocess','type':'manual_task','system_id':'Оператор/поддержка','target_system_id':'Worker сервиса 2','channel':'manual','user_waits':False,'status_after_success':'REPROCESSED','owner':'TBD'},
            ],
            'edges': [
                {'from_node_id':'S1','to_node_id':'S2','transition_type':'success','condition':'запрос валиден','is_blocking':True},
                {'from_node_id':'S2','to_node_id':'S3','transition_type':'success','condition':'задача сохранена','is_blocking':True},
                {'from_node_id':'S2','to_node_id':'S4','transition_type':'async_start','condition':'фоновая обработка','is_blocking':False},
                {'from_node_id':'S4','to_node_id':'S5','transition_type':'success','condition':'данные найдены','is_blocking':False},
                {'from_node_id':'S5','to_node_id':'S7','transition_type':'success','condition':'сервис 3 принял запрос','is_blocking':False},
                {'from_node_id':'S5','to_node_id':'S6','transition_type':'timeout/retry','condition':'timeout/5xx','is_blocking':False},
                {'from_node_id':'S6','to_node_id':'S5','transition_type':'retry','condition':'attempts left','is_blocking':False},
                {'from_node_id':'S6','to_node_id':'S8','transition_type':'manual_recovery','condition':'attempts exhausted','is_blocking':False},
                {'from_node_id':'S8','to_node_id':'S4','transition_type':'reprocess','condition':'оператор разрешил повтор','is_blocking':False},
            ],
            'meta': {'template':'service2_async_worker','explanation':'Сервис 2 быстро принимает запрос от сервиса 1, сохраняет задачу и дальше через внутренний worker асинхронно отправляет данные в сервис 3.'}
        }, ensure_ascii=False)
    f['fields'] = 'entityId:uuid|required|unique|indexed, idempotencyKey:string|unique, correlationId:string|indexed, status:string|required|indexed, updatedAt:datetime|required'
    f['statuses'] = 'ACCEPTED,PROCESSING,DONE,FAILED,MANUAL_REVIEW'
    f['final_statuses'] = 'DONE,FAILED'
    constraints = draft.get('constraints', {})
    if constraints.get('orchestration') in ['orchestrator','choreography','hybrid','bpm']:
        f['orchestration'] = constraints.get('orchestration')
    if constraints.get('chain_depth') in ['simple','multi_level','fanout_fanin','cycle']:
        f['chain_depth'] = 'fanout_fanin' if constraints.get('chain_depth') == 'fanout_fanin' else ('multi_level' if constraints.get('chain_depth') in ['multi_level','cycle'] else 'simple')
    if constraints.get('source_change') == 'no':
        f['source_change_policy'] = 'forbidden'
    elif constraints.get('source_change') == 'read_only':
        f['source_change_policy'] = 'read_only'
    elif constraints.get('source_change') == 'partial':
        f['source_change_policy'] = 'minimal_table_only'
    if constraints.get('new_infra') == 'no':
        f['new_infra_policy'] = 'forbidden'
    elif constraints.get('new_infra') == 'existing_only':
        f['new_infra_policy'] = 'existing_only'
    if key in ['kafka_async', 'rest_enrichment_kafka', 'service2_async_worker']:
        f['delivery'] = 'at_least_once'; f['replay'] = 'yes'; f['existing_capabilities'] = ['outbox', 'inbox', 'dlq', 'monitoring']
    if key == 'dwh':
        f['dwh'] = 'batch'; f['freshness_requirement'] = 'minutes_hours'; f['data_quality_lineage_matrix'] = f'{draft.get("target_data", "Entity")} | {source} | DWH | count/checksum/schema validation | daily | reconciliation report | Data owner'
    if key == 'webhook':
        f['webhook_signature_required'] = 'unknown'; f['webhook_raw_body_preserved'] = 'unknown'; f['manual_recovery'] = 'yes'
    f['compromise_comment'] = 'Progressive wizard defaults: ' + ', '.join(all_controls) + ('. Нужно уточнить: ' + ', '.join(draft.get('unknowns', [])) if draft.get('unknowns') else '')
    f['wizard_missing_information'] = ', '.join(draft.get('unknowns', []))
    f['wizard_defaults_applied'] = ', '.join(all_controls)
    f['wizard_decision_summary'] = f'{source} → ' + ' → '.join(chain[1:-1]) + f' → {target}; режим {mode}, канал {channel}.'
    f['wizard_production_gate'] = compute_production_gate_from_controls(all_controls, key)
    return f

def compute_production_gate_from_controls(controls, case_key='rest_sync'):
    text = ' '.join(controls).lower()
    gaps = []
    for needle, title, risk, where in PRODUCTION_BLOCKING_GAPS:
        if needle.lower() not in text:
            if needle == 'reconciliation' and case_key not in ['dwh', 'legacy_file']:
                continue
            if needle == 'external unavailable' and case_key not in ['external', 'rest_enrichment_kafka', 'webhook', 'rest_sync']:
                continue
            gaps.append({'title': title, 'risk': risk, 'fix': 'Добавить контроль: '+needle, 'where': where})
    if any(g['title'] in ['нет idempotency', 'нет DLQ/manual recovery', 'нет мониторинга'] for g in gaps):
        verdict = 'RED'; text_label = 'Нельзя в production без исправлений'
    elif gaps:
        verdict = 'YELLOW'; text_label = 'Можно только с ограничениями / feature toggle'
    else:
        verdict = 'GREEN'; text_label = 'Можно пилотировать'
    return {'verdict': verdict, 'text': text_label, 'gaps': gaps}

def apply_progressive_ui_mapping(raw, form):
    # Programmatic expert compatibility: raw matrices are preserved if ux_mode=expert.
    # The visible deep user mode uses ux_mode=advanced and stays choice-based.
    if _raw_first(raw, 'ux_mode') == 'expert':
        return form
    if not any(k.startswith(('quick_', 'wizard_', 'risk_', 'constraint_', 'advanced_')) or k == 'ux_mode' for k in raw):
        return form
    draft = normalize_wizard_draft(raw)
    mapped = map_draft_to_internal_fields(draft, form)
    # In all choice-based modes the main downloaded/report markdown must stay human-readable.
    # Raw matrices/DDL are only for true expert mode.
    mapped['report_detail'] = 'human'
    return mapped

def parse_post(body):
    raw=parse_qs(body); f={}
    for _,_,qs in QUESTIONS:
        for qid,_,typ,default,_ in qs:
            if typ=='multi':
                f[qid]=raw.get(qid, default.split(','))
            else:
                f[qid]=raw.get(qid,[default])[0]
    f['preset_name']=raw.get('preset_name',[''])[0]
    for extra_key in ['delivery_guarantee','audit_required','rollback_plan','manual_recovery_owner','lineage_required','data_quality_required','report_detail','ux_mode','project_name','business_goal','task_type','systems_matrix','process_steps','target_integration_matrix','contract_matrix','error_matrix','process_graph_json','process_graph_meta','custom_chain_json','business_case','business_process_json','business_actors_json','business_steps_json','business_object','business_result_timing','business_result_type','business_constraints_json','business_criticality','auto_generated_technical_chain_json','simple_situation','simple_goal','simple_q_systems','simple_q_immediate','simple_q_payload','simple_q_risk','simple_q_external','simple_q_source_change','simple_q_load','simple_q_critical','simple_q_error','simple_q_status','operation_kind','result_model','delivery','load_profile','sensitivity','money_impact','regulatory_impact','source_change_policy','allowed_channels','forbidden_channels','orchestration','step_count','chain_depth','partial_response_ok','replay','retention','current_controls','kafka_topology','consistency']:
        if extra_key in raw:
            f[extra_key]=raw.get(extra_key,[''])[0]
    if 'constraint_flags' in raw:
        f['constraint_flags']=raw.get('constraint_flags', [])
    if 'business_situations' in raw:
        f['business_situations']=raw.get('business_situations', [])
    return apply_progressive_ui_mapping(raw, f)

def yaml_scalar(v):
    text=str(v).replace('"','\\"')
    if any(ch in text for ch in [':','#','\n','{','}','[',']',',']):
        return '"'+text+'"'
    return text

def make_openapi_yaml(res):
    rec=res.get('recommended',{})
    ent='entity'
    return f'''openapi: 3.0.3
info:
  title: Integration API Contract
  version: 1.0.0
  description: Generated by Integration Architect Pro v5.0.9 for {yaml_scalar(ru_label(rec.get('name','')))}
paths:
  /api/v1/{ent}:
    post:
      summary: Start or create integration process
      parameters:
        - in: header
          name: X-Request-Id
          schema: {{ type: string }}
          required: true
        - in: header
          name: Correlation-Id
          schema: {{ type: string }}
          required: true
        - in: header
          name: Idempotency-Key
          schema: {{ type: string }}
          required: false
      responses:
        '202': {{ description: Accepted for processing }}
        '400': {{ description: Validation error }}
        '409': {{ description: Duplicate or conflicting request }}
        '429': {{ description: Rate limit exceeded }}
        '500': {{ description: Technical error }}
  /api/v1/{ent}/{{id}}:
    get:
      summary: Get current state/status
      parameters:
        - in: path
          name: id
          schema: {{ type: string }}
          required: true
        - in: header
          name: Correlation-Id
          schema: {{ type: string }}
          required: true
      responses:
        '200': {{ description: Current status }}
        '404': {{ description: Not found }}
components:
  schemas:
    Error:
      type: object
      required: [code, message, correlationId]
      properties:
        code: {{ type: string }}
        message: {{ type: string }}
        correlationId: {{ type: string }}
'''

def make_event_contract_json(res):
    rec=res.get('recommended',{})
    pids=rec.get('pattern_ids',[])
    contract={
      'schema':'integration-event-contract-v1',
      'topic':'<define-topic-name>',
      'partitionKey':'aggregateId/entityId',
      'delivery':'at-least-once; consumers must be idempotent',
      'envelope':{
        'eventId':'uuid, required, unique','eventType':'string, required','eventVersion':'integer, required',
        'producer':'string, required','businessOwner':'string, required','occurredAt':'timestamp, required',
        'publishedAt':'timestamp, required','correlationId':'string, required','causationId':'string, optional',
        'aggregateId':'string, required','aggregateVersion':'integer, recommended'},
      'payload':{'type':'object','compatibility':'backward-compatible by default'},
      'consumerRules':['deduplicate by eventId','handle retries and duplicates','handle out-of-order by aggregateVersion/timestamp','send invalid accepted events to DLQ/quarantine'],
      'observability':['consumer_lag','published_total','failed_total','dlq_size','retry_rate']}
    if 'selective_consumer' in pids:
        contract['selectiveConsumer']={'inputTopic':'shared topic','filter':'key/header/body deterministic rule','metrics':['consumed_total','filtered_out_total','accepted_total','filter_ratio','db_write_latency'],'commitPolicy':'commit only after safe write or deterministic skip'}
    if 'integration_publisher' in pids:
        contract['enrichment']={'sourceEventId':'required','consistency':'AS_OF_CHANGE | CURRENT_AT_PUBLISH | BEST_EFFORT','failure':'no silent drop; retry/manual reprocess'}
    return json.dumps(contract,ensure_ascii=False,indent=2)

def make_risk_register_md(res):
    anti=res.get('anti_patterns',[])
    rows=['| Риск | Severity | Где | Что сделать | Owner |','|---|---|---|---|---|']
    if not anti:
        rows.append('| Критичных рисков не выявлено | low | n/a | Подтвердить ADR, тесты и мониторинг | Архитектор/SA |')
    for a in anti:
        rows.append(f"| {str(a.get('title','')).replace('|','/')} | {a.get('severity','')} | {str(a.get('where','process')).replace('|','/')} | {str(a.get('fix','')).replace('|','/')} | TBD |")
    return '# Risk Register\n\n'+'\n'.join(rows)+'\n'

def make_test_cases_md(res):
    life=res.get('lifecycle',{}) or {}
    scenarios=res.get('scenarios',{}) or {}
    tests=list(life.get('tests',[]) or [])
    base=['happy path','duplicate request/event','timeout from external dependency','retry exhausted','DLQ/quarantine replay','consumer/process crash before commit','DB unavailable','schema incompatible','out-of-order event','security/auth failure','rollback/canary disable','reconciliation mismatch']
    for x in base:
        if x not in tests: tests.append(x)
    md=['# Test Cases / QA Pack\n']
    for i,t in enumerate(tests,1):
        md.append(f'## TC-{i:03d}: {t}\n')
        md.append('- Given: входные данные и зависимости подготовлены.\n- When: выполняется сценарий/ошибка.\n- Then: система сохраняет корректный статус, не создаёт дублей, пишет audit/metrics и позволяет recovery.\n')
    if scenarios.get('alternatives'):
        md.append('## Alternative/error scenarios from model\n')
        for k,v in scenarios.get('alternatives',{}).items(): md.append(f'- **{k}**: '+ '; '.join(v)+'\n')
    return '\n'.join(md)

def make_checklist_md(res):
    gate=(res.get('production_gate') or {})
    ready=res.get('readiness',{}) or {}
    rec=res.get('recommended',{}) or {}
    items=['ADR approved','source of truth and ownership approved','API/event/file contracts versioned','idempotency for commands/events','timeouts for sync calls','retry/backoff and DLQ/quarantine for async','correlationId/tracing/log masking','metrics/alerts/dashboard','load/stress/failover tests','replay/recovery runbook','security review','rollback/canary/feature-toggle plan']
    md=['# Production Checklist\n',f"Recommended architecture: **{ru_label(rec.get('name',''))}**\n",f"Gate: **{gate.get('level','UNKNOWN')}** — {gate.get('text','')}\n",f"Readiness score: **{ready.get('score','?')}%**\n"]
    if gate.get('blocking_gaps'):
        md.append('## Blocking gaps\n'+bullet(gate.get('blocking_gaps')))
    md.append('## Checklist\n')
    md.extend([f'- [ ] {x}\n' for x in items])
    return ''.join(md)

def make_adr_md(res):
    adr=((res.get('advanced') or {}).get('adr') or (res.get('structured_result') or {}).get('adr') or {})
    md=['# ADR-001: Integration Architecture Decision\n']
    md.append('## Context\n'+bullet(adr.get('context')))
    md.append('## Decision\n'+bullet(adr.get('decision')))
    md.append('## Alternatives\n'+bullet(adr.get('alternatives')))
    md.append('## Consequences\n'+bullet(adr.get('consequences')))
    md.append('## Rollback\n- Feature toggle/canary rollback.\n- Replay/reconciliation plan before full rollout.\n')
    return ''.join(md)

def make_integration_design_md(res):
    return res.get('markdown','')

def make_document_bundle(res, rid, ver):
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix=f'integration_architect_v5_0_9_bundle_{ver}_{stamp}_{rid[:6]}'
    folder=OUT_DIR/prefix
    folder.mkdir(parents=True,exist_ok=True)
    files={
      'integration_design.md':make_integration_design_md(res),
      'ADR.md':make_adr_md(res),
      'api_contract.yaml':make_openapi_yaml(res),
      'event_contract.json':make_event_contract_json(res),
      'test_cases.md':make_test_cases_md(res),
      'risk_register.md':make_risk_register_md(res),
      'checklist.md':make_checklist_md(res),
      'structured_result.json':json.dumps({k:v for k,v in res.items() if k!='markdown'},ensure_ascii=False,indent=2,default=str),
    }
    for name,content in files.items(): (folder/name).write_text(content,encoding='utf-8')
    zipname=prefix+'.zip'; zippath=OUT_DIR/zipname
    with zipfile.ZipFile(zippath,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files: z.write(folder/name,arcname=name)
    return zipname, prefix, list(files.keys())

def simple_result_summary(res):
    rec = res.get('recommended', {})
    patterns = rec.get('patterns', [])[:5]
    anti = res.get('anti_patterns', [])[:5]
    ready = res.get('readiness', {})
    md = res.get('markdown','')
    bullets = []
    bullets.append(f"Главный вариант: {ru_label(rec.get('name','не определён'))}.")
    if patterns:
        bullets.append("Ключевые паттерны: " + ", ".join(patterns) + ".")
    if ready.get('score') is not None:
        bullets.append(f"Готовность входных данных: {ready.get('score')}%; доверие к выводу: {ready.get('confidence', ready.get('score'))}%.")
    if anti:
        worst = [a for a in anti if a.get('severity') in ['critical','high']]
        if worst:
            bullets.append("Сначала закрыть риски: " + "; ".join(a.get('title','') for a in worst[:3]) + ".")
        else:
            bullets.append("Критичных anti-patterns в первых проверках не найдено, но отчёт всё равно нужно прочитать.")
    if '## 2A. Ограничения, компромиссы и реалистичный вариант' in md:
        bullets.append("Отчёт разделяет реалистичный v1 при ограничениях и целевую production-архитектуру.")
    return bullets


def _graph_edge_human_py(tp):
    m={
        'success':'success', 'parallel_start':'fork/parallel', 'parallel_join':'join', 'business_error':'condition',
        'timeout':'timeout', 'fallback':'fallback', 'reprocess':'reprocess', 'compensation':'compensation',
        'retry':'retry', 'manual_recovery':'manual recovery', 'event_trigger':'event', 'scheduled':'scheduled'
    }
    return m.get(str(tp or '').lower(), str(tp or 'next'))


def _graph_node_badges_py(n):
    badges=[]
    ch=str(n.get('channel') or '').strip()
    if ch: badges.append(ch)
    badges.append('sync/wait' if n.get('user_waits') else 'async')
    if n.get('idempotency_required'): badges.append('idempotency')
    if str(n.get('retry_policy') or '').strip(): badges.append('retry/recovery')
    tp=str(n.get('type') or '').lower()
    if tp in ['parallel_start','parallel_join','fan_in','decision']: badges.append('branch/join')
    if tp in ['retry_loop','polling_loop','reconciliation']: badges.append('loop')
    if tp in ['wait_callback','wait_event']: badges.append('wait/callback')
    if tp in ['compensation','manual_task','reprocess']: badges.append('recovery')
    out=[]
    for x in badges[:5]:
        out.append(f"<span>{escape(str(x))}</span>")
    return ''.join(out)


def result_process_flow_html(res):
    ctx = res.get('ctx', {}) or {}
    # When the engine did not preserve the original form, infer the graph from ctx.steps.
    graph = extract_process_graph({}, ctx)
    nodes = list(graph.get('nodes') or [])
    edges = list(graph.get('edges') or [])
    if not nodes:
        return "<div class='chain-empty'>Схема процесса пока не построена. Добавьте шаги цепочки — и здесь появится нормальная визуализация потока, retry, callback и recovery.</div>"

    node_map={str(n.get('id')):n for n in nodes}
    edge_map={(str(e.get('from_node_id')), str(e.get('to_node_id'))): e for e in edges}

    def node_cls(n):
        tp=str(n.get('type') or '').lower()
        if tp in ['parallel_start','parallel_join','fan_in','decision']: return 'parallel'
        if tp in ['retry_loop','polling_loop','reconciliation']: return 'loop'
        if tp in ['wait_event','wait_callback']: return 'wait'
        if tp in ['compensation','manual_task','reprocess']: return 'compensation'
        return ''

    def title(n):
        return escape(str(n.get('title') or human_node_type(n.get('type')) or 'Шаг процесса'))

    steps=[]
    for i,n in enumerate(nodes):
        nid=str(n.get('id') or f'S{i+1}')
        target=str(n.get('target_system_id') or '').strip()
        meta=[f"<span>{escape(str(n.get('system_id') or 'System'))}</span>"]
        if target:
            meta.append(f"<span>→ {escape(target)}</span>")
        meta.append(_graph_node_badges_py(n))
        node_html=(
            f"<div class='complex-flow-node {node_cls(n)}'>"
            f"<div class='complex-node-top'><span class='complex-node-id'>{escape(nid)}</span><span class='complex-node-kind'>{escape(human_node_type(n.get('type')))}</span></div>"
            f"<div class='complex-node-title'>{title(n)}</div>"
            f"<div class='complex-node-meta'>{''.join(meta)}</div>"
            f"</div>"
        )
        edge_html=''
        if i < len(nodes)-1:
            nxt=str(nodes[i+1].get('id') or f'S{i+2}')
            edge=edge_map.get((nid,nxt), {})
            label=_graph_edge_human_py(edge.get('transition_type') or edge.get('condition') or 'success')
            edge_html=(
                f"<div class='complex-flow-edge'>"
                f"<span class='complex-edge-label'>{escape(label)}</span>"
                f"<span class='complex-edge-arrow'>→</span>"
                f"</div>"
            )
        steps.append(f"<div class='complex-flow-step'>{node_html}{edge_html}</div>")

    caps=graph_capabilities(graph)
    summary=''.join([
        f"<span><b>{len(nodes)}</b> шагов</span>",
        f"<span><b>{sum(1 for n in nodes if str(n.get('type','')).lower() in ['parallel_start','parallel_join','fan_in','decision'])}</b> ветвлений/join</span>",
        f"<span><b>{sum(1 for n in nodes if str(n.get('type','')).lower() in ['retry_loop','polling_loop','reconciliation'])}</b> циклов</span>",
        f"<span><b>{sum(1 for n in nodes if str(n.get('type','')).lower() in ['wait_callback','wait_event'])}</b> ожиданий callback/event</span>",
        f"<span><b>{sum(1 for n in nodes if str(n.get('type','')).lower() in ['compensation','manual_task','reprocess'])}</b> recovery/compensation</span>",
        f"<span><b>{sum(1 for n in nodes if n.get('user_waits'))}</b> блокирующих шагов</span>",
    ])

    special_edges=[]
    sequential_pairs={(str(nodes[i].get('id') or f'S{i+1}'), str(nodes[i+1].get('id') or f'S{i+2}')) for i in range(len(nodes)-1)}
    for e in edges:
        pair=(str(e.get('from_node_id') or ''), str(e.get('to_node_id') or ''))
        if pair in sequential_pairs and (e.get('transition_type') or 'success') == 'success':
            continue
        if pair[0] == pair[1] or pair not in sequential_pairs or (e.get('transition_type') or 'success') != 'success':
            src=node_map.get(pair[0],{}).get('title') or pair[0]
            dst=node_map.get(pair[1],{}).get('title') or pair[1]
            special_edges.append(f"<li><b>{escape(str(src))}</b> → <b>{escape(str(dst))}</b>: {escape(_graph_edge_human_py(e.get('transition_type') or e.get('condition') or 'transition'))}</li>")

    explain=[]
    if caps.get('parallel'): explain.append('есть ветвление / параллельные участки')
    if caps.get('loops'): explain.append('есть циклы retry / polling / reconciliation')
    if caps.get('wait'): explain.append('есть ожидание callback/event')
    if caps.get('compensation'): explain.append('есть recovery / компенсация / ручной разбор')
    if not explain: explain.append('основной сценарий последовательный, без сложных разветвлений')

    special_block=("<div class='readiness-list' style='margin-top:12px'><b>Дополнительные переходы и специальные ветки</b><ul class='todo-list'>" + ''.join(special_edges[:12]) + "</ul></div>") if special_edges else ""

    return (
        "<div class='card'>"
        "<div class='chain-section-title'><div><h2>Визуальная схема потока процесса</h2><p class='muted chain-subtitle'>Это нормальная схема процесса, а не набор бессвязных карточек. Слева направо видно основной поток, над стрелками — тип перехода, а цветом выделены циклы, ожидания callback и recovery.</p></div><span class='mode-badge'>Поток выполнения</span></div>"
        + "<div class='chain-hint'><b>Как читать схему:</b> тёмные блоки — обычные шаги, синие — ветвление/join, жёлтые — циклы retry/polling/reconciliation, фиолетовые — ожидание callback/event, красные — компенсация или ручное восстановление. Для понимания важно смотреть не только на шаги, но и на подписи над стрелками.</div>"
        + f"<div class='complex-graph-preview'><div class='complex-flow-map'>{''.join(steps)}</div><div class='complex-flow-summary'>{summary}</div><p class='small'>По этой схеме видно, {escape('; '.join(explain))}. Ниже, в карте сервисов, показывается уже разрез по участникам, контрактам и хранилищам.</p></div>"
        + special_block
        + "</div>"
    )


def service_chain_html(res):
    ctx = res.get('ctx', {}) or {}
    db = res.get('db', {}) or {}
    systems = list(ctx.get('systems') or [])
    steps = list(ctx.get('steps') or [])
    integrations = list(ctx.get('target_integrations') or [])
    if not systems:
        seen=[]
        for st in steps:
            name=(st.get('system') or '').strip()
            if name and name not in seen:
                seen.append(name)
                systems.append({
                    'name':name,
                    'role':'участник процесса',
                    'owner':st.get('owner','TBD'),
                    'criticality':'unknown',
                    'channel':st.get('channel',''),
                    'blocking':st.get('blocking',''),
                    'sla':st.get('timeout','')
                })
    if not systems and not integrations:
        return ''

    step_by_system={}
    for st in steps:
        step_by_system.setdefault(st.get('system','Не указан'),[]).append(st)

    tables = db.get('tables') or []
    integration_rows=[]
    if integrations:
        for i in integrations[:16]:
            integration_rows.append({
                'from': i.get('from','?'),
                'channel': i.get('channel','?') or '?',
                'to': i.get('to','?'),
                'contract': i.get('contract','') or 'уточнить контракт',
                'data': i.get('data','') or i.get('trigger','') or 'payload уточнить',
                'retry': i.get('retry','') or 'уточнить',
                'dlq': i.get('dlq','') or 'n/a',
                'idempotency': i.get('idempotency','') or 'уточнить',
                'mode': i.get('mode','') or ''
            })
    else:
        prev=None
        for st in steps[:16]:
            cur=st.get('system') or '?'
            if prev and prev!=cur:
                integration_rows.append({
                    'from': prev,
                    'channel': st.get('channel','?') or '?',
                    'to': cur,
                    'contract': st.get('step','') or 'связь по шагу процесса',
                    'data': st.get('input','') or st.get('output','') or 'данные уточнить',
                    'retry': st.get('retry','') or 'уточнить',
                    'dlq': 'n/a',
                    'idempotency': st.get('idempotency','') or 'уточнить',
                    'mode': st.get('blocking','') or ''
                })
            prev=cur

    channels = sorted({str((x.get('channel') or '')).upper() for x in integrations if x.get('channel')} | {str((x.get('channel') or '')).upper() for x in steps if x.get('channel')})
    sync_count = sum(1 for x in integration_rows if str(x.get('channel','')).lower() in ['rest','http','grpc','soap'])
    async_count = sum(1 for x in integration_rows if str(x.get('channel','')).lower() in ['kafka','queue','amqp','event','webhook'])

    cards=[]
    for idx, sys in enumerate(systems[:12], 1):
        name=sys.get('name') or sys.get('system') or 'Сервис'
        own=sys.get('owner') or 'owner уточнить'
        role=sys.get('role') or 'роль уточнить'
        st_items=step_by_system.get(name,[])[:4]
        if st_items:
            lis=''.join(
                f"<li><b>{escape(x.get('step','шаг'))}</b><span class='small'>Канал: {escape(x.get('channel','?'))}; input: {escape(x.get('input','—'))}; output: {escape(x.get('output','—'))}</span></li>"
                for x in st_items
            )
        else:
            lis='<li><b>Шаги не указаны явно</b><span class="small">Можно дополнить matrix шагов, чтобы визуализация стала детальнее.</span></li>'
        badge_parts=[]
        if role:
            badge_parts.append(f"<span class='badge cyan'>{escape(role)}</span>")
        if own:
            badge_parts.append(f"<span class='badge'>owner: {escape(own)}</span>")
        channel_set=[]
        for x in st_items:
            ch=(x.get('channel') or '').upper()
            if ch and ch not in channel_set:
                channel_set.append(ch)
        if sys.get('channel'):
            ch=str(sys.get('channel')).upper()
            if ch and ch not in channel_set:
                channel_set.append(ch)
        for ch in channel_set[:3]:
            badge_parts.append(f"<span class='badge green'>{escape(ch)}</span>")
        if sys.get('sla'):
            badge_parts.append(f"<span class='badge amber'>SLA/timeout: {escape(sys.get('sla'))}</span>")
        cards.append(
            f"<div class='chain-stage'><div class='chain-stage-head'><div class='chain-stepno'>{idx}</div><div><h3>{escape(name)}</h3><div class='chain-role'>{escape(role)} · владелец: {escape(own)}</div></div></div><div class='badge-row'>{''.join(badge_parts)}</div><ul class='chain-list'>{lis}</ul></div>"
        )

    storage_html=''
    if tables:
        storage_cards=[]
        for t in tables[:8]:
            indexes=', '.join(t.get('indexes',[]) or [])
            extra = f"<li><span class='small'>Индексы: {escape(indexes)}</span></li>" if indexes else ''
            storage_cards.append(
                f"<div class='storage-card'><h4>{escape(t.get('name','table'))}</h4><ul><li>{escape(t.get('purpose','назначение уточнить'))}</li>{extra}</ul></div>"
            )
        storage_html = "<div class='storage-panel'><h3>БД и хранилища</h3><p class='muted'>Показываем, где хранится статус процесса, техническое состояние и артефакты для recovery.</p><div class='storage-list'>" + ''.join(storage_cards) + "</div></div>"
    else:
        storage_html = "<div class='storage-panel'><h3>БД и хранилища</h3><div class='chain-empty'>Таблицы не заданы явно. Если заполнить раздел про БД / outbox / idempotency, здесь появится точная структура хранения.</div></div>"

    if integration_rows:
        interaction_cards=[]
        for row in integration_rows[:14]:
            mode = f"<span class='badge'>{escape(row.get('mode'))}</span>" if row.get('mode') else ''
            interaction_cards.append(
                f"<div class='integration-card'><div class='integration-top'><div class='integration-route'><span class='node-pill'>{escape(row['from'])}</span><span class='route-arrow'>→</span><span class='node-pill'>{escape(row['to'])}</span></div><div class='badge-row'><span class='badge cyan'>{escape(str(row['channel']).upper())}</span>{mode}</div></div><div class='integration-meta'><div class='meta-box'><b>Контракт / вызов</b><span>{escape(row['contract'])}</span></div><div class='meta-box'><b>Какие данные идут</b><span>{escape(row['data'])}</span></div><div class='meta-box'><b>Retry / DLQ</b><span>retry={escape(row['retry'])}; DLQ={escape(row['dlq'])}</span></div><div class='meta-box'><b>Идемпотентность</b><span>{escape(row['idempotency'])}</span></div></div></div>"
            )
        interactions_html = ''.join(interaction_cards)
    else:
        interactions_html = "<div class='chain-empty'>Связи пока определены слишком общо. Добавьте target integration matrix или шаги процесса — и появится подробная карта взаимодействий.</div>"

    legend = "".join([
        "<span class='badge cyan'>REST / HTTP / gRPC — синхронные вызовы</span>",
        "<span class='badge green'>Kafka / Queue / Event — асинхронные взаимодействия</span>",
        "<span class='badge amber'>SLA / timeout — где особенно важны деградация и fallback</span>"
    ])

    return (
        "<div class='card'><div class='chain-section-title'><div><h2>Визуальная карта цепочки сервисов и данных</h2><p class='muted chain-subtitle'>Не просто схема, а наглядное представление: кто в цепочке участвует, что делает каждый сервис, где идут синхронные и асинхронные вызовы, и какие данные нужно хранить для статусов, retry, идемпотентности и recovery.</p></div><span class='mode-badge'>Наглядная визуализация результата</span></div>"
        + f"<div class='chain-kpis'><div class='chain-kpi'><b>{len(systems)}</b><span>сервисов / систем в цепочке</span></div><div class='chain-kpi'><b>{len(integration_rows)}</b><span>интеграционных взаимодействий</span></div><div class='chain-kpi'><b>{len(tables)}</b><span>таблиц / хранилищ описано</span></div><div class='chain-kpi'><b>{sync_count}/{async_count}</b><span>синхронных / асинхронных связей</span></div></div>"
        + "<div class='chain-hint'><b>Как читать блок:</b> сверху показан основной поток по сервисам, ниже — детальные карточки взаимодействий и отдельно слой хранения данных. На мобильном всё складывается в вертикальную понятную ленту.</div>"
        + "<div class='chain-viz'><div class='chain-track'>" + ''.join(cards) + "</div><div class='chain-legend'>" + legend + "</div></div>"
        + "<div class='chain-grid'><div class='integration-panel'><h3>Детализация интеграционных взаимодействий</h3><p class='muted'>Для каждой связи видно канал, контракт, payload, retry / DLQ и ключ идемпотентности.</p><div class='integration-list'>" + interactions_html + "</div></div>"
        + storage_html + "</div></div>"
    )

def service_chain_markdown(ctx, db):
    systems=list((ctx or {}).get('systems') or [])
    steps=list((ctx or {}).get('steps') or [])
    integrations=list((ctx or {}).get('target_integrations') or [])
    lines=['## 17A. Карта цепочки сервисов, БД и интеграций\n']
    lines.append('### Что делает каждый сервис\n')
    for sys in systems[:20]:
        name=sys.get('name') or 'Сервис'
        owned_steps=[x for x in steps if x.get('system')==name]
        lines.append(f"- **{name}** — роль: {sys.get('role','')}; owner: {sys.get('owner','')}; SLA: {sys.get('sla','')}.\n")
        for st in owned_steps[:6]:
            lines.append(f"  - Делает: {st.get('step','')}; канал: {st.get('channel','')}; input: {st.get('input','')}; output: {st.get('output','')}; retry: {st.get('retry','')}; compensation: {st.get('compensation','')}.\n")
    lines.append('### Связи между сервисами\n')
    if integrations:
        for i in integrations[:20]:
            lines.append(f"- **{i.get('from','?')} → {i.get('to','?')}** через {i.get('channel','?')}; mode={i.get('mode','')}; contract={i.get('contract','')}; data={i.get('data','')}; retry={i.get('retry','')}; DLQ={i.get('dlq','')}; idempotency={i.get('idempotency','')}.\n")
    else:
        prev=None
        for st in steps[:20]:
            cur=st.get('system') or '?'
            if prev and prev!=cur:
                lines.append(f"- **{prev} → {cur}** через {st.get('channel','?')}; шаг: {st.get('step','')}; timeout={st.get('timeout','')}; retry={st.get('retry','')}.\n")
            prev=cur
    tables=(db or {}).get('tables') or []
    if tables:
        lines.append('### Взаимодействие с БД/хранилищем\n')
        for t in tables[:12]:
            lines.append(f"- **{t.get('name','table')}** — {t.get('purpose','')}. Индексы: {', '.join(t.get('indexes',[]) or [])}.\n")
    return ''.join(lines)+'\n'


def _diagram_node_class(name):
    n=str(name).lower()
    if any(x in n for x in ['db','outbox','inbox','dwh','staging','cache','registry']):
        return 'diagram-node diagram-node-db'
    if any(x in n for x in ['worker','publisher','consumer','adapter','bff','composition']):
        return 'diagram-node diagram-node-worker'
    if any(x in n for x in ['quarantine','reconciliation','risk','callback']):
        return 'diagram-node diagram-node-error'
    return 'diagram-node diagram-node-main'

def _diagram_icon(name):
    n=str(name).lower()
    if any(x in n for x in ['db','outbox','inbox','dwh','staging','cache','registry']): return '▣'
    if any(x in n for x in ['worker','publisher','consumer','adapter','bff','composition']): return '⚙'
    if any(x in n for x in ['kafka','event']): return '⇄'
    if 'file' in n: return '▤'
    if 'callback' in n: return '↩'
    return '●'

def interaction_diagram_html(schema):
    nodes=[x.strip() for x in str(schema or '').split('→') if x.strip()]
    cards=[]
    total=len(nodes)
    for i,n in enumerate(nodes):
        role='Запускает поток' if i==0 else ('Получает результат' if i==total-1 else 'Обрабатывает и передаёт дальше')
        cards.append(f"<div class='{_diagram_node_class(n)}'><div class='diagram-icon'>{escape(_diagram_icon(n))}</div><div class='diagram-title'>{escape(n)}</div><div class='diagram-role'>{escape(role)}</div></div>")
        if i < total-1:
            cards.append("<div class='diagram-edge'>→</div>")
    return "<div class='interaction-diagram'><div class='diagram-track'>" + ''.join(cards) + "</div><div class='diagram-side'><span class='diagram-chip'>ошибка/retry</span><span class='diagram-chip'>статус</span><span class='diagram-chip'>ручной разбор</span></div></div>"

def storage_items_from_form(form):
    form=form or {}
    storage=str(form.get('data_storage_choice','') or 'none')
    role=str(form.get('data_storage_role','') or 'none')
    mapping={
      'task_table':['integration_task DB','статусы задач','monitoring stuck tasks'],
      'outbox':['transactional outbox','publisher retry','publish status'],
      'inbox':['inbox/idempotency','duplicate protection'],
      'cache_read_model':['Cache / Read Model','freshness marker','stale data policy'],
      'dwh_staging':['watermark','reconciliation','data quality checks'],
      'file_registry':['file_id','checksum','batch_id','quarantine','reprocessing'],
      'service_db':['business DB','status table'],
    }
    items=list(mapping.get(storage, []))
    role_map={
      'business_data':'роль базы: хранит бизнес-данные',
      'task_state':'роль базы: хранит задачу на обработку',
      'process_status':'роль базы: хранит статус процесса',
      'event_before_publish':'роль базы: хранит события перед публикацией',
      'duplicate_protection':'роль базы: защищает от дублей',
      'last_known_status':'роль базы: хранит последний известный статус',
      'reporting':'роль базы: используется для отчётности',
      'reconciliation':'роль базы: используется для сверки/reconciliation',
    }
    if role in role_map:
        items.append(role_map[role])
    return items

def result_page(res,rid,fname,bundle_name=None,json_name=None):
    case_type = res.get('case_type') or (res.get('ctx') or {}).get('case_type') or 'sync_rest'
    specialized_case = res.get('specialized_case') or (res.get('ctx') or {}).get('specialized_case') or specialized_case_from_form(res.get('form') or {}, case_type)
    schema = res.get('case_schema') or custom_schema_from_form(res.get('form') or {}) or build_canonical_schema_for_case(specialized_case) or CASE_SCHEMAS.get(case_type, CASE_SCHEMAS['sync_rest'])
    checklist = res.get('case_checklist') or case_specific_handoff(specialized_case, case_type) or []
    storage_extras = storage_items_from_form(res.get('form') or {})
    checklist = list(checklist) + [x for x in storage_extras if x not in checklist]
    risks = risks_for_specialized_case(specialized_case, case_type, res.get('form') or {})
    risk_items = [f'{a} → {c}' for a, b, c in risks[:5]]
    process = concrete_process(case_type)
    readiness = res.get('readiness') or {'score': 0}
    score = readiness.get('score', 0)
    handoff = case_specific_handoff(specialized_case, case_type)
    def li(items):
        return ''.join(f'<li>{escape(str(x))}</li>' for x in items)
    readiness_label = 'Полный отчёт' if score >= 70 else ('Предварительный результат' if score >= 40 else 'Черновик')
    form = res.get('form') or {}
    ordered_steps_text = ordered_business_process_text(form)
    order_warnings = business_order_warnings_from_form(form)
    business_process = ordered_steps_text or (form.get('business_goal') or '').strip() or case_summary(form, case_type)
    summary = specialized_case_summary(specialized_case, case_type, form) + ((' Порядок бизнес-шагов учтён: ' + business_process.replace('\n', ' → ')) if ordered_steps_text else '')
    technical = technical_details_for_case(case_type)
    full_links = f'<a class="btn" href="/download?file={escape(fname)}">Скачать markdown</a>'
    if json_name:
        full_links += f'<a class="btn" href="/download?file={escape(json_name)}">Скачать JSON bundle</a>'
    if bundle_name:
        full_links += f'<a class="btn" href="/download?file={escape(bundle_name)}">Скачать пакет ZIP</a>'
    if score < 40:
        missing = (readiness.get('missing') or readiness.get('gaps') or ['ситуация', 'участвующие системы', 'ответ сразу или позже', 'что передаём', 'главный риск', 'обработка ошибок', 'статус процесса'])
        content = f"""<div class="card result-human-page">
          <h1>Черновик</h1>
          <div class="warnbox"><b>Пока данных мало</b> · готовность {escape(str(score))}%</div>
          <p class="muted">Недостаточно данных для архитектурного вывода. Полная схема, рекомендации и отчёт заблокированы, чтобы не выдавать случайные советы.</p>
          <div class="simple-result"><h3>Что нужно выбрать</h3><ul class="todo-list">{li(missing)}</ul></div>
          <div class="report-actions"><a class="btn secondary" href="/">Вернуться к конструктору</a></div>
        </div>
        <details class="full-report card"><summary>Открыть черновик</summary><div class="result">{escape(res.get('markdown',''))}</div></details>"""
        return HTML.replace('{content}', content)
    content = f"""<div class="card result-human-page">
      <h1>Результат</h1>
      <p class="muted">Сначала показаны бизнес-процесс, схема, объяснение выбора, обязательные элементы, риски и handoff. Полный markdown скрыт ниже.</p>
      <div class="warnbox"><b>{escape(readiness_label)}</b> · готовность {escape(str(score))}%</div>
      <div class="simple-result"><h3>1. Бизнес-процесс</h3><p>{escape(business_process)}</p></div>
      <div class="simple-result"><h3>2. Класс сложного кейса</h3><p>{escape(case_class_narrative(specialized_case, case_type, res.get('form') or {}))}</p></div>
      <div class="simple-result"><h3>3. Схема взаимодействия</h3>{interaction_diagram_html(schema)}</div>
      <div class="simple-result"><h3>4. Почему выбрана такая схема</h3><p>{escape(summary)}</p></div>
      <div class="simple-result-grid four-blocks">
        <div class="simple-result"><h3>5. Что обязательно сделать</h3><ul class="todo-list">{li(checklist)}</ul></div>
        <div class="simple-result"><h3>6. Главные риски</h3><ul class="todo-list">{li(risk_items + order_warnings)}</ul></div>
        <div class="simple-result"><h3>7. Что отдать разработке</h3><ul class="todo-list">{li(handoff)}</ul></div>
      </div>
      <h3>8. Пошаговый процесс</h3><div class="simple-result"><ol class="todo-list">{li(process)}</ol></div>
      <div class="report-actions">{full_links}<a class="btn secondary" href="/run?id={escape(rid)}">Открыть run</a><a class="btn secondary" href="/">Вернуться к конструктору</a></div>
    </div>
    <details class="full-report card"><summary>Открыть полный отчёт</summary><div class="result">{escape(res.get('markdown',''))}</div></details>
    <details class="full-report card"><summary>Показать технические детали</summary><div class="must-checklist">{''.join(f'<span>✓ {escape(str(x))}</span>' for x in technical)}</div></details>"""
    content = explain_english_terms_ru_html_fragment(content)
    return HTML.replace('{content}', content)

class Handler(BaseHTTPRequestHandler):
    def send_html(self,s,status=200):
        data=s.encode('utf-8'); self.send_response(status); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path.startswith('/download'):
            q=self.path.split('?',1)[1] if '?' in self.path else ''; fn=Path(parse_qs(q).get('file',[''])[0]).name; fp=OUT_DIR/fn
            if not fp.exists(): return self.send_html('Файл не найден',404)
            data=fp.read_bytes(); self.send_response(200); ctype='application/zip' if fn.endswith('.zip') else 'text/markdown; charset=utf-8'; self.send_header('Content-Type',ctype); self.send_header('Content-Disposition',f'attachment; filename="{fn}"'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
        if self.path.startswith('/run'):
            q=self.path.split('?',1)[1] if '?' in self.path else ''; row=get_run(parse_qs(q).get('id',[''])[0])
            if not row: return self.send_html('Run не найден',404)
            return self.send_html(HTML.replace('{content}', f'<div class="card"><h2>Сохранённая генерация v{row["version"]}</h2><p><a href="/">Новая генерация</a></p><div class="result">{escape(row["markdown"])}</div></div>'))
        if self.path == '/' or self.path.startswith('/?'):
            return self.send_html(form_page())
        return self.send_html('Not found',404)
    def do_POST(self):
        if self.path!='/generate': return self.send_html('Not found',404)
        content_length=int(self.headers.get('Content-Length','0'))
        if content_length > MAX_POST_BYTES:
            return self.send_html('Payload too large',413)
        body=self.rfile.read(content_length).decode('utf-8')
        try:
            form=parse_post(body); res=Engine().generate(form); pid,rid,ver=save_run(form,res); stamp=datetime.now().strftime("%Y%m%d_%H%M%S"); fname=f'integration_architect_report_v5_0_9_{ver}_{stamp}_{rid[:6]}.md'; (OUT_DIR/fname).write_text(res['markdown'],encoding='utf-8'); json_name=f'integration_architect_bundle_v5_0_9_{ver}_{stamp}_{rid[:6]}.json'; (OUT_DIR/json_name).write_text(json.dumps({'form': form, 'result': {k:v for k,v in res.items() if k!='markdown'}, 'markdown_file': fname}, ensure_ascii=False, indent=2, default=str), encoding='utf-8'); bundle_name,_,_=make_document_bundle(res,rid,ver); self.send_html(result_page(res,rid,fname,bundle_name,json_name))
        except Exception as e:
            self.send_html('<h1>Ошибка</h1><pre>'+escape(str(e))+'</pre>',500)
def main():
    init_db(); server=HTTPServer((HOST,PORT),Handler); print(f'Интеграционный инструктор v5.0.9: http://{HOST}:{PORT}'); print(f'SQLite: {DB_PATH}');
    try: server.serve_forever()
    except KeyboardInterrupt: print('\nОстановлено')
if __name__=='__main__': main()
