# -*- coding: utf-8 -*-
from engine import analyze


def _payload(steps):
    return {
        'meta': {'name': 'Проверка зависимостей'},
        'systems': [{'name': n, 'role': 'internal'} for n in ['A', 'B', 'C', 'D']],
        'steps': steps,
    }


def test_secondary_fanin_dependency_cycle_is_rejected():
    res = analyze(_payload([
        {'order': 1, 'name': 'Шаг 1', 'system': 'A', 'channel': 'rest', 'depends_on': '2,3'},
        {'order': 2, 'name': 'Шаг 2', 'system': 'B', 'channel': 'rest'},
        {'order': 3, 'name': 'Шаг 3', 'system': 'C', 'channel': 'rest', 'depends_on': '1'},
    ]))
    assert not res['ok']
    assert any('Циклическая зависимость' in x for x in res['errors'])


def test_deep_secondary_fanin_dependency_cycle_is_rejected():
    res = analyze(_payload([
        {'order': 1, 'name': 'Шаг 1', 'system': 'A', 'channel': 'rest', 'depends_on': '2,4'},
        {'order': 2, 'name': 'Шаг 2', 'system': 'B', 'channel': 'rest'},
        {'order': 3, 'name': 'Шаг 3', 'system': 'C', 'channel': 'rest', 'depends_on': '1'},
        {'order': 4, 'name': 'Шаг 4', 'system': 'D', 'channel': 'rest', 'depends_on': '3'},
    ]))
    assert not res['ok']
    assert any('Циклическая зависимость' in x for x in res['errors'])


def test_valid_fanin_dag_is_still_allowed():
    res = analyze(_payload([
        {'order': 1, 'name': 'Ветка A', 'system': 'A', 'channel': 'rest'},
        {'order': 2, 'name': 'Ветка B', 'system': 'B', 'channel': 'rest'},
        {'order': 3, 'name': 'Сведение веток', 'system': 'C', 'channel': 'rest', 'depends_on': '1,2'},
    ]))
    assert res['ok'], res.get('errors')
    assert res['model']['steps'][2]['is_join'] is True
