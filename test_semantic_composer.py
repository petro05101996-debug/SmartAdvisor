# -*- coding: utf-8 -*-
"""Regression tests for v8.4 semantic composer.

The composer must support a shallow, option-only user input path:
choose a universal chain -> get a valid analysis payload -> optionally add complexity layers.
"""
from engine import analyze
import ui


def _systems(*items):
    return [{"name": name, "role": role, "criticality": crit, "stability": stab}
            for name, role, crit, stab in items]


def _step(order, name, source, system, target, channel="rest", blocking="yes",
          timeout="500", retry="auto", idem="key", writes="no", dep="",
          comp="retry, manual review", failure="Повторить автоматически"):
    return {
        "order": order,
        "name": name,
        "source_system": source,
        "system": system,
        "target_system": target,
        "channel": channel,
        "blocking": blocking,
        "timeout_ms": timeout,
        "retry": retry,
        "idempotency": idem,
        "writes_entity": writes,
        "depends_on": dep,
        "compensation": comp,
        "failure_policy": failure,
        "component_type": "action",
        "data_in": "partition key / lookup key: businessId; correlationId пробрасывается через шаги",
        "data_out": "eventId, correlationId, status, statusVersion",
    }


def test_semantic_composer_is_main_entry_and_templates_are_secondary():
    html = ui.form_page()
    assert "Соберите цепочку из универсальных вариантов" in html
    assert "data-action=\"compose-choice\"" in html
    assert "data-action=\"compose-chain\"" in html
    assert "data-action=\"blueprint\"" not in html
    assert "abc_get_save_forward" not in html
    assert "А идёт" not in html
    assert "А просто" not in html
    assert "Сложный процесс, детали пока не ясны" not in html
    assert "Показать примеры, не основной путь" in html
    assert "Опционально: уточнить смысл вручную" in html
    assert "template-first" not in html


def test_simple_a_b_save_c_case_is_accepted_and_useful():
    payload = {
        "meta": {
            "name": "Черновик: А получает из Б, сохраняет и передаёт в В",
            "entity": "BusinessEntity",
            "goal": "Получить результат из системы Б, сохранить и передать в систему В.",
            "lookup_keys": "requestId + targetSystem; eventId для дедупликации",
            "statuses": "CREATED, REQUESTED_IN_B, RECEIVED_FROM_B, SAVED, SENT_TO_C, FAILED, NEEDS_MANUAL_REVIEW",
            "fields": "requestId:string|required|unique, eventId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required",
            "customer_visible": "mixed",
            "ordering": "per_entity",
        },
        "systems": _systems(
            ("Система А", "internal", "medium", "stable"),
            ("Сервис процесса", "internal", "high", "stable"),
            ("Система Б", "external", "high", "limited"),
            ("Система В", "external", "high", "limited"),
            ("БД процесса", "db", "high", "stable"),
        ),
        "steps": [
            _step(1, "Система А запускает процесс", "Система А", "Сервис процесса", "БД процесса", "db", writes="yes", dep="", comp="transaction, audit journal"),
            _step(2, "Сервис процесса идёт в Систему Б", "Сервис процесса", "Сервис процесса", "Система Б", "rest", timeout="1500", dep="1", comp="timeout, circuit breaker, retry with idempotencyKey"),
            _step(3, "Сервис процесса сохраняет результат", "Система Б", "Сервис процесса", "БД процесса", "db", writes="yes", dep="2", comp="transaction, unique requestId, status history"),
            _step(4, "Сервис процесса передаёт результат в Систему В", "Сервис процесса", "Сервис процесса", "Система В", "rest", timeout="1500", dep="3", comp="outbox, retry, manual review"),
        ],
    }
    res = analyze(payload)
    assert res["ok"] is True
    assert res.get("scenario", {}).get("main_flow")
    assert res.get("artifacts", {}).get("event_contract_skeleton") is not None
    # A simple shallow case should not be rejected merely because it lacks full manual detail.
    assert res.get("verdict", {}).get("color") in {"green", "yellow", "red"}


