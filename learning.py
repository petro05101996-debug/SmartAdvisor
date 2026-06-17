# -*- coding: utf-8 -*-
"""Учебный слой SmartAdvisor.

MVP-цель: превратить rule-based ядро проектирования в тренажёр системного
аналитика: кейс -> решение -> оценка навыков -> разбор ошибок -> эталон.
Модуль не использует LLM и не меняет базовое ядро анализа.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3
import uuid
from typing import Any, Dict, Iterable, List, Tuple

from engine import analyze, humanize_terms, SEVERITY_RU, display_channel
from report import markdown_report

APP_LEARNING_VERSION = "8.6.47-language-polished"
CASE_CATALOG_VERSION = "2026-06-16-v3-language-polished"

SKILLS: Dict[str, str] = {
    "process": "Понимание процесса и декомпозиция",
    "sync_async": "Выбор синхронного и асинхронного взаимодействия",
    "reliability": "Надёжность, повторы, очередь ошибок и восстановление",
    "idempotency": "Идемпотентность, дубли и порядок обработки",
    "contracts": "Контракты и версионирование",
    "data": "Данные, хранилища и проекции",
    "operations": "Эксплуатация, целевое время ответа и наблюдаемость",
    "security": "Безопасность, внешние контуры и ПДн",
}

SEVERITY_PENALTY = {"critical": 2.4, "high": 1.4, "medium": 0.7, "info": 0.25}

# ---------------------------------------------------------------------------
# Набор кейсов MVP. Каждый кейс содержит эталонный payload, чтобы продукт можно
# было демонстрировать без ручного ввода и использовать в regression/progress.
# ---------------------------------------------------------------------------


def _step(order: int, name: str, source: str, system: str, target: str, channel: str,
          *, depends_on: str = "", blocking: str = "no", retry: str = "auto",
          idem: str = "key", timeout: str = "", writes: str = "no", comp: str = "") -> Dict[str, Any]:
    return {
        "order": order,
        "name": name,
        "source_system": source,
        "system": system,
        "target_system": target,
        "channel": channel,
        "depends_on": depends_on,
        "blocking": blocking,
        "retry": retry,
        "idempotency": idem,
        "timeout_ms": timeout,
        "writes_entity": writes,
        "compensation": comp,
    }


def _base_payload(name: str, entity: str, goal: str, systems: List[Tuple[str, str]], steps: List[Dict[str, Any]],
                  *, description: str = "", constraints: str = "", statuses: str = "", fields: str = "",
                  lookup: str = "") -> Dict[str, Any]:
    return {
        "meta": {
            "name": name,
            "entity": entity,
            "goal": goal,
            "description": description,
            "constraints": constraints,
            "rps": "80",
            "peak_multiplier": "3",
            "sla_ms": "2200",
            "visible_to_user": "mixed",
            "money_movement": "yes" if any(x in goal.lower() for x in ("плат", "кредит", "договор")) else "no",
            "regulatory": "yes" if any(x in goal.lower() for x in ("банк", "цб", "бки", "регуля")) else "no",
            "ordering": "per_entity",
            "multi_tenant": "no",
            "legacy": "mixed" if any(role == "legacy" for _, role in systems) else "no",
            "read_pattern": "mixed",
            "lookup_keys": lookup or "entityId + eventId + correlationId; idempotencyKey для команд; partition key по entityId",
            "statuses": statuses or "CREATED, VALIDATED, WAITING_EXTERNAL, APPROVED, REJECTED, SENT, DELIVERED, FAILED, NEEDS_MANUAL_REVIEW",
            "fields": fields or "entityId:string|required|indexed, eventId:uuid|required|unique, correlationId:uuid|required|indexed, idempotencyKey:string|required|unique, status:string|required, statusVersion:int, updatedAt:datetime|required, payloadVersion:int|required",
        },
        "systems": [{"name": n, "role": r} for n, r in systems],
        "steps": steps,
    }

CASES: List[Dict[str, Any]] = [
    {
        "id": "bank-credit-bki-fraud",
        "title": "Банк: кредитная заявка, БКИ, антифрод и аналитика",
        "level": "Middle+",
        "track": "Финтех / интеграции",
        "timebox": "45–60 минут",
        "brief": "Клиент подаёт заявку. Нужно проверить данные, сходить в БКИ и fraud, сохранить решение, опубликовать событие и выгрузить данные в аналитику.",
        "goal": "Построить production-ready цепочку без дублей, потери статусов и нарушения порядка по заявке.",
        "hidden_traps": ["внешние вызовы нельзя бесконечно ретраить", "Kafka требует ключ порядка", "решение и публикация события не должны расходиться", "DWH не должен быть core dependency"],
        "skills": ["sync_async", "reliability", "idempotency", "contracts", "data", "operations"],
        "expected_controls": [
            {"id": "outbox", "label": "Outbox для публикации события после фиксации решения", "keywords": ["outbox", "исходящ"], "skill": "reliability", "why": "иначе решение может сохраниться без события или событие уйдёт без решения"},
            {"id": "kafka_key", "label": "Ключ Kafka по applicationId", "keywords": ["partition", "ключ порядка", "applicationid", "entityid"], "skill": "idempotency", "why": "порядок гарантируется только внутри партиции"},
            {"id": "dlq_replay", "label": "DLQ/quarantine и replay", "keywords": ["dlq", "replay", "карантин", "повторн"], "skill": "reliability", "why": "ошибочные события нужно разбирать и переобрабатывать"},
            {"id": "timeouts", "label": "Таймауты и ограниченные повторы внешних вызовов", "keywords": ["таймаут", "timeout", "rate limit", "огранич"], "skill": "operations", "why": "внешние системы не должны подвешивать клиентский сценарий"},
            {"id": "versioning", "label": "Версия события/контракта", "keywords": ["version", "верси", "schema"], "skill": "contracts", "why": "события живут дольше одного релиза"},
        ],
        "payload": _base_payload(
            "Кредитная заявка с БКИ и fraud", "CreditApplication",
            "Банк принимает заявку, проверяет внешние источники, фиксирует решение и публикует событие для downstream.",
            [("Клиентский канал", "external"), ("Сервис заявок", "internal"), ("БД заявок", "db"), ("БКИ", "external"), ("Fraud-сервис", "external"), ("Kafka", "broker"), ("DWH", "analytics"), ("Audit Log", "analytics")],
            [
                _step(1, "Принять заявку и создать запись", "Клиентский канал", "Сервис заявок", "БД заявок", "api_gateway", blocking="yes", retry="none", timeout="300", writes="yes", comp="idempotencyKey, validation, единая модель ошибок"),
                _step(2, "Запросить кредитную историю", "Сервис заявок", "Сервис заявок", "БКИ", "rest", depends_on="1", blocking="yes", retry="auto", timeout="900", comp="timeout, circuit breaker, ограниченные повторы, сохранение внешнего requestId"),
                _step(3, "Проверить fraud-риск", "Сервис заявок", "Сервис заявок", "Fraud-сервис", "grpc", depends_on="1", blocking="yes", retry="auto", timeout="250", comp="короткий deadline, fallback to manual review"),
                _step(4, "Сохранить решение и outbox", "Сервис заявок", "Сервис заявок", "БД заявок", "db", depends_on="2,3", blocking="yes", retry="auto", timeout="150", writes="yes", comp="transaction, optimistic locking, outbox, statusVersion"),
                _step(5, "Опубликовать событие о решении", "БД заявок", "Сервис заявок", "Kafka", "kafka", depends_on="4", retry="auto", comp="partition key applicationId, event envelope, schemaVersion, DLQ, replay"),
                _step(6, "Передать обезличенную витрину в DWH", "Kafka", "DWH consumer", "DWH", "clickhouse", depends_on="5", retry="auto", comp="consumer group, lag monitoring, reprocess, freshness SLA"),
                _step(7, "Записать аудит решения", "Сервис заявок", "Сервис заявок", "Audit Log", "observability", depends_on="4", retry="auto", comp="immutable audit, correlationId, retention"),
            ],
            constraints="БКИ и fraud могут быть недоступны; решение должно быть трассируемым; ПДн не должны утекать в аналитику.",
            lookup="applicationId + eventId + correlationId; idempotencyKey клиента; partition key applicationId",
        ),
    },
    {
        "id": "uk-bank-status-flow",
        "title": "УК → банк: обратный поток статусов операций",
        "level": "Middle+",
        "track": "Банк / управляющая компания",
        "timebox": "45 минут",
        "brief": "УК сообщает банку статусы операций/документов. Банку нужно подтвердить приём, связать внешний id с внутренним и раздать статус ресурсным системам.",
        "goal": "Спроектировать обратный поток без потери статусов, дублей и разрыва между внешними и внутренними идентификаторами.",
        "hidden_traps": ["нужен mapping externalId → internalId", "ack не равен бизнес-успеху", "один топик на всех потребителей требует контракта", "нужен inbox для повторной обработки"],
        "skills": ["contracts", "idempotency", "reliability", "data", "operations"],
        "expected_controls": [
            {"id": "inbox", "label": "Inbox для входящих статусов", "keywords": ["inbox", "eventid", "дедуп"], "skill": "idempotency", "why": "повторный статус от УК не должен менять состояние дважды"},
            {"id": "mapping", "label": "Таблица соответствия внешнего и внутреннего id", "keywords": ["externalid", "internalid", "mapping", "соответств"], "skill": "data", "why": "без mapping невозможно надёжно связать статус УК с заявкой банка"},
            {"id": "status_model", "label": "Статусная модель и unknown/manual review", "keywords": ["unknown", "workflow_engine", "неизвест", "status"], "skill": "process", "why": "новые или спорные статусы нельзя молча терять"},
            {"id": "contract_owner", "label": "Владелец и версия контракта события", "keywords": ["version", "schema", "контракт", "владел"], "skill": "contracts", "why": "топик для нескольких систем требует управляемой эволюции"},
        ],
        "payload": _base_payload(
            "Обратный поток статусов УК", "FundOperationStatus",
            "Получать статусы операций от управляющей компании, связывать их с внутренними заявками банка и публиковать для ресурсных систем.",
            [("УК", "external"), ("Сервис приёма статусов", "internal"), ("БД статусов", "db"), ("Kafka", "broker"), ("Ресурсные системы", "internal"), ("Ручной разбор", "workflow_engine")],
            [
                _step(1, "Принять статус от УК", "УК", "Сервис приёма статусов", "БД статусов", "webhook", blocking="no", retry="auto", writes="yes", comp="signature, inbox, UNIQUE eventId, externalOperationId, correlationId"),
                _step(2, "Сопоставить внешний и внутренний идентификатор", "Сервис приёма статусов", "Сервис приёма статусов", "БД статусов", "db", depends_on="1", blocking="yes", retry="auto", writes="yes", comp="externalId/internalId mapping, unknown -> manual review"),
                _step(3, "Подтвердить технический приём", "Сервис приёма статусов", "Сервис приёма статусов", "УК", "callback", depends_on="1", blocking="no", retry="auto", comp="ack не означает бизнес-успех, signed response, retry window"),
                _step(4, "Опубликовать нормализованный статус", "БД статусов", "Сервис приёма статусов", "Kafka", "kafka", depends_on="2", retry="auto", comp="operationId partition key, schemaVersion, DLQ, replay"),
                _step(5, "Обновить ресурсные системы", "Kafka", "Consumer ресурсных систем", "Ресурсные системы", "kafka", depends_on="4", retry="auto", comp="consumer group, idempotent update, lag monitoring"),
                _step(6, "Отправить спорные статусы в ручной разбор", "Сервис приёма статусов", "Сервис приёма статусов", "Ручной разбор", "workflow_engine", depends_on="2", retry="workflow_engine", comp="reason code, SLA manual review, audit"),
            ],
            constraints="УК может присылать дубли и статусы не по порядку; банк должен сохранить исходное тело события для разбора.",
            lookup="externalOperationId + internalOperationId + eventId + correlationId; partition key internalOperationId",
        ),
    },
    {
        "id": "event-enrichment-rest-kafka",
        "title": "Kafka + REST enrichment: кто должен обогащать событие",
        "level": "Middle",
        "track": "Enterprise integration",
        "timebox": "35 минут",
        "brief": "Исходный сервис публикует событие, но части данных нет. Нужно решить: обогащать до публикации, в consumer или отдельным enrichment service.",
        "goal": "Выбрать компромиссную архитектуру с явным владельцем данных, таймаутами, кэшем и политикой деградации.",
        "hidden_traps": ["REST в async handler может заблокировать поток", "обогащение у каждого consumer плодит связанность", "нужен cache/fallback", "нужно определить владельца контракта"],
        "skills": ["sync_async", "reliability", "contracts", "data"],
        "expected_controls": [
            {"id": "owner", "label": "Владелец данных и контракта", "keywords": ["owner", "владел", "контракт"], "skill": "contracts", "why": "иначе потребители начнут угадывать смысл полей"},
            {"id": "cache", "label": "Кэш/проекция для enrichment", "keywords": ["cache", "кэш", "projection", "read model"], "skill": "data", "why": "REST на каждое событие может стать узким местом"},
            {"id": "fallback", "label": "Fallback/manual review при недоступности enrichment", "keywords": ["fallback", "workflow_engine", "degrad", "ручн"], "skill": "reliability", "why": "события не должны бесконечно зависать"},
        ],
        "payload": _base_payload(
            "Обогащение событий через REST", "ContractChangedEvent",
            "Передать изменения договора через Kafka и дообогатить событие данными из справочного сервиса без блокировки основного контура.",
            [("Сервис договоров", "internal"), ("БД договоров", "db"), ("Kafka", "broker"), ("Enrichment service", "internal"), ("Справочный сервис", "internal"), ("Кэш справочника", "cache"), ("Потребители", "internal")],
            [
                _step(1, "Сохранить изменение договора и outbox", "Сервис договоров", "Сервис договоров", "БД договоров", "db", blocking="yes", writes="yes", comp="transaction, outbox, contractId, version"),
                _step(2, "Опубликовать базовое событие", "БД договоров", "Сервис договоров", "Kafka", "kafka", depends_on="1", comp="partition key contractId, schemaVersion, DLQ/replay"),
                _step(3, "Обогатить событие в отдельном сервисе", "Kafka", "Enrichment service", "Кэш справочника", "kafka", depends_on="2", comp="consumer group, idempotent processing, fallback if enrichment stale"),
                _step(4, "Обновить кэш справочника", "Справочный сервис", "Enrichment service", "Кэш справочника", "rest", blocking="yes", retry="auto", timeout="300", comp="timeout, circuit breaker, TTL, stale-read policy"),
                _step(5, "Опубликовать обогащённое событие", "Enrichment service", "Enrichment service", "Kafka", "kafka", depends_on="3,4", comp="enriched schemaVersion, owner, DLQ, replay"),
                _step(6, "Обработать событие потребителями", "Kafka", "Consumer", "Потребители", "kafka", depends_on="5", comp="consumer group, idempotency, lag alert"),
            ],
            constraints="Нельзя делать тяжёлый REST-вызов в каждом downstream consumer; справочник может быть временно недоступен.",
            lookup="contractId + eventId + enrichmentVersion + correlationId",
        ),
    },
    {
        "id": "fanin-partial-failure-order",
        "title": "Fan-in: несколько внешних проверок и частичный отказ",
        "level": "Middle+",
        "track": "Fault tolerance",
        "timebox": "40 минут",
        "brief": "Процесс ждёт результаты KYC, скоринга и антифрода. Один сервис может не ответить. Нужно решить, когда можно продолжать, когда нужна ручная проверка.",
        "goal": "Описать fan-in с timeout budget, partial response policy, fallback и статусной моделью.",
        "hidden_traps": ["нельзя ждать бесконечно", "частичный ответ должен быть формализован", "join требует статусов ожидания", "manual review не равен fail"],
        "skills": ["process", "sync_async", "reliability", "operations"],
        "expected_controls": [
            {"id": "partial_policy", "label": "Политика частичного ответа", "keywords": ["partial", "частич", "fallback", "workflow_engine"], "skill": "process", "why": "иначе команда не знает, можно ли продолжать при одном сбое"},
            {"id": "timeout_budget", "label": "Общий бюджет времени", "keywords": ["timeout", "deadline", "budget", "таймаут"], "skill": "operations", "why": "параллельные вызовы всё равно должны укладываться в SLA"},
            {"id": "statuses", "label": "WAITING/NEEDS_MANUAL_REVIEW статусы", "keywords": ["waiting", "workflow_engine", "review"], "skill": "process", "why": "длинный процесс должен быть наблюдаемым"},
        ],
        "payload": _base_payload(
            "Fan-in внешних проверок", "ApplicantCheck",
            "Собрать результаты нескольких проверок и принять решение с учётом частичной недоступности.",
            [("Канал продаж", "external"), ("Сервис проверок", "internal"), ("БД проверок", "db"), ("KYC", "external"), ("Скоринг", "external"), ("Антифрод", "external"), ("Ручной разбор", "workflow_engine")],
            [
                _step(1, "Создать проверку", "Канал продаж", "Сервис проверок", "БД проверок", "rest", blocking="yes", timeout="300", writes="yes", comp="idempotencyKey, status WAITING_CHECKS"),
                _step(2, "Запросить KYC", "Сервис проверок", "Сервис проверок", "KYC", "rest", depends_on="1", blocking="yes", timeout="700", comp="timeout, fallback to manual review"),
                _step(3, "Запросить скоринг", "Сервис проверок", "Сервис проверок", "Скоринг", "grpc", depends_on="1", blocking="yes", timeout="400", comp="deadline, limited retry"),
                _step(4, "Запросить антифрод", "Сервис проверок", "Сервис проверок", "Антифрод", "rest", depends_on="1", blocking="yes", timeout="500", comp="rate limit, circuit breaker"),
                _step(5, "Собрать результаты и применить partial response policy", "Сервис проверок", "Сервис проверок", "БД проверок", "db", depends_on="2,3,4", blocking="yes", writes="yes", comp="partial response policy, statusVersion, timeout budget, manual review for missing critical check"),
                _step(6, "Передать спорные заявки в ручной разбор", "Сервис проверок", "Сервис проверок", "Ручной разбор", "workflow_engine", depends_on="5", retry="workflow_engine", comp="reason codes, SLA, audit"),
            ],
        ),
    },
    {
        "id": "bki-dwh-search-batch",
        "title": "БКИ → DWH → поиск: batch, качество и переобработка",
        "level": "Middle",
        "track": "Data / DWH",
        "timebox": "35 минут",
        "brief": "Раз в день банк получает большой объём данных, складывает в DWH и строит поиск/витрину. Нужно обеспечить контроль качества и повторную обработку.",
        "goal": "Разделить ingestion, quality gate, DWH, search projection и operational monitoring.",
        "hidden_traps": ["batch нужен checksum и quarantine", "DWH не должен быть источником оперативного состояния", "поиск требует переиндексации", "нужен freshness SLA"],
        "skills": ["data", "operations", "reliability"],
        "expected_controls": [
            {"id": "quality", "label": "Quality gate/checksum/quarantine", "keywords": ["checksum", "quality", "quarantine", "карантин"], "skill": "data", "why": "плохой пакет нельзя молча загружать в витрину"},
            {"id": "reprocess", "label": "Reprocess и audit загрузок", "keywords": ["reprocess", "повторн", "audit", "batchid"], "skill": "reliability", "why": "ежедневную загрузку нужно уметь восстановить"},
            {"id": "freshness", "label": "Freshness SLA и lag monitoring", "keywords": ["freshness", "lag", "sla", "отстав"], "skill": "operations", "why": "потребители должны понимать актуальность данных"},
        ],
        "payload": _base_payload(
            "Ежедневная загрузка БКИ", "CreditHistorySnapshot",
            "Получать ежедневный файл БКИ, проверять качество, загружать в DWH и обновлять поисковую проекцию.",
            [("БКИ", "external"), ("Ingestion service", "internal"), ("Object Storage", "analytics"), ("DWH", "analytics"), ("Search", "analytics"), ("Audit Log", "analytics")],
            [
                _step(1, "Забрать ежедневный файл", "БКИ", "Ingestion service", "Object Storage", "sftp", retry="workflow_engine", comp="batchId, checksum, immutable raw zone"),
                _step(2, "Проверить качество пакета", "Ingestion service", "Ingestion service", "Audit Log", "observability", depends_on="1", comp="schema validation, quarantine, reject report"),
                _step(3, "Загрузить очищенные данные в DWH", "Object Storage", "Ingestion service", "DWH", "clickhouse", depends_on="2", comp="idempotent load by batchId, partition, reprocess"),
                _step(4, "Обновить поисковую проекцию", "DWH", "Ingestion service", "Search", "search", depends_on="3", comp="reindex, freshness SLA, lag monitoring"),
                _step(5, "Записать журнал загрузки", "Ingestion service", "Ingestion service", "Audit Log", "observability", depends_on="3,4", comp="load status, row counts, data quality metrics, alerting"),
            ],
            constraints="Пакет большой; данные используются для аналитики и поиска, не для синхронного клиентского ответа.",
            lookup="batchId + fileHash + sourceDate + correlationId",
        ),
    },
    {
        "id": "contract-evolution-expand-contract",
        "title": "Регуляторное изменение: у кредита несколько целей займа",
        "level": "Middle+",
        "track": "Contract evolution",
        "timebox": "50 минут",
        "brief": "Раньше у кредита была одна цель займа, теперь регулятор требует несколько. Нужно изменить модель данных, API, события и миграцию без остановки потребителей.",
        "goal": "Применить expand/contract, версионирование контракта, миграцию данных и обратную совместимость.",
        "hidden_traps": ["нельзя одномоментно заменить scalar на array", "старые потребители могут читать старое поле", "нужен период совместимости", "нужны data migration и monitoring"],
        "skills": ["contracts", "data", "operations", "process"],
        "expected_controls": [
            {"id": "expand_contract", "label": "Expand/Contract migration", "keywords": ["expand", "contract", "dual", "совместим"], "skill": "contracts", "why": "потребители должны пережить миграцию без простоя"},
            {"id": "data_migration", "label": "Миграция данных и backfill", "keywords": ["migration", "backfill", "миграц"], "skill": "data", "why": "старые записи надо привести к новой модели"},
            {"id": "versioning", "label": "Версия API/события", "keywords": ["version", "v2", "schema"], "skill": "contracts", "why": "контракт должен явно отражать новую структуру"},
        ],
        "payload": _base_payload(
            "Несколько целей займа", "LoanPurpose",
            "Изменить модель кредита с одной цели займа на несколько целей без поломки API, событий и аналитики.",
            [("Кредитный UI", "external"), ("Кредитный сервис", "internal"), ("БД кредитов", "db"), ("Kafka", "broker"), ("DWH", "analytics"), ("Старые потребители", "legacy")],
            [
                _step(1, "Принять новую структуру целей через API v2", "Кредитный UI", "Кредитный сервис", "БД кредитов", "rest", blocking="yes", retry="none", writes="yes", comp="backward compatibility, validation, old purpose field preserved during expand"),
                _step(2, "Сохранить новую таблицу целей займа", "Кредитный сервис", "Кредитный сервис", "БД кредитов", "db", depends_on="1", writes="yes", comp="expand phase, loan_purpose_items, migration, backfill"),
                _step(3, "Опубликовать событие v2", "БД кредитов", "Кредитный сервис", "Kafka", "kafka", depends_on="2", comp="schemaVersion, old+new fields during compatibility window, partition key loanId, DLQ/replay"),
                _step(4, "Поддержать старых потребителей", "Kafka", "Compatibility consumer", "Старые потребители", "kafka", depends_on="3", comp="adapter, deprecation date, consumer readiness tracking"),
                _step(5, "Обновить аналитику", "Kafka", "DWH consumer", "DWH", "clickhouse", depends_on="3", comp="new dimension, backfill, data quality checks"),
            ],
            constraints="Нельзя останавливать старых потребителей; нужен период совместимости и план удаления старого поля.",
            lookup="loanId + eventId + schemaVersion + migrationBatchId",
            fields="loanId:string|required|indexed, primaryPurpose:string|deprecated, purposes:array|required, purposeCode:string, purposeShare:decimal, schemaVersion:int|required, eventId:uuid|required|unique",
        ),
    },
]

# Добавим ещё короткие кейсы, чтобы MVP выглядел как библиотека, а не демо из 6 карточек.
SHORT_CASES = [
    ("webhook-dedup-signature", "Webhook от партнёра: подпись, дубли и окно времени", "Junior+", "Security / callbacks"),
    ("rabbitmq-task-queue", "RabbitMQ task queue: DLX, ack и prefetch", "Middle", "Async tasks"),
    ("saga-payment-reservation", "Saga: заказ, оплата, резерв склада и компенсации", "Middle+", "Distributed transactions"),
    ("redis-cache-hot-read", "Hot read: кэш, TTL и защита от лавины запросов", "Junior+", "Performance"),
    ("legacy-soap-adapter", "Legacy SOAP adapter: fault model и трансформация", "Middle", "Legacy integration"),
    ("multi-consumer-event-contract", "Один топик — много потребителей: contract ownership", "Middle+", "Event-driven architecture"),
    ("callback-status-polling", "Callback или polling: статусы внешнего провайдера", "Middle", "External integration"),
    ("file-exchange-sftp", "SFTP-файлы: checksum, идемпотентная загрузка и quarantine", "Middle", "Batch / files"),
    ("grpc-low-latency", "gRPC-вызов с deadline, fallback и circuit breaker", "Middle", "Synchronous integration"),
    ("websocket-notifications", "WebSocket-уведомления: fan-out, reconnect и delivery status", "Middle+", "Realtime"),
    ("event-sourcing-read-model", "Event sourcing: read model, replay и snapshot", "Senior", "Architecture patterns"),
    ("cdc-outbox-debezium", "CDC/outbox через Debezium: ordering и schema evolution", "Middle+", "CDC / Kafka"),
    ("pii-tokenization-analytics", "ПДн в аналитике: tokenization, masking и retention", "Middle+", "Security / data"),
    ("multi-tenant-isolation", "Multi-tenant интеграция: изоляция tenantId и лимиты", "Senior", "Enterprise"),
    ("partner-rate-limit-bulkhead", "Внешний партнёр с rate limit: bulkhead, queue и backpressure", "Middle+", "Resilience"),
    ("manual-review-workflow", "Manual review: workflow engine, SLA и возврат в основной поток", "Middle", "Workflow"),
    ("payment-reconciliation", "Платёжная сверка: ledger, reconciliation и расхождения", "Senior", "Payments"),
    ("schema-registry-governance", "Schema Registry: совместимость событий и governance", "Middle+", "Contract governance"),
]

for idx, (cid, title, level, track) in enumerate(SHORT_CASES, start=1):
    CASES.append({
        "id": cid,
        "title": title,
        "level": level,
        "track": track,
        "timebox": "25–40 минут",
        "brief": "Короткий учебный кейс для закрепления отдельного архитектурного навыка.",
        "goal": "Построить минимально безопасное решение и явно указать контроли готовности к промышленному запуску.",
        "hidden_traps": ["не забыть идемпотентность и сквозной идентификатор", "описать отказ и повторную обработку", "зафиксировать владельца контракта"],
        "skills": ["reliability", "idempotency", "contracts", "operations"],
        "expected_controls": [
            {"id": "idem", "label": "Идемпотентность и дедупликация", "keywords": ["idempot", "дедуп", "unique", "eventid"], "skill": "idempotency", "why": "повторные сообщения не должны портить состояние"},
            {"id": "correlation", "label": "Сквозной идентификатор и трассировка", "keywords": ["correlation", "trace", "трасс"], "skill": "operations", "why": "без трассировки трудно разбирать инциденты"},
            {"id": "dlq", "label": "Очередь ошибок, карантин и ручной разбор", "keywords": ["dlq", "quarantine", "workflow_engine", "карантин"], "skill": "reliability", "why": "ошибки должны быть управляемыми"},
        ],
        "payload": _base_payload(
            title, "TrainingEntity", "Учебный кейс: " + title,
            [("Инициатор", "external"), ("Сервис процесса", "internal"), ("БД процесса", "db"), ("Внешняя система", "external"), ("Kafka", "broker"), ("Audit Log", "analytics")],
            [
                _step(1, "Принять запрос и сохранить состояние", "Инициатор", "Сервис процесса", "БД процесса", "rest", blocking="yes", timeout="300", writes="yes", comp="idempotencyKey, validation, correlationId"),
                _step(2, "Вызвать внешнюю систему", "Сервис процесса", "Сервис процесса", "Внешняя система", "rest", depends_on="1", blocking="yes", timeout="700", comp="timeout, limited retry, fallback/manual review"),
                _step(3, "Опубликовать событие результата", "БД процесса", "Сервис процесса", "Kafka", "kafka", depends_on="2", comp="eventId, schemaVersion, partition key, DLQ/replay"),
                _step(4, "Записать аудит", "Сервис процесса", "Сервис процесса", "Audit Log", "observability", depends_on="3", comp="correlationId, immutable audit, retention"),
            ],
        ),
    })


# ---------------------------------------------------------------------------
# Расширенная библиотека практики v8.6.46.
# Цель: не раздувать продукт случайными карточками, а закрыть максимум
# повторяемых enterprise-сценариев: банки, платежи, телеком, e-commerce,
# DWH, realtime, security, legacy, broker-specific и data-heavy практику.
# ---------------------------------------------------------------------------

def _controls_for_pattern(pattern: str) -> List[Dict[str, Any]]:
    common = [
        {"id": "idempotency", "label": "Идемпотентность и дедупликация", "keywords": ["idempotencykey", "idempot", "eventid", "dedup", "unique"], "skill": "idempotency", "why": "повторный запрос/событие не должен портить состояние"},
        {"id": "traceability", "label": "Сквозной идентификатор и трассировка", "keywords": ["correlationid", "trace", "трасс"], "skill": "operations", "why": "без трассировки инциденты трудно расследовать"},
        {"id": "contract_version", "label": "Версия контракта и версия схемы", "keywords": ["schemaversion", "version", "контракт"], "skill": "contracts", "why": "контракт должен переживать изменения без поломки потребителей"},
    ]
    extra = {
        "event": [
            {"id": "outbox", "label": "Outbox и публикация после фиксации состояния", "keywords": ["outbox", "исходящ", "transaction"], "skill": "reliability", "why": "состояние и событие не должны расходиться"},
            {"id": "partition_key", "label": "Ключ порядка по entityId", "keywords": ["partition key", "ключ порядка", "entityid"], "skill": "idempotency", "why": "порядок событий гарантируется только в рамках ключа/партиции"},
            {"id": "dlq_replay", "label": "Очередь ошибок и повторная обработка", "keywords": ["dlq", "replay", "quarantine"], "skill": "reliability", "why": "ошибочные сообщения нужно уметь переобрабатывать"},
        ],
        "sync": [
            {"id": "timeout", "label": "Таймаут, предельный срок ожидания и предохранитель", "keywords": ["timeout", "deadline", "circuit breaker"], "skill": "operations", "why": "внешняя зависимость не должна подвешивать основной поток"},
            {"id": "fallback", "label": "Запасной сценарий и ручной разбор", "keywords": ["fallback", "manual review", "workflow_engine"], "skill": "reliability", "why": "при недоступности провайдера процесс должен деградировать управляемо"},
            {"id": "rate_limit", "label": "Лимит запросов и изоляция ресурса", "keywords": ["rate limit", "bulkhead", "лимит"], "skill": "operations", "why": "партнёрские лимиты нужно изолировать от всего сервиса"},
        ],
        "batch": [
            {"id": "checksum", "label": "Контрольная сумма и проверка качества", "keywords": ["checksum", "quality", "schema validation"], "skill": "data", "why": "плохой пакет нельзя молча загружать дальше"},
            {"id": "quarantine", "label": "Карантин и отчёт об отклонении", "keywords": ["quarantine", "reject", "карантин"], "skill": "reliability", "why": "ошибочный файл должен попадать в управляемый разбор"},
            {"id": "freshness", "label": "Соглашение о свежести данных и переобработка", "keywords": ["freshness", "reprocess", "batchid"], "skill": "operations", "why": "потребители должны понимать актуальность витрины"},
        ],
        "realtime": [
            {"id": "delivery", "label": "Статус доставки и переподключение", "keywords": ["delivery", "reconnect", "ack"], "skill": "reliability", "why": "онлайн-канал ненадёжен без подтверждений и восстановления"},
            {"id": "fanout", "label": "Рассылка и обратное давление", "keywords": ["fan-out", "backpressure", "lag"], "skill": "operations", "why": "массовые уведомления могут перегрузить потребителей"},
            {"id": "state", "label": "Состояние подписки/сессии", "keywords": ["session", "subscription", "state"], "skill": "data", "why": "нужно знать, кому и что доставлено"},
        ],
        "security": [
            {"id": "auth", "label": "OIDC, API Gateway и авторизация", "keywords": ["oidc", "auth", "authorization", "gateway"], "skill": "security", "why": "границы доступа должны быть явными"},
            {"id": "secrets", "label": "Vault/KMS и ротация секретов", "keywords": ["vault", "kms", "secret", "rotation"], "skill": "security", "why": "секреты нельзя хранить в коде и логах"},
            {"id": "audit", "label": "Аудит, срок хранения и маскирование", "keywords": ["audit", "retention", "masking", "пдн"], "skill": "security", "why": "действия с чувствительными данными должны быть проверяемыми"},
        ],
    }.get(pattern, [])
    return common + extra


def _practice_payload(title: str, entity: str, pattern: str, channel: str, target: str, *, level: str) -> Dict[str, Any]:
    if pattern == "event":
        broker = "Kafka" if channel in ("kafka", "pulsar", "nats") else "Message Broker"
        return _base_payload(
            title, entity, "Учебный event-driven кейс: зафиксировать состояние, опубликовать событие и обработать downstream без потери порядка.",
            [("Инициатор", "external"), ("Core service", "internal"), ("Core DB", "db"), (broker, "broker"), (target, "internal"), ("DWH", "analytics"), ("Audit Log", "analytics")],
            [
                _step(1, "Принять команду и сохранить состояние", "Инициатор", "Core service", "Core DB", "rest", blocking="yes", timeout="300", writes="yes", comp="idempotencyKey, validation, correlationId"),
                _step(2, "Зафиксировать outbox-событие", "Core service", "Core service", "Core DB", "db", depends_on="1", writes="yes", comp="transaction, outbox, schemaVersion, entityId"),
                _step(3, "Опубликовать доменное событие", "Core DB", "Core service", broker, channel, depends_on="2", comp="eventId, schemaVersion, partition key entityId, DLQ/replay"),
                _step(4, "Обработать событие потребителем", broker, "Consumer", target, channel, depends_on="3", comp="consumer group, inbox/dedup, idempotent handler, lag alert"),
                _step(5, "Обновить аналитическую витрину", broker, "DWH consumer", "DWH", "clickhouse", depends_on="3", comp="freshness SLA, reprocess, data quality"),
                _step(6, "Записать аудит", "Core service", "Core service", "Audit Log", "observability", depends_on="2", comp="correlationId, immutable audit, retention"),
            ],
            constraints="Нужны управляемые повторы, порядок по сущности и безопасная эволюция события.",
        )
    if pattern == "batch":
        return _base_payload(
            title, entity, "Учебный batch/data кейс: принять пакет, проверить качество, загрузить витрину и обеспечить переобработку.",
            [("Источник файла", "external"), ("Ingestion service", "internal"), ("Raw storage", "analytics"), ("DWH", "analytics"), (target, "analytics"), ("Audit Log", "analytics")],
            [
                _step(1, "Получить пакет данных", "Источник файла", "Ingestion service", "Raw storage", channel, retry="workflow_engine", comp="batchId, checksum, immutable raw zone, correlationId"),
                _step(2, "Проверить качество и схему", "Ingestion service", "Ingestion service", "Audit Log", "observability", depends_on="1", comp="schema validation, reject report, quarantine"),
                _step(3, "Загрузить очищенные данные", "Raw storage", "Ingestion service", "DWH", "clickhouse", depends_on="2", comp="idempotent load by batchId, partition, reprocess"),
                _step(4, "Обновить потребительскую проекцию", "DWH", "Ingestion service", target, "search" if "поиск" in target.lower() or "search" in target.lower() else "dbt", depends_on="3", comp="freshness SLA, lineage, data quality metrics"),
                _step(5, "Сохранить аудит загрузки", "Ingestion service", "Ingestion service", "Audit Log", "observability", depends_on="3,4", comp="row counts, checksum, alerts, retention"),
            ],
            constraints="Данные большие; нужна воспроизводимость загрузки и понятная актуальность витрины.",
        )
    if pattern == "realtime":
        return _base_payload(
            title, entity, "Учебный realtime кейс: доставить онлайн-события пользователям/устройствам с контролем доставки.",
            [("Источник события", "external"), ("Realtime service", "internal"), ("Session store", "cache"), ("Event Broker", "broker"), (target, "external"), ("Audit Log", "analytics")],
            [
                _step(1, "Принять событие", "Источник события", "Realtime service", "Event Broker", "kafka" if channel in ("websocket", "sse") else channel, blocking="no", comp="eventId, schemaVersion, partition key userId, DLQ/replay"),
                _step(2, "Обновить состояние подписки", "Realtime service", "Realtime service", "Session store", "redis_cache", depends_on="1", writes="yes", comp="session state, TTL, reconnect token"),
                _step(3, "Доставить уведомление", "Event Broker", "Realtime service", target, channel, depends_on="1,2", comp="delivery status, ack, reconnect, backpressure"),
                _step(4, "Записать аудит доставки", "Realtime service", "Realtime service", "Audit Log", "observability", depends_on="3", comp="correlationId, delivery metrics, lag alert"),
            ],
            constraints="Клиенты могут отваливаться; нужна деградация и наблюдаемость доставки.",
        )
    if pattern == "security":
        return _base_payload(
            title, entity, "Учебный security/API кейс: защитить доступ, секреты, аудит и работу с чувствительными данными.",
            [("Клиент/партнёр", "external"), ("API Gateway", "internal"), ("Auth service", "internal"), ("Protected service", "internal"), ("Vault/KMS", "internal"), ("Protected DB", "db"), ("Audit Log", "analytics")],
            [
                _step(1, "Принять внешний запрос", "Клиент/партнёр", "API Gateway", "Protected service", "api_gateway", blocking="yes", timeout="200", comp="OIDC/JWT validation, rate limit, correlationId"),
                _step(2, "Проверить авторизацию", "API Gateway", "Auth service", "Protected service", "auth_oidc", depends_on="1", blocking="yes", timeout="150", comp="scopes, tenantId, policy decision"),
                _step(3, "Получить секрет/ключ", "Protected service", "Protected service", "Vault/KMS", "vault", depends_on="2", blocking="yes", timeout="120", comp="secret rotation, least privilege, no secrets in logs"),
                _step(4, "Выполнить операцию с данными", "Protected service", "Protected service", "Protected DB", "db", depends_on="3", writes="yes", comp="masking, retention, audit fields, idempotencyKey"),
                _step(5, "Записать аудит доступа", "Protected service", "Protected service", "Audit Log", "observability", depends_on="4", comp="immutable audit, retention, ПДн masking, correlationId"),
            ],
            constraints="Нужно исключить утечку чувствительных данных и обеспечить расследуемость действий.",
        )
    # sync/external dependency
    return _base_payload(
        title, entity, "Учебный sync/API кейс: вызвать внешнюю зависимость без зависания основного процесса и без дублей.",
        [("Инициатор", "external"), ("Process service", "internal"), ("Process DB", "db"), (target, "external"), ("Workflow", "workflow_engine"), ("Audit Log", "analytics")],
        [
            _step(1, "Принять запрос и сохранить состояние", "Инициатор", "Process service", "Process DB", "rest", blocking="yes", timeout="300", writes="yes", comp="idempotencyKey, validation, correlationId"),
            _step(2, "Вызвать внешнюю зависимость", "Process service", "Process service", target, channel, depends_on="1", blocking="yes", timeout="500", comp="timeout, deadline, circuit breaker, rate limit, limited retry"),
            _step(3, "Сохранить результат или статус ожидания", "Process service", "Process service", "Process DB", "db", depends_on="2", writes="yes", comp="statusVersion, fallback/manual review, optimistic lock"),
            _step(4, "Передать спорные случаи в workflow", "Process service", "Process service", "Workflow", "workflow_engine", depends_on="3", comp="manual review SLA, reason codes, compensation"),
            _step(5, "Записать аудит", "Process service", "Process service", "Audit Log", "observability", depends_on="3,4", comp="correlationId, immutable audit, retention"),
        ],
        constraints="Внешний провайдер может тормозить, возвращать дубли и менять контракт.",
    )


EXTENDED_PRACTICE_CASES = [
    ("card-authorization-clearing", "Карточная авторизация и клиринг: online + batch reconciliation", "Senior", "Payments", "event", "kafka", "Clearing consumer", "CardTransaction"),
    ("aml-screening-case", "AML screening: проверка клиента и ручной комплаенс-разбор", "Middle+", "Compliance", "sync", "rest", "AML Provider", "AmlCase"),
    ("kyc-refresh-expiry", "KYC refresh: истечение документов, уведомления и блокировка операций", "Middle+", "Banking", "event", "kafka", "KYC consumer", "KycProfile"),
    ("mortgage-document-package", "Ипотека: пакет документов, статусы, архив и недостающие файлы", "Middle+", "Document flow", "batch", "object_storage", "Документный архив", "MortgageDocument"),
    ("insurance-claim-partners", "Страховая выплата: партнёры, документы, fraud и компенсации", "Senior", "Insurance", "event", "kafka", "Claim settlement", "InsuranceClaim"),
    ("broker-order-status", "Брокерская заявка: статусы исполнения и сверка с биржей", "Senior", "Brokerage", "event", "kafka", "Order status consumer", "BrokerOrder"),
    ("deposit-opening-remote", "Удалённое открытие вклада: KYC, договор, уведомление", "Middle", "Banking", "sync", "rest", "KYC Provider", "DepositContract"),
    ("loan-restructuring-workflow", "Реструктуризация кредита: workflow, документы и статусы", "Middle+", "Banking", "sync", "rest", "Document service", "LoanRestructure"),
    ("chargeback-dispute-flow", "Chargeback dispute: спорная операция, сроки и доказательства", "Senior", "Payments", "event", "kafka", "Dispute consumer", "Chargeback"),
    ("loyalty-bonus-ledger", "Бонусная программа: начисление, списание и ledger", "Middle+", "Ledger", "event", "kafka", "Bonus ledger", "BonusOperation"),

    ("ecom-order-fulfillment", "E-commerce заказ: оплата, склад, доставка и уведомления", "Middle+", "E-commerce", "event", "kafka", "Fulfillment consumer", "Order"),
    ("returns-refund-saga", "Возврат товара: refund, склад и компенсации", "Middle+", "E-commerce", "event", "rabbitmq", "Refund worker", "ReturnRequest"),
    ("inventory-reservation-oversell", "Резерв остатков: защита от oversell и дедуп команд", "Middle+", "Inventory", "sync", "grpc", "Inventory service", "InventoryReservation"),
    ("promo-price-recalculation", "Промо-цены: массовый пересчёт и кеширование чтения", "Middle", "Retail", "batch", "airflow", "Price Search", "PromoPrice"),
    ("delivery-slot-booking", "Бронирование слота доставки: внешний лимит и отмены", "Middle", "Logistics", "sync", "rest", "Delivery Provider", "DeliverySlot"),
    ("marketplace-seller-feed", "Фид продавца: SFTP, валидация и публикация карточек", "Middle", "Marketplace", "batch", "sftp", "Product Search", "SellerFeed"),
    ("catalog-search-index", "Каталог: обновление поискового индекса и переиндексация", "Middle", "Search", "event", "kafka", "Search Indexer", "CatalogItem"),
    ("warehouse-wms-integration", "Интеграция WMS: очереди задач, ack и повторная отправка", "Middle", "Warehouse", "event", "rabbitmq", "WMS adapter", "WarehouseTask"),

    ("telecom-cdr-billing", "Телеком CDR: поток событий, биллинг и batch-сверка", "Senior", "Telecom", "event", "pulsar", "Billing consumer", "CallDetailRecord"),
    ("sim-provisioning-flow", "Provisioning SIM/eSIM: внешние статусы и callback", "Middle+", "Telecom", "sync", "rest", "Provisioning Platform", "SimActivation"),
    ("iot-mqtt-alarms", "IoT тревоги: MQTT, дедуп, окно времени и ClickHouse", "Middle+", "IoT", "realtime", "mqtt", "Device clients", "DeviceAlarm"),
    ("smart-meter-data-lake", "Smart meter: телеметрия, data lake и качество данных", "Middle", "IoT / Data", "batch", "data_lake", "Analytics Mart", "MeterReading"),
    ("gaming-matchmaking-events", "Gaming matchmaking: realtime-события и backpressure", "Middle+", "Realtime", "realtime", "websocket", "Game clients", "MatchEvent"),
    ("support-chat-sse", "Support chat: SSE/WebSocket, reconnect и история сообщений", "Middle", "Realtime", "realtime", "sse", "Agent UI", "ChatMessage"),

    ("hr-onboarding-bpm", "HR onboarding: BPMN, ручные задачи и SLA", "Middle", "Workflow", "sync", "rest", "HR System", "OnboardingCase"),
    ("erp-master-data-odata", "ERP master data: OData, справочники и кэш", "Middle", "ERP", "sync", "odata", "ERP", "MasterDataRecord"),
    ("sap-soap-adapter", "SAP SOAP adapter: fault model, mapping и ретраи", "Middle", "Legacy / SAP", "sync", "soap", "SAP", "SapDocument"),
    ("esb-strangler-migration", "Strangler migration через ESB: старый и новый контур", "Senior", "Migration", "sync", "esb", "Legacy Core", "LegacyProcess"),
    ("mainframe-ibm-mq", "Mainframe + IBM MQ: гарантированная доставка и корреляция", "Senior", "Mainframe", "event", "ibm_mq", "Mainframe Adapter", "MainframeMessage"),
    ("active-mq-legacy-queue", "ActiveMQ legacy queue: poison messages и DLQ", "Middle", "Legacy queues", "event", "activemq", "Legacy Consumer", "LegacyTask"),

    ("cdc-read-model-postgres", "CDC из Postgres: read model и порядок изменений", "Middle+", "CDC", "event", "kafka", "Read model consumer", "DbChange"),
    ("debezium-schema-migration", "Debezium + schema migration: совместимость и backfill", "Middle+", "CDC / Schema", "event", "kafka", "Debezium consumer", "SchemaChange"),
    ("data-quality-lakehouse", "Lakehouse: quality gate, lineage и reprocess", "Middle+", "Data platform", "batch", "lakehouse", "BI Mart", "LakehouseDataset"),
    ("spark-large-transform", "Spark: большая трансформация, retry и идемпотентность партиций", "Middle", "Big Data", "batch", "spark", "Feature Store", "SparkJob"),
    ("dbt-mart-contracts", "dbt marts: контракт витрины и freshness SLA", "Middle", "Analytics Engineering", "batch", "dbt", "BI Dashboard", "AnalyticsMart"),
    ("airflow-dag-dependencies", "Airflow DAG: зависимости, rerun и quarantine", "Middle", "Orchestration", "batch", "airflow", "DWH", "DagRun"),
    ("object-storage-archive", "Object Storage архив: lifecycle, checksum и поиск", "Middle", "Storage", "batch", "object_storage", "Archive Index", "ArchivedObject"),
    ("vector-db-rag-index", "Vector DB индекс: загрузка документов, версии эмбеддингов", "Middle+", "AI / Search", "batch", "object_storage", "Vector Index", "EmbeddingDocument"),

    ("graphql-bff-aggregation", "GraphQL BFF: агрегация нескольких сервисов и partial response", "Middle+", "API", "sync", "graphql", "Profile Service", "UserProfile"),
    ("api-gateway-rate-limit", "API Gateway: лимиты, quotas и защита внешнего API", "Middle", "API Security", "security", "api_gateway", "Protected API", "ApiRequest"),
    ("service-mesh-mtls", "Service Mesh: mTLS, retries и observability", "Middle+", "Platform", "security", "service_mesh", "Internal Service", "MeshCall"),
    ("oidc-consent-flow", "OIDC consent: авторизация, scopes и аудит согласия", "Middle+", "Identity", "security", "auth_oidc", "Resource API", "ConsentGrant"),
    ("vault-secret-rotation", "Vault/KMS: ротация секретов без простоя", "Middle", "Security", "security", "vault", "Protected Service", "SecretRotation"),
    ("cdn-invalidation-flow", "CDN invalidation: событие обновления и purge", "Middle", "Web platform", "event", "kafka", "CDN invalidator", "CdnAsset"),

    ("aws-sns-sqs-fanout", "AWS SNS/SQS fan-out: разные consumer groups и DLQ", "Middle+", "Cloud messaging", "event", "sns_sqs", "SQS consumer", "CloudEvent"),
    ("azure-service-bus-session", "Azure Service Bus: sessions, ordering и dead-letter", "Middle+", "Cloud messaging", "event", "azure_service_bus", "ASB consumer", "ServiceBusMessage"),
    ("gcp-pubsub-delivery", "Google Pub/Sub: ack deadline, redelivery и ordering key", "Middle+", "Cloud messaging", "event", "gcp_pubsub", "PubSub consumer", "PubSubMessage"),
    ("redis-streams-consumer", "Redis Streams: consumer group, pending entries и replay", "Middle", "Messaging", "event", "redis_streams", "Stream consumer", "RedisStreamEvent"),
    ("nats-request-reply", "NATS: request/reply и event bus с timeout", "Middle", "Messaging", "event", "nats", "NATS consumer", "NatsEvent"),
    ("pulsar-multi-tenant-topic", "Pulsar: multi-tenant topics и retention", "Senior", "Messaging", "event", "pulsar", "Pulsar consumer", "PulsarEvent"),
    ("redis-queue-short-tasks", "Redis Queue: короткие задачи, retries и visibility timeout", "Junior+", "Queues", "event", "redis_queue", "Worker", "ShortTask"),

    ("mongodb-document-model", "MongoDB документная модель: версии документа и индексы", "Middle", "NoSQL", "sync", "mongodb", "Document Store", "DocumentAggregate"),
    ("cassandra-time-series", "Cassandra/ScyllaDB: time-series, partition key и TTL", "Middle+", "NoSQL", "batch", "cassandra", "Time-series Store", "TimeSeriesPoint"),
    ("dynamodb-idempotency-table", "DynamoDB idempotency table: conditional write и TTL", "Middle", "NoSQL", "sync", "dynamodb", "DynamoDB", "IdempotencyRecord"),
    ("db-sharding-tenant", "Шардирование БД по tenantId: маршрутизация и миграции", "Senior", "Database scaling", "sync", "db_sharding", "Shard Router", "TenantData"),
    ("read-replica-staleness", "Read replica: stale reads и read-your-writes", "Middle", "Database", "sync", "read_replica", "Read Replica", "ReadModelQuery"),
    ("redis-lock-concurrency", "Redis distributed lock: конкуренция и истечение lock", "Middle+", "Concurrency", "sync", "redis_lock", "Lock Service", "DistributedLock"),
    ("memcached-session-cache", "Memcached session cache: TTL, invalidation и fallback", "Junior+", "Caching", "sync", "memcached", "Session Cache", "SessionData"),
    ("search-reindex-bluegreen", "Search reindex: blue/green индекс и переключение алиаса", "Middle+", "Search", "batch", "object_storage", "Search Index", "SearchDocument"),
]

for cid, title, level, track, pattern, channel, target, entity in EXTENDED_PRACTICE_CASES:
    if any(c.get("id") == cid for c in CASES):
        continue
    CASES.append({
        "id": cid,
        "title": title,
        "level": level,
        "track": track,
        "timebox": "35–60 минут" if level in ("Middle+", "Senior") else "25–40 минут",
        "brief": "Практический enterprise-кейс для отработки архитектурных решений, рисков и production-контролей.",
        "goal": "Построить решение, явно указать границы ответственности, отказы, контракты, данные и эксплуатационные контроли.",
        "hidden_traps": [
            "не путать бизнес-успех с техническим ack",
            "не забыть идемпотентность, correlationId и владельца контракта",
            "описать degraded path, replay/reprocess и наблюдаемость",
        ],
        "skills": ["process", "sync_async", "reliability", "idempotency", "contracts", "data", "operations"] + (["security"] if pattern == "security" else []),
        "expected_controls": _controls_for_pattern(pattern),
        "payload": _practice_payload(title, entity, pattern, channel, target, level=level),
    })



# v8.6.47: языковая вычитка каталога кейсов. Термины вроде Kafka, REST,
# GraphQL и gRPC оставляем, но убираем техобрывки из названий и треков.
_CASE_TITLE_POLISH = {
    "Kafka + REST enrichment: кто должен обогащать событие": "Kafka + REST: кто должен обогащать событие",
    "БКИ → DWH → поиск: batch, качество и переобработка": "БКИ → аналитическое хранилище → поиск: пакетная загрузка, качество и переобработка",
    "Webhook от партнёра: подпись, дубли и окно времени": "Входящий веб-вызов от партнёра: подпись, дубли и окно времени",
    "RabbitMQ task queue: DLX, ack и prefetch": "RabbitMQ: очередь задач, подтверждения обработки и очередь ошибок",
    "Saga: заказ, оплата, резерв склада и компенсации": "Saga: заказ, оплата, резерв склада и компенсации",
    "Legacy SOAP adapter: fault model и трансформация": "Адаптер legacy SOAP: модель ошибок и преобразование форматов",
    "gRPC-вызов с deadline, fallback и circuit breaker": "gRPC-вызов: предельный срок ожидания, запасной сценарий и предохранитель",
    "Event sourcing: read model, replay и snapshot": "Event Sourcing: модель чтения, повторная обработка и снимки состояния",
    "CDC/outbox через Debezium: ordering и schema evolution": "CDC и Outbox через Debezium: порядок событий и эволюция схемы",
    "Multi-tenant интеграция: изоляция tenantId и лимиты": "Многоклиентская интеграция: изоляция tenantId и лимиты",
    "Внешний партнёр с rate limit: bulkhead, queue и backpressure": "Внешний партнёр с лимитом запросов: изоляция ресурса, очередь и обратное давление",
    "Manual review: workflow engine, SLA и возврат в основной поток": "Ручной разбор: workflow engine, SLA и возврат в основной поток",
    "Schema Registry: совместимость событий и governance": "Schema Registry: совместимость событий и управление изменениями",
    "Карточная авторизация и клиринг: online + batch reconciliation": "Карточная авторизация и клиринг: онлайн-операция и пакетная сверка",
    "Телеком CDR: поток событий, биллинг и batch-сверка": "Телеком CDR: поток событий, биллинг и пакетная сверка",
    "IoT тревоги: MQTT, дедуп, окно времени и ClickHouse": "IoT-тревоги: MQTT, дедупликация, окно времени и ClickHouse",
    "ActiveMQ legacy queue: poison messages и DLQ": "ActiveMQ в legacy-контуре: ядовитые сообщения и очередь ошибок",
    "CDC из Postgres: read model и порядок изменений": "CDC из Postgres: модель чтения и порядок изменений",
    "Debezium + schema migration: совместимость и backfill": "Debezium и миграция схемы: совместимость и дозагрузка истории",
    "GraphQL BFF: агрегация нескольких сервисов и partial response": "GraphQL BFF: агрегация нескольких сервисов и частичный ответ",
    "API Gateway: лимиты, quotas и защита внешнего API": "API Gateway: лимиты, квоты и защита внешнего API",
    "Redis Streams: consumer group, pending entries и replay": "Redis Streams: группы потребителей, зависшие сообщения и повторная обработка",
    "NATS: request/reply и event bus с timeout": "NATS: request/reply, событийная шина и таймауты",
    "Pulsar: multi-tenant topics и retention": "Pulsar: многоклиентские топики и срок хранения",
    "Redis Queue: короткие задачи, retries и visibility timeout": "Redis Queue: короткие задачи, повторы и таймаут видимости",
    "Redis distributed lock: конкуренция и истечение lock": "Redis distributed lock: конкуренция и истечение блокировки",
    "Memcached session cache: TTL, invalidation и fallback": "Memcached для сессий: срок жизни, инвалидация и запасной сценарий",
    "Search reindex: blue/green индекс и переключение алиаса": "Поиск: blue/green-переиндексация и переключение алиаса",
}
_TRACK_POLISH = {
    "Enterprise integration": "Enterprise-интеграции",
    "Data / DWH": "Данные и аналитическое хранилище",
    "Security / callbacks": "Безопасность и входящие вызовы",
    "Async tasks": "Асинхронные задачи",
    "Distributed transactions": "Распределённые транзакции",
    "Legacy integration": "Legacy-интеграции",
    "Synchronous integration": "Синхронные интеграции",
    "Architecture patterns": "Архитектурные паттерны",
    "CDC / Kafka": "CDC и Kafka",
    "Enterprise": "Enterprise-архитектура",
    "Resilience": "Отказоустойчивость",
    "Workflow": "Процессы и ручной разбор",
    "Contract governance": "Управление контрактами",
    "Payments": "Платежи",
    "Telecom": "Телеком",
    "Legacy queues": "Legacy-очереди",
    "CDC": "CDC",
    "CDC / Schema": "CDC и схемы данных",
    "API": "API-интеграции",
    "API Security": "Безопасность API",
    "Messaging": "Обмен сообщениями",
    "Queues": "Очереди",
    "Concurrency": "Конкурентность",
    "Caching": "Кэширование",
    "Search": "Поиск",
}
for _case in CASES:
    _case["title"] = _CASE_TITLE_POLISH.get(_case.get("title"), _case.get("title"))
    _case["track"] = _TRACK_POLISH.get(_case.get("track"), _case.get("track"))

CASE_BY_ID = {c["id"]: c for c in CASES}

# ---------------------------------------------------------------------------
# Оценивание решения
# ---------------------------------------------------------------------------


def list_cases() -> List[Dict[str, Any]]:
    """Возвращает безопасное описание кейсов без полного эталонного payload."""
    out = []
    for c in CASES:
        out.append({k: deepcopy(v) for k, v in c.items() if k != "payload"})
    return out


def get_case(case_id: str) -> Dict[str, Any] | None:
    case = CASE_BY_ID.get(case_id)
    return deepcopy(case) if case else None


def _blob(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).lower()


def _finding_skill(f: Dict[str, Any]) -> str:
    text = " ".join(str(f.get(k, "")) for k in ("rule", "category", "title", "why", "fix")).lower()
    if any(x in text for x in ("idempot", "дуб", "ordering", "partition", "ключ", "повтор", "eventid", "inbox")):
        return "idempotency"
    if any(x in text for x in ("contract", "контракт", "version", "schema", "api", "envelope", "expand", "migration")):
        return "contracts"
    if any(x in text for x in ("dlq", "replay", "retry", "timeout", "callback", "failure", "fallback", "poison")):
        return "reliability"
    if any(x in text for x in ("db", "dwh", "cache", "read model", "projection", "храни", "данн", "growth")):
        return "data"
    if any(x in text for x in ("sla", "monitor", "observe", "trace", "correlation", "capacity", "limit", "latency")):
        return "operations"
    if any(x in text for x in ("security", "auth", "token", "signature", "пдн", "sensitive", "gateway")):
        return "security"
    if any(x in text for x in ("sync", "async", "blocking", "external", "fan-in", "fanout", "очеред")):
        return "sync_async"
    return "process"


def _control_hits(case: Dict[str, Any], res: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    text = _blob({"model": res.get("model"), "patterns": res.get("patterns"), "findings": res.get("findings"), "tests": res.get("tests")})
    hits, misses = [], []
    for control in case.get("expected_controls", []):
        keywords = [str(k).lower() for k in control.get("keywords", [])]
        found = any(k and k in text for k in keywords)
        item = {**control, "found": found}
        (hits if found else misses).append(item)
    return hits, misses


def _skill_scores(case: Dict[str, Any], res: Dict[str, Any], misses: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    raw_scores = {k: 8.2 for k in SKILLS}
    # Навыки, заявленные кейсом, стартуют выше: это те оси, по которым мы специально тренируем.
    for skill in case.get("skills", []):
        if skill in raw_scores:
            raw_scores[skill] = 9.0
    evidence = {k: [] for k in SKILLS}
    for f in res.get("findings", []):
        skill = _finding_skill(f)
        sev = f.get("severity", "medium")
        raw_scores[skill] = max(0.0, raw_scores[skill] - SEVERITY_PENALTY.get(sev, 0.5))
        evidence[skill].append(f"{SEVERITY_RU.get(sev, sev)}: {f.get('title')}")
    for miss in misses:
        skill = miss.get("skill") or "process"
        if skill in raw_scores:
            raw_scores[skill] = max(0.0, raw_scores[skill] - 1.4)
            evidence[skill].append(f"Не найден контроль: {miss.get('label')}")
    return {
        k: {"name": SKILLS[k], "score": round(max(0.0, min(10.0, v)), 1), "evidence": evidence[k][:5]}
        for k, v in raw_scores.items()
    }


def _level(avg: float, critical: int, high: int) -> str:
    if critical > 0:
        return "ниже production-ready: есть критичные блокеры"
    if avg >= 9.0 and high == 0:
        return "Middle+/Senior-ready по этому кейсу"
    if avg >= 7.6:
        return "уверенный Middle"
    if avg >= 6.2:
        return "Junior+/Middle-: решение рабочее, но есть пробелы"
    return "требуется повторная практика по базовым инвариантам"


def _next_tasks(case: Dict[str, Any], misses: List[Dict[str, Any]], skills: Dict[str, Dict[str, Any]]) -> List[str]:
    tasks = []
    for m in misses[:4]:
        tasks.append(f"Доработать контроль «{m.get('label')}»: {m.get('why')}.")
    weak = sorted(skills.values(), key=lambda x: x["score"])[:3]
    for w in weak:
        if w["score"] < 7:
            tasks.append(f"Повторить тему: {w['name']} — текущая оценка {w['score']}/10.")
    if not tasks:
        tasks.append("Перерешать кейс в усложнении: добавить второго потребителя, сбой внешней системы и replay после падения consumer.")
    return tasks[:6]


def evaluate_learning_solution(case_id: str, payload: Dict[str, Any], mode: str = "learning") -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    mode = str(mode or "learning")
    base = analyze(payload)
    if not base.get("ok"):
        validation = base.get("errors", [])
        return {
            "ok": True,
            "case": {k: v for k, v in case.items() if k != "payload"},
            "base_ok": False,
            "mode": mode,
            "summary": "Схема не прошла базовую валидацию. Сначала исправьте структуру участников, связей и зависимостей.",
            "validation_errors": validation,
            "learning_score": 0.0,
            "learning_level": "невалидная схема: разбор невозможен до исправления структуры",
            "skill_scores": {k: {"name": name, "score": 0, "evidence": ["Базовая схема невалидна"]} for k, name in SKILLS.items()},
            "control_hits": [],
            "control_misses": case.get("expected_controls", []),
            "report_markdown": learning_markdown(case, None, None, mode, validation_errors=validation),
        }
    hits, misses = _control_hits(case, base)
    skills = _skill_scores(case, base, misses)
    avg = round(sum(x["score"] for x in skills.values()) / len(skills), 1)
    verdict = base.get("verdict", {})
    critical = verdict.get("group_counts", {}).get("critical", verdict.get("counts", {}).get("critical", 0))
    high = verdict.get("group_counts", {}).get("high", verdict.get("counts", {}).get("high", 0))
    learning_level = _level(avg, critical, high)
    strengths = []
    for h in hits[:8]:
        strengths.append(f"Найден контроль: {h.get('label')}.")
    if base.get("verdict", {}).get("verdict") == "green":
        strengths.append("Базовое ядро не видит high/critical блокеров: решение можно обсуждать как production-ready черновик.")
    if not strengths:
        strengths.append("Решение построено и прошло базовый анализ, но ключевые учебные контроли кейса выражены слабо.")
    gaps = []
    for m in misses[:8]:
        gaps.append({"title": m.get("label"), "why": m.get("why"), "skill": SKILLS.get(m.get("skill"), m.get("skill")), "fix": f"Явно добавьте в шаги/компенсации: {', '.join(m.get('keywords', [])[:4])}."})
    # В режиме собеседования оценка чуть строже: важно явно проговаривать контроли.
    if mode == "interview" and misses:
        avg = round(max(0.0, avg - min(1.2, len(misses) * 0.25)), 1)
        learning_level = _level(avg, critical, high)
    result = {
        "ok": True,
        "case": {k: v for k, v in case.items() if k != "payload"},
        "base_ok": True,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "base_verdict": verdict,
        "learning_score": avg,
        "learning_level": learning_level,
        "skill_scores": skills,
        "control_hits": hits,
        "control_misses": misses,
        "strengths": strengths,
        "gaps": gaps,
        "next_tasks": _next_tasks(case, misses, skills),
        "reference_payload": case.get("payload") if mode in ("reference", "interview_review") else None,
        "base_result": base,
    }
    result["reference_comparison"] = compare_to_reference(case, payload, result)
    result["hints_available"] = [1, 2, 3, 4]
    result["report_markdown"] = learning_markdown(case, result, base, mode)
    return result


# ---------------------------------------------------------------------------
# v8.6.56: честная визуальная сборка учебного решения.
# Визуальные чекбоксы больше не отдают полный эталон под видом "выбранных
# контролей". Payload строится из ослабленного эталона и добавляет только те
# production-контроли, которые пользователь действительно выбрал.
# ---------------------------------------------------------------------------

def _visual_payload_scrub_text_v8656(value: str, keywords: List[str]) -> str:
    import re
    out = str(value or "")
    for kw in sorted({str(k).strip() for k in keywords if str(k).strip()}, key=len, reverse=True):
        out = re.sub(re.escape(kw), " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip(" ;,.-")
    return out


def _visual_payload_walk_scrub_v8656(obj: Any, keywords: List[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _visual_payload_walk_scrub_v8656(v, keywords) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_visual_payload_walk_scrub_v8656(v, keywords) for v in obj]
    if isinstance(obj, str):
        return _visual_payload_scrub_text_v8656(obj, keywords)
    return obj


def build_learning_visual_payload(case_id: str, selected_control_ids: List[str] | None = None, kind: str = "selected") -> Dict[str, Any]:
    """Собирает payload для визуального тренажёра без ручного JSON.

    kind:
    - reference: полный эталон;
    - weak: намеренно слабый черновик;
    - selected: ослабленный эталон + только выбранные пользователем контроли.
    """
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    controls = case.get("expected_controls") or []
    selected_ids = {str(x) for x in (selected_control_ids or []) if str(x).strip()}
    if kind == "reference":
        return {
            "ok": True,
            "kind": "reference",
            "selected_count": len(controls),
            "control_count": len(controls),
            "payload": deepcopy(case.get("payload") or {}),
            "message": "Подставлен полный эталон кейса.",
        }

    selected_controls = [c for c in controls if str(c.get("id")) in selected_ids]
    all_keywords: List[str] = []
    for c in controls:
        all_keywords.extend([str(c.get("label", "")), str(c.get("why", ""))])
        all_keywords.extend(str(k) for k in c.get("keywords", []))

    payload = deepcopy(case.get("payload") or {})
    # Сначала убираем признаки всех учебных контролей из эталона, чтобы пустой
    # выбор не проходил как сильное решение только потому, что эталон был внутри.
    payload = _visual_payload_walk_scrub_v8656(payload, all_keywords)
    meta = payload.setdefault("meta", {})
    meta["description"] = "Черновик, собранный визуальным тренажёром. Production-контроли добавляются только из выбранных чекбоксов."
    meta["lookup_keys"] = "entity"
    meta["fields"] = "entity:string|required, status:string|required, updatedAt:datetime|required"
    meta["statuses"] = "CREATED, PROCESSED, FAILED"

    # В слабом/выборочном режиме технические гарантии по умолчанию сняты.
    for step in payload.get("steps", []) or []:
        step["retry"] = "none"
        step["idempotency"] = "none"
        step["timeout_ms"] = ""
        step["compensation"] = "Контроль не выбран пользователем."

    if kind == "weak":
        payload["systems"] = (payload.get("systems") or [])[:3]
        payload["steps"] = (payload.get("steps") or [])[:1]
        meta["description"] = "Слабый учебный черновик: пользователь пока не описал production-контроли."
        return {
            "ok": True,
            "kind": "weak",
            "selected_count": 0,
            "control_count": len(controls),
            "payload": payload,
            "message": "Собран намеренно слабый черновик для проверки ошибок.",
        }

    evidence_lines = []
    selected_keywords: List[str] = []
    for c in selected_controls:
        kws = [str(k) for k in c.get("keywords", []) if str(k).strip()]
        selected_keywords.extend(kws)
        evidence_lines.append(f"Выбран контроль: {c.get('label')}. Ключевые признаки: {', '.join(kws[:5])}.")

    if evidence_lines:
        meta["description"] = (meta.get("description", "") + "\n" + "\n".join(evidence_lines)).strip()
        selected_blob = " ".join(selected_keywords).lower()
        fields = ["entity:string|required", "status:string|required", "updatedAt:datetime|required"]
        if any(x in selected_blob for x in ("eventid", "event id", "дедуп", "unique", "idempot")):
            fields.append("eventId:uuid|required|unique")
            fields.append("idempotencyKey:string|required|unique")
        if any(x in selected_blob for x in ("correlation", "trace", "трасс")):
            fields.append("correlationId:uuid|required|indexed")
        if any(x in selected_blob for x in ("version", "schema", "контракт", "верси", "v2")):
            fields.append("payloadVersion:int|required")
            fields.append("schemaVersion:string|required")
        if any(x in selected_blob for x in ("externalid", "internalid", "mapping", "соответств")):
            meta["lookup_keys"] = "externalId + internalId + entity"
        if any(x in selected_blob for x in ("partition", "ключ порядка", "entityid", "applicationid")):
            meta["lookup_keys"] = (meta.get("lookup_keys", "entity") + "; partition key entityId/applicationId").strip("; ")
        meta["fields"] = ", ".join(dict.fromkeys(fields))
        if any(x in selected_blob for x in ("waiting", "review", "unknown", "workflow")):
            meta["statuses"] = "CREATED, WAITING_EXTERNAL, PROCESSED, FAILED, NEEDS_MANUAL_REVIEW, UNKNOWN"

        note = " ".join(evidence_lines)
        for step in payload.get("steps", []) or []:
            step["compensation"] = (step.get("compensation", "") + "; " + note).strip("; ")
            if any(x in selected_blob for x in ("timeout", "deadline", "таймаут", "rate limit", "circuit", "лимит")):
                if str(step.get("blocking", "")).lower() in ("yes", "true", "1") or str(step.get("channel", "")).lower() in ("rest", "grpc", "soap", "api_gateway"):
                    step["timeout_ms"] = step.get("timeout_ms") or "500"
            if any(x in selected_blob for x in ("retry", "replay", "dlq", "quarantine", "карантин", "повтор")):
                step["retry"] = "auto"
            if any(x in selected_blob for x in ("idempot", "eventid", "unique", "дедуп", "partition", "ключ")):
                step["idempotency"] = "key"

    return {
        "ok": True,
        "kind": "selected",
        "selected_count": len(selected_controls),
        "control_count": len(controls),
        "payload": payload,
        "message": "Собран черновик по выбранным контролям." if selected_controls else "Контроли не выбраны: собран слабый черновик, который должен показать пропуски.",
    }

def evaluate_reference(case_id: str) -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    return evaluate_learning_solution(case_id, case["payload"], mode="reference")


# ---------------------------------------------------------------------------
# Production layer: подсказки, сравнение с эталоном, сохранение попыток,
# прогресс и проверка каталога. Всё остаётся rule-based и не ломает старое ядро.
# ---------------------------------------------------------------------------

LEARNING_APP_DIR = Path(os.environ.get("APP_DIR", ".architect6"))
LEARNING_DB_NAME = "learning.sqlite3"

LEVEL_ORDER = ["Junior", "Junior+", "Middle", "Middle+", "Senior"]

PROGRESS_BADGES = [
    {"id": "first_case", "title": "Первый кейс", "rule": "Решить хотя бы один учебный кейс"},
    {"id": "middle_score", "title": "Уверенный Middle", "rule": "Получить 7.6+ за любой кейс"},
    {"id": "production_ready", "title": "Production-ready", "rule": "Получить 9.0+ без critical/high"},
    {"id": "five_cases", "title": "Серия практики", "rule": "Решить 5 разных кейсов"},
]


def _safe_learner_id(value: str | None) -> str:
    value = str(value or "anonymous").strip()
    value = re.sub(r"[^a-zA-Z0-9_.:@-]", "_", value)[:96]
    return value or "anonymous"


def _learning_db_path() -> Path:
    app_dir = Path(os.environ.get("APP_DIR", str(LEARNING_APP_DIR)))
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / LEARNING_DB_NAME


def learning_db() -> sqlite3.Connection:
    con = sqlite3.connect(_learning_db_path())
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE IF NOT EXISTS learning_attempts ("
        "id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, case_id TEXT NOT NULL, "
        "created TEXT NOT NULL, mode TEXT NOT NULL, score REAL NOT NULL, "
        "level TEXT NOT NULL, base_verdict TEXT, payload_hash TEXT, "
        "skills_json TEXT, hits_json TEXT, misses_json TEXT, report TEXT NOT NULL)"
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_learning_attempts_learner ON learning_attempts(learner_id, created)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_learning_attempts_case ON learning_attempts(case_id, created)")
    return con


def _payload_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def save_learning_attempt(learner_id: str | None, case_id: str, payload: Dict[str, Any], ev: Dict[str, Any], mode: str = "learning") -> str:
    """Сохраняет учебную попытку. Не требует авторизации; caller задаёт learner_id.

    Для публичного SaaS этот id заменяется authenticated user id, но для MVP уже
    появляется история, прогресс, экспорт и контроль повторных попыток.
    """
    aid = uuid.uuid4().hex
    learner = _safe_learner_id(learner_id)
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with learning_db() as con:
        con.execute(
            "INSERT INTO learning_attempts "
            "(id, learner_id, case_id, created, mode, score, level, base_verdict, payload_hash, skills_json, hits_json, misses_json, report) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                aid,
                learner,
                case_id,
                created,
                mode,
                float(ev.get("learning_score") or 0),
                str(ev.get("learning_level") or ""),
                str((ev.get("base_verdict") or {}).get("verdict") or "invalid"),
                _payload_hash(payload),
                json.dumps(ev.get("skill_scores") or {}, ensure_ascii=False),
                json.dumps(ev.get("control_hits") or [], ensure_ascii=False),
                json.dumps(ev.get("control_misses") or [], ensure_ascii=False),
                str(ev.get("report_markdown") or ""),
            ),
        )
    return aid


def load_learning_attempt(attempt_id: str) -> Dict[str, Any] | None:
    if not re.fullmatch(r"[0-9a-f]{32}", str(attempt_id or "")):
        return None
    with learning_db() as con:
        row = con.execute("SELECT * FROM learning_attempts WHERE id=?", (attempt_id,)).fetchone()
    return dict(row) if row else None


def learning_attempt_markdown(attempt_id: str) -> str | None:
    row = load_learning_attempt(attempt_id)
    return row.get("report") if row else None


def learning_catalog_summary() -> Dict[str, Any]:
    by_level: Dict[str, int] = {}
    by_track: Dict[str, int] = {}
    for c in CASES:
        by_level[c.get("level", "—")] = by_level.get(c.get("level", "—"), 0) + 1
        by_track[c.get("track", "—")] = by_track.get(c.get("track", "—"), 0) + 1
    return {
        "version": APP_LEARNING_VERSION,
        "catalog_version": CASE_CATALOG_VERSION,
        "case_count": len(CASES),
        "levels": by_level,
        "tracks": by_track,
        "skills": SKILLS,
        "badges": PROGRESS_BADGES,
    }


def learning_hints(case_id: str, level: int = 1) -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    level = max(1, min(4, int(level or 1)))
    controls = case.get("expected_controls", [])
    hints: List[str] = []
    if level == 1:
        hints = [f"Обратите внимание на риск: {_ru_sentence(x)}" for x in case.get("hidden_traps", [])[:3]]
    elif level == 2:
        hints = [f"Проверьте контроль «{_ru_sentence(c.get('label')).rstrip('.')}»: {_ru_sentence(c.get('why'))}" for c in controls[:4]]
    elif level == 3:
        hints = [f"Добавьте в решение явное описание контроля «{_ru_sentence(c.get('label')).rstrip('.')}». В тексте решения должно быть понятно, как именно закрывается риск: {_ru_sentence(c.get('why'))}" for c in controls[:5]]
    else:
        steps = case.get("payload", {}).get("steps", [])[:6]
        hints = [f"Эталонный шаг {s.get('order')}: {humanize_terms(s.get('source_system'))} → {humanize_terms(s.get('target_system'))}. Способ взаимодействия: {display_channel(s.get('channel'))}. Действие: {_ru_sentence(s.get('name'))}" for s in steps]
    return {"ok": True, "case_id": case_id, "level": level, "hints": hints}


def _steps_signature(payload: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    sig = []
    for s in payload.get("steps", []) or []:
        sig.append((str(s.get("source_system") or "").lower(), str(s.get("target_system") or "").lower(), str(s.get("channel") or "").lower()))
    return sig


def compare_to_reference(case: Dict[str, Any], payload: Dict[str, Any], ev: Dict[str, Any]) -> Dict[str, Any]:
    ref = case.get("payload") or {}
    ref_sig = set(_steps_signature(ref))
    got_sig = set(_steps_signature(payload or {}))
    ref_channels = {x[2] for x in ref_sig if x[2]}
    got_channels = {x[2] for x in got_sig if x[2]}
    ref_roles = {str(s.get("role") or "").lower() for s in ref.get("systems", [])}
    got_roles = {str(s.get("role") or "").lower() for s in (payload or {}).get("systems", [])}
    hits = ev.get("control_hits") or []
    misses = ev.get("control_misses") or []
    return {
        "matched_route_count": len(ref_sig & got_sig),
        "reference_route_count": len(ref_sig),
        "channel_coverage": sorted(ref_channels & got_channels),
        "missing_channels": sorted(ref_channels - got_channels),
        "role_coverage": sorted(ref_roles & got_roles),
        "missing_roles": sorted(ref_roles - got_roles),
        "control_hit_count": len(hits),
        "control_miss_count": len(misses),
    }


def progress_for_learner(learner_id: str | None) -> Dict[str, Any]:
    learner = _safe_learner_id(learner_id)
    with learning_db() as con:
        rows = [dict(r) for r in con.execute(
            "SELECT id, case_id, created, mode, score, level, base_verdict, payload_hash, skills_json, hits_json, misses_json "
            "FROM learning_attempts WHERE learner_id=? ORDER BY created DESC LIMIT 250", (learner,)
        ).fetchall()]
    solved_cases = sorted({r["case_id"] for r in rows if float(r.get("score") or 0) > 0})
    latest_by_case: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        latest_by_case.setdefault(r["case_id"], r)
    skill_totals: Dict[str, List[float]] = {k: [] for k in SKILLS}
    for r in rows:
        try:
            skills = json.loads(r.get("skills_json") or "{}")
        except Exception:
            skills = {}
        for k, v in skills.items():
            if isinstance(v, dict) and k in skill_totals:
                skill_totals[k].append(float(v.get("score") or 0))
    skill_avg = {
        k: {"name": SKILLS[k], "score": round(sum(vals) / len(vals), 1) if vals else None}
        for k, vals in skill_totals.items()
    }
    badges = []
    if rows:
        badges.append("first_case")
    if any(float(r.get("score") or 0) >= 7.6 for r in rows):
        badges.append("middle_score")
    if any(float(r.get("score") or 0) >= 9.0 and str(r.get("base_verdict")) == "green" for r in rows):
        badges.append("production_ready")
    if len(solved_cases) >= 5:
        badges.append("five_cases")
    weak = sorted([v for v in skill_avg.values() if v["score"] is not None], key=lambda x: x["score"])[:3]
    return {
        "ok": True,
        "learner_id": learner,
        "attempt_count": len(rows),
        "solved_case_count": len(solved_cases),
        "case_count": len(CASES),
        "latest_attempts": rows[:20],
        "latest_by_case": latest_by_case,
        "skill_average": skill_avg,
        "weak_skills": weak,
        "badges": badges,
        "catalog": learning_catalog_summary(),
    }


def progress_markdown(learner_id: str | None) -> str:
    p = progress_for_learner(learner_id)
    out = ["# Прогресс обучения", "", f"Пользователь: `{p['learner_id']}`", f"Попыток: **{p['attempt_count']}**", f"Кейсов решено: **{p['solved_case_count']} / {p['case_count']}**", ""]
    out.append("## Средние оценки по навыкам")
    for _, s in p["skill_average"].items():
        out.append(f"- {s['name']}: {s['score'] if s['score'] is not None else 'нет данных'}")
    out.append("")
    out.append("## Последние попытки")
    if not p["latest_attempts"]:
        out.append("- Пока попыток нет.")
    for a in p["latest_attempts"][:20]:
        out.append(f"- {a['created']} · {a['case_id']} · {a['score']}/10 · {a['level']}")
    return "\n".join(out).strip() + "\n"


def _fast_reference_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    """Быстрая deep-проверка эталона без генерации большого markdown-отчёта.

    Для 80+ кейсов полноценный learning report занимает заметное время, а
    каталожная проверка должна запускаться в CI быстро: нам нужно доказать,
    что payload валиден, ключевые учебные контроли видны ядру и score не ниже
    порога.
    """
    base = analyze(case.get("payload") or {})
    if not base.get("ok"):
        return {"ok": False, "base_ok": False, "score": 0.0, "errors": base.get("errors", [])}
    hits, misses = _control_hits(case, base)
    skills = _skill_scores(case, base, misses)
    avg = round(sum(x["score"] for x in skills.values()) / len(skills), 1)
    return {"ok": True, "base_ok": True, "score": avg, "hit_count": len(hits), "miss_count": len(misses)}


def validate_learning_catalog(deep: bool = False) -> Dict[str, Any]:
    issues: List[str] = []
    deep_results: List[Dict[str, Any]] = []
    ids = set()
    required = {"id", "title", "level", "track", "brief", "goal", "expected_controls", "hidden_traps", "payload"}
    for c in CASES:
        cid = c.get("id")
        if not cid or cid in ids:
            issues.append(f"duplicate_or_empty_id:{cid}")
        ids.add(cid)
        miss = required - set(c.keys())
        if miss:
            issues.append(f"{cid}:missing:{','.join(sorted(miss))}")
        if not c.get("expected_controls"):
            issues.append(f"{cid}:no_expected_controls")
        if not c.get("hidden_traps"):
            issues.append(f"{cid}:no_hidden_traps")
        if len((c.get("payload") or {}).get("steps", [])) < 3:
            issues.append(f"{cid}:too_few_steps")
        if deep:
            ev = _fast_reference_quality(c)
            deep_results.append({"id": cid, **ev})
            if not ev.get("ok") or ev.get("base_ok") is not True:
                issues.append(f"{cid}:reference_invalid:{ev.get('errors')}")
            elif float(ev.get("score") or 0) < 7.0:
                issues.append(f"{cid}:reference_low_score:{ev.get('score')}")
    return {"ok": not issues, "case_count": len(CASES), "issues": issues, "summary": learning_catalog_summary(), "deep_results": deep_results if deep else []}


def _mode_label(mode: str) -> str:
    return {
        "learning": "учебная проверка",
        "interview": "режим собеседования",
        "interview_review": "разбор собеседования",
        "reference": "проверка эталона",
    }.get(mode, mode)

# ---------------------------------------------------------------------------
# Отчёты и HTML
# ---------------------------------------------------------------------------


def _md_list(items: Iterable[str]) -> str:
    arr = [str(x).strip() for x in items if str(x).strip()]
    return "\n".join(f"- {x}" for x in arr) if arr else "- Не указано."



def _ru_sentence(text: Any) -> str:
    """Возвращает аккуратное русское предложение для учебного отчёта."""
    text = humanize_terms(str(text or '')).strip()
    text = re.sub(r'\s+', ' ', text)
    fixes = {
        'DLQ/quarantine': 'очередь ошибок или карантин',
        'DLQ / карантин': 'очередь ошибок или карантин',
        'DLQ': 'очередь ошибок',
        'quarantine': 'карантин',
        'manual review': 'ручной разбор',
        'fallback': 'запасной сценарий',
        'event envelope': 'обёртка события',
        'partition key': 'ключ партиционирования',
        'production-ready': 'готовый к промышленному запуску',
        'Production-ready': 'Готовый к промышленному запуску',
        'verdict': 'вывод',
        'промышленный запуск-ready': 'готовую к промышленному запуску',
        'ГОТОВО к проектированию': 'готово к проектированию',
        'УСЛОВНО ГОТОВО': 'условно готово',
        'DLQ/quarantine': 'очередь ошибок или карантин',
        'DLQ / quarantine': 'очередь ошибок или карантин',
        'DLQ': 'очередь ошибок',
        'outbox': 'Outbox',
        'Outbox для': 'Outbox для',
        'partition': 'ключ партиционирования',
        'applicationid': 'applicationId',
        'entityid': 'entityId',
        'timeout': 'таймаут',
        'version': 'версия',
        'schema': 'схема',
        'Повторная попытка настроен': 'Повторные попытки настроены',
        'повторная попытка настроен': 'повторные попытки настроены',
        'Повторная попытка без лимита': 'Повторные попытки без лимита',
        'повторная попытка без лимита': 'повторные попытки без лимита',
        'очередь ошибочных сообщений': 'очередь ошибок',
        'replay': 'повторная обработка',
        'manual review': 'ручной разбор',
        'correlationId': 'сквозной идентификатор',
        'idempotencyKey': 'ключ идемпотентности',
        'eventId': 'идентификатор события',
        'event envelope': 'обёртка события',
        'обязательную обёртка события': 'обязательную обёртку события',
        'обязательная обёртка события': 'обязательная обёртка события',
        'reconciliation-сверки': 'сверки',
        'reconciliation-сверка': 'сверка',
        'reconciliation': 'сверка',
        'online': 'онлайн',
        'batch': 'пакетная обработка',
        'ready': 'готово',
        'ГОТОВО': 'готово',
        'УСЛОВНО ГОТОВО': 'условно готово',
        'fraud': 'антифрод',
        'Fraud': 'Антифрод',
        'core dependency': 'зависимостью основного потока',
        'degraded path': 'сценарий управляемой деградации',
        'reprocess': 'переобработка',
        'validation': 'валидация',
        'deadline': 'предельный срок ожидания',
        'transaction': 'транзакция',
        'optimistic locking': 'оптимистичная блокировка',
        'optimistic lock': 'оптимистичная блокировка',
        'monitoring': 'мониторинг',
        'freshness': 'свежесть данных',
        'schema validation': 'валидация схемы',
        'reject report': 'отчёт об отклонении',
        'idempotent load by': 'идемпотентная загрузка по',
        'idempotent handler': 'идемпотентный обработчик',
        'idempotent update': 'идемпотентное обновление',
        'inbox/dedup': 'Inbox и дедупликация',
        'dedup': 'дедупликация',
        'delivery status': 'статус доставки',
        'ack': 'подтверждение обработки',
        'reconnect': 'переподключение',
        'backpressure': 'обратное давление',
        'limited повторная попытка': 'ограниченные повторы',
        'externalOperationId': 'внешний идентификатор операции',
        'externalId/internalId mapping': 'сопоставление внешнего и внутреннего идентификаторов',
        'mapping': 'сопоставление',
        'unknown': 'неизвестный статус',
        'signature': 'подпись запроса',
        'signed response': 'подписанный ответ',
        'повторная попытка window': 'окно повторной отправки',
        'UNIQUE': 'уникальный индекс',
        'schemaVersion': 'версия схемы',
        'Core service': 'Core service',
        'Core DB': 'Core DB',
        'Process service': 'Process service',
        'Process DB': 'Process DB',
        'Raw storage': 'Raw storage',
        'Audit Log': 'журнал аудита',
        'DWH': 'аналитическое хранилище',
    }
    for old, new in fixes.items():
        text = text.replace(old, new)
    if text and text[-1] not in '.!?':
        text += '.'
    return text


def _ru_list(items: Iterable[Any]) -> str:
    arr = [_ru_sentence(x) for x in items if str(x or '').strip()]
    return "\n".join(f"- {x}" for x in arr) if arr else "- Не указано."


def _display_channels(keys: Iterable[str]) -> str:
    vals = []
    for key in keys or []:
        label = display_channel(key)
        vals.append(label.split(' — ')[0])
    return ', '.join(vals) if vals else 'нет'


def _reference_scheme_lines(payload: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for st in payload.get('steps', []) or []:
        src = humanize_terms(st.get('source_system') or 'источник не указан')
        tgt = humanize_terms(st.get('target_system') or 'получатель не указан')
        tech = display_channel(st.get('channel'))
        name = _ru_sentence(st.get('name') or 'действие не указано')
        deps = str(st.get('depends_on') or '').strip()
        dep_text = f" После шагов: {deps}." if deps else " Это стартовый шаг или вход в процесс."
        controls = _ru_sentence(st.get('compensation') or 'Для шага нужно явно описать обработку ошибок и владельца.')
        lines.append(f"{st.get('order')}. **{name}** {src} → {tgt}. Способ: {tech}.{dep_text} Контроли: {controls}")
    return lines


def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    """Грамотный учебный отчёт без технических обрубков и сырого JSON как основного ответа."""
    out: List[str] = []
    out.append(f"# Учебный разбор: {humanize_terms(case['title'])}")
    out.append("")
    out.append(f"**Уровень кейса:** {humanize_terms(case.get('level'))}  ")
    out.append(f"**Трек:** {humanize_terms(case.get('track'))}  ")
    out.append(f"**Цель:** {_ru_sentence(case.get('goal'))}  ")
    out.append(f"**Режим:** {_mode_label(mode)}")
    out.append("")
    if validation_errors:
        out.append("## 1. Схема пока невалидна")
        out.append(_ru_list(validation_errors))
        out.append("")
        out.append("Сначала исправьте базовую структуру: участники должны существовать, зависимости должны ссылаться на реальные шаги, а циклов в цепочке быть не должно.")
        return "\n".join(out).strip() + "\n"

    assert ev is not None and base is not None
    bv = ev.get("base_verdict") or {}
    out.append("## 1. Итоговая оценка")
    out.append(f"- Учебная оценка: **{ev['learning_score']}/10**.")
    out.append(f"- Уровень решения: **{_ru_sentence(ev['learning_level'])}**")
    out.append(f"- Вывод архитектурного ядра: **{_ru_sentence(bv.get('verdict', 'не рассчитан')).rstrip('.')}**, {bv.get('score', '—')}/10.")
    out.append("")

    out.append("## 2. Профиль навыков")
    for _, data in ev["skill_scores"].items():
        out.append(f"- **{humanize_terms(data['name'])}**: {data['score']}/10.")
        for e in data.get("evidence", [])[:2]:
            out.append(f"  - {_ru_sentence(e)}")
    out.append("")

    out.append("## 3. Что сделано правильно")
    out.append(_ru_list(ev.get("strengths", [])))
    out.append("")

    comp = ev.get("reference_comparison") or {}
    out.append("## 4. Сравнение с эталоном")
    out.append(f"- Совпавших маршрутов: **{comp.get('matched_route_count', 0)} / {comp.get('reference_route_count', 0)}**.")
    out.append(f"- Покрытые способы взаимодействия: {_display_channels(comp.get('channel_coverage') or [])}.")
    out.append(f"- Недостающие способы из эталона: {_display_channels(comp.get('missing_channels') or [])}.")
    out.append(f"- Найдено учебных контролей: **{comp.get('control_hit_count', 0)}**; пропущено: **{comp.get('control_miss_count', 0)}**.")
    out.append("")

    out.append("## 5. Что мешает готовности к промышленному запуску")
    if ev.get("gaps"):
        for g in ev["gaps"]:
            out.append(f"### {_ru_sentence(g['title']).rstrip('.')}")
            out.append(f"**Почему важно:** {_ru_sentence(g.get('why'))}")
            out.append(f"**Как исправить:** {_ru_sentence(g.get('fix'))}")
            out.append("")
    else:
        out.append("Ключевые учебные контроли кейса найдены. Перед реальным выпуском всё равно проверьте нефункциональные требования, контракты, нагрузку, безопасность и эксплуатационные сценарии.")
        out.append("")

    out.append("## 6. Типовые ловушки этого кейса")
    out.append(_ru_list(case.get("hidden_traps", [])))
    out.append("")

    out.append("## 7. Следующие задания")
    out.append(_ru_list(ev.get("next_tasks", [])))
    out.append("")

    out.append("## 8. Эталонная схема решения")
    out.append("Ниже показан не сырой технический JSON, а человеческое описание эталонного варианта. Его можно использовать как ориентир для повторного прохождения кейса.")
    out.append("")
    for line in _reference_scheme_lines(case.get("payload") or {}):
        out.append(line)
    out.append("")

    if mode in ("reference", "interview_review"):
        out.append("## 9. Как читать эталон")
        out.append("Эталон не является единственно возможной архитектурой. Он показывает минимальный набор гарантий, без которых решение обычно нельзя считать готовым к промышленному запуску: идемпотентность, управляемые повторы, понятные контракты, восстановление после ошибок и наблюдаемость.")
        out.append("")

    out.append("## 10. Полный архитектурный отчёт ядра")
    out.append("")
    out.append(markdown_report(base))
    return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

def learning_result_html(ev: Dict[str, Any]) -> str:
    if not ev.get("ok"):
        return "<div class='err'>" + escape("; ".join(ev.get("errors", []))) + "</div>"
    if not ev.get("base_ok", True):
        errs = "".join(f"<li>{escape(x)}</li>" for x in ev.get("validation_errors", []))
        return f"<div class='finding critical'><h3>Схема невалидна</h3><ul>{errs}</ul></div>"
    skills = ev.get("skill_scores", {})
    skill_cards = []
    for _, s in skills.items():
        evs = "".join(f"<li>{escape(x)}</li>" for x in s.get("evidence", [])[:3])
        skill_cards.append(f"<div class='learn-skill'><b>{escape(s['name'])}</b><span>{s['score']}/10</span><ul>{evs}</ul></div>")
    gaps = ev.get("gaps", [])
    gap_html = "".join(
        f"<div class='finding high'><h3>{escape(_ru_sentence(g['title']).rstrip('.'))}</h3><p><b>Почему важно:</b> {escape(_ru_sentence(g.get('why','')))}</p><p><b>Как исправить:</b> {escape(_ru_sentence(g.get('fix','')))}</p></div>"
        for g in gaps
    ) or "<p>Ключевые учебные контроли найдены. Проверьте детали контрактов и эксплуатационные ограничения.</p>"
    tasks = "".join(f"<li>{escape(x)}</li>" for x in ev.get("next_tasks", []))
    strengths = "".join(f"<li>{escape(x)}</li>" for x in ev.get("strengths", []))
    comp = ev.get("reference_comparison") or {}
    compare_html = f"<div class='learn-compare'><b>Сравнение с эталоном:</b> маршруты {comp.get('matched_route_count',0)}/{comp.get('reference_route_count',0)}, найдено контролей {comp.get('control_hit_count',0)}, пропущено {comp.get('control_miss_count',0)}.</div>"
    return f"""
    <div class='learn-verdict'>
      <h2>{escape(str(ev.get('learning_score')))} / 10 · {escape(ev.get('learning_level',''))}</h2>
      <p>Архитектурная оценка ядра: {escape(str((ev.get('base_verdict') or {}).get('verdict','—')))} · {(ev.get('base_verdict') or {}).get('score','—')}/10</p>
    </div>
    {compare_html}
    <h3>Профиль навыков</h3><div class='learn-skills'>{''.join(skill_cards)}</div>
    <h3>Что сделано правильно</h3><ul>{strengths}</ul>
    <h3>Что доработать</h3>{gap_html}
    <h3>Следующие задания</h3><ol>{tasks}</ol>
    """

# v8.6.47b: финальная языковая вычитка учебного слоя.
_PREV_RU_SENTENCE_V8647B = _ru_sentence


def _ru_sentence(text: str) -> str:
    out = _PREV_RU_SENTENCE_V8647B(text)
    replacements = {
        'immutable audit': 'неизменяемый журнал аудита',
        'immutable raw zone': 'неизменяемая зона исходных данных',
        'consumer': 'потребителя',
        'business metrics': 'бизнес-метрики',
        'technical metrics': 'технические метрики',
        'dashboard': 'дашборд',
        'alert rules': 'правила алертов',
        'breaker state': 'состояние предохранителя',
        'Read-your-writes после async-записи': 'чтение сразу после асинхронной записи',
        'data quality metrics': 'метрики качества данных',
        'data quality': 'качество данных',
        'event-driven': 'событийный',
        'downпоток': 'нижестоящий поток',
        'sync/API': 'синхронный API',
        'orchestration state': 'состояние оркестрации',
        'workflow': 'длительный процесс',
        'reason code': 'код причины',
        'audit reason': 'причина аудита',
        'audit hash/evidence': 'хэш аудита и доказательства',
        'audit queries': 'аудиторские запросы',
        'audit trail': 'неизменяемый журнал аудита',
        'audit/журнал событий': 'аудит и журнал событий',
        'audit': 'аудит',
        'row counts': 'количество строк',
        'alerts': 'алерты',
        'lineage': 'происхождение данных',
        'metrics:': 'метрики:',
        'created/completed/failed/stuck/контроль возраста статуса/повторно обработано/reconciled': 'создано, завершено, завершено ошибкой, зависло, возраст статуса, повторно обработано, сверено',
        'correction records': 'записи корректировок',
        'versioned reports': 'версионированные отчёты',
        'evidence': 'доказательства',
        'anonymization': 'обезличивание',
        'legal hold': 'юридическое удержание данных',
        'actor': 'участник действия',
        'body hash': 'хэш тела сообщения',
        'hash': 'хэш',
        'Core service': 'Основной сервис',
        'Core DB': 'Основная БД',
        'Process service': 'Сервис процесса',
        'Process DB': 'БД процесса',
        'Raw storage': 'Хранилище исходных данных',
        'Audit Log': 'Журнал аудита',
        'Event Broker': 'Брокер событий',
        'Device clients': 'Клиентские устройства',
        'Realtime service': 'Сервис реального времени',
        'Clearing consumer': 'Потребитель клиринговых событий',
        'Session store': 'Хранилище сессий',
        'Ingestion service': 'Сервис загрузки данных',
        'Search Index': 'Поисковый индекс',
        'schema валидация': 'валидация схемы',
        'схемаVersion': 'версия схемы',
        'таблица исходящих сообщений-событие': 'событие в Outbox-таблице',
        'Зафиксировать таблица исходящих сообщений-событие': 'Зафиксировать событие в Outbox-таблице',
        'DLX': 'очередь ошибок',
        'routing key': 'ключ маршрутизации',
        'publisher confirms': 'подтверждения публикации',
        'manual ack': 'ручное подтверждение обработки',
        'poison message': 'ядовитое сообщение',
        'batch reconciliation': 'пакетная сверка',
    }
    for old, new in replacements.items():
        out = out.replace(old, new)
    regex_fixes = [
        (r'Перерешать кейс', 'Повторно решить кейс'),
        (r'после падения потребителя', 'после сбоя потребителя'),
        (r'заведите история статусов', 'заведите историю статусов'),
        (r'алерт rules', 'правила алертов'),
        (r'идемпотентная загрузка по идентификатор ([а-яё]+)', r'идемпотентная загрузка по идентификатору \1'),
        (r'свежесть данных требование к времени ответа', 'требование к свежести данных'),
        (r'ролевая модель доступа/ABAC', 'ролевая модель доступа или ABAC'),
        (r'закрыт / открыт / пробный режим', 'закрытый, открытый и пробный режимы'),
        (r'таблица входящих сообщений для дедупликации и дедупликация', 'Inbox-таблица и дедупликация'),
        (r'отставание обработки alert', 'алерт на отставание обработки'),
        (r'\s+([,.;:!?])', r'\1'),
        (r' {2,}', ' '),
    ]
    for pattern, repl in regex_fixes:
        out = re.sub(pattern, repl, out)
    return out

# Повторно полируем уже созданные элементы каталога: CASE_BY_ID строится раньше,
# поэтому правим словари на месте.
for _case in CASES:
    for _key in ("title", "track", "business_context", "learning_goal", "difficulty", "mode"):
        if isinstance(_case.get(_key), str):
            _case[_key] = _ru_sentence(_case[_key])
    for _key in ("traps", "expected_controls", "interview_questions", "next_tasks"):
        if isinstance(_case.get(_key), list):
            _case[_key] = [_ru_sentence(x) if isinstance(x, str) else x for x in _case[_key]]
CASE_BY_ID = {case["id"]: case for case in CASES}

# v8.6.47c: учебный слой должен пользоваться тем же финальным словарём,
# что и полный архитектурный отчёт.
from report import humanize_terms as _REPORT_HUMANIZE_TERMS_V8647C
humanize_terms = _REPORT_HUMANIZE_TERMS_V8647C
_PREV_RU_SENTENCE_V8647C = _ru_sentence


def _ru_sentence(text: str) -> str:
    out = _PREV_RU_SENTENCE_V8647C(text)
    out = humanize_terms(out)
    fixes = {
        'bподтверждение обработкиpressure': 'обратное давление',
        'код причиныs': 'код причины',
        'ручной разбор требование к времени ответа': 'требование к времени ручного разбора',
        'повторная попытка и компенсациях': 'повторных попытках и компенсациях',
        'событийный кейс': 'кейс на событийную архитектуру',
        'нижестоящий поток': 'нижестоящий поток',
    }
    for old, new in fixes.items():
        out = out.replace(old, new)
    out = re.sub(r'([А-Яа-яЁё])s\b', r'\1', out)
    return out

for _case in CASES:
    for _key in ("title", "track", "business_context", "learning_goal", "goal", "difficulty", "mode"):
        if isinstance(_case.get(_key), str):
            _case[_key] = _ru_sentence(_case[_key])
    for _key in ("traps", "hidden_traps", "expected_controls", "interview_questions", "next_tasks"):
        if isinstance(_case.get(_key), list):
            _case[_key] = [_ru_sentence(x) if isinstance(x, str) else x for x in _case[_key]]
CASE_BY_ID = {case["id"]: case for case in CASES}

# v8.6.47d: те же финальные правки для учебных фрагментов.
_PREV_RU_SENTENCE_V8647D = _ru_sentence

def _ru_sentence(text: str) -> str:
    out = _PREV_RU_SENTENCE_V8647D(text)
    fixes = {
        'bподтверждение обработкиward-compatible': 'обратно совместимыми',
        'bподтверждение обработки-office': 'бэк-офиса',
        'backward-compatible': 'обратно совместимыми',
        'back-office': 'бэк-офиса',
        'Temporal / workflow engine': 'Temporal / движок длительных процессов',
        'workflow engine': 'движок длительных процессов',
        'compensation': 'компенсация',
        'nullable first': 'сначала допускайте пустые значения',
        'expand → migrate → contract': 'расширить → перенести данные → сузить контракт',
        'Процесс должен иметь владелец ручных решений': 'У процесса должен быть владелец ручных решений',
        'ручной разбор целевое время ответа': 'целевое время ручного разбора',
        'целевое время ответа ручной разбор': 'целевое время ручного разбора',
    }
    for old, new in fixes.items():
        out = out.replace(old, new)
    return out

# v8.6.47e: синхронизация учебных предложений с финальным отчётным словарём.
_PREV_RU_SENTENCE_V8647E = _ru_sentence

def _ru_sentence(text: str) -> str:
    return humanize_terms(_PREV_RU_SENTENCE_V8647E(text))

# v8.6.47f: грамматическая доводка учебного текста.
_PREV_RU_SENTENCE_V8647F = _ru_sentence

def _ru_sentence(text: str) -> str:
    return humanize_terms(_PREV_RU_SENTENCE_V8647F(text))

# v8.6.47g: учебные строки через итоговую вычитку.
_PREV_RU_SENTENCE_V8647G = _ru_sentence

def _ru_sentence(text: str) -> str:
    return humanize_terms(_PREV_RU_SENTENCE_V8647G(text))

# v8.6.47h: финальная прокладка через общий словарь.
_PREV_RU_SENTENCE_V8647H = _ru_sentence

def _ru_sentence(text: str) -> str:
    return humanize_terms(_PREV_RU_SENTENCE_V8647H(text))

# v8.6.47k: повторная вычитка каталога после финального словаря.
for _case in CASES:
    for _key in ("title", "track", "business_context", "learning_goal", "goal", "difficulty", "mode"):
        if isinstance(_case.get(_key), str):
            _case[_key] = humanize_terms(_case[_key])
    for _key in ("traps", "hidden_traps", "expected_controls", "interview_questions", "next_tasks"):
        if isinstance(_case.get(_key), list):
            _case[_key] = [humanize_terms(x) if isinstance(x, str) else x for x in _case[_key]]
CASE_BY_ID = {case["id"]: case for case in CASES}

# ---------------------------------------------------------------------------
# v8.6.48: production-доводка эталонов и режима собеседования.
# ---------------------------------------------------------------------------
APP_LEARNING_VERSION = "8.6.48-reference-interview-polished"
CASE_CATALOG_VERSION = "2026-06-16-v4-reference-interview-polished"

_INTERVIEW_BASE_QUESTIONS = [
    {
        "id": "context",
        "question": "С чего вы начнёте разбор задачи и какие границы процесса зафиксируете?",
        "expected": [
            "Сначала определить участников, владельцев данных, входные и выходные события.",
            "Отделить основной бизнес-поток от аналитики, аудита и эксплуатационных действий.",
            "Зафиксировать ограничения: нагрузку, целевое время ответа, регуляторные требования и допустимые отказы.",
        ],
        "red_flags": [
            "Сразу выбирать Kafka, REST или БД без описания процесса.",
            "Не уточнять владельца статуса, контракта и данных.",
        ],
        "skill": "process",
    },
    {
        "id": "failure",
        "question": "Что произойдёт, если один из внешних или асинхронных участников временно недоступен?",
        "expected": [
            "Нужны таймауты, ограниченные повторы, очередь ошибок или карантин.",
            "Для событий нужно предусмотреть повторную обработку и защиту от дублей.",
            "Для пользователя или downstream-системы должен быть понятный статус: ожидает, требует ручного разбора или завершено ошибкой.",
        ],
        "red_flags": [
            "Бесконечные повторы без лимита.",
            "Потеря сообщения после ошибки обработки.",
        ],
        "skill": "reliability",
    },
    {
        "id": "contract",
        "question": "Как вы будете менять контракт без поломки потребителей?",
        "expected": [
            "Ввести версию схемы и правила совместимости.",
            "Использовать подход расширить → перенести данные → сузить контракт.",
            "Отделить обязательные поля от расширяемых и договориться о владельце контракта.",
        ],
        "red_flags": [
            "Удалять или переименовывать поля одним релизом.",
            "Не иметь владельца контракта и тестов совместимости.",
        ],
        "skill": "contracts",
    },
]


def _case_keywords(case: Dict[str, Any]) -> List[str]:
    words: List[str] = []
    for c in case.get("expected_controls", []) or []:
        words.extend(str(x).lower() for x in c.get("keywords", []) or [])
        words.append(str(c.get("label", "")).lower())
    for t in case.get("hidden_traps", []) or []:
        words.extend(re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9_]{4,}", str(t).lower()))
    return sorted({w for w in words if w})


def interview_pack(case_id: str) -> Dict[str, Any]:
    """Возвращает собеседовательный пакет по кейсу: вопросы, ожидаемые тезисы,
    красные флаги, критерии оценки и рекомендации по ответу.
    """
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    questions: List[Dict[str, Any]] = []
    questions.extend(deepcopy(_INTERVIEW_BASE_QUESTIONS))
    for i, control in enumerate(case.get("expected_controls", [])[:7], start=1):
        label = _ru_sentence(control.get("label", "контроль не указан")).rstrip(".")
        why = _ru_sentence(control.get("why", "этот контроль снижает риск промышленного запуска")).rstrip(".")
        skill = control.get("skill") or "process"
        questions.append({
            "id": f"control_{i}",
            "question": f"Как в вашем решении закрывается контроль «{label}»?",
            "expected": [
                f"Назвать сам контроль: {label}.",
                f"Объяснить риск: {why}.",
                "Показать, в каком шаге процесса этот контроль реализован и кто за него отвечает.",
                "Назвать проверку, по которой будет видно, что контроль действительно работает.",
            ],
            "red_flags": [
                "Контроль только упомянут, но не привязан к шагу процесса.",
                "Не указано, как проверить контроль на тестировании или в эксплуатации.",
            ],
            "skill": skill,
            "keywords": control.get("keywords", []),
        })
    return {
        "ok": True,
        "case_id": case_id,
        "title": case.get("title"),
        "level": case.get("level"),
        "timebox": case.get("timebox", "45 минут"),
        "opening_prompt": (
            "Представьте, что вы на собеседовании. За 5–7 минут объясните границы процесса, "
            "ключевые решения, риски отказов, контракты, данные и эксплуатационные проверки."
        ),
        "questions": questions,
        "rubric": [
            "Ответ на Middle должен объяснять процесс, участников, sync/async выбор и базовые отказы.",
            "Ответ на Middle+ должен явно покрывать идемпотентность, порядок, replay, контракты и наблюдаемость.",
            "Ответ на Senior должен показывать компромиссы: MVP-вариант, production-вариант, legacy-ограничения и план миграции.",
        ],
        "global_red_flags": [
            "Кандидат выбирает технологию до описания процесса и гарантий.",
            "Нет владельца данных, статуса или контракта.",
            "Нет сценария повтора после сбоя и защиты от дублей.",
            "Аналитика или аудит становятся блокирующей зависимостью основного бизнес-потока без необходимости.",
        ],
    }


def reference_variants(case_id: str) -> Dict[str, Any]:
    """Строит полезные эталонные варианты: промышленный, MVP и вариант под legacy.
    Это не один «единственно правильный ответ», а набор допустимых архитектурных компромиссов.
    """
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    payload = case.get("payload") or {}
    controls = case.get("expected_controls", []) or []
    steps = payload.get("steps", []) or []
    production_steps = _reference_scheme_lines(payload)
    must_have = [
        _ru_sentence(f"{c.get('label')}: {c.get('why')}")
        for c in controls[:8]
    ]
    mvp_kept = []
    mvp_deferred = []
    for c in controls:
        label = _ru_sentence(c.get("label", "")).rstrip(".")
        skill = c.get("skill")
        if skill in {"idempotency", "reliability", "contracts"}:
            mvp_kept.append(f"Оставить обязательно: {label}.")
        else:
            mvp_deferred.append(f"Можно упростить на MVP, но зафиксировать как риск: {label}.")
    if not mvp_kept:
        mvp_kept = ["Оставить идемпотентность, ограниченные повторы, журнал ошибок и владельца контракта."]
    if not mvp_deferred:
        mvp_deferred = ["Можно временно упростить аналитику, ручные отчёты и часть наблюдаемости, если это не влияет на основной поток."]
    legacy_notes = [
        "Вынесите адаптацию legacy-форматов в отдельный anti-corruption layer или интеграционный адаптер.",
        "Не протаскивайте legacy-статусы и технические коды напрямую в доменную модель без нормализации.",
        "Добавьте сверку, ручной разбор и журнал соответствия внешних и внутренних идентификаторов.",
    ]
    acceptance = [
        "Есть тест на повтор одного и того же события или команды: дубль не создаёт вторую бизнес-операцию.",
        "Есть тест на недоступность внешней системы: процесс получает управляемый статус, а не зависает бесконечно.",
        "Есть тест совместимости контракта: старый потребитель не ломается от расширения события или ответа.",
        "Есть эксплуатационный сценарий: оператор видит очередь ошибок, причину отказа и способ безопасной повторной обработки.",
    ]
    return {
        "ok": True,
        "case_id": case_id,
        "title": case.get("title"),
        "production": {
            "title": "Промышленный эталон",
            "description": "Вариант для реального запуска: сохраняет порядок, идемпотентность, контракты, восстановление после ошибок и наблюдаемость.",
            "steps": production_steps,
            "must_have_controls": must_have,
        },
        "mvp": {
            "title": "Допустимый MVP-вариант",
            "description": "Вариант для раннего запуска, где нельзя выбросить гарантии корректности, но можно отложить часть удобств и автоматизации.",
            "keep": mvp_kept[:6],
            "defer": mvp_deferred[:6],
        },
        "legacy": {
            "title": "Вариант при legacy-ограничениях",
            "description": "Компромисс, если часть систем не поддерживает современные контракты, события или быстрые изменения.",
            "notes": legacy_notes,
        },
        "acceptance_criteria": acceptance,
        "route_count": len(steps),
        "control_count": len(controls),
    }


def _assess_interview_answer(case: Dict[str, Any], answer_text: str, ev: Dict[str, Any]) -> Dict[str, Any]:
    text = humanize_terms(str(answer_text or "")).lower()
    pack = interview_pack(case["id"])
    expected_keywords = _case_keywords(case)
    base_words = [
        "процесс", "участник", "контракт", "идемпотент", "дуб", "повтор", "таймаут",
        "ошиб", "монитор", "correlation", "trace", "верси", "данн", "статус",
    ]
    coverage_hits = []
    for kw in expected_keywords + base_words:
        if kw and kw.lower() in text and kw not in coverage_hits:
            coverage_hits.append(kw)
    question_count = len((pack or {}).get("questions", [])) or 1
    # Ограничиваем вклад текста: архитектурный payload важнее, но устный ответ
    # показывает, умеет ли пользователь объяснять решение на собеседовании.
    answer_score = min(10.0, round(2.0 + len(coverage_hits) * 0.55, 1)) if text.strip() else 0.0
    red_flags = []
    if text.strip() and not any(x in text for x in ("идемпот", "дуб", "повтор")):
        red_flags.append("В устном ответе не раскрыта защита от дублей и повторной обработки.")
    if text.strip() and not any(x in text for x in ("контракт", "схем", "верси")):
        red_flags.append("В устном ответе не раскрыто управление контрактом и его изменениями.")
    if text.strip() and not any(x in text for x in ("таймаут", "ошиб", "dlq", "очеред", "карантин")):
        red_flags.append("В устном ответе слабо раскрыт сценарий отказов.")
    advice = []
    if answer_score < 6:
        advice.append("Стройте ответ по структуре: процесс → участники → данные → синхронность/асинхронность → отказы → контракты → эксплуатация.")
    if red_flags:
        advice.append("Отдельно проговорите идемпотентность, контракты, повторную обработку и наблюдаемость: это типовые вопросы на Middle+/Senior.")
    if not advice:
        advice.append("Ответ выглядит связным. Усильте его компромиссами: что можно упростить на MVP и что нельзя выпускать без production-контролей.")
    return {
        "answer_score": answer_score,
        "matched_keywords": coverage_hits[:20],
        "question_count": question_count,
        "red_flags": red_flags,
        "advice": advice,
    }


# Сохраняем ссылку на предыдущую реализацию на случай регрессий.
_PREV_EVALUATE_LEARNING_SOLUTION_V8648 = evaluate_learning_solution


def evaluate_learning_solution(case_id: str, payload: Dict[str, Any], mode: str = "learning", answer_text: str = "") -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    mode = str(mode or "learning")
    base = analyze(payload)
    if not base.get("ok"):
        validation = base.get("errors", [])
        ev = {
            "ok": True,
            "case": {k: v for k, v in case.items() if k != "payload"},
            "base_ok": False,
            "mode": mode,
            "summary": "Схема не прошла базовую валидацию. Сначала исправьте структуру участников, связей и зависимостей.",
            "validation_errors": validation,
            "learning_score": 0.0,
            "learning_level": "невалидная схема: разбор невозможен до исправления структуры",
            "skill_scores": {k: {"name": name, "score": 0, "evidence": ["Базовая схема невалидна"]} for k, name in SKILLS.items()},
            "control_hits": [],
            "control_misses": case.get("expected_controls", []),
            "reference_variants": reference_variants(case_id),
            "interview_pack": interview_pack(case_id),
        }
        ev["report_markdown"] = learning_markdown(case, ev, None, mode, validation_errors=validation)
        return ev

    hits, misses = _control_hits(case, base)
    skills = _skill_scores(case, base, misses)
    avg = round(sum(x["score"] for x in skills.values()) / len(skills), 1)
    verdict = base.get("verdict", {})
    critical = verdict.get("group_counts", {}).get("critical", verdict.get("counts", {}).get("critical", 0))
    high = verdict.get("group_counts", {}).get("high", verdict.get("counts", {}).get("high", 0))
    interview_assessment = _assess_interview_answer(case, answer_text, {"skill_scores": skills}) if mode == "interview" else None
    if mode == "interview":
        if misses:
            avg = round(max(0.0, avg - min(1.2, len(misses) * 0.25)), 1)
        if answer_text.strip():
            avg = round((avg * 0.72) + (float(interview_assessment.get("answer_score") or 0) * 0.28), 1)
        else:
            avg = round(max(0.0, avg - 0.8), 1)
    learning_level = _level(avg, critical, high)
    strengths = [f"Найден контроль: {h.get('label')}." for h in hits[:8]]
    if base.get("verdict", {}).get("verdict") == "green":
        strengths.append("Базовое ядро не видит high/critical блокеров: решение можно обсуждать как готовый к промышленному запуску черновик.")
    if not strengths:
        strengths.append("Решение построено и прошло базовый анализ, но ключевые учебные контроли кейса выражены слабо.")
    gaps = [
        {
            "title": m.get("label"),
            "why": m.get("why"),
            "skill": SKILLS.get(m.get("skill"), m.get("skill")),
            "fix": f"Явно добавьте в шаги или компенсации: {', '.join(m.get('keywords', [])[:4])}.",
        }
        for m in misses[:8]
    ]
    result = {
        "ok": True,
        "case": {k: v for k, v in case.items() if k != "payload"},
        "base_ok": True,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "base_verdict": verdict,
        "learning_score": avg,
        "learning_level": learning_level,
        "skill_scores": skills,
        "control_hits": hits,
        "control_misses": misses,
        "strengths": strengths,
        "gaps": gaps,
        "next_tasks": _next_tasks(case, misses, skills),
        "reference_payload": case.get("payload") if mode in ("reference", "interview_review") else None,
        "base_result": base,
        "reference_variants": reference_variants(case_id),
        "interview_pack": interview_pack(case_id),
        "interview_answer_assessment": interview_assessment,
    }
    result["reference_comparison"] = compare_to_reference(case, payload, result)
    result["hints_available"] = [1, 2, 3, 4]
    result["report_markdown"] = learning_markdown(case, result, base, mode)
    return result


def _md_nested_list(items: Iterable[Any], prefix: str = "") -> List[str]:
    lines: List[str] = []
    for item in items or []:
        if isinstance(item, str):
            lines.append(f"{prefix}- {_ru_sentence(item)}")
        else:
            lines.append(f"{prefix}- {_ru_sentence(str(item))}")
    return lines


def _reference_variants_markdown(ref: Dict[str, Any]) -> List[str]:
    if not ref or not ref.get("ok"):
        return ["Эталонные варианты недоступны для этого кейса."]
    out: List[str] = []
    prod = ref.get("production") or {}
    out.append(f"### {prod.get('title', 'Промышленный эталон')}")
    out.append(_ru_sentence(prod.get("description")))
    out.append("")
    out.append("**Шаги эталона:**")
    for line in prod.get("steps", [])[:12]:
        out.append(f"- {line}")
    out.append("")
    out.append("**Обязательные контроли:**")
    out.extend(_md_nested_list(prod.get("must_have_controls", [])))
    out.append("")
    mvp = ref.get("mvp") or {}
    out.append(f"### {mvp.get('title', 'Допустимый MVP-вариант')}")
    out.append(_ru_sentence(mvp.get("description")))
    out.append("**Нельзя выбрасывать даже на MVP:**")
    out.extend(_md_nested_list(mvp.get("keep", [])))
    out.append("**Можно упростить, если риск явно зафиксирован:**")
    out.extend(_md_nested_list(mvp.get("defer", [])))
    out.append("")
    legacy = ref.get("legacy") or {}
    out.append(f"### {legacy.get('title', 'Вариант при legacy-ограничениях')}")
    out.append(_ru_sentence(legacy.get("description")))
    out.extend(_md_nested_list(legacy.get("notes", [])))
    out.append("")
    out.append("### Критерии приёмки")
    out.extend(_md_nested_list(ref.get("acceptance_criteria", [])))
    return out


def _interview_markdown(pack: Dict[str, Any], assessment: Dict[str, Any] | None = None) -> List[str]:
    if not pack or not pack.get("ok"):
        return ["Собеседовательный пакет недоступен для этого кейса."]
    out: List[str] = []
    out.append(_ru_sentence(pack.get("opening_prompt")))
    out.append("")
    out.append("### Вопросы интервьюера и ожидаемые тезисы")
    for q in (pack.get("questions") or [])[:12]:
        out.append(f"**Вопрос:** {_ru_sentence(q.get('question'))}")
        out.append("Ожидается в сильном ответе:")
        out.extend(_md_nested_list(q.get("expected", [])))
        out.append("Красные флаги:")
        out.extend(_md_nested_list(q.get("red_flags", [])))
        out.append("")
    out.append("### Рубрика оценки")
    out.extend(_md_nested_list(pack.get("rubric", [])))
    out.append("")
    out.append("### Общие красные флаги")
    out.extend(_md_nested_list(pack.get("global_red_flags", [])))
    if assessment:
        out.append("")
        out.append("### Оценка устного ответа")
        out.append(f"- Оценка объяснения: **{assessment.get('answer_score', 0)}/10**.")
        out.append(f"- Найденные смысловые маркеры: {', '.join(assessment.get('matched_keywords', [])[:12]) or 'нет'}.")
        if assessment.get("red_flags"):
            out.append("- Что насторожило бы интервьюера:")
            out.extend(_md_nested_list(assessment.get("red_flags", []), prefix="  "))
        out.append("- Как усилить ответ:")
        out.extend(_md_nested_list(assessment.get("advice", []), prefix="  "))
    return out


def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    """v8.6.48: учебный отчёт с полноценными эталонами и собеседованием."""
    out: List[str] = []
    out.append(f"# Учебный разбор: {humanize_terms(case['title'])}")
    out.append("")
    out.append(f"**Уровень кейса:** {humanize_terms(case.get('level'))}  ")
    out.append(f"**Трек:** {humanize_terms(case.get('track'))}  ")
    out.append(f"**Цель:** {_ru_sentence(case.get('goal'))}  ")
    out.append(f"**Режим:** {_mode_label(mode)}")
    out.append("")
    if validation_errors:
        out.append("## 1. Схема пока невалидна")
        out.append(_ru_list(validation_errors))
        out.append("")
        out.append("Сначала исправьте базовую структуру: участники должны существовать, зависимости должны ссылаться на реальные шаги, а циклов в цепочке быть не должно.")
        if ev:
            out.append("")
            out.append("## 2. Эталонные ориентиры")
            out.extend(_reference_variants_markdown(ev.get("reference_variants") or reference_variants(case["id"])))
            out.append("")
            out.append("## 3. Как это спросили бы на собеседовании")
            out.extend(_interview_markdown(ev.get("interview_pack") or interview_pack(case["id"])))
        return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

    assert ev is not None and base is not None
    bv = ev.get("base_verdict") or {}
    out.append("## 1. Итоговая оценка")
    out.append(f"- Учебная оценка: **{ev['learning_score']}/10**.")
    out.append(f"- Уровень решения: **{_ru_sentence(ev['learning_level'])}**")
    out.append(f"- Вывод архитектурного ядра: **{_ru_sentence(bv.get('verdict', 'не рассчитан')).rstrip('.')}**, {bv.get('score', '—')}/10.")
    out.append("")
    out.append("## 2. Что пользователь должен уметь объяснить")
    out.append("Хорошее решение должно быть не только нарисовано, но и объяснено. На ревью или собеседовании важно проговорить границы процесса, владельцев данных, гарантии доставки, обработку дублей, контракты, восстановление после ошибок и наблюдаемость.")
    out.append("")
    out.append("## 3. Профиль навыков")
    for _, data in ev["skill_scores"].items():
        out.append(f"- **{humanize_terms(data['name'])}**: {data['score']}/10.")
        for e in data.get("evidence", [])[:2]:
            out.append(f"  - {_ru_sentence(e)}")
    out.append("")
    out.append("## 4. Что сделано правильно")
    out.append(_ru_list(ev.get("strengths", [])))
    out.append("")
    comp = ev.get("reference_comparison") or {}
    out.append("## 5. Сравнение с эталоном")
    out.append(f"- Совпавших маршрутов: **{comp.get('matched_route_count', 0)} / {comp.get('reference_route_count', 0)}**.")
    out.append(f"- Покрытые способы взаимодействия: {_display_channels(comp.get('channel_coverage') or [])}.")
    out.append(f"- Недостающие способы из эталона: {_display_channels(comp.get('missing_channels') or [])}.")
    out.append(f"- Найдено учебных контролей: **{comp.get('control_hit_count', 0)}**; пропущено: **{comp.get('control_miss_count', 0)}**.")
    out.append("")
    out.append("## 6. Что мешает готовности к промышленному запуску")
    if ev.get("gaps"):
        for g in ev["gaps"]:
            out.append(f"### {_ru_sentence(g['title']).rstrip('.')}")
            out.append(f"**Почему важно:** {_ru_sentence(g.get('why'))}")
            out.append(f"**Как исправить:** {_ru_sentence(g.get('fix'))}")
            out.append("")
    else:
        out.append("Ключевые учебные контроли кейса найдены. Перед реальным выпуском всё равно проверьте нефункциональные требования, контракты, нагрузку, безопасность и эксплуатационные сценарии.")
        out.append("")
    out.append("## 7. Полноценные эталоны")
    out.extend(_reference_variants_markdown(ev.get("reference_variants") or reference_variants(case["id"])))
    out.append("")
    out.append("## 8. Блок собеседования")
    out.extend(_interview_markdown(ev.get("interview_pack") or interview_pack(case["id"]), ev.get("interview_answer_assessment")))
    out.append("")
    out.append("## 9. Типовые ловушки этого кейса")
    out.append(_ru_list(case.get("hidden_traps", [])))
    out.append("")
    out.append("## 10. Следующие задания")
    out.append(_ru_list(ev.get("next_tasks", [])))
    out.append("")
    out.append("## 11. Полный архитектурный отчёт ядра")
    out.append("")
    out.append(markdown_report(base))
    return "\n".join(humanize_terms(x) for x in out).strip() + "\n"


def learning_result_html(ev: Dict[str, Any]) -> str:
    if not ev.get("ok"):
        return "<div class='err'>" + escape("; ".join(ev.get("errors", []))) + "</div>"
    if not ev.get("base_ok", True):
        errs = "".join(f"<li>{escape(x)}</li>" for x in ev.get("validation_errors", []))
        return f"<div class='finding critical'><h3>Схема невалидна</h3><ul>{errs}</ul></div>"
    skills = ev.get("skill_scores", {})
    skill_cards = []
    for _, s in skills.items():
        evs = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in s.get("evidence", [])[:3])
        skill_cards.append(f"<div class='learn-skill'><b>{escape(s['name'])}</b><span>{s['score']}/10</span><ul>{evs}</ul></div>")
    gaps = ev.get("gaps", [])
    gap_html = "".join(
        f"<div class='finding high'><h3>{escape(_ru_sentence(g['title']).rstrip('.'))}</h3><p><b>Почему важно:</b> {escape(_ru_sentence(g.get('why','')))}</p><p><b>Как исправить:</b> {escape(_ru_sentence(g.get('fix','')))}</p></div>"
        for g in gaps
    ) or "<p>Ключевые учебные контроли найдены. Проверьте детали контрактов и эксплуатационные ограничения.</p>"
    tasks = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ev.get("next_tasks", []))
    strengths = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ev.get("strengths", []))
    comp = ev.get("reference_comparison") or {}
    ass = ev.get("interview_answer_assessment") or {}
    interview_html = ""
    if ev.get("mode") == "interview":
        rf = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ass.get("red_flags", [])) or "<li>Критичных красных флагов в устном объяснении не найдено.</li>"
        adv = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ass.get("advice", []))
        interview_html = f"<h3>Оценка собеседования</h3><div class='learn-compare'><b>Устное объяснение:</b> {escape(str(ass.get('answer_score', 0)))} / 10<br><b>Красные флаги:</b><ul>{rf}</ul><b>Как усилить ответ:</b><ol>{adv}</ol></div>"
    compare_html = f"<div class='learn-compare'><b>Сравнение с эталоном:</b> маршруты {comp.get('matched_route_count',0)}/{comp.get('reference_route_count',0)}, найдено контролей {comp.get('control_hit_count',0)}, пропущено {comp.get('control_miss_count',0)}.</div>"
    return f"""
    <div class='learn-verdict'>
      <h2>{escape(str(ev.get('learning_score')))} / 10 · {escape(ev.get('learning_level',''))}</h2>
      <p>Архитектурная оценка ядра: {escape(str((ev.get('base_verdict') or {}).get('verdict','—')))} · {(ev.get('base_verdict') or {}).get('score','—')}/10</p>
    </div>
    {compare_html}
    {interview_html}
    <h3>Профиль навыков</h3><div class='learn-skills'>{''.join(skill_cards)}</div>
    <h3>Что сделано правильно</h3><ul>{strengths}</ul>
    <h3>Что доработать</h3>{gap_html}
    <h3>Следующие задания</h3><ol>{tasks}</ol>
    """

# v8.6.48b: итоговая структура учебного отчёта совместима со старыми
# language-verifier'ами и при этом содержит полноценные эталоны/интервью.
def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    out: List[str] = []
    out.append(f"# Учебный разбор: {humanize_terms(case['title'])}")
    out.append("")
    out.append(f"**Уровень кейса:** {humanize_terms(case.get('level'))}  ")
    out.append(f"**Трек:** {humanize_terms(case.get('track'))}  ")
    out.append(f"**Цель:** {_ru_sentence(case.get('goal'))}  ")
    out.append(f"**Режим:** {_mode_label(mode)}")
    out.append("")
    if validation_errors:
        out.append("## 1. Схема пока невалидна")
        out.append(_ru_list(validation_errors))
        out.append("")
        out.append("Сначала исправьте базовую структуру: участники должны существовать, зависимости должны ссылаться на реальные шаги, а циклов в цепочке быть не должно.")
        out.append("")
        out.append("## 8. Эталонная схема решения")
        out.extend(_reference_variants_markdown((ev or {}).get("reference_variants") or reference_variants(case["id"])))
        out.append("")
        out.append("## 9. Блок собеседования")
        out.extend(_interview_markdown((ev or {}).get("interview_pack") or interview_pack(case["id"])))
        return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

    assert ev is not None and base is not None
    bv = ev.get("base_verdict") or {}
    out.append("## 1. Итоговая оценка")
    out.append(f"- Учебная оценка: **{ev['learning_score']}/10**.")
    out.append(f"- Уровень решения: **{_ru_sentence(ev['learning_level'])}**")
    out.append(f"- Вывод архитектурного ядра: **{_ru_sentence(bv.get('verdict', 'не рассчитан')).rstrip('.')}**, {bv.get('score', '—')}/10.")
    out.append("- На ревью важно уметь объяснить не только выбранные технологии, но и гарантии: идемпотентность, порядок, восстановление после ошибок, контракты и эксплуатацию.")
    out.append("")
    out.append("## 2. Профиль навыков")
    for _, data in ev["skill_scores"].items():
        out.append(f"- **{humanize_terms(data['name'])}**: {data['score']}/10.")
        for e in data.get("evidence", [])[:2]:
            out.append(f"  - {_ru_sentence(e)}")
    out.append("")
    out.append("## 3. Что сделано правильно")
    out.append(_ru_list(ev.get("strengths", [])))
    out.append("")
    comp = ev.get("reference_comparison") or {}
    out.append("## 4. Сравнение с эталоном")
    out.append(f"- Совпавших маршрутов: **{comp.get('matched_route_count', 0)} / {comp.get('reference_route_count', 0)}**.")
    out.append(f"- Покрытые способы взаимодействия: {_display_channels(comp.get('channel_coverage') or [])}.")
    out.append(f"- Недостающие способы из эталона: {_display_channels(comp.get('missing_channels') or [])}.")
    out.append(f"- Найдено учебных контролей: **{comp.get('control_hit_count', 0)}**; пропущено: **{comp.get('control_miss_count', 0)}**.")
    out.append("")
    out.append("## 5. Что мешает готовности к промышленному запуску")
    if ev.get("gaps"):
        for g in ev["gaps"]:
            out.append(f"### {_ru_sentence(g['title']).rstrip('.')}")
            out.append(f"**Почему важно:** {_ru_sentence(g.get('why'))}")
            out.append(f"**Как исправить:** {_ru_sentence(g.get('fix'))}")
            out.append("")
    else:
        out.append("Ключевые учебные контроли кейса найдены. Перед реальным выпуском всё равно проверьте нефункциональные требования, контракты, нагрузку, безопасность и эксплуатационные сценарии.")
        out.append("")
    out.append("## 6. Типовые ловушки этого кейса")
    out.append(_ru_list(case.get("hidden_traps", [])))
    out.append("")
    out.append("## 7. Следующие задания")
    out.append(_ru_list(ev.get("next_tasks", [])))
    out.append("")
    out.append("## 8. Эталонная схема решения")
    out.append("Эталон — это не один жёсткий ответ, а набор ориентиров: промышленный вариант, допустимый MVP и компромисс для legacy-среды.")
    out.append("")
    out.extend(_reference_variants_markdown(ev.get("reference_variants") or reference_variants(case["id"])))
    out.append("")
    out.append("## 9. Блок собеседования")
    out.extend(_interview_markdown(ev.get("interview_pack") or interview_pack(case["id"]), ev.get("interview_answer_assessment")))
    out.append("")
    out.append("## 10. Полный архитектурный отчёт ядра")
    out.append("")
    out.append(markdown_report(base))
    return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

# ---------------------------------------------------------------------------
# v8.6.49: пользовательский аудит. Исправления доверия тренажёра:
# - учебные контроли засчитываются только из решения пользователя / устного ответа;
# - эталонный payload даёт высокий учебный score, если обязательные контроли явно описаны;
# - слабое решение больше не получает «найденные» Outbox/DLQ/versioning из рекомендаций ядра;
# - интервью оценивает структуру ответа, а не только отдельные ключевые слова;
# - учебный отчёт начинается с короткого резюме, а полный разбор остаётся ниже.
# ---------------------------------------------------------------------------
APP_LEARNING_VERSION = "8.6.49-user-trust-polished"
CASE_CATALOG_VERSION = "2026-06-16-v5-user-trust-polished"


def _payload_user_evidence(payload: Dict[str, Any], answer_text: str = "") -> str:
    """Текст только из решения пользователя. Важно: сюда нельзя добавлять findings,
    patterns или рекомендации ядра, иначе тренажёр снова начнёт хвалить то, чего
    пользователь не сделал.
    """
    p = payload or {}
    parts: List[str] = []
    meta = p.get("meta") or {}
    for k in ("name", "entity", "goal", "description", "constraints", "lookup_keys", "statuses", "fields"):
        parts.append(str(meta.get(k, "")))
    for sys in p.get("systems", []) or []:
        parts.append(str(sys.get("name", "")))
        parts.append(str(sys.get("role", "")))
    for step in p.get("steps", []) or []:
        for k in (
            "name", "source_system", "system", "target_system", "channel", "blocking", "retry",
            "idempotency", "timeout_ms", "writes_entity", "compensation", "failure_policy",
            "data_in", "data_out", "depends_on",
        ):
            parts.append(str(step.get(k, "")))
    parts.append(str(answer_text or ""))
    return humanize_terms("\n".join(parts)).lower()


def _has_re(rx: str, text: str) -> bool:
    return bool(re.search(rx, text, flags=re.IGNORECASE | re.UNICODE))


def _external_steps_with_timeout(payload: Dict[str, Any]) -> bool:
    systems = {str(s.get("name", "")).lower(): str(s.get("role", "")).lower() for s in (payload or {}).get("systems", []) or []}
    for step in (payload or {}).get("steps", []) or []:
        target = str(step.get("target_system") or step.get("system") or "").lower()
        role = systems.get(target, "")
        if role in {"external", "legacy"} or _has_re(r"бки|fraud|partner|партн|external|legacy|внеш", target):
            if str(step.get("timeout_ms") or "").strip() or _has_re(r"timeout|тайм.?аут|deadline|circuit.?breaker|rate.?limit|ограниченн", str(step.get("compensation") or "")):
                return True
    return False


def _control_found_in_user_solution(control: Dict[str, Any], payload: Dict[str, Any], answer_text: str = "") -> Tuple[bool, str]:
    text = _payload_user_evidence(payload, answer_text)
    cid = str(control.get("id") or "").lower()
    label = str(control.get("label") or "")
    source = "payload_or_answer"
    # Частные правила нужны, чтобы applicationId или сама Kafka не считались
    # «ключом партиционирования», а слово retry — полноценным DLQ/replay.
    if cid in {"outbox"} or _has_re(r"outbox|исходящ", label):
        return _has_re(r"\boutbox\b|таблиц[аы]? исходящ|исходящ[а-я\s-]*сообщ", text), source
    if cid in {"inbox"} or _has_re(r"\binbox\b", label):
        return _has_re(r"\binbox\b|входящ[а-я\s-]*сообщ|дедуп|dedup|event.?id.*unique|уникальн.*event", text), source
    if cid in {"kafka_key", "ordering_key", "partition_key"} or _has_re(r"ключ kafka|partition|поряд", label):
        return _has_re(r"partition\s*key|ключ\s+(kafka|партиц|поряд)|партиционир.*(application|entity|order|contract|document|operation|id)|partition.*(application|entity|order|contract|document|operation)", text), source
    if cid in {"dlq_replay", "replay", "dlq"} or _has_re(r"dlq|replay|карантин|ошиб", label):
        return _has_re(r"\bdlq\b|dead.?letter|карантин|replay|переобработ|повторн[а-я\s-]*обработ|ручн[а-я\s-]*разбор|parking", text), source
    if cid in {"timeouts", "timeout_budget"} or _has_re(r"таймаут|timeout|врем", label):
        return _external_steps_with_timeout(payload) or _has_re(r"timeout|тайм.?аут|deadline|circuit.?breaker|rate.?limit|ограниченн[а-я\s-]*повтор|ограниченн[а-я\s-]*ожидан|budget", text), source
    if cid in {"versioning", "contract_owner"} or _has_re(r"верс|контракт|schema", label):
        return _has_re(r"schema.?version|event.?version|payload.?version|\bversion\b|верси[яи]|версионир|schema registry|контракт.*(владел|верс|совмест)|владел.*контракт|backward compatibility|совместим", text), source
    if cid in {"mapping"} or _has_re(r"соответств|mapping|external", label):
        return _has_re(r"external.?id.*internal.?id|internal.?id.*external.?id|mapping|маппинг|соответств.*(внешн|внутр)|внешн.*внутр", text), source
    if cid in {"status_model"} or _has_re(r"статус", label):
        return _has_re(r"статусн|status.?model|unknown|manual.?review|ручн[а-я\s-]*разбор|waiting|needs_manual_review|state.?machine|workflow", text), source
    if cid in {"partial_policy"} or _has_re(r"частич|partial", label):
        return _has_re(r"partial|частич|fallback|деградац|best.?effort|manual.?review|ручн[а-я\s-]*разбор|политик[а-я\s-]*частич", text), source
    if cid in {"quality"} or _has_re(r"quality|checksum", label):
        return _has_re(r"quality|checksum|контрольн[а-я\s-]*сумм|карантин|reject report|провер[каи].*кач", text), source
    if cid in {"freshness"} or _has_re(r"freshness|lag", label):
        return _has_re(r"freshness|lag|отставан|актуальн|sla.*данн|данн.*sla", text), source
    keywords = [str(k).lower().strip() for k in control.get("keywords", []) if str(k).strip()]
    found = any(k in text for k in keywords)
    return found, source


def _control_hits(case: Dict[str, Any], payload_or_res: Dict[str, Any], answer_text: str = "") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """v8.6.49: контроль засчитывается только по пользовательскому решению.

    Сохраняем обратную совместимость: старые verifier'ы могли передавать сюда
    результат analyze(). Если это result, пытаемся взять вложенную модель, но в
    новых путях evaluate_learning_solution всегда передаёт исходный payload.
    """
    candidate = payload_or_res or {}
    payload = candidate if "steps" in candidate or "meta" in candidate else (candidate.get("payload") or {})
    hits: List[Dict[str, Any]] = []
    misses: List[Dict[str, Any]] = []
    for control in case.get("expected_controls", []) or []:
        found, source = _control_found_in_user_solution(control, payload, answer_text)
        item = {**control, "found": bool(found), "source": source if found else "not_found"}
        (hits if found else misses).append(item)
    return hits, misses


def _skill_scores(case: Dict[str, Any], res: Dict[str, Any], misses: List[Dict[str, Any]], hits: List[Dict[str, Any]] | None = None) -> Dict[str, Dict[str, Any]]:
    hits = hits or []
    raw_scores = {k: 7.0 for k in SKILLS}
    evidence = {k: [] for k in SKILLS}
    for skill in case.get("skills", []):
        if skill in raw_scores:
            raw_scores[skill] = 7.6
    for h in hits:
        skill = h.get("skill") or "process"
        if skill in raw_scores:
            raw_scores[skill] = min(9.6, raw_scores[skill] + 0.75)
            evidence[skill].append(f"Пользователь явно указал контроль: {h.get('label')}.")
    for miss in misses:
        skill = miss.get("skill") or "process"
        if skill in raw_scores:
            raw_scores[skill] = max(0.0, raw_scores[skill] - 1.8)
            evidence[skill].append(f"Не найден контроль в решении пользователя: {miss.get('label')}.")
    # Реальные findings ядра учитываем, но мягче: это замечания к архитектуре,
    # а не доказательство отсутствия учебного контроля, если пользователь его описал.
    for f in res.get("findings", []) or []:
        sev = f.get("severity", "medium")
        if sev not in {"critical", "high", "medium"}:
            continue
        skill = _finding_skill(f)
        penalty = {"critical": 1.15, "high": 0.35, "medium": 0.10}.get(sev, 0.0)
        raw_scores[skill] = max(0.0, raw_scores[skill] - penalty)
        if sev in {"critical", "high"}:
            evidence[skill].append(f"{SEVERITY_RU.get(sev, sev)}: {_ru_sentence(f.get('title')).rstrip('.')}")
    return {
        k: {"name": SKILLS[k], "score": round(max(0.0, min(10.0, v)), 1), "evidence": evidence[k][:5]}
        for k, v in raw_scores.items()
    }


def _interview_dimension_hits(text: str) -> Dict[str, bool]:
    t = humanize_terms(text or "").lower()
    return {
        "process": _has_re(r"границ|процесс|участник|поток|сценар|этап", t),
        "data": _has_re(r"данн|сущност|статус|id|идентификатор|хранилищ|бд", t),
        "sync_async": _has_re(r"синхрон|асинхрон|kafka|очеред|событи|rest|grpc", t),
        "failure": _has_re(r"ошиб|отказ|timeout|тайм.?аут|dlq|карантин|replay|fallback|circuit", t),
        "idempotency": _has_re(r"идемпотент|дубл|повтор|partition|ключ|event.?id|inbox|outbox", t),
        "contracts": _has_re(r"контракт|schema|version|верси|совместим|envelope", t),
        "operations": _has_re(r"монитор|trace|correlation|лог|alert|lag|sla|метрик|наблюдаем", t),
        "tradeoffs": _has_re(r"mvp|production|компромисс|legacy|упрост|нельзя", t),
    }


def _assess_interview_answer(case: Dict[str, Any], answer_text: str, ev: Dict[str, Any]) -> Dict[str, Any]:
    text = humanize_terms(str(answer_text or "")).lower().strip()
    if not text:
        return {
            "answer_score": 0.0,
            "matched_keywords": [],
            "dimension_hits": {},
            "red_flags": ["Пользователь не дал устное объяснение решения."],
            "advice": ["Дайте ответ по структуре: процесс → участники → данные → sync/async → отказы → идемпотентность → контракты → эксплуатация → компромиссы."],
        }
    dims = _interview_dimension_hits(text)
    case_keywords = _case_keywords(case)
    matched = []
    for kw in case_keywords:
        if kw and kw in text and kw not in matched:
            matched.append(kw)
    dim_score = sum(1 for v in dims.values() if v) / max(1, len(dims))
    keyword_score = min(1.0, len(matched) / 8.0)
    answer_score = round((dim_score * 7.0) + (keyword_score * 3.0), 1)
    red_flags: List[str] = []
    if not dims.get("process"):
        red_flags.append("Ответ не начинается с границ процесса и участников.")
    if not dims.get("failure"):
        red_flags.append("В ответе слабо раскрыты отказы, таймауты и восстановление.")
    if not dims.get("idempotency"):
        red_flags.append("В ответе не раскрыта защита от дублей, повторов и нарушения порядка.")
    if not dims.get("contracts"):
        red_flags.append("В ответе не раскрыто управление контрактом и его изменениями.")
    if not dims.get("operations"):
        red_flags.append("В ответе не хватает наблюдаемости, метрик, логирования и эксплуатационных проверок.")
    advice: List[str] = []
    missing_dims = [name for name, ok in dims.items() if not ok]
    if missing_dims:
        advice.append("Добавьте в ответ недостающие блоки: " + ", ".join(missing_dims) + ".")
    if answer_score < 7.0:
        advice.append("Не перечисляйте технологии сами по себе: привязывайте каждую к риску, гарантии и проверке на тестировании.")
    else:
        advice.append("Ответ выглядит связным. Усильте его явными компромиссами между MVP, production и legacy-вариантом.")
    return {
        "answer_score": answer_score,
        "matched_keywords": matched[:20],
        "dimension_hits": dims,
        "red_flags": red_flags,
        "advice": advice,
    }


def _score_learning(case: Dict[str, Any], payload: Dict[str, Any], base: Dict[str, Any], hits: List[Dict[str, Any]], misses: List[Dict[str, Any]], skills: Dict[str, Dict[str, Any]], mode: str, interview_assessment: Dict[str, Any] | None = None) -> float:
    controls_total = max(1, len(case.get("expected_controls", []) or []))
    control_ratio = len(hits) / controls_total
    comp = compare_to_reference(case, payload, {"control_hits": hits, "control_misses": misses})
    route_ratio = comp.get("matched_route_count", 0) / max(1, comp.get("reference_route_count", 1))
    skill_avg = sum(float(x["score"]) for x in skills.values()) / max(1, len(skills))
    base_score = float((base.get("verdict") or {}).get("score") or 0)
    critical = int((base.get("verdict") or {}).get("group_counts", {}).get("critical", 0) or 0)
    high = int((base.get("verdict") or {}).get("group_counts", {}).get("high", 0) or 0)
    score = (control_ratio * 4.8) + (route_ratio * 1.6) + (skill_avg / 10.0 * 2.2) + (base_score / 10.0 * 1.4)
    # High findings снижают confidence, но не должны обнулять хороший эталон,
    # если обязательные учебные контроли явно описаны в решении.
    score -= min(1.2, critical * 1.0 + high * 0.12)
    if misses:
        score -= min(1.2, len(misses) * 0.18)
    if mode == "reference" and not misses and critical == 0:
        score = max(score, 9.1)
    if mode == "interview":
        ans = float((interview_assessment or {}).get("answer_score") or 0.0)
        score = (score * 0.72) + (ans * 0.28)
    return round(max(0.0, min(10.0, score)), 1)


def _learning_level_v8649(score: float, critical: int, high: int, misses: int) -> str:
    if critical > 0:
        return "ниже production-ready: есть критичные блокеры"
    if score >= 9.0 and misses == 0:
        return "сильное Middle+/Senior-ready решение по этому кейсу"
    if score >= 7.6 and misses <= 1:
        return "уверенный Middle/Middle+"
    if score >= 6.2:
        return "Junior+/Middle-: решение частично рабочее, но важные гарантии раскрыты не полностью"
    return "нужно повторить базовые инварианты и перерешать кейс"


def _quick_summary(ev: Dict[str, Any]) -> Dict[str, List[str]]:
    gaps = ev.get("gaps") or []
    top_errors = []
    fixes = []
    for g in gaps[:3]:
        top_errors.append(f"{g.get('title')}: {g.get('why')}")
        fixes.append(str(g.get("fix") or "Явно добавьте недостающий контроль в шаги решения."))
    if not top_errors:
        top_errors = ["Ключевые учебные контроли найдены; проверьте нагрузку, безопасность и эксплуатационные ограничения перед реальным запуском."]
        fixes = ["Усложните кейс: добавьте сбой внешней системы, повторное событие и replay после падения consumer."]
    return {"top_errors": top_errors, "quick_fixes": fixes}


def evaluate_learning_solution(case_id: str, payload: Dict[str, Any], mode: str = "learning", answer_text: str = "") -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    mode = str(mode or "learning")
    base = analyze(payload)
    if not base.get("ok"):
        validation = base.get("errors", [])
        ev = {
            "ok": True,
            "case": {k: v for k, v in case.items() if k != "payload"},
            "base_ok": False,
            "mode": mode,
            "summary": "Схема не прошла базовую валидацию. Сначала исправьте структуру участников, связей и зависимостей.",
            "validation_errors": validation,
            "learning_score": 0.0,
            "learning_level": "невалидная схема: разбор невозможен до исправления структуры",
            "skill_scores": {k: {"name": name, "score": 0, "evidence": ["Базовая схема невалидна"]} for k, name in SKILLS.items()},
            "control_hits": [],
            "control_misses": case.get("expected_controls", []),
            "reference_variants": reference_variants(case_id),
            "interview_pack": interview_pack(case_id),
        }
        ev["quick_summary"] = _quick_summary({"gaps": [{"title": "Невалидная схема", "why": "; ".join(validation), "fix": "Исправьте участников, связи, зависимости и циклы."}]})
        ev["report_markdown"] = learning_markdown(case, ev, None, mode, validation_errors=validation)
        return ev

    hits, misses = _control_hits(case, payload, answer_text if mode == "interview" else "")
    skills = _skill_scores(case, base, misses, hits)
    verdict = base.get("verdict", {})
    critical = int(verdict.get("group_counts", {}).get("critical", verdict.get("counts", {}).get("critical", 0)) or 0)
    high = int(verdict.get("group_counts", {}).get("high", verdict.get("counts", {}).get("high", 0)) or 0)
    interview_assessment = _assess_interview_answer(case, answer_text, {"skill_scores": skills}) if mode == "interview" else None
    avg = _score_learning(case, payload, base, hits, misses, skills, mode, interview_assessment)
    learning_level = _learning_level_v8649(avg, critical, high, len(misses))
    strengths = [f"Пользователь явно указал контроль: {h.get('label')}." for h in hits[:8]]
    if base.get("verdict", {}).get("verdict") == "green" and not misses:
        strengths.append("Архитектурное ядро не видит high/critical блокеров: решение можно обсуждать как промышленный черновик.")
    if not strengths:
        strengths.append("Схема построена, но ключевые учебные контроли кейса не выражены в решении пользователя.")
    gaps = [
        {
            "title": m.get("label"),
            "why": m.get("why"),
            "skill": SKILLS.get(m.get("skill"), m.get("skill")),
            "fix": _control_fix_text_v8652(m, include_answer=True),
        }
        for m in misses[:8]
    ]
    result = {
        "ok": True,
        "case": {k: v for k, v in case.items() if k != "payload"},
        "base_ok": True,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "base_verdict": verdict,
        "learning_score": avg,
        "learning_level": learning_level,
        "skill_scores": skills,
        "control_hits": hits,
        "control_misses": misses,
        "strengths": strengths,
        "gaps": gaps,
        "next_tasks": _next_tasks(case, misses, skills),
        "reference_payload": case.get("payload") if mode in ("reference", "interview_review") else None,
        "base_result": base,
        "reference_variants": reference_variants(case_id),
        "interview_pack": interview_pack(case_id),
        "interview_answer_assessment": interview_assessment,
    }
    result["reference_comparison"] = compare_to_reference(case, payload, result)
    result["hints_available"] = [1, 2, 3, 4]
    result["quick_summary"] = _quick_summary(result)
    result["report_markdown"] = learning_markdown(case, result, base, mode)
    return result


def _fast_reference_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    base = analyze(case.get("payload") or {})
    if not base.get("ok"):
        return {"ok": False, "base_ok": False, "score": 0.0, "errors": base.get("errors", [])}
    ev = evaluate_learning_solution(str(case.get("id")), case.get("payload") or {}, mode="reference")
    return {
        "ok": bool(ev.get("ok")),
        "base_ok": True,
        "score": float(ev.get("learning_score") or 0),
        "hit_count": len(ev.get("control_hits") or []),
        "miss_count": len(ev.get("control_misses") or []),
    }


def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    out: List[str] = []
    out.append(f"# Учебный разбор: {humanize_terms(case['title'])}")
    out.append("")
    out.append(f"**Уровень кейса:** {humanize_terms(case.get('level'))}  ")
    out.append(f"**Трек:** {humanize_terms(case.get('track'))}  ")
    out.append(f"**Цель:** {_ru_sentence(case.get('goal'))}  ")
    out.append(f"**Режим:** {_mode_label(mode)}")
    out.append("")
    if validation_errors:
        out.append("## 1. Короткий вывод")
        out.append("- Схема пока невалидна: разбор невозможен до исправления структуры.")
        out.append("- Сначала проверьте участников, связи, зависимости и отсутствие циклов.")
        out.append("")
        out.append("## 2. Ошибки валидации")
        out.append(_ru_list(validation_errors))
        out.append("")
        out.append("## 3. Эталонные ориентиры")
        out.extend(_reference_variants_markdown((ev or {}).get("reference_variants") or reference_variants(case["id"])))
        out.append("")
        out.append("## 4. Как это спросили бы на собеседовании")
        out.extend(_interview_markdown((ev or {}).get("interview_pack") or interview_pack(case["id"])))
        return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

    assert ev is not None and base is not None
    bv = ev.get("base_verdict") or {}
    qs = ev.get("quick_summary") or _quick_summary(ev)
    out.append("## 1. Короткий вывод")
    out.append(f"- Учебная оценка: **{ev['learning_score']}/10**.")
    out.append(f"- Уровень решения: **{_ru_sentence(ev['learning_level'])}**")
    out.append(f"- Архитектурное ядро: **{_ru_sentence(bv.get('verdict', 'не рассчитан')).rstrip('.')}**, {bv.get('score', '—')}/10.")
    out.append("")
    out.append("**Три главных замечания:**")
    out.extend(_md_nested_list(qs.get("top_errors", [])[:3]))
    out.append("")
    out.append("**Быстрые исправления:**")
    out.extend(_md_nested_list(qs.get("quick_fixes", [])[:3]))
    out.append("")
    out.append("## 2. Профиль навыков")
    for _, data in ev["skill_scores"].items():
        out.append(f"- **{humanize_terms(data['name'])}**: {data['score']}/10.")
        for e in data.get("evidence", [])[:2]:
            out.append(f"  - {_ru_sentence(e)}")
    out.append("")
    out.append("## 3. Что пользователь действительно указал")
    out.append(_ru_list(ev.get("strengths", [])))
    out.append("")
    comp = ev.get("reference_comparison") or {}
    out.append("## 4. Сравнение с эталоном")
    out.append(f"- Совпавших маршрутов: **{comp.get('matched_route_count', 0)} / {comp.get('reference_route_count', 0)}**.")
    out.append(f"- Покрытые способы взаимодействия: {_display_channels(comp.get('channel_coverage') or [])}.")
    out.append(f"- Недостающие способы из эталона: {_display_channels(comp.get('missing_channels') or [])}.")
    out.append(f"- Найдено учебных контролей в решении пользователя: **{comp.get('control_hit_count', 0)}**; пропущено: **{comp.get('control_miss_count', 0)}**.")
    out.append("")
    out.append("## 5. Что мешает готовности к промышленному запуску")
    if ev.get("gaps"):
        for g in ev["gaps"]:
            out.append(f"### {_ru_sentence(g['title']).rstrip('.')}")
            out.append(f"**Почему важно:** {_ru_sentence(g.get('why'))}")
            out.append(f"**Как исправить:** {_ru_sentence(g.get('fix'))}")
            out.append("")
    else:
        out.append("Ключевые учебные контроли кейса явно указаны пользователем. Перед реальным выпуском всё равно проверьте нагрузку, безопасность, эксплуатационные сценарии и договорённости с владельцами систем.")
        out.append("")
    out.append("## 6. Типовые ловушки этого кейса")
    out.append(_ru_list(case.get("hidden_traps", [])))
    out.append("")
    out.append("## 7. Следующие задания")
    out.append(_ru_list(ev.get("next_tasks", [])))
    out.append("")
    out.append("## 8. Эталонная схема решения")
    out.append("Эталон — это не один жёсткий ответ, а набор ориентиров: промышленный вариант, допустимый MVP и компромисс для legacy-среды.")
    out.append("")
    out.extend(_reference_variants_markdown(ev.get("reference_variants") or reference_variants(case["id"])))
    out.append("")
    out.append("## 9. Блок собеседования")
    out.extend(_interview_markdown(ev.get("interview_pack") or interview_pack(case["id"]), ev.get("interview_answer_assessment")))
    out.append("")
    out.append("## 10. Полный архитектурный отчёт ядра")
    out.append("")
    out.append(markdown_report(base))
    return "\n".join(humanize_terms(x) for x in out).strip() + "\n"


def learning_result_html(ev: Dict[str, Any]) -> str:
    if not ev.get("ok"):
        return "<div class='err'>" + escape("; ".join(ev.get("errors", []))) + "</div>"
    if not ev.get("base_ok", True):
        errs = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ev.get("validation_errors", []))
        return f"<div class='finding critical'><h3>Схема невалидна</h3><ul>{errs}</ul></div>"
    skills = ev.get("skill_scores", {})
    skill_cards = []
    for _, s in skills.items():
        evs = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in s.get("evidence", [])[:3])
        skill_cards.append(f"<div class='learn-skill'><b>{escape(s['name'])}</b><span>{s['score']}/10</span><ul>{evs}</ul></div>")
    qs = ev.get("quick_summary") or _quick_summary(ev)
    top_errors = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in qs.get("top_errors", [])[:3])
    quick_fixes = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in qs.get("quick_fixes", [])[:3])
    gaps = ev.get("gaps", [])
    gap_html = "".join(
        f"<div class='finding high'><h3>{escape(_ru_sentence(g['title']).rstrip('.'))}</h3><p><b>Почему важно:</b> {escape(_ru_sentence(g.get('why','')))}</p><p><b>Как исправить:</b> {escape(_ru_sentence(g.get('fix','')))}</p></div>"
        for g in gaps
    ) or "<p>Ключевые учебные контроли найдены в решении пользователя. Проверьте детали контрактов и эксплуатационные ограничения.</p>"
    tasks = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ev.get("next_tasks", []))
    strengths = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ev.get("strengths", []))
    comp = ev.get("reference_comparison") or {}
    ass = ev.get("interview_answer_assessment") or {}
    interview_html = ""
    if ev.get("mode") == "interview":
        rf = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ass.get("red_flags", [])) or "<li>Критичных красных флагов в устном объяснении не найдено.</li>"
        adv = "".join(f"<li>{escape(_ru_sentence(x))}</li>" for x in ass.get("advice", []))
        dims = ass.get("dimension_hits") or {}
        dim_text = ", ".join(f"{k}: {'да' if v else 'нет'}" for k, v in dims.items())
        interview_html = f"<h3>Оценка собеседования</h3><div class='learn-compare'><b>Устное объяснение:</b> {escape(str(ass.get('answer_score', 0)))} / 10<br><b>Покрытие структуры:</b> {escape(dim_text)}<br><b>Красные флаги:</b><ul>{rf}</ul><b>Как усилить ответ:</b><ol>{adv}</ol></div>"
    compare_html = f"<div class='learn-compare'><b>Сравнение с эталоном:</b> маршруты {comp.get('matched_route_count',0)}/{comp.get('reference_route_count',0)}, найдено контролей в решении пользователя {comp.get('control_hit_count',0)}, пропущено {comp.get('control_miss_count',0)}.</div>"
    return f"""
    <div class='learn-verdict'>
      <h2>{escape(str(ev.get('learning_score')))} / 10 · {escape(ev.get('learning_level',''))}</h2>
      <p>Архитектурная оценка ядра: {escape(str((ev.get('base_verdict') or {}).get('verdict','—')))} · {(ev.get('base_verdict') or {}).get('score','—')}/10</p>
    </div>
    <div class='learn-compare'><b>Короткий разбор</b><br><b>Главные замечания:</b><ol>{top_errors}</ol><b>Быстрые исправления:</b><ol>{quick_fixes}</ol></div>
    {compare_html}
    {interview_html}
    <h3>Профиль навыков</h3><div class='learn-skills'>{''.join(skill_cards)}</div>
    <h3>Что пользователь действительно указал</h3><ul>{strengths}</ul>
    <h3>Что доработать</h3>{gap_html}
    <h3>Следующие задания</h3><ol>{tasks}</ol>
    """

# v8.6.49b: быстрый catalog deep-check без генерации полноразмерного markdown.
def _fast_reference_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    payload = case.get("payload") or {}
    base = analyze(payload)
    if not base.get("ok"):
        return {"ok": False, "base_ok": False, "score": 0.0, "errors": base.get("errors", [])}
    hits, misses = _control_hits(case, payload, "")
    skills = _skill_scores(case, base, misses, hits)
    score = _score_learning(case, payload, base, hits, misses, skills, "reference", None)
    return {
        "ok": True,
        "base_ok": True,
        "score": float(score),
        "hit_count": len(hits),
        "miss_count": len(misses),
    }

# v8.6.49c: дополнительные строгие правила для общих контролей из массового каталога.
_PREV_CONTROL_FOUND_IN_USER_SOLUTION_V8649 = _control_found_in_user_solution

def _control_found_in_user_solution(control: Dict[str, Any], payload: Dict[str, Any], answer_text: str = "") -> Tuple[bool, str]:
    text = _payload_user_evidence(payload, answer_text)
    cid = str(control.get("id") or "").lower()
    label = str(control.get("label") or "")
    if cid in {"correlation", "trace", "tracing"} or _has_re(r"correlation|trace|трасс|сквоз", label):
        return _has_re(r"correlation.?id|trace.?id|traceparent|трассиров|сквозн[а-я\s-]*идентификатор|идентификатор отслеж", text), "payload_or_answer"
    if cid in {"idem", "idempotency"} or _has_re(r"идемпот|дедуп", label):
        return _has_re(r"idempot|идемпот|дедуп|dedup|unique|уникальн|event.?id|operation.?id|request.?id", text), "payload_or_answer"
    if cid in {"dlq", "quarantine"}:
        return _has_re(r"\bdlq\b|dead.?letter|карантин|quarantine|workflow_engine|ручн[а-я\s-]*разбор|parking|replay|переобработ", text), "payload_or_answer"
    return _PREV_CONTROL_FOUND_IN_USER_SOLUTION_V8649(control, payload, answer_text)

# v8.6.49d: сохраняем совместимость с языковым verifier'ом: раздел 1 снова
# называется «Итоговая оценка», а короткий вывод находится внутри него.
def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    out: List[str] = []
    out.append(f"# Учебный разбор: {humanize_terms(case['title'])}")
    out.append("")
    out.append(f"**Уровень кейса:** {humanize_terms(case.get('level'))}  ")
    out.append(f"**Трек:** {humanize_terms(case.get('track'))}  ")
    out.append(f"**Цель:** {_ru_sentence(case.get('goal'))}  ")
    out.append(f"**Режим:** {_mode_label(mode)}")
    out.append("")
    if validation_errors:
        out.append("## 1. Итоговая оценка")
        out.append("### Короткий вывод")
        out.append("- Схема пока невалидна: разбор невозможен до исправления структуры.")
        out.append("- Сначала проверьте участников, связи, зависимости и отсутствие циклов.")
        out.append("")
        out.append("## 2. Ошибки валидации")
        out.append(_ru_list(validation_errors))
        out.append("")
        out.append("## 8. Эталонная схема решения")
        out.extend(_reference_variants_markdown((ev or {}).get("reference_variants") or reference_variants(case["id"])))
        out.append("")
        out.append("## 9. Блок собеседования")
        out.extend(_interview_markdown((ev or {}).get("interview_pack") or interview_pack(case["id"])))
        return "\n".join(humanize_terms(x) for x in out).strip() + "\n"
    assert ev is not None and base is not None
    bv = ev.get("base_verdict") or {}
    qs = ev.get("quick_summary") or _quick_summary(ev)
    out.append("## 1. Итоговая оценка")
    out.append("### Короткий вывод")
    out.append(f"- Учебная оценка: **{ev['learning_score']}/10**.")
    out.append(f"- Уровень решения: **{_ru_sentence(ev['learning_level'])}**")
    out.append(f"- Архитектурное ядро: **{_ru_sentence(bv.get('verdict', 'не рассчитан')).rstrip('.')}**, {bv.get('score', '—')}/10.")
    out.append("")
    out.append("**Три главных замечания:**")
    out.extend(_md_nested_list(qs.get("top_errors", [])[:3]))
    out.append("")
    out.append("**Быстрые исправления:**")
    out.extend(_md_nested_list(qs.get("quick_fixes", [])[:3]))
    out.append("")
    out.append("## 2. Профиль навыков")
    for _, data in ev["skill_scores"].items():
        out.append(f"- **{humanize_terms(data['name'])}**: {data['score']}/10.")
        for e in data.get("evidence", [])[:2]:
            out.append(f"  - {_ru_sentence(e)}")
    out.append("")
    out.append("## 3. Что пользователь действительно указал")
    out.append(_ru_list(ev.get("strengths", [])))
    out.append("")
    comp = ev.get("reference_comparison") or {}
    out.append("## 4. Сравнение с эталоном")
    out.append(f"- Совпавших маршрутов: **{comp.get('matched_route_count', 0)} / {comp.get('reference_route_count', 0)}**.")
    out.append(f"- Покрытые способы взаимодействия: {_display_channels(comp.get('channel_coverage') or [])}.")
    out.append(f"- Недостающие способы из эталона: {_display_channels(comp.get('missing_channels') or [])}.")
    out.append(f"- Найдено учебных контролей в решении пользователя: **{comp.get('control_hit_count', 0)}**; пропущено: **{comp.get('control_miss_count', 0)}**.")
    out.append("")
    out.append("## 5. Что мешает готовности к промышленному запуску")
    if ev.get("gaps"):
        for g in ev["gaps"]:
            out.append(f"### {_ru_sentence(g['title']).rstrip('.')}")
            out.append(f"**Почему важно:** {_ru_sentence(g.get('why'))}")
            out.append(f"**Как исправить:** {_ru_sentence(g.get('fix'))}")
            out.append("")
    else:
        out.append("Ключевые учебные контроли кейса явно указаны пользователем. Перед реальным выпуском всё равно проверьте нагрузку, безопасность, эксплуатационные сценарии и договорённости с владельцами систем.")
        out.append("")
    out.append("## 6. Типовые ловушки этого кейса")
    out.append(_ru_list(case.get("hidden_traps", [])))
    out.append("")
    out.append("## 7. Следующие задания")
    out.append(_ru_list(ev.get("next_tasks", [])))
    out.append("")
    out.append("## 8. Эталонная схема решения")
    out.append("Эталон — это не один жёсткий ответ, а набор ориентиров: промышленный вариант, допустимый MVP и компромисс для legacy-среды.")
    out.append("")
    out.extend(_reference_variants_markdown(ev.get("reference_variants") or reference_variants(case["id"])))
    out.append("")
    out.append("## 9. Блок собеседования")
    out.extend(_interview_markdown(ev.get("interview_pack") or interview_pack(case["id"]), ev.get("interview_answer_assessment")))
    out.append("")
    out.append("## 10. Полный архитектурный отчёт ядра")
    out.append("")
    out.append(markdown_report(base))
    return "\n".join(humanize_terms(x) for x in out).strip() + "\n"

# ---------------------------------------------------------------------------
# v8.6.50: пользовательская приёмка. Главное исправление — в режиме
# собеседования итоговая оценка больше не маскирует слабую схему сильным
# устным ответом и наоборот. Пользователь видит отдельно: архитектурное
# решение, устное объяснение и итог собеседования.
# ---------------------------------------------------------------------------
APP_LEARNING_VERSION = "8.6.50-user-acceptance-polished"
CASE_CATALOG_VERSION = "2026-06-16-v6-user-acceptance-polished"

_TRACK_RU_V8650 = {
    "AI / Search": "ИИ и поиск",
    "Analytics Engineering": "Инженерия аналитики",
    "Banking": "Банковские процессы",
    "Batch / files": "Пакетные загрузки и файлы",
    "Big Data": "Большие данные",
    "Brokerage": "Брокерские операции",
    "CDC": "CDC и потоковые изменения",
    "Cloud messaging": "Облачные очереди и события",
    "Compliance": "Регуляторика и контроль",
    "Contract evolution": "Эволюция контрактов",
    "Data platform": "Платформа данных",
    "Database scaling": "Масштабирование БД",
    "Database": "Базы данных",
    "Document flow": "Документооборот",
    "E-commerce": "Электронная коммерция",
    "Event-driven architecture": "Событийная архитектура",
    "External integration": "Внешние интеграции",
    "Fault tolerance": "Отказоустойчивость",
    "Identity": "Идентификация и доступ",
    "Insurance": "Страхование",
    "Inventory": "Складские остатки",
    "IoT / Data": "IoT и данные",
    "Ledger": "Учётные книги и проводки",
    "Logistics": "Логистика",
    "Marketplace": "Маркетплейсы",
    "Migration": "Миграции",
    "NoSQL": "NoSQL-хранилища",
    "Orchestration": "Оркестрация процессов",
    "Performance": "Производительность",
    "Platform": "Платформенная архитектура",
    "Realtime": "Режим реального времени",
    "Retail": "Розница",
    "Security / data": "Безопасность данных",
    "Security": "Безопасность",
    "Storage": "Хранение данных",
    "Warehouse": "Складская логистика",
    "Web platform": "Веб-платформа",
    "Legacy / SAP": "Legacy и SAP",
    "Mainframe": "Mainframe и legacy",
}

_TEXT_FIXES_V8650 = (
    ("аналитическое хранилище не должен быть зависимость основного потока", "аналитическое хранилище не должно быть зависимостью основного потока"),
    ("DWH не должен быть core dependency", "DWH не должен быть зависимостью основного потока"),
    ("core dependency", "зависимость основного потока"),
    ("event-driven", "событийная"),
    ("Event-driven", "Событийная"),
    ("Data / DWH", "Данные и аналитическое хранилище"),
    ("External integration", "Внешние интеграции"),
    ("Fault tolerance", "Отказоустойчивость"),
    ("Contract evolution", "Эволюция контрактов"),
    ("Security / data", "Безопасность данных"),
    ("Analytics Engineering", "Инженерия аналитики"),
    ("Cloud messaging", "Облачные очереди и события"),
    ("Batch / files", "Пакетные загрузки и файлы"),
    ("Performance", "Производительность"),
    ("Realtime", "Режим реального времени"),
    ("Banking", "Банковские процессы"),
)


def _clean_user_text_v8650(value: Any) -> Any:
    if isinstance(value, str):
        s = value.strip()
        if s.endswith(".") and s[:-1] in _TRACK_RU_V8650:
            s = s[:-1]
        s = _TRACK_RU_V8650.get(s, s)
        for old, new in _TEXT_FIXES_V8650:
            s = s.replace(old, new)
        return s
    if isinstance(value, list):
        return [_clean_user_text_v8650(x) for x in value]
    if isinstance(value, dict):
        return {k: _clean_user_text_v8650(v) for k, v in value.items()}
    return value


def _normalize_cases_v8650() -> None:
    for c in CASES:
        if c.get("track"):
            track = str(c.get("track") or "").strip().rstrip(".")
            c["track"] = _TRACK_RU_V8650.get(track, track)
        for key in ("brief", "goal"):
            if c.get(key):
                c[key] = _clean_user_text_v8650(c.get(key))
        if c.get("hidden_traps"):
            c["hidden_traps"] = _clean_user_text_v8650(c.get("hidden_traps"))


_normalize_cases_v8650()

_PREV_LEARNING_MARKDOWN_V8649D = learning_markdown
_PREV_LEARNING_RESULT_HTML_V8649 = learning_result_html
_PREV_EVALUATE_LEARNING_SOLUTION_V8649 = evaluate_learning_solution
_PREV_FAST_REFERENCE_QUALITY_V8649 = _fast_reference_quality


def _combine_interview_score_v8650(solution_score: float, answer_score: float) -> Tuple[float, str]:
    """Итог собеседования не должен проходить, если провален один из двух
    независимых блоков: схема или объяснение. Это ключевое пользовательское
    правило доверия.
    """
    solution_score = float(solution_score or 0.0)
    answer_score = float(answer_score or 0.0)
    weighted = round((solution_score * 0.62) + (answer_score * 0.38), 1)
    if solution_score < 5.0 and answer_score >= 7.0:
        return min(weighted, 4.9), "устный ответ звучит сильнее, чем построенная схема; собеседование не пройдено из-за слабого решения"
    if answer_score < 5.0 and solution_score >= 7.0:
        return min(weighted, 4.9), "схема выглядит сильной, но устное объяснение слабое; собеседование не пройдено"
    if solution_score < 5.0 or answer_score < 5.0:
        return min(weighted, 4.9), "один из обязательных блоков собеседования провален"
    if solution_score < 7.0 or answer_score < 7.0:
        return min(weighted, 7.4), "собеседование условно не пройдено: один из блоков требует доработки"
    if weighted >= 8.5:
        return weighted, "собеседование пройдено на сильном уровне"
    return weighted, "собеседование пройдено, но есть зоны роста"


def _interview_level_v8650(interview_score: float, solution_score: float, answer_score: float, critical: int, misses: int) -> str:
    if critical > 0:
        return "собеседование не пройдено: в схеме есть критичные архитектурные блокеры"
    if solution_score < 5.0 and answer_score >= 7.0:
        return "сильное объяснение не компенсирует слабую схему: нужно перестроить решение"
    if solution_score >= 7.6 and answer_score < 5.0:
        return "сильная схема, но слабое устное объяснение: на интервью решение не будет защищено"
    if interview_score >= 8.5 and misses == 0:
        return "сильный Middle+/Senior-ready ответ на собеседовании"
    if interview_score >= 7.0:
        return "уверенный Middle/Middle+, но ответ нужно усилить деталями"
    if interview_score >= 5.0:
        return "частично рабочий ответ: есть база, но до уверенного Middle не хватает структуры"
    return "собеседование не пройдено: нужно заново разобрать схему и объяснение"


def evaluate_learning_solution(case_id: str, payload: Dict[str, Any], mode: str = "learning", answer_text: str = "") -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    mode = str(mode or "learning")
    base = analyze(payload)
    if not base.get("ok"):
        return _PREV_EVALUATE_LEARNING_SOLUTION_V8649(case_id, payload, mode=mode, answer_text=answer_text)

    hits, misses = _control_hits(case, payload, answer_text if mode == "interview" else "")
    skills = _skill_scores(case, base, misses, hits)
    verdict = base.get("verdict", {})
    critical = int(verdict.get("group_counts", {}).get("critical", verdict.get("counts", {}).get("critical", 0)) or 0)
    high = int(verdict.get("group_counts", {}).get("high", verdict.get("counts", {}).get("high", 0)) or 0)

    solution_mode = "reference" if mode == "reference" else "learning"
    solution_score = _PREV_SCORE_LEARNING_V8649(case, payload, base, hits, misses, skills, solution_mode, None)
    interview_assessment = _assess_interview_answer(case, answer_text, {"skill_scores": skills}) if mode == "interview" else None
    answer_score = float((interview_assessment or {}).get("answer_score") or 0.0)
    interview_score = None
    interview_verdict = None
    if mode == "interview":
        interview_score, interview_verdict = _combine_interview_score_v8650(solution_score, answer_score)
        avg = interview_score
        learning_level = _interview_level_v8650(interview_score, solution_score, answer_score, critical, len(misses))
    else:
        avg = solution_score
        learning_level = _learning_level_v8649(avg, critical, high, len(misses))

    strengths = [f"Пользователь явно указал контроль: {h.get('label')}." for h in hits[:8]]
    if base.get("verdict", {}).get("verdict") == "green" and not misses:
        strengths.append("Архитектурное ядро не видит high/critical блокеров: решение можно обсуждать как промышленный черновик.")
    if not strengths:
        strengths.append("Схема построена, но ключевые учебные контроли кейса не выражены в решении пользователя.")
    gaps = [
        {
            "title": m.get("label"),
            "why": m.get("why"),
            "skill": SKILLS.get(m.get("skill"), m.get("skill")),
            "fix": _control_fix_text_v8652(m, include_answer=True),
        }
        for m in misses[:8]
    ]
    result = {
        "ok": True,
        "case": {k: _clean_user_text_v8650(v) for k, v in case.items() if k != "payload"},
        "base_ok": True,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "base_verdict": verdict,
        "learning_score": avg,
        "learning_level": learning_level,
        "solution_score": solution_score,
        "answer_score": answer_score if mode == "interview" else None,
        "interview_score": interview_score,
        "interview_verdict": interview_verdict,
        "score_breakdown": {
            "solution_score": solution_score,
            "answer_score": answer_score if mode == "interview" else None,
            "interview_score": interview_score,
            "rule": "Итог собеседования не может быть высоким, если провалена схема или устное объяснение.",
        },
        "skill_scores": skills,
        "control_hits": hits,
        "control_misses": misses,
        "strengths": strengths,
        "gaps": gaps,
        "next_tasks": _next_tasks(case, misses, skills),
        "reference_payload": case.get("payload") if mode in ("reference", "interview_review") else None,
        "base_result": base,
        "reference_variants": reference_variants(case_id),
        "interview_pack": interview_pack(case_id),
        "interview_answer_assessment": interview_assessment,
    }
    result["reference_comparison"] = compare_to_reference(case, payload, result)
    result["hints_available"] = [1, 2, 3, 4]
    result["quick_summary"] = _quick_summary(result)
    result["report_markdown"] = learning_markdown(case, result, base, mode)
    return result


def _fast_reference_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    payload = case.get("payload") or {}
    base = analyze(payload)
    if not base.get("ok"):
        return {"ok": False, "base_ok": False, "score": 0.0, "errors": base.get("errors", [])}
    hits, misses = _control_hits(case, payload, "")
    skills = _skill_scores(case, base, misses, hits)
    score = _PREV_SCORE_LEARNING_V8649(case, payload, base, hits, misses, skills, "reference", None)
    return {
        "ok": True,
        "base_ok": True,
        "score": float(score),
        "hit_count": len(hits),
        "miss_count": len(misses),
    }


def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    if validation_errors or not ev or not base:
        return _PREV_LEARNING_MARKDOWN_V8649D(case, ev, base, mode, validation_errors)
    text = _PREV_LEARNING_MARKDOWN_V8649D(case, ev, base, mode, validation_errors)
    if mode == "interview":
        lines = [
            "",
            "### Раздельная оценка собеседования",
            f"- Архитектурное решение: **{ev.get('solution_score', 0)}/10**.",
            f"- Устное объяснение: **{ev.get('answer_score', 0)}/10**.",
            f"- Итог собеседования: **{ev.get('interview_score', ev.get('learning_score', 0))}/10**.",
            f"- Вердикт собеседования: {_ru_sentence(ev.get('interview_verdict') or ev.get('learning_level'))}",
            "",
        ]
        marker = "**Три главных замечания:**"
        if marker in text:
            text = text.replace(marker, "\n".join(lines) + marker, 1)
        else:
            text = text + "\n" + "\n".join(lines)
    return _clean_user_text_v8650(text)


def learning_result_html(ev: Dict[str, Any]) -> str:
    html = _PREV_LEARNING_RESULT_HTML_V8649(ev)
    if ev.get("mode") == "interview":
        block = (
            "<div class='learn-compare'><b>Раздельная оценка собеседования</b><br>"
            f"Архитектурное решение: {escape(str(ev.get('solution_score', 0)))} / 10<br>"
            f"Устное объяснение: {escape(str(ev.get('answer_score', 0)))} / 10<br>"
            f"Итог собеседования: {escape(str(ev.get('interview_score', ev.get('learning_score', 0))))} / 10<br>"
            f"Вердикт: {escape(_ru_sentence(ev.get('interview_verdict') or ev.get('learning_level') or ''))}</div>"
        )
        html = html.replace("<h3>Профиль навыков</h3>", block + "<h3>Профиль навыков</h3>", 1)
    return _clean_user_text_v8650(html)

# v8.6.50 compatibility: evaluate_learning_solution above looks up this name at
# call time, so assigning it here keeps the previous scoring function available.
_PREV_SCORE_LEARNING_V8649 = _score_learning


# ---------------------------------------------------------------------------
# v8.6.52: пользовательская вычитка быстрых исправлений.
# Не показываем в отчёте стемы и технические ключевые слова вроде
# "исходящ", "повторн", "огранич", "верси".
# ---------------------------------------------------------------------------
def _control_fix_text_v8652(m: Dict[str, Any], include_answer: bool = False) -> str:
    cid = str(m.get("id") or "")
    readable = {
        "outbox": "Outbox-таблицу или другой надёжный механизм публикации после фиксации решения",
        "kafka_key": "ключ партиционирования по идентификатору бизнес-сущности, например applicationId",
        "dlq_replay": "очередь ошибок, карантин и понятную процедуру повторной обработки",
        "timeouts": "таймауты, ограниченное число повторов и лимиты внешних вызовов",
        "versioning": "версию события или контракта и правила совместимости изменений",
        "idempotency": "ключ идемпотентности и безопасную обработку дублей",
        "contract": "версию контракта, обязательные поля и правила обратной совместимости",
        "observability": "метрики, журналы, трассировку и корреляционный идентификатор",
        "security": "правила доступа, аудит и защиту чувствительных данных",
    }
    hint = readable.get(cid)
    if not hint:
        label = str(m.get("label") or "недостающий контроль").strip().rstrip(".")
        hint = label[0].lower() + label[1:] if label else "недостающий контроль"
    where = "в шаги, компенсации или устное объяснение" if include_answer else "в шаги или компенсации схемы"
    return f"Явно добавьте {hint} {where}."

# v8.6.50b: в режиме собеседования архитектурная часть оценивается только
# по схеме/payload. Устный ответ оценивается отдельно и не должен превращать
# слабую схему в сильное архитектурное решение.
def evaluate_learning_solution(case_id: str, payload: Dict[str, Any], mode: str = "learning", answer_text: str = "") -> Dict[str, Any]:
    case = get_case(case_id)
    if not case:
        return {"ok": False, "errors": ["Учебный кейс не найден."]}
    mode = str(mode or "learning")
    base = analyze(payload)
    if not base.get("ok"):
        return _PREV_EVALUATE_LEARNING_SOLUTION_V8649(case_id, payload, mode=mode, answer_text=answer_text)

    # Только payload для архитектурного решения. Это принципиально для доверия.
    hits, misses = _control_hits(case, payload, "")
    answer_hits, answer_misses = _control_hits(case, payload, answer_text if mode == "interview" else "")
    skills = _skill_scores(case, base, misses, hits)
    verdict = base.get("verdict", {})
    critical = int(verdict.get("group_counts", {}).get("critical", verdict.get("counts", {}).get("critical", 0)) or 0)
    high = int(verdict.get("group_counts", {}).get("high", verdict.get("counts", {}).get("high", 0)) or 0)

    solution_mode = "reference" if mode == "reference" else "learning"
    solution_score = _PREV_SCORE_LEARNING_V8649(case, payload, base, hits, misses, skills, solution_mode, None)
    interview_assessment = _assess_interview_answer(case, answer_text, {"skill_scores": skills}) if mode == "interview" else None
    answer_score = float((interview_assessment or {}).get("answer_score") or 0.0)
    interview_score = None
    interview_verdict = None
    if mode == "interview":
        interview_score, interview_verdict = _combine_interview_score_v8650(solution_score, answer_score)
        avg = interview_score
        learning_level = _interview_level_v8650(interview_score, solution_score, answer_score, critical, len(misses))
    else:
        avg = solution_score
        learning_level = _learning_level_v8649(avg, critical, high, len(misses))

    strengths = [f"Пользователь явно указал контроль в схеме: {h.get('label')}." for h in hits[:8]]
    if mode == "interview":
        answer_only = [h for h in answer_hits if h.get("id") not in {x.get("id") for x in hits}]
        strengths.extend([f"Пользователь проговорил в устном ответе: {h.get('label')}." for h in answer_only[:5]])
    if base.get("verdict", {}).get("verdict") == "green" and not misses:
        strengths.append("Архитектурное ядро не видит high/critical блокеров: решение можно обсуждать как промышленный черновик.")
    if not strengths:
        strengths.append("Схема построена, но ключевые учебные контроли кейса не выражены в решении пользователя.")
    gaps = [
        {
            "title": m.get("label"),
            "why": m.get("why"),
            "skill": SKILLS.get(m.get("skill"), m.get("skill")),
            "fix": _control_fix_text_v8652(m, include_answer=False),
        }
        for m in misses[:8]
    ]
    result = {
        "ok": True,
        "case": {k: _clean_user_text_v8650(v) for k, v in case.items() if k != "payload"},
        "base_ok": True,
        "mode": mode,
        "mode_label": _mode_label(mode),
        "base_verdict": verdict,
        "learning_score": avg,
        "learning_level": learning_level,
        "solution_score": solution_score,
        "answer_score": answer_score if mode == "interview" else None,
        "interview_score": interview_score,
        "interview_verdict": interview_verdict,
        "score_breakdown": {
            "solution_score": solution_score,
            "answer_score": answer_score if mode == "interview" else None,
            "interview_score": interview_score,
            "rule": "Архитектурная оценка считается только по схеме. Устный ответ оценивается отдельно и не маскирует слабое решение.",
        },
        "skill_scores": skills,
        "control_hits": hits,
        "control_misses": misses,
        "answer_control_hits": answer_hits if mode == "interview" else [],
        "answer_control_misses": answer_misses if mode == "interview" else [],
        "strengths": strengths,
        "gaps": gaps,
        "next_tasks": _next_tasks(case, misses, skills),
        "reference_payload": case.get("payload") if mode in ("reference", "interview_review") else None,
        "base_result": base,
        "reference_variants": reference_variants(case_id),
        "interview_pack": interview_pack(case_id),
        "interview_answer_assessment": interview_assessment,
    }
    result["reference_comparison"] = compare_to_reference(case, payload, result)
    result["hints_available"] = [1, 2, 3, 4]
    result["quick_summary"] = _quick_summary(result)
    result["report_markdown"] = learning_markdown(case, result, base, mode)
    return result

# v8.6.50c: финальная пользовательская вычитка фраз режима собеседования.
_MORE_TEXT_FIXES_V8650C = (
    ("сильный Middle+/Senior-готово ответ на собеседовании", "сильный ответ уровня Middle+/Senior на собеседовании"),
    ("сильный Middle+/Senior-ready ответ на собеседовании", "сильный ответ уровня Middle+/Senior на собеседовании"),
    ("после падения потребитель", "после падения потребителя"),
    ("после падения consumer", "после падения потребителя"),
)
_PREV_CLEAN_USER_TEXT_V8650 = _clean_user_text_v8650

def _clean_user_text_v8650(value: Any) -> Any:
    value = _PREV_CLEAN_USER_TEXT_V8650(value)
    if isinstance(value, str):
        for old, new in _MORE_TEXT_FIXES_V8650C:
            value = value.replace(old, new)
    elif isinstance(value, list):
        value = [_clean_user_text_v8650(x) for x in value]
    elif isinstance(value, dict):
        value = {k: _clean_user_text_v8650(v) for k, v in value.items()}
    return value

_PREV_INTERVIEW_LEVEL_V8650 = _interview_level_v8650

def _interview_level_v8650(interview_score: float, solution_score: float, answer_score: float, critical: int, misses: int) -> str:
    if critical > 0:
        return "собеседование не пройдено: в схеме есть критичные архитектурные блокеры"
    if solution_score < 5.0 and answer_score >= 7.0:
        return "сильное объяснение не компенсирует слабую схему: нужно перестроить решение"
    if solution_score >= 7.6 and answer_score < 5.0:
        return "сильная схема, но слабое устное объяснение: на интервью решение не будет защищено"
    if interview_score >= 8.5 and misses == 0:
        return "сильный ответ уровня Middle+/Senior на собеседовании"
    if interview_score >= 7.0:
        return "уверенный ответ уровня Middle/Middle+, но его нужно усилить деталями"
    if interview_score >= 5.0:
        return "частично рабочий ответ: есть база, но до уверенного Middle не хватает структуры"
    return "собеседование не пройдено: нужно заново разобрать схему и объяснение"

_PREV_QUICK_SUMMARY_V8649 = _quick_summary

def _quick_summary(ev: Dict[str, Any]) -> Dict[str, List[str]]:
    qs = _PREV_QUICK_SUMMARY_V8649(ev)
    return _clean_user_text_v8650(qs)

# ---------------------------------------------------------------------------
# v8.6.51: повторная пользовательская приёмка. Исправляем последние фразы,
# которые читались как технические обрубки в эталонах и отчётах собеседования.
# ---------------------------------------------------------------------------
APP_LEARNING_VERSION = "8.6.52-user-retest-polished"
CASE_CATALOG_VERSION = "2026-06-16-v8-user-retest-polished"

_MORE_TEXT_FIXES_V8651 = (
    ("fallback to manual review", "запасной сценарий с переводом на ручной разбор"),
    ("запасной сценарий to ручной разбор", "запасной сценарий с переводом на ручной разбор"),
    ("fallback to ручной разбор", "запасной сценарий с переводом на ручной разбор"),
    ("Сохранить решение и таблица исходящих сообщений", "Сохранить решение и запись в Outbox-таблицу"),
    ("Сохранить решение и Outbox", "Сохранить решение и запись в Outbox-таблицу"),
    ("таблица исходящих сообщений для публикации события после фиксации решения", "Outbox-таблица для публикации события после фиксации решения"),
    ("очередь ошибок или карантин и повторная обработка", "очередь ошибок, карантин и повторная обработка"),
    ("Ключ Kafka по applicationId", "ключ Kafka по applicationId"),
    ("DLQ/quarantine и replay", "очередь ошибок, карантин и повторная обработка"),
    ("Таймауты и ограниченные повторы внешних вызовов", "таймауты и ограниченные повторы внешних вызовов"),
    ("Версия события/контракта", "версия события или контракта"),
    ("Контроли: ключ партиционирования applicationId, обёртку события", "Контроли: ключ партиционирования applicationId, обёртка события"),
    ("Контроли: ключ партиционирования applicationId, стандартную обёртку события", "Контроли: ключ партиционирования applicationId, стандартная обёртка события"),
    ("обёртку события, версия", "обёртка события, версия"),
    ("обёртку события, schemaVersion", "обёртка события, schemaVersion"),
    ("Архитектурное ядро: **условно готово: закрыть высокие риски**", "Архитектурное ядро: **условно готово по формальным правилам: есть внешние зависимости, которые нужно держать под контролем**"),
    ("Повторить тему: Данные, хранилища и проекции", "Дополнительно потренировать тему: данные, хранилища и проекции"),
    ("Усложните кейс: добавьте сбой внешней системы, повторное событие и повторная обработка после сбоя потребителя", "Усложните кейс: добавьте сбой внешней системы, повторную доставку события и восстановление после сбоя потребителя"),
)

_PREV_CLEAN_USER_TEXT_V8650C = _clean_user_text_v8650

def _dedupe_consecutive_lines_v8651(text: str) -> str:
    lines = str(text or "").splitlines()
    out = []
    prev_norm = None
    for line in lines:
        norm = re.sub(r"\s+", " ", line.strip()).lower()
        # Убираем только точные повторы подряд, чтобы не потерять разные места риска.
        if norm and norm == prev_norm:
            continue
        out.append(line)
        prev_norm = norm if norm else None
    return "\n".join(out)


def _clean_user_text_v8650(value: Any) -> Any:
    value = _PREV_CLEAN_USER_TEXT_V8650C(value)
    if isinstance(value, str):
        s = value
        for old, new in _MORE_TEXT_FIXES_V8651:
            s = s.replace(old, new)
        # Локально правим падеж только в списках контролей, но не ломаем фразы
        # "обязательную/единую/стандартную обёртку события".
        s = re.sub(r"(?<!обязательную )(?<!единую )(?<!стандартную )обёртку события,", "обёртка события,", s)
        s = _dedupe_consecutive_lines_v8651(s)
        return s
    if isinstance(value, list):
        return [_clean_user_text_v8650(x) for x in value]
    if isinstance(value, dict):
        return {k: _clean_user_text_v8650(v) for k, v in value.items()}
    return value

_PREV_LEARNING_MARKDOWN_V8650 = learning_markdown

def learning_markdown(case: Dict[str, Any], ev: Dict[str, Any] | None, base: Dict[str, Any] | None,
                      mode: str = "learning", validation_errors: List[str] | None = None) -> str:
    return _clean_user_text_v8650(_PREV_LEARNING_MARKDOWN_V8650(case, ev, base, mode, validation_errors))

_PREV_LEARNING_RESULT_HTML_V8650 = learning_result_html

def learning_result_html(ev: Dict[str, Any]) -> str:
    return _clean_user_text_v8650(_PREV_LEARNING_RESULT_HTML_V8650(ev))

# Применяем чистку к каталогу после объявления финальной функции.
for _case in CASES:
    for _key in ("title", "track", "brief", "goal"):
        if _case.get(_key):
            _case[_key] = _clean_user_text_v8650(_case[_key])
    if _case.get("hidden_traps"):
        _case["hidden_traps"] = _clean_user_text_v8650(_case["hidden_traps"])
    if _case.get("expected_controls"):
        _case["expected_controls"] = _clean_user_text_v8650(_case["expected_controls"])
CASE_BY_ID = {c["id"]: c for c in CASES}

# v8.6.53: версия учебного слоя для SaaS UI.
APP_LEARNING_VERSION = "8.6.56-polished-final"
CASE_CATALOG_VERSION = "2026-06-16-v9-saas-ui-polished"
