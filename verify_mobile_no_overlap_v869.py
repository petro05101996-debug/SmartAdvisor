# -*- coding: utf-8 -*-
from pathlib import Path
import re, shutil, json
from playwright.sync_api import sync_playwright
import ui

html = ui.form_page().replace('</head>', '''<script>
window.__submittedPayloads=[];
window.fetch=async function(url, opts){
 if(String(url).includes('/api/analyze')){
  try{window.__submittedPayloads.push(JSON.parse(opts && opts.body || '{}'));}catch(e){window.__submittedPayloads.push({parseError:String(e)});}
  return new Response(JSON.stringify({ok:true,id:'layout-probe'}),{status:200,headers:{'Content-Type':'application/json'}});
 }
 return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}});
};
</script></head>''')

VIEWPORTS=[('phone360',360,800),('phone390',390,844),('tablet768',768,1024),('desktop1366',1366,900)]
STAGES=[]

def launch(p):
    exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

def select_option_safe(page, sel, value=None, label=None):
    loc=page.locator(sel)
    if loc.count():
        if value is not None: loc.select_option(value=value)
        elif label is not None: loc.select_option(label=label)

def add_participants(page):
    for text in ['Добавить инициатора','Добавить сервис процесса','Добавить внешнюю систему','Добавить хранилище состояния','Добавить аналитику','Добавить ручной разбор']:
        page.get_by_text(text, exact=False).first.click()
        page.wait_for_timeout(30)

def go_interactions(page):
    btn=page.get_by_role('button', name=re.compile('Дальше: связи'))
    if btn.count(): btn.click()
    page.wait_for_timeout(150)

def add_interaction(page, source, target, action, timing, result, basis):
    select_option_safe(page,'#interactionSource', value=source)
    select_option_safe(page,'#interactionTarget', value=target)
    select_option_safe(page,'#interactionAction', value=action)
    select_option_safe(page,'#interactionTiming', value=timing)
    select_option_safe(page,'#interactionResult', value=result)
    select_option_safe(page,'#interactionBasis', label=basis)
    page.get_by_role('button', name='Добавить связь в цепочку').click()
    page.wait_for_timeout(80)

def add_demo_chain(page):
    add_interaction(page,'Система-инициатор','Сервис процесса','send_data','sync','pass_next','результат предыдущего взаимодействия')
    add_interaction(page,'Сервис процесса','Внешняя система / партнёр','request_data','sync','save','после ответа внешней системы')
    add_interaction(page,'Сервис процесса','Хранилище состояния процесса','save','sync','save','после сохранения состояния')
    add_interaction(page,'Внешняя система / партнёр','Сервис процесса','wait_status','later','save','после позднего статуса')
    add_interaction(page,'Хранилище состояния процесса','Аналитическое хранилище','compare','background','check','по расписанию или контрольной отметке')

def go_clarifications(page):
    page.get_by_role('button', name=re.compile('Дальше: уточнения')).click(); page.wait_for_timeout(200)

def answer_clarifications(page):
    labels=['история и повторная обработка','несколько получателей','строгий порядок','быстро читать часто используемые данные','разгрузить основную БД','поиск','большие документы','историю изменений','ручные задачи','видеть сбои']
    for label in labels:
        loc=page.locator('.branch-question-btn').filter(has_text=label)
        if loc.count():
            loc.first.click(); page.wait_for_timeout(20)

def generate_stack(page):
    loc=page.get_by_role('button', name='Определить стек по процессу')
    if loc.count(): loc.click()
    page.wait_for_timeout(300)

def rects(page):
    return page.evaluate('''() => {
      const selectors = ['.titleblock','.guidebar','.flow-stage-panel','.participants-section','.interactions-section','.clarifications-section','.stack-section','.report-section','.chain-preview','.sticky-submit'];
      const res=[];
      for(const sel of selectors){
        document.querySelectorAll(sel).forEach((el,i)=>{
          const cs=getComputedStyle(el);
          if(cs.display==='none'||cs.visibility==='hidden'||Number(cs.opacity)===0) return;
          const r=el.getBoundingClientRect();
          if(r.width<2||r.height<2) return;
          res.push({sel, i, x:r.left+scrollX, y:r.top+scrollY, w:r.width, h:r.height, pos:cs.position, z:cs.zIndex, text:(el.innerText||'').slice(0,60)});
        });
      }
      return res;
    }''')