def test_ultra_complex_layered_case_is_accepted_and_finds_real_risks():
    payload = {
        "meta": {
            "name": "УК возвращает документы и операции разными потоками",
            "entity": "ApplicationStatus",
            "goal": "Банк должен видеть финал обработки документов и операций, сверять расхождения и отдавать данные в DWH.",
            "lookup_keys": "applicationId + documentId/operationId + eventId; partition key по applicationId",
            "statuses": "CREATED, SENT_TO_UK, DOC_STATUS_RECEIVED, OP_STATUS_RECEIVED, WAITING_RECONCILIATION, RECONCILED, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW",
            "fields": "applicationId:uuid|required|indexed, documentId:string|indexed, operationId:string|indexed, eventId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required, statusVersion:int|required",
            "customer_visible": "mixed",
            "money": "direct",
            "regulatory": "yes",
            "ordering": "per_entity",
            "read_freq": "high",
            "load_rps": "1200",
            "peak_factor": "5",
            "replacing_legacy": "yes",
        },
        "systems": _systems(
            ("Банк", "internal", "critical", "stable"),
            ("Сервис процесса", "internal", "critical", "stable"),
            ("УК", "external", "critical", "limited"),
            ("Kafka", "broker", "critical", "stable"),
            ("БД процесса", "db", "critical", "stable"),
            ("Сервис сверки", "internal", "high", "stable"),
            ("DWH", "analytics", "medium", "stable"),
            ("Legacy consumer", "legacy", "medium", "unstable"),
            ("Security layer", "internal", "high", "stable"),
        ),
        "steps": [
            _step(1, "Банк создаёт заявку и сохраняет начальный статус", "Банк", "Сервис процесса", "БД процесса", "db", timeout="200", writes="yes", comp="transaction, audit journal, status CREATED"),
            _step(2, "Сервис процесса отправляет документы в УК", "Сервис процесса", "Сервис процесса", "УК", "rest", timeout="2000", dep="1", comp="outbox, timeout, circuit breaker, retry with idempotencyKey"),
            _step(3, "УК публикует статусы документов", "УК", "УК", "Kafka", "kafka", "no", "", "auto", "key", "no", "2", "outbox, DLQ, replay", "DLQ / replay"),
            _step(4, "УК публикует статусы операций", "УК", "УК", "Kafka", "kafka", "no", "", "auto", "key", "no", "2", "outbox, DLQ, replay", "DLQ / replay"),
            _step(5, "Сервис процесса принимает статусы документов и дедуплицирует", "Kafka", "Сервис процесса", "БД процесса", "kafka", "no", "", "auto", "key", "yes", "3", "Inbox, unique eventId, replay, status history", "DLQ / replay"),
            _step(6, "Сервис процесса принимает статусы операций и дедуплицирует", "Kafka", "Сервис процесса", "БД процесса", "kafka", "no", "", "auto", "key", "yes", "4", "Inbox, unique eventId, replay, status history", "DLQ / replay"),
            _step(7, "Сервис сверки ждёт обе ветки и сверяет расхождения", "БД процесса", "Сервис сверки", "БД процесса", "batch", "no", "", "manual", "natural", "yes", "5,6", "fan-in window, reconciliation, timeout ожидания парной ветки", "Ручной разбор"),
            _step(8, "Security layer маскирует чувствительные поля для витрин", "БД процесса", "Security layer", "DWH", "cdc", "no", "", "auto", "natural", "no", "7", "watermark, masking, retention, replay/resync", "Replay / resync"),
            _step(9, "Legacy consumer временно получает совместимый формат", "Kafka", "Legacy consumer", "Legacy consumer", "kafka", "no", "", "auto", "key", "no", "5,6", "adapter, backward compatibility, dual-run, rollback", "DLQ / replay"),
            _step(10, "Оператор разбирает зависшие или противоречивые статусы", "Сервис сверки", "Сервис сверки", "БД процесса", "rest", "no", "", "manual", "natural", "yes", "7", "manual review, runbook, correction journal, replay", "Ручной разбор"),
        ],
    }
    res = analyze(payload)
    assert res["ok"] is True
    rules = {f["rule"] for f in res.get("findings", [])}
    assert "callback_inbox" not in rules  # there is Inbox/idempotency on inbound statuses
    assert "ordering" not in rules  # partition key is stated
    assert res.get("checklist", {}).get("items")
    assert res.get("schema", {}).get("ddl")
    assert res.get("scenario", {}).get("error_flows")
