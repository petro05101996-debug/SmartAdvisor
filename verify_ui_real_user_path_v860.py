# -*- coding: utf-8 -*-
from pathlib import Path
import json, shutil, re
from playwright.sync_api import sync_playwright, expect
import ui

TECH_TERMS = ['REST','Kafka','RabbitMQ','Redis','SOAP','gRPC','GraphQL','OData','Pulsar','NATS','SFTP','CDC','ETL','Airflow','Spark','dbt','WebSocket','MQTT']

html = ui.form_page().replace('</head>', '''<script>
window.__submittedPayloads=[];
window.fetch=async function(url, opts){
 if(String(url).includes('/api/analyze')){
  try{window.__submittedPayloads.push(JSON.parse(opts && opts.body || '{}'));}catch(e){window.__submittedPayloads.push({parseError:String(e)});}
  return new Response(JSON.stringify({ok:true,id:'real-user-probe'}),{status:200,headers:{'Content-Type':'application/json'}});
 }
 return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}});
};
</script></head>''')

checks=[]
def ok(name, details=''): checks.append(('OK', name, details))
def fail(name, details=''): checks.append(('FAIL', name, details))

def launch(p):
    exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

def visible_text(page):
    return page.locator('body').inner_text()

def assert_no_tech_visible(page, context):
    text=visible_text(page)
    bad=[t for t in TECH_TERMS if t in text]
    if bad: fail('no_tech_before_stack_'+context, ', '.join(bad[:10]))
    else: ok('no_tech_before_stack_'+context)

