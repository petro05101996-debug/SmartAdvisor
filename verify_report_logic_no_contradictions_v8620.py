# -*- coding: utf-8 -*-
"""Глубокий аудит логики отчёта v8.6.20.
Проверяет не только зелёные unit-тесты, а типовые классы противоречий в отчёте:
- внешний запрос не подменяется БД/callback/webhook;
- аналитический контур не становится «способом взаимодействия»;
- аудит/секреты/маскирование/наблюдаемость не становятся обычными бизнес-шагами;
- заведомо кривая связь не получает уверенный стек;
- в markdown нет старых машинных фраз и сырых Python-словарей.
"""
import json, glob, re, os
from pathlib import Path
from engine import analyze
from report import (
    markdown_report, _channel_decision, _is_outbound_external_v8619, _is_inbound_external_v8619,
    _is_analytics_target_v8619, _is_cross_control_step_v8619, _is_audit_v8619, _is_security_v8619,
    _is_observability_v8619, _route_error_v8620, _split_steps_v8619
)

payloads = []
# Основные сложные JSON-кейсы из архива
for p in sorted(glob.glob('COMPLEX_CASE_*.json')):
    payloads.append((p, json.loads(Path(p).read_text(encoding='utf-8'))))
# Ультра payload из v8.6.18, если есть
if Path('ULTRA_REAL_USER_PAYLOAD_v8_6_18.json').exists():
    payloads.append(('ULTRA_REAL_USER_PAYLOAD_v8_6_18.json', json.loads(Path('ULTRA_REAL_USER_PAYLOAD_v8_6_18.json').read_text(encoding='utf-8'))))
