from report import _channel_decision, markdown_report
from engine import analyze


def _tech(step):
    return _channel_decision(step)['primary_channel']


def test_late_external_inbound_is_webhook_not_callback():
    step = {
        'order': 1,
        'name': 'Партнёр сам присылает результат во входящий веб-вызов',
        'source_system': 'Внешняя система / партнёр',
        'system': 'Внешняя система / партнёр',
        'target_system': 'Сервис процесса',
        'channel': 'callback',
        'blocking': 'no',
        'interaction_action': 'wait_status',
        'interaction_timing': 'later',
        'interaction_result': 'update_status',
    }
    assert _tech(step) == 'webhook'


def test_explicit_named_broker_and_platform_are_not_replaced():
    cases = [
        ('RabbitMQ — очередь задач', 'rabbitmq'),
        ('Журнал событий Pulsar', 'pulsar'),
        ('NATS — лёгкая шина сообщений', 'nats'),
        ('Redis Streams — поток событий', 'redis_streams'),
        ('ClickHouse — аналитическая база', 'clickhouse'),
        ('Объектное хранилище S3', 'object_storage'),
    ]
    for target, expected in cases:
        step = {
            'order': 1,
            'name': f'Сервис процесса передаёт данные в {target}',
            'source_system': 'Сервис процесса',
            'system': 'Сервис процесса',
            'target_system': target,
            'channel': 'kafka',
            'blocking': 'no',
            'interaction_action': 'notify_many' if 'очеред' in target or 'шина' in target or 'Pulsar' in target or 'Streams' in target else 'send_data',
            'interaction_timing': 'later',
            'interaction_result': 'pass_next',
        }
        assert _tech(step) == expected, (target, _tech(step), expected)


def test_report_mentions_service_components_separately_from_main_stack():
    payload = {
        'meta': {'name': 'Проверка основного стека и служебных компонентов', 'entity': 'Entity', 'lookup_keys': 'businessId', 'statuses': 'NEW,DONE', 'fields': 'businessId:string'},
        'systems': [
            {'name': 'Сервис процесса', 'role': 'internal'},
            {'name': 'Внешняя система / партнёр', 'role': 'external'},
            {'name': 'Хранилище состояния процесса', 'role': 'db'},
        ],
        'steps': [{
            'order': 1,
            'name': 'Сервис процесса передаёт данные в Внешняя система / партнёр',
            'source_system': 'Сервис процесса',
            'system': 'Сервис процесса',
            'target_system': 'Внешняя система / партнёр',
            'channel': 'db',
            'blocking': 'no',
            'writes_entity': 'yes',
            'interaction_action': 'send_data',
            'interaction_timing': 'later',
            'interaction_result': 'save',
        }],
        'modules': [],
    }
    md = markdown_report(analyze(payload))
    assert 'Основной способ взаимодействия: Обратный вызов' in md
    assert 'БД процесса нужна как служебный компонент' in md
    assert 'Основной способ взаимодействия: Основная база данных' not in md
