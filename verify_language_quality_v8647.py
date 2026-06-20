# -*- coding: utf-8 -*-
"""v8.6.47: проверка качества русского текста в учебном слое и отчётах."""
from __future__ import annotations
import json
from pathlib import Path

import ui
from learning import list_cases, get_case, evaluate_reference
from report import markdown_report
from engine import analyze

ROOT = Path(__file__).resolve().parent
SAMPLE_IDS = [
    'bank-credit-bki-fraud',
    'uk-bank-status-flow',
    'card-authorization-clearing',
    'iot-mqtt-alarms',
    'graphql-bff-aggregation',
    'search-reindex-bluegreen',
]
BAD_FRAGMENTS = [
    'Read-режимl', 'без частичный', 'заявленный целевое', 'операционный целевое',
    'без модель', 'freshness contract', 'change process', 'CREATE TABLE таблица',
    'Почему\nПочему', 'Открыть база знаний', 'Подходит, когда в процессе выбран признак',
    'Другой вариант не выбран', 'сырой JSON\n```json', 'Эталонный payload',
    'таблица исходящих сообщений-событие', 'Outbox-таблица-таблица', 'схемаVersion',
    'bподтверждение', 'boсрок', 'business metrics', 'technical metrics', 'alert rules',
    'breaker state', 'Read-your-writes', 'data quality metrics', 'event-driven', 'downпоток',
    'schema/version', 'required/optional', 'enum lifecycle', 'compatibility rules',
    'nullable', 'incident response', 'заведите история', 'параллелизмааа',
    'created/completed', 'stuck/', '/reconciled', 'dependencyName', 'core dependency',
    'degraded path', 'reject report', 'schema poisoning', 'silence policy',
]
REQUIRED_SECTIONS = [
    '## 1. Итоговая оценка', '## 2. Профиль навыков', '## 4. Сравнение с эталоном',
    '## 8. Эталонная схема решения', '## 10. Полный архитектурный отчёт ядра',
]

def scan_text(name: str, text: str):
    # Проверяем пользовательский текст, а не JavaScript/стили.
    text = __import__('re').sub(r'<script[\s\S]*?</script>', '', text, flags=__import__('re').I)
    text = __import__('re').sub(r'<style[\s\S]*?</style>', '', text, flags=__import__('re').I)
    issues = []
    for bad in BAD_FRAGMENTS:
        if bad in text:
            issues.append({'where': name, 'type': 'bad_fragment', 'fragment': bad})
    if '```json' in text and 'Ниже показан не сырой технический JSON' in text:
        issues.append({'where': name, 'type': 'raw_json_in_learning_report'})
    return issues

def main():
    issues = []
    cases = list_cases()
    sample_reports = []
    # Полная проверка каталога: все кейсы должны иметь раскрытые русские описания.
    for c in cases:
        blob = '\n'.join(str(c.get(k, '')) for k in ('title', 'track', 'goal', 'business_context', 'learning_goal'))
        issues.extend(scan_text('catalog:' + c['id'], blob))
        if len(str(c.get('goal', '')).strip()) < 20:
            issues.append({'where': 'catalog:' + c['id'], 'type': 'short_goal'})
    # Проверяем representative-набор отчётов по разным трекам; все кейсы выше
    # проверены как каталог, а генераторы отчёта проверяются на выборке, чтобы
    # verifier оставался пригодным для CI.
    sample_ids = set(SAMPLE_IDS)
    for c in cases:
        if c['id'] not in sample_ids:
            continue
        ev = evaluate_reference(c['id'])
        md = ev.get('report_markdown', '')
        issues.extend(scan_text('learning_report:' + c['id'], md))
        for sec in REQUIRED_SECTIONS:
            if sec not in md:
                issues.append({'where': 'learning_report:' + c['id'], 'type': 'missing_section', 'section': sec})
        out = ROOT / f'LANGUAGE_STYLE_SAMPLE_{c["id"]}_v8647.md'
        out.write_text(md, encoding='utf-8')
        sample_reports.append(str(out.name))
    # Старый проектировщик: проверяем, что обычный архитектурный отчёт тоже не содержит старых обрубков.
    base_payload = get_case('bank-credit-bki-fraud')['payload']
    base = analyze(base_payload)
    old_md = markdown_report(base)
    issues.extend(scan_text('legacy_architecture_report', old_md))
    (ROOT / 'LANGUAGE_STYLE_LEGACY_REPORT_v8647.md').write_text(old_md, encoding='utf-8')
    # UI-страницы как пользовательский текст.
    pages = {
        'learning_home': ui.learning_home_page(),
        'learning_case': ui.learning_case_page('bank-credit-bki-fraud'),
        'form': ui.form_page(),
        'invariants': ui.invariant_reference_page(),
        'patterns': ui.design_pattern_reference_page(),
    }
    for name, html in pages.items():
        issues.extend(scan_text('ui:' + name, html))
    result = {
        'ok': not issues,
        'case_count': len(cases),
        'reports_checked': len(sample_reports) + 1,
        'sample_reports': sample_reports,
        'issues': issues[:50],
        'issue_count': len(issues),
    }
    out_json = ROOT / 'LANGUAGE_STYLE_VERIFY_v8647.json'
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
