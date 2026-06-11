# -*- coding: utf-8 -*-
"""Web-интерфейс v7.6: проводник по описанию интеграции и справочник инвариантов.

Ядро анализа осталось прежним: UI собирает тот же JSON, что и v6.4+.
Дополнительно интерфейс показывает каталог архитектурных инвариантов как
понятный справочник: что проверить, почему это важно и пример ошибки.
"""
from html import escape
from engine import SEVERITY_RU
from invariant_catalog import INVARIANT_CATALOG

STATUS_RU = {'ok': 'Проверено', 'warn': 'Требует проверки', 'unknown': 'Не указано', 'fail': 'Блокирует выпуск',
             'pass': 'Проходит'}

CSS = """
:root{
  --paper:#F4F6F5; --panel:#FFFFFF; --ink:#15211F; --muted:#5C6B68;
  --line:#D7DEDC; --accent:#155E66; --accent-soft:#E3EEEF;
  --critical:#B3361C; --high:#B87714; --medium:#857C2E; --info:#5C6B68;
  --good:#1E6E3C;
  --mono:ui-monospace,'JetBrains Mono','Cascadia Mono',Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);font:15px/1.55 var(--sans);background:var(--paper);
  background-image:linear-gradient(var(--line) 1px,transparent 1px),linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:28px 28px;}
.wrap{max-width:1120px;margin:0 auto;padding:20px 16px 72px}
.titleblock{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;border:2px solid var(--ink);background:var(--panel);padding:14px 18px;margin-bottom:18px}
.titleblock h1{margin:0;font:700 19px/1.2 var(--mono);letter-spacing:.06em;text-transform:uppercase}
.titleblock .meta{font:11px/1.5 var(--mono);color:var(--muted);text-align:right;letter-spacing:.05em}
.hero{background:var(--panel);border:1px solid var(--line);border-left:6px solid var(--accent);padding:16px 18px;margin-bottom:18px}
.hero h2{margin:0 0 6px;font-size:20px}.hero p{margin:6px 0;color:var(--muted)}
.steps3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}.stepbox{border:1px solid var(--line);background:#FCFDFD;padding:10px 12px}.stepbox b{font-family:var(--mono);font-size:12px;color:var(--accent)}
.card{background:var(--panel);border:1px solid var(--line);border-top:3px solid var(--accent);padding:18px 20px;margin-bottom:18px}
.card h2{margin:0 0 12px;font:700 13px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
details.card{padding:0}details.card>summary{display:flex;align-items:center;justify-content:space-between;gap:10px;cursor:pointer;padding:16px 20px;list-style:none}details.card>summary::-webkit-details-marker{display:none}details.card>summary h2{margin:0}details.card>summary:after{content:'развернуть';font:11px var(--mono);color:var(--muted)}details.card[open]>summary:after{content:'свернуть'}details.card>.inside{padding:0 20px 18px}
label{display:block;font:11px var(--mono);letter-spacing:.06em;color:var(--muted);margin:10px 0 3px;text-transform:uppercase}
input,select,textarea{width:100%;padding:8px 9px;border:1px solid var(--line);border-radius:0;font:14px var(--sans);background:#FCFDFD;color:var(--ink)}
textarea{font-family:var(--mono);font-size:13px;min-height:64px}input:focus,select:focus,textarea:focus{outline:2px solid var(--accent);outline-offset:-1px}
.grid{display:grid;gap:0 16px}.g2{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(3,1fr)}.g4{grid-template-columns:repeat(4,1fr)}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.toolbar .spacer{flex:1}.mode{display:inline-flex;border:1px solid var(--ink)}.mode button{border:0;border-right:1px solid var(--ink);background:#fff;color:var(--ink);padding:8px 12px;font:700 12px var(--mono);cursor:pointer}.mode button:last-child{border-right:0}.mode button.active{background:var(--ink);color:#fff}
.scenarios{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.scenario{border:1px solid var(--line);background:#FCFDFD;padding:12px;text-align:left;cursor:pointer}.scenario:hover{border-color:var(--accent);background:var(--accent-soft)}.scenario b{display:block;margin-bottom:4px}.scenario span{font-size:12.5px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}th{font:10px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);text-align:left;padding:6px 6px;border-bottom:2px solid var(--ink)}td{padding:5px 4px;border-bottom:1px solid var(--line);vertical-align:top}td input,td select{padding:6px 6px;font-size:13px}
.btn{display:inline-block;border:2px solid var(--ink);background:var(--ink);color:#fff;font:700 13px var(--mono);letter-spacing:.08em;text-transform:uppercase;padding:11px 22px;cursor:pointer;text-decoration:none}.btn:hover{background:var(--accent);border-color:var(--accent)}.btn.ghost{background:transparent;color:var(--ink);font-weight:600;padding:7px 12px;border-width:1px}.btn.ghost:hover{color:var(--accent);border-color:var(--accent);background:var(--accent-soft)}.btn:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.progress{height:10px;background:#E7ECEB;border:1px solid var(--line);margin:8px 0 4px}.progress i{display:block;height:100%;width:0;background:var(--accent)}
.rail{display:flex;flex-wrap:wrap;align-items:center;gap:0;padding:14px 6px;min-height:58px}.rail .chip{border:1.5px solid var(--ink);background:var(--panel);padding:6px 10px;font:12px var(--mono);max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.rail .chip small{display:block;color:var(--muted);font-size:10px;letter-spacing:.05em}.rail .link{width:34px;border-top:2px solid var(--ink);position:relative;flex:none}.rail .link.async{border-top-style:dashed;border-top-color:var(--muted)}.rail .link::after{content:'';position:absolute;right:-1px;top:-4px;border:3px solid transparent;border-left:6px solid var(--ink)}.rail .link.async::after{border-left-color:var(--muted)}.rail:empty::before{content:'Шаги появятся здесь по мере добавления';color:var(--muted);font:12px var(--mono)}
.hint{font-size:12.5px;color:var(--muted);margin:4px 0 0}.err{border:2px solid var(--critical);color:var(--critical);background:#FBEEE9;padding:10px 14px;margin:10px 0;font:13px var(--mono)}a{color:var(--accent)}
.quick-mode .advanced-only{display:none!important}.quick-note{display:none}.quick-mode .quick-note{display:block}.advanced-note{display:block}.quick-mode .advanced-note{display:none}
.badge{font:10px var(--mono);letter-spacing:.05em;padding:1px 6px;border:1px solid currentColor}.b-critical{color:var(--critical)}.b-high{color:var(--high)}.b-medium{color:var(--medium)}.b-info{color:var(--info)}
.verdict{border:2px solid var(--ink);padding:16px 20px;margin-bottom:18px;background:var(--panel)}.verdict.green{border-color:var(--good);box-shadow:inset 6px 0 0 var(--good)}.verdict.yellow{border-color:var(--high);box-shadow:inset 6px 0 0 var(--high)}.verdict.red{border-color:var(--critical);box-shadow:inset 6px 0 0 var(--critical)}.verdict h2{margin:0;font:700 16px var(--mono);letter-spacing:.04em}.verdict p{margin:6px 0 0;color:var(--muted);font:12px var(--mono)}
.finding{border:1px solid var(--line);border-left:4px solid var(--info);padding:12px 14px;margin:0 0 10px;background:#FCFDFD}.finding.critical{border-left-color:var(--critical)}.finding.high{border-left-color:var(--high)}.finding.medium{border-left-color:var(--medium)}.finding h3{margin:0 0 2px;font-size:14.5px}.finding .where{font:11px var(--mono);color:var(--muted)}.finding p{margin:7px 0 0;font-size:13.5px}
pre{background:#10201E;color:#D9E6E3;padding:14px;overflow:auto;font:12.5px var(--mono);margin:8px 0}.mermaid{background:#FCFDFD;border:1px solid var(--line);padding:8px;margin:8px 0;overflow:auto}ol.tests{padding-left:20px;font-size:13.5px}ol.tests li{margin:5px 0}.pat{margin:0 0 12px}.pat b{font-family:var(--mono)}.pat .ctl{font:12px var(--mono);color:var(--muted)}
.gates{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.gate{border:1px solid var(--line);padding:10px 12px;background:#FCFDFD}.gate.fail{border-left:4px solid var(--critical)}.gate.warn{border-left:4px solid var(--high)}.gate.pass{border-left:4px solid var(--good)}.gate b{font-family:var(--mono);font-size:12px}.gate p{margin:6px 0 0;font-size:12.5px;color:var(--muted)}
.check{width:100%;border-collapse:collapse}.check td,.check th{font-size:12.5px;padding:7px;border-bottom:1px solid var(--line)}.st{font:10px var(--mono);letter-spacing:.05em;padding:2px 6px;border:1px solid currentColor;white-space:nowrap}.st.ok,.st.pass{color:var(--good)}.st.warn,.st.unknown{color:var(--high)}.st.fail{color:var(--critical)}
.alt{border:1px solid var(--line);padding:12px 14px;margin:0 0 10px;background:#FCFDFD}.alt h3{margin:0;font-size:14px}.alt p{margin:6px 0;font-size:13px}.alt ul{margin:6px 0 0 18px;padding:0;font-size:13px}.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}.actions{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.action{border:1px solid var(--line);background:#FCFDFD;padding:10px 12px}.action b{font-family:var(--mono);font-size:12px}.flowbox{border:1px solid var(--line);background:#FCFDFD;padding:10px 12px;margin:0 0 10px}.flowbox h3{margin:0 0 5px;font-size:14px}.flowbox ul{margin:6px 0 0 18px;padding:0}.flowbox li{margin:3px 0}.flowbox .meta{font:11px var(--mono);color:var(--muted)}

.navlinks{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.navlinks a{display:inline-block;border:1px solid var(--ink);padding:8px 10px;background:#fff;color:var(--ink);text-decoration:none;font:12px var(--mono);text-transform:uppercase;letter-spacing:.05em}
.refbar{display:grid;grid-template-columns:1fr 260px;gap:12px;margin:12px 0}
.refcard{border:1px solid var(--line);background:#fff;padding:14px;margin:10px 0}
.refcard h3{margin:0 0 8px;font:700 17px/1.3 var(--sans)}
.refcode{display:inline-block;font:11px var(--mono);border:1px solid var(--line);padding:2px 6px;margin-right:8px;background:#F4F6F7;color:var(--muted)}
.refarea{font:11px var(--mono);text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.refgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.refbox{background:#F8FAFA;border:1px solid var(--line);padding:10px}
.refbox b{display:block;margin-bottom:5px}
.reflead{border-left:4px solid var(--accent);background:#F6FBFA;margin:10px 0}.okbox{border-left:4px solid var(--good);background:#F7FBF8;margin-top:10px}
.refexample{border-left:4px solid var(--ink);background:#FBFCFC;padding:10px;margin-top:10px}.refexample.light{border-left-color:var(--high);background:#FFFDF8}.dangerbox{border-left:4px solid var(--critical);background:#FFF7F7;margin-top:10px}
.refempty{display:none;border:1px dashed var(--line);padding:16px;background:#fff}
@media(max-width:760px){.refbar,.refgrid{grid-template-columns:1fr}.navlinks a{width:100%}}

@media(max-width:860px){.g3,.g4,.scenarios,.steps3,.actions,.minimal{grid-template-columns:1fr 1fr}.wrap{padding:12px 8px}.card{padding:14px 12px}.titleblock{display:block}.titleblock .meta{text-align:left;margin-top:8px}}
.help{border-left:3px solid var(--accent);background:#F7FAFA;padding:8px 10px;margin:6px 0 10px;font-size:12.5px;color:var(--muted)}
.help b{color:var(--ink)}
.fieldtip{font-size:12px;color:var(--muted);margin:3px 0 0}
#steps{border-collapse:separate;border-spacing:0 10px}
#steps thead{display:none}
#steps tbody tr{display:grid;grid-template-columns:52px minmax(220px,1.7fr) minmax(150px,1fr) 128px 120px 82px minmax(110px,.8fr) minmax(135px,.9fr) 120px 80px minmax(220px,1.4fr) 42px;gap:8px;align-items:end;border:1px solid var(--line);background:#FCFDFD;padding:10px;margin-bottom:10px}
#steps td{border:0;padding:0}
#steps td:before{content:attr(data-label);display:block;font:10px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:3px}
.resultnav{position:sticky;top:0;z-index:3;background:rgba(244,246,245,.96);backdrop-filter:blur(4px);border:1px solid var(--line);padding:8px;margin:0 0 14px;display:flex;gap:6px;flex-wrap:wrap}
.resultnav a{border:1px solid var(--line);background:#fff;color:var(--ink);padding:8px 10px;font:700 11px var(--mono);text-transform:uppercase;letter-spacing:.04em;text-decoration:none}.resultnav a:hover{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.jumpfix{display:inline-block;margin-top:8px;border:1px solid var(--line);padding:5px 8px;background:#fff;font:11px var(--mono);text-decoration:none;color:var(--accent)}
.top10{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.top10 .refbox{background:#FCFDFD}
.guidebar{position:sticky;top:0;z-index:4;background:rgba(244,246,245,.97);backdrop-filter:blur(4px);border:1px solid var(--line);padding:8px;margin:0 0 14px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.guidebar a{border:1px solid var(--line);background:#fff;color:var(--ink);padding:8px 10px;font:700 11px var(--mono);text-transform:uppercase;letter-spacing:.04em;text-decoration:none}.guidebar a:hover{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.guidebar .guide-title{font:700 11px var(--mono);color:var(--muted);margin-right:4px;text-transform:uppercase;letter-spacing:.06em}
.assist{border:1px solid var(--line);background:#FBFDFD;padding:12px 14px;margin-top:10px}.assist b{font-family:var(--mono);font-size:12px;color:var(--accent)}
.assist ul{margin:8px 0 0 18px;padding:0}.assist li{margin:3px 0}.assist.ok{border-left:4px solid var(--good)}.assist.warn{border-left:4px solid var(--high)}
.templatebar{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 12px}.templatebar .btn{letter-spacing:.03em;text-transform:none;font-size:12px;padding:8px 10px}
.process-layout{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:14px;align-items:start}.sidepanel{position:sticky;top:62px;border:1px solid var(--line);background:#FCFDFD;padding:12px}.sidepanel h3{margin:0 0 8px;font:700 12px var(--mono);text-transform:uppercase;letter-spacing:.08em;color:var(--accent)}.sidepanel p{margin:6px 0;color:var(--muted);font-size:12.5px}.sidepanel ul{margin:8px 0 0 18px;padding:0;font-size:12.5px}.sidepanel li{margin:4px 0}
.row-actions{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}.row-actions button{border:1px solid var(--line);background:#fff;color:var(--ink);padding:5px 7px;font:700 11px var(--mono);cursor:pointer}.row-actions button:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}
.reviewbox{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.reviewbox .metric{border:1px solid var(--line);background:#FCFDFD;padding:10px}.reviewbox .metric b{display:block;font:700 18px var(--mono);color:var(--accent)}.reviewbox .metric span{font-size:12px;color:var(--muted)}
.minimal{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.minimal .mini{border:1px solid var(--line);background:#fff;padding:8px 10px}.minimal .mini b{display:block;font:700 11px var(--mono);color:var(--accent);margin-bottom:3px}.minimal .mini span{font-size:12px;color:var(--muted)}
@media(max-width:900px){#steps tbody tr{grid-template-columns:1fr 1fr}.resultnav,.guidebar{position:static}.top10,.process-layout,.reviewbox,.minimal{grid-template-columns:1fr}.sidepanel{position:static}}

@media(max-width:640px){.guidebar a{width:100%}.process-layout,.reviewbox,.minimal{grid-template-columns:1fr}#steps tbody tr{display:block}#steps td{display:grid;grid-template-columns:128px 1fr;gap:8px;align-items:center;padding:5px 0}.g2,.g3,.g4,.gates,.two,.scenarios,.steps3,.actions{grid-template-columns:1fr}.toolbar{display:block}.toolbar>*{margin:6px 0}.mode{display:flex}.mode button{flex:1}.card{padding:12px}.titleblock h1{font-size:16px}table,thead,tbody,tr,td,th{display:block;width:100%}thead{display:none}tr{border:1px solid var(--line);background:#FCFDFD;margin:10px 0;padding:8px}td{border:0;display:grid;grid-template-columns:128px 1fr;gap:8px;align-items:center;padding:5px 0}td:before{content:attr(data-label);font:10px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}td:last-child{display:block;text-align:right}.check{display:table}.check thead{display:table-header-group}.check tbody{display:table-row-group}.check tr{display:table-row;border:0;background:transparent;margin:0;padding:0}.check td,.check th{display:table-cell}.check td:before{content:none}}
"""

