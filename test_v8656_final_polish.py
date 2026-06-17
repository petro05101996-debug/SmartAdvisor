# -*- coding: utf-8 -*-
from learning import build_learning_visual_payload, evaluate_learning_solution, get_case
import ui


def test_visual_builder_empty_selection_is_not_reference_v8656():
    case_id = 'bank-credit-bki-fraud'
    built = build_learning_visual_payload(case_id, [], kind='selected')
    blob = str(built['payload']).lower()
    assert built['ok'] is True
    assert built['selected_count'] == 0
    assert built['payload'] != get_case(case_id)['payload']
    assert 'outbox' not in blob
    assert 'dlq' not in blob
    assert 'schemaversion' not in blob
    assert 'контроли не выбраны' in built['message'].lower()


def test_visual_builder_selected_controls_are_reflected_in_payload_v8656():
    case_id = 'bank-credit-bki-fraud'
    partial = build_learning_visual_payload(case_id, ['outbox', 'timeouts'], kind='selected')
    blob = str(partial['payload']).lower()
    assert partial['selected_count'] == 2
    assert 'outbox' in blob or 'исходящ' in blob
    assert 'timeout' in blob or 'таймаут' in blob
    assert 'dlq' not in blob
    assert 'schema' not in blob


def test_visual_builder_reference_keeps_full_reference_payload_v8656():
    case_id = 'bank-credit-bki-fraud'
    case = get_case(case_id)
    ref = build_learning_visual_payload(case_id, [], kind='reference')
    assert ref['selected_count'] == len(case['expected_controls'])
    assert ref['payload'] == case['payload']


def test_learning_ui_no_longer_defaults_controls_to_checked_v8656():
    html = ui.learning_case_page('bank-credit-bki-fraud')
    assert '8.6.56-polished-final' in html
    assert '/api/learning/visual-payload' in html
    assert 'Собрать по моим выбранным контролям' in html
    # Пользователь должен сам выбрать контроли; эталон доступен отдельной кнопкой.
    assert 'class="visual-control" value="outbox" data-label=' in html
    assert 'value="outbox" data-label="Outbox для публикации события после фиксации решения" checked' not in html
