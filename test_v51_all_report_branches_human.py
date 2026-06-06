from integration_architect_pro import Engine


def test_audit_existing_solution_report_is_human_readable_too():
    form = {
        'project_name': 'Audit existing chain',
        'task_type': 'audit_existing_solution',
        'audit_depth': 'deep',
        'current_systems_matrix': 'api | API заявок | service | Product | critical | yes | application\nkafka | Kafka | broker | Platform | critical | yes | events\ncrm | CRM | external_service | CRM | important | no | customer',
        'current_integration_matrix': 'api | kafka | Kafka | async | no | status event | 1s | yes | 3 | no | no | service | Product\nkafka | crm | Kafka/event | async | no | status event | 30s | yes | 5 | yes | eventId | service | CRM',
        'current_process_steps': '0 | root | 1 | Создать заявку | frontend | api | REST | yes | CREATED | ERROR | retry | yes\n1 | 1 | 2 | Опубликовать событие | api | kafka | Kafka | no | EVENT_SENT | EVENT_ERROR | DLQ/manual | yes',
        'current_error_matrix': 'kafka_publish_error | api | technical | no | yes | log_only | no | Platform | no\ncrm_error | crm | technical | no | yes | dlq/manual | yes | CRM | yes',
        'current_problem_matrix': 'duplicates | crm | weekly | дубли статусов в CRM | manual cleanup\nlost_event | api_to_kafka | monthly | CRM/DWH не видят часть изменений | manual reload',
    }
    md = Engine().generate(form)['markdown']
    for marker in ['## 0. Читаемый вывод', '### Что проверяем', '### Что делать', '### Почему именно так', '### Главные ограничения и риски', '## 2. Построенная текущая цепочка', '## 3. Что делать по проблемам и почему', '## 10. Что нельзя делать', '## 12. Тест-кейсы для проверки исправлений']:
        assert marker in md
    assert 'Что сделать:' in md and 'Почему:' in md
    assert '## 14. Expert appendix: матрицы' in md