FORM_JS = r"""
const CH=[['rest','REST / HTTP'],['grpc','gRPC'],['soap','SOAP'],['db','Прямой доступ к БД'],['kafka','Kafka'],['queue','Очередь'],['webhook','Webhook'],['callback','Callback'],['file','Файл'],['batch','Batch'],['cdc','CDC']];
const ROLES=[['internal','Внутренний сервис'],['external','Внешняя система'],['broker','Брокер сообщений'],['db','База данных'],['legacy','Legacy-система'],['analytics','Аналитический контур']];
const CRIT=[['low','Низкая'],['medium','Средняя'],['high','Высокая'],['critical','Критичная']];
const STAB=[['unknown','Не указано'],['stable','Стабильная'],['unstable','Нестабильная'],['limited','Есть лимиты']];
const RETRY=[['none','Не повторяем'],['auto','Автоматически'],['manual','Вручную']];
const IDEM=[['none','Не указана'],['key','По idempotency key'],['natural','По бизнес-ключу']];
const YESNO=[['no','Нет'],['yes','Да']];
const SYNC=new Set(['rest','grpc','soap','db']);
let n=0;
function optPairs(list,sel){return list.map(x=>`<option value="${x[0]}" ${x[0]===sel?'selected':''}>${x[1]}</option>`).join('')}
function setCellLabels(tr, labels){[...tr.children].forEach((td,i)=>td.setAttribute('data-label',labels[i]||''))}
function addStep(p={}){
  n++;
  const tb=document.querySelector('#steps tbody');
  const tr=document.createElement('tr');
  tr.innerHTML=`
   <td style="width:46px"><input name="order" value="${p.order||n}" inputmode="numeric"></td>
   <td><input name="name" placeholder="Например: создать заявку" value="${p.name||''}"></td>
   <td><input name="system" list="syslist" placeholder="Например: сервис заявок" value="${p.system||''}"></td>
   <td style="width:130px"><select name="channel">${optPairs(CH,p.channel||'rest')}</select></td>
   <td style="width:120px"><select name="blocking"><option value="yes" ${p.blocking!=='no'?'selected':''}>Ждёт ответа</option><option value="no" ${p.blocking==='no'?'selected':''}>Не ждёт</option></select></td>
   <td style="width:86px"><input name="timeout_ms" placeholder="500" value="${p.timeout_ms||''}" inputmode="numeric"></td>
   <td style="width:120px" class="advanced-only"><select name="retry">${optPairs(RETRY,p.retry||'none')}</select></td>
   <td style="width:150px" class="advanced-only"><select name="idempotency">${optPairs(IDEM,p.idempotency||'none')}</select></td>
   <td style="width:130px"><select name="writes_entity">${optPairs(YESNO,p.writes_entity||'no')}</select></td>
   <td style="width:80px" class="advanced-only"><input name="depends_on" placeholder="1 или 1,2" value="${p.depends_on||''}" inputmode="numeric"></td>
   <td class="advanced-only"><input name="compensation" placeholder="Например: DLQ после 5 попыток, replay, компенсация" value="${p.compensation||''}"></td>
   <td class="row-actions"><button type="button" title="Выше" onclick="moveStep(this,-1)">↑</button><button type="button" title="Ниже" onclick="moveStep(this,1)">↓</button><button type="button" title="Копировать шаг" onclick="duplicateStep(this)">⧉</button><button type="button" class="safe-btn" title="Подставить безопасные настройки для канала" onclick="applySafeDefaults(this)">✓</button><button type="button" aria-label="Удалить шаг" onclick="this.closest('tr').remove();renumberSteps()">×</button></td>`;
  tb.appendChild(tr);
  setCellLabels(tr,['№','Что происходит','Кто выполняет','Канал','Следующий шаг','Timeout, мс','Повтор при ошибке','Идемпотентность','Меняет сущность','После шага','Восстановление','Действия']);
  tr.querySelectorAll('input,select').forEach(e=>{e.addEventListener('input',()=>{rail();updateProgress()});e.addEventListener('change',()=>{rail();updateProgress()})});
  rail();updateProgress();
}
function addSystem(p={}){
  const tb=document.querySelector('#systems tbody');
  const tr=document.createElement('tr');
  tr.innerHTML=`
   <td><input name="sname" placeholder="Например: CRM" value="${p.name||''}"></td>
   <td><select name="srole">${optPairs(ROLES,p.role||'internal')}</select></td>
   <td><input name="sowner" placeholder="Например: команда CRM" value="${p.owner||''}"></td>
   <td class="advanced-only"><select name="scrit">${optPairs(CRIT,p.crit||'medium')}</select></td>
   <td class="advanced-only"><select name="sstab">${optPairs(STAB,p.stab||'unknown')}</select></td>
   <td style="width:100px" class="advanced-only"><input name="slimit" placeholder="100" value="${p.limit||''}" inputmode="numeric"></td>
   <td style="width:40px"><button type="button" class="btn ghost" aria-label="Удалить систему" onclick="this.closest('tr').remove();syncSys();updateProgress()">×</button></td>`;
  tb.appendChild(tr);
  setCellLabels(tr,['Система','Роль','Владелец','Критичность','Стабильность','RPS-лимит','']);
  tr.querySelector('[name=sname]').addEventListener('input',()=>{syncSys();updateProgress()});
  tr.querySelectorAll('select,input').forEach(e=>{e.addEventListener('input',updateProgress);e.addEventListener('change',updateProgress)});
  syncSys();updateProgress();
}
function syncSys(){
  const dl=document.getElementById('syslist');
  dl.innerHTML=[...document.querySelectorAll('#systems [name=sname]')].map(i=>`<option value="${esc(i.value)}">`).join('');
}
function rows(sel){return [...document.querySelectorAll(sel+' tbody tr')].map(tr=>{const o={};tr.querySelectorAll('input,select').forEach(e=>{if(e.name)o[e.name]=e.value});return o})}
function rail(){
  const r=document.getElementById('rail'); if(!r)return; r.innerHTML='';
  const steps=rows('#steps').filter(s=>s.name&&s.name.trim()).sort((a,b)=>(+a.order||0)-(+b.order||0));
  steps.forEach((s,i)=>{if(i>0){const l=document.createElement('span');l.className='link'+(s.blocking==='no'||!SYNC.has(s.channel)?' async':'');r.appendChild(l);}const c=document.createElement('span');c.className='chip';c.innerHTML=`${s.order}. ${esc(s.name)}<small>${esc(s.system||'—')} · ${labelOf(CH,s.channel)}${s.blocking==='no'?' · async':''}</small>`;r.appendChild(c);});
}
function labelOf(list,val){const x=list.find(i=>i[0]===val);return x?x[1]:val}
function esc(s){const d=document.createElement('i');d.textContent=s||'';return d.innerHTML}
function v(id){return document.getElementById(id).value}
function setv(id,val){document.getElementById(id).value=val}
function updateProgress(){
  const essentials=[v('p_name'),v('p_entity'),v('p_goal'),v('p_statuses'),v('p_fields'),v('p_lookup')];
  const sys=rows('#systems').filter(s=>s.sname).length;
  const steps=rows('#steps').filter(s=>s.name&&s.system).length;
  let done=essentials.filter(Boolean).length + Math.min(sys,2) + Math.min(steps,3);
  const total=11; const pct=Math.min(100,Math.round(done/total*100));
  const bar=document.querySelector('#fillbar i'); if(bar)bar.style.width=pct+'%';
  const text=document.getElementById('filltext'); if(text)text.textContent=pct<50?'Заполните сценарий, сущность, системы и первые шаги.':pct<80?'Уже достаточно для первичного разбора. Для качества добавьте статусы, поля и восстановление.':'Вводные выглядят достаточно полными для полезного архитектурного разбора.';
  updateGuidance();updateReview();
}
function setMode(mode){
  document.body.classList.toggle('quick-mode',mode==='quick');
  document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
}
function clearAll(){document.querySelector('#systems tbody').innerHTML='';document.querySelector('#steps tbody').innerHTML='';n=0;}

function renumberSteps(){
  [...document.querySelectorAll('#steps tbody tr')].forEach((tr,i)=>{const inp=tr.querySelector('[name=order]'); if(inp) inp.value=i+1;});
  rail();updateProgress();
}
function moveStep(btn,dir){
  const tr=btn.closest('tr');
  if(!tr)return;
  if(dir<0 && tr.previousElementSibling) tr.parentNode.insertBefore(tr,tr.previousElementSibling);
  if(dir>0 && tr.nextElementSibling) tr.parentNode.insertBefore(tr.nextElementSibling,tr);
  renumberSteps();
}
function duplicateStep(btn){
  const tr=btn.closest('tr'); if(!tr)return;
  const data={}; tr.querySelectorAll('input,select').forEach(e=>{data[e.name]=e.value});
  data.order=(+data.order||n)+1; data.name=(data.name||'Шаг')+' — копия';
  addStep(data); renumberSteps();
}
function safeDefaultsFor(channel){
  if(['rest','grpc','soap'].includes(channel)) return {retry:'auto',idempotency:'key',compensation:'timeout, circuit breaker, fallback, ограниченный retry с backoff'};
  if(['kafka','queue'].includes(channel)) return {retry:'auto',idempotency:'key',compensation:'retry с backoff, DLQ, replay, контроль offset/ack'};
  if(['webhook','callback'].includes(channel)) return {retry:'auto',idempotency:'key',compensation:'проверка подписи, timestamp/nonce, Inbox-дедупликация, повтор callback'};
  if(channel==='db') return {retry:'none',idempotency:'natural',compensation:'транзакция, UNIQUE constraint, optimistic locking'};
  if(['file','batch'].includes(channel)) return {retry:'manual',idempotency:'natural',compensation:'batchId, checksum, quarantine, reprocess'};
  if(channel==='cdc') return {retry:'auto',idempotency:'natural',compensation:'offset/LSN, watermark, replay/resync'};
  return {retry:'none',idempotency:'none',compensation:''};
}
function applySafeDefaults(btn){
  const tr=btn.closest('tr'); if(!tr)return;
  const ch=tr.querySelector('[name=channel]').value;
  const d=safeDefaultsFor(ch);
  tr.querySelector('[name=retry]').value=d.retry;
  tr.querySelector('[name=idempotency]').value=d.idempotency;
  const comp=tr.querySelector('[name=compensation]'); if(!comp.value) comp.value=d.compensation;
  if(SYNC.has(ch) && !tr.querySelector('[name=timeout_ms]').value) tr.querySelector('[name=timeout_ms]').value='500';
  updateProgress();
}
function applySafeDefaultsAll(){
  document.querySelectorAll('#steps tbody tr').forEach(tr=>applySafeDefaults(tr.querySelector('.safe-btn')||tr));
}
function addTemplate(kind){
  const base=rows('#steps').length+1;
  if(kind==='rest') addStep({order:base,name:'Вызвать внешний или внутренний API',system:'',channel:'rest',blocking:'yes',timeout_ms:500,retry:'auto',idempotency:'key',compensation:'timeout, circuit breaker, fallback'});
  if(kind==='kafka') addStep({order:base,name:'Опубликовать или обработать событие Kafka',system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'DLQ, replay, контроль offset/ack'});
  if(kind==='db') addStep({order:base,name:'Записать или обновить состояние в БД',system:'',channel:'db',blocking:'yes',timeout_ms:200,retry:'none',idempotency:'natural',writes_entity:'yes',compensation:'транзакция, UNIQUE constraint, optimistic locking'});
  if(kind==='webhook') addStep({order:base,name:'Принять webhook или callback от внешней системы',system:'',channel:'webhook',blocking:'no',retry:'auto',idempotency:'key',compensation:'подпись, timestamp/nonce, Inbox-дедупликация'});
  if(kind==='batch') addStep({order:base,name:'Передать или обработать пакет данных',system:'',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',compensation:'batchId, checksum, quarantine, reprocess'});
}
function suggestBasics(){
  if(!v('p_statuses')) setv('p_statuses','CREATED, PROCESSING, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW');
  if(!v('p_fields')) setv('p_fields','requestId:string|required|unique, correlationId:uuid|required|indexed, status:string|required, createdAt:datetime|required, updatedAt:datetime|required');
  if(!v('p_lookup')) setv('p_lookup','requestId + operationType + targetSystem; eventId для дедупликации событий');
  updateProgress();
}
function updateReview(){
  const box=document.getElementById('reviewBox'); if(!box)return;
  const sys=rows('#systems').filter(s=>s.sname).length;
  const steps=rows('#steps').filter(s=>s.name).length;
  const async=rows('#steps').filter(s=>['kafka','queue','webhook','callback','batch','cdc'].includes(s.channel)).length;
  box.innerHTML=`<div class="metric"><b>${sys}</b><span>систем участвует</span></div><div class="metric"><b>${steps}</b><span>шагов описано</span></div><div class="metric"><b>${async}</b><span>асинхронных границ</span></div>`;
}
function updateGuidance(){
  const g=document.getElementById('liveGuide'); if(!g)return;
  const issues=[];
  if(!v('p_name')) issues.push('Назовите процесс так, чтобы его понял бизнес и разработка.');
  if(!v('p_entity')) issues.push('Укажите основную сущность: заявка, документ, договор, платёж или операция.');
  if(!v('p_goal')) issues.push('Опишите бизнес-цель процесса одним предложением.');
  if(!v('p_lookup')) issues.push('Заполните ключ поиска/дедупликации. Для общих сервисов проверьте scope: requestId + operationType + targetSystem.');
  if(!v('p_statuses')) issues.push('Добавьте статусы процесса и финальные состояния.');
  if(rows('#systems').filter(s=>s.sname).length<2) issues.push('Добавьте минимум две системы-участника.');
  if(rows('#steps').filter(s=>s.name&&s.system).length<2) issues.push('Добавьте цепочку хотя бы из двух шагов.');
  const noRecovery=rows('#steps').filter(s=>s.name && !s.compensation && ['kafka','queue','webhook','callback','batch','cdc'].includes(s.channel)).length;
  if(noRecovery) issues.push(`У ${noRecovery} асинхронных шагов не описано восстановление: DLQ, replay, Inbox или reprocess.`);
  if(!issues.length){g.className='assist ok';g.innerHTML='<b>Вводные выглядят хорошо.</b><p>Можно запускать разбор. Для максимального качества проверьте расширенный режим: зависимости, retry, идемпотентность и компенсации.</p>';return;}
  g.className='assist warn';g.innerHTML='<b>Что ещё заполнить, чтобы разбор был полезнее:</b><ul>'+issues.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>';
}
function applyScenario(kind){
  clearAll();
  setv('p_name','');setv('p_entity','');setv('p_goal','');setv('p_description','');setv('p_lookup','');setv('p_constraints','');setv('p_sla','');setv('p_statuses','');setv('p_fields','');setv('p_visible','no');setv('p_money','no');setv('p_reg','no');setv('p_order','no');setv('p_rps','');setv('p_peak','1');setv('p_tenant','no');setv('p_legacy','no');setv('p_read','medium');
  if(kind==='reverse'){
    setv('p_name','Обратный поток статусов между банком и УК');setv('p_entity','ApplicationStatus');setv('p_goal','Банк передаёт документы в УК и получает обратно понятные статусы обработки документов и операций.');setv('p_visible','mixed');setv('p_money','direct');setv('p_reg','yes');setv('p_order','per_entity');setv('p_sla','');setv('p_statuses','CREATED, SENT_TO_UK, RECEIVED_BY_UK, PROCESSING, COMPLETED, REJECTED, ERROR');setv('p_fields','applicationId:uuid|required|indexed, documentId:string|required, operationId:string, status:string|required, eventId:uuid|required|unique, correlationId:uuid|required|indexed, occurredAt:datetime|required');setv('p_lookup','applicationId + documentId или operationId, eventId для дедупликации');setv('p_description','Банк передаёт документы и операции в УК. УК должна вернуть обратный поток статусов, чтобы банк видел финал обработки и мог расследовать зависшие заявки.');
    [['Банк','internal','Команда банка','critical','stable'],['УК','external','Управляющая компания','critical','limited'],['Kafka','broker','Платформа','high','stable'],['БД банка','db','Команда банка','critical','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4]}));
    [{order:1,name:'Банк создаёт заявку и документы',system:'Банк',channel:'rest',timeout_ms:300,idempotency:'key',writes_entity:'yes'},
     {order:2,name:'Банк передаёт документы в УК',system:'УК',channel:'rest',timeout_ms:2000,retry:'auto',idempotency:'key',depends_on:1,compensation:'timeout, повтор с тем же idempotencyKey'},
     {order:3,name:'УК публикует статус документа',system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:2,compensation:'outbox, DLQ, replay'},
     {order:4,name:'Банк принимает статус и обновляет историю',system:'БД банка',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',writes_entity:'yes',depends_on:3,compensation:'inbox-дедупликация'}].forEach(addStep);
  } else if(kind==='kafka'){
    setv('p_name','Публикация событий об изменении договора');setv('p_entity','Contract');setv('p_goal','Исходный сервис публикует изменения договора, а потребители получают их через Kafka без потери и дублей.');setv('p_order','per_entity');setv('p_statuses','CHANGED, CANCELLED, ERROR');setv('p_fields','contractId:uuid|required|indexed, eventId:uuid|required|unique, eventVersion:string|required, correlationId:uuid|required|indexed, occurredAt:datetime|required');setv('p_lookup','contractId для порядка по сущности, eventId для дедупликации');setv('p_description','Исходный сервис меняет договор, публикует событие, а несколько потребителей обрабатывают его независимо.');
    [['Сервис договоров','internal','Команда договоров','critical','stable'],['Kafka','broker','Платформа','high','stable'],['Потребитель','internal','Команда потребителя','medium','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4]}));
    [{order:1,name:'Сервис договоров сохраняет изменение',system:'Сервис договоров',channel:'db',timeout_ms:200,writes_entity:'yes',idempotency:'natural'},
     {order:2,name:'Сервис договоров публикует событие',system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:1,compensation:'transactional outbox, DLQ, replay'},
     {order:3,name:'Потребитель обрабатывает событие',system:'Потребитель',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:2,compensation:'inbox-дедупликация'}].forEach(addStep);
  } else if(kind==='enrichment'){
    setv('p_name','Обогащение события через внешний REST-сервис');setv('p_entity','EnrichedEvent');setv('p_goal','Событие из Kafka нужно дополнить данными внешнего сервиса и передать дальше без блокировки основного потока.');setv('p_visible','no');setv('p_order','per_entity');setv('p_statuses','RECEIVED, ENRICHED, SENT, ERROR');setv('p_fields','sourceEventId:uuid|required|unique, aggregateId:string|required|indexed, enrichmentStatus:string|required, correlationId:uuid|required|indexed');setv('p_lookup','sourceEventId для дедупликации, aggregateId для порядка');setv('p_description','Событие нужно дообогатить через REST-зависимость. Основной поток не должен зависеть от долгого ответа внешнего сервиса.');
    [['Kafka','broker','Платформа','high','stable'],['Сервис обогащения','internal','Команда интеграций','high','stable'],['Внешний справочник','external','Партнёр','high','limited'],['Выходной топик','broker','Платформа','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4]}));
    [{order:1,name:'Сервис обогащения читает исходное событие',system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key'},
     {order:2,name:'Сервис обогащения вызывает внешний справочник',system:'Внешний справочник',channel:'rest',timeout_ms:1000,retry:'auto',idempotency:'natural',depends_on:1,compensation:'circuit breaker, fallback, DLQ'},
     {order:3,name:'Сервис публикует обогащённое событие',system:'Выходной топик',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:2,compensation:'outbox, DLQ, replay'}].forEach(addStep);
  } else if(kind==='dwh'){
    setv('p_name','Передача данных в DWH через CDC');setv('p_entity','OperationalData');setv('p_goal','Операционные данные должны попадать в аналитический контур без чтения из продовой БД в core-flow.');setv('p_read','very_high');setv('p_statuses','CAPTURED, DELIVERED, FAILED');setv('p_fields','recordId:uuid|required|indexed, changedAt:datetime|required|indexed, sourceSystem:string|required');setv('p_lookup','recordId + sourceSystem, changedAt для инкрементальной сверки');setv('p_description','Операционные данные выгружаются в DWH через CDC/ETL. Аналитический контур не должен блокировать основной бизнес-процесс.');
    [['OLTP БД','db','Команда продукта','critical','stable'],['CDC-пайплайн','internal','Платформа данных','high','stable'],['DWH','analytics','Команда данных','medium','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4]}));
    [{order:1,name:'Бизнес-сервис пишет данные в OLTP БД',system:'OLTP БД',channel:'db',timeout_ms:200,writes_entity:'yes',idempotency:'natural'},
     {order:2,name:'CDC-пайплайн забирает изменения',system:'CDC-пайплайн',channel:'cdc',blocking:'no',retry:'auto',idempotency:'natural',depends_on:1,compensation:'повтор чтения, контроль lag'},
     {order:3,name:'DWH принимает данные и строит витрину',system:'DWH',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',depends_on:2,compensation:'reconciliation-сверка'}].forEach(addStep);
  } else if(kind==='highload'){
    setv('p_name','Highload consumer из Kafka в Postgres');setv('p_entity','FilteredEvent');setv('p_goal','Консьюмеры читают общий топик, фильтруют события и сохраняют только нужные записи в Postgres.');setv('p_rps','5000');setv('p_peak','5');setv('p_order','per_entity');setv('p_statuses','RECEIVED, STORED, SKIPPED, FAILED');setv('p_fields','eventId:uuid|required|unique, aggregateId:string|required|indexed, eventType:string|required, receivedAt:datetime|required');setv('p_lookup','eventId для дедупликации, aggregateId + eventType для бизнес-поиска');setv('p_description','Консьюмер читает общий топик, фильтрует только нужные события и сохраняет результат в Postgres. Нужно контролировать lag, backpressure и filter ratio.');
    [['Kafka','broker','Платформа','critical','stable'],['Consumer group','internal','Команда интеграций','high','stable'],['Postgres','db','DBA','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4],limit:s[5]||''}));
    [{order:1,name:'Консьюмер читает пачку событий',system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key'},
     {order:2,name:'Консьюмер фильтрует события по признаку',system:'Consumer group',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:1},
     {order:3,name:'Консьюмер сохраняет нужные события в Postgres',system:'Postgres',channel:'db',timeout_ms:300,retry:'auto',idempotency:'key',writes_entity:'yes',depends_on:2,compensation:'unique key, DLQ, replay'}].forEach(addStep);
  } else if(kind==='dispatcher'){
    setv('p_name','Универсальный докатчик запросов в системы А и Б');setv('p_entity','DispatchOperation');setv('p_goal','Один универсальный сервис отправляет запросы в разные целевые системы в рамках одного бизнес-процесса и должен корректно различать подоперации.');setv('p_description','Сервис используется несколькими процессами. Для связи используется operUid, но в одном процессе запрос в систему А и запрос в систему Б могут иметь одинаковый operUid. Сейчас часть поиска выполняется только по operUid, из-за чего записи могут пересекаться. Нужно использовать operationType и при необходимости targetSystem.');setv('p_lookup','operUid + operationType + targetSystem');setv('p_constraints','Сервис универсальный, менять внешние системы дорого, нужно сохранить совместимость старых вызовов.');setv('p_visible','no');setv('p_order','per_entity');setv('p_statuses','CREATED, SENT_TO_TARGET, ACCEPTED_BY_TARGET, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW');setv('p_fields','operUid:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed, requestId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required');
    [['Инициатор процесса','internal','Команда продукта','high','stable'],['Универсальный докатчик','internal','Команда интеграций','critical','stable'],['Система А','external','Владелец системы А','high','limited'],['Система Б','external','Владелец системы Б','high','limited'],['БД докатчика','db','Команда интеграций','critical','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],crit:s[3],stab:s[4]}));
    [{order:1,name:'Инициатор создаёт бизнес-процесс с одним operUid',system:'Инициатор процесса',channel:'rest',timeout_ms:300,idempotency:'key',writes_entity:'yes'},
     {order:2,name:'Докатчик создаёт запись подоперации для системы А',system:'БД докатчика',channel:'db',timeout_ms:200,retry:'auto',idempotency:'natural',writes_entity:'yes',depends_on:1,compensation:'unique key: operUid + operationType + targetSystem'},
     {order:3,name:'Докатчик отправляет запрос в систему А',system:'Система А',channel:'rest',timeout_ms:1500,retry:'auto',idempotency:'key',depends_on:2,compensation:'timeout, retry, manual recovery'},
     {order:4,name:'Докатчик создаёт запись подоперации для системы Б с тем же operUid',system:'БД докатчика',channel:'db',timeout_ms:200,retry:'auto',idempotency:'natural',writes_entity:'yes',depends_on:1,compensation:'unique key: operUid + operationType + targetSystem'},
     {order:5,name:'Докатчик отправляет запрос в систему Б',system:'Система Б',channel:'rest',timeout_ms:1500,retry:'auto',idempotency:'key',depends_on:4,compensation:'timeout, retry, manual recovery'}].forEach(addStep);
  } else {
    addSystem();addStep();
  }
  rail();syncSys();updateProgress();
}
async function submitForm(){
  const payload={
    meta:{name:v('p_name'),entity:v('p_entity'),goal:v('p_goal'),description:v('p_description'),lookup_keys:v('p_lookup'),constraints:v('p_constraints'),customer_visible:v('p_visible'),money:v('p_money'),regulatory:v('p_reg'),sla_ms:v('p_sla'),read_freq:v('p_read'),ordering:v('p_order'),statuses:v('p_statuses'),fields:v('p_fields'),load_rps:v('p_rps'),peak_factor:v('p_peak'),multi_tenant:v('p_tenant'),replacing_legacy:v('p_legacy')},
    systems:rows('#systems').map(s=>({name:s.sname,role:s.srole,owner:s.sowner,criticality:s.scrit,stability:s.sstab,rate_limit_rps:s.slimit})),
    steps:rows('#steps')};
  const box=document.getElementById('errors');box.innerHTML='';
  try{
    const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json();
    if(d.ok){location.href='/run/'+d.id}else{(d.errors||['Неизвестная ошибка']).forEach(e=>{const el=document.createElement('div');el.className='err';el.textContent=e;box.appendChild(el)})}
  }catch(e){const el=document.createElement('div');el.className='err';el.textContent='Сервер недоступен: '+e;box.appendChild(el)}
}
function demo(){applyScenario('reverse')}
window.addEventListener('DOMContentLoaded',()=>{setMode('quick');applyScenario('blank');document.querySelectorAll('input,select,textarea').forEach(e=>e.addEventListener('input',updateProgress));updateProgress();});
"""


