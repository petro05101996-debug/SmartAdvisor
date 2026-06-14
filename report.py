# -*- coding: utf-8 -*-
"""Генерация markdown-отчёта по результату анализа."""
from engine import SEVERITY_RU

STATUS_RU = {
    'ok': 'Проверено', 'warn': 'Требует проверки', 'unknown': 'Не указано', 'fail': 'Блокирует выпуск',
    'pass': 'Проходит'
}


def _a(out, text=''):
    out.append(text)


def _clean_sentence(text):
    return str(text).strip().rstrip('.')


def _join_items(items):
    cleaned = [_clean_sentence(x) for x in (items or []) if str(x).strip()]
    return '; '.join(cleaned)


def _finding_groups(res):
    if res.get('finding_groups'):
        return res['finding_groups']
    groups = []
    for f in res.get('findings', []):
        groups.append({**f, 'count': 1, 'affected': [f.get('where', '')],
                       'where_summary': f.get('where', ''), 'where': f.get('where', '')})
    return groups


def _affected_lines(group, limit=20):
    affected = [x for x in (group.get('affected') or []) if str(x).strip()]
    if not affected:
        return []
    lines = affected[:limit]
    if len(affected) > limit:
        lines.append(f'Ещё затронуто мест: {len(affected) - limit}.')
    return lines


