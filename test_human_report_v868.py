from engine import analyze
from report import markdown_report


def _base():
    return {
        'meta': {'name': 'Проверка человеческого отчёта', 'entity': 'Request'},
        'systems': [{'name': 'A', 'role': 'client'}, {'name': 'B', 'role': 'external'}],
        'steps': [
            {'order': 1, 'name': 'A вызывает B', 'system': 'B', 'channel': 'rest',
             'blocking': 'yes', 'timeout_ms': 1000, 'depends_on': 0,
             'source_system': 'A', 'target_system': 'B'},
        ],
    }


def test_report_has_human_explanation_structure_v868():
    md = markdown_report(analyze(_base()))
    assert '## Короткий человеческий вывод' in md
    assert '### Объяснение по шагам' in md
    assert '**Что:**' in md
    assert '**Где:**' in md
    assert '**Почему:**' in md
    assert '**Почему не другой вариант:**' in md
    assert '**Что проверить перед выпуском:**' in md