# Специальный регрессионный payload с намеренной ошибкой маршрута
payloads.append(('synthetic_core_regression', {
    'meta': {'name': 'synthetic v8.6.20 report audit', 'entity': 'Entity', 'regulatory': 'yes', 'statuses': 'NEW, SENT, DONE'},
    'systems': [
        {'name': 'Система-инициатор', 'role': 'external'},
        {'name': 'Сервис процесса', 'role': 'internal'},
        {'name': 'Хранилище состояния процесса', 'role': 'db'},
        {'name': 'Внешняя система / партнёр', 'role': 'external'},
        {'name': 'Аналитическое хранилище', 'role': 'analytics'},
        {'name': 'Контур наблюдаемости', 'role': 'observability'},
        {'name': 'Хранилище секретов', 'role': 'security'},
        {'name': 'Audit journal', 'role': 'audit'},
        {'name': 'Слой защиты и маскирования', 'role': 'security'},
        {'name': 'Внутренний сервис быстрых ответов', 'role': 'internal'},
    ],
    'steps': [
        {'order': 1, 'name': 'Система-инициатор передаёт данные в Сервис процесса', 'source_system': 'Система-инициатор', 'system': 'Система-инициатор', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': 'yes', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 2, 'name': 'Сервис процесса сохраняет результат в Хранилище состояния процесса', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Хранилище состояния процесса', 'channel': 'db', 'blocking': 'yes', 'writes_entity': 'yes', 'depends_on': '1', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 3, 'name': 'Сервис процесса передаёт данные в Внешняя система / партнёр', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Внешняя система / партнёр', 'channel': 'db', 'blocking': 'no', 'writes_entity': 'yes', 'depends_on': '2', 'retry': 'auto', 'idempotency': 'key', 'interaction_action': 'send_data', 'interaction_timing': 'later', 'interaction_result': 'save'},
        {'order': 4, 'name': 'Сервис процесса передаёт данные в Аналитическое хранилище', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Аналитическое хранилище', 'channel': 'data_warehouse', 'blocking': 'no', 'depends_on': '2', 'retry': 'auto', 'idempotency': 'key'},
        {'order': 5, 'name': 'Быстро получить ответ от внутреннего сервиса', 'source_system': 'Аналитическое хранилище', 'system': 'Сервис процесса', 'target_system': 'Внутренний сервис быстрых ответов', 'channel': 'grpc', 'blocking': 'yes', 'depends_on': '4'},
        {'order': 6, 'name': 'Нужно видеть, где завис процесс', 'source_system': 'Все шаги процесса', 'system': 'Сервис процесса', 'target_system': 'Контур наблюдаемости', 'channel': 'observability', 'blocking': 'no'},
        {'order': 7, 'name': 'Нужно безопасно хранить секреты и ключи', 'source_system': 'Сервис процесса', 'system': 'Сервис процесса', 'target_system': 'Хранилище секретов', 'channel': 'vault', 'blocking': 'yes'},
        {'order': 8, 'name': 'Записать неизменяемый audit journal', 'source_system': 'Сервис процесса', 'system': 'Audit journal', 'target_system': 'Audit journal', 'channel': 'db', 'blocking': 'yes'},
        {'order': 9, 'name': 'Классифицировать и маскировать чувствительные поля', 'source_system': 'Сервис процесса', 'system': 'Слой защиты и маскирования', 'target_system': 'Сервис процесса', 'channel': 'rest', 'blocking': 'no'},
    ]
}))

bad_text_patterns = [
    r'Основной способ взаимодействия: Аналитическое хранилище',
    r'Основной способ взаимодействия: Data Warehouse',
    r'Основной способ взаимодействия: Обратный вызов\b.*Сервис процесса переда[её]т данные в Внеш',
    r'Основной способ взаимодействия: Наблюдаемость',
    r'Основной способ взаимодействия: OAuth2/OIDC',
    r'Основной способ взаимодействия: Vault',
    r'лимит запросовs', r'повторная обработка должен', r'повторная попытка должен',
    r'каждая повторная попытка[^\n|.]*должен', r'таблица входящих сообщений для дедупликации table',
    r'\{\'tables\'', r'идентификатораа+', r'целевой целевое', r'ваш целевое', r'Без таймаут\b',
    r'auto-повтор', r'повторная попытка-шторм', r'thundering herd', r'backpressure',
]

failures = []
checked_steps = 0
# v8.6.62: old archived COMPLEX_CASE result files can make full markdown regression slow.
# In normal CI we perform channel/route logic on every payload, but run markdown text
# regression only on a representative sample plus the synthetic regression payload.
# Set FULL_AUDIT_REPORTS=1 to generate markdown for every archived case.
full_reports = os.environ.get('FULL_AUDIT_REPORTS') == '1'
markdown_sample_limit = len(payloads) if full_reports else 2
for idx, (label, payload) in enumerate(payloads):
    res = payload if isinstance(payload, dict) and 'model' in payload else analyze(payload)
    should_check_markdown = full_reports or idx < markdown_sample_limit or label == 'synthetic_core_regression'
    if should_check_markdown:
        md = markdown_report(res)
        if full_reports:
            Path(f'AUDIT_REPORT_{Path(label).stem}.md').write_text(md, encoding='utf-8')
        for pat in bad_text_patterns:
            if re.search(pat, md, flags=re.I | re.S):
                failures.append(f'{label}:bad_text:{pat}')
        if "```sql\n{'tables'" in md:
            failures.append(f'{label}:raw_schema_dict')
    main, controls = _split_steps_v8619(res['model']['steps'])
    for st in res['model']['steps']:
        checked_steps += 1
        dec = _channel_decision(st)
        primary = dec.get('primary_channel')
        name = st.get('name','')
        if _is_outbound_external_v8619(st) and primary in {'db','callback','webhook'}:
            failures.append(f'{label}:outbound_external_wrong:{st.get("order")}:{primary}')
        if _is_outbound_external_v8619(st) and primary == 'rest' and 'финальный бизнес-результат должен приходить отдельным входящим шагом' not in dec.get('why','') and (not st.get('blocking') or st.get('interaction_timing') == 'later'):
            failures.append(f'{label}:outbound_late_rest_bad_explanation:{st.get("order")}')
        if _is_inbound_external_v8619(st) and (not st.get('blocking')) and primary not in {'webhook','sftp','file','soap','rest'}:
            failures.append(f'{label}:inbound_external_odd:{st.get("order")}:{primary}')
        if _is_analytics_target_v8619(st) and primary in {'db','data_warehouse','data_lake','lakehouse'}:
            failures.append(f'{label}:analytics_target_wrong:{st.get("order")}:{primary}')
        if _is_audit_v8619(' '.join([name, st.get('system',''), st.get('target_system','')])) and primary == 'db':
            failures.append(f'{label}:audit_as_db:{st.get("order")}')
        if _is_security_v8619(name) and 'маскир' in name.lower() and primary == 'rest':
            failures.append(f'{label}:masking_as_rest:{st.get("order")}')
        if _route_error_v8620(st) and primary != 'invalid_schema':
            failures.append(f'{label}:route_error_not_blocked:{st.get("order")}:{primary}')
        if _is_cross_control_step_v8619(st) and st in main:
            failures.append(f'{label}:control_in_main:{st.get("order")}:{name}')
if failures:
    print('FAIL')
    for f in failures[:80]:
        print('-', f)
    print('total_failures=', len(failures), 'checked_steps=', checked_steps, 'payloads=', len(payloads))
    raise SystemExit(1)
print(f'REPORT_LOGIC_v8620 ok (fast markdown sample; FULL_AUDIT_REPORTS=1 for all reports): payloads={len(payloads)} checked_steps={checked_steps}')
