# -*- coding: utf-8 -*-
"""v8.6.29: регрессия по реальному отчёту пользователя.
Проверяет конкретные ошибки, найденные в отчёте после v8.6.28.
"""
from engine import analyze
from report import markdown_report

payload = {
    'meta': {'name': 'Проверка пользовательского отчёта v8.6.29', 'goal': 'Проверка отчёта после замечаний пользователя', 'entity': 'Entity'},
    'systems': [
        {'name':'Система-инициатор','role':'external'},
        {'name':'Сервис процесса','role':'internal'},
        {'name':'Старый контур','role':'legacy'},
        {'name':'Внешняя система / партнёр','role':'external'},
        {'name':'Аналитическое хранилище','role':'analytics'},
        {'name':'Хранилище состояния процесса','role':'db'},
    ],
    'steps': [
        {'order':1,'name':'Система-инициатор сохраняет результат в Сервис процесса','source_system':'Система-инициатор','system':'Система-инициатор','target_system':'Сервис процесса','channel':'api_gateway','blocking':'yes','writes_entity':'yes','retry':'auto','idempotency':'key','interaction_action':'save','interaction_timing':'sync','interaction_result':'save'},
        {'order':2,'name':'Сервис процесса запрашивает данные у Старый контур','source_system':'Сервис процесса','system':'Сервис процесса','target_system':'Старый контур','channel':'kafka','blocking':'no','retry':'auto','idempotency':'none','depends_on':'1','interaction_action':'request_data','interaction_timing':'later','interaction_result':'pass_next'},
        {'order':3,'name':'Сервис процесса передаёт данные в Внешняя система / партнёр','source_system':'Сервис процесса','system':'Сервис процесса','target_system':'Внешняя система / партнёр','channel':'odata','blocking':'yes','retry':'auto','idempotency':'key','depends_on':'2','interaction_action':'send_data','interaction_timing':'sync','interaction_result':'pass_next'},
        {'order':4,'name':'Сервис процесса передаёт данные в Аналитическое хранилище','source_system':'Сервис процесса','system':'Сервис процесса','target_system':'Аналитическое хранилище','channel':'mongodb','blocking':'no','retry':'auto','idempotency':'key','depends_on':'3','interaction_action':'send_data','interaction_timing':'later','interaction_result':'pass_next'},
    ],
}
md = markdown_report(analyze(payload))
open('USER_REPORT_v8_6_29.md', 'w', encoding='utf-8').write(md)
required = [
    'сначала исправить схему',
    'Шаг называется запросом данных, но выбран брокер сообщений',
    'Основной способ взаимодействия: ETL/ELT-загрузка',
    'event_id uuid UNIQUE',
    'correlation_id uuid NOT NULL',
    'CREATE TABLE inbox_dedup',
]
for phrase in required:
    assert phrase in md, phrase
for bad in [
    'Основной способ взаимодействия: Kafka.\n**Где:** связь идёт от «Сервис процесса» к «Старый контур»',
    'Основной способ взаимодействия: Документное хранилище',
    'Основную сущность изменяют несколько систем',
    'status text NOT NULL,\n    status text NOT NULL',
    'идентификатор события uuid',
    '| — |',
    'экспоненциальная увеличением',
    'Какой целевое время ответа',
    'сквозной сквозной',
    'Как выполнить повторная обработка',
]:
    assert bad not in md, bad
print('USER_REPORT_REGRESSION_v8629 ok')