def overlaps(rs):
    issues=[]
    # Only compare top-level layout blocks, not parent-child expected containment.
    # chain-preview/sticky/flowstage/panels must not geometrically overlap as siblings.
    for i in range(len(rs)):
        a=rs[i]
        for j in range(i+1,len(rs)):
            b=rs[j]
            # ignore guidebar/titleblock minor sticky top, and stage panel with hidden children impossible
            if a['sel'] in ['.titleblock','.guidebar'] and b['sel'] in ['.titleblock','.guidebar']: continue
            # ignore containment of children? selected selectors are mostly siblings, but sticky-submit can be inside preview? use text no
            x1=max(a['x'],b['x']); y1=max(a['y'],b['y']); x2=min(a['x']+a['w'],b['x']+b['w']); y2=min(a['y']+a['h'],b['y']+b['h'])
            if x2>x1 and y2>y1:
                area=(x2-x1)*(y2-y1)
                minarea=min(a['w']*a['h'], b['w']*b['h'])
                if area>200 and area/minarea>0.05:
                    # Accept when .chain-preview and .sticky-submit? sticky-submit should not overlap on mobile after fix.
                    issues.append((a,b,area/minarea))
    return issues

def horizontal_overflow(page):
    return page.evaluate('''() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth''')

def setup_stage(page, stage):
    if stage=='participants_empty':
        return
    add_participants(page)
    if stage=='participants_filled':
        return
    go_interactions(page)
    if stage=='interactions_empty':
        return
    add_demo_chain(page)
    if stage=='interactions_filled':
        return
    go_clarifications(page)
    if stage=='clarifications':
        return
    answer_clarifications(page)
    generate_stack(page)
    if stage=='stack_ready':
        return
    page.get_by_role('button', name='Проверить архитектуру').click(); page.wait_for_timeout(200)

stages=['participants_empty','participants_filled','interactions_empty','interactions_filled','clarifications','stack_ready']
results=[]
failures=[]
Path('layout_screens').mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=launch(p)
    for name,w,h in VIEWPORTS:
        for st in stages:
            page=browser.new_page(viewport={'width':w,'height':h})
            page.set_default_timeout(7000)
            page.set_content(html, wait_until='load')
            page.wait_for_timeout(250)
            try:
                setup_stage(page, st)
                # scroll to chain-builder and also to top positions for current stage
                page.locator('#chain-builder').scroll_into_view_if_needed(); page.wait_for_timeout(80)
                r=rects(page); ov=overlaps(r); overflow=horizontal_overflow(page)
                # screenshots disabled for speed
                status='OK'
                detail=f'overflow={overflow:.1f}, overlaps={len(ov)}, rects={len(r)}'
                if overflow>4:
                    status='FAIL'; failures.append((name,st,'horizontal_overflow',overflow))
                if ov:
                    status='FAIL'; failures.append((name,st,'overlap',[(a['sel'],b['sel'],round(frac,2)) for a,b,frac in ov[:5]]))
                results.append((status,name,st,detail))
            except Exception as e:
                results.append(('FAIL',name,st,str(e))); failures.append((name,st,'exception',str(e)))
            finally:
                page.close()
    browser.close()

lines=['# Проверка мобильной и адаптивной вёрстки v8.6.9','']
for status,name,st,detail in results:
    lines.append(f'- {status}: {name} / {st} — {detail}')
lines.append('')
lines.append(f'SUMMARY: {sum(1 for s,_,__,___ in results if s=="OK")} ok, {sum(1 for s,_,__,___ in results if s!="OK")} fail')
if failures:
    lines.append('')
    lines.append('FAILURES:')
    for f in failures[:50]: lines.append(f'- {f}')
Path('LAYOUT_RESPONSIVE_v8_6_9.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
if failures:
    raise SystemExit(1)
