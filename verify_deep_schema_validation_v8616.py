# -*- coding: utf-8 -*-
from pathlib import Path
import json, shutil
from playwright.sync_api import sync_playwright
import ui

html = ui.form_page()
checks = []
def ok(name, details=''): checks.append(('OK', name, details))
def fail(name, details=''): checks.append(('FAIL', name, details))

def launch(p):
    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

BASE_SYSTEMS = [
    {'id':'sys_a','name':'Система-инициатор','role':'internal'},
    {'id':'sys_proc','name':'Сервис процесса','role':'internal'},
    {'id':'sys_ext','name':'Внешняя система / партнёр','role':'external'},
    {'id':'sys_db','name':'Хранилище состояния процесса','role':'db'},
    {'id':'sys_ana','name':'Аналитическое хранилище','role':'analytics'},
    {'id':'sys_broker','name':'Журнал событий','role':'broker'},
    {'id':'sys_manual','name':'Оператор / ручной разбор','role':'internal'},
]

def run_case(page, steps):
    page.evaluate("([systems,steps])=>{state.systems=systems;state.steps=steps;state.stage='stack';state.schemaValidation=null;state.stackReady=false;renderAll();}", [BASE_SYSTEMS, steps])
    return page.evaluate("validateSchemaBeforeStack().issues.map(x=>({step:x.stepIndex,title:x.title,body:x.body,fix:x.fix}))")

def step(i, name, src, tgt, action='send_data', timing='sync', result='pass_next', ch='rest', blocking='yes'):
    return {'id':f'step_{i}','order':i,'name':name,'source_system':src,'system':src,'target_system':tgt,'channel':ch,'blocking':blocking,'retry':'auto','idempotency':'key','writes_entity':'yes' if result=='save' or action in ('save','update_status') else 'no','depends_on':str(i-1) if i>1 else '', 'interaction_action':action,'interaction_timing':timing,'interaction_result':result,'dependency_basis':'результат предыдущего взаимодействия'}

with sync_playwright() as p:
    browser=launch(p)
    page=browser.new_page(viewport={'width':1366,'height':900})
    page.set_content(html, wait_until='load')

    good = [
        step(1,'Система-инициатор передаёт данные в Сервис процесса','Система-инициатор','Сервис процесса','send_data','sync','pass_next','rest'),
        step(2,'Сервис процесса запрашивает данные у Внешняя система / партнёр','Сервис процесса','Внешняя система / партнёр','request_data','sync','save','rest'),
        step(3,'Сервис процесса сохраняет результат в Хранилище состояния процесса','Сервис процесса','Хранилище состояния процесса','save','sync','save','db'),
        step(4,'Внешняя система / партнёр передаёт поздний статус в Сервис процесса','Внешняя система / партнёр','Сервис процесса','wait_status','later','save','webhook','no'),
        step(5,'Хранилище состояния процесса сверяет данные с Аналитическое хранилище','Хранилище состояния процесса','Аналитическое хранилище','compare','background','check','data_warehouse','no'),
        step(6,'Сервис процесса передаёт данные в Оператор / ручной разбор','Сервис процесса','Оператор / ручной разбор','send_data','background','manual','rest','no'),
    ]
    issues=run_case(page, good)
    if not issues: ok('good_process_has_no_blocking_validation')
    else: fail('good_process_has_no_blocking_validation', json.dumps(issues, ensure_ascii=False))

    bad_storage = [step(1,'Сервис процесса передаёт данные в Хранилище состояния процесса','Сервис процесса','Хранилище состояния процесса','send_data','sync','pass_next','rest')]
    titles=[x['title'] for x in run_case(page,bad_storage)]
    if 'Передача данных направлена в хранилище' in titles: ok('send_data_to_storage_detected')
    else: fail('send_data_to_storage_detected', str(titles))

    bad_async = [step(1,'Сервис процесса передаёт данные в Внешняя система / партнёр','Сервис процесса','Внешняя система / партнёр','send_data','later','pass_next','callback','no')]
    titles=[x['title'] for x in run_case(page,bad_async)]
    if 'Есть асинхронный запрос партнёру, но нет обратного статуса' in titles: ok('missing_external_return_detected')
    else: fail('missing_external_return_detected', str(titles))

    bad_wait = [step(1,'Сервис процесса передаёт поздний статус в Внешняя система / партнёр','Сервис процесса','Внешняя система / партнёр','wait_status','later','save','callback','no')]
    titles=[x['title'] for x in run_case(page,bad_wait)]
    if 'Направление позднего статуса выглядит перепутанным' in titles: ok('late_status_direction_detected')
    else: fail('late_status_direction_detected', str(titles))

    bad_notify = [step(1,'Сервис процесса сообщает другим системам через Внешняя система / партнёр','Сервис процесса','Внешняя система / партнёр','notify_many','later','pass_next','rest','no')]
    titles=[x['title'] for x in run_case(page,bad_notify)]
    if 'Рассылка многим системам без канала событий' in titles: ok('notify_many_without_broker_detected')
    else: fail('notify_many_without_broker_detected', str(titles))

    bad_file = [step(1,'Сервис процесса передаёт файл в Хранилище состояния процесса','Сервис процесса','Хранилище состояния процесса','file','background','pass_next','file','no')]
    titles=[x['title'] for x in run_case(page,bad_file)]
    if 'Файл направлен в обычную БД' in titles: ok('file_to_db_detected')
    else: fail('file_to_db_detected', str(titles))

    # Проверяем применение сложной автоправки: добавление обратного статуса после async-запроса.
    page.evaluate("([systems,steps])=>{state.systems=systems;state.steps=steps;state.schemaValidation=validateSchemaBeforeStack();}", [BASE_SYSTEMS, bad_async])
    page.evaluate("applySchemaValidationFixes()")
    count = page.evaluate("state.steps.length")
    has_return = page.evaluate("state.steps.some(s=>s.interaction_action==='wait_status' && s.source_system==='Внешняя система / партнёр' && s.target_system==='Сервис процесса')")
    if count == 2 and has_return: ok('apply_fix_adds_late_status_step')
    else: fail('apply_fix_adds_late_status_step', f'count={count}, has_return={has_return}')
    browser.close()

lines=['# Глубокая проверка логики связей v8.6.16','']
for st,name,details in checks:
    lines.append(f'- {st}: {name}' + (f' — {details}' if details else ''))
lines.append('')
lines.append(f"SUMMARY: {sum(1 for x,_,__ in checks if x=='OK')} ok, {sum(1 for x,_,__ in checks if x!='OK')} fail")
Path('DEEP_SCHEMA_VALIDATION_v8_6_16.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
if any(x!='OK' for x,_,__ in checks):
    raise SystemExit(1)
