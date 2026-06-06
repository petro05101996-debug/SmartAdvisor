import integration_architect_pro as app


def main_html():
    return app.form_page()


def test_situation_cards_explain_complex_coverage_in_plain_language():
    html = main_html()
    assert 'Покрывает:' in html
    for term in [
        'таблицу задач', 'надёжную публикацию события', 'несколько получателей',
        'защиту от дублей', 'очередь ошибок', 'повторную обработку',
        'отдельном обработчике', 'адаптере/оркестраторе',
        'агрегатор для экрана', 'кеш/модель чтения',
        'контрольную сумму', 'карантин ошибок', 'переобработку'
    ]:
        assert term in html


def test_chain_cards_have_visible_text_classes_and_no_black_empty_buttons():
    html = main_html()
    assert 'chain-template-card' in html
    assert '.chain-template-card' in html
    assert 'color:#e5e7eb' in html or 'color: #e5e7eb' in html
    for text in ['Service A → Service B', 'Source → Enrichment → Target', 'Internal → External → Callback']:
        assert text in html


def test_database_storage_options_visible_in_constructor():
    html = main_html()
    assert 'Где храним состояние / данные?' in html
    for text in [
        'В таблице задач', 'В таблице исходящих событий', 'В таблице обработанных событий',
        'В кеше / модели чтения', 'В отчётном хранилище / staging', 'В файловом реестре',
        'Какая роль базы?', 'Хранит задачу на обработку', 'Защищает от дублей',
        'Используется для сверки/reconciliation'
    ]:
        assert text in html


def test_result_uses_visual_interaction_diagram_not_plain_arrow_only():
    res = app.Engine().generate({
        'simple_situation': 'async_worker',
        'simple_q_systems': '3',
        'simple_q_immediate': 'нужно принять запрос сейчас, а результат получить позже',
        'simple_q_payload': 'команду/заявку',
        'simple_q_risk': 'потерять данные',
        'simple_q_error': 'повторить позже',
        'simple_q_status': 'да',
    })
    html = app.result_page(res, 'rid', 'report.md')
    assert '1. Схема взаимодействия' in html
    assert 'interaction-diagram' in html
    assert 'diagram-node' in html
    assert 'diagram-edge' in html
    assert 'Service 2 API' in html
    assert 'integration_task DB' in html
    assert 'Worker' in html


def test_storage_choice_affects_result_recommendations():
    cases = [
        ('async_worker', 'task_table', 'task_state', ['integration_task DB', 'stuck tasks', 'роль базы: хранит задачу на обработку']),
        ('event_kafka', 'outbox', 'event_before_publish', ['transactional outbox', 'publisher retry', 'роль базы: хранит события перед публикацией']),
        ('event_kafka', 'inbox', 'duplicate_protection', ['inbox/idempotency', 'duplicate protection', 'роль базы: защищает от дублей']),
        ('status_aggregation', 'cache_read_model', 'last_known_status', ['Cache / Read Model', 'freshness marker', 'роль базы: хранит последний известный статус']),
        ('dwh', 'dwh_staging', 'reconciliation', ['watermark', 'reconciliation', 'data quality checks', 'роль базы: используется для сверки/reconciliation']),
        ('legacy_file', 'file_registry', 'reconciliation', ['file_id', 'checksum', 'batch_id', 'quarantine', 'reprocessing']),
    ]
    for case_type, storage, role, expected_terms in cases:
        res = app.Engine().generate({
            'simple_situation': case_type,
            'simple_q_systems': '3',
            'simple_q_immediate': 'нет, можно позже',
            'simple_q_payload': 'изменение данных',
            'simple_q_risk': 'потерять данные',
            'simple_q_error': 'повторить позже',
            'simple_q_status': 'да',
            'data_storage_choice': storage,
            'data_storage_role': role,
        })
        html = app.result_page(res, 'rid', 'report.md')
        for term in expected_terms:
            assert term in html
