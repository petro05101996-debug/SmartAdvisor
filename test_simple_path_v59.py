from integration_architect_pro import Engine, form_page, required_items_for_case


def _start_fragment():
    html = form_page()
    return html.split("id='startScreen'", 1)[1].split('</section>', 1)[0]


def test_home_has_only_three_goals():
    start = _start_fragment()
    for text in ['Спроектировать новую интеграцию', 'Проверить существующее решение', 'Разобрать сложный кейс']:
        assert text in start
    for text in ['Глубокий / расширенный режим', 'Быстрый режим', 'Ультракороткий путь', 'Экспертный режим']:
        assert text not in start
    assert start.count("class='mode-choice") == 3


def test_start_screen_has_no_technical_dump():
    start = _start_fragment()
    for text in ['REST', 'Kafka', 'Outbox', 'Inbox', 'DLQ', 'raw matrices', 'ADR']:
        assert text not in start


def test_simple_wizard_has_six_steps():
    html = form_page()
    for text in ['Что делаем?', 'Какая ситуация?', 'Простые вопросы', 'Я понял задачу так', 'Схема', 'Отчёт']:
        assert text in html
    for i in range(6):
        assert f"data-simple-panel='{i}'" in html


def test_full_report_blocked_under_40():
    res = Engine().generate({})
    assert res['readiness']['score'] <= 40
    assert 'Недостаточно данных для архитектурного вывода' in res['markdown']
    assert 'Выбрана схема:' not in res['markdown']


def test_empty_input_shows_missing_questions():
    res = Engine().generate({})
    assert 'Недостаточно данных для архитектурного вывода' in res['markdown']
    assert 'Выбрана схема:' not in res['markdown']


def test_rest_case_has_no_forced_kafka_items():
    res = Engine().generate({'business_goal': 'Один сервис вызывает другой и ждёт ответ сразу.'})
    assert res['case_type'] == 'sync_rest'
    checklist = '\n'.join(res['case_checklist'])
    for item in ['eventId', 'DLQ', 'Outbox', 'Inbox', 'reconciliation']:
        assert item not in checklist
    for item in ['REST-контракт', 'timeout', 'error mapping', 'correlationId', 'contract tests']:
        assert item in checklist




def _complete_case_form(case_type, goal, payload='команду/заявку', immediate='нет, можно позже'):
    return {
        'business_goal': goal,
        'simple_situation': case_type,
        'simple_q_systems': '3' if case_type != 'sync_rest' else '2',
        'simple_q_immediate': immediate,
        'simple_q_payload': payload,
        'simple_q_risk': 'потерять данные',
        'simple_q_error': 'повторить позже',
        'simple_q_status': 'да',
    }

def test_async_worker_case_has_required_items():
    text = 'Service 1 отправляет запрос в Service 2. Service 2 сохраняет задачу. Worker читает БД и вызывает Service 3 позже.'
    md = Engine().generate(_complete_case_form('async_worker', text))['markdown']
    for item in ['integration_task DB', 'Worker', 'trackingId', 'idempotencyKey', 'correlationId', 'NEW', 'IN_PROGRESS', 'RETRY', 'SUCCESS', 'FAILED', 'manual recovery']:
        assert item in md


def test_kafka_case_has_outbox_inbox():
    text = 'В сервисе изменился договор. Нужно отправить событие в Kafka. Потеря недопустима, дубли возможны.'
    md = Engine().generate(_complete_case_form('event_kafka', text, payload='изменение данных'))['markdown']
    for item in ['transactional outbox', 'eventId', 'aggregateId', 'occurredAt', 'version', 'inbox', 'DLQ/manual recovery', 'consumer lag']:
        assert item in md


def test_enrichment_case_has_options():
    text = 'Перед отправкой события в Kafka нужно обогатить данные через REST из другого сервиса. Kafka есть только в одном сервисе. Source менять дорого.'
    md = Engine().generate(_complete_case_form('enrichment_kafka', text, payload='изменение данных'))['markdown']
    assert Engine().generate(_complete_case_form('enrichment_kafka', text, payload='изменение данных'))['case_type'] == 'enrichment_kafka'
    for item in ['Обогащать в source', 'Публиковать минимальное событие', 'Enrichment-worker', 'Adapter/orchestrator', 'Связность', 'Стоимость внедрения', 'Свежесть данных', 'Отказоустойчивость']:
        assert item in md


def test_default_project_name_not_fake_crm_dwh():
    md = Engine().generate(_complete_rest_form())['markdown']
    for item in ['скоринг', 'CRM', 'DWH']:
        assert item not in md


def test_report_starts_with_human_sections():
    md = Engine().generate(_complete_rest_form())['markdown']
    assert md.index('## 1. Короткий вывод') < md.index('## 2. Рекомендуемая схема') < md.index('## 3. Почему выбрана эта схема') < md.index('## 4. Пошаговый процесс')
    assert 'raw matrices' not in md[:300]


def test_expert_details_hidden_by_default():
    md = Engine().generate(_complete_rest_form())['markdown']
    assert '<details class="expert-details">' in md
    assert '<details class="expert-details" open>' not in md


def test_report_has_developer_handoff():
    assert 'Что отдать разработке' in Engine().generate(_complete_rest_form())['markdown']


