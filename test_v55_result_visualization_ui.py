from urllib.parse import urlencode

from integration_architect_pro import Engine, parse_post, result_page


def test_result_page_renders_real_process_flow_visualization_from_graph():
    case = {
        'ux_mode': 'advanced',
        'quick_description': (
            'Сервис 1 отправляет запрос в сервис 2. Сервис 2 принимает запрос, сохраняет состояние '
            'и должен асинхронно отправить запрос в сервис 3. Внутри сервиса 2 есть worker, который '
            'читает из БД нужные записи и отправляет их в сервис 3.'
        ),
        'quick_goal': 'design_new',
        'quick_speed': 'async_status',
        'quick_broker': 'unknown',
        'quick_external': 'yes',
        'constraint_orchestration': 'orchestrator',
        'constraint_chain_depth': 'multi_level',
        'constraint_source_change': 'partial',
        'constraint_new_infra': 'existing_only',
        'advanced_complexity': ['retry_loop', 'reconciliation'],
        'risk_duplicate_event': 'yes',
        'risk_external_timeout': 'yes',
        'risk_traceability': 'yes',
    }
    form = parse_post(urlencode(case, doseq=True))
    res = Engine().generate(form)
    html = result_page(res, 'rid-demo', 'report.md')

    assert 'Визуальная схема потока процесса' in html
    assert 'complex-flow-map' in html
    assert 'Это нормальная схема процесса, а не набор бессвязных карточек' in html
    assert 'Сервис 2 принимает и сохраняет задачу' in html
    assert 'Worker сервиса 2 читает нужные записи из БД' in html
    assert 'Worker асинхронно отправляет запрос в сервис 3' in html
    assert 'Архитектурные акценты' in html
    assert 'роль: участник решения' not in html
