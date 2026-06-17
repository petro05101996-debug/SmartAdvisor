import json
import pathlib
import re

import engine
import report

ROOT = pathlib.Path(__file__).resolve().parent
PAYLOAD = pathlib.Path('/mnt/data/mega_all_tech_payload_v8620.json')
if not PAYLOAD.exists():
    PAYLOAD = ROOT / 'mega_all_tech_payload_v8620.json'

payload = json.loads(PAYLOAD.read_text(encoding='utf-8'))
res = engine.analyze(payload)
assert res.get('ok') is True
md = report.markdown_report(res)
(ROOT / 'ALL_TECH_REPORT_v8_6_24_SCENARIOS.md').write_text(md, encoding='utf-8')

start = md.index('Приложение C. Сценарная основа')
end = md.index('Приложение D. Артефакты')
scenario = md[start:end]

required = [
    'карту множества интеграционных возможностей',
    'Сценарные блоки по типам взаимодействий',
    'Сквозные сценарии контроля',
    'Альтернативные сценарии',
    'Ошибочные сценарии и восстановление',
    'Критерии приёмки сценариев',
    'API и онлайн-взаимодействие',
    'Асинхронный обмен',
    'Данные и чтение',
    'Аналитика и загрузки',
    'Файлы и доставка контента',
    'Оркестрация процесса',
]
for token in required:
    assert token in scenario, f'missing scenario token: {token}'

for bad in [
    '### Основной сценарий\n\n1. Сервис процесса:',
    'Сервис процесса: Отправить корпоративное сообщение',
    'повторная обработка был пропущен',
    'повторная попытка должен',
    'лимит запросовs',
    'топикs',
    'дедупликации table',
    'ограниченный повторная попытка',
    'постепенно увеличивайте',
]:
    assert bad not in scenario, f'bad phrase in scenario: {bad}'

# Сквозные контроли не должны быть частью основного сценарного блока как линейные шаги.
main_part = scenario.split('### Сквозные сценарии контроля')[0]
assert 'Отправить метрики, логи и трассировки' not in main_part
assert 'Получить секрет интеграции из Vault/KMS' not in main_part
assert 'Записать неизменяемый audit journal' not in main_part

# Все old-style single-line alternatives должны быть раскрыты как мини-use-case.
assert '**Когда возникает:**' in scenario
assert '**Как должен пройти сценарий:**' in scenario
assert '**Ожидаемый результат:**' in scenario
assert '**Обязательные проверки:**' in scenario

# Таблица ошибок должна иметь ожидаемое восстановление.
assert '| Ошибка | Где возникает | Как система должна восстановиться |' in scenario
assert 'транзакционную таблицу исходящих сообщений' in scenario or 'таблица исходящих сообщений' in scenario

print('SCENARIOS_v8624 ok: scenario_lines=', len(scenario.splitlines()))
