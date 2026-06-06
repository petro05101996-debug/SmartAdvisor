from integration_architect_pro import form_page, Engine, result_page


def test_constructor_has_simple_guidance_presets_edit_and_delete_controls():
    html = form_page()
    assert 'Простой конструктор без текста' in html
    assert 'выберите роли блоков' in html
    assert 'добавьте связи “откуда → куда”' in html
    assert 'результат и отчёт возьмут именно эту цепочку' in html
    for preset in ['Принять запрос сейчас, обработать позже', 'Надёжная публикация и обработка события', 'Сбор статуса из нескольких систем', 'Файл, checksum, карантин']:
        assert preset in html
    assert 'data-del-part' in html
    assert 'data-del-conn' in html
    assert 'data-edit-conn' in html
    assert 'Собранная схема' in html
    assert 'Эта схема будет использована в результате и полном отчёте' in html
    assert 'Блок 1' not in html
    assert 'linkTypeSelect' not in html


def test_engine_result_uses_custom_chain_schema_from_constructor_payload():
    custom_schema = 'UI → BFF/API Composition → Service A → Service B → Cache / Read Model'
    form = {
        'ux_mode': 'no_text_constructor',
        'simple_situation': 'status_aggregation',
        'simple_goal': 'complex',
        'simple_q_systems': 'Больше 3',
        'simple_q_immediate': 'Да',
        'simple_q_payload': 'Статус',
        'simple_q_risk': 'Устаревшие данные',
        'simple_q_error': 'Сохранить и обработать потом',
        'simple_q_status': 'Да',
        'custom_chain_json': '{"schema":"' + custom_schema + '","participants":[],"connections":[]}',
        'process_graph_json': '{"case_type":"status_aggregation","schema":"' + custom_schema + '"}',
        'data_storage_choice': 'cache_read_model',
        'data_storage_role': 'last_known_status',
    }
    res = Engine().generate(form)
    assert res['case_schema'] == custom_schema
    page = result_page(res, 'custom-status', 'custom-status.md')
    for expected in ['UI', 'BFF/API Composition', 'Service A', 'Service B', 'Cache / Read Model', 'freshness marker', 'partial response']:
        assert expected in page


def test_custom_async_chain_report_keeps_exact_user_built_flow():
    schema = 'Service 1 → Service 2 API → integration_task DB → Worker → External Service → Status DB'
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
        'custom_chain_json': '{"schema":"' + schema + '","participants":[],"connections":[]}',
        'process_graph_json': '{"case_type":"async_worker","schema":"' + schema + '"}',
        'data_storage_choice': 'task_table',
        'data_storage_role': 'task_state',
    }
    res = Engine().generate(form)
    assert res['case_schema'] == schema
    page = result_page(res, 'custom-async', 'custom-async.md')
    for expected in ['Service 1', 'Service 2 API', 'integration_task DB', 'Worker', 'External Service', 'Status DB', 'trackingId', 'manual recovery']:
        assert expected in page


def test_no_text_constructor_buttons_are_wired_and_do_not_submit_accidentally():
    html = form_page()
    assert "function startApp" in html
    assert "on('startNoTextBtn','click',()=>startApp(0))" in html
    assert "on('prevBtn','click',()=>go(3))" in html
    assert "on('constructorNext','click',()=>go(step+1))" in html
    assert "on('confirmUnderstanding','click',()=>go(4))" in html
    assert "on('applyHelperPick','click',()=>updateCase(pickHelperCase()))" in html
    assert "function pickHelperCase" in html
    assert "function on(id,event,handler)" in html
    assert "document.getElementById('startNoTextBtn').addEventListener" not in html

    constructor_start = html.index("<form method='POST' action='/generate'")
    constructor_end = html.index("</form>", constructor_start)
    form_html = html[constructor_start:constructor_end]
    for fragment in form_html.split('<button')[1:]:
        head = fragment.split('>', 1)[0]
        assert "type='button'" in head or 'type="button"' in head or "type='submit'" in head or 'type="submit"' in head