def markdown_report(res):
    m = res['model']['meta']
    g = res['model']['graph']
    v = res['verdict']
    comp = res.get('completeness') or {'summary': 'Полнота вводных не рассчитана.', 'missing': []}
    gates = res.get('quality_gates') or {'readiness': 'не рассчитано', 'gates': []}
    checklist = res.get('checklist') or {'items': [], 'counters': {}}
    artifacts = res.get('artifacts') or {}
    groups = _finding_groups(res)
    out = []
    a = lambda text='': _a(out, text)

    a(f"# Архитектурный разбор: {m['name']}")
    a('')
    grouped_counts = v.get('group_counts') or {}
    if grouped_counts:
        a(f"**Итоговый вывод:** {v['verdict']} Оценка архитектурной готовности: {v['score']}/10. "
          f"Найдено классов рисков: критичных — {grouped_counts.get('critical', 0)}, "
          f"высоких — {grouped_counts.get('high', 0)}, средних — {grouped_counts.get('medium', 0)}. "
          f"Всего отдельных срабатываний правил: {sum(v['counts'].values())}.")
    else:
        a(f"**Итоговый вывод:** {v['verdict']} Оценка архитектурной готовности: {v['score']}/10. "
          f"Найдено критичных рисков: {v['counts']['critical']}, высоких рисков: {v['counts']['high']}, "
          f"средних рисков: {v['counts']['medium']}.")
    a(f"**Готовность к production:** {gates.get('readiness', 'не рассчитано')}. "
      f"**{comp.get('summary', '')}**")
    a('')
    if m['goal']:
        a(f"**Бизнес-цель:** {m['goal']}")
    a(f"**Основная сущность:** {m['entity']}. "
      f"Деньги: {m['money']}. Регуляторика: {'да' if m['regulatory'] else 'нет'}. "
      f"Клиентский сценарий: {'да' if m['customer_visible'] else 'нет'}.")
    if m['sla_ms']:
        a(f"**SLA ответа:** {m['sla_ms']} мс; бюджет таймаутов критического пути: "
          f"{g['critical_budget_ms']} мс.")
    a('')

    a('## Проверка готовности к production (quality gates)')
    a('')
    if gates.get('gates'):
        a('| Проверка | Статус | Что мешает выпуску | Что нужно уточнить |')
        a('|---|---|---|---|')
        for gate in gates['gates']:
            fail = _join_items(gate.get('fail') or []) or '—'
            warn = _join_items(gate.get('warn') or []) or '—'
            a(f"| {gate['name']} | {STATUS_RU.get(gate['status'], gate['status'])} | {fail} | {warn} |")
    else:
        a('Проверка готовности к production не рассчитана.')
    a('')

    a('## Какие вводные нужно уточнить')
    a('')
    if comp.get('missing'):
        a('| Приоритет | Область | Что нужно уточнить | Почему это важно |')
        a('|---|---|---|---|')
        for item in comp['missing']:
            a(f"| {item['priority']} | {item['area']} | {item['question']} | {item['why']} |")
    else:
        a('Критичных пропусков во вводных не найдено. При этом архитектурное ревью и согласование контрактов всё равно нужны.')
    a('')

    a('## Обязательный архитектурный чек-лист')
    a('')
    if checklist.get('items'):
        a('| Область | Статус | Что проверяется | Как закрыть пункт |')
        a('|---|---|---|---|')
        for item in checklist['items']:
            a(f"| {item['area']} | {STATUS_RU.get(item['status'], item['status'])} | "
              f"{_clean_sentence(item['title'])}. {item['check']} | {item['fix']} |")
    else:
        a('Архитектурный чек-лист не рассчитан.')
    a('')


    radar = res.get('detail_radar') or {'summary': 'Матрица деталей не рассчитана.', 'probes': []}
    a('## Матрица деталей, которые нельзя забыть')
    a('')
    a(radar.get('summary', 'Матрица деталей не рассчитана.'))
    a('')
    if radar.get('probes'):
        a('| Область | Статус | Что проверить | Почему это важно | Как закрыть |')
        a('|---|---|---|---|---|')
        for item in radar['probes']:
            examples = ''
            if item.get('examples'):
                examples = ' Примеры: ' + '; '.join(item.get('examples') or []) + '.'
            a(f"| {item['area']} | {STATUS_RU.get(item['status'], item['status'])} | "
              f"{_clean_sentence(item['title'])}. {item['question']} | {item['why']} | {item['how']}{examples} |")
    else:
        a('Матрица деталей не рассчитана.')
    a('')

    a('## Варианты архитектурного решения')
    a('')
    for alt in res.get('alternatives', []):
        a(f"### {alt['name']}")
        a('')
        a(f"Этот вариант подходит, когда {alt['when']}")
        a(f"Оценка варианта: стоимость — {alt['cost']}; надёжность — {alt['reliability']}; риск — {alt['risk']}.")
        a('')
        a('В вариант нужно включить следующие изменения:')
        for c in alt.get('changes', []):
            a(f"- {c}")
        if alt.get('must_close'):
            a('')
            a(f'Перед внедрением обязательно закрыть блокеры из раздела «Найденные риски». Количество классов блокеров: {len(alt["must_close"])}.')
        a('')
        a(alt.get('not_enough', ''))
        a('')

    scenario = res.get('scenario') or {}
    a('## Сценарная основа для дальнейшей разработки')
    a('')
    if scenario:
        if scenario.get('statuses'):
            a('**Рекомендуемая статусная модель:** ' + ', '.join(scenario.get('statuses', [])) + '.')
            a('')
        a('### Основной сценарий')
        a('')
        for st in scenario.get('main_flow', []):
            a(f"{st['order']}. **{st['title']}**")
            a(f"   - Что происходит: {st['what_happens']}")
            a(f"   - Зависимость: {st['depends_on']}.")
            a(f"   - Результат: {st['result']}")
            if st.get('controls'):
                a('   - Контроли: ' + '; '.join(st['controls']) + '.')
            a(f"   - При ошибке: {st['failure_handling']}")
        a('')
        if scenario.get('alternative_flows'):
            a('### Альтернативные сценарии')
            a('')
            for i, alt in enumerate(scenario.get('alternative_flows', []), 1):
                a(f"{i}. **{alt['name']}**")
                a(f"   - Когда возникает: {alt['trigger']}")
                for step_text in alt.get('steps', []):
                    a(f"   - {step_text}")
                a(f"   - Ожидаемый результат: {alt['result']}")
                a('   - Обязательные контроли: ' + '; '.join(alt.get('controls', [])) + '.')
                a('')
        if scenario.get('error_flows'):
            a('### Ошибочные сценарии, которые нужно учесть')
            a('')
            for i, err in enumerate(scenario.get('error_flows', []), 1):
                affected = f" Затронуто мест: {err.get('affected_count')}" if err.get('affected_count', 1) > 1 else ''
                a(f"{i}. **{err['name']}** — {err['where']}.{affected}")
                a(f"   - Что может пойти не так: {err['failure']}")
                a(f"   - Как должно обрабатываться: {err['expected_handling']}")
        a('')
        if scenario.get('development_tasks'):
            a('### Что перенести в постановку на разработку')
            a('')
            for t in scenario.get('development_tasks', []):
                a(f"- {t}")
            a('')
        if scenario.get('acceptance_criteria'):
            a('### Критерии приёмки')
            a('')
            for t in scenario.get('acceptance_criteria', []):
                a(f"- {t}")
            a('')
    else:
        a('Сценарная основа не рассчитана.')
        a('')

    a('## Карта процесса и последовательность взаимодействий')
    a('')
    a('```mermaid')
    a(res['diagrams']['flow'])
    a('```')
    a('')
    a('```mermaid')
    a(res['diagrams']['sequence'])
    a('```')
    a('')

    a('## Найденные риски и слабые места')
    a('')
    if not groups:
        a('Структурных проблем не обнаружено. Это не отменяет архитектурное ревью, код-ревью, контрактные проверки и нагрузочные тесты.')
    last_sev = None
    for f in groups:
        if f['severity'] != last_sev:
            last_sev = f['severity']
            a(f"### {SEVERITY_RU[f['severity']]}")
            a('')
        suffix = f" (затронуто мест: {f.get('count', 1)})" if f.get('count', 1) > 1 else ''
        a(f"**{f['title']}**{suffix} — {f.get('where_summary') or f.get('where') or '—'}")
        a('')
        a(f"Почему это важно: {f['why']}")
        a('')
        a(f"Что нужно сделать: {f['fix']}")
        affected = _affected_lines(f)
        if f.get('count', 1) > 1 and affected:
            a('')
            a('Затронутые места:')
            for w in affected:
                a(f"- {w}")
        a('')

    a('## Рекомендуемые архитектурные паттерны')
    a('')
    if not res['patterns']:
        a('Дополнительные архитектурные паттерны не требуются по текущим вводным.')
    for p in res['patterns']:
        a(f"**{p['name']}.** {p['why']}")
        a('')
        a('Обязательные контроли для паттерна: ' + '; '.join(p['controls']) + '.')
        a('')

    a('## Предлагаемая структура базы данных')
    a('')
    a('В проекте могут понадобиться следующие таблицы: ' + ', '.join(res['schema']['tables']) + '.')
    a('')
    a('```sql')
    a(res['schema']['ddl'])
    a('```')
    a('')

    a('## Definition of Ready: что должно быть готово до разработки')
    a('')
    for i in artifacts.get('definition_of_ready', []):
        a(f"- {i}")
    a('')

    a('## Definition of Done: что должно быть выполнено перед выпуском')
    a('')
    for i in artifacts.get('definition_of_done', []):
        a(f"- {i}")
    a('')

    a('## Мониторинг и эксплуатационные метрики')
    a('')
    for i in artifacts.get('monitoring', []):
        a(f"- {i}")
    a('')

    if artifacts.get('event_contract_skeleton'):
        a('## Черновик контракта события')
        a('')
        a('```json')
        a('{')
        sk = artifacts['event_contract_skeleton']
        for idx, (k, desc) in enumerate(sk.items()):
            comma = ',' if idx < len(sk) - 1 else ''
            a(f'  "{k}": "{desc}"{comma}')
        a('}')
        a('```')
        a('')

    a('## Чек-лист проверок и тестов')
    a('')
    for i, t in enumerate(res['tests'], 1):
        a(f"{i}. {t}")
    a('')

    crit_high = [f for f in groups if f['severity'] in ('critical', 'high')]
    a('## План внедрения и безопасного вывода в production')
    a('')
    a('**Этап 1 — обязательный минимум перед разработкой:** закройте все critical/high классы рисков и failed quality gates — '
      + ('; '.join(f['title'] for f in crit_high) + '.' if crit_high
         else 'critical/high рисков нет, можно начинать с целевой схемы.'))
    a('')
    a('**Этап 2 — production hardening:** закройте unknown/warn пункты чек-листа: контракты, '
      'наблюдаемость, replay, retention, сверка, нагрузочный тест.')
    a('')
    a('**Этап 3 — эксплуатация:** подготовьте runbook инцидентов, регулярную сверку, обучение поддержки и '
      'проверка replay/rollback на регламентной основе.')
    a('')
    return '\n'.join(out)
