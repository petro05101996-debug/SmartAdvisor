#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-facing UX gate for v8.6.64.
Checks that the UI actually exposes beginner-friendly explanations and does not only pass technical gates.
"""
from __future__ import annotations
import json
from pathlib import Path
import ui

REQUIRED = {
    'home': [
        'Начните с одного понятного действия', 'Пройти первый кейс', 'Не выбирайте технологию раньше процесса',
        'Плохо начинать с технологии', 'Хорошо начинать с участников'
    ],
    'learning': [
        'Если вы открыли тренажёр впервые', 'Не открывайте весь каталог из 83 кейсов сразу',
        'Начать первый кейс', 'Сначала термины', 'Я уже понимаю тему'
    ],
    'case': [
        'Режим новичка', 'Ответьте на 5 простых вопросов', 'Может ли событие потеряться',
        'Куда деть плохое сообщение', 'Важен ли порядок событий', 'Добавить защиту от потери события',
        'Простыми словами', 'Простой режим', 'Экспертный режим'
    ],
    'glossary': ['Сначала поймите, что ломается', 'Дубли', 'Потери', 'Порядок'],
    'reports': ['Как читать отчёт', 'Не начинайте с полного markdown', 'Сначала вердикт', 'Потом главные риски']
}

def check(name, html, issues):
    for f in REQUIRED[name]:
        if f not in html:
            issues.append({'page': name, 'missing': f})
    if 'uf-panel' not in html:
        issues.append({'page': name, 'missing': 'uf-panel'})
    if '8.6.67-ultimate-gated' not in html:
        issues.append({'page': name, 'missing': 'version'})

def main() -> int:
    assert ui.APP_VERSION == '8.6.67-ultimate-gated'
    pages = {
        'home': ui.form_page(),
        'learning': ui.learning_home_page(),
        'case': ui.learning_case_page('bank-credit-bki-fraud'),
        'glossary': ui.glossary_page(),
        'reports': ui.reports_page(),
    }
    issues=[]
    for name, html in pages.items():
        check(name, html, issues)
    case = pages['case']
    # Beginner controls must select the real visual-control IDs used by the model.
    for cid in ['outbox','dlq_replay','kafka_key','timeouts','versioning']:
        if f"ufSelectControl('{cid}')" not in case and f'ufSelectControl(\"{cid}\")' not in case:
            issues.append({'page':'case','missing_control_binding':cid})
        if f'value="{cid}"' not in case:
            issues.append({'page':'case','missing_visual_control':cid})
    out={'ok': not issues, 'version': ui.APP_VERSION, 'issues': issues, 'sizes': {k:len(v) for k,v in pages.items()}}
    Path('USER_FRIENDLY_VERIFY_v8664.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not issues else 1

if __name__ == '__main__':
    raise SystemExit(main())
