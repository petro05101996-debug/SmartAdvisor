from engine import analyze
from report import markdown_report


def test_report_explains_technology_decisions_and_alternatives():
    payload = {
        'meta': {'name': 'Тест объяснений решений', 'goal': 'Проверить понятность отчёта', 'entity': 'заявка'},
        'systems': [
            {'name': 'Клиент', 'role': 'external'},
            {'name': 'API Gateway', 'role': 'gateway'},
            {'name': 'Сервис', 'role': 'internal'},
            {'name': 'БД', 'role': 'db'},
            {'name': 'Kafka', 'role': 'broker'},
        ],
        'steps': [
            {'order': 1, 'name': 'Принять внешний запрос', 'source_system': 'Клиент', 'system': 'API Gateway', 'target_system': 'Сервис', 'channel': 'api_gateway', 'blocking': 'yes', 'retry': 'auto', 'idempotency': 'key', 'stack_reason': 'Выбрано автоматически: нужен единый внешний вход и лимит запросов.'},
            {'order': 2, 'name': 'Сохранить заявку', 'source_system': 'Сервис', 'system': 'Сервис', 'target_system': 'БД', 'channel': 'db', 'depends_on': '1', 'blocking': 'yes', 'writes_entity': 'yes', 'retry': 'auto', 'idempotency': 'key', 'stack_reason': 'Выбрано автоматически: шаг сохраняет состояние процесса.'},
            {'order': 3, 'name': 'Опубликовать событие', 'source_system': 'БД', 'system': 'Сервис', 'target_system': 'Kafka', 'channel': 'kafka', 'depends_on': '2', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'stack_reason': 'Выбрано автоматически: нужен поток событий и повторная обработка.'},
        ],
    }
    md = markdown_report(analyze(payload))
    assert '## Почему выбраны технологии и способы взаимодействия' in md
    assert 'Почему выбрано' in md
    assert 'Почему не другой вариант' in md
    assert 'Обязательные условия' in md
    assert 'Почему предлагается именно так' in md
    assert 'Почему нельзя просто не делать' in md
    assert 'API Gateway' in md and 'Kafka' in md
