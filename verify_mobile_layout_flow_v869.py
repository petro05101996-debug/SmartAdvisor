# -*- coding: utf-8 -*-
from pathlib import Path
import re, shutil
from playwright.sync_api import sync_playwright
import ui
html = ui.form_page().replace('</head>', '<script>window.fetch=async()=>new Response(JSON.stringify({ok:true,id:"x"}),{status:200,headers:{"Content-Type":"application/json"}});</script></head>')
VIEWPORTS=[('phone360',360,800),('phone390',390,844),('phone430',430,932),('tablet768',768,1024),('desktop1024',1024,768),('desktop1366',1366,900)]
results=[]

def launch(p):
    exe=shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    return p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])

def report(page, vp, stage):
    page.locator('#chain-builder').scroll_into_view_if_needed(); page.wait_for_timeout(40)
    data=page.evaluate('''() => {
      const overflow = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - window.innerWidth;
      const sels=['.flow-stage-panel','.participants-section','.interactions-section','.clarifications-section','.stack-section','.chain-preview'];
      const items=[];
      for(const sel of sels){
        document.querySelectorAll(sel).forEach(el=>{
          const cs=getComputedStyle(el); const r=el.getBoundingClientRect();
          if(cs.display==='none'||cs.visibility==='hidden'||r.width<2||r.height<2) return;
          items.push({sel,x:r.left+scrollX,y:r.top+scrollY,w:r.width,h:r.height});
        });
      }
      function overlap(a,b){
        const x1=Math.max(a.x,b.x), y1=Math.max(a.y,b.y), x2=Math.min(a.x+a.w,b.x+b.w), y2=Math.min(a.y+a.h,b.y+b.h);
        if(x2<=x1||y2<=y1) return 0;
        const area=(x2-x1)*(y2-y1); return area/Math.min(a.w*a.h,b.w*b.h);
      }
      const overlaps=[];
      for(let i=0;i<items.length;i++) for(let j=i+1;j<items.length;j++){
        const fr=overlap(items[i],items[j]);
        if(fr>0.03) overlaps.push([items[i].sel,items[j].sel,fr]);
      }
      return {overflow, overlaps, items};
    }''')
    status='OK'
    details=f"overflow={data['overflow']:.1f}, overlaps={len(data['overlaps'])}"
    if data['overflow']>4 or data['overlaps']:
        status='FAIL'; details += ' ' + str(data['overlaps'][:5])
    results.append((status, vp, stage, details))

def click_text(page, text):
    page.get_by_text(text, exact=False).first.click(); page.wait_for_timeout(30)

def add_chain(page):
    for text in ['Добавить инициатора','Добавить сервис процесса','Добавить внешнюю систему','Добавить хранилище состояния','Добавить аналитику','Добавить ручной разбор']:
        click_text(page, text)
    report(page, vp_name, 'participants')
    page.get_by_role('button', name=re.compile('Дальше: связи')).click(); page.wait_for_timeout(100)
    report(page, vp_name, 'interactions_empty')
    def add(src,tgt,act,timing,result,basis):
        page.select_option('#interactionSource', value=src)
        page.select_option('#interactionTarget', value=tgt)
        page.select_option('#interactionAction', value=act)
        page.select_option('#interactionTiming', value=timing)
        page.select_option('#interactionResult', value=result)
        page.select_option('#interactionBasis', label=basis)
        page.get_by_role('button', name='Добавить связь в цепочку').click(); page.wait_for_timeout(30)
    add('Система-инициатор','Сервис процесса','send_data','sync','pass_next','результат предыдущего взаимодействия')
    add('Сервис процесса','Внешняя система / партнёр','request_data','sync','save','после ответа внешней системы')
    add('Сервис процесса','Хранилище состояния процесса','save','sync','save','после сохранения состояния')
    add('Внешняя система / партнёр','Сервис процесса','wait_status','later','save','после позднего статуса')
    add('Хранилище состояния процесса','Аналитическое хранилище','compare','background','check','по расписанию или контрольной отметке')
    report(page, vp_name, 'interactions_filled')
    page.get_by_role('button', name=re.compile('Дальше: уточнения')).click(); page.wait_for_timeout(100)
    report(page, vp_name, 'clarifications')
    page.get_by_role('button', name='Определить стек по процессу').click(); page.wait_for_timeout(150)
    report(page, vp_name, 'stack')

with sync_playwright() as p:
    browser=launch(p)
    for vp_name,w,h in VIEWPORTS:
        page=browser.new_page(viewport={'width':w,'height':h})
        page.set_default_timeout(3500)
        page.set_content(html, wait_until='load')
        page.wait_for_timeout(150)
        try:
            report(page, vp_name, 'initial')
            add_chain(page)
        except Exception as e:
            results.append(('FAIL', vp_name, 'exception', repr(e)))
        finally:
            page.close()
    browser.close()

lines=['# Проверка отсутствия наложений v8.6.9','']
for r in results: lines.append(f'- {r[0]}: {r[1]} / {r[2]} — {r[3]}')
lines.append('')
lines.append(f"SUMMARY: {sum(1 for x in results if x[0]=='OK')} ok, {sum(1 for x in results if x[0]!='OK')} fail")
Path('LAYOUT_NO_OVERLAP_v8_6_9.md').write_text('\n'.join(lines), encoding='utf-8')
print('\n'.join(lines))
if any(x[0]!='OK' for x in results): raise SystemExit(1)
