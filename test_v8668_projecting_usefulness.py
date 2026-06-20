import engine
import process_parser


def test_meta_money_indirect_not_direct():
    p = process_parser.parse_process('''
процесс: Обратный поток
сущность: Operation
деньги: indirect
получить статус | УК -> Банк | rest | блокирует
сохранить входящее событие | Банк -> InboxDB(база) | db | пишет, идемпотентность:key
''')
    assert p['meta']['money'] == 'indirect'
    res = engine.analyze(p)
    assert res['model']['meta']['money'] == 'indirect'


def test_compact_route_has_source_and_target_not_self_link():
    p = process_parser.parse_process('''
процесс: Статусы УК
сущность: Operation
получить статус | УК -> Банк | rest | блокирует
сопоставить внешний ID | Банк -> MappingDB(база) | db
опубликовать событие | Банк -> Kafka | kafka | retry:auto, идемпотентность:key
''')
    res = engine.analyze(p)
    assert res['ok']
    routes = [(s['source_system'], s['target_system']) for s in res['model']['steps']]
    assert routes == [('УК', 'Банк'), ('Банк', 'MappingDB'), ('Банк', 'Kafka')]
    assert all(src != tgt for src, tgt in routes)
    assert res['process_understanding']['steps'][0]['route'] == 'УК → Банк'


def test_natural_text_requires_confirmation_and_caps_score():
    text = '''
процесс: Обратный поток статусов
сущность: Operation
деньги: indirect
УК отправляет в банк статусы операций, банк сохраняет входящее сообщение, банк сопоставляет внешний ID с внутренним, банк отправляет статус в ресурсные системы и DWH.
'''
    p = process_parser.parse_process(text)
    assert len(p['steps']) >= 4
    assert p['steps'][0]['source_system'] == 'УК'
    assert p['steps'][0]['target_system'].lower() == 'банк'
    res = engine.analyze(p)
    assert res['process_understanding']['confidence']['confidence_pct'] <= 70
    assert res['verdict']['score'] <= 4.8
    assert res['quality_gates']['readiness_levels']['design_ready'] is True
    assert res['quality_gates']['readiness_levels']['production_ready'] is False
    assert any(g['name'] == 'Карта процесса' and g['status'] == 'warn' for g in res['quality_gates']['gates'])


def test_legacy_step_format_gets_inferred_route():
    p = process_parser.parse_process('''
процесс: Legacy
сущность: Order
принять заказ | API | rest | пишет
сохранить заказ | DB(база) | db | пишет
опубликовать событие | Kafka | kafka
''')
    res = engine.analyze(p)
    routes = [(s['source_system'], s['target_system']) for s in res['model']['steps']]
    assert routes[0][1] == 'API'
    assert routes[1] == ('API', 'DB')
    assert routes[2] == ('DB', 'Kafka')
