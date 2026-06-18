#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Release gate for v8.6.64 complete UI/UX layer."""
from __future__ import annotations
import json
import shutil
from pathlib import Path

import ui
from learning import get_case, evaluate_reference
from engine import analyze

REQUIRED_HOME = [
    'Что хотите сделать сейчас?', 'Потренироваться', 'Собрать интеграцию',
    'Понять термины', 'Найти решение', 'Ctrl+K', 'mobile-bottom-nav'
]
REQUIRED_LEARNING = [
    'Выберите глубину тренировки', 'Новичок', 'Собеседование', 'Senior-разбор',
    'Начать первый кейс', 'Весь каталог кейсов', 'caseSearch'
]
REQUIRED_CASE = [
    'Работайте по слоям', 'Карта закрытых и незакрытых рисков',
    'Как сказать на собеседовании', 'Проверить выбранное решение', 'Экспертный режим: JSON решения'
]
REQUIRED_RESULT = ['Executive summary', 'Что сделать первым', 'Production readiness']
REQUIRED_KNOWLEDGE = ['Knowledge base', 'Поиск по справочнику']
REQUIRED_GLOSSARY = ['Термины простыми словами', 'Outbox', 'DLQ', 'идемпотентность']
REQUIRED_PROGRESS = ['Карта навыков', 'Рекомендуемый маршрут Middle → Senior']
REQUIRED_REPORTS = ['История отчётов и попыток', 'Сохранение проектов', 'Экспорт']


def assert_fragments(name: str, html: str, fragments: list[str], issues: list[dict]):
    for f in fragments:
        if f not in html:
            issues.append({'page': name, 'missing': f})


def main() -> int:
    issues: list[dict] = []
    assert ui.APP_VERSION == '8.6.67-ultimate-gated'
    pages = {
        'home': ui.form_page(),
        'learning_home': ui.learning_home_page(),
        'case': ui.learning_case_page('bank-credit-bki-fraud'),
        'invariants': ui.invariant_reference_page(),
        'patterns': ui.design_pattern_reference_page(),
        'glossary': ui.glossary_page(),
        'progress': ui.progress_page(),
        'reports': ui.reports_page(),
    }
    assert_fragments('home', pages['home'], REQUIRED_HOME, issues)
    assert_fragments('learning_home', pages['learning_home'], REQUIRED_LEARNING, issues)
    assert_fragments('case', pages['case'], REQUIRED_CASE, issues)
    assert_fragments('invariants', pages['invariants'], REQUIRED_KNOWLEDGE, issues)
    assert_fragments('patterns', pages['patterns'], REQUIRED_KNOWLEDGE, issues)
    assert_fragments('glossary', pages['glossary'], REQUIRED_GLOSSARY, issues)
    assert_fragments('progress', pages['progress'], REQUIRED_PROGRESS, issues)
    assert_fragments('reports', pages['reports'], REQUIRED_REPORTS, issues)

    ref = evaluate_reference('bank-credit-bki-fraud')
    if not ref.get('ok') or ref.get('learning_score', 0) < 8.0:
        issues.append({'api': 'evaluate_reference', 'score': ref.get('learning_score')})
    result_html = ui.result_page('0'*32, analyze(get_case('bank-credit-bki-fraud')['payload']))
    assert_fragments('result', result_html, REQUIRED_RESULT, issues)

    for name, html in pages.items():
        if 'app-shell' not in html or 'cmdBackdrop' not in html:
            issues.append({'page': name, 'missing': 'global shell or command palette'})
        if len(html) < 10000:
            issues.append({'page': name, 'suspicious_size': len(html)})

    out = {'ok': not issues, 'version': ui.APP_VERSION, 'pages': {k: len(v) for k, v in pages.items()}, 'issues': issues}
    Path('COMPLETE_UIUX_VERIFY_v8663.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not issues else 1

if __name__ == '__main__':
    raise SystemExit(main())