def page(title, body, extra_head=''):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style>{extra_head}</head>
<body><div class="wrap">{body}</div></body></html>"""


def titleblock(sub):
    return (f'<header class="titleblock"><h1>Интеграционный проектировщик</h1>'
            f'<div class="meta">ЛИСТ: {escape(sub)}<br>РЕВ. 7.4 · rule-engine · без LLM</div></header>')


def form_page():
    body = titleblock('КОНСТРУКТОР ПРОЦЕССА · ПРОВОДНИК ПО ИНТЕГРАЦИИ') + f"""
<section class="hero">
 <h2>Сначала выберите тип задачи, потом уточните детали.</h2>
 <p>Инструмент не просит писать длинное описание. Выберите ближайший сценарий, проверьте шаги процесса и запустите архитектурный разбор. В расширенном режиме остаются все технические поля, поэтому качество анализа не теряется.</p>
 <div class="steps3"><div class="stepbox"><b>1. Сценарий</b><br>Подставляем шаблон процесса.</div><div class="stepbox"><b>2. Шаги</b><br>Уточняем системы, каналы и восстановление.</div><div class="stepbox"><b>3. Разбор</b><br>Получаем риски, gates, чек-лист и артефакты.</div></div>
 <div class="navlinks"><a href="/invariants">Открыть справочник инвариантов</a><a href="/">Конструктор процесса</a></div>
