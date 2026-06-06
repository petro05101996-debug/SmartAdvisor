from integration_architect_pro import Engine, result_page


def _base(case_type):
    return {
        'simple_situation': case_type,
        'simple_goal': 'Разобрать сложный кейс',
        'simple_q_systems': 'Больше 3',
        'simple_q_immediate': 'Нет, можно позже',
        'simple_q_payload': 'Изменение данных',
        'simple_q_risk': 'Потерять данные',
        'simple_q_error': 'Сохранить и обработать потом',
        'simple_q_status': 'Да',
    }


def _assert_result_readable(res):
    html = result_page(res, 'rid', 'report.md')
    for text in ['1. Схема', '2. Что обязательно сделать', '3. Главные риски', '4. Что отдать разработке']:
        assert text in html
    md = res['markdown']
    for text in ['Короткий вывод', 'Пошаговый процесс', 'Что отдать разработке', 'Тест-кейсы', 'ADR']:
        assert text in md


def test_hard_event_banking_saga_has_outbox_inbox_and_compensation_note():
    form = _base('event_kafka')
    form['constraint_flags'] = ['money', 'many_consumers', 'compensation', 'manual']
    res = Engine().generate(form)
    assert res['case_type'] == 'event_kafka'
    md = res['markdown']
    for text in ['transactional outbox', 'inbox/idempotency', 'eventId', 'aggregateId', 'consumer lag']:
        assert text in md
    for text in ['Долгий многошаговый процесс', 'компенсация', 'manual recovery', 'compensation_failed']:
        assert text in md
    _assert_result_readable(res)


def test_shared_kafka_topic_has_filtering_specific_guidance():
    form = _base('shared_topic')
    form['simple_q_risk'] = 'Долго ждать'
    res = Engine().generate(form)
    assert res['case_type'] == 'event_kafka'
    md = res['markdown']
    for text in ['Kafka topic один', 'discard rate', 'processing time', 'consumer lag', 'Отдельный topic']:
        assert text in md
    _assert_result_readable(res)


def test_cdc_dwh_backfill_reconciliation_case_is_specific():
    form = _base('dwh')
    res = Engine().generate(form)
    md = res['markdown']
    for text in ['Export/CDC', 'Staging', 'DWH', 'Reconciliation', 'watermark', 'reload/backfill', 'data quality checks']:
        assert text in md
    _assert_result_readable(res)


def test_status_aggregation_bff_partial_response_case_is_specific():
    form = _base('status_aggregation')
    form['simple_q_immediate'] = 'Да'
    form['simple_q_payload'] = 'Статус'
    res = Engine().generate(form)
    md = res['markdown']
    for text in ['BFF/API Composition', 'partial response', 'Cache/Read Model', 'freshness marker', 'latency/error']:
        assert text in md
    _assert_result_readable(res)
