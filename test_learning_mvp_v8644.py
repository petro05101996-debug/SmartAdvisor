# -*- coding: utf-8 -*-
from learning import list_cases, get_case, evaluate_reference, evaluate_learning_solution, validate_learning_catalog


def test_learning_case_library_has_paid_mvp_shape():
    cases = list_cases()
    assert len(cases) >= 10
    required = {'id', 'title', 'level', 'track', 'brief', 'goal', 'expected_controls', 'hidden_traps'}
    for case in cases:
        assert required.issubset(case.keys())
        assert case['expected_controls']
        assert case['hidden_traps']


def test_reference_solutions_are_valid_and_render_learning_reports():
    # В расширенной библиотеке 80+ кейсов. Полный markdown для каждого кейса
    # намеренно не рендерим в unit-тесте: для каталога есть быстрая deep-
    # проверка, а полноразмерные отчёты проверяем на репрезентативной выборке.
    catalog = validate_learning_catalog(deep=True)
    assert catalog['ok'], catalog['issues']
    cases = list_cases()
    sample = [cases[0], cases[len(cases)//2], cases[-1]]
    for case in sample:
        ev = evaluate_reference(case['id'])
        assert ev['ok']
        assert ev.get('base_ok') is True
        assert ev.get('learning_score', 0) >= 7.0
        md = ev.get('report_markdown') or ''
        assert '# Учебный разбор:' in md
        assert 'Профиль навыков' in md
        assert 'Следующие задания' in md
        assert 'Полный архитектурный отчёт ядра' in md


def test_invalid_learning_solution_gets_training_validation_feedback():
    case = list_cases()[0]
    ev = evaluate_learning_solution(case['id'], {'meta': {'name': 'bad'}, 'systems': [], 'steps': []})
    assert ev['ok']
    assert ev.get('base_ok') is False
    assert ev.get('validation_errors')
    assert 'Схема пока невалидна' in ev.get('report_markdown', '')


def test_unknown_case_is_rejected():
    ev = evaluate_learning_solution('missing-case', {})
    assert ev['ok'] is False