</section>

<nav class="guidebar" aria-label="Навигация по проектированию"><span class="guide-title">Проектирование:</span><a href="#scenario">1. сценарий</a><a href="#basics">2. смысл</a><a href="#systems-block">3. системы</a><a href="#process-designer">4. шаги</a><a href="#review">5. проверка</a></nav>

<section class="card">
 <div class="toolbar">
  <div class="mode" aria-label="Режим заполнения"><button type="button" data-mode="quick" onclick="setMode('quick')">Быстрый режим</button><button type="button" data-mode="advanced" onclick="setMode('advanced')">Расширенный режим</button></div>
  <span class="spacer"></span>
  <button type="button" class="btn ghost" onclick="applyScenario('blank')">очистить</button>
 </div>
 <p class="hint quick-note">В быстром режиме скрыты редкие технические поля. Они не удалены: переключитесь в расширенный режим, чтобы настроить retry, идемпотентность, зависимости, лимиты и компенсации.</p>
 <p class="hint advanced-note">В расширенном режиме доступны все поля, которые использует rule-engine.</p>
 <div class="progress" id="fillbar"><i></i></div><p class="hint" id="filltext"></p><div id="liveGuide" class="assist"></div>
</section>

<section class="card" id="scenario"><h2>Выберите ближайший сценарий</h2>
 <div class="scenarios">
  <button type="button" class="scenario" onclick="applyScenario('reverse')"><b>Обратный поток статусов</b><span>Банк ↔ УК, статусы документов и операций.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('kafka')"><b>События через Kafka</b><span>Публикация изменений, Outbox, Inbox, DLQ.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('enrichment')"><b>Обогащение данных</b><span>Kafka + REST к внешней системе + новый топик.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('dwh')"><b>DWH / CDC / витрина</b><span>Передача данных в аналитику без нагрузки на core-flow.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('highload')"><b>Highload consumer</b><span>Фильтрация общего топика и запись в Postgres.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('dispatcher')"><b>Универсальный докатчик</b><span>Один operUid, разные operationType и целевые системы.</span></button>
  <button type="button" class="scenario" onclick="applyScenario('blank')"><b>С нуля</b><span>Пустая форма для нестандартного процесса.</span></button>
 </div>
</section>

<section class="card" id="basics"><h2>1. Опишите бизнес-процесс</h2>
 <p class="hint">Достаточно заполнить смысл процесса, основную сущность и несколько ключевых ограничений. Остальное можно уточнить позже.</p><div class="minimal"><div class="mini"><b>Сущность</b><span>что меняется в процессе</span></div><div class="mini"><b>Ключ</b><span>по чему искать и дедуплицировать</span></div><div class="mini"><b>Статусы</b><span>где процесс может зависнуть</span></div><div class="mini"><b>Ошибки</b><span>как восстановиться</span></div></div>
 <div class="grid g3">
  <div><label for="p_name">Как называется процесс?</label><input id="p_name" placeholder="Например: обратный поток статусов"></div>
  <div><label for="p_entity">Какая основная сущность?</label><input id="p_entity" placeholder="Например: заявка, договор, документ"><div class="fieldtip">То, вокруг чего строится процесс: заявка, договор, документ, платёж или операция.</div></div>
  <div><label for="p_sla">Сколько можно ждать ответ?</label><input id="p_sla" inputmode="numeric" placeholder="мс; пусто, если процесс асинхронный"><div class="fieldtip">Если клиент ждёт ответ, укажите SLA. Если обработка фоновая, поле можно оставить пустым.</div></div>
 </div>
 <label for="p_goal">Какую бизнес-задачу решает процесс?</label><input id="p_goal" placeholder="Например: банк должен видеть финальный статус обработки в УК">
 <label for="p_description">Краткое описание ситуации своими словами</label><textarea id="p_description" placeholder="Например: универсальный докатчик отправляет запросы в систему А и систему Б. В рамках одного процесса используется один operUid, поэтому поиск только по operUid может склеить разные записи."></textarea>
 <div class="grid g2">
  <div id="fix-lookup"><label for="p_lookup">По каким полям искать, обновлять и дедуплицировать запись?</label><input id="p_lookup" placeholder="Например: operUid + operationType + targetSystem"><div class="fieldtip">Это ключ, по которому система понимает, какую запись обновлять и что считать дублем. Для общих адаптеров часто нужен составной ключ: requestId + operationType + targetSystem + tenantId.</div></div>
  <div id="fix-constraints"><label for="p_constraints">Какие ограничения или компромиссы есть?</label><input id="p_constraints" placeholder="Например: нельзя менять сервис А, новый топик запрещён, срок 2 недели"><div class="fieldtip">Ограничения нужны, чтобы модель предложила не только идеальное решение, но и безопасный компромисс.</div></div>
 </div>
 <div class="grid g4">
  <div><label for="p_visible">Клиент ждёт результат?</label><select id="p_visible"><option value="no">Нет</option><option value="yes">Да</option><option value="mixed">Частично</option></select></div>
  <div><label for="p_money">Есть влияние на деньги?</label><select id="p_money"><option value="no">Нет</option><option value="indirect">Косвенно</option><option value="direct">Напрямую</option></select></div>
  <div><label for="p_reg">Есть регуляторный риск?</label><select id="p_reg"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_order">Нужен порядок событий?</label><select id="p_order"><option value="no">Нет</option><option value="per_entity">В рамках одной сущности</option><option value="global">Глобальный порядок</option></select></div>
 </div>
 <div class="grid g3 advanced-only">
  <div><label for="p_rps">Средняя нагрузка, RPS</label><input id="p_rps" inputmode="numeric" placeholder="Например: 100"></div>
  <div><label for="p_peak">Пиковая нагрузка</label><select id="p_peak"><option value="1">x1</option><option value="2">x2</option><option value="5">x5</option><option value="10">x10</option></select></div>
  <div><label for="p_tenant">Один поток для разных клиентов?</label><select id="p_tenant"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_legacy">Это замена legacy?</label><select id="p_legacy"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_read">Как часто читают результат?</label><select id="p_read"><option value="low">Редко</option><option value="medium" selected>Средне</option><option value="high">Часто</option><option value="very_high">Очень часто</option></select></div>
 </div>
 <div class="grid g2">
  <div id="fix-statuses"><label for="p_statuses">Какие статусы есть у процесса?</label><input id="p_statuses" placeholder="Например: CREATED, PROCESSING, COMPLETED, REJECTED"><div class="fieldtip">Статусы показывают, где находится заявка и какие состояния считаются финальными.</div></div>
  <div id="fix-fields"><label for="p_fields">Какие ключевые поля есть у сущности?</label><input id="p_fields" placeholder="Например: requestId:string|required|unique"><div class="fieldtip">Отметьте required, unique, indexed и sensitive: это влияет на контракт, индексы, безопасность и тесты.</div></div>
 </div>
 <p class="hint">Формат поля: имя:тип|required|unique|indexed|sensitive. Пример: requestId:string|required|unique.</p><p><button type="button" class="btn ghost" onclick="suggestBasics()">подставить базовые статусы, поля и ключи</button></p>
</section>

<section class="card" id="systems-block"><h2>2. Укажите системы-участники</h2>
 <p class="hint">Добавьте сервисы, брокеры, внешние системы, базы данных и аналитические контуры. В быстром режиме достаточно названия, роли и владельца.</p>
 <table id="systems"><thead><tr><th>Система</th><th>Роль</th><th>Владелец</th><th class="advanced-only">Критичность</th><th class="advanced-only">Стабильность</th><th class="advanced-only">RPS-лимит</th><th></th></tr></thead><tbody></tbody></table>
 <p><button type="button" class="btn ghost" onclick="addSystem()">+ добавить систему</button></p>
 <datalist id="syslist"></datalist>
</section>

<section class="card" id="process-designer"><h2>3. Соберите цепочку шагов</h2>
 <p class="hint">Каждый шаг — это ответ на вопрос: кто что делает, через какой канал, ждёт ли ответ и как восстановиться при ошибке.</p><div class="help"><b>Как заполнять шаг:</b> сначала укажите понятное действие и систему. Технические поля можно раскрыть в расширенном режиме: retry, идемпотентность, зависимости и восстановление.</div>
 <div class="templatebar" aria-label="Быстро добавить типовой шаг"><button type="button" class="btn ghost" onclick="addTemplate('rest')">+ REST-вызов</button><button type="button" class="btn ghost" onclick="addTemplate('kafka')">+ Kafka-событие</button><button type="button" class="btn ghost" onclick="addTemplate('db')">+ запись в БД</button><button type="button" class="btn ghost" onclick="addTemplate('webhook')">+ webhook/callback</button><button type="button" class="btn ghost" onclick="addTemplate('batch')">+ batch/file</button><button type="button" class="btn ghost" onclick="applySafeDefaultsAll()">безопасные настройки всем шагам</button></div>
 <div class="process-layout"><div><table id="steps"><thead><tr><th>№</th><th>Что происходит</th><th>Кто выполняет</th><th>Канал</th><th>Следующий шаг</th><th>Timeout</th><th class="advanced-only">Повтор</th><th class="advanced-only">Идемпотентность</th><th>Меняет сущность</th><th class="advanced-only">После №</th><th class="advanced-only">Восстановление</th><th></th></tr></thead><tbody></tbody></table>
 <p><button type="button" class="btn ghost" onclick="addStep()">+ пустой шаг</button>
    <button type="button" class="btn ghost" onclick="demo()">заполнить примером</button></p></div>
 <aside class="sidepanel"><h3>Подсказка по цепочке</h3><p>Хороший процесс описывает не только happy path, но и восстановление.</p><ul><li>Для REST — timeout, fallback, circuit breaker.</li><li>Для Kafka — DLQ, replay, offset/ack.</li><li>Для webhook — подпись, timestamp, Inbox.</li><li>Для БД — транзакция и уникальный ключ.</li></ul></aside></div>
</section>

<section class="card" id="review"><h2>4. Проверьте ленту процесса</h2><p class="hint">Сплошная линия — блокирующий шаг. Пунктир — асинхронная граница или событие.</p><div class="rail" id="rail"></div><h3>Краткая сводка ввода</h3><div id="reviewBox" class="reviewbox"></div></section>

