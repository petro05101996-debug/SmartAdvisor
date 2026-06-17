# -*- coding: utf-8 -*-
"""v8.6.50: финальная пользовательская приёмка.
Проверяет, что тренажёр не вводит пользователя в заблуждение:
- слабая схема не проходит интервью даже при сильном устном ответе;
- сильная схема без устного ответа не считается успешным собеседованием;
- сильная схема + сильный ответ проходят;
- каталог, язык, старое ядро и пользовательские отчёты остаются рабочими.
"""
from __future__ import annotations
from copy import deepcopy
import json
import re
from pathlib import Path

from engine import analyze
from report import markdown_report
from learning import (
    list_cases, get_case, evaluate_learning_solution, validate_learning_catalog,
    learning_catalog_summary,
)

OUT = Path('/mnt/data')

STRONG_ANSWER = (
    "Сначала определяю границы процесса и участников: клиентский канал, сервис заявок, БКИ, fraud, БД, Kafka, DWH и аудит. "
    "Синхронно принимаем заявку и фиксируем состояние в БД, а публикацию события делаем через outbox, чтобы решение и событие не разошлись. "
    "Для Kafka задаю partition key по applicationId, добавляю eventId, correlationId, occurredAt, eventType и schemaVersion. "
    "Для БКИ и fraud задаю таймауты, circuit breaker, ограниченные повторы и fallback/manual review. "
    "На стороне потребителей нужны идемпотентность, inbox, DLQ/quarantine и replay. "
    "Контракты версионируем, проверяем backward compatibility и contract tests. "
    "ПДн в DWH обезличиваем, эксплуатационно смотрим lag, error rate, trace, correlationId, alerting, SLA и аудит. "
    "Для MVP можно упростить аналитику, но нельзя выбрасывать outbox, идемпотентность, ключ порядка, DLQ/replay и версионирование."
)

WEAK_ANSWER = "Я вызову БКИ, потом отправлю событие в Kafka. Если ошибка, попробуем ещё раз."

BAD_FRAGMENTS = [
    "сильный Middle+/Senior-готово", "после падения потребитель", "core dependency",
    "event-driven", "Fault tolerance", "Contract evolution", "Security / data",
    "business metrics", "read-your-writes", "bподтверждение",
]


def weak_payload(case_id: str = 'bank-credit-bki-fraud') -> dict:
    payload = deepcopy(get_case(case_id)['payload'])
    for step in payload['steps']:
        step['compensation'] = ''
        step['retry'] = 'none'
        step['idempotency'] = 'none'
        step['timeout_ms'] = ''
        step['name'] = str(step.get('name', '')).replace('outbox', 'запись статуса').replace('Outbox', 'запись статуса')
    payload['meta']['lookup_keys'] = 'applicationId'
    payload['meta']['fields'] = 'applicationId,status,updatedAt'
    return payload


def assert_clean_text(name: str, text: str):
    bad = [x for x in BAD_FRAGMENTS if x.lower() in text.lower()]
    assert not bad, f'{name}: bad fragments {bad}'
    assert re.search(r'Раздельная оценка собеседования', text), f'{name}: no separated interview score'


def main() -> dict:
    case_id = 'bank-credit-bki-fraud'
    weak = weak_payload(case_id)
    reference = get_case(case_id)['payload']

    weak_solution = evaluate_learning_solution(case_id, weak, mode='learning')
    weak_interview = evaluate_learning_solution(case_id, weak, mode='interview', answer_text=WEAK_ANSWER)
    weak_schema_strong_answer = evaluate_learning_solution(case_id, weak, mode='interview', answer_text=STRONG_ANSWER)
    reference_no_answer = evaluate_learning_solution(case_id, reference, mode='interview', answer_text='')
    reference_strong_answer = evaluate_learning_solution(case_id, reference, mode='interview', answer_text=STRONG_ANSWER)

    assert weak_solution['learning_score'] <= 5.5
    assert weak_interview['learning_score'] <= 5.5
    assert weak_schema_strong_answer['solution_score'] <= 5.5
    assert weak_schema_strong_answer['answer_score'] >= 8.0
    assert weak_schema_strong_answer['learning_score'] <= 4.9
    assert 'не компенсирует слабую схему' in weak_schema_strong_answer['learning_level']
    assert reference_no_answer['solution_score'] >= 8.0
    assert reference_no_answer['answer_score'] == 0.0
    assert reference_no_answer['learning_score'] <= 4.9
    assert 'слабое устное объяснение' in reference_no_answer['learning_level']
    assert reference_strong_answer['solution_score'] >= 8.0
    assert reference_strong_answer['answer_score'] >= 8.0
    assert reference_strong_answer['learning_score'] >= 9.0

    for name, ev in [
        ('weak_schema_strong_answer', weak_schema_strong_answer),
        ('reference_no_answer', reference_no_answer),
        ('reference_strong_answer', reference_strong_answer),
    ]:
        md = ev['report_markdown']
        assert_clean_text(name, md)
        (OUT / f'USER_ACCEPTANCE_{name}_v8650.md').write_text(md, encoding='utf-8')

    catalog = validate_learning_catalog(deep=True)
    assert catalog['ok'], catalog['issues'][:5]
    summary = learning_catalog_summary()
    tracks = summary.get('tracks', {})
    bad_tracks = [t for t in tracks if any(x in t for x in ['Fault', 'Performance', 'Banking', 'Security /', 'Event-driven', 'Contract evolution'])]
    assert not bad_tracks, bad_tracks
    assert len(list_cases()) >= 83

    old_payload = reference
    old_res = analyze(old_payload)
    assert old_res.get('ok'), old_res.get('errors')
    old_md = markdown_report(old_res)
    assert '# ' in old_md and len(old_md) > 1000
    (OUT / 'USER_ACCEPTANCE_legacy_analyze_v8650.md').write_text(old_md, encoding='utf-8')

    result = {
        'ok': True,
        'version': summary.get('version'),
        'case_count': len(list_cases()),
        'scores': {
            'weak_solution': weak_solution['learning_score'],
            'weak_interview': weak_interview['learning_score'],
            'weak_schema_strong_answer': {
                'solution_score': weak_schema_strong_answer['solution_score'],
                'answer_score': weak_schema_strong_answer['answer_score'],
                'interview_score': weak_schema_strong_answer['learning_score'],
                'level': weak_schema_strong_answer['learning_level'],
            },
            'reference_no_answer': {
                'solution_score': reference_no_answer['solution_score'],
                'answer_score': reference_no_answer['answer_score'],
                'interview_score': reference_no_answer['learning_score'],
                'level': reference_no_answer['learning_level'],
            },
            'reference_strong_answer': {
                'solution_score': reference_strong_answer['solution_score'],
                'answer_score': reference_strong_answer['answer_score'],
                'interview_score': reference_strong_answer['learning_score'],
                'level': reference_strong_answer['learning_level'],
            },
        },
        'catalog_tracks': len(tracks),
        'old_analyze': 'ok',
    }
    (OUT / 'USER_ACCEPTANCE_VERIFY_v8650.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result

if __name__ == '__main__':
    main()