def test_report_has_test_cases():
    assert 'Тест-кейсы' in Engine().generate(_complete_rest_form())['markdown']


def test_report_has_adr_draft():
    assert 'ADR-черновик' in Engine().generate(_complete_rest_form())['markdown']


def _complete_rest_form():
    return {
        'business_goal': 'Связать Service A и Service B',
        'simple_situation': 'sync_rest',
        'simple_q_systems': '2',
        'simple_q_immediate': 'да, нужен сразу',
        'simple_q_payload': 'команду/заявку',
        'simple_q_risk': 'долго ждать ответ',
        'simple_q_error': 'показать ошибку сразу',
        'simple_q_status': 'нет',
    }


def test_no_quick_mode_as_separate_main_path():
    html = form_page()
    assert 'quick-mode-panel' not in html
    assert 'Очень быстрый режим' not in html
    assert 'Быстро разобрать задачу' not in html


def test_old_progress_rail_removed():
    html = form_page()
    rail = html.split("id='progressRail'", 1)[1].split('</div>', 1)[0]
    for text in ['1. Задача', '2. Участники', '3. Процесс', '4. Ограничения', '5. Риски', '6. Проверка', '7. Результат']:
        assert text not in rail
    for text in ['1. Что делаем?', '2. Какая ситуация?', '3. Простые вопросы', '4. Я понял задачу так', '5. Схема', '6. Отчёт']:
        assert text in rail


def test_step2_contains_only_situations():
    html = form_page()
    step2 = html.split("data-simple-panel='1'", 1)[1].split("data-simple-panel='2'", 1)[0]
    for situation in ['Один сервис вызывает другой и ждёт ответ', 'Нужно принять запрос сейчас, а обработать позже', 'Нужно отправить событие об изменении данных', 'Не знаю, помогите выбрать']:
        assert situation in step2
    for question in ['Кто запускает процесс?', 'Что должно произойти?', 'Кто видит результат?', 'Что делать при ошибке?', 'Есть финансовый риск?', 'Есть персональные данные?', 'Есть регуляторные требования?', 'Нужен ответ сразу?', 'Требование к свежести']:
        assert question not in step2


def test_business_goal_default_is_empty():
    from integration_architect_pro import defaults
    assert defaults()['business_goal'] == ''


def test_readiness_requires_required_answers_not_text_length():
    long_text = ' '.join(['Один сервис вызывает другой и ждёт ответ сразу'] * 80)
    res = Engine().generate({'business_goal': long_text})
    assert res['readiness']['score'] <= 40
    assert 'Недостаточно данных для архитектурного вывода' in res['markdown']
    full = Engine().generate(_complete_rest_form())
    assert full['readiness']['score'] >= 70
    assert '## 1. Короткий вывод' in full['markdown']


def test_rest_technical_details_do_not_show_outbox_inbox_dlq():
    md = Engine().generate(_complete_rest_form())['markdown']
    tech = md.split('## 11. Технические детали', 1)[1].split('</details>', 1)[0]
    for item in ['Outbox', 'Inbox', 'DLQ']:
        assert item not in tech
    for item in ['REST-контракт', 'timeout', 'error mapping']:
        assert item in tech


def test_old_questions_hidden_in_expert_details_by_default():
    html = form_page()
    assert "<details class='expert-details legacy-questions-details'>" in html
    assert "<details class='expert-details legacy-questions-details' open>" not in html
    assert "<summary>Показать технические детали</summary>" in html


def test_legacy_file_has_own_case_type_schema_and_checklist():
    form = _complete_case_form('legacy_file', 'Legacy-система отдаёт файл, новая система валидирует и загружает', payload='файл')
    res = Engine().generate(form)
    assert res['case_type'] == 'legacy_file'
    assert res['case_schema'] == 'Legacy System → File Export → Validation/Checksum → Quarantine → Target System'
    checklist = '\n'.join(res['case_checklist'])
    for item in ['file_id', 'checksum', 'batch_id', 'file registry', 'validation', 'quarantine', 'reprocessing', 'manual recovery']:
        assert item in checklist
    assert 'Выгрузка данных в DWH/отчётность' not in res['markdown'].split('## 1. Короткий вывод', 1)[1][:500]


def test_status_aggregation_has_own_case_type_schema_and_checklist():
    form = _complete_case_form('status_aggregation', 'Нужно собрать статус из нескольких систем', payload='статус', immediate='да, нужен сразу')
    res = Engine().generate(form)
    assert res['case_type'] == 'status_aggregation'
    assert res['case_schema'] == 'Client/UI → BFF/API Composition → Service A / Service B / Service C → Cache/Read Model'
    checklist = '\n'.join(res['case_checklist'])
    for item in ['BFF/API Composition contract', 'частичный ответ', 'Cache/Read Model', 'freshness marker', 'fallback для недоступной системы']:
        assert item in checklist
    assert 'Service A → REST API → Service B' not in res['markdown'].split('## 2. Рекомендуемая схема', 1)[1][:500]


def test_readiness_line_not_duplicated():
    md = Engine().generate(_complete_rest_form())['markdown']
    assert md.count('Готовность требований') == 1


def test_mode_choice_checked_css_selector_has_dot():
    html = form_page()
    assert '.mode-choice.selected,.mode-choice:has(input:checked)' in html
    assert '.mode-choice.selected,mode-choice:has(input:checked)' not in html
