"""v8.6.30: реальный прогон сложных кейсов и содержательная проверка отчётов.
Проверяет не только тесты ядра, но и то, что отчёт не врёт по типовым ошибкам:
- старые component/self шаги не превращаются в «сначала исправить схему»;
- запрос данных через Kafka не утверждается как корректный стек;
- аналитика не становится Document Store;
- входящий инициатор не считается внешней зависимостью;
- сценарии/таблицы/диаграммы используют эффективный маршрут, а не source=target из старого payload;
- SQL и русский язык не содержат известных артефактов.
"""
import json
import pathlib
import re
from engine import analyze
from report import markdown_report

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'REAL_COMPLEX_REPORTS_v8_6_30'
OUT.mkdir(exist_ok=True)

BAD_PATTERNS = {
    'request_data_as_kafka': r'запрашивает данные.*Основной способ взаимодействия: Kafka|запрашивает данные.*\| Kafka',
    'analytics_as_document_store': r'Аналитическое хранилище.*Документное хранилище|Документное хранилище.*Аналитическое хранилище',
    'empty_matrix_rows': r'\| — \| — \|',
    'duplicated_status_sql': r'status text NOT NULL,\n\s*status text NOT NULL',
    'russian_sql_identifiers': r'идентификатор события uuid|идентификатор сквозной связи uuid|тело сообщения jsonb',
    'bad_ru_fragments': r'лимит запросовing|топикs|сверка-сверку|Без очередь|без очередь|Какой целевое|какой целевое|Горячий рассылка|не виден|промышленный запуск-вариант|клиентский лимиты запросовer|операционном основной поток|аналитическое хранилище находятся',
    'old_self_route': r'GraphQL BFF → GraphQL BFF|Сервис процесса → Сервис процесса',
}


def payload_from_saved_result(path: pathlib.Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    model = data['model']
    return {'meta': model['meta'], 'systems': list(model['systems'].values()), 'steps': model['steps']}


def check_no_bad_patterns(name: str, md: str):
    errors = []
    for key, pattern in BAD_PATTERNS.items():
        m = re.search(pattern, md, re.I)
        if m:
            line = md.count('\n', 0, m.start()) + 1
            errors.append(f'{name}: {key} at line {line}: {m.group(0)[:120]}')
    return errors


def run_saved_complex_cases():
    errors = []
    checked = 0
    for path in sorted(ROOT.glob('COMPLEX_CASE_*.json')):
        payload = payload_from_saved_result(path)
        res = analyze(payload)
        if not res.get('ok'):
            errors.append(f'{path.name}: analyze failed {res.get("errors")}')
            continue
        md = markdown_report(res)
        (OUT / f'REPORT_{path.stem}.md').write_text(md, encoding='utf-8')
        checked += 1
        errors.extend(check_no_bad_patterns(path.name, md))
        # Для старых сложных кейсов component steps должны быть распознаны, а не объявлены ошибкой.
        if 'сначала исправить схему' in md:
            errors.append(f'{path.name}: unexpected invalid_schema in complex report')
    return checked, errors


def run_user_regression_case():
    payload = {
        'meta': {'name': 'Регресс пользовательского отчёта', 'entity': 'Entity', 'money': 'no', 'regulatory': False, 'sla_ms': 1000, 'load_rps': 100, 'peak_factor': 2, 'ordering': 'per_entity'},
        'systems': [
            {'name':'Система-инициатор','role':'external'},
            {'name':'Сервис процесса','role':'internal'},
            {'name':'Старый контур','role':'legacy'},
            {'name':'Внешняя система / партнёр','role':'external'},
            {'name':'Аналитическое хранилище','role':'analytics'},
        ],
        'steps': [
            {'order':1,'name':'Система-инициатор передаёт данные в Сервис процесса','system':'Система-инициатор','source_system':'Система-инициатор','target_system':'Сервис процесса','channel':'api_gateway','blocking':True,'timeout_ms':200,'retry':'manual','idempotency':'key','writes_entity':False},
            {'order':2,'name':'Сервис процесса запрашивает данные у Старый контур','system':'Сервис процесса','source_system':'Сервис процесса','target_system':'Старый контур','channel':'kafka','blocking':False,'timeout_ms':0,'retry':'auto','idempotency':'none','writes_entity':True,'depends_on':1},
            {'order':3,'name':'Сервис процесса передаёт данные в Внешняя система / партнёр','system':'Сервис процесса','source_system':'Сервис процесса','target_system':'Внешняя система / партнёр','channel':'odata','blocking':True,'timeout_ms':500,'retry':'manual','idempotency':'key','writes_entity':False,'depends_on':2},
            {'order':4,'name':'Сервис процесса передаёт данные в Аналитическое хранилище','system':'Сервис процесса','source_system':'Сервис процесса','target_system':'Аналитическое хранилище','channel':'mongodb','blocking':False,'timeout_ms':0,'retry':'none','idempotency':'none','writes_entity':False,'depends_on':3},
        ]
    }
    res = analyze(payload)
    assert res.get('ok'), res.get('errors')
    md = markdown_report(res)
    (OUT / 'USER_REPORT_REGRESSION_v8_6_30.md').write_text(md, encoding='utf-8')
    errors = check_no_bad_patterns('user_regression', md)
    if 'Шаг 1 «Система-инициатор' in md and 'Процесс блокируется на вызове внешней системы.' in md:
        errors.append('user_regression: входящий инициатор ошибочно считается внешней блокирующей зависимостью')
    if 'Основную сущность изменяют несколько систем' in md or 'Несколько систем явно изменяют одну сущность' in md:
        errors.append('user_regression: входящий инициатор ошибочно считается вторым писателем')
    if 'Основной способ взаимодействия: Kafka' in md and 'Сервис процесса запрашивает данные у Старый контур' in md:
        errors.append('user_regression: запрос данных через Kafka утверждён как корректный стек')
    if 'Основной способ взаимодействия: Документное хранилище' in md and 'Аналитическое хранилище' in md:
        errors.append('user_regression: аналитический контур подменён документным хранилищем')
    if 'сначала исправить схему' not in md:
        errors.append('user_regression: некорректный request_data через Kafka не подсвечен как ошибка схемы')
    return errors


def main():
    checked, errors = run_saved_complex_cases()
    errors.extend(run_user_regression_case())
    if errors:
        for e in errors:
            print('FAIL:', e)
        raise SystemExit(1)
    print(f'REAL_COMPLEX_REPORTS_v8630 ok: complex_cases={checked}, output={OUT.name}')

if __name__ == '__main__':
    main()
