import json

import integration_architect_pro as app


def html():
    return app.form_page()


def test_business_first_main_screen_has_no_technical_terms():
    h = html()
    start = h[h.index("id='startScreen'"):h.index('</section>', h.index("id='startScreen'"))]
    assert 'Конструктор бизнес-процесса' in start
    assert 'Спроектировать процесс' in start
    assert 'Проверить текущее решение' in start
    assert 'Разобрать сложный процесс' in start
    for forbidden in ['Kafka', 'Outbox', 'Inbox', 'DB', 'Worker', 'REST', 'BFF', 'Cache', 'DLQ']:
        assert forbidden not in start


def test_business_process_constructor_exists_and_technical_constructor_hidden():
    h = html()
    for required in [
        'Соберите бизнес-процесс', '+ Добавить участника', '+ Добавить шаг процесса',
        'Роль нового участника', 'Действие шага', 'Бизнес-объект', 'Когда нужен результат',
        'Результат процесса', 'Показать технический конструктор'
    ]:
        assert required in h
    # Technical controls still exist, but behind details.
    assert '+ Добавить связь' in h
    assert "id='customChainJson'" in h or 'id="customChainJson"' in h


def test_business_hidden_fields_are_present_and_parsed():
    h = html()
    for field in [
        'business_case', 'business_process_json', 'business_actors_json', 'business_steps_json',
        'business_object', 'business_result_timing', 'business_result_type', 'business_constraints_json',
        'business_criticality', 'auto_generated_technical_chain_json'
    ]:
        assert f"name='{field}'" in h
    body = '&'.join([
        'business_case=application_creation',
        'business_object=%D0%97%D0%B0%D1%8F%D0%B2%D0%BA%D0%B0',
        'business_result_timing=%D0%9D%D1%83%D0%B6%D0%BD%D0%BE+%D0%BF%D1%80%D0%B8%D0%BD%D1%8F%D1%82%D1%8C+%D1%81%D0%B5%D0%B9%D1%87%D0%B0%D1%81',
        'business_constraints_json=%5B%22compensation%22%5D',
        'business_goal=%D0%91%D0%B8%D0%B7%D0%BD%D0%B5%D1%81-%D0%BF%D1%80%D0%BE%D1%86%D0%B5%D1%81%D1%81%3A+test',
        'simple_situation=async_worker',
        'simple_q_systems=3',
        'simple_q_immediate=%D0%9F%D1%80%D0%B8%D0%BD%D1%8F%D1%82%D1%8C+%D1%81%D0%B5%D0%B9%D1%87%D0%B0%D1%81%2C+%D1%80%D0%B5%D0%B7%D1%83%D0%BB%D1%8C%D1%82%D0%B0%D1%82+%D0%BF%D0%BE%D0%B7%D0%B6%D0%B5',
        'simple_q_payload=%D0%97%D0%B0%D1%8F%D0%B2%D0%BA%D1%83',
        'simple_q_risk=%D0%9F%D0%BE%D1%82%D0%B5%D1%80%D1%8F%D1%82%D1%8C+%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D0%B5',
        'simple_q_error=%D0%A1%D0%BE%D1%85%D1%80%D0%B0%D0%BD%D0%B8%D1%82%D1%8C+%D0%B8+%D0%BE%D0%B1%D1%80%D0%B0%D0%B1%D0%BE%D1%82%D0%B0%D1%82%D1%8C+%D0%BF%D0%BE%D1%82%D0%BE%D0%BC',
        'simple_q_status=%D0%94%D0%B0'
    ]).encode()
    parsed = app.parse_post(body.decode())
    assert parsed['business_case'] == 'application_creation'
    assert 'Бизнес-процесс' in parsed['business_goal']


def _form(case_type, schema, business_goal='Бизнес-процесс: пользователь создаёт заявку → система обрабатывает позже.'):
    return {
        'simple_goal': 'new',
        'simple_situation': case_type,
        'business_goal': business_goal,
        'simple_q_systems': '3',
        'simple_q_immediate': 'Принять сейчас, результат позже',
        'simple_q_payload': 'Заявку / команду',
        'simple_q_risk': 'Потерять данные',
        'simple_q_error': 'Сохранить и обработать потом',
        'simple_q_status': 'Да',
        'process_graph_json': json.dumps({'case_type': case_type, 'schema': schema}, ensure_ascii=False),
        'custom_chain_json': json.dumps({'schema': schema}, ensure_ascii=False),
    }


def test_business_first_report_starts_with_business_then_scheme_then_reason():
    res = app.Engine().generate(_form('async_worker', 'Client/UI → Service API → integration_task DB → Worker → Target Service → Status DB'))
    md = res['markdown']
    assert '## 1. Бизнес-процесс' in md
    assert '## 2. Схема взаимодействия' in md
    assert '## 3. Почему выбрана такая техническая схема' in md
    assert 'integration_task DB' in md
    result = app.result_page(res, 'rid', 'report.md')
    assert '1. Бизнес-процесс' in result
    assert '2. Схема взаимодействия' in result
    assert '3. Почему выбрана такая техническая схема' in result
    assert 'Что обязательно сделать' in result
    assert 'Главные риски' in result
    assert 'Что отдать разработке' in result


def test_business_event_flow_recommendations_are_specific():
    res = app.Engine().generate(_form('event_kafka', 'Source Service → Business DB → Outbox → Publisher → Event Stream → Consumer → Inbox → Target Service', 'Бизнес-процесс: данные изменились → другие системы должны узнать об изменении.'))
    text = res['markdown'] + app.result_page(res, 'rid', 'report.md')
    for term in ['Outbox', 'Event Stream', 'Inbox', 'eventId', 'aggregateId', 'consumer lag']:
        assert term in text


def test_business_constraints_affect_recommendations():
    form = _form('event_kafka', 'Source Service → Business DB → Outbox → Publisher → Event Stream → Consumer → Inbox → Target Service')
    form['constraint_flags'] = ['no_new_topic', 'compensation', 'money', 'highload']
    form['business_constraints_json'] = json.dumps(form['constraint_flags'])
    res = app.Engine().generate(form)
    text = res['markdown']
    for term in ['discard rate', 'consumer lag', 'compensation_failed', 'manual recovery']:
        assert term in text


def test_technical_constructor_terms_are_not_on_start_screen_but_available_later():
    h = html()
    start = h[h.index("id='startScreen'"):h.index('</section>', h.index("id='startScreen'"))]
    assert 'Worker' not in start and 'Outbox' not in start and 'Kafka' not in start
    assert 'Показать технический конструктор' in h
    assert 'Service API' in h or '+ Добавить связь' in h
