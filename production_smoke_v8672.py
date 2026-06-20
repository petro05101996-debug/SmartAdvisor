#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production smoke for SmartAdvisor v8.6.72.

Checks the deployable surface, not only unit rules:
- imports and direct analyze() on raw/production design cases;
- public markdown has no known contradiction markers;
- local HTTP server exposes health/version/analyze/run markdown.
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from engine import analyze
from report import markdown_report

BAD_TEXT = [
    r"Без таймаут\b",
    r"промышленный запуск-ready",
    r"готово к промышленному запуску-ready",
    r"0\.0/10.*production-ready",
]

RAW_CASE = {
    "systems": [
        {"name": "UK", "kind": "external"},
        {"name": "BankStatusAPI", "kind": "service"},
        {"name": "InboxDB", "kind": "db"},
        {"name": "MappingDB", "kind": "db"},
        {"name": "Kafka", "kind": "broker"},
        {"name": "DWH", "kind": "analytics"},
    ],
    "steps": [
        {"name": "получить статус", "source_system": "UK", "target_system": "BankStatusAPI", "channel": "rest", "blocking": True, "writes": True},
        {"name": "сохранить входящее событие", "source_system": "BankStatusAPI", "target_system": "InboxDB", "channel": "db", "writes": True, "idempotency_key": "eventId"},
        {"name": "найти внутренний идентификатор операции", "source_system": "BankStatusAPI", "target_system": "MappingDB", "channel": "db", "blocking": True},
        {"name": "опубликовать статус", "source_system": "BankStatusAPI", "target_system": "Kafka", "channel": "kafka", "writes": True},
        {"name": "загрузить событие в аналитику", "source_system": "Kafka", "target_system": "DWH", "channel": "kafka", "writes": True},
    ],
    "meta": {"money": "indirect", "client_facing": True, "sla_ms": 0},
}

PRODUCTION_CASE = {
    "systems": RAW_CASE["systems"],
    "steps": [
        {"name": "получить статус с eventId eventType eventVersion occurredAt operationId correlationId", "source_system": "UK", "target_system": "BankStatusAPI", "channel": "rest", "blocking": True, "writes": True, "timeout_ms": 3000, "idempotency_key": "eventId"},
        {"name": "сохранить входящее событие в Inbox с audit journal retention", "source_system": "BankStatusAPI", "target_system": "InboxDB", "channel": "db", "writes": True, "idempotency_key": "eventId", "retry": "limited"},
        {"name": "найти внутренний идентификатор операции с failed_mapping manual review replay", "source_system": "BankStatusAPI", "target_system": "MappingDB", "channel": "db", "blocking": True, "timeout_ms": 1000},
        {"name": "записать outbox и опубликовать статус в Kafka partition key operationId DLQ replay backoff limit", "source_system": "BankStatusAPI", "target_system": "Kafka", "channel": "kafka", "writes": True, "idempotency_key": "eventId", "retry": "limited", "dlq": True, "outbox": True, "replay": True, "ordering_key": "operationId", "correlation_id": True},
        {"name": "загрузить событие в аналитику с reconciliation runbook lag alert", "source_system": "Kafka", "target_system": "DWH", "channel": "kafka", "writes": True, "idempotency_key": "eventId", "retry": "limited", "dlq": True, "replay": True, "reconciliation": True},
    ],
    "meta": {
        "money": "indirect",
        "client_facing": True,
        "sla_ms": 3000,
        "goal": "Доставить подтверждённый статус операции из УК в банк, ресурсные системы и аналитический контур без потерь и дублей",
        "entity": "Operation",
        "fields": "operationId:string|required|unique|indexed, ukOperationId:string|required|indexed, operationType:string|required|indexed, status:string|required, statusVersion:int|required, correlationId:string|required|indexed",
        "lookup_keys": "operationId + operationType + sourceSystem",
        "statuses": "RECEIVED, VALIDATED, MAPPED, PUBLISHED, FAILED_MAPPING, FAILED_PUBLISHING, CONSUMED, RECONCILED",
        "ordering": "per_entity",
        "load_rps": 200,
        "peak_factor": 5,
        "status_model": ["RECEIVED", "VALIDATED", "MAPPED", "PUBLISHED", "FAILED_MAPPING", "FAILED_PUBLISHING"],
        "event_envelope": True,
        "event_version": True,
        "correlation_id": True,
        "reconciliation": True,
        "observability": True,
        "runbook": True,
        "retention_policy": True,
    },
}


def _assert_no_bad_text(md: str) -> None:
    for pattern in BAD_TEXT:
        if re.search(pattern, md, flags=re.S | re.I):
            raise AssertionError(f"bad public markdown text: {pattern}")


def _get_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _request(url, data=None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as resp:
        payload = resp.read().decode("utf-8")
        ctype = resp.headers.get("Content-Type", "")
        return resp.status, ctype, payload


def check_direct():
    raw = analyze(RAW_CASE)
    prod = analyze(PRODUCTION_CASE)
    assert raw.get("ok"), raw
    assert prod.get("ok"), prod
    raw_readiness = raw.get("readiness_matrix") or []
    prod_readiness = prod.get("readiness_matrix") or []
    assert any((item.get("name") == "Готово к production" and not item.get("ok")) for item in raw_readiness), raw_readiness
    assert any((item.get("name") == "Готово к production" and item.get("ok")) for item in prod_readiness), prod_readiness
    assert (prod.get("verdict") or {}).get("score", 0) >= 8.5, prod.get("verdict")
    md = markdown_report(prod)
    assert "Рабочий проектный пакет" in md
    assert "Карта процесса source → target" in md
    _assert_no_bad_text(md)
    return {"raw_score": (raw.get("verdict") or {}).get("score"), "production_score": (prod.get("verdict") or {}).get("score"), "markdown_chars": len(md)}


def check_http():
    port = _get_free_port()
    app_dir = tempfile.mkdtemp(prefix="sa_smoke_")
    env = os.environ.copy()
    env.update({"HOST": "127.0.0.1", "PORT": str(port), "APP_DIR": app_dir})
    proc = subprocess.Popen([sys.executable, "-u", "app.py"], cwd=Path(__file__).parent, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        base = f"http://127.0.0.1:{port}"
        last_error = None
        for _ in range(60):
            try:
                status, ctype, body = _request(base + "/health")
                if status == 200 and json.loads(body).get("ok"):
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.1)
        else:
            raise AssertionError(f"server did not become healthy: {last_error}")
        status, ctype, version_body = _request(base + "/api/version")
        version = json.loads(version_body)
        assert status == 200 and version.get("ok") and "8.6.72" in version.get("version", ""), version
        status, ctype, html = _request(base + "/")
        assert status == 200 and "SmartAdvisor" in html
        status, ctype, analyze_body = _request(base + "/api/analyze", PRODUCTION_CASE)
        analyzed = json.loads(analyze_body)
        assert analyzed.get("ok") and analyzed.get("id"), analyzed
        status, ctype, md = _request(base + f"/run/{analyzed['id']}.md")
        assert status == 200 and "Рабочий проектный пакет" in md
        _assert_no_bad_text(md)
        return {"port": port, "version": version.get("version"), "run_id": analyzed.get("id")}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    result = {"direct": check_direct(), "http": check_http(), "ok": True}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
