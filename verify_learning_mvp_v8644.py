# -*- coding: utf-8 -*-
"""v8.6.59 stable learning MVP smoke.
Проверяет актуальный простой UX тренажёра без тяжёлого рендера всех 83 отчётов.
FULL_AUDIT=1 включает полный прогон всех кейсов.
"""
import json, os
from learning import list_cases, evaluate_reference, evaluate_learning_solution
from ui import learning_home_page, learning_case_page

issues=[]
cases=list_cases()
if len(cases) < 10:
    issues.append(f'case_count<{len(cases)}>')
home=learning_home_page()
for fragment in ('Тренажёр системного аналитика','Как пользоваться','Начать первый кейс','Весь каталог кейсов','learning-grid'):
    if fragment not in home:
        issues.append('home_missing_'+fragment)

sample = cases if os.environ.get('FULL_AUDIT') == '1' else cases[:10]
summary=[]
for case in sample:
    page=learning_case_page(case['id'])
    for fragment in (case['title'], 'Проверить выбранное решение', 'REFERENCE_PAYLOAD', 'Показать эталон'):
        if fragment not in page:
            issues.append(f'case_page_missing:{case["id"]}:{fragment}')
    ev=evaluate_reference(case['id'])
    if not ev.get('base_ok'):
        issues.append(f'reference_invalid:{case["id"]}:{ev.get("validation_errors")}')
    if ev.get('learning_score',0) < 7.0:
        issues.append(f'reference_low_score:{case["id"]}:{ev.get("learning_score")}')
    md=ev.get('report_markdown','')
    for fragment in ('Учебный разбор','Профиль навыков','Полный архитектурный отчёт ядра'):
        if fragment not in md:
            issues.append(f'md_missing:{case["id"]}:{fragment}')
    summary.append({'id':case['id'], 'score':ev.get('learning_score'), 'level':ev.get('learning_level')})
invalid=evaluate_learning_solution(cases[0]['id'], {'meta': {'name':'bad'}, 'systems': [], 'steps': []})
if invalid.get('base_ok') is not False or not invalid.get('validation_errors'):
    issues.append('invalid_solution_not_explained')
print(json.dumps({'ok': not issues, 'case_count': len(cases), 'checked': len(sample), 'summary': summary, 'issues': issues}, ensure_ascii=False, indent=2))
if issues:
    raise SystemExit(1)
