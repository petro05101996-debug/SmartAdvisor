# -*- coding: utf-8 -*-
from learning import (
    list_cases, get_case, evaluate_learning_solution, evaluate_reference,
    learning_hints, validate_learning_catalog, save_learning_attempt,
    progress_for_learner, learning_attempt_markdown,
)


def test_learning_catalog_is_production_sized_and_valid():
    cases = list_cases()
    assert len(cases) >= 20
    report = validate_learning_catalog(deep=False)
    assert report["ok"], report["issues"]
    assert report["summary"]["case_count"] == len(cases)
    assert "skills" in report["summary"] and len(report["summary"]["skills"]) == 8


def test_learning_reference_has_comparison_and_hints():
    case = list_cases()[0]
    ev = evaluate_reference(case["id"])
    assert ev["ok"] and ev["base_ok"] is True
    assert ev["learning_score"] >= 7.0
    assert ev["reference_comparison"]["reference_route_count"] >= 3
    assert ev["reference_comparison"]["control_miss_count"] == 0
    assert "Сравнение с эталоном" in ev["report_markdown"]
    h = learning_hints(case["id"], 3)
    assert h["ok"] and h["hints"]


def test_learning_attempts_are_persisted_and_progress_is_available(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DIR", str(tmp_path))
    case = list_cases()[0]
    payload = get_case(case["id"])["payload"]
    ev = evaluate_learning_solution(case["id"], payload, mode="learning")
    aid = save_learning_attempt("learner-test", case["id"], payload, ev, mode="learning")
    md = learning_attempt_markdown(aid)
    assert md and "Учебный разбор" in md
    p = progress_for_learner("learner-test")
    assert p["ok"] and p["attempt_count"] == 1
    assert p["solved_case_count"] == 1
    assert p["badges"]


def test_invalid_solution_keeps_training_feedback():
    case = list_cases()[0]
    ev = evaluate_learning_solution(case["id"], {"meta": {"name": "bad"}, "systems": [], "steps": []})
    assert ev["ok"] and ev["base_ok"] is False
    assert ev["learning_score"] == 0.0
    assert ev["validation_errors"]
