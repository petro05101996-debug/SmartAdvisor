from engine import analyze
from report import markdown_report


def test_v8672_no_public_production_contradictions():
    payload = {
        'systems': [{'name':'A'}, {'name':'B'}],
        'steps': [{'name':'sync call Без таймаут', 'source_system':'A', 'target_system':'B', 'channel':'rest', 'blocking':True}],
        'meta': {'money':'no', 'sla_ms':1000},
    }
    res = analyze(payload)
    md = markdown_report(res)
    assert 'Без таймаут ' not in md
    assert 'промышленный запуск-ready' not in md
    assert 'готово к промышленному запуску-ready' not in md


def test_v8672_diagnostics_imports():
    import app
    payload = app._diagnostics_payload(deep=True)
    assert payload['ok'] is True
    assert '8.6.72' in payload['version']
    assert payload['checks']['database'] is True