<div id="errors"></div>
<p><button type="button" class="btn" onclick="submitForm()">Проверить архитектуру и сформировать разбор</button></p>
<script>{FORM_JS}</script>"""
    return page('Интеграционный проектировщик v7.6', body)




def _inv_plain(inv):
    title = inv.get('title') or 'Инвариант'
    question = inv.get('question') or ''
    return f'{title}. Главная проверка: {question}'


def _inv_prefix(inv):
    return str(inv.get('code') or '').split('-')[0].upper()


def _inv_term_hint(inv):
    """Мини-расшифровка терминов, которые часто пугают новичка."""
    text = ' '.join(str(inv.get(k, '')) for k in ('title', 'question', 'why', 'how', 'area')).lower()
    hints = []
    if any(x in text for x in ['scope', 'област', 'уникальн']):
        hints.append('Область уникальности — это ответ на вопрос «где именно этот id не должен повторяться»: во всей системе, внутри типа операции, внутри провайдера, внутри tenant или внутри целевой системы.')
    if any(x in text for x in ['idempotency', 'идемпот']):
        hints.append('Идемпотентность означает, что повтор того же запроса или события не создаёт второй документ, платёж, заявку или статус.')
    if 'dlq' in text:
        hints.append('DLQ — это отдельное место для сообщений, которые не удалось обработать автоматически; после исправления ошибки их нужно уметь безопасно переиграть.')
    if 'replay' in text or 'переигр' in text:
        hints.append('Replay — это повторная обработка уже полученного сообщения или операции после исправления причины ошибки.')
    if 'outbox' in text:
        hints.append('Outbox — это способ сначала надёжно записать событие рядом с бизнес-данными в БД, а потом безопасно опубликовать его в брокер.')
    if 'inbox' in text:
        hints.append('Inbox — это таблица или механизм на стороне получателя, который запоминает уже обработанные события и не даёт обработать дубль второй раз.')
    if 'correlation' in text or 'trace' in text:
        hints.append('CorrelationId или traceId нужен не для уникальности операции, а чтобы найти всю цепочку вызовов и событий при разборе инцидента.')
    if 'backpressure' in text:
        hints.append('Backpressure — это управляемое замедление обработки, чтобы система не умерла под пиком нагрузки.')
    if 'cutover' in text:
        hints.append('Cutover — это момент переключения со старого процесса на новый; для него нужны критерии успеха и план отката.')
    return ' '.join(hints)


def _inv_simple_core(inv):
    """Короткое объяснение без канцелярита: что именно нужно не забыть."""
    prefix = _inv_prefix(inv)
    question = (inv.get('question') or '').rstrip('?.')
    title = (inv.get('title') or '').rstrip('.')
    starters = {
        'BIZ': 'Сначала надо договориться о смысле процесса, а уже потом выбирать Kafka, REST, БД или очереди.',
        'ID': 'Главная мысль: Любой id кажется уникальным, пока не появляется второй тип операции, другая целевая система, другой провайдер или tenant. Поэтому id сам по себе почти никогда не бывает «просто уникальным»; нужно понять, внутри какой области он уникален.',
        'CON': 'Контракт — это не просто JSON-пример, а договор между системами о полях, ошибках, версиях и совместимости.',
        'SCN': 'Процесс нельзя описывать только happy path: обязательно нужны альтернативы, ошибки, зависания и финальные состояния.',
        'DAT': 'Данные должны меняться предсказуемо: один владелец записи, понятная транзакция, защита от дублей и история изменений.',
        'ASY': 'В асинхронной обработке сообщение может прийти дважды, опоздать, прийти не по порядку или упасть в ошибку — это нормальные сценарии, а не исключения.',
        'API': 'В синхронном вызове одна система ждёт другую, поэтому время ожидания, ошибки и деградация должны быть жёстко ограничены.',
        'EXT': 'Внешняя система вам не подчиняется: она может тормозить, вернуть 429/5xx, прислать дубль callback или не дать однозначный результат.',
        'PERF': 'Производительность надо проверять не на среднем happy path, а на пиках, лагах, лимитах зависимостей и росте данных.',
        'SEC': 'Безопасность — это не только авторизация: ПДн, секреты, DLQ, логи, дампы, replay и ручные инструменты тоже должны быть защищены.',
        'OBS': 'Если в production что-то сломалось, команда должна быстро найти цепочку, понять статус и выполнить понятный runbook.',
        'CMP': 'Для денег, регуляторики и юридически значимых действий мало “сделали”: нужно уметь доказать кто, когда, почему и что изменил.',
        'MIG': 'Релиз и миграция должны быть обратимыми: нужно понимать, как переключаемся, что с незавершёнными процессами и как откатываемся.',
        'DWH': 'Аналитика и витрины не должны ломать основной процесс, а данные должны быть полными, проверяемыми и пересобираемыми.',
        'TST': 'Любой важный риск должен превратиться в конкретный тест или production-gate, иначе он останется красивой фразой в отчёте.',
    }
    first = starters.get(prefix, 'Этот пункт нужен, чтобы не пропустить важную проверку до разработки и релиза.')
    return f'{first} В этом инварианте надо проверить: {question}. Если сказать совсем коротко: {title.lower()}.'


def _inv_deep_description(inv):
    """Понятное, но не обеднённое описание инварианта."""
    why = inv.get('why') or ''
    how = inv.get('how') or ''
    hint = _inv_term_hint(inv)
    parts = [_inv_simple_core(inv)]
    if why:
        parts.append(f'Почему это важно: {why}')
    if how:
        parts.append(f'Что нужно сделать: {how}')
    if hint:
        parts.append(f'Расшифровка терминов: {hint}')
    return ' '.join(parts)


def _inv_bad_good(inv):
    prefix = _inv_prefix(inv)
    bad_good = {
        'BIZ': ('Плохо: команда описала набор вызовов, но не знает, какой статус считается финальным и кто владелец результата.', 'Хорошо: есть цель процесса, финальный результат, владелец, обязательные шаги и понятные правила ручного разбора.'),
        'ID': ('Плохо: поиск, дедупликация или replay идут только по requestId/operUid, хотя тот же id может встретиться в другом типе операции или целевой системе.', 'Хорошо: во всех местах используется один составной ключ, например requestId + operationType + targetSystem + tenantId.'),
        'CON': ('Плохо: есть пример JSON, но не описаны required-поля, ошибки, версии, enum и совместимость.', 'Хорошо: есть OpenAPI/AsyncAPI/схема, правила версионирования и contract tests для успеха, дубля, ошибки и новой версии.'),
        'SCN': ('Плохо: описан только основной путь, а зависание, отказ партнёра, отмена, дубль и ручное исправление не разобраны.', 'Хорошо: для каждого важного отклонения есть статус, действие системы, владелец и критерий завершения.'),
        'DAT': ('Плохо: несколько сервисов пишут одну сущность, БД и событие обновляются отдельно, а повтор может создать дубль.', 'Хорошо: есть system of record, транзакционная граница, Outbox/Inbox, уникальные индексы и правила конкурентного обновления.'),
        'ASY': ('Плохо: consumer просто читает сообщение и пишет в БД, но не описаны дубли, DLQ, replay, offset/ack и out-of-order.', 'Хорошо: обработка повторяемая, дедуплицируется, poison message уходит в DLQ, replay безопасен, offset коммитится после успешной записи.'),
        'API': ('Плохо: цепочка REST-вызовов ждёт все внешние системы и суммарно превышает SLA.', 'Хорошо: критический путь короткий, timeout ограничен, тяжёлый хвост вынесен в async, клиент получает trackingId или понятный fallback.'),
        'EXT': ('Плохо: отказ провайдера считается редкостью и не описан как штатный сценарий.', 'Хорошо: есть timeout, circuit breaker, rate limit strategy, status inquiry, дедупликация callback и деградация.'),
        'PERF': ('Плохо: проверили 100 событий на тестовом контуре и решили, что production выдержит пик.', 'Хорошо: рассчитаны RPS, p95/p99, partitions, consumer lag, индексы, rate limits, backpressure и проведены load/stress/soak-тесты.'),
        'SEC': ('Плохо: ПДн, токены или payload событий попадают в логи, DLQ и витрины без маскирования и retention.', 'Хорошо: данные минимизированы, секреты не логируются, доступ ограничен, retention описан, replay защищён.'),
        'OBS': ('Плохо: при инциденте команда ищет руками по разным логам и не понимает, где зависла операция.', 'Хорошо: по одному correlationId видна вся цепочка, есть метрики, алерты, дашборд, владелец и runbook.'),
        'CMP': ('Плохо: операция изменилась, но нельзя доказать автора, время, причину и исходные данные.', 'Хорошо: есть audit trail, ledger/status history, сверки, причины ручных исправлений и неизменяемый журнал.'),
        'MIG': ('Плохо: включили новый поток и надеются, что откатится простым rollback кода.', 'Хорошо: есть dual-run/shadow, cutover checklist, обработка in-flight, совместимость схем и проверенный rollback.'),
        'DWH': ('Плохо: витрина синхронно читает production-БД или отчёт строится без контроля полноты.', 'Хорошо: данные уходят через CDC/ETL вне core-flow, есть watermark, lineage, freshness, сверка и backfill.'),
        'TST': ('Плохо: тест есть только на happy path.', 'Хорошо: есть тест на дубль, out-of-order, timeout, DLQ/replay, контракт, rollback, security-negative и нагрузку.'),
    }
    bad, good = bad_good.get(prefix, ('Плохо: пункт остался как устная договорённость и не попал в контракт, DDL, ADR, тест или DoD.', 'Хорошо: решение зафиксировано в артефакте и проверяется до релиза.'))
    return f'{bad} {good}'


def _inv_steps_to_apply(inv):
    prefix = _inv_prefix(inv)
    common = {
        'BIZ': '1) Назовите бизнес-результат. 2) Укажите владельца результата. 3) Разделите обязательные и необязательные шаги. 4) Опишите финальные статусы и ручной разбор.',
        'ID': '1) Выпишите все id. 2) Для каждого id укажите область уникальности. 3) Сравните lookup, UNIQUE-индекс, idempotency key, Inbox/Outbox и replay. 4) Исправьте места, где ключ неполный.',
        'CON': '1) Зафиксируйте схему. 2) Отметьте required/optional поля. 3) Опишите ошибки и enum. 4) Проверьте backward/forward compatibility. 5) Добавьте contract tests.',
        'SCN': '1) Опишите happy path. 2) Для каждого шага добавьте отказную ветку. 3) Добавьте альтернативы и отмену. 4) Укажите финальные статусы. 5) Добавьте критерии приёмки.',
        'DAT': '1) Найдите владельца сущности. 2) Опишите границы транзакций. 3) Добавьте уникальные индексы. 4) Проверьте повторы и конкурентные обновления. 5) Зафиксируйте аудит/историю.',
        'ASY': '1) Опишите delivery semantics. 2) Добавьте idempotency/Inbox. 3) Опишите retry, DLQ и replay. 4) Определите partition/ordering. 5) Настройте lag/DLQ-алерты.',
        'API': '1) Посчитайте timeout критического пути. 2) Ограничьте retry. 3) Добавьте error contract. 4) Настройте circuit breaker/fallback. 5) Сверьте с SLA.',
        'EXT': '1) Узнайте лимиты и SLA провайдера. 2) Опишите timeout/429/5xx. 3) Добавьте idempotency и status inquiry. 4) Проверьте callback signature и duplicate callback. 5) Опишите деградацию.',
        'PERF': '1) Укажите средний и пиковый RPS. 2) Найдите узкие места. 3) Проверьте индексы/партиции/lag. 4) Добавьте backpressure. 5) Проведите load/stress/soak.',
        'SEC': '1) Найдите ПДн/секреты. 2) Проверьте логи, DLQ, outbox и витрины. 3) Ограничьте доступ. 4) Опишите retention. 5) Добавьте security-negative tests.',
        'OBS': '1) Проведите correlationId через все шаги. 2) Добавьте метрики и алерты. 3) Назначьте владельца. 4) Напишите runbook. 5) Проверьте разбор одного тестового инцидента.',
        'CMP': '1) Определите юридически значимые действия. 2) Запишите audit trail. 3) Добавьте сверки. 4) Опишите ручные исправления. 5) Проверьте хранение доказательств.',
        'MIG': '1) Опишите старый и новый путь. 2) Запустите dual-run/shadow. 3) Опишите cutover. 4) Решите судьбу in-flight процессов. 5) Проверьте rollback.',
        'DWH': '1) Уберите DWH из core-flow. 2) Опишите CDC/ETL. 3) Добавьте watermark и сверки. 4) Укажите freshness. 5) Подготовьте backfill.',
        'TST': '1) Возьмите риск из инварианта. 2) Превратите его в тест-кейс. 3) Добавьте проверку в DoD. 4) Прогоните happy path и отказные ветки. 5) Зафиксируйте ожидаемый результат.',
    }
    return common.get(prefix, '1) Ответьте на вопрос карточки. 2) Зафиксируйте решение в проектном артефакте. 3) Добавьте проверку в DoD или тест. 4) Назначьте владельца.')


def _inv_normal_state(inv):
    prefix = _inv_prefix(inv)
    if prefix == 'BIZ':
        return 'Нормальное состояние: понятны бизнес-цель, финальный результат, владелец процесса, обязательные и необязательные шаги, финальные статусы и правила ручного разбора.'
    if prefix == 'ID':
        return 'Нормальное состояние: для каждого id написано, где он уникален. Один и тот же набор полей используется в SELECT, UPDATE, UPSERT, UNIQUE-индексе, idempotency key, Inbox/Outbox и replay. Например, не просто requestId, а requestId + operationType + targetSystem + tenantId.'
    if prefix == 'CON':
        return 'Нормальное состояние: контракт описан в OpenAPI/AsyncAPI или другой явной схеме, а не только примером. В нём есть версии, обязательные поля, enum, формат ошибок и правила совместимости. Все важные ветки проверяются contract tests.'
    if prefix == 'SCN':
        return 'Нормальное состояние: кроме happy path описаны альтернативные ветки, ошибки, отмена, зависания, финальные статусы и владелец ручного разбора.'
    if prefix == 'DAT':
        return 'Нормальное состояние: понятно, кто владеет сущностью, кто имеет право писать, где граница транзакции, как защищаемся от дублей, гонок и фантомных событий.'
    if prefix == 'ASY':
        return 'Нормальное состояние: повтор сообщения безопасен, дубль не создаёт вторую бизнес-операцию, DLQ и replay описаны, offset/ack коммитится в правильный момент, порядок событий учтён.'
    if prefix == 'API':
        return 'Нормальное состояние: каждый синхронный вызов имеет короткий timeout, ограниченный retry, понятный ответ об ошибке, circuit breaker/fallback и укладывается в общий SLA.'
    if prefix == 'EXT':
        return 'Нормальное состояние: внешний отказ не ломает весь процесс. Есть лимиты, timeout, circuit breaker, status inquiry, дедупликация callback и понятный сценарий деградации.'
    if prefix == 'PERF':
        return 'Нормальное состояние: рассчитаны средняя и пиковая нагрузка, consumer lag, rate limits, индексы, рост таблиц, backpressure и деградация. Это подтверждено нагрузочными тестами.'
    if prefix == 'SEC':
        return 'Нормальное состояние: ПДн и секреты минимизированы, маскируются и не попадают в логи/DLQ/outbox/витрины без правил доступа и retention.'
    if prefix == 'OBS':
        return 'Нормальное состояние: по одному correlationId можно восстановить путь операции через все системы, увидеть статус, ошибки, лаги, DLQ, владельца алерта и runbook.'
    if prefix == 'CMP':
        return 'Нормальное состояние: юридически значимые изменения пишутся в неизменяемую историю, ручные исправления имеют автора/причину/время, а результат можно сверить с источником.'
    if prefix == 'MIG':
        return 'Нормальное состояние: есть план переключения, dual-run или shadow mode, обработка незавершённых процессов, совместимость версий и проверенный откат.'
    if prefix == 'DWH':
        return 'Нормальное состояние: аналитика получает данные вне основного клиентского процесса, полнота контролируется, freshness известна, lineage есть, backfill возможен.'
    if prefix == 'TST':
        return 'Нормальное состояние: для инварианта есть конкретный тест или production-gate. Тест покрывает не только успех, но и дубли, отказы, rollback, безопасность или нагрузку.'
    return 'Нормальное состояние: решение явно отвечает на вопрос карточки, зафиксировано в контракте, ADR, DDL, тесте или DoD и имеет владельца.'


def _inv_review_questions(inv):
    prefix = _inv_prefix(inv)
    base = inv.get('question') or 'Что нужно проверить по этому инварианту?'
    extra = {
        'BIZ': 'Какой финальный результат? Кто владелец? Что видит клиент или система-потребитель? Какие шаги можно выполнить позже?',
        'ID': 'Где именно уникален id? Совпадают ли поля SELECT, UPDATE, UPSERT, UNIQUE, idempotency, Inbox, Outbox и replay?',
        'CON': 'Проверены ли успех, ошибка, дубль, новая версия, неизвестное enum-значение и отсутствие обязательного поля?',
        'SCN': 'Что происходит при отказе каждого шага, зависании, отмене, повторе, частичном успехе и ручном исправлении?',
        'DAT': 'Кто единственный писатель? Где атомарность? Что будет при двух параллельных запросах и повторной доставке?',
        'ASY': 'Когда коммитится offset/ack? Где DLQ? Кто делает replay? Как обрабатываются дубль, stale event и out-of-order?',
        'API': 'Сходится ли сумма timeout с SLA? Что при 429/5xx/timeout? Есть ли ограниченный retry, circuit breaker и fallback?',
        'EXT': 'Какие лимиты провайдера? Что при дубле callback, невалидной подписи, неизвестном результате и недоступности?',
        'PERF': 'Какой peak RPS, p95/p99, limit зависимости, lag, размер таблиц, индексы и план деградации?',
        'SEC': 'Попадают ли ПДн/секреты в логи, DLQ, outbox, дампы, витрины, ошибочные ответы или replay-инструменты?',
        'OBS': 'Можно ли по одному id расследовать инцидент? Какие метрики/алерты сработают? Кто владелец? Есть ли runbook?',
        'CMP': 'Можно ли доказать факт операции, автора, время, причину исправления и источник данных для отчёта?',
        'MIG': 'Как переключаем трафик? Что с in-flight? Как сравниваем старый и новый путь? Как откатываемся?',
        'DWH': 'Как доказать полноту выгрузки, freshness, lineage и возможность пересобрать период?',
        'TST': 'Какой конкретный тест доказывает, что инвариант соблюдён? Где он в QA/DoD?',
    }.get(prefix, 'Где это зафиксировано и кто отвечает за проверку перед релизом?')
    return f'Главный вопрос: {base} Дополнительные вопросы: {extra}'


def _inv_example(inv):
    examples = inv.get('examples') or []
    if examples:
        return '; '.join(str(x) for x in examples)
    code = (inv.get('code') or '').upper()
    area = (inv.get('area') or '').lower()
    title = (inv.get('title') or '').lower()
    if code.startswith('ID-') or 'ключ' in area or 'идентификатор' in title:
        return 'Ошибка: универсальный адаптер ищет запись только по requestId. В процессе есть разные operationType и targetSystem, поэтому запись системы A может пересечься с записью системы B. Правильно: искать и дедуплицировать по requestId + operationType + targetSystem.'
    if code.startswith('CON-') or 'контракт' in area:
        return 'Ошибка: в успешном ответе поле statusReason есть, а в ветке “дубль” его забыли вернуть, хотя по контракту поле обязательное. Правильно: contract test должен проверить все ветки ответа.'
    if code.startswith('EVT-') or 'событ' in area:
        return 'Ошибка: событие пришло без eventVersion и correlationId. Потребитель не может безопасно обработать новую версию и расследовать цепочку. Правильно: использовать event envelope.'
    if code.startswith('OBS-') or 'наблюдаем' in area:
        return 'Ошибка: заявка зависла, но в логах разных систем нет общего correlationId, алерта и владельца. Поддержка ищет причину вручную. Правильно: сквозной correlationId, метрики, алерты, дашборд и runbook.'
    if code.startswith('CMP-') or 'комплаенс' in area or 'аудит' in area:
        return 'Ошибка: статус финансовой операции изменили вручную, но не зафиксировали автора, причину и исходные данные. Правильно: audit trail, причина исправления, автор, время и сверка с источником.'
    if code.startswith('TST-') or 'тест' in area:
        return 'Ошибка: проверили только успешный путь. В production пришёл дубль, out-of-order событие или ошибка контракта. Правильно: добавить отдельный тест на этот отказный сценарий.'
    if 'retry' in title or 'dlq' in title or 'replay' in title or 'надёж' in area:
        return 'Ошибка: consumer упал после записи в БД, Kafka прислала сообщение повторно, и создалась вторая бизнес-запись. Правильно: сначала проверить idempotency/Inbox, потом писать данные, затем коммитить offset.'
    if 'статус' in area or 'статус' in title:
        return 'Ошибка: заявка зависла между SENT и COMPLETED, но нет статуса ERROR/NEEDS_MANUAL_REVIEW и неясно, кто должен разбирать зависание.'
    if 'безопас' in area or 'пдн' in title or 'sensitive' in title:
        return 'Ошибка: паспортные данные попали в лог, DLQ или outbox без маскирования и срока хранения. Правильно: минимизировать payload, маскировать ПДн и ограничить доступ.'
    if 'dwh' in area or 'cdc' in title or 'витрин' in title:
        return 'Ошибка: аналитическая витрина синхронно читает production-БД и влияет на клиентский сценарий. Правильно: CDC/ETL вне core-flow и сверка полноты.'
    if 'миграц' in area or 'legacy' in title or 'rollback' in title:
        return 'Ошибка: новая схема данных включена без rollback-плана. При откате старый сервис не понимает новые поля или статусы.'
    if 'нагруз' in area or 'consumer' in title or 'backpressure' in title:
        return 'Ошибка: пик входящих событий превышает способность consumer group, растёт lag, а backpressure и алерты не описаны.'
    if 'внешн' in area or 'provider' in title or 'timeout' in title:
        return 'Ошибка: внешний сервис отвечает 10 секунд, а клиентский SLA — 1 секунда. Правильно: ограничить timeout, включить circuit breaker и вернуть trackingId/деградацию.'
    return 'Ошибка: команда устно договорилась “потом разберёмся”, но не добавила проверку в контракт, DDL, ADR, тест или Definition of Done.'


def _inv_stage(inv):
    prefix = _inv_prefix(inv)
    area = (inv.get('area') or '').lower()
    scope = (inv.get('scope') or '').lower()
    if prefix == 'BIZ':
        return 'Сбор требований и предпроект: до выбора протоколов, топиков, БД и контрактов. Повторить перед согласованием сценария.'
    if prefix == 'ID':
        return 'Проектирование данных и контрактов: до DDL, API/Event-схем, Inbox/Outbox и replay. Повторить при любом изменении ключей.'
    if prefix == 'CON':
        return 'Проектирование API/Event/File-контракта: до разработки. Обязательно проверить на контрактном ревью и в contract tests.'
    if prefix == 'SCN':
        return 'Проектирование сценария: после happy path и до постановки задач в разработку. Потом перенести в QA-сценарии.'
    if prefix == 'DAT':
        return 'Проектирование хранения и записи: до DDL, миграций, разработки записи и публикации событий.'
    if prefix == 'ASY':
        return 'Проектирование асинхронной обработки: до создания топиков, consumer group, retry, DLQ и replay-процедур.'
    if prefix == 'API':
        return 'Проектирование синхронного взаимодействия: до утверждения SLA, timeout, retry и клиентского контракта ошибок.'
    if prefix == 'EXT':
        return 'Интеграция с внешней системой: до подключения провайдера и до отказных/нагрузочных тестов.'
    if prefix == 'DWH':
        return 'Проектирование аналитического контура: до выбора CDC/ETL, витрин, retention и правил сверки с источником.'
    if prefix == 'MIG':
        return 'План внедрения и миграции: до релиза, cutover, dual-run и rollback-плана.'
    if prefix == 'SEC' or 'безопас' in area or scope == 'security':
        return 'Security/Data review: до вывода данных в логи, DLQ, outbox, витрины и внешние интеграции.'
    if prefix == 'PERF':
        return 'Capacity planning: до согласования SLA и перед load/stress/soak-тестированием.'
    if prefix == 'OBS':
        return 'Проектирование эксплуатации: до запуска в тестовый контур и до настройки алертов/дашбордов.'
    if prefix == 'CMP':
        return 'Комплаенс и аудит: до согласования регуляторного или финансового процесса и перед production gate.'
    if prefix == 'TST':
        return 'План тестирования: до разработки автотестов и перед release readiness.'
    return 'Архитектурное ревью: проверить до постановки в разработку и повторить перед выпуском.'


def _inv_when(inv):
    prefix = _inv_prefix(inv)
    title = (inv.get('title') or '').lower()
    area = (inv.get('area') or '').lower()
    if prefix == 'ID':
        return 'Всегда, когда id используется для поиска, обновления, дедупликации, идемпотентности, replay или связи записей между системами.'
    if prefix == 'CON':
        return 'Всегда, когда одна система отдаёт другой API, событие, файл, webhook или batch-формат.'
    if prefix == 'SCN':
        return 'Для любого процесса длиннее одного шага, особенно если есть статусы, ожидание внешней системы, ручной разбор или клиентский результат.'
    if prefix == 'DAT':
        return 'Когда шаг пишет бизнес-сущность, меняет статус, создаёт операцию, публикует событие после записи или допускает параллельные обновления.'
    if prefix == 'ASY':
        return 'Для Kafka, очередей, webhook/callback, CDC, файловой загрузки и любой обработки, где результат появляется позже запроса.'
    if prefix == 'API':
        return 'Для REST, gRPC, SOAP и прямых синхронных вызовов, где вызывающая система ждёт ответ.'
    if prefix == 'EXT':
        return 'При любом провайдере или системе вне вашего контроля: банк, УК, БКИ, PSP, KYC, логистика, гос/регуляторный контур.'
    if prefix == 'DWH':
        return 'Когда данные уходят в DWH, витрины, BI, отчётность, ML, CDC/ETL или читаются аналитическим контуром.'
    if prefix == 'MIG':
        return 'При замене legacy, параллельном запуске старого и нового потока, изменении схемы, cutover или rollback.'
    if prefix == 'SEC':
        return 'При ПДн, финансовых данных, секретах, токенах, webhook-подписях, внешних каналах, логах и DLQ.'
    if prefix == 'PERF':
        return 'Когда есть SLA, RPS, пики нагрузки, consumer lag, rate limits, большие таблицы, массовая обработка или highload.'
    if prefix == 'OBS':
        return 'Для распределённых цепочек, асинхронных потоков, внешних вызовов и процессов, которые должна сопровождать поддержка.'
    if prefix == 'CMP':
        return 'Для денег, юридически значимых действий, регуляторной отчётности, аудита и процессов с ручным согласованием.'
    if prefix == 'TST':
        return 'При подготовке DoD, QA-чек-листа, контрактных, интеграционных, отказных и регрессионных тестов.'
    if 'файл' in area or 'batch' in title:
        return 'Для файлового обмена, пакетной обработки и повторной загрузки больших наборов данных.'
    return 'Если условие из карточки может встретиться в процессе или влияет на данные, SLA, восстановление, безопасность или эксплуатацию.'


def _inv_consequence(inv):
    prefix = _inv_prefix(inv)
    if prefix == 'ID':
        return 'Система может найти или обновить чужую запись, ошибочно принять корректное событие за дубль, создать дубль при replay или перезаписать операцию другой целевой системы.'
    if prefix == 'CON':
        return 'Потребитель сломается на новой версии, редкая ветка вернёт неполный ответ, обязательное поле пропадёт в ошибке или дубле, а дефект всплывёт на интеграции или в production.'
    if prefix == 'SCN':
        return 'Процесс зависнет в промежуточном статусе, поддержка не поймёт владельца проблемы, клиент увидит неопределённый результат, а команда начнёт чинить вручную без правил.'
    if prefix == 'DAT':
        return 'Появятся рассинхрон, lost update, двойная запись, фантомное событие, конфликт владельцев данных или невозможность доказать корректное состояние.'
    if prefix == 'ASY':
        return 'Сообщение потеряется, будет бесконечно ретраиться, попадёт в DLQ без процедуры восстановления, обработается не по порядку или создаст дубль.'
    if prefix == 'API':
        return 'Один медленный вызов потянет задержку по всей цепочке, исчерпает пул потоков, нарушит SLA и может вызвать каскадный отказ.'
    if prefix == 'EXT':
        return 'Отказ или лимит внешней системы станет отказом вашего процесса: появятся 429, timeout, дубли callback или неизвестный результат без понятной деградации.'
    if prefix == 'DWH':
        return 'Аналитика начнёт влиять на core-flow, витрины разойдутся с источником, отчётность будет неполной или устаревшей, а период нельзя будет пересобрать.'
    if prefix == 'MIG':
        return 'Релиз нельзя будет безопасно откатить, старый и новый потоки разойдутся, in-flight процессы потеряются, данные новой схемы окажутся несовместимы со старой системой.'
    if prefix == 'SEC':
        return 'ПДн или секреты попадут в логи, DLQ, outbox или витрины; появится риск утечки, replay-атаки, неверного доступа или нарушения retention.'
    if prefix == 'PERF':
        return 'На пике вырастет latency, consumer lag, очередь, размер таблиц или число 429; система начнёт деградировать именно в момент максимальной нагрузки.'
    if prefix == 'OBS':
        return 'Инцидент нельзя будет быстро расследовать: не будет сквозного id, метрик, алертов, владельца или runbook для восстановления.'
    if prefix == 'CMP':
        return 'Не получится доказать юридически значимый шаг, провести сверку, объяснить ручное исправление или восстановить аудиторскую картину процесса.'
    if prefix == 'TST':
        return 'Критичный сценарий не попадёт в тесты: дубли, out-of-order, ошибка контракта, rollback, security-negative или нагрузочный дефект всплывут после релиза.'
    return 'Проблема проявится не на happy path, а при отказе, повторе, ручном исправлении, миграции или production-инциденте.'


def _inv_reference_case(inv):
    prefix = _inv_prefix(inv)
    if prefix == 'ID':
        return 'Универсальный адаптер отправляет запросы в системы A и B. Везде используется один ключ: requestId + operationType + targetSystem + tenantId. Именно этот ключ стоит в DDL, SELECT, UPDATE, Inbox, Outbox и replay.'
    if prefix == 'CON':
        return 'Для REST API или Kafka-события есть схема, версия, required-поля и contract tests. Тесты проверяют успешный ответ, дубль, ошибку, неизвестное enum-значение и новую версию.'
    if prefix == 'SCN':
        return 'Для заявки описаны CREATED → SENT → PROCESSING → COMPLETED/REJECTED/NEEDS_MANUAL_REVIEW. Для каждого статуса понятно, кто его выставляет и что делать при зависании.'
    if prefix == 'DAT':
        return 'Сервис-владелец пишет в свою БД и публикует событие через Transactional Outbox. Потребитель применяет Inbox и optimistic locking при обновлении проекции.'
    if prefix == 'ASY':
        return 'Consumer читает Kafka at-least-once: проверяет Inbox/idempotency key, пишет данные, коммитит offset после успеха, отправляет poison message в DLQ и имеет replay-runbook.'
    if prefix == 'API':
        return 'Клиентский API отвечает быстро: тяжёлые проверки уходят в фон с trackingId, а синхронные вызовы имеют timeout, retry budget, circuit breaker и fallback.'
    if prefix == 'EXT':
        return 'Интеграция с PSP учитывает rate limit, idempotency key, подпись callback, повторные уведомления, timeout, circuit breaker и деградацию при недоступности PSP.'
    if prefix == 'DWH':
        return 'Данные в витрину попадают через CDC/ETL вне клиентского core-flow. Есть watermark, контрольные суммы, lineage и сверка количества/сумм с источником истины.'
    if prefix == 'MIG':
        return 'Новый поток запускается в dual-run со старым, результаты сравниваются, cutover идёт по чек-листу, rollback проверен заранее.'
    if prefix == 'SEC':
        return 'Событие содержит только минимально нужные поля. ПДн маскируются в логах, DLQ и отчётах; доступ к replay и ручному исправлению ограничен ролями.'
    if prefix == 'PERF':
        return 'Для consumer group рассчитаны partitions, throughput, max lag, backpressure и retention. Нагрузочный тест покрывает средний поток, пик, стресс и длительный soak.'
    if prefix == 'OBS':
        return 'Во всех логах и событиях есть correlationId/traceId. Настроены алерты на DLQ, lag, 5xx, timeout, retry storm и зависшие статусы; есть runbook.'
    if prefix == 'CMP':
        return 'Для финансовой операции есть audit trail, ledger/status_history, сверка с внешней системой и журнал ручных исправлений с причиной, автором и временем.'
    if prefix == 'TST':
        return 'QA-план содержит контрактные тесты, duplicate delivery, out-of-order, replay из DLQ, отказ внешней системы, rollback, security-negative и нагрузочный прогон.'
    return _inv_example(inv)


def _inv_verification(inv):
    prefix = _inv_prefix(inv)
    if prefix == 'ID':
        return 'Возьмите один id и пройдите его путь: входной контракт → поиск → запись → уникальный индекс → дедупликация → replay. Если где-то используется другой набор полей, есть риск.'
    if prefix == 'CON':
        return 'Откройте контракт и тесты. Для каждого required-поля, enum, ошибки и версии должен быть автоматический тест или явный production-gate.'
    if prefix == 'SCN':
        return 'Пройдите процесс как сценарий: основной путь, отказ каждого внешнего шага, дубль, отмена, зависание, ручной разбор. У каждого состояния должен быть следующий допустимый переход.'
    if prefix == 'DAT':
        return 'Проверьте, кто пишет сущность, где транзакция, есть ли UNIQUE/locking, не расходятся ли БД и событие, что будет при двух параллельных запросах.'
    if prefix == 'ASY':
        return 'Сымитируйте повтор сообщения, падение consumer после записи, poison message, replay из DLQ и out-of-order доставку. Бизнес-дублей быть не должно.'
    if prefix == 'API':
        return 'Сложите timeout всех блокирующих шагов, проверьте 429/5xx/timeout, circuit breaker и fallback. Ответ должен укладываться в SLA или уходить в async.'
    if prefix == 'EXT':
        return 'Через sandbox/заглушку провайдера проверьте timeout, 429, дубль callback, невалидную подпись, задержку, недоступность и неизвестный результат.'
    if prefix == 'DWH':
        return 'Сравните источник истины и витрину по количеству, суммам, watermark, freshness и lineage. Проверьте, что период можно пересобрать через backfill.'
    if prefix == 'MIG':
        return 'Проведите пробный cutover и rollback, сравните dual-run, проверьте совместимость старой и новой схемы и обработку in-flight процессов.'
    if prefix == 'SEC':
        return 'Проверьте логи, DLQ, outbox, дампы, витрины, сообщения об ошибке и replay-инструменты: там не должно быть лишних ПДн/секретов и открытого доступа.'
    if prefix == 'PERF':
        return 'Запустите load/stress/soak, измерьте p95/p99, lag, saturation, размер таблиц, rate limits и поведение при деградации.'
    if prefix == 'OBS':
        return 'Возьмите один correlationId и восстановите путь через все системы, логи, метрики, алерты и дашборды. Должно быть понятно, кто чинит проблему.'
    if prefix == 'CMP':
        return 'По одной операции проверьте доказательность: кто, когда, почему изменил данные, какой был исходный источник и как результат сверяется.'
    if prefix == 'TST':
        return 'Убедитесь, что у инварианта есть конкретный тест-кейс, проверка в DoD или production-gate. Без этого пункт считается незакрытым.'
    return 'Проверьте пункт на архитектурном ревью и добавьте его в DoD, контракт или тест-кейс.'

def invariant_reference_page():
    areas = sorted({str(i.get('area') or 'Другое') for i in INVARIANT_CATALOG})
    options = ''.join(f'<option value="{escape(a.lower())}">{escape(a)}</option>' for a in areas)
    cards = []
    for inv in INVARIANT_CATALOG:
        area = str(inv.get('area') or 'Другое')
        when = _inv_when(inv)
        stage = _inv_stage(inv)
        consequence = _inv_consequence(inv)
        reference_case = _inv_reference_case(inv)
        verification = _inv_verification(inv)
        deep_description = _inv_deep_description(inv)
        normal_state = _inv_normal_state(inv)
        review_questions = _inv_review_questions(inv)
        bad_good = _inv_bad_good(inv)
        steps_to_apply = _inv_steps_to_apply(inv)
        term_hint = _inv_term_hint(inv)
        hay = ' '.join([str(inv.get(k, '')) for k in ('code', 'area', 'title', 'question', 'why', 'how', 'scope')] + [when, stage, consequence, reference_case, verification, deep_description, normal_state, review_questions, bad_good, steps_to_apply, term_hint]).lower()
        example = _inv_example(inv)
        examples = inv.get('examples') or []
        extra_examples = ''
        if examples:
            extra_examples = '<ul>' + ''.join(f'<li>{escape(str(x))}</li>' for x in examples) + '</ul>'
        cards.append(f'''<article class="refcard" data-area="{escape(area.lower())}" data-search="{escape(hay)}">
 <div><span class="refcode">{escape(inv.get('code',''))}</span><span class="refarea">{escape(area)}</span></div>
 <h3>{escape(inv.get('title','Инвариант'))}</h3>
 <div class="refbox reflead"><b>Простыми словами: что это значит</b><p>{escape(deep_description)}</p></div>
 <div class="refgrid">
  <div class="refbox"><b>Когда использовать</b><p>{escape(when)}</p></div>
  <div class="refbox"><b>На каком этапе процесса</b><p>{escape(stage)}</p></div>
 </div>
 <div class="refbox okbox" style="margin-top:10px"><b>Как выглядит правильное решение</b><p>{escape(normal_state)}</p></div>
 <div class="refbox" style="margin-top:10px"><b>Как применить по шагам</b><p>{escape(steps_to_apply)}</p></div>
 <div class="refgrid">
  <div class="refbox"><b>Что проверить</b><p>{escape(inv.get('question',''))}</p></div>
  <div class="refbox"><b>Почему это важно</b><p>{escape(inv.get('why',''))}</p></div>
 </div>
 <div class="refbox" style="margin-top:10px"><b>Плохо / правильно</b><p>{escape(bad_good)}</p></div>
 <div class="refbox" style="margin-top:10px"><b>Вопросы для ревью</b><p>{escape(review_questions)}</p></div>
 <div class="refbox" style="margin-top:10px"><b>Как закрыть</b><p>{escape(inv.get('how',''))}</p></div>
 <div class="refbox dangerbox"><b>Последствия, если не соблюдать</b><p>{escape(consequence)}</p></div>
 <div class="refexample"><b>Эталонный кейс</b><br>{escape(reference_case)}</div>
 <div class="refbox" style="margin-top:10px"><b>Как проверить на практике</b><p>{escape(verification)}</p></div>
 <div class="refexample light"><b>Пример ошибки</b><br>{escape(example)}{extra_examples}</div>
</article>''')
    important_codes = {'ID-001','ID-002','CON-001','CON-002','STAT-001','ERR-001','REL-001','REL-002','OBS-001','MIG-002'}
    important = [i for i in INVARIANT_CATALOG if i.get('code') in important_codes]
    top_cards = ''.join(
        f'<div class="refbox"><b>{escape(i.get("code",""))} · {escape(i.get("title",""))}</b><br>{escape(_inv_example(i))}</div>'
        for i in important
    )
    body = titleblock('СПРАВОЧНИК ИНВАРИАНТОВ · ЧТО НЕЛЬЗЯ ЗАБЫТЬ') + f'''
<section class="hero">
 <h2>Справочник архитектурных инвариантов</h2>
 <p>Инвариант — это универсальная проверка, которая должна оставаться верной в любом нормальном интеграционном решении. Справочник написан как практическая шпаргалка: что это значит простыми словами, когда применять, как выглядит плохое и правильное решение, какие последствия будут, как проверить и какие вопросы задать на ревью.</p>
 <div class="navlinks"><a href="/">Вернуться в конструктор процесса</a></div>
</section>
<section class="card">
 <h2>Как пользоваться</h2>
 <p>Откройте нужную область или найдите термин: например, <b>operUid</b>, <b>retry</b>, <b>DLQ</b>, <b>eventVersion</b>, <b>rollback</b>. Каждый пункт теперь построен одинаково: простое объяснение, когда применять, этап процесса, правильное состояние, пошаговое применение, плохой/хороший вариант, последствия, проверка на практике и пример ошибки.</p>
 <h3>10 инвариантов, которые чаще всего ломают интеграции</h3>
 <div class="top10">{top_cards}</div>
 <div class="refbar">
  <input id="inv_q" placeholder="Поиск по справочнику: ключ, retry, Kafka, ПДн, rollback..." oninput="filterInvariants()">
  <select id="inv_area" onchange="filterInvariants()"><option value="">Все области</option>{options}</select>
 </div>
 <p class="hint" id="inv_count">Показаны все инварианты.</p>
 <div class="refempty" id="inv_empty">По таким условиям ничего не найдено. Попробуйте другой термин или выберите «Все области».</div>
</section>
<section class="card">
 <h2>Список инвариантов</h2>
 {''.join(cards)}
</section>
<script>
function filterInvariants(){{
  const q=(document.getElementById('inv_q').value||'').toLowerCase().trim();
  const area=(document.getElementById('inv_area').value||'').toLowerCase();
  let shown=0,total=0;
  document.querySelectorAll('.refcard').forEach(card=>{{
    total++;
    const okq=!q || card.dataset.search.includes(q) || card.textContent.toLowerCase().includes(q);
    const oka=!area || card.dataset.area===area;
    const ok=okq&&oka;
    card.style.display=ok?'block':'none';
    if(ok) shown++;
  }});
  document.getElementById('inv_count').textContent='Показано: '+shown+' из '+total+'.';
  document.getElementById('inv_empty').style.display=shown?'none':'block';
}}
window.addEventListener('DOMContentLoaded', filterInvariants);
</script>'''
    return page('Справочник инвариантов v7.6', body)

MERMAID_HEAD = """<script>
window.addEventListener('DOMContentLoaded',function(){
  var s=document.createElement('script');
  s.src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js';
  s.onload=function(){mermaid.initialize({startOnLoad:true,theme:'neutral'})};
  s.onerror=function(){document.querySelectorAll('.mermaid').forEach(function(d){
    var p=document.createElement('pre');p.textContent=d.textContent;d.replaceWith(p);})};
  document.head.appendChild(s);});
