import engine
import process_parser
import report
import ui
import sa_agent


def sample_payload():
    return process_parser.parse_process('''
процесс: Обратный поток статусов УК
сущность: Operation
деньги: indirect
цель: Получить статусы операций от УК и передать их ресурсным системам
порядок: per_entity
получить статус | УК(внешняя) -> Банк | rest | блокирует, таймаут:1500
сохранить входящее событие | Банк -> InboxDB(база) | db | пишет, идемпотентность:key
сопоставить внешний ID | Банк -> MappingDB(база) | db | блокирует
опубликовать статус | Банк -> Kafka | kafka | retry:auto, идемпотентность:key
прочитать ресурсной системой | Kafka -> ResourceSystem | kafka | retry:auto, идемпотентность:key
выгрузить в DWH | Kafka -> DWH(аналитика) | kafka | retry:auto, идемпотентность:key
''')


def test_project_navigator_outputs_working_artifacts():
    res = engine.analyze(sample_payload())
    assert res['ok']
    assert res['product_readiness']['positioning'].startswith('архитектурный ревьюер')
    assert {m['id'] for m in res['design_modes']} >= {'review_solution', 'design_integration', 'prepare_documentation', 'interview_case'}
    assert len(res['readiness_matrix']) == 4
    assert any(x['name'] == 'Готово к передаче в разработку' for x in res['readiness_matrix'])
    pkg = res['project_package']
    assert pkg['process_map'][0]['from'] == 'УК'
    assert pkg['process_map'][0]['to'] == 'Банк'
    assert pkg['contracts']
    assert pkg['errors_by_step']
    assert pkg['adr']
    assert res['questions']['business']
    assert res['questions']['development']
    assert res['solution_review']['first_actions']


def test_report_and_ui_show_project_package():
    res = engine.analyze(sample_payload())
    md = report.markdown_report(res)
    assert '# Рабочий проектный пакет' in md
    assert 'Матрица готовности' in md
    assert 'Карта процесса source → target' in md
    html = ui.result_page('0' * 32, res)
    assert 'Project Navigator' in html
    assert 'Рабочий проектный пакет' in html
    assert 'УК' in html and 'Банк' in html


def test_sa_agent_product_review_text_api():
    out = sa_agent.product_review_text(sample_payload())
    assert out['ok']
    assert out['solution_review']['summary'] == 'Ревью готового решения'
    assert out['project_package']['process_map']
