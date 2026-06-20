from engine import analyze
from process_parser import parse_process

RAW_BANK_UK_CASE = """
процесс: Обратный поток статусов операций и документов от УК в банк
сущность: OperationStatus, DocumentStatus
деньги: indirect
клиенту: да
sla: 0
нагрузка: 120 x5

получить статус операции от УК | УК(внешняя, нестабильная) -> BankStatusAPI | rest | пишет, блокирует, таймаут:3000
сохранить входящее событие в inbox | BankStatusAPI -> InboxDB(база) | db | пишет, идемпотентность:key
проверить контракт и версию события | BankStatusAPI -> ContractValidator | internal | блокирует
сопоставить внешний id УК с внутренним operationId банка | BankStatusAPI -> MappingDB(база) | db | блокирует
обновить статус операции | BankStatusAPI -> OperationalDB(база) | db | пишет, идемпотентность:key
опубликовать обогащённый статус операции | BankStatusAPI -> Kafka(брокер) | kafka | retry:auto, идемпотентность:key
прочитать статус ресурсной системой кредитов | Kafka -> CreditResourceSystem | kafka | неблокирует, идемпотентность:key
прочитать статус ресурсной системой документов | Kafka -> DocumentResourceSystem | kafka | неблокирует, идемпотентность:key
отправить событие в DWH для аналитики | Kafka -> DWH(аналитика) | kafka | неблокирует
разобрать ошибочные события вручную | DLQ(брокер) -> SupportOperator | queue | retry:manual
"""

READY_BANK_UK_CASE = """
процесс: Обратный поток статусов операций и документов от УК в банк
сущность: OperationStatus, DocumentStatus
деньги: indirect
клиенту: да
regulatory: да
sla: 0
нагрузка: 120 x5
цель: обеспечить correlationId traceparent, reconciliation сверку, status history, metrics dashboard alert, retention, replay runbook, source of truth BankStatusAPI owner Bank
порядок: per_entity
статусы: RECEIVED, VALIDATED, MAPPED, PUBLISHED, FAILED_VALIDATION, FAILED_MAPPING, FAILED_PUBLISHING, SENT_TO_DLQ, NEEDS_MANUAL_REVIEW
ключи: operationId + sourceSystem + statusType
поля: operationId:string|required|unique|indexed, sourceSystem:string|required|indexed, statusType:string|required|indexed, statusVersion:int|required, eventId:string|required|unique|indexed, correlationId:string|required|indexed

получить статус операции от УК с requestId correlationId и моделью ошибок 4xx 5xx | УК(внешняя, нестабильная) -> BankStatusAPI | rest | пишет, блокирует, таймаут:3000
сохранить входящее событие в inbox audit с eventId unique и retention | BankStatusAPI -> InboxDB(база) | db | пишет, идемпотентность:key
проверить schema contract eventVersion и problem+json модель ошибок | BankStatusAPI -> ContractValidator | rest | блокирует, таймаут:1500
сопоставить внешний id УК с внутренним operationId банка через unique mapping manual review | BankStatusAPI -> MappingDB(база) | db | блокирует, таймаут:1000
обновить статус операции statusVersion optimistic lock status history audit | BankStatusAPI -> OperationalDB(база) | db | пишет, идемпотентность:key
записать событие в transactional outbox eventId eventType eventVersion occurredAt operationId correlationId producer payload | BankStatusAPI -> OutboxDB(база) | db | пишет, идемпотентность:key
publisher публикует outbox в Kafka с partition key operationId retry backoff limit DLQ replay | OutboxPublisher -> Kafka(брокер) | kafka | retry:auto, идемпотентность:key
прочитать статус ресурсной системой кредитов с retry backoff limit DLQ replay idempotent consumer | Kafka -> CreditResourceSystem | kafka | неблокирует, идемпотентность:key
прочитать статус ресурсной системой документов с retry backoff limit DLQ replay idempotent consumer | Kafka -> DocumentResourceSystem | kafka | неблокирует, идемпотентность:key
отправить событие в DWH асинхронно best-effort с retry backoff DLQ replay reconciliation | Kafka -> DWH(аналитика) | kafka | неблокирует, идемпотентность:key
разобрать ошибочные события вручную из DLQ с owner support replay runbook | DLQ(брокер) -> SupportOperator | queue | retry:manual
"""


def _matrix(res):
    return {x["name"]: x for x in res["readiness_matrix"]}


def test_real_bank_uk_raw_case_blocks_dev_and_production():
    res = analyze(parse_process(RAW_BANK_UK_CASE))
    assert res["ok"] is True
    assert res["model"]["meta"]["money"] == "indirect"
    assert res["verdict"]["score"] <= 7.5
    m = _matrix(res)
    assert m["Готово к передаче в разработку"]["ok"] is False
    assert m["Готово к production"]["ok"] is False
    assert "не к разработке" in res["project_package"]["executive_summary"]["readiness"]


def test_kafka_fanout_consumers_depend_on_producer_not_each_other():
    res = analyze(parse_process(RAW_BANK_UK_CASE))
    kafka_consumers = [s for s in res["model"]["steps"] if s.get("source_system") == "Kafka"]
    assert kafka_consumers
    assert {s["depends_on"] for s in kafka_consumers[:3]} == {6}


def test_ready_bank_uk_case_produces_project_package_and_production_green():
    res = analyze(parse_process(READY_BANK_UK_CASE))
    assert res["ok"] is True
    assert res["verdict"]["counts"] == {"critical": 0, "high": 0, "medium": 0, "info": 0}
    assert res["completeness"]["score_pct"] >= 90
    m = _matrix(res)
    assert m["Готово к передаче в разработку"]["ok"] is True
    assert m["Готово к production"]["ok"] is True
    pkg = res["project_package"]
    assert pkg["executive_summary"]["readiness"] == "готово к production"
    assert pkg["contracts"]
    assert pkg["business_entities"]
    assert pkg["status_model"]
    assert pkg["adr"]
