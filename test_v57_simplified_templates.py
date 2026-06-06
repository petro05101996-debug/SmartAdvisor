from pathlib import Path
from urllib.parse import urlencode

from integration_architect_pro import Engine, parse_post, result_page


def test_v57_ui_has_human_templates_and_no_advanced_default_checked_risks():
    html = Path('integration_architect_pro.py').read_text(encoding='utf-8')
    assert 'Сервис принял запрос и обработал позже' in html
    assert 'Собрать рекомендуемую цепочку автоматически' in html
    assert "value='service2_async_worker'" in html
    assert "data-scenario='help_me_choose'" in html
    assert "data-scenario='service2_worker'" in html
    assert "name='risk_duplicate_event' value='yes' checked" not in html
    assert "name='risk_lost_event' value='yes' checked" not in html
    assert "name='risk_external_timeout' value='yes' checked" not in html
    assert "name='risk_traceability' value='yes' checked" not in html


def test_v57_quick_free_text_auto_builds_worker_chain_and_human_report():
    form = parse_post(urlencode({
        'ux_mode': 'quick',
        'quick_description': 'Сервис 1 отправляет запрос в сервис 2. Сервис 2 принимает запрос, сохраняет состояние. Внутри сервиса 2 есть worker, который читает из БД нужные записи и асинхронно отправляет запрос в сервис 3.',
        'quick_goal': 'design_new',
        'quick_speed': 'async_status',
        'quick_broker': 'unknown',
        'quick_external': 'yes',
    }))
    assert 'process_graph_json' in form
    assert 'Worker сервиса 2' in form['process_graph_json']
    res = Engine().generate(form)
    html = result_page(res, 'rid', 'report.md')
    assert 'Визуальная схема потока процесса' in html
    assert 'Сервис 2 принимает и сохраняет задачу' in html
    assert 'Worker сервиса 2 читает нужные записи из БД' in html
    assert 'Worker асинхронно отправляет запрос в сервис 3' in html
    for forbidden in ['Draft SQL DDL', 'create table', 'Введённые матрицы полного описания процесса']:
        assert forbidden not in res['markdown']
