from integration_architect_pro import form_page, Engine, result_page


def test_real_custom_constructor_controls_exist():
    html = form_page()
    assert '+ Добавить участника' in html
    assert '+ Добавить связь' in html
    assert 'Собрать свою цепочку' in html
    assert 'Откуда' in html and 'Куда' in html and 'Тип связи' in html
    for role in ['Инициатор процесса','Принимающий сервис','Обработчик / Worker','База данных','Брокер / очередь','BFF / агрегатор','Cache / Read Model']:
        assert role in html


def test_custom_chain_hidden_payload_fields_exist():
    html = form_page()
    assert "name='custom_chain_json'" in html
    assert 'customSystemsMatrix' in html
    assert 'customTargetMatrix' in html
    assert 'customProcessSteps' in html
    assert 'Собранная пользователем цепочка' in html


def test_manual_async_chain_report_uses_custom_chain():
    form = {
        'ux_mode': 'no_text_constructor',
        'simple_situation': 'async_worker',
        'simple_goal': 'complex',
        'simple_q_systems': 'Больше 3',
        'simple_q_immediate': 'Принять сейчас, результат позже',
        'simple_q_payload': 'Заявку / команду',
        'simple_q_risk': 'Потерять данные',
        'simple_q_error': 'Отправить в ручной разбор',
        'simple_q_status': 'Да',
        'business_goal': 'Пользователь собрал цепочку: Service 1 → Service 2 API → DB → Worker → Service 3',
        'systems_matrix': '\n'.join([
            'Service 1 | Инициатор процесса | TBD | important | selected | blocking | уточнить',
            'Service 2 API | Принимающий сервис | TBD | critical | selected | blocking | уточнить',
            'DB | База данных | TBD | critical | selected | non_blocking | уточнить',
            'Worker | Обработчик / Worker | TBD | critical | selected | non_blocking | уточнить',
            'Service 3 | Получатель данных | TBD | important | selected | non_blocking | уточнить',
        ]),
        'target_integration_matrix': '\n'.join([
            'Service 1 | Service 2 API | selected | selected | Запрос и быстрый ответ | payload | Contract.v1 | уточнить | yes | 3 | manual | idempotencyKey+correlationId | service auth | уточнить | TBD',
            'Service 2 API | DB | selected | selected | Принять сейчас, обработать позже | payload | Contract.v1 | уточнить | yes | 3 | manual | idempotencyKey+correlationId | service auth | уточнить | TBD',
            'DB | Worker | selected | selected | Принять сейчас, обработать позже | payload | Contract.v1 | уточнить | yes | 3 | manual | idempotencyKey+correlationId | service auth | уточнить | TBD',
            'Worker | Service 3 | selected | selected | Запрос и быстрый ответ | payload | Contract.v1 | уточнить | yes | 3 | manual | idempotencyKey+correlationId | service auth | уточнить | TBD',
        ]),
        'process_steps': '1 | 1 | root | Service 1 → Service 2 API | Service 1 | Запрос и быстрый ответ | input | output | уточнить | yes | manual | blocking | TBD',
        'data_storage_choice': 'task_table',
        'data_storage_role': 'Хранит задачу на обработку',
    }
    res = Engine().generate(form)
    assert res['case_type'] == 'async_worker'
    page = result_page(res, 'manual-async', 'manual-async.md')
    for expected in ['Схема взаимодействия','Service 1','Service 2 API','DB','Worker','Service 3','trackingId','integration_task DB','manual recovery','Что отдать разработке']:
        assert expected in page


def test_manual_kafka_chain_report_uses_outbox_inbox_nodes():
    form = {
        'ux_mode': 'no_text_constructor',
        'simple_situation': 'event_kafka',
        'simple_goal': 'complex',
        'simple_q_systems': 'Больше 3',
        'simple_q_immediate': 'Нет, можно позже',
        'simple_q_payload': 'Изменение данных',
        'simple_q_risk': 'Потерять данные',
        'simple_q_error': 'Сохранить и обработать потом',
        'simple_q_status': 'Желательно',
        'business_goal': 'Пользователь собрал цепочку: Source Service → Business DB → Outbox → Kafka → Consumer → Inbox → Target DB',
        'systems_matrix': '\n'.join([
            'Source Service | Источник данных | TBD | critical | selected | blocking | уточнить',
            'Outbox | База данных | TBD | critical | selected | non_blocking | уточнить',
            'Kafka | Брокер / очередь | TBD | critical | selected | non_blocking | уточнить',
            'Consumer | Получатель события | TBD | critical | selected | non_blocking | уточнить',
            'Inbox | База данных | TBD | critical | selected | non_blocking | уточнить',
            'Target DB | Получатель данных | TBD | important | selected | non_blocking | уточнить',
        ]),
        'target_integration_matrix': 'Source Service | Outbox | selected | selected | Передать событие | payload | Event.v1 | уточнить | yes | 3 | manual | eventId+correlationId | service auth | уточнить | TBD',
        'data_storage_choice': 'outbox',
        'data_storage_role': 'Хранит события перед публикацией',
    }
    res = Engine().generate(form)
    assert res['case_type'] == 'event_kafka'
    page = result_page(res, 'manual-kafka', 'manual-kafka.md')
    for expected in ['Outbox','Kafka','Consumer','Inbox','transactional outbox','eventId','inbox/idempotency','DLQ/manual recovery']:
        assert expected in page
