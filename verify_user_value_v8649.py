# -*- coding: utf-8 -*-
"""User-value regression for v8.6.49.
Проверяет ровно те дефекты, которые нашли при пользовательском тесте:
- слабое решение не получает зачёт за контроли, которых пользователь не описал;
- эталон получает высокий учебный score;
- слабый устный ответ не оценивается как сильный;
- сильный ответ закрывает структуру собеседования;
- короткое резюме присутствует в markdown/html.
"""
from copy import deepcopy
from learning import get_case, evaluate_learning_solution, validate_learning_catalog, learning_result_html


def _weak_payload(case_id="bank-credit-bki-fraud"):
    case = get_case(case_id)
    payload = deepcopy(case["payload"])
    # Убираем реальные production-контроли и даже явное имя outbox, чтобы проверить,
    # что система не засчитает их из собственных рекомендаций.
    for step in payload["steps"]:
        step["compensation"] = ""
        step["retry"] = "none"
        step["idempotency"] = "none"
        step["timeout_ms"] = ""
        step["name"] = str(step.get("name", "")).replace("outbox", "запись статуса").replace("Outbox", "запись статуса")
    payload["meta"]["lookup_keys"] = "applicationId"
    payload["meta"]["fields"] = "applicationId,status,updatedAt"
    return payload


def main():
    case_id = "bank-credit-bki-fraud"
    weak = _weak_payload(case_id)
    weak_ev = evaluate_learning_solution(case_id, weak, mode="learning")
    assert weak_ev["ok"] and weak_ev["base_ok"]
    hit_ids = {h["id"] for h in weak_ev.get("control_hits", [])}
    assert "dlq_replay" not in hit_ids, hit_ids
    assert "timeouts" not in hit_ids, hit_ids
    assert "versioning" not in hit_ids, hit_ids
    assert weak_ev["learning_score"] <= 5.5, weak_ev["learning_score"]
    md = weak_ev["report_markdown"]
    assert "### Короткий вывод" in md
    assert "Три главных замечания" in md
    assert "Быстрые исправления" in md
    html = learning_result_html(weak_ev)
    assert "Короткий разбор" in html

    ref_ev = evaluate_learning_solution(case_id, get_case(case_id)["payload"], mode="reference")
    assert ref_ev["learning_score"] >= 9.0, ref_ev["learning_score"]
    assert not ref_ev.get("control_misses"), ref_ev.get("control_misses")

    weak_answer = "Я вызову сервис, потом отправлю событие в Kafka. Если ошибка, попробуем ещё раз."
    weak_int = evaluate_learning_solution(case_id, weak, mode="interview", answer_text=weak_answer)
    assert weak_int["learning_score"] <= 5.5, weak_int["learning_score"]
    assert weak_int["interview_answer_assessment"]["answer_score"] < 5.0
    assert weak_int["interview_answer_assessment"].get("red_flags")

    strong_answer = (
        "Сначала фиксирую границы процесса и участников: клиент, сервис заявок, БКИ, fraud, БД, Kafka, DWH и аудит. "
        "Синхронный клиентский путь отделяю от асинхронных событий. Внешние вызовы идут с timeout, circuit breaker, limited retry и fallback. "
        "Решение сохраняю транзакционно вместе с outbox. Событие публикую в Kafka с partition key по applicationId, event envelope, eventId, correlationId, occurredAt, eventType и schemaVersion. "
        "Consumer идемпотентен через eventId/inbox, есть DLQ, quarantine и replay. Контракт версионируется, backward compatibility проверяется contract tests. "
        "В эксплуатации смотрим lag, trace, correlationId, alerting, SLA и audit. На MVP можно упростить аналитику, но нельзя выбрасывать идемпотентность, outbox, DLQ и версионирование."
    )
    strong_int = evaluate_learning_solution(case_id, get_case(case_id)["payload"], mode="interview", answer_text=strong_answer)
    assert strong_int["learning_score"] >= 8.8, strong_int["learning_score"]
    dims = strong_int["interview_answer_assessment"].get("dimension_hits", {})
    assert all(dims.values()), dims

    catalog = validate_learning_catalog(deep=True)
    assert catalog["ok"], catalog["issues"][:5]
    assert catalog["case_count"] >= 83
    print({
        "ok": True,
        "weak_score": weak_ev["learning_score"],
        "weak_hits": sorted(hit_ids),
        "reference_score": ref_ev["learning_score"],
        "weak_interview_score": weak_int["learning_score"],
        "strong_interview_score": strong_int["learning_score"],
        "case_count": catalog["case_count"],
    })

if __name__ == "__main__":
    main()
