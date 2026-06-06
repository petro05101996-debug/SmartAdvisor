from urllib.parse import urlencode
from integration_architect_pro import parse_post, Engine


def test_service2_internal_worker_async_to_service3_human_report():
    case = {
        'ux_mode': 'advanced',
        'quick_description': (
            'Сервис 1 отправляет запрос в сервис 2. Сервис 2 принимает запрос, сохраняет состояние '
            'и должен асинхронно отправить запрос в сервис 3. Внутри сервиса 2 есть отдельный '
            'микросервис/worker, который читает из БД нужные записи и отправляет их в сервис 3.'
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
    assert form['report_detail'] == 'human'
    assert 'Сервис 2 API' in form['systems_matrix']
    assert 'Worker сервиса 2' in form['systems_matrix']
    assert 'Сервис 3' in form['systems_matrix']
    assert 'process_graph_json' in form and 'Worker сервиса 2' in form['process_graph_json']

    md = Engine().generate(form)['markdown']
    assert 'Сервис 1 отправляет запрос' in md
    assert 'Сервис 2 принимает и сохраняет задачу' in md
    assert 'Worker сервиса 2 читает нужные записи из БД' in md
    assert 'Worker асинхронно отправляет запрос в сервис 3' in md
    assert 'Retry loop при timeout/5xx сервиса 3' in md
    assert 'Ручное восстановление / reprocess' in md
    assert 'flowchart LR' in md
    assert 'async_start' in md
    assert 'timeout/retry' in md
    assert 'manual_recovery' in md

    forbidden = [
        'Draft SQL DDL',
        'Введённые матрицы полного описания процесса',
        'Матрица систем',
        'create table',
        '## 17B',
        'Специализированные сложные кейсы',
    ]
    for marker in forbidden:
        assert marker not in md