with sync_playwright() as p:
    browser=launch(p)
    page=browser.new_page(viewport={'width':390,'height':844})
    page.set_default_timeout(7000)
    console=[]
    page.on('console', lambda msg: console.append((msg.type,msg.text)))
    page.on('pageerror', lambda exc: console.append(('pageerror',str(exc))))
    page.set_content(html, wait_until='load')
    page.wait_for_timeout(500)
    Path('real_user_start_text.txt').write_text(visible_text(page), encoding='utf-8')
    page.screenshot(path='real_user_start.png', full_page=True)
    txt=visible_text(page)
    if 'Ответьте на 5 вопросов' not in txt and 'универсальных вариантов' not in txt:
        ok('initial_no_old_wizard_text')
    else:
        fail('initial_no_old_wizard_text', 'old wizard wording visible')
    assert_no_tech_visible(page,'initial')
    if page.locator('[data-action="flow-stage"][data-stage="interactions"]').first.is_disabled():
        ok('interactions_locked_until_participants')
    else:
        fail('interactions_locked_until_participants')

    # Participants: real user adds all needed participants first.
    for text in ['Добавить инициатора','Добавить сервис процесса','Добавить внешнюю систему','Добавить хранилище состояния','Добавить аналитику','Добавить ручной разбор']:
        page.get_by_text(text, exact=False).first.click()
    ok('participants_added', f"systems={page.locator('.system-card').count()}")
    assert_no_tech_visible(page,'after_participants')

    # Move to interactions.
    page.get_by_role('button', name=re.compile('Дальше: связи')).click()
    ok('stage_interactions_open')
    assert_no_tech_visible(page,'interactions_empty')

    def add_interaction(source, target, action, timing, result, basis):
        page.select_option('#interactionSource', value=source)
        page.select_option('#interactionTarget', value=target)
        page.select_option('#interactionAction', value=action)
        page.select_option('#interactionTiming', value=timing)
        page.select_option('#interactionResult', value=result)
        page.select_option('#interactionBasis', label=basis)
        page.get_by_role('button', name='Добавить связь в цепочку').click()
        page.wait_for_timeout(100)

    add_interaction('Система-инициатор','Сервис процесса','send_data','sync','pass_next','результат предыдущего взаимодействия')
    add_interaction('Сервис процесса','Внешняя система / партнёр','request_data','sync','save','после ответа внешней системы')
    add_interaction('Сервис процесса','Хранилище состояния процесса','save','sync','save','после сохранения состояния')
    add_interaction('Внешняя система / партнёр','Сервис процесса','wait_status','later','save','после позднего статуса')
    add_interaction('Сервис процесса','Оператор / ручной разбор','send_data','background','manual','результат предыдущего взаимодействия')
    add_interaction('Хранилище состояния процесса','Аналитическое хранилище','compare','background','check','по расписанию или контрольной отметке')
    ok('interactions_added', f"relations={page.locator('.relation-card').count()}, steps={page.locator('[data-step-id]').count()}")
    assert_no_tech_visible(page,'after_interactions')
    page.screenshot(path='real_user_interactions.png', full_page=True)

    # Clarifications: only branch questions should show.
    page.get_by_role('button', name=re.compile('Дальше: уточнения')).click()
    page.wait_for_timeout(300)
    groups=page.locator('.branch-question-group')
    group_titles=[groups.nth(i).inner_text().split('\n')[0] for i in range(groups.count())]
    ok('branch_questions_visible', '; '.join(group_titles[:8])) if groups.count() else fail('branch_questions_visible','none')
    # Click a set of relevant semantic answers. No free text.
    clicked=[]
    for label in ['история и повторная обработка','получателей', 'строгий порядок', 'быстро читать часто используемые данные', 'разгрузить основную БД', 'поиск', 'большие документы', 'историю изменений', 'ручные задачи', 'видеть сбои']:
        loc=page.locator('.branch-question-btn').filter(has_text=label)
        if loc.count():
            loc.first.click(); clicked.append(label)
    ok('branch_answers_clicked', ', '.join(clicked)) if clicked else fail('branch_answers_clicked','no labels matched')
    assert_no_tech_visible(page,'clarifications')

    # Generate stack.
    page.get_by_role('button', name='Определить стек по процессу').click()
    page.wait_for_timeout(500)
    tech_after=visible_text(page)
    found_after=[t for t in TECH_TERMS if t in tech_after]
    ok('tech_visible_after_stack', ', '.join(found_after[:12])) if found_after else fail('tech_visible_after_stack','no technology labels visible after stack')
    chips=page.locator('.channel-chip:visible').count()
    stack_cards=page.locator('.stack-simple-card:visible').count()
    ok('stack_cards_visible', f'chips={chips}, explanations={stack_cards}') if stack_cards else fail('stack_cards_visible')
    page.screenshot(path='real_user_stack.png', full_page=True)

    # Expert correction: ensure manual stack list exists and can change one technology.
    page.get_by_role('button', name='Экспертный режим', exact=True).click()
    page.evaluate('document.querySelectorAll("details").forEach(d=>d.open=true)')
    manual_count=page.locator('[data-action="set-channel"]').count()
    ok('manual_catalog_full', f'buttons={manual_count}') if manual_count>=55 else fail('manual_catalog_full', str(manual_count))
    rabbit=page.locator('[data-action="set-channel"][data-channel="rabbitmq"]')
    if rabbit.count():
        rabbit.first.click(force=True); ok('manual_override_rabbitmq')
    else: fail('manual_override_rabbitmq','not found')
    auto=page.locator('[data-action="auto-channel"]')
    if auto.count(): auto.first.click(force=True); ok('reset_auto_stack')
    else: fail('reset_auto_stack','not found')

    # Submit and validate payload.
    page.get_by_role('button', name='Проверить архитектуру').click()
    page.wait_for_timeout(500)
    submitted=page.evaluate('window.__submittedPayloads.length')
    if submitted: ok('submit_called', f'submitted={submitted}')
    else: fail('submit_called','0')
    payload=page.evaluate('window.__submittedPayloads[window.__submittedPayloads.length-1]') if submitted else {}
    sysnames={s.get('name') for s in payload.get('systems',[])}
    issues=[]
    for idx, step in enumerate(payload.get('steps',[]),1):
        for f in ['source_system','system','target_system']:
            if step.get(f) and step.get(f) not in sysnames:
                issues.append(f'step {idx} missing {f}={step.get(f)}')
        deps=[int(x.strip()) for x in str(step.get('depends_on','')).replace(';',',').split(',') if x.strip().isdigit()]
        if idx in deps: issues.append(f'step {idx} self-dependency')
        for d in deps:
            if d<1 or d>len(payload.get('steps',[])): issues.append(f'step {idx} bad dep {d}')
    if issues: fail('payload_references_valid','; '.join(issues[:10]))
    else: ok('payload_references_valid', f"systems={len(payload.get('systems',[]))}, steps={len(payload.get('steps',[]))}")
    errs=[x for x in console if x[0] in ('error','pageerror')]
    if errs: fail('console_errors', str(errs[:5]))
    else: ok('console_errors','0')
    browser.close()

lines=['# Проверка пути реального пользователя v8.6.6', '']
for st,name,details in checks:
    lines.append(f'- {st}: {name}' + (f' — {details}' if details else ''))
lines.append('')
lines.append(f"SUMMARY: {sum(1 for x,_,__ in checks if x=='OK')} ok, {sum(1 for x,_,__ in checks if x!='OK')} fail")
Path('REAL_USER_FLOW_v8_6_6.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
if any(x!='OK' for x,_,__ in checks):
    raise SystemExit(1)
