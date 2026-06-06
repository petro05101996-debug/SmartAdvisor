import re
import integration_architect_pro as app


def main_html():
    return app.form_page().split('Показать технические детали')[0]


def filled_form(case_type):
    return {
        'simple_goal': 'new' if case_type != 'audit' else 'audit',
        'simple_situation': case_type,
        'simple_q_systems': '3',
        'simple_q_immediate': 'нужно принять запрос сейчас, а результат получить позже',
        'simple_q_payload': 'изменение данных',
        'simple_q_risk': 'потерять данные',
        'simple_q_error': 'повторить позже',
        'simple_q_status': 'да',
        **({'task_type': 'audit_existing_solution'} if case_type == 'audit' else {}),
    }


def test_main_constructor_is_no_text_and_has_no_legacy_modes():
    html = main_html().lower()
    assert '<textarea' not in html
    for forbidden in ['быстрый режим', 'глубокий режим', 'экспертный режим', 'расширенный режим', 'ультракороткий путь', 'raw matrices']:
        assert forbidden not in html
    assert 'no_text_constructor' in html


def test_user_answers_are_lists_buttons_selects_not_free_text():
    html = main_html()
    # 10 human situations, 9 chain templates, 6 required select questions.
    assert html.count("data-case=") >= 10
    assert html.count("data-chain=") >= 9
    assert html.count("data-map-hidden=") == 6
    for question in ['Сколько систем участвует?', 'Ответ нужен сразу?', 'Что передаём?', 'Что страшнее всего?', 'Что делать при ошибке?', 'Нужно видеть статус процесса?']:
        assert question in html
    # Case-specific clarifications are generated as selects too.
    assert 'caseSpecificQuestions' in html
    assert '<textarea' not in html.lower()


def test_empty_input_blocks_recommendations_and_full_result():
    res = app.Engine().generate({})
    html = app.result_page(res, 'empty', 'empty.md')
    assert 'Недостаточно данных для архитектурного вывода' in html
    assert 'Полная схема, рекомендации и отчёт заблокированы' in html
    assert '1. Схема' not in html
    assert 'Что нужно выбрать' in html


def test_all_complex_case_types_have_specific_scheme_must_risks_and_handoff():
    expected = {
        'sync_rest': ['Service A', 'Service B', 'REST-контракт', 'Повтор после timeout', 'API-контракт'],
        'async_worker': ['Service 1', 'Service 2 API', 'integration_task DB', 'Worker', 'trackingId', 'Потеря задачи', 'таблица integration_task'],
        'event_kafka': ['Source Service', 'Outbox', 'Consumer', 'transactional outbox', 'Потеря события', 'outbox table'],
        'enrichment_kafka': ['Source Service', 'Enrichment Worker', 'Target Service', 'Adapter/orchestrator', 'Сервис обогащения недоступен', 'варианты source/consumer/worker/adapter'],
        'callback': ['Internal Service', 'Callback API', 'Status DB', 'endpoint', 'Callback повторился', 'endpoint contract'],
        'dwh': ['Source System', 'Staging', 'Reconciliation', 'watermark', 'Неполная выгрузка', 'backfill procedure'],
        'legacy_file': ['Legacy System', 'Validation/Checksum', 'Target System', 'checksum', 'Файл повреждён', 'quarantine'],
        'status_aggregation': ['Client/UI', 'BFF', 'Cache/Read Model', 'freshness marker', 'Один источник тормозит', 'timeout/fallback policy'],
        'audit': ['Risk Review', 'Developer Handoff', 'найденные риски', 'risk register'],
    }
    for case_type, terms in expected.items():
        res = app.Engine().generate(filled_form(case_type))
        html = app.result_page(res, case_type, f'{case_type}.md')
        assert res['case_type'] == case_type
        for block in ['1. Схема', '2. Что обязательно сделать', '3. Главные риски', '4. Что отдать разработке']:
            assert block in html
        for term in terms:
            assert term in html
        assert html.index('1. Схема') < html.index('Открыть полный отчёт')


def test_rest_case_does_not_drag_kafka_outbox_dlq_as_main_requirement():
    res = app.Engine().generate(filled_form('sync_rest'))
    html = app.result_page(res, 'rest', 'rest.md')
    main = html.split('Показать технические детали')[0]
    for forbidden in ['transactional outbox', 'Kafka topic', 'DLQ/manual recovery', 'consumer lag']:
        assert forbidden not in main
    for required in ['REST-контракт', 'timeout', 'error mapping', 'correlationId']:
        assert required in main


def test_report_is_recommendation_like_not_raw_markdown_first():
    res = app.Engine().generate(filled_form('async_worker'))
    html = app.result_page(res, 'async', 'async.md')
    # User first sees practical recommendations, not raw appendix.
    assert 'Сначала показаны 4 рабочих блока' in html
    assert 'Пошаговый процесс' in html
    assert 'Service 3 недоступен' in html or 'Worker переводит задачу' in html
    assert html.index('Что отдать разработке') < html.index('Открыть полный отчёт')
    assert '<details class="full-report card"><summary>Открыть полный отчёт</summary>' in html