</script>"""


def section(title, html, open_=False, anchor=''):
    o = ' open' if open_ else ''
    aid = f' id="{escape(anchor)}"' if anchor else ''
    return f'<details class="card"{o}{aid}><summary><h2>{escape(title)}</h2></summary><div class="inside">{html}</div></details>'



def _fix_link(title, text):
    data = ((title or '') + ' ' + (text or '')).lower()
    if any(x in data for x in ('ключ', 'scope', 'идентификатор', 'requestid', 'operuid', 'externalid', 'idempotency')):
        return '<a class="jumpfix" href="/#fix-lookup">Открыть поле ключей</a>'
    if any(x in data for x in ('статус', 'финальн')):
        return '<a class="jumpfix" href="/#fix-statuses">Открыть поле статусов</a>'
    if any(x in data for x in ('поле', 'контракт', 'event envelope', 'eventid', 'eventversion', 'sensitive')):
        return '<a class="jumpfix" href="/#fix-fields">Открыть поле ключевых полей</a>'
    if any(x in data for x in ('огранич', 'компромисс', 'нельзя', 'срок', 'бюджет')):
        return '<a class="jumpfix" href="/#fix-constraints">Открыть поле ограничений</a>'
    return '<a class="jumpfix" href="/">Вернуться к вводным</a>'

def result_page(rid, res):
    v, m = res['verdict'], res['model']['meta']
    comp = res.get('completeness') or {'summary': 'Полнота вводных не рассчитана.', 'missing': []}
    gates = res.get('quality_gates') or {'readiness': 'не рассчитано', 'gates': [], 'overall': 'warn'}
    checklist = res.get('checklist') or {'items': [], 'counters': {}}
    artifacts = res.get('artifacts') or {}
    finding_groups = res.get('finding_groups') or [
        {**f, 'count': 1, 'affected': [f.get('where', '')],
         'where_summary': f.get('where', ''), 'where': f.get('where', '')}
        for f in (res.get('findings') or [])
    ]
    parts = [titleblock(f'РАЗБОР {rid[:8].upper()}')]
    parts.append(f"""<div class="verdict {v['color']}">
 <h2>{escape(v['verdict'])} · {v['score']}/10</h2>
 <p>Готовность к production: {escape(gates.get('readiness','не рассчитано'))}. {escape(comp.get('summary',''))}<br>
 Классы рисков: критичные — {v.get('group_counts',{}).get('critical', v['counts']['critical'])}, высокие — {v.get('group_counts',{}).get('high', v['counts']['high'])}, средние — {v.get('group_counts',{}).get('medium', v['counts']['medium'])}. Всего срабатываний правил: {sum(v['counts'].values())}<br>
 <a href="/run/{rid}.md">скачать полный Markdown-отчёт</a> · <a href="/">начать новый разбор</a> · <a href="/invariants">справочник инвариантов</a></p>
