from urllib.parse import urlencode

from integration_architect_pro import Engine, form_page, parse_post, result_page


def test_english_terms_have_short_russian_explanations_in_ui_and_report():
    html = form_page()
    assert 'worker</b> (фоновый обработчик)' in html
    assert 'callback / webhook</b> (обратный вызов от внешней системы)' in html
    assert 'retry</b> (повторная попытка)' in html

    form = parse_post(urlencode({
        'ux_mode': 'advanced',
        'quick_description': 'Сервис 1 вызывает сервис 2, далее worker отправляет callback, retry, Kafka и DWH.',
        'quick_goal': 'design_new',
        'quick_speed': 'async_status',
        'quick_broker': 'unknown',
        'quick_external': 'yes',
        'constraint_chain_depth': 'multi_level',
    }, doseq=True))
    res = Engine().generate(form)
    md = res['markdown']
    assert 'worker (фоновый обработчик)' in md
    assert 'callback (обратный вызов от внешней системы)' in md
    assert 'retry (повторная попытка)' in md
    assert 'Kafka (брокер событий/поток сообщений)' in md
    assert 'DWH (хранилище данных для аналитики)' in md

    page = result_page(res, 'rid', 'report.md', json_name='bundle.json')
    assert 'worker (фоновый обработчик)' in page
    assert 'Скачать JSON bundle' in page
