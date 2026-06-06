import integration_architect_pro as app


def _main_visible_html():
    html = app.form_page()
    return html.split('Показать технические детали')[0]


def test_no_text_constructor_main_flow_has_no_textarea_or_modes():
    main = _main_visible_html().lower()
    assert '<textarea' not in main
    for forbidden in ['быстрый режим', 'глубокий режим', 'экспертный режим', 'расширенный режим', 'ультракороткий путь', 'raw matrices']:
        assert forbidden not in main


def test_start_screen_has_only_human_situations_no_technical_dump():
    html = app.form_page()
    start = html[html.index("id='startScreen'"):html.index('</section>', html.index("id='startScreen'"))]
    for required in ['Спроектировать новую интеграцию', 'Проверить готовое решение', 'Разобрать сложный кейс']:
        assert required in start
    for forbidden in ['REST', 'Kafka', 'Outbox', 'Inbox', 'DLQ', 'ADR', 'raw matrices']:
        assert forbidden not in start


def test_constructor_has_five_simple_screens_and_six_questions():
    html = app.form_page()
    for required in ['Что нужно спроектировать?', 'Соберите цепочку систем', 'Настройте поведение процесса', 'Я понял задачу так', 'Результат']:
        assert required in html
    main = _main_visible_html()
    assert main.count('data-map-hidden=') == 6
    for q in ['Сколько систем участвует?', 'Ответ нужен сразу?', 'Что передаём?', 'Что страшнее всего?', 'Что делать при ошибке?', 'Нужно видеть статус процесса?']:
        assert q in main


def test_all_case_types_generate_contextual_reports():
    expected = {
        'sync_rest': ['Service A → REST API → Service B', 'REST-контракт', 'timeout'],
        'async_worker': ['Service 1 → Service 2 API → integration_task DB → Worker → Service 3', 'trackingId', 'GET /status'],
        'event_kafka': ['Outbox', 'eventId', 'consumer lag'],
        'enrichment_kafka': ['Enrichment Worker', 'Варианты обогащения', 'Adapter/orchestrator'],
        'callback': ['Callback API', 'idempotency callback', 'polling fallback'],
        'dwh': ['Staging', 'Reconciliation', 'watermark'],
        'legacy_file': ['Validation/Checksum', 'quarantine', 'reprocessing'],
        'status_aggregation': ['BFF/API Composition', 'Cache/Read Model', 'freshness marker'],
        'audit': ['Risk Review', 'risk register', 'варианты исправления'],
    }
    base = {
        'simple_goal': 'new',
        'simple_q_systems': '3',
        'simple_q_immediate': 'нужно принять запрос сейчас, а результат получить позже',
        'simple_q_payload': 'изменение данных',
        'simple_q_risk': 'потерять данные',
        'simple_q_error': 'повторить позже',
        'simple_q_status': 'да',
    }
    for case_type, terms in expected.items():
        form = dict(base, simple_situation=case_type)
        if case_type == 'audit':
            form['task_type'] = 'audit_existing_solution'
        res = app.Engine().generate(form)
        text = ' '.join([res.get('case_schema', ''), ' '.join(res.get('case_checklist', [])), res.get('markdown', '')])
        assert res.get('case_type') == case_type
        for term in terms:
            assert term in text


def test_result_page_starts_with_four_human_blocks_not_raw_markdown():
    form = {
        'simple_goal': 'new', 'simple_situation': 'async_worker', 'simple_q_systems': '3',
        'simple_q_immediate': 'нужно принять запрос сейчас, а результат получить позже',
        'simple_q_payload': 'команду/заявку', 'simple_q_risk': 'получить дубль',
        'simple_q_error': 'отправить в ручной разбор', 'simple_q_status': 'да',
    }
    res = app.Engine().generate(form)
    html = app.result_page(res, 'rid123', 'report.md')
    for block in ['1. Схема', '2. Что обязательно сделать', '3. Главные риски', '4. Что отдать разработке']:
        assert block in html
    assert 'Открыть полный отчёт' in html
    assert html.index('1. Схема') < html.index('Открыть полный отчёт')
