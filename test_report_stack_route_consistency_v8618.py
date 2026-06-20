# -*- coding: utf-8 -*-
from engine import analyze
from report import markdown_report


def test_analytics_target_is_not_reported_as_primary_db_and_language_is_cleaner():
    payload = {
        'meta': {'name': 'Проверка аналитической связи', 'entity': 'Operation', 'goal': 'проверить отчёт'},
        'systems': [
            {'name': 'Сервис процесса', 'role': 'internal'},
            {'name': 'Хранилище состояния процесса', 'role': 'db'},
            {'name': 'Аналитическое хранилище', 'role': 'analytics'},
        ],
        'steps': [
            {'order': 1, 'name': 'Хранилище состояния процесса сверяет данные с Аналитическое хранилище',
             'source_system': 'Хранилище состояния процесса', 'system': 'Хранилище состояния процесса',
             'target_system': 'Аналитическое хранилище', 'channel': 'data_warehouse', 'blocking': 'no',
             'retry': 'auto', 'idempotency': 'natural', 'depends_on': ''}
        ],
    }
    md = markdown_report(analyze(payload))
    assert 'Основной способ взаимодействия: Основная база данных' not in md
    assert 'Основной способ взаимодействия: Передача изменений из базы данных' in md
    assert 'требование ко времени ответа' not in md
    assert 'без таблица исходящих сообщений' not in md


def test_sftp_file_to_external_is_not_rewritten_to_callback():
    payload = {
        'meta': {'name': 'Файл партнёру', 'entity': 'Document', 'goal': 'проверить файл'},
        'systems': [
            {'name': 'Сервис процесса', 'role': 'internal'},
            {'name': 'Внешняя система / партнёр', 'role': 'external'},
        ],
        'steps': [
            {'order': 1, 'name': 'Сервис процесса передаёт файл в Внешняя система / партнёр',
             'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Внешняя система / партнёр',
             'channel': 'sftp', 'blocking': 'no', 'retry': 'auto', 'idempotency': 'key', 'depends_on': ''}
        ],
    }
    md = markdown_report(analyze(payload))
    assert 'Основной способ взаимодействия: SFTP' in md
    assert 'Основной способ взаимодействия: REST API' not in md
