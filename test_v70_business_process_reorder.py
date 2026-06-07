import json
from urllib.parse import urlencode

import integration_architect_pro as app


def html():
    return app.form_page()


def test_business_steps_have_reorder_buttons():
    h = html()
    assert 'data-step-up' in h
    assert 'data-step-down' in h
    assert 'data-step-delete' in h
    assert 'data-step-edit' in h
    assert 'function moveBusinessStep(index,direction)' in h
    assert 'type="button" class="mini-action" data-step-up' in h


def test_business_step_order_saved_to_json():
    h = html()
    assert "order:i+1" in h or 'order = i + 1' in h
    assert 'setHidden(\'businessStepsJson\',JSON.stringify(businessSteps))' in h
    assert 'const tmp=businessSteps[index]' in h
    assert 'businessSteps[index]=businessSteps[next]' in h
    steps = [
        {'id': 'a', 'order': 2, 'actorLabel': 'Внутренняя система', 'action': 'Проверяет данные', 'object': 'Заявка'},
        {'id': 'b', 'order': 1, 'actorLabel': 'Клиент', 'action': 'Создаёт заявку / запрос', 'object': 'Заявка'},
    ]
    form = {'business_steps_json': json.dumps(steps, ensure_ascii=False)}
    ordered = app.ordered_business_steps_from_form(form)
    assert [s['actorLabel'] for s in ordered] == ['Клиент', 'Внутренняя система']
    assert [s['order'] for s in ordered] == [1, 2]


def test_business_presets_exist():
    h = html()
    for text in [
        'Заявка с отложенной обработкой',
        'Изменение данных для нескольких систем',
        'Обогащение перед отправкой',
        'Сбор статуса на экран',
        'Отчётность',
        'Legacy file',
    ]:
        assert text in h
    assert 'data-business-preset' in h
    assert 'applyBusinessPreset' in h


def test_report_contains_ordered_business_steps():
    steps = [
        {'id': '1', 'order': 1, 'actorLabel': 'Клиент', 'action': 'Создаёт заявку / запрос', 'object': 'Заявка'},
        {'id': '2', 'order': 2, 'actorLabel': 'Внутренняя система', 'action': 'Проверяет данные', 'object': 'Заявка'},
        {'id': '3', 'order': 3, 'actorLabel': 'Внешняя система', 'action': 'Получает ответ позже', 'object': 'Заявка'},
    ]
    form = {
        'simple_goal': 'new',
        'simple_situation': 'async_worker',
        'simple_q_systems': '3',
        'simple_q_immediate': 'Принять сейчас, результат позже',
        'simple_q_payload': 'Заявку / команду',
        'simple_q_risk': 'Потерять данные',
        'simple_q_error': 'Сохранить и обработать потом',
        'simple_q_status': 'Да',
        'business_steps_json': json.dumps(steps, ensure_ascii=False),
        'business_process_json': json.dumps({'case': 'application_creation', 'steps': steps}, ensure_ascii=False),
        'process_graph_json': json.dumps({'case_type': 'async_worker', 'schema': 'Client/UI → Service API → Validation / Check Step → External Service / Worker'}, ensure_ascii=False),
    }
    res = app.Engine().generate(form)
    text = res['markdown'] + app.result_page(res, 'rid', 'report.md')
    assert '1. Клиент создаёт заявку / запрос — Заявка.' in text
    assert '2. Внутренняя система проверяет данные — Заявка.' in text
    assert text.index('1. Клиент') < text.index('2. Внутренняя система') < text.index('3. Внешняя система')
    assert 'Порядок бизнес-шагов учтён' in text


def test_risky_order_warnings_are_reported():
    steps = [
        {'order': 1, 'actorLabel': 'Внутренняя система', 'action': 'Передаёт данные дальше', 'object': 'Заявка'},
        {'order': 2, 'actorLabel': 'Внутренняя система', 'action': 'Проверяет данные', 'object': 'Заявка'},
    ]
    warnings = app.business_order_warnings_from_form({'business_steps_json': json.dumps(steps, ensure_ascii=False)})
    assert 'Данные передаются до проверки. Проверьте, допустимо ли это.' in warnings


def test_reorder_does_not_break_technical_constructor():
    h = html()
    assert '+ Добавить участника' in h
    assert '+ Добавить связь' in h
    assert 'custom_chain_json' in h
    assert 'process_graph_json' in h
    assert 'systems_matrix' in h
    assert 'process_steps' in h
    assert 'target_integration_matrix' in h
    assert 'error_matrix' in h
    assert 'Показать технический конструктор' in h


def test_parse_post_keeps_business_first_fields():
    steps = [
        {'id': '1', 'order': 1, 'actorLabel': 'Клиент', 'action': 'Создаёт заявку / запрос', 'object': 'Заявка'},
        {'id': '2', 'order': 2, 'actorLabel': 'Внутренняя система', 'action': 'Проверяет данные', 'object': 'Заявка'},
    ]
    process = {'case': 'application_creation', 'steps': steps, 'schema': 'Клиент создаёт заявку / запрос → Внутренняя система проверяет данные'}
    auto_chain = {'case_type': 'async_worker', 'schema': 'Client/UI → Service API → Validation / Check Step', 'steps': steps}
    body = urlencode({
        'business_case': 'application_creation',
        'business_process_json': json.dumps(process, ensure_ascii=False),
        'business_steps_json': json.dumps(steps, ensure_ascii=False),
        'business_actors_json': json.dumps([{'id': 'BA1', 'name': 'Клиент'}], ensure_ascii=False),
        'business_object': 'Заявка',
        'business_result_timing': 'Нужно принять сейчас, результат получить позже',
        'business_result_type': 'Создана заявка',
        'business_constraints_json': json.dumps(['compensation'], ensure_ascii=False),
        'business_criticality': 'Потерять данные',
        'auto_generated_technical_chain_json': json.dumps(auto_chain, ensure_ascii=False),
    })
    parsed = app.parse_post(body)
    assert parsed['business_case'] == 'application_creation'
    assert json.loads(parsed['business_steps_json'])[1]['actorLabel'] == 'Внутренняя система'
    assert json.loads(parsed['business_process_json'])['steps'][0]['order'] == 1
    assert json.loads(parsed['auto_generated_technical_chain_json'])['case_type'] == 'async_worker'
    assert parsed['business_object'] == 'Заявка'
    assert parsed['business_result_timing'] == 'Нужно принять сейчас, результат получить позже'
    assert parsed['business_result_type'] == 'Создана заявка'
    assert parsed['business_constraints_json']
    assert parsed['business_criticality'] == 'Потерять данные'


def test_open_technical_constructor_does_not_change_step():
    h = html()
    handler_start = h.index("on('openTechnicalConstructor'")
    handler_end = h.index("on('approveAutoScheme'", handler_start)
    handler = h[handler_start:handler_end]
    assert "scrollIntoView" in handler
    assert "go(1)" not in handler
