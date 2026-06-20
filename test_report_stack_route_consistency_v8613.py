from engine import analyze
from report import markdown_report


def _payload():
    return {
        'meta': {
            'name': 'Проверка согласованности маршрута и стека',
            'entity': 'Entity',
            'goal': 'Проверить, что основной стек выбирается по связи между участниками, а не по служебной записи в БД.',
            'lookup_keys': 'businessId + eventId',
            'statuses': 'CREATED, PROCESSING, DONE, FAILED',
            'fields': 'businessId:string, eventId:uuid, correlationId:uuid, status:string',
        },
        'systems': [
            {'name': 'Система-инициатор', 'role': 'internal'},
            {'name': 'Сервис процесса', 'role': 'internal'},
            {'name': 'Хранилище состояния процесса', 'role': 'db'},
            {'name': 'Внешняя система / партнёр', 'role': 'external'},
            {'name': 'Аналитическое хранилище', 'role': 'dwh'},
            {'name': 'Журнал событий Pulsar', 'role': 'broker'},
        ],
        'steps': [
            # Специально оставляем channel=db, чтобы проверить защиту отчёта от старой ошибки:
            # БД не должна подменять основной способ связи между участниками.
            {'order': 1, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'source_system': 'Система-инициатор', 'system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'db', 'blocking': 'yes', 'writes_entity': 'yes'},
            {'order': 2, 'name': 'Сервис процесса сохраняет результат в Хранилище состояния процесса', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Хранилище состояния процесса', 'channel': 'db', 'blocking': 'yes', 'writes_entity': 'yes', 'depends_on': '1'},
            {'order': 3, 'name': 'Сервис процесса передаёт данные в Внешняя система / партнёр', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Внешняя система / партнёр', 'channel': 'db', 'blocking': 'no', 'writes_entity': 'yes', 'depends_on': '2'},
            {'order': 4, 'name': 'Сервис процесса передаёт данные в Аналитическое хранилище', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Аналитическое хранилище', 'channel': 'db', 'blocking': 'no', 'writes_entity': 'yes', 'depends_on': '2'},
            {'order': 5, 'name': 'Опубликовать событие в долговременный журнал событий', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Журнал событий Pulsar', 'channel': 'kafka', 'blocking': 'no', 'depends_on': '2'},
        ],
        'modules': [],
    }


def test_report_does_not_confuse_service_db_with_main_transport():
    md = markdown_report(analyze(_payload()))
    assert 'Шаг 1' in md and 'Основной способ взаимодействия: REST API' in md
    assert 'Шаг 3' in md and 'Основной способ взаимодействия: REST API' in md
    assert 'Шаг 4' in md and 'Основной способ взаимодействия: ETL/ELT-загрузка' in md
    assert 'Шаг 5' in md and 'Основной способ взаимодействия: Pulsar' in md
    assert 'Служебная запись в БД не должна подменять канал взаимодействия с получателем' in md
    assert 'БД процесса нужна как служебный компонент' in md
