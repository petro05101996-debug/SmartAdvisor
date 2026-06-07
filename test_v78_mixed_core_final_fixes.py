import json
from integration_architect_pro import Engine, detect_primary_and_modifiers


def _steps(rows):
    return json.dumps([
        {"order": i + 1, "actorLabel": actor, "action": action, "object": obj}
        for i, (actor, action, obj) in enumerate(rows)
    ], ensure_ascii=False)


def test_audit_privacy_erasure_uses_primary_modifiers_engine_path():
    form = {
        "business_case": "audit",
        "simple_situation": "audit",
        "business_object": "Клиентские данные",
        "business_result_timing": "Можно позже",
        "business_result_type": "Удаление/исправление ПДн",
        "business_criticality": "Потерять данные",
        "business_steps_json": _steps([
            ("Клиент", "Запрашивает удаление ПДн", "Клиентские данные"),
            ("Внутренняя система", "Проверяет legal hold", "Клиентские данные"),
        ]),
        "business_constraints_json": json.dumps(["pii", "regulatory", "privacy_erasure", "replay"], ensure_ascii=False),
    }
    detected = detect_primary_and_modifiers(form, "audit")
    assert detected["primary"] == "privacy_erasure_pipeline"

    res = Engine().generate(form)
    assert res["primary_specialized_case"] == "privacy_erasure_pipeline"
    assert "regulatory_process" in res["secondary_modifiers"]
    assert "personal_data_exchange" in res["secondary_modifiers"]
    assert "Legal Hold Check" in res["case_schema"]
    assert "Per-System Erasure Tasks" in res["case_schema"]
    md = res["markdown"]
    assert "legal hold" in md.lower() or "Legal Hold" in md
    assert "Receipts" in md or "receipt" in md.lower()
    assert "retention" in md.lower()
    assert "audit" in md.lower()


def test_callback_compensation_saga_keeps_callback_modifier():
    form = {
        "business_case": "external_check",
        "simple_situation": "callback",
        "business_object": "Заявка",
        "business_result_timing": "Внешняя система ответит позже",
        "business_result_type": "Обновлён статус",
        "business_criticality": "Потерять данные",
        "business_steps_json": _steps([
            ("Внутренняя система", "Отправляет запрос", "Заявка"),
            ("Внешняя система", "Получает ответ позже", "Заявка"),
            ("Внутренняя система", "Компенсирует / откатывает шаг", "Заявка"),
        ]),
        "business_constraints_json": json.dumps(["unstable_external", "compensation"], ensure_ascii=False),
    }
    res = Engine().generate(form)
    assert res["primary_specialized_case"] == "saga_state_machine"
    assert "webhook_callback" in res["secondary_modifiers"]
    assert "external_dependency" in res["secondary_modifiers"]
    assert "unstable_external_provider" in res["secondary_modifiers"]
    md = res["markdown"]
    assert "Callback API" in md
    assert "callback inbox" in md.lower()
    assert "idempotent callback transition" in md
    assert "polling fallback" in md
    assert "reconciliation" in md.lower()


def test_business_first_green_readiness_has_no_required_field_gaps():
    form = {
        "business_case": "reporting",
        "simple_situation": "dwh",
        "business_object": "Отчётные данные",
        "business_result_timing": "Данные нужны для отчёта",
        "business_result_type": "Данные попали в отчётность",
        "business_criticality": "Потерять данные",
        "business_steps_json": _steps([
            ("Внутренняя система", "Меняет данные", "Отчётные данные"),
            ("Внутренняя система", "Передаёт в отчётность", "Отчётные данные"),
            ("Отчётный контур", "Проверяет полноту", "Отчётные данные"),
        ]),
        "business_constraints_json": json.dumps(["replay", "regulatory"], ensure_ascii=False),
    }
    res = Engine().generate(form)
    readiness = res["readiness"]
    assert readiness["score"] >= 70
    assert readiness["status"] == "GREEN"
    gaps = readiness.get("gaps") or []
    assert not any("Не заполнено обязательное поле" in str(x) for x in gaps)
    assert "Не заполнено обязательное поле" not in res["markdown"]


def test_mixed_application_saga_still_not_overridden_by_modifiers():
    form = {
        "business_case": "application_creation",
        "simple_situation": "async_worker",
        "business_object": "Заявка",
        "business_result_timing": "Нужно принять сейчас, результат получить позже",
        "business_result_type": "Обновлён статус",
        "business_criticality": "Потерять данные",
        "business_steps_json": _steps([
            ("Клиент", "Создаёт заявку / запрос", "Заявка"),
            ("Внутренняя система", "Принимает заявку", "Заявка"),
            ("Внутренняя система", "Проверяет данные", "Заявка"),
            ("Внешняя система", "Обрабатывает запрос", "Заявка"),
            ("Внутренняя система", "Обновляет статус", "Статус"),
        ]),
        "business_constraints_json": json.dumps(["highload", "regulatory", "pii", "many_consumers", "compensation", "multi_tenant", "active_active"], ensure_ascii=False),
    }
    res = Engine().generate(form)
    assert res["primary_specialized_case"] == "saga_state_machine"
    assert "multi_tenant_noisy_neighbor" in res["secondary_modifiers"]
    assert "Process State DB" in res["case_schema"]
    assert "Compensation" in res["case_schema"]
    assert not res["case_schema"].startswith("Shared Stream")
    md = res["markdown"]
    assert "tenantId key" in md
    assert "Process State DB" in md
    assert "compensation_failed" in md