</div>""")
    parts.append('<nav class="resultnav" aria-label="Навигация по результату">\n <a href="#main-actions">Главное</a>\n <a href="#checklist">Риски и чек-листы</a>\n <a href="#scenario-base">Сценарий</a>\n <a href="#artifacts">Артефакты</a>\n</nav>')

    action_items = []
    for i in checklist.get('items') or []:
        if i.get('status') == 'fail':
            action_items.append(('Чек-лист', i.get('fix') or i.get('title')))
    for i in comp.get('missing') or []:
        if i.get('priority') == 'high':
            action_items.append(('Уточнить вводные', i.get('question')))
    for f in finding_groups:
        if f.get('severity') == 'critical':
            suffix = f" Затронуто мест: {f.get('count')}." if f.get('count', 1) > 1 else ''
            action_items.append(('Критичный риск', (f.get('fix') or '') + suffix))
    seen, top = set(), []
    for area, text in action_items:
        text = (text or '').strip()
        if text and text not in seen:
            seen.add(text); top.append((area, text))
        if len(top) >= 6:
            break
    if top:
        actions_html = '<div class="actions">' + ''.join(f'<div class="action"><b>{escape(a)}</b><br>{escape(t)}{_fix_link(a, t)}</div>' for a, t in top) + '</div>'
    else:
        actions_html = '<p>Блокирующих первоочередных действий не найдено. Всё равно проверьте контракт, тесты и эксплуатационные требования.</p>'
    parts.append(section('Что сделать в первую очередь', actions_html, True, 'main-actions'))

    gate_html = []
    for gate in gates.get('gates', []):
        issues = (gate.get('fail') or gate.get('warn') or [])[:4]
        issue_txt = '<br>'.join(escape(x) for x in issues) if issues else 'Блокирующих замечаний нет.'
        gate_html.append(f"""<div class="gate {escape(gate['status'])}">
 <b><span class="st {escape(gate['status'])}">{escape(STATUS_RU.get(gate['status'], gate['status']))}</span> {escape(gate['name'])}</b>
 <p>{issue_txt}</p></div>""")
    parts.append(section('Проверка готовности к production', f'<div class="gates">{"".join(gate_html)}</div>', True))

    miss = comp.get('missing') or []
    if miss:
        rows = ''.join(
            f'<tr><td><span class="st {"fail" if i["priority"]=="high" else "warn" if i["priority"]=="medium" else "unknown"}">{escape(i["priority"])}</span></td>'
            f'<td>{escape(i["area"])}</td><td>{escape(i["question"])}</td><td>{escape(i["why"])}</td></tr>'
            for i in miss)
        miss_html = f'<table class="check"><thead><tr><th>Приоритет</th><th>Область</th><th>Что нужно уточнить</th><th>Почему это важно</th></tr></thead><tbody>{rows}</tbody></table>'
    else:
        miss_html = '<p>Критичных пропусков во вводных не найдено. При этом ревью контрактов и тест-плана всё равно нужно.</p>'
    parts.append(section('Какие вводные нужно уточнить', miss_html, True, 'missing-inputs'))

    items = checklist.get('items') or []
    if items:
        rows = ''.join(
            f'<tr><td>{escape(i["area"])}</td><td><span class="st {escape(i["status"])}">{escape(STATUS_RU.get(i["status"], i["status"]))}</span></td>'
            f'<td><b>{escape(i["title"])}</b><br><span class="hint">{escape(i["check"])}</span></td>'
            f'<td>{escape(i["fix"])}{_fix_link(i.get("title"), i.get("fix")) if i.get("status") == "fail" else ""}</td></tr>'
            for i in items)
        counts = checklist.get('counters') or {}
        checklist_html = (f'<p class="hint">Блокируют выпуск: {counts.get("fail",0)}, требуют проверки: {counts.get("warn",0)}, '
                          f'не указано: {counts.get("unknown",0)}, OK: {counts.get("ok",0)}.</p>'
                          f'<table class="check"><thead><tr><th>Область</th><th>Статус</th><th>Что проверяется</th><th>Как закрыть пункт</th></tr></thead><tbody>{rows}</tbody></table>')
    else:
        checklist_html = '<p>Архитектурный чек-лист не рассчитан.</p>'
    parts.append(section('Обязательный архитектурный чек-лист', checklist_html, False, 'checklist'))

    radar = res.get('detail_radar') or {'summary': 'Матрица деталей не рассчитана.', 'probes': []}
    probes = radar.get('probes') or []
    if probes:
        rows = ''.join(
            f'<tr><td>{escape(i["area"])}</td><td><span class="st {escape(i["status"])}">{escape(STATUS_RU.get(i["status"], i["status"]))}</span></td>'
            f'<td><b>{escape(i["title"])}</b><br><span class="hint">{escape(i["question"])}</span></td>'
            f'<td>{escape(i["why"])}</td><td>{escape(i["how"])}' +
            (('<br><span class="hint">Примеры: ' + escape('; '.join(i.get('examples') or [])) + '</span>') if i.get('examples') else '') +
            '</td></tr>'
            for i in probes)
        radar_html = (f'<p class="hint">{escape(radar.get("summary", ""))}</p>'
                      f'<table class="check"><thead><tr><th>Область</th><th>Статус</th><th>Что проверить</th><th>Почему важно</th><th>Как закрыть</th></tr></thead><tbody>{rows}</tbody></table>')
    else:
        radar_html = '<p>Матрица деталей не рассчитана.</p>'
    parts.append(section('Матрица деталей, которые нельзя забыть', radar_html, False, 'detail-radar'))

    alt_html = []
    for alt in res.get('alternatives', []):
        changes = ''.join(f'<li>{escape(c)}</li>' for c in alt.get('changes', []))
        must_count = len([x for x in alt.get('must_close', []) if x.strip()])
        close = f'<p><b>Перед внедрением закрыть:</b> блокеры из раздела «Найденные риски». Количество классов блокеров: {must_count}.</p>' if must_count else ''
        alt_html.append(f"""<div class="alt"><h3>{escape(alt['name'])}</h3>
 <p><b>Когда применять:</b> этот вариант подходит, когда {escape(alt['when'])}</p>
 <p><b>Оценка:</b> стоимость — {escape(alt['cost'])}; надёжность — {escape(alt['reliability'])}; риск — {escape(alt['risk'])}.</p>
 <ul>{changes}</ul>{close}<p class="hint">{escape(alt.get('not_enough',''))}</p></div>""")
    parts.append(section('Варианты архитектурного решения', ''.join(alt_html) or '<p>Варианты архитектурного решения не рассчитаны.</p>', False))

    scenario = res.get('scenario') or {}
    if scenario:
        main_html = []
        for st in scenario.get('main_flow', []):
            ctrls = ''.join(f'<li>{escape(x)}</li>' for x in st.get('controls', []))
            main_html.append(f'''<div class="flowbox"><h3>{st['order']}. {escape(st['title'])}</h3>
 <div class="meta">Канал: {escape(st['channel'])} · зависит от: {escape(str(st['depends_on']))}</div>
 <p>{escape(st['what_happens'])}</p><p><b>Результат:</b> {escape(st['result'])}</p>
 <ul>{ctrls}</ul><p><b>При ошибке:</b> {escape(st['failure_handling'])}</p></div>''')
        alt_html2 = []
        for alt in scenario.get('alternative_flows', []):
            steps_html = ''.join(f'<li>{escape(x)}</li>' for x in alt.get('steps', []))
            ctrls = '; '.join(alt.get('controls', []))
            alt_html2.append(f'''<div class="flowbox"><h3>{escape(alt['name'])}</h3>
 <p><b>Когда возникает:</b> {escape(alt['trigger'])}</p><ul>{steps_html}</ul>
 <p><b>Ожидаемый результат:</b> {escape(alt['result'])}</p><p class="hint">Контроли: {escape(ctrls)}</p></div>''')
        err_html = []
        for err in scenario.get('error_flows', [])[:10]:
            count = f' · затронуто мест: {err.get("affected_count")}' if err.get('affected_count',1)>1 else ''
            err_html.append(f'''<div class="flowbox"><h3>{escape(err['name'])}{escape(count)}</h3>
 <div class="meta">{escape(err.get('where',''))}</div><p><b>Что может пойти не так:</b> {escape(err['failure'])}</p>
 <p><b>Как должно обрабатываться:</b> {escape(err['expected_handling'])}</p></div>''')
        tasks = ''.join(f'<li>{escape(x)}</li>' for x in scenario.get('development_tasks', []))
        acc = ''.join(f'<li>{escape(x)}</li>' for x in scenario.get('acceptance_criteria', []))
        scen_html = f'''<p class="hint">Рекомендуемая статусная модель: {escape(', '.join(scenario.get('statuses', [])))}</p>
 <h3>Основной сценарий</h3>{''.join(main_html) or '<p>Основной сценарий не рассчитан.</p>'}
 <h3>Альтернативные сценарии</h3>{''.join(alt_html2) or '<p>Альтернативные сценарии не рассчитаны.</p>'}
 <h3>Ошибки, которые нужно учесть</h3>{''.join(err_html) or '<p>Ошибочные сценарии не рассчитаны.</p>'}
 <div class="two"><div><h3>Перенести в разработку</h3><ol class="tests">{tasks}</ol></div>
 <div><h3>Критерии приёмки</h3><ol class="tests">{acc}</ol></div></div>'''
    else:
        scen_html = '<p>Сценарная основа не рассчитана.</p>'
    parts.append(section('Сценарная основа для разработки', scen_html, False, 'scenario-base'))

    fhtml = []
    last = None
    for f in finding_groups:
        if f['severity'] != last:
            last = f['severity']
            fhtml.append(f'<p><span class="badge b-{f["severity"]}">{SEVERITY_RU[f["severity"]]}</span></p>')
        affected = f.get('affected') or []
        affected_preview = affected[:12]
        tail = len(affected) - len(affected_preview)
        affected_html = ''
        if f.get('count', 1) > 1:
            items = ''.join(f'<li>{escape(x)}</li>' for x in affected_preview)
            if tail > 0:
                items += f'<li>Ещё затронуто мест: {tail}.</li>'
            affected_html = f'<details><summary>Показать затронутые места</summary><ul>{items}</ul></details>'
        count_txt = f' · затронуто мест: {f.get("count")}' if f.get('count', 1) > 1 else ''
        fhtml.append(f"""<div class="finding {f['severity']}">
 <h3>{escape(f['title'])}</h3><div class="where">{escape(f.get('where_summary') or f.get('where') or '—')}{escape(count_txt)} · {escape(f['category'])} · {escape(f['rule'])}</div>
 <p><b>Почему это важно:</b> {escape(f['why'])}</p><p><b>Что нужно сделать:</b> {escape(f['fix'])}</p>{_fix_link(f.get('title'), f.get('fix'))}{affected_html}</div>""")
    if not finding_groups:
        fhtml.append('<p>Структурных проблем не обнаружено. Это не отменяет ревью контрактов, тестов и эксплуатационных требований.</p>')
    parts.append(section('Найденные риски и слабые места', ''.join(fhtml), True, 'risk-list'))

    pats = ''.join(
        f'<div class="pat"><b>{escape(p["name"])}</b> — {escape(p["why"])}<br><span class="ctl">обязательные контроли: {escape("; ".join(p["controls"]))}</span></div>'
        for p in res['patterns']) or '<p>Дополнительные архитектурные паттерны не требуются по текущим вводным.</p>'
    parts.append(section('Рекомендуемые архитектурные паттерны', pats, False, 'patterns'))

    parts.append(section('Карта процесса и последовательность взаимодействий',
                         f'<div class="mermaid">{escape(res["diagrams"]["flow"])}</div><div class="mermaid">{escape(res["diagrams"]["sequence"])}</div>', False))

    parts.append(section('Предлагаемая структура базы данных',
                         f'<p class="hint">В проекте могут понадобиться следующие таблицы: {escape(", ".join(res["schema"]["tables"]))}</p><pre>{escape(res["schema"]["ddl"])}</pre>', False))

    dor = ''.join(f'<li>{escape(x)}</li>' for x in artifacts.get('definition_of_ready', []))
    dod = ''.join(f'<li>{escape(x)}</li>' for x in artifacts.get('definition_of_done', []))
    mon = ''.join(f'<li>{escape(x)}</li>' for x in artifacts.get('monitoring', []))
    contract = artifacts.get('event_contract_skeleton') or {}
    contract_txt = '\n'.join(f'{k}: {v}' for k, v in contract.items())
    artifacts_html = f"""<div class="two"><div><h3>Definition of Ready</h3><ol class="tests">{dor}</ol></div>
 <div><h3>Definition of Done</h3><ol class="tests">{dod}</ol></div></div>
 <h3>Мониторинг и эксплуатационные метрики</h3><ol class="tests">{mon}</ol>
 <h3>Черновик контракта события</h3><pre>{escape(contract_txt)}</pre>"""
    parts.append(section('Проектные артефакты для аналитика и команды', artifacts_html, False, 'artifacts'))

    tests = ''.join(f'<li>{escape(t)}</li>' for t in res['tests'])
    parts.append(section('Чек-лист проверок и тестов', f'<ol class="tests">{tests}</ol>', False))

    return page(f"Разбор: {m['name']}", ''.join(parts), MERMAID_HEAD)
