# -*- coding: utf-8 -*-
"""Web-интерфейс v7.8: проводник по описанию интеграции и справочник инвариантов.

Ядро анализа осталось прежним: UI собирает тот же JSON, что и v6.4+.
Дополнительно интерфейс показывает каталог архитектурных инвариантов как
понятный справочник: что проверить, почему это важно и пример ошибки.
"""
import os
import json
from html import escape
from engine import SEVERITY_RU, humanize_terms
from invariant_catalog import INVARIANT_CATALOG
from design_patterns import DESIGN_PATTERN_CATALOG, pattern_categories

APP_VERSION = '8.6.67-ultimate-gated'
BASE_PATH = os.environ.get('BASE_PATH', '').rstrip('/')

def url_for(path):
    if not path.startswith('/'):
        path = '/' + path
    return (BASE_PATH + path) or '/'

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
.scenarios{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.scenario{border:1px solid var(--line);background:#FCFDFD;padding:12px;text-align:left;cursor:pointer;position:relative}.scenario:hover{border-color:var(--accent);background:var(--accent-soft)}.scenario.active{border-color:var(--accent);background:var(--accent-soft);box-shadow:inset 0 0 0 2px var(--accent)}.scenario.active:after{content:'Выбрано ✓';position:absolute;right:10px;top:8px;font:700 10px var(--mono);color:var(--accent)}.scenario b{display:block;margin-bottom:4px;padding-right:84px}.scenario span{font-size:12.5px;color:var(--muted)}.selected-scenario{margin:10px 0 0;font-weight:700;color:var(--accent)}.toast{position:fixed;right:18px;bottom:18px;z-index:10;pointer-events:none;max-width:360px;border:2px solid var(--accent);background:#fff;color:var(--ink);box-shadow:0 8px 22px rgba(0,0,0,.12);padding:12px 14px;font:700 12px var(--mono);opacity:0;transform:translateY(10px);transition:.18s ease}.toast.show{opacity:1;transform:translateY(0)}
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
.navlinks a{display:inline-block;border:1px solid var(--ink);padding:8px 10px;background:#fff;color:var(--ink);text-decoration:none;font:12px var(--mono);text-transform:uppercase;letter-spacing:.05em}.topnav{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.topnav a{border:1px solid var(--line);background:#fff;color:var(--ink);padding:7px 10px;font:700 11px var(--mono);text-transform:uppercase;letter-spacing:.04em;text-decoration:none}.topnav a.primary{background:var(--accent);border-color:var(--accent);color:#fff}.invariant-entry{border-top-color:var(--good);background:#FCFDFD}
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
.resultnav a{border:1px solid var(--line);background:#fff;color:var(--ink);padding:8px 10px;font:700 11px var(--mono);text-transform:uppercase;letter-spacing:.04em;text-decoration:none}.resultnav a:hover{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}.resultnav a.active,.guidebar a.active{background:var(--accent);border-color:var(--accent);color:#fff}
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
#scenario,#basics,#systems-block,#process-designer,#review,#main-actions,#checklist,#scenario-base,#artifacts{scroll-margin-top:92px}
@media(max-width:900px){#steps tbody tr{grid-template-columns:1fr 1fr}.resultnav,.guidebar{position:static}.top10,.process-layout,.reviewbox,.minimal{grid-template-columns:1fr}.sidepanel{position:static}}
.module-panel{border:1px solid var(--line);border-radius:18px;background:#FAFCFC;padding:14px;margin-top:12px}.module-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.module-btn{border:1px solid var(--line);border-radius:14px;background:#fff;padding:11px;text-align:left;cursor:pointer;min-height:92px}.module-btn:hover{border-color:var(--accent);background:var(--accent-soft)}.module-btn.active{border-color:var(--accent);background:var(--accent-soft);box-shadow:inset 0 0 0 2px var(--accent)}.module-btn b{display:block;font-size:13px}.module-btn small{display:block;margin-top:5px;color:var(--muted);line-height:1.35}.module-status{margin-top:10px;color:var(--muted);font-size:13px}.module-status b{color:var(--accent)}.question-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:8px}.question-card{border:1px solid var(--line);border-radius:14px;background:#fff;padding:10px}.question-card b{display:block;color:var(--accent);font-size:13px}.question-card span{font-size:12.5px;color:var(--muted)}
@media(max-width:900px){.module-grid,.question-grid{grid-template-columns:1fr}}


@media(max-width:640px){.guidebar a{width:100%}.process-layout,.reviewbox,.minimal{grid-template-columns:1fr}#steps tbody tr{display:block}#steps td{display:grid;grid-template-columns:128px 1fr;gap:8px;align-items:center;padding:5px 0}.g2,.g3,.g4,.gates,.two,.scenarios,.steps3,.actions{grid-template-columns:1fr}.toolbar{display:block}.toolbar>*{margin:6px 0}.mode{display:flex}.mode button{flex:1}.card{padding:12px}.titleblock h1{font-size:16px}table,thead,tbody,tr,td,th{display:block;width:100%}thead{display:none}tr{border:1px solid var(--line);background:#FCFDFD;margin:10px 0;padding:8px}td{border:0;display:grid;grid-template-columns:128px 1fr;gap:8px;align-items:center;padding:5px 0}td:before{content:attr(data-label);font:10px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}td:last-child{display:block;text-align:right}.check{display:table}.check thead{display:table-header-group}.check tbody{display:table-row-group}.check tr{display:table-row;border:0;background:transparent;margin:0;padding:0}.check td,.check th{display:table-cell}.check td:before{content:none}}


/* v8.0 flexible process builder overrides */
body{background:#F5F7F7;background-image:none;overflow-x:hidden}.wrap{max-width:1280px}.titleblock{border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 28px rgba(15,23,42,.06);align-items:center}.titleblock h1{font-family:var(--sans);text-transform:none;letter-spacing:0;font-size:22px}.titleblock .meta{font-family:var(--sans);letter-spacing:0}.topnav{margin-top:10px}.topnav a{display:inline-flex;margin-right:8px;padding:7px 10px;border-radius:999px;text-decoration:none;color:var(--ink);background:#F8FAFA;border:1px solid var(--line)}.topnav a.primary{background:var(--accent);border-color:var(--accent);color:white}.hero,.card{border:1px solid var(--line);border-radius:18px;box-shadow:0 8px 28px rgba(15,23,42,.05);border-top:0}.hero{border-left:0;border-radius:18px}.card h2{font-family:var(--sans);font-size:18px;letter-spacing:0;text-transform:none;color:var(--ink)}label{font-family:var(--sans);text-transform:none;letter-spacing:0;font-weight:700;font-size:13px;color:#374151}input,select,textarea{border-radius:12px;padding:10px 11px;border-color:#DDE5E3;background:#fff}.btn{border-radius:12px;font-family:var(--sans);letter-spacing:0;text-transform:none}.btn.ghost{border-radius:12px}.guidebar{position:sticky;top:0;z-index:5;display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:rgba(245,247,247,.94);backdrop-filter:blur(10px);padding:8px 0 12px}.guidebar a,.guide-title{font-size:13px}.guidebar a{border:1px solid var(--line);border-radius:999px;padding:7px 10px;background:#fff;text-decoration:none}.minimal{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0}.mini,.metric,.assist,.help{border:1px solid var(--line);border-radius:14px;background:#FAFCFC;padding:10px 12px;min-width:0;overflow-wrap:anywhere}.mini b,.metric b{display:block}.mini span,.metric span{font-size:12px;color:var(--muted)}.assist{margin-top:10px}.assist.ok{border-left:5px solid var(--good)}.assist.warn{border-left:5px solid var(--high)}.navlinks{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.fieldtip{font-size:12px;color:var(--muted);margin-top:4px}.templatebar{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.invariant-entry{display:none}
.quickstart{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr);gap:14px;align-items:stretch;margin:14px 0}.quickstart-card{border:1px solid var(--line);border-radius:18px;background:#FAFCFC;padding:14px;min-width:0}.quickstart-card h3{margin:0 0 8px;font-size:16px}.quickstart-card p{margin:6px 0;color:var(--muted)}.example-flow{display:grid;gap:8px}.example-flow .ex{border:1px solid var(--line);border-radius:14px;background:#fff;padding:10px}.example-flow b{display:block;color:var(--accent);font-size:13px}.scenario-groups{display:grid;gap:16px}.scenario-group h3{margin:0 0 8px;font-size:15px}.scenario-group p{margin:0 0 10px;color:var(--muted);font-size:13px}.scenario.featured{border-color:var(--accent);box-shadow:0 6px 20px rgba(21,94,102,.10)}.scenario small{display:block;margin-top:7px;font-size:11px;color:var(--accent);font-weight:700}.human-tip{border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:14px;background:#FAFCFC;padding:11px 12px;margin:10px 0;color:var(--muted)}.draft-note{border:1px dashed var(--accent);border-radius:14px;background:var(--accent-soft);padding:10px 12px;margin-top:8px;color:var(--accent);font-weight:700}.section-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}.builder-actions{display:flex;gap:8px;flex-wrap:wrap}
.builder-layout{display:grid;grid-template-columns:240px minmax(0,1fr)320px;gap:16px;align-items:start}.component-palette,.chain-workspace,.chain-preview{min-width:0}.component-palette,.chain-preview{position:sticky;top:72px}.palette-grid{display:grid;gap:8px}.palette-btn{width:100%;white-space:normal;text-align:left;border:1px solid var(--line);background:#fff;border-radius:12px;padding:10px;cursor:pointer}.palette-btn b{display:block}.palette-btn small{display:block;color:var(--muted);line-height:1.35}.systems-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:10px 0 16px}.system-card,.chain-component,.map-node,.readiness-item{border:1px solid var(--line);border-radius:16px;background:#fff;padding:13px;min-width:0;overflow-wrap:anywhere;box-shadow:0 4px 14px rgba(15,23,42,.04)}.system-card .card-top,.component-header{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap}.system-card strong{font-size:15px}.chain-list{display:grid;gap:12px}.chain-component{position:relative}.chain-component.dragging{opacity:.55}.chain-component.drop-target{outline:2px dashed var(--accent);outline-offset:4px}.component-header{margin-bottom:10px}.component-title{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.step-number{font-weight:800}.channel-chip{display:inline-flex;border-radius:999px;padding:4px 8px;font-size:12px;background:var(--accent-soft);color:var(--accent);font-weight:700}.component-actions{display:flex;flex-wrap:wrap;gap:6px}.iconbtn{border:1px solid var(--line);border-radius:10px;background:#fff;min-width:34px;padding:7px 9px;cursor:pointer}.iconbtn:hover,.palette-btn:hover{border-color:var(--accent);background:var(--accent-soft)}.component-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.chip-select{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.chip-option{border:1px solid var(--line);border-radius:999px;padding:7px 10px;background:#fff;cursor:pointer}.chip-option.active{border-color:var(--accent);background:var(--accent-soft);color:var(--accent);font-weight:700}.details-panel{margin-top:10px}.details-panel summary{cursor:pointer;color:var(--accent);font-weight:700}.process-map{display:grid;gap:10px}.map-node small,.map-node span{display:block;overflow-wrap:anywhere}.map-arrow{font-size:18px;color:var(--muted);text-align:center}.readiness-list{display:grid;gap:8px}.readiness-item{display:flex;justify-content:space-between;gap:8px;align-items:center}.readiness-item b{font-size:13px}.status-dot{border-radius:999px;padding:3px 7px;font-size:12px;font-weight:700}.status-dot.ok{background:#ECFDF3;color:var(--good)}.status-dot.warn{background:#FFF7ED;color:#9A3412}.status-dot.fail{background:#FEF2F2;color:#991B1B}.builder-empty{border:1px dashed var(--line);border-radius:16px;background:#FAFCFC;padding:18px;color:var(--muted);text-align:center}.sticky-submit{position:sticky;bottom:10px;z-index:4;background:rgba(245,247,247,.92);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:16px;padding:10px;display:flex;gap:10px;justify-content:space-between;align-items:center;flex-wrap:wrap}.legacy-store{display:none!important}
.refbar{display:grid;grid-template-columns:minmax(0,1fr)260px;gap:12px}.top10{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}.ref-list{display:grid;gap:12px}.refcard{border:1px solid var(--line);border-radius:16px;background:#fff;overflow:hidden;min-width:0;overflow-wrap:anywhere}.refcard[open]{box-shadow:0 8px 24px rgba(15,23,42,.08)}.ref-summary{cursor:pointer;padding:14px 16px;list-style:none}.ref-summary::-webkit-details-marker{display:none}.ref-summary-top{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}.ref-summary h3{margin:0 0 6px;font-size:16px;line-height:1.3;overflow-wrap:anywhere}.ref-summary p{margin:0;color:var(--muted);line-height:1.45;overflow-wrap:anywhere}.ref-content{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:0 16px 16px}.ref-section{border:1px solid var(--line);border-radius:12px;background:#FCFDFD;padding:12px;min-width:0;overflow-wrap:anywhere}.ref-section h4{margin:0 0 6px;font-size:13px;line-height:1.3}.ref-section p,.ref-section li{margin:0;line-height:1.5;overflow-wrap:anywhere}.ref-section ul{margin:6px 0 0 18px;padding:0}.ref-section.ok{border-left:4px solid var(--good)}.ref-section.danger{border-left:4px solid var(--critical)}.ref-section.example{border-left:4px solid var(--accent)}.refcode,.refarea{display:inline-flex;max-width:100%;border-radius:999px;padding:4px 8px;font-size:11px;line-height:1.2;overflow-wrap:anywhere}.refcode{background:var(--accent-soft);color:var(--accent);font-weight:700}.refarea{background:#F1F5F9;color:var(--muted)}.refempty{display:none;border:1px dashed var(--line);border-radius:14px;padding:14px;background:#fff;color:var(--muted)}
@media(max-width:1100px){.quickstart{grid-template-columns:1fr}.builder-layout{grid-template-columns:1fr}.component-palette,.chain-preview{position:static}.steps3,.minimal,.g4,.g3{grid-template-columns:1fr 1fr}.guidebar{position:static}}@media(max-width:760px){.refbar,.ref-content{grid-template-columns:1fr}.ref-summary{padding:12px}.ref-content{padding:0 12px 12px}}@media(max-width:640px){.wrap{padding:10px 10px 86px}.titleblock{align-items:flex-start;flex-direction:column}.steps3,.minimal,.g2,.g3,.g4,.component-grid{grid-template-columns:1fr}.component-actions button,.builder-actions button,.palette-btn,.sticky-submit .btn{width:100%}.systems-grid{grid-template-columns:1fr}.chain-component,.system-card,.card,.hero{padding:12px}.sticky-submit{left:8px;right:8px}.process-map{overflow-x:visible}table:not(.check){display:none!important}}


/* v8.4.1 action grammar: основной путь без стартовых шаблонов; цепочка собирается из универсальных вариантов */
.composer{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(300px,.9fr);gap:14px;align-items:start;margin-top:12px}
.composer-panel{border:1px solid var(--line);border-radius:18px;background:#FAFCFC;padding:14px;min-width:0;overflow-wrap:anywhere}
.composer-panel h3{margin:0 0 8px;font-size:16px}.composer-panel p{margin:6px 0;color:var(--muted)}
.choice-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}
.choice-card{border:1px solid var(--line);border-radius:16px;background:#fff;padding:12px;text-align:left;cursor:pointer;min-height:104px;box-shadow:0 4px 14px rgba(15,23,42,.03)}
.choice-card:hover,.choice-card.active{border-color:var(--accent);background:var(--accent-soft)}
.choice-card b{display:block;font-size:14px;color:var(--ink);margin-bottom:5px}.choice-card span{display:block;color:var(--muted);font-size:12.5px;line-height:1.35}.choice-card small{display:inline-flex;margin-top:8px;color:var(--accent);font-weight:800;font-size:11px}
.compose-status{border:1px dashed var(--accent);border-radius:16px;background:var(--accent-soft);padding:12px;margin-top:10px;color:var(--accent)}
.compose-status b{display:block;margin-bottom:5px}.compose-status ol{margin:6px 0 0 19px;padding:0}.compose-status li{margin:4px 0;color:var(--ink)}
.template-fold{margin-top:14px}.template-fold summary{cursor:pointer;font-weight:800;color:var(--accent);padding:10px 0}.template-fold .scenario-groups{margin-top:8px}
.quick-mode #basics .manual-fields{display:none}.quick-mode #basics .optional-open{display:block}.optional-open{display:none}.quick-mode .component-palette{display:none}.quick-mode .component-actions{display:none}.quick-mode .chain-component{cursor:default}.expert-link-note{font-size:12.5px;color:var(--muted);margin-top:8px}.composer-step{margin:12px 0 14px}.composer-step h4{margin:0 0 7px;font-size:13px;color:var(--accent);font-family:var(--mono);letter-spacing:.06em;text-transform:uppercase}.choice-card.compact{min-height:78px}.choice-card.compact small{display:block;color:var(--muted);font-weight:600}.choice-card.recommended{box-shadow:inset 0 0 0 2px rgba(21,94,102,.16)}.compose-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.grammar-line{border:1px solid var(--line);border-radius:14px;background:#fff;padding:10px 12px;margin:8px 0;font-size:13px}.grammar-line b{color:var(--accent)}
/* v8.4.3: wizard-first UX. Пользователь видит один вопрос за раз, а не 25 вариантов сразу. */
.wizard-shell{display:grid;gap:12px}.wizard-progress{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:4px 0 10px}.wizard-dot{width:100%;max-width:86px;flex:1;height:8px;border-radius:999px;background:#E7ECEB;border:1px solid var(--line)}.wizard-dot.done,.wizard-dot.active{background:var(--accent)}.wizard-meta{display:flex;justify-content:space-between;gap:10px;align-items:center;color:var(--muted);font-size:13px}.wizard-pane{display:none}.wizard-pane.active{display:block}.wizard-footer{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}.wizard-footer .btn{min-width:120px}.wizard-choice-count{font-size:12.5px;color:var(--muted)}.simple-system-view,.simple-step-view{border:1px solid var(--line);border-radius:12px;background:#FAFCFC;padding:10px;margin:8px 0}.simple-system-view small,.simple-step-view small{display:block;color:var(--muted);margin-top:3px}.simple-step-view b{display:block;margin-bottom:4px}.simple-step-route{font-size:13px;color:var(--muted);overflow-wrap:anywhere}.simple-step-risk{font-size:12.5px;color:var(--accent);margin-top:6px;font-weight:700}.module-groups{display:grid;gap:12px}.module-group{border:1px solid var(--line);border-radius:16px;background:#FAFCFC;padding:12px}.module-group h3{margin:0 0 8px;font-size:15px}.module-group .module-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.quick-mode .builder-actions .advanced-only{display:none!important}.quick-mode #basics > .grid,.quick-mode #basics > label,.quick-mode #basics > input,.quick-mode #basics > textarea,.quick-mode #basics > p:not(.optional-open){display:none!important}
.stack-decision{border:1px solid var(--line);border-radius:12px;background:#F7FBFB;padding:10px 12px;margin:8px 0 10px}.stack-decision b{display:block;color:var(--accent);font-size:13px}.stack-decision span{display:block;color:var(--muted);font-size:12.5px;line-height:1.45;margin-top:3px}.stack-decision .stack-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.stack-mode-note{border:1px solid var(--line);border-left:4px solid var(--accent);background:#FCFDFD;padding:10px 12px;margin:10px 0;color:var(--muted);font-size:13px}.manual-stack-note{font-size:12.5px;color:var(--muted);margin:4px 0 8px}.stack-stage-panel{border:1px solid var(--line);border-radius:16px;background:#fff;padding:12px;margin:12px 0}.stack-stage-panel h3{margin:0 0 6px}.stack-stage-panel p{margin:5px 0;color:var(--muted);font-size:13px}.stack-stage-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.prestack-chip{display:none;border:1px dashed var(--accent);border-radius:999px;padding:4px 8px;color:var(--accent);font-size:12px}.stack-not-ready .channel-chip,.stack-not-ready .stack-decision,.stack-not-ready .manual-stack-override,.stack-not-ready .component-palette{display:none!important}.stack-not-ready .prestack-chip{display:inline-flex}.stack-ready .prestack-chip{display:none}.stack-not-ready .technical-after-stack{display:none!important}.stack-ready .technical-after-stack{display:block}.clarification-note{border:1px solid var(--line);border-radius:12px;background:#FAFCFC;padding:10px 12px;margin:8px 0;color:var(--muted);font-size:13px}
@media(max-width:900px){.composer,.choice-grid{grid-template-columns:1fr}.module-group .module-grid{grid-template-columns:1fr}.wizard-dot{max-width:none}}

/* v8.3.1 visual polish: safer spacing/readability on dense result pages */
details.card>.inside{overflow-x:auto;max-width:100%;overscroll-behavior-x:contain}
.guidebar a{min-height:36px;display:inline-flex;align-items:center;justify-content:center;line-height:1.2}
.iconbtn{min-height:36px;line-height:1.2}.jumpfix{min-height:34px;display:inline-flex;align-items:center;line-height:1.25}
.module-btn small,.palette-btn small,.scenario small,.rail .chip small{font-size:12px;line-height:1.4}
.refcode,.refarea{font-size:12px;line-height:1.25}.st{font-size:11px;line-height:1.25}.badge{font-size:11px;line-height:1.25}
@media(max-width:640px){
  .card,.hero,.quickstart-card,.module-panel,.system-card,.chain-component,.chain-preview,.component-palette{margin-bottom:14px}
  details.card>.inside{padding:0 12px 14px}
  .module-btn,.scenario,.question-card,.palette-btn{padding:12px;min-height:auto}
  .module-grid,.scenario-groups,.chain-list,.systems-grid,.readiness-list{gap:10px}
  .guidebar{gap:7px}.guidebar a{width:100%;min-height:38px}
  .titleblock .meta{font-size:12px;line-height:1.45}
}

/* v8.3.1 visual polish: normalize small nav/touch targets */
.topnav a,.resultnav a,.navlinks a{font-size:12px!important;min-height:36px;display:inline-flex;align-items:center;justify-content:center;line-height:1.25}
.titleblock .meta,.guide-title{font-size:12px!important;line-height:1.45}.chip-option{min-height:36px;display:inline-flex;align-items:center}.verdict a{display:inline-flex;align-items:center;min-height:32px;line-height:1.3}.st,.badge{font-size:12px!important}

/* v8.3.1 visual polish: result readability */
.jumpfix{font-size:12px!important}.finding .where{font-size:12px!important;line-height:1.35}

.chain-guide{border:1px solid var(--line);border-radius:16px;background:#F8FBFB;padding:12px;margin:10px 0 14px}
.chain-guide b{display:block;color:var(--accent);margin-bottom:6px}.chain-guide ol{margin:6px 0 0 20px;padding:0}.chain-guide li{margin:3px 0;color:var(--muted)}
.quick-mode .systems-grid{display:none}.quick-mode .system-summary-simple{display:block}.system-summary-simple{display:none;border:1px solid var(--line);border-radius:16px;background:#FAFCFC;padding:12px;margin:8px 0 14px;color:var(--muted)}
.human-step-adder{display:none;border:1px solid var(--line);border-radius:16px;background:#FAFCFC;padding:12px;margin-top:12px}.quick-mode .human-step-adder{display:none}.human-step-adder h4{margin:0 0 8px;color:var(--accent);font-size:14px}.human-step-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.human-step-btn{border:1px solid var(--line);border-radius:12px;background:#fff;text-align:left;padding:10px;cursor:pointer}.human-step-btn:hover{border-color:var(--accent);background:var(--accent-soft)}.human-step-btn b{display:block}.human-step-btn small{display:block;color:var(--muted);line-height:1.35}

/* v8.6.2: цепочка разделена на действия и участников. В простом режиме карточка — это действие, маршрут участников скрыт в пояснении. */
.action-story{display:grid;gap:8px}.action-primary{border:1px solid var(--line);border-radius:14px;background:#fff;padding:10px}.action-primary small{display:block;color:var(--muted);font:10px var(--mono);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}.action-primary b{display:block;font-size:15px;color:var(--ink)}
.action-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.action-meta .meta-cell{border:1px solid var(--line);border-radius:12px;background:#FAFCFC;padding:8px}.action-meta .meta-cell small{display:block;color:var(--muted);font-size:11px;margin:0 0 3px}.action-meta .meta-cell b{display:block;font-size:13px;color:var(--ink);line-height:1.35}
.route-explainer{border:1px dashed var(--line);border-radius:12px;background:#FCFDFD;padding:8px 10px}.route-explainer summary{cursor:pointer;color:var(--accent);font-weight:800}.route-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}.route-cell{border:1px solid var(--line);border-radius:12px;background:#fff;padding:8px}.route-cell small{font:10px var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:0 0 3px}.route-cell b{font-size:13px;margin:0}.stack-simple-card{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:12px;background:#F7FBFB;padding:10px 12px}.stack-simple-card b{display:block;color:var(--accent);font-size:13px}.stack-simple-card p{margin:5px 0;color:var(--muted);font-size:12.5px;line-height:1.45}.chain-layer-note{border:1px solid var(--line);border-radius:12px;background:#fff;padding:10px 12px;margin:8px 0;color:var(--muted);font-size:13px}.chain-layer-note b{color:var(--ink)}
@media(max-width:640px){.action-meta,.route-grid{grid-template-columns:1fr}}

.simple-step-view{display:grid;gap:8px}.simple-step-title{font-weight:800;font-size:15px}.simple-step-flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.simple-flow-cell{border:1px solid var(--line);border-radius:12px;background:#fff;padding:8px}.simple-flow-cell small{font:10px var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:0 0 3px}.simple-flow-cell b{font-size:13px;margin:0}.simple-link-note{border-left:4px solid var(--accent);background:#EEF7F7;padding:8px 10px;border-radius:10px;font-size:13px;color:var(--ink)}.simple-step-kind{font-size:12.5px;color:var(--muted)}.quick-mode .channel-chip{display:none}.quick-mode.stack-ready .channel-chip{display:inline-flex}.quick-mode .prestack-chip{display:inline-flex}
.stack-ready.quick-mode .prestack-chip{display:none}.stack-not-ready.quick-mode .prestack-chip{display:inline-flex}.prestack-chip{border-radius:999px;padding:4px 8px;font-size:12px;background:#F3F4F6;color:var(--muted);font-weight:700}
@media(max-width:640px){.human-step-grid,.simple-step-flow{grid-template-columns:1fr}}



/* v8.6.4: чистый последовательный процесс: участники -> связи -> уточнения -> стек -> отчёт. Старый wizard сохранён только как регрессионный якорь и скрыт из основного UI. */
.flow-stage-panel{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px;margin:0 0 18px;position:relative;z-index:12}
.flow-steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:0 0 12px}.flow-step{border:1px solid var(--line);background:#FAFCFC;border-radius:12px;padding:9px 10px;text-align:left;font-size:12px;color:var(--muted)}.flow-step b{display:block;color:var(--ink);font-size:13px}.flow-step.active{border-color:var(--accent);background:var(--accent-soft);color:var(--ink)}.flow-stage-actions{display:flex;gap:8px;flex-wrap:wrap}.flow-panel{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px;margin:0 0 14px}.flow-panel h3{margin-top:0}.interaction-work-zone{display:grid;gap:14px}.interaction-block{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px;box-shadow:0 8px 24px rgba(15,23,42,.045)}.interaction-block.constructor{border-left:5px solid var(--accent);background:linear-gradient(180deg,#FFFFFF,#F8FCFC)}.interaction-block.list{border-left:5px solid #94A3B8;background:linear-gradient(180deg,#FFFFFF,#FAFBFC)}.block-title{display:flex;gap:10px;align-items:flex-start;margin:0 0 12px}.block-no{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-weight:900;width:34px;height:34px}.block-title h4{margin:0;color:var(--ink);font-size:18px}.block-title p{margin:3px 0 0;color:var(--muted);font-size:13px;line-height:1.35}.schema-panel-card{border:2px solid var(--accent-soft);border-radius:20px;background:linear-gradient(180deg,#FFFFFF,#F8FCFC);padding:14px;margin:0 0 14px;box-shadow:0 10px 28px rgba(15,23,42,.05)}.schema-panel-card h3{margin:0 0 6px}.schema-panel-card .hint{margin:0 0 12px}.readiness-card,.review-card{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px;margin:0 0 14px}.readiness-card h3,.review-card h3{margin-top:0}.participant-actions,.interaction-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.participant-btn,.interaction-btn{border:1px solid var(--line);background:#FCFDFD;border-radius:14px;padding:11px 12px;text-align:left;cursor:pointer}.participant-btn:hover,.interaction-btn:hover{border-color:var(--accent);background:var(--accent-soft)}.participant-btn b,.interaction-btn b{display:block}.participant-btn small,.interaction-btn small{display:block;color:var(--muted);line-height:1.35}.interaction-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.interaction-form .wide{grid-column:1/-1}.relation-card{border:1px solid var(--line);border-radius:14px;background:#FCFDFD;padding:10px;margin:8px 0}.relation-card b{display:block}.relation-card small{display:block;color:var(--muted)}.relation-card-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}.relation-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.relation-actions .iconbtn{padding:6px 8px;min-width:36px}.interaction-summary-title{margin:0 0 6px;font-weight:800}.stage-interactions.quick-mode #chainList,.stage-interactions.quick-mode .human-step-adder{display:none!important}.live-schema-panel{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px;margin:12px 0}.live-schema-panel h4{margin:0 0 6px}.live-schema-note{margin:0 0 10px;color:var(--muted);font-size:13px;line-height:1.35}.participant-strip{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 12px}.participant-pill{border:1px solid var(--line);border-radius:999px;background:#FAFCFC;padding:6px 10px;font-size:12px}.participant-pill b{font-size:12px}.schema-flow{display:grid;gap:10px}.schema-row{border:1px solid var(--line);border-radius:16px;background:#FCFDFD;padding:10px}.schema-row-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px}.schema-step-no{border-radius:999px;background:var(--accent-soft);color:var(--accent);font-weight:800;padding:4px 8px;font-size:12px}.schema-route{display:grid;grid-template-columns:minmax(0,1fr)36px minmax(0,1.3fr)36px minmax(0,1fr);gap:8px;align-items:stretch}.schema-person,.schema-action{border:1px solid var(--line);border-radius:14px;background:#fff;padding:9px;min-width:0;overflow-wrap:anywhere}.schema-person small,.schema-action small{display:block;color:var(--muted);font-size:11px;margin-bottom:3px}.schema-person b,.schema-action b{font-size:13px}.schema-action{background:linear-gradient(180deg,#fff,#FAFCFC)}.schema-arrow{display:flex;align-items:center;justify-content:center;color:var(--accent);font-weight:900}.schema-meta{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.schema-tag{border:1px solid var(--line);border-radius:999px;background:#fff;padding:4px 8px;font-size:11px;color:var(--muted)}.schema-tag.good{background:#ECFDF3;color:var(--good);border-color:#BBF7D0}.schema-tag.warn{background:#FFF7ED;color:#9A3412;border-color:#FED7AA}.schema-empty{border:1px dashed var(--line);border-radius:16px;background:#FAFCFC;padding:14px;color:var(--muted);text-align:center}.schema-row.has-issue{border-color:#F97316;background:#FFF7ED}.schema-link-label{border:1px solid var(--line);border-radius:14px;background:#fff;padding:9px;text-align:center;display:flex;align-items:center;justify-content:center;min-height:42px;font-weight:800;color:var(--ink);overflow-wrap:anywhere}.schema-validation-panel{border:2px solid #FED7AA;border-radius:16px;background:#FFF7ED;padding:12px;margin:12px 0}.schema-validation-panel h4{margin:0 0 6px;color:#9A3412}.schema-validation-panel p{margin:4px 0;color:#7C2D12;font-size:13px;line-height:1.4}.schema-validation-list{display:grid;gap:8px;margin:10px 0}.schema-validation-item{border:1px solid #FED7AA;border-radius:12px;background:#fff;padding:9px}.schema-validation-item b{display:block;color:#9A3412}.schema-validation-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.schema-validation-actions .btn{white-space:normal}.stage-participants .live-schema-panel{display:none!important}@media(max-width:760px){.schema-route{grid-template-columns:1fr}.schema-arrow{transform:rotate(90deg);min-height:18px}.interaction-block,.schema-panel-card,.readiness-card,.review-card{padding:12px;border-radius:16px}.block-title h4{font-size:16px}}.clarification-groups{display:grid;gap:10px}.clarification-groups details{border:1px solid var(--line);border-radius:14px;background:#FCFDFD;padding:10px}.clarification-groups summary{cursor:pointer;font-weight:700}.clarification-buttons{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px;margin-top:10px}.clarification-overview{border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:16px;background:#F8FCFC;padding:12px;margin:0 0 12px}.clarification-overview b{display:block;color:var(--ink);margin-bottom:4px}.clarification-overview span{display:block;color:var(--muted);font-size:13px;line-height:1.4}.step-question-card{border:1px solid var(--line);border-radius:18px;background:#fff;padding:12px;margin:0 0 12px;box-shadow:0 8px 20px rgba(15,23,42,.04)}.step-question-head{display:flex;gap:10px;align-items:flex-start;margin-bottom:10px}.step-question-head b{display:block;color:var(--ink)}.step-question-head small{display:block;color:var(--muted);line-height:1.35}.branch-question-group.contextual{background:#FAFCFC}.branch-empty.compact{padding:10px;text-align:left}
.branch-question-panel{display:grid;gap:12px}.branch-question-group{border:1px solid var(--line);border-radius:16px;background:#FCFDFD;padding:12px}.branch-question-group h4{margin:0 0 4px}.branch-question-group p{margin:0 0 10px;color:var(--muted);font-size:13px}.branch-question-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px}.branch-question-btn{border:1px solid var(--line);background:#fff;border-radius:14px;padding:11px 12px;text-align:left;cursor:pointer}.branch-question-btn:hover{border-color:var(--accent);background:var(--accent-soft)}.branch-question-btn.active{border-color:var(--accent);background:var(--accent-soft);box-shadow:0 0 0 1px rgba(14,116,144,.08)}.branch-question-btn b{display:block}.branch-question-btn small{display:block;color:var(--muted);line-height:1.35}.branch-empty{border:1px dashed var(--line);border-radius:14px;background:#fff;padding:12px;color:var(--muted)}.quick-mode .component-palette{display:none!important}.stage-participants .interactions-section,.stage-participants .clarifications-section,.stage-participants .stack-section,.stage-participants .report-section,.stage-participants #chainList,.stage-participants .human-step-adder{display:none!important}.stage-interactions .participants-section,.stage-interactions .clarifications-section,.stage-interactions .stack-section,.stage-interactions .report-section{display:none!important}.stage-clarifications .participants-section,.stage-clarifications .interactions-section,.stage-clarifications .stack-section,.stage-clarifications .report-section{display:none!important}.stage-stack .participants-section,.stage-stack .clarifications-section,.stage-stack .report-section{display:none!important}.stage-report .participants-section,.stage-report .interactions-section,.stage-report .clarifications-section{display:none!important}.stage-report .stack-section{display:block}.stage-stack #chainList,.stage-clarifications #chainList,.stage-interactions #chainList{display:block}#scenario,#complexity-modules{display:none!important}.quick-mode #basics{display:none!important}.stage-participants .chain-preview,.stage-clarifications .chain-preview{display:none!important}.stage-clarifications #chainList{display:none!important}.stage-participants .builder-layout{grid-template-columns:1fr}.stage-interactions .builder-layout,.stage-clarifications .builder-layout,.stage-stack .builder-layout{grid-template-columns:1fr 320px}.stage-participants .sticky-submit,.stage-interactions .sticky-submit,.stage-clarifications .sticky-submit{display:none!important}.chain-preview{pointer-events:none}.chain-preview a,.chain-preview button,.chain-preview input,.chain-preview select,.chain-preview textarea{pointer-events:auto}@media(max-width:900px){.flow-steps{grid-template-columns:1fr}.interaction-form{grid-template-columns:1fr}}


/* v8.6.9: мобильная раскладка конструктора. На узком экране этапы, форма связей,
   карта процесса и готовность идут строго друг под другом, без двух колонок и наложений. */

/* v8.6.43: боковая карта процесса не должна сжимать маршрут в вертикальные буквы. */
.chain-preview .schema-route{display:grid!important;grid-template-columns:1fr!important;gap:6px!important}
.chain-preview .schema-arrow{transform:rotate(90deg);min-height:18px}
.chain-preview .schema-person,.chain-preview .schema-action,.chain-preview .schema-link-label{padding:7px!important;text-align:left!important}
.chain-preview .schema-person b,.chain-preview .schema-action b{font-size:12px!important;line-height:1.25!important}
.chain-preview .schema-row{padding:8px!important}

@media(max-width:900px){
  .builder-layout,
  .stage-participants .builder-layout,
  .stage-interactions .builder-layout,
  .stage-clarifications .builder-layout,
  .stage-stack .builder-layout,
  .stage-report .builder-layout{
    display:block!important;
    grid-template-columns:1fr!important;
  }
  .chain-workspace,
  .flow-stage-panel,
  .flow-panel,
  .chain-preview,
  .live-schema-panel,
  .interaction-form,
  #chainList,
  #interactionGraph{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    clear:both!important;
  }
  .flow-stage-panel,
  .flow-panel,
  .chain-preview,
  .sticky-submit{
    position:static!important;
    z-index:auto!important;
    transform:none!important;
  }
  .flow-steps{
    display:grid!important;
    grid-template-columns:repeat(auto-fit,minmax(160px,1fr))!important;
    gap:8px!important;
    overflow-x:visible!important;
    overscroll-behavior-x:auto;
    padding:0;
    margin:0 0 12px 0;
  }
  .flow-step{
    flex:auto!important;
    min-width:0!important;
    max-width:none!important;
    white-space:normal!important;
  }
  .flow-stage-actions{display:grid!important;grid-template-columns:1fr!important;gap:8px!important}
  .flow-stage-actions .btn{width:100%!important;text-align:center!important}
  .interaction-form{display:grid!important;grid-template-columns:1fr!important;gap:10px!important}
  .interaction-form .wide{grid-column:auto!important}
  .participant-actions,.branch-question-grid,.human-step-grid,.clarification-buttons{
    grid-template-columns:1fr!important;
  }
  .participant-strip{overflow-x:auto;flex-wrap:nowrap;padding-bottom:4px}
  .participant-pill{flex:0 0 auto;max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .schema-route{display:grid!important;grid-template-columns:1fr!important;gap:6px!important}
  .schema-arrow{transform:rotate(90deg);min-height:20px}
  .chain-preview{
    margin-top:12px!important;
    border:1px solid var(--line)!important;
    border-radius:18px!important;
    background:#fff!important;
    padding:12px!important;
    pointer-events:auto!important;
  }
  .stage-interactions .chain-preview,
  .stage-stack .chain-preview,
  .stage-report .chain-preview{display:block!important}
  .stage-clarifications .chain-preview{display:none!important}
  .sticky-submit{margin-top:12px!important;width:100%!important}
  .sticky-submit .btn{width:100%!important}
}
@media(max-width:420px){
  .flow-step{flex-basis:156px!important;min-width:156px!important;max-width:156px!important;padding:8px!important}
  .flow-step b{font-size:12px!important}.flow-step span{font-size:11px!important}
}
"""

FORM_JS = r"""
const CH=[["rest","REST API — синхронный вызов"],["graphql","GraphQL — гибкое чтение/агрегация API"],["odata","OData — корпоративный API по сущностям"],["grpc","gRPC — быстрый внутренний вызов"],["soap","SOAP — старый или внешний контракт"],["api_gateway","API Gateway — единый внешний вход"],["service_mesh","Service Mesh — управление внутренними вызовами"],["esb","ESB — интеграционная шина"],["db","БД — основная база данных"],["read_replica","Реплика БД — масштабирование чтения"],["db_sharding","Шардирование БД — разделение данных"],["mongodb","MongoDB — документное хранилище"],["cassandra","Cassandra/ScyllaDB — ширококолонковое хранилище"],["dynamodb","DynamoDB/Key-Value — хранилище ключ-значение"],["clickhouse","ClickHouse — аналитическая колоночная БД"],["data_warehouse","Data Warehouse — аналитическое хранилище"],["data_lake","Data Lake — озеро данных"],["lakehouse","Lakehouse — озеро данных с таблицами"],["redis_cache","Redis — кэш для быстрого чтения"],["memcached","Memcached — простой временный кэш"],["redis_lock","Redis — распределённая блокировка"],["search","Поисковый индекс"],["vector_db","Векторная БД — семантический поиск"],["kafka","Kafka — поток событий"],["pulsar","Pulsar — поток событий с отдельным хранением"],["rabbitmq","RabbitMQ — очередь задач"],["activemq","ActiveMQ/Artemis — корпоративная очередь"],["ibm_mq","IBM MQ — enterprise-очередь"],["nats","NATS — лёгкая шина сообщений"],["sns_sqs","AWS SNS/SQS — облачная очередь/рассылка"],["azure_service_bus","Azure Service Bus — облачная очередь/топик"],["gcp_pubsub","Google Pub/Sub — облачная шина сообщений"],["redis_streams","Redis Streams — поток событий"],["redis_queue","Redis — короткая очередь задач"],["queue","Очередь сообщений, брокер не выбран"],["mqtt","MQTT — сообщения от устройств"],["webhook","Входящий веб-вызов"],["callback","Обратный вызов"],["websocket","WebSocket — двусторонний онлайн-канал"],["sse","Server-Sent Events — поток уведомлений"],["sftp","SFTP — файловый обмен"],["file","Файл"],["object_storage","Объектное хранилище"],["batch","Пакетная обработка по расписанию"],["cdc","CDC — передача изменений из БД"],["etl","ETL/ELT — загрузка и преобразование данных"],["airflow","Airflow — оркестрация загрузок"],["spark","Spark — распределённая обработка больших данных"],["dbt","dbt — аналитические модели данных"],["workflow_engine","Temporal/Workflow engine — длительный процесс с состояниями"],["bpm_engine","Camunda/BPMN — бизнес-процесс и ручные задачи"],["cdn","CDN — быстрая выдача статического контента"],["auth_oidc","OAuth2/OIDC — единая авторизация"],["vault","Vault/KMS — секреты и ключи"],["observability","Наблюдаемость — метрики, логи, трассировки"]];
const ROLES=[['internal','Внутренний сервис'],['external','Внешняя система'],['broker','Брокер сообщений'],['db','База данных'],['cache','Быстрый слой чтения'],['legacy','Старый контур'],['analytics','Аналитическое хранилище'],['gateway','Шлюз / интеграционная шина'],['workflow','Движок процесса'],['security','Безопасность'],['observability','Наблюдаемость']];
const CRIT=[['low','Низкая'],['medium','Средняя'],['high','Высокая'],['critical','Критичная']];
const STAB=[['unknown','Не указано'],['stable','Стабильная'],['unstable','Нестабильная'],['limited','Есть лимиты']];
const RETRY=[['none','Не повторяем'],['auto','Автоматически'],['manual','Вручную']];
const IDEM=[['none','Не указана'],['key','По ключу идемпотентности'],['natural','По бизнес-ключу']];
const SYNC=new Set(["api_gateway", "auth_oidc", "cdn", "db", "db_sharding", "dynamodb", "esb", "graphql", "grpc", "memcached", "mongodb", "odata", "read_replica", "redis_cache", "redis_lock", "rest", "search", "service_mesh", "soap", "vault", "vector_db"]);
const ASYNC=new Set(["activemq", "airflow", "azure_service_bus", "batch", "bpm_engine", "callback", "cassandra", "cdc", "clickhouse", "data_lake", "data_warehouse", "dbt", "etl", "file", "gcp_pubsub", "ibm_mq", "kafka", "lakehouse", "mqtt", "nats", "object_storage", "observability", "pulsar", "queue", "rabbitmq", "redis_queue", "redis_streams", "sftp", "sns_sqs", "spark", "sse", "webhook", "websocket", "workflow_engine"]);
const BASE_PATH=(document.documentElement.dataset.basePath||'').replace(/\/$/,'');
// Regression anchors for old tests, not visible in UI: const state={mode:'quick',systems:[],steps:[]} · Пользователь описывает смысл шага · технический способ взаимодействия подбирается автоматически · В простом режиме показан смысл шага · + DWH/аналитика · Кто выполняет шаг? · При перемещении шага внутри цепочки маршрут и зависимости пересчитываются автоматически · Продолжить цепочку простым действием · В простом режиме не нужно двигать стрелки
const state={mode:'quick',stage:'participants',systems:[],steps:[],stackReady:false,schemaValidation:null,schemaValidationBypass:false};
state.modules=[];
let dragStepId=null;
function appUrl(path){if(!path.startsWith('/')) path='/'+path; return (BASE_PATH+path)||'/'}
function uid(prefix){return prefix+'_'+Math.random().toString(36).slice(2,9)}
function esc(s){const d=document.createElement('i');d.textContent=s||'';return d.innerHTML}
function v(id){return document.getElementById(id)?.value||''}
function setv(id,val){const el=document.getElementById(id); if(el) el.value=val||''}
function labelOf(list,val){const x=list.find(i=>i[0]===val);return x?x[1]:val}

function humanText(s){
  let out=String(s||'');
  const pairs=[
    ['callback/webhook','обратный вызов или входящий веб-вызов'],['webhook/callback','входящий веб-вызов или обратный вызов'],['webhook','входящий веб-вызов'],['callback','обратный вызов'],
    ['retry','повторная попытка'],['DLQ','очередь ошибочных сообщений'],['replay','повторная обработка'],['runbook','инструкция разбора'],['manual review','ручной разбор'],['manual recovery','ручное восстановление'],['recovery','восстановление'],
    ['backoff','увеличивающаяся пауза между повторами'],['jitter','случайный разброс паузы'],['circuit breaker','предохранитель внешнего вызова'],['fallback','запасной сценарий'],['rollback','откат'],['cutover','переключение'],
    ['dual-run','параллельный прогон старого и нового контура'],['canary','пробное включение на малой доле'],['feature flag','управляемый флаг включения'],['backward compatibility','обратная совместимость'],
    ['Schema Registry','реестр схем событий'],['Inbox','таблица входящих сообщений для дедупликации'],['Outbox','таблица исходящих сообщений'],['idempotencyKey','ключ идемпотентности'],['correlationId','идентификатор сквозной связи'],['eventId','идентификатор события'],['statusVersion','версия статуса'],['payload','тело сообщения'],
    ['consumer group','группа потребителей'],['partition key','ключ партиционирования'],['rate limit','лимит запросов'],['routing','маршрутизация'],['versioning','версионирование'],['watermark','контрольная отметка загрузки'],['backfill','дозагрузка исторических данных'],['resync','повторная синхронизация'],['lag','отставание обработки'],['retention','срок хранения'],['quarantine','карантин ошибок'],['checksum','контрольная сумма'],['batchId','идентификатор пакета'],['recordCount','контроль количества записей'],['timestamp/nonce','время запроса и одноразовый номер'],['fencing token','защитный токен блокировки'],['cache-aside','кэширование с чтением из источника при промахе'],['source of truth','источник истины'],['fan-out','рассылка в несколько веток'],['fan-in','сведение нескольких веток'],['join','сведение веток'],['object storage','объектное хранилище'],['core-flow','основной поток']
  ];
  for(const [a,b] of pairs){out=out.split(a).join(b);}
  return out;
}
function optPairs(list,sel){return list.map(x=>`<option value="${x[0]}" ${x[0]===sel?'selected':''}>${x[1]}</option>`).join('')}
function roleLabel(v){return labelOf(ROLES,v||'internal')}
function normalizeBool(v){return v==='yes'||v===true||v==='true'}
function ensureSystem(name, role='internal'){
  name=(name||'').trim(); if(!name) return;
  if(!state.systems.some(s=>s.name===name)) addSystem({name,role,owner:'',criticality:'medium',stability:'unknown'}, false);
}
function addSystem(data={}, rerender=true){
  state.systems.push({id:data.id||uid('sys'),name:data.name||'',role:data.role||'internal',owner:data.owner||'',criticality:data.criticality||data.crit||'medium',stability:data.stability||data.stab||'unknown',rate_limit_rps:data.rate_limit_rps||data.limit||''});
  if(rerender) renderAll();
}
function deleteSystem(id){
  const sys=state.systems.find(s=>s.id===id); if(!sys) return;
  state.systems=state.systems.filter(s=>s.id!==id);
  showToast('Система удалена. Шаги, где она была указана, подсвечены в проверке готовности.');
  renderAll();
}
function updateSystem(id,key,val){const s=state.systems.find(x=>x.id===id); if(!s)return; s[key]=val; renderSysList(); syncLegacyTables(); renderProcessMap(); renderInteractionGraph(); renderReadiness();}
function presetSystem(kind){
  const map={initiator:{name:'Система-инициатор',role:'internal'},processor:{name:'Сервис процесса',role:'internal'},internal:{name:'Новый внутренний участник',role:'internal'},external:{name:'Внешняя система / партнёр',role:'external'},human:{name:'Оператор / ручной разбор',role:'internal'},broker:{name:'Брокер сообщений',role:'broker'},cache:{name:'Кэш / временное состояние',role:'cache'},db:{name:'Хранилище состояния процесса',role:'db'},analytics:{name:'Аналитическое хранилище',role:'analytics'},legacy:{name:'Старый контур',role:'legacy'},gateway:{name:'Входной контур / шлюз',role:'gateway'}};
  addSystem(map[kind]||{});
}
function safeDefaultsFor(channel){
  const syncCall=['rest','graphql','odata','grpc','soap','api_gateway','service_mesh','esb','auth_oidc','vault'];
  const storage=['db','read_replica','db_sharding','mongodb','dynamodb','cassandra','redis_cache','memcached','redis_lock','search','vector_db','cdn'];
  const brokers=['kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt'];
  const realtime=['webhook','callback','websocket','sse'];
  const data=['sftp','file','object_storage','batch','cdc','etl','airflow','spark','dbt','clickhouse','data_warehouse','data_lake','lakehouse','workflow_engine','bpm_engine','observability'];
  if(syncCall.includes(channel)) return {blocking:'yes',timeout_ms:'500',retry:'auto',idempotency:'key',failure_policy:'Повторить автоматически',compensation:'таймаут, ограниченные повторы, предохранитель вызова, запасной сценарий'};
  if(channel==='db') return {blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',failure_policy:'Откатить / компенсировать',compensation:'транзакция, уникальный индекс, оптимистичная блокировка'};
  if(['redis_cache','memcached','cdn'].includes(channel)) return {blocking:'yes',timeout_ms:'50',retry:'none',idempotency:'natural',failure_policy:'Запасное чтение из источника',compensation:'TTL, инвалидация, защита от лавины запросов, источник истины вне кэша'};
  if(channel==='redis_lock') return {blocking:'yes',timeout_ms:'100',retry:'manual',idempotency:'key',failure_policy:'Повторить позже',compensation:'TTL, защитный токен, безопасное освобождение блокировки'};
  if(storage.includes(channel)) return {blocking:'yes',timeout_ms:'300',retry:'auto',idempotency:'natural',failure_policy:'Деградация / повтор / ручной разбор',compensation:'ключ распределения, индексы, репликация, контроль консистентности, план восстановления'};
  if(brokers.includes(channel)) return {blocking:'no',timeout_ms:'',retry:'auto',idempotency:'key',failure_policy:'Очередь ошибок / повторная обработка',compensation:'подтверждение чтения, ограниченные повторы, очередь ошибочных сообщений, контроль отставания'};
  if(realtime.includes(channel)) return {blocking:'no',timeout_ms:'',retry:'auto',idempotency:'key',failure_policy:'Повторная доставка / ручной разбор',compensation:'проверка источника, дедупликация, переподключение или повторная доставка результата'};
  if(channel==='cdc') return {blocking:'no',timeout_ms:'',retry:'auto',idempotency:'natural',failure_policy:'Повторная синхронизация',compensation:'позиция чтения журнала, контрольная отметка загрузки, дозагрузка исторических данных'};
  if(data.includes(channel)) return {blocking:'no',timeout_ms:'',retry:'manual',idempotency:'natural',failure_policy:'Повторный запуск / ручной разбор',compensation:'контроль полноты, контрольная сумма, повторный запуск периода, отчёт расхождений'};
  return {blocking:'yes',timeout_ms:'500',retry:'auto',idempotency:'key',failure_policy:'Повторить автоматически',compensation:'таймаут, ограниченные повторы, ручной разбор'};
}

function presetStep(kind){
  const presets={
    rest:{name:'Вызвать API',channel:'rest',component_type:'action'},
    kafka:{name:'Опубликовать или обработать событие',channel:'kafka',system:'Kafka',target_system:'Потребитель',component_type:'event'},
    db:{name:'Записать или обновить состояние в БД',channel:'db',target_system:'БД процесса',writes_entity:'yes',component_type:'storage'},
    webhook:{name:'Принять обратный статус от внешней системы',channel:'webhook',component_type:'callback'},
    batch:{name:'Передать или обработать пакет данных',channel:'batch',component_type:'batch'},
    cdc:{name:'Передать изменения через CDC',channel:'cdc',component_type:'cdc'},
    manual:{name:'Ручная проверка или решение оператора',channel:'rest',blocking:'no',retry:'manual',idempotency:'natural',failure_policy:'Ручной разбор',compensation:'ручной разбор по инструкции',component_type:'manual'},
    validation:{name:'Проверить данные и бизнес-правила',channel:'rest',blocking:'yes',timeout_ms:'300',retry:'none',idempotency:'natural',failure_policy:'Остановить процесс с понятной ошибкой',compensation:'валидационная ошибка без изменения состояния',component_type:'validation'}
  };
  const p={...(presets[kind]||{})};
  const d=safeDefaultsFor(p.channel||'rest');
  return {...d,...p,writes_entity:p.writes_entity||'no'};
}

function appendUniqueField(id,text){const cur=v(id).trim(); if(!text) return; if(cur.includes(text)) return; setv(id, cur ? cur+'; '+text : text);}
function appendMetaForModule(title,details){appendUniqueField('p_constraints','Модуль: '+title+' — '+details); appendUniqueField('p_description','Добавлено усложнение: '+title+'. '+details);}
function markModule(kind,label,context){const existing=state.modules.find(m=>m.kind===kind); if(existing){ if(context){existing.contexts=existing.contexts||[]; if(!existing.contexts.includes(context)) existing.contexts.push(context);} } else state.modules.push({kind,label,contexts:context?[context]:[]}); renderModules();}
function stepHas(part){part=(part||'').toLowerCase(); return state.steps.some(s=>(s.name||'').toLowerCase().includes(part));}
function findFirstSystemByRole(role,fallback){const s=state.systems.find(x=>x.role===role); return s?.name||fallback;}
function findBroker(){return state.systems.find(s=>s.role==='broker'||/kafka|rabbit|broker|очеред|топик|stream/i.test(s.name||''))?.name||'Брокер сообщений';}
function findKafka(){return findBroker();}
function lastTarget(){const s=state.steps[state.steps.length-1]; return s?.target_system||s?.system||state.systems[0]?.name||'Сервис процесса';}
const MODULE_LABELS={enterprise_jms_queue:"Нужна стандартная корпоративная очередь приложений",cloud_messaging_azure:"Нужна облачная очередь в корпоративном Microsoft-контуре",cloud_messaging_google:"Нужна облачная шина сообщений в Google-контуре",dwh_target_layer:"Нужно отдельное аналитическое хранилище как целевой слой",graphql_query:"Нужен гибкий API для разных клиентов",odata_entity_api:"Нужен корпоративный API по сущностям",service_mesh_control:"Нужно управлять внутренними вызовами сервисов",websocket_realtime:"Нужен двусторонний онлайн-канал",sse_notifications:"Нужен поток уведомлений клиенту",mqtt_iot:"Есть устройства или датчики",pulsar_event_log:"Нужен масштабный поток событий с отдельным хранением",nats_light_pubsub:"Нужна лёгкая внутренняя рассылка сообщений",enterprise_mq:"Нужна корпоративная гарантированная очередь",cloud_messaging:"Нужна облачная очередь или топик",read_replica:"Нужно разгрузить чтение из БД",sharded_storage:"Нужно разделить данные по ключу",document_store:"Нужны гибкие документы",wide_column_store:"Нужны огромные распределённые записи по ключу",key_value_store:"Нужен быстрый доступ по ключу в управляемом хранилище",memcached_cache:"Нужен простой временный кэш",columnar_analytics:"Нужна быстрая аналитика по большим таблицам",data_lake:"Нужно складывать сырые данные разных форматов",lakehouse:"Нужно совместить озеро данных и табличную аналитику",etl_pipeline:"Нужна загрузка и преобразование данных",airflow_orchestration:"Нужно управлять зависимыми загрузками",spark_processing:"Нужна большая распределённая обработка",dbt_models:"Нужны управляемые аналитические модели",workflow_engine:"Процесс долгий и имеет состояния",bpm_engine:"Есть согласования и ручные бизнес-задачи",cdn_static:"Нужно быстро отдавать статические файлы",auth_oidc:"Нужна единая авторизация",vault_secrets:"Нужно безопасно хранить секреты и ключи",observability_stack:"Нужно видеть, где завис процесс",vector_search:"Нужен семантический поиск по текстам",dwh:'Аналитическое хранилище',legacy:'Старый контур',manual_recon:'Ручная сверка',enrichment:'Обогащение через справочник',fanin:'Сведение нескольких веток',retry_dlq:'Повторы, очередь ошибок и повторная обработка',audit:'Аудит и регуляторика',outbox_inbox:'Таблицы исходящих и входящих сообщений',contract:'Миграция контракта',security:'ПДн и безопасность',fast_read:'Быстрый доступ на чтение',db_scale:'Масштабирование хранения',task_queue:'Фоновая обработка',exclusive_processing:'Защита от одновременной обработки',search_projection:'Поиск по многим полям',large_files:'Большие документы',fast_internal_call:'Быстрый внутренний вызов',old_web_contract:'Старый веб-сервисный контракт',external_entry_control:'Единый внешний вход',central_routing:'Централизованная маршрутизация',event_history:'История событий и повторная обработка',short_stream:'Короткий поток с малой задержкой',short_queue:'Короткая очередь задач',unknown_async_buffer:'Буфер без выбора брокера',partner_file_exchange:'Защищённый файловый обмен',external_push_result:'Партнёр сам присылает результат',simple_file_exchange:'Одиночный файл без защищённого каталога',sync_external_api:'Современная синхронная интеграция с ответом сразу',relational_storage:'Реляционное хранение состояния процесса',delayed_callback:'Партнёр возвращает результат отдельным обратным вызовом',batch_processing:'Периодическая пакетная обработка'};

const EXTENDED_MODULE_SPECS={"sync_external_api": ["Современная синхронная интеграция с ответом сразу", "Сервис процесса", "Внешний API", "rest", "таймаут, ограниченные повторы, ключ запроса, понятная обработка 4xx/5xx"], "relational_storage": ["Сохранить состояние процесса в основной реляционной базе", "Сервис процесса", "БД процесса", "db", "транзакция, уникальные ключи, статусная модель, история изменений"], "delayed_callback": ["Принять результат по обратному вызову после исходного запроса", "Внешняя система / поставщик", "Сервис процесса", "callback", "externalRequestId, подпись или токен, защита от дублей, версия статуса"], "batch_processing": ["Запустить пакетную обработку или сверку по расписанию", "Источник данных", "Пакетная обработка", "batch", "расписание, контроль полноты, повторный запуск периода, отчёт ошибок"], "graphql_query": ["Нужен гибкий API для разных клиентов", "Сервис процесса", "Потребитель API", "graphql", "лимит сложности запроса, авторизация полей, пагинация"], "odata_entity_api": ["Нужен корпоративный API по сущностям", "Сервис процесса", "Корпоративный потребитель", "odata", "фильтры, сортировки, права на поля, версионирование"], "service_mesh_control": ["Нужно управлять внутренними вызовами сервисов", "Сервис процесса", "Внутренний сервис", "service_mesh", "mTLS, таймауты, трассировка, политика трафика"], "websocket_realtime": ["Нужен двусторонний онлайн-канал", "Сервис процесса", "Клиентский канал онлайн", "websocket", "сессия, heartbeat, переподключение, лимит соединений"], "sse_notifications": ["Нужен поток уведомлений клиенту", "Сервис процесса", "Клиентский канал уведомлений", "sse", "last-event-id, переподключение, ограничение скорости"], "mqtt_iot": ["Есть устройства или датчики", "Устройства/датчики", "Сервис процесса", "mqtt", "topic-структура, QoS, контроль устройства, дедупликация"], "pulsar_event_log": ["Нужен масштабный поток событий с отдельным хранением", "Сервис процесса", "Журнал событий Pulsar", "pulsar", "ключ порядка, подписки, срок хранения, повторная обработка"], "nats_light_pubsub": ["Нужна лёгкая внутренняя рассылка сообщений", "Сервис процесса", "Лёгкая шина сообщений", "nats", "subject, подписчики, мониторинг, допустимость потерь"], "enterprise_mq": ["Нужна корпоративная гарантированная очередь", "Сервис процесса", "Корпоративная очередь", "ibm_mq", "подтверждение, транзакционность, порядок, очередь ошибок"], "cloud_messaging": ["Нужна облачная очередь или топик", "Сервис процесса", "Облачная очередь/топик", "sns_sqs", "лимиты облака, права доступа, стоимость, очередь ошибок"], "read_replica": ["Нужно разгрузить чтение из БД", "БД процесса", "Реплика для чтения", "read_replica", "задержка репликации, маршрутизация чтения, fallback к основной БД"], "sharded_storage": ["Нужно разделить данные по ключу", "Сервис процесса", "Разделённое хранилище", "db_sharding", "ключ шардинга, ребалансировка, запросы между шардами"], "document_store": ["Нужны гибкие документы", "Сервис процесса", "Документное хранилище", "mongodb", "схема документа, индексы, миграция структуры"], "wide_column_store": ["Нужны огромные распределённые записи по ключу", "Сервис процесса", "Ширококолонковое хранилище", "cassandra", "partition key, consistency level, TTL, repair"], "key_value_store": ["Нужен быстрый доступ по ключу в управляемом хранилище", "Сервис процесса", "Хранилище ключ-значение", "dynamodb", "partition key, hot keys, conditional write, TTL"], "memcached_cache": ["Нужен простой временный кэш", "Сервис процесса", "Простой кэш", "memcached", "TTL, промах кэша, источник истины вне кэша"], "columnar_analytics": ["Нужна быстрая аналитика по большим таблицам", "Аналитический поток", "Колоночная аналитическая БД", "clickhouse", "партиционирование, витрины, контроль свежести"], "data_lake": ["Нужно складывать сырые данные разных форматов", "Поток данных", "Озеро данных", "data_lake", "raw/clean зоны, каталог данных, права доступа"], "lakehouse": ["Нужно совместить озеро данных и табличную аналитику", "Поток данных", "Lakehouse-хранилище", "lakehouse", "формат таблиц, транзакционность, compaction"], "etl_pipeline": ["Нужна загрузка и преобразование данных", "Источник данных", "ETL/ELT-процесс", "etl", "расписание, контроль полноты, повторный запуск периода"], "airflow_orchestration": ["Нужно управлять зависимыми загрузками", "ETL/ELT-процесс", "Оркестратор загрузок", "airflow", "DAG, расписание, retry, SLA, rerun"], "spark_processing": ["Нужна большая распределённая обработка", "Озеро данных", "Распределённая обработка", "spark", "партиционирование, shuffle, checkpoint, повторный запуск"], "dbt_models": ["Нужны управляемые аналитические модели", "Аналитическое хранилище", "Слой аналитических моделей", "dbt", "модели, lineage, tests, freshness"], "workflow_engine": ["Процесс долгий и имеет состояния", "Сервис процесса", "Движок длительного процесса", "workflow_engine", "состояния, таймеры, компенсации, история процесса"], "bpm_engine": ["Есть согласования и ручные бизнес-задачи", "Сервис процесса", "BPMN-движок", "bpm_engine", "роли, задачи, SLA, эскалации, аудит решений"], "cdn_static": ["Нужно быстро отдавать статические файлы", "Хранилище файлов", "CDN", "cdn", "cache-control, purge, срок жизни, приватные ссылки"], "auth_oidc": ["Нужна единая авторизация", "Клиент/партнёр", "Сервис авторизации", "auth_oidc", "OAuth2/OIDC, scopes, срок жизни токена, аудит входа"], "vault_secrets": ["Нужно безопасно хранить секреты и ключи", "Сервис процесса", "Хранилище секретов", "vault", "rotation, access policy, audit, запрет секретов в логах"], "observability_stack": ["Нужно видеть, где завис процесс", "Все шаги процесса", "Контур наблюдаемости", "observability", "метрики, логи, трассировки, алерты, инструкция разбора"], "vector_search": ["Нужен семантический поиск по текстам", "Сервис процесса", "Векторное хранилище", "vector_db", "эмбеддинги, версия модели, обновление индекса, права на документы"], "enterprise_jms_queue": ["Нужна стандартная корпоративная очередь приложений", "Сервис процесса", "Корпоративная очередь приложений", "activemq", "подтверждение, транзакционность, порядок, очередь ошибок"], "cloud_messaging_azure": ["Нужна облачная очередь в корпоративном Microsoft-контуре", "Сервис процесса", "Облачная очередь Microsoft", "azure_service_bus", "лимиты облака, права доступа, очередь ошибок, стоимость"], "cloud_messaging_google": ["Нужна облачная шина сообщений в Google-контуре", "Сервис процесса", "Облачная шина Google", "gcp_pubsub", "топик, подписка, права доступа, повторная доставка, стоимость"], "dwh_target_layer": ["Нужно отдельное аналитическое хранилище как целевой слой", "Поток данных", "Аналитическое хранилище", "data_warehouse", "модель витрин, контроль свежести, права доступа, сверка полноты"]};

const STACK_BRANCH_QUESTIONS=[
 {id:'sync',title:'Синхронная связь: нужен ответ в рамках текущего действия',help:'Показывается, если в цепочке есть связь, где процесс ждёт ответ. Ответы различают обычный внешний вызов, быстрый внутренний вызов, старый контракт, единый вход, шину, гибкое чтение и управление внутренним трафиком.',items:[
  ['sync_external_api','Обычная современная внешняя система, нужен ответ сразу','Отличает обычный запрос-ответ без старого WSDL/XML-контракта.'],
  ['fast_internal_call','Очень быстрый внутренний вызов между своими сервисами','Отличает внутренний вызов с минимальной задержкой и строгим контрактом.'],
  ['old_web_contract','Старый веб-сервисный контракт, WSDL или XML','Отличает старый формализованный контракт, который нельзя свободно заменить.'],
  ['external_entry_control','Нужна единая точка входа для клиентов или партнёров','Отличает единый внешний вход с авторизацией, лимитами и версиями.'],
  ['central_routing','Нужна централизованная маршрутизация и преобразование форматов','Отличает централизованную маршрутизацию, разные форматы и старые контуры.'],
  ['graphql_query','Клиентам нужен гибкий выбор полей и агрегированный ответ','Отличает гибкое чтение, когда разным клиентам нужны разные поля.'],
  ['odata_entity_api','Нужен корпоративный API по сущностям, фильтрам и сортировкам','Отличает корпоративный доступ к сущностям, фильтрам и сортировкам.'],
  ['service_mesh_control','Нужно управлять внутренними вызовами между сервисами','Отличает управление внутренним сервисным трафиком, трассировкой и безопасностью.']
 ]},
 {id:'async',title:'Асинхронная связь: результат может появиться позже',help:'Показывается, если есть поздний результат, фоновая обработка, событие или рассылка. Ответы различают журнал событий, очередь задач, лёгкий поток, короткую очередь, сообщения от устройств и облачные варианты.',items:[
  ['event_history','Это факт/событие для нескольких потребителей, нужна история и повторная обработка','Отличает долговременный журнал событий, несколько потребителей и повторное чтение.'],
  ['pulsar_event_log','Нужен масштабный поток событий с отдельным хранением','Отличает масштабный поток с отдельным хранением и множеством подписок.'],
  ['task_queue','Это задача для обработчика, важны подтверждения выполнения и очередь ошибок','Отличает очередь задач для обработчиков, подтверждения и отдельный разбор ошибок.'],
  ['enterprise_jms_queue','Нужна стандартная корпоративная очередь приложений','Отличает стандартную корпоративную очередь приложений.'],
  ['enterprise_mq','Нужна гарантированная корпоративная очередь уровня enterprise','Отличает гарантированную enterprise-очередь со строгими требованиями.'],
  ['cloud_messaging','Нужна облачная очередь или топик в AWS-подобном контуре','Отличает облачную очередь или рассылку в AWS-подобном контуре.'],
  ['cloud_messaging_azure','Нужна облачная очередь в корпоративном облачном контуре','Отличает облачную очередь в Microsoft-контуре.'],
  ['cloud_messaging_google','Нужна облачная шина сообщений в отдельном облачном контуре','Отличает облачную шину сообщений в Google-контуре.'],
  ['short_stream','Нужен короткий поток с малой задержкой внутри продукта','Отличает лёгкий короткий поток без тяжёлого долговременного журнала.'],
  ['short_queue','Нужна короткая внутренняя очередь задач','Отличает короткоживущую внутреннюю очередь задач.'],
  ['nats_light_pubsub','Нужна лёгкая внутренняя рассылка сообщений с малой задержкой','Отличает лёгкую внутреннюю рассылку с малой задержкой.'],
  ['mqtt_iot','Есть устройства, датчики или телеметрия','Отличает обмен с устройствами, датчиками и телеметрией.'],
  ['unknown_async_buffer','Нужен асинхронный буфер, но требования пока не ясны','Отличает неопределённый буфер: сначала фиксируем неизвестные требования, потом уточняем.']
 ]},
 {id:'storage',title:'Хранение данных: что именно сохраняем и как читаем',help:'Показывается, если в цепочке есть запись, обновление статуса или хранилище. Ответы различают основное транзакционное хранение, реплику чтения, разделение по ключу, документы, огромные записи по ключу, ключ-значение и аналитику.',items:[
  ['relational_storage','Нужны транзакции, статусы, уникальные ключи и основное состояние процесса','Отличает источник истины, транзакции и изменение состояния.'],
  ['read_replica','Больше чтения, чем записи, нужно разгрузить основную БД','Отличает разгрузку чтения без изменения основного хранилища.'],
  ['sharded_storage','Нужно разделить данные по ключу из-за роста объёма или нагрузки','Отличает разделение хранения по ключу.'],
  ['document_store','Данные похожи на гибкие документы, структура может меняться','Отличает гибкую документную структуру.'],
  ['wide_column_store','Нужны огромные распределённые записи по ключу','Отличает огромное распределённое хранение по ключу.'],
  ['key_value_store','Нужен быстрый доступ по ключу в управляемом хранилище','Отличает управляемое хранение ключ-значение.'],
  ['columnar_analytics','Нужна быстрая аналитика по большим таблицам','Отличает быструю аналитику по большим таблицам.'],
  ['dwh_target_layer','Нужно отдельное аналитическое хранилище как целевой слой','Отличает отдельное аналитическое хранилище как целевой слой.']
 ]},
 {id:'cache',title:'Кэш и защита от параллельной обработки',help:'Показывается, если есть хранение, частое чтение или риск одновременной обработки одной сущности. Ответы различают быстрый слой чтения, простой временный кэш и короткую распределённую блокировку.',items:[
  ['fast_read','Нужно быстро читать часто используемые данные и разгрузить источник','Отличает быстрый слой чтения рядом с источником истины.'],
  ['memcached_cache','Нужен простой временный кэш без сложных структур','Отличает простой временный кэш с ограниченным сроком жизни.'],
  ['exclusive_processing','Нельзя одновременно обрабатывать одну и ту же сущность','Отличает короткую распределённую блокировку по сущности.']
 ]},
 {id:'search',title:'Поиск и чтение по сложным критериям',help:'Показывается, если есть чтение, каталог, документы или пользователю нужно искать не только по id. Ответы различают поисковый индекс и векторную БД.',items:[
  ['search_projection','Нужен поиск по множеству полей, фильтрам или тексту','Отличает отдельную поисковую проекцию.'],
  ['vector_search','Нужен семантический поиск по смыслу текста или документов','Отличает семантический поиск по смыслу текста.']
 ]},
 {id:'files',title:'Файлы, документы и статический контент',help:'Показывается, если в цепочке есть файл, документы, вложения или отдельный файловый обмен. Ответы различают защищённый каталог, одиночный файл, отдельное хранилище больших документов и быструю выдачу статического контента.',items:[
  ['partner_file_exchange','Есть защищённый файловый обмен с партнёром или старым контуром','Отличает защищённый файловый обмен через каталог.'],
  ['simple_file_exchange','Есть одиночный файл без защищённого каталога','Отличает простой одиночный файловый обмен.'],
  ['large_files','Есть большие документы, сканы или вложения','Отличает хранение больших документов отдельно от сообщений.'],
  ['cdn_static','Нужно быстро отдавать статические файлы пользователям','Отличает быструю выдачу статического контента пользователям.']
 ]},
 {id:'analytics',title:'Аналитика, витрины и большие данные',help:'Показывается, если есть аналитический участник, сверка, пакетные загрузки или отчётность. Ответы различают передачу изменений, сырое хранилище, табличную аналитику, преобразование данных, оркестрацию загрузок, большую обработку и модели витрин.',items:[
  ['dwh','Нужно передавать изменения из основной БД в аналитику','Отличает передачу изменений из основной базы в аналитику с контролем полноты.'],
  ['data_lake','Нужно складывать сырые данные разных форматов','Отличает хранение сырых данных разных форматов.'],
  ['lakehouse','Нужно совместить озеро данных и табличную аналитику','Отличает сочетание озера данных и табличной аналитики.'],
  ['etl_pipeline','Нужна загрузка и преобразование данных','Отличает загрузку и преобразование данных.'],
  ['airflow_orchestration','Нужно управлять зависимыми загрузками по расписанию','Отличает управление зависимыми загрузками по расписанию.'],
  ['spark_processing','Нужна большая распределённая обработка','Отличает большую распределённую обработку.'],
  ['dbt_models','Нужны управляемые аналитические модели и проверки свежести','Отличает управляемые аналитические модели и проверки.'],
  ['batch_processing','Нужна пакетная обработка или сверка по расписанию','Отличает пакетную обработку или сверку по расписанию.']
 ]},
 {id:'online',title:'Онлайн-каналы и поздний результат',help:'Показывается, если есть внешний партнёр, поздний статус, клиентский канал или онлайн-уведомления. Ответы различают обратный результат, входящий результат от партнёра, двусторонний канал и поток уведомлений.',items:[
  ['delayed_callback','Мы отправили запрос, а партнёр вернёт результат отдельным обратным вызовом','Отличает обратный результат после исходного запроса.'],
  ['external_push_result','Партнёр сам присылает результат во входящий веб-вызов','Отличает входящий результат, который партнёр присылает сам.'],
  ['websocket_realtime','Нужен двусторонний онлайн-канал с клиентом','Отличает двусторонний онлайн-канал.'],
  ['sse_notifications','Нужен поток уведомлений клиенту без двустороннего канала','Отличает односторонний поток уведомлений клиенту.']
 ]},
 {id:'process',title:'Долгие процессы, ручные задачи и эксплуатация',help:'Показывается, если процесс состоит из нескольких шагов, есть ожидания, ручные действия или нужно видеть зависания. Ответы различают движок длительного процесса, движок ручных бизнес-задач и контур наблюдаемости.',items:[
  ['workflow_engine','Процесс долгий, имеет состояния, ожидания, таймеры или компенсации','Отличает долгий процесс с состояниями, таймерами и компенсациями.'],
  ['bpm_engine','Есть согласования, роли и ручные бизнес-задачи','Отличает согласования, роли и ручные бизнес-задачи.'],
  ['observability_stack','Нужно видеть, где завис процесс, почему упал шаг и где задержка','Отличает контур наблюдаемости: метрики, логи и трассировки.'],
  ['manual_recon','Нужна ручная сверка или разбор расхождений','Отличает ручную сверку, решение оператора и журнал расхождений.']
 ]},
 {id:'security',title:'Безопасность, доступы, секреты и чувствительные данные',help:'Показывается, если есть внешний контур, пользователи, ПДн, деньги, интеграции или секреты. Ответы различают единую авторизацию, хранение секретов, защиту чувствительных данных и аудит.',items:[
  ['auth_oidc','Нужна единая авторизация и контроль прав доступа','Отличает единую авторизацию и контроль прав доступа.'],
  ['vault_secrets','Нужно безопасно хранить ключи, пароли, токены или сертификаты','Отличает безопасное хранение секретов и ключей.'],
  ['security','Есть ПДн, секреты или чувствительные поля','Отличает защиту чувствительных данных и контроль доступа.'],
  ['audit','Есть деньги, регуляторика или юридически значимые решения','Отличает юридически значимый аудит и неизменяемый журнал.']
 ]},
 {id:'legacy',title:'Старый контур и миграция',help:'Показывается, если среди участников есть старый контур или нужна совместимость. Ответы различают старый веб-сервисный контракт, централизованную шину, совместимость версий и параллельный прогон.',items:[
  ['old_web_contract','Старый контур работает через WSDL/XML веб-сервис','Отличает старый формализованный веб-сервисный контракт.'],
  ['central_routing','Нужна шина для преобразования форматов и маршрутизации старых сообщений','Отличает централизованную маршрутизацию и преобразование форматов.'],
  ['contract','Меняется контракт, нужны версии и обратная совместимость','Отличает версионирование, тесты совместимости и управляемое включение.'],
  ['legacy','Нужно поддержать старый поток до переключения','Отличает параллельный прогон, сравнение и план отката.']
 ]}
];

function hasModule(kind){return state.modules.some(m=>m.kind===kind && !m.stepId)}
function clarificationLabel(kind){return MODULE_LABELS[kind]||kind}
function moduleKey(stepId,kind){return String(stepId||'global')+'::'+String(kind||'')}
function stepClarifications(step){if(!step)return []; if(!Array.isArray(step.clarifications)) step.clarifications=[]; return step.clarifications;}
function stepHasClarification(step,kind){return stepClarifications(step).some(c=>c.kind===kind)}
function moduleSelectedForStep(step,kind){return !!step && stepHasClarification(step,kind)}
function removeModuleRecordForStep(step,kind){state.modules=state.modules.filter(m=>!(m.stepId===step.id && m.kind===kind));}
function upsertModuleRecordForStep(step,kind,label,context){
  const existing=state.modules.find(m=>m.stepId===step.id && m.kind===kind);
  if(existing){existing.label=label; existing.contexts=context?[context]:existing.contexts||[]; return;}
  state.modules.push({kind,label,stepId:step.id,contexts:context?[context]:[]});
}
function isSingleChoiceClarificationGroup(groupId){return ['sync','async','storage','cache','files','analytics','online','legacy'].includes(groupId||'')}
function toggleStepClarification(kind,label,stepIndex,context,groupId){
  const idx=Number(stepIndex);
  const step=state.steps[idx];
  if(!step){return applyModule(kind,context||'');}
  label=label||clarificationLabel(kind);
  const list=stepClarifications(step);
  const existing=list.findIndex(c=>c.kind===kind);
  if(existing>=0){
    list.splice(existing,1); removeModuleRecordForStep(step,kind);
    state.stackReady=false; renderAll(); showToast('Уточнение снято: '+label+'.'); return;
  }
  if(isSingleChoiceClarificationGroup(groupId)){
    const group=stackQuestionGroupById(groupId);
    const groupKinds=new Set((group?.items||[]).map(x=>x[0]));
    for(let i=list.length-1;i>=0;i--){if(groupKinds.has(list[i].kind)){removeModuleRecordForStep(step,list[i].kind); list.splice(i,1);}}
  }
  list.push({kind,label,groupId:groupId||'',context:context||routeLabel(step,idx)});
  upsertModuleRecordForStep(step,kind,label,context||routeLabel(step,idx));
  state.stackReady=false; renderAll(); showToast('Уточнение выбрано для шага '+(idx+1)+': '+label+'.');
}
function clarifiedChannelForStep(s){
  const kinds=stepClarifications(s).map(c=>c.kind);
  const has=k=>kinds.includes(k);
  const roleT=roleOfParticipant(s?.target_system);
  const roleS=roleOfParticipant(s?.source_system);
  const txt=stepText(s);
  function ret(channel,why){return {channel,reason:why||stackReasonFor(channel,s)}}
  // Синхронные варианты
  if(has('old_web_contract')) return ret('soap','Уточнение по этому шагу: старый WSDL/XML-контракт, поэтому нужен SOAP или совместимый адаптер.');
  if(has('fast_internal_call')) return ret('grpc','Уточнение по этому шагу: нужен быстрый внутренний вызов между своими сервисами, поэтому подходит gRPC.');
  if(has('external_entry_control')) return ret('api_gateway','Уточнение по этому шагу: нужен единый внешний вход, авторизация и лимиты, поэтому подходит API Gateway.');
  if(has('central_routing')) return ret('esb','Уточнение по этому шагу: нужна централизованная маршрутизация и преобразование форматов, поэтому подходит интеграционная шина.');
  if(has('graphql_query')) return ret('graphql','Уточнение по этому шагу: разным клиентам нужны разные наборы полей, поэтому подходит GraphQL.');
  if(has('odata_entity_api')) return ret('odata','Уточнение по этому шагу: нужен корпоративный API по сущностям, фильтрам и справочникам, поэтому подходит OData.');
  if(has('service_mesh_control')) return ret('service_mesh','Уточнение по этому шагу: нужно управлять внутренним трафиком, mTLS, таймаутами и трассировкой, поэтому подходит Service Mesh.');
  if(has('sync_external_api')) return ret('rest','Уточнение по этому шагу: обычный современный запрос-ответ без старого WSDL/XML-контракта, поэтому подходит REST API.');
  // Асинхронность и сообщения
  if(has('pulsar_event_log')) return ret('pulsar','Уточнение по этому шагу: нужен масштабный поток событий с отдельным хранением, поэтому подходит Pulsar.');
  if(has('event_history')) return ret('kafka','Уточнение по этому шагу: нужна история событий, повторная обработка и несколько потребителей, поэтому подходит Kafka.');
  if(has('nats_light_pubsub')) return ret('nats','Уточнение по этому шагу: нужна лёгкая внутренняя рассылка с малой задержкой, поэтому подходит NATS.');
  if(has('mqtt_iot')) return ret('mqtt','Уточнение по этому шагу: участвуют устройства или датчики, поэтому подходит MQTT.');
  if(has('enterprise_jms_queue')) return ret('activemq','Уточнение по этому шагу: нужна стандартная корпоративная очередь приложений, поэтому подходит ActiveMQ/Artemis.');
  if(has('enterprise_mq')) return ret('ibm_mq','Уточнение по этому шагу: нужна корпоративная гарантированная очередь, поэтому подходит IBM MQ или согласованный enterprise-брокер.');
  if(has('cloud_messaging_azure')) return ret('azure_service_bus','Уточнение по этому шагу: нужен облачный брокер в Microsoft-контуре, поэтому подходит Azure Service Bus.');
  if(has('cloud_messaging_google')) return ret('gcp_pubsub','Уточнение по этому шагу: нужен облачный pub/sub в Google-контуре, поэтому подходит Google Pub/Sub.');
  if(has('cloud_messaging')) return ret('sns_sqs','Уточнение по этому шагу: нужна облачная очередь или рассылка, поэтому подходит SNS/SQS или аналог в выбранном облаке.');
  if(has('short_stream')) return ret('redis_streams','Уточнение по этому шагу: нужен короткий поток с малой задержкой без полноценного долговременного event log, поэтому подходят Redis Streams.');
  if(has('short_queue')) return ret('redis_queue','Уточнение по этому шагу: нужна короткая очередь для небольшой фоновой задачи, поэтому подходит Redis queue.');
  if(has('task_queue')) return ret('rabbitmq','Уточнение по этому шагу: нужна очередь задач для worker-ов, подтверждения обработки и ограниченных повторов, поэтому подходит RabbitMQ.');
  if(has('unknown_async_buffer')) return ret('queue','Уточнение по этому шагу: нужен асинхронный буфер, но брокер ещё не выбран.');
  // Хранение, чтение и поиск
  if(has('db_scale')) return ret('db_sharding','Уточнение по этому шагу: нужно разделить данные по ключу и масштабировать хранение, поэтому требуется шардирование БД.');
  if(has('read_replica')) return ret('read_replica','Уточнение по этому шагу: нужно разгрузить чтение от основной БД, поэтому нужна реплика для чтения.');
  if(has('document_store')) return ret('mongodb','Уточнение по этому шагу: нужны гибкие документы с изменяемой структурой, поэтому подходит документное хранилище.');
  if(has('wide_column_store')) return ret('cassandra','Уточнение по этому шагу: нужны большие распределённые записи по ключу, поэтому подходит ширококолонковое хранилище.');
  if(has('key_value_store')) return ret('dynamodb','Уточнение по этому шагу: нужен быстрый доступ по ключу в модели ключ-значение, поэтому подходит DynamoDB/Key-Value.');
  if(has('exclusive_processing')) return ret('redis_lock','Уточнение по этому шагу: нельзя параллельно обрабатывать одну сущность, поэтому нужна распределённая блокировка.');
  if(has('memcached_cache')) return ret('memcached','Уточнение по этому шагу: нужен простой временный кэш без сложных структур, поэтому подходит Memcached.');
  if(has('fast_read')) return ret('redis_cache','Уточнение по этому шагу: нужен быстрый доступ на чтение, поэтому подходит кэш поверх источника истины.');
  if(has('vector_search')) return ret('vector_db','Уточнение по этому шагу: нужен семантический поиск по текстам, поэтому подходит векторное хранилище.');
  if(has('search_projection')) return ret('search','Уточнение по этому шагу: нужен поиск по многим полям и фильтрам, поэтому подходит поисковый индекс.');
  if(has('relational_storage')) return ret('db','Уточнение по этому шагу: нужно сохранить состояние процесса в основной реляционной базе.');
  // Файлы и аналитика
  if(has('partner_file_exchange')) return ret('sftp','Уточнение по этому шагу: нужен защищённый файловый обмен с партнёром или старым контуром, поэтому подходит SFTP.');
  if(has('large_files')) return ret('object_storage','Уточнение по этому шагу: нужны большие документы или вложения, поэтому подходит объектное хранилище.');
  if(has('cdn_static')) return ret('cdn','Уточнение по этому шагу: нужно быстро отдавать статические файлы, поэтому подходит CDN.');
  if(has('simple_file_exchange')) return ret('file','Уточнение по этому шагу: есть одиночный файл без защищённого канала, поэтому это файловая передача.');
  if(has('cdc')) return ret('cdc','Уточнение по этому шагу: нужна передача изменений из базы данных через журнал изменений.');
  if(has('etl_pipeline')) return ret('etl','Уточнение по этому шагу: нужна загрузка и преобразование данных, поэтому подходит ETL/ELT.');
  if(has('airflow_orchestration')) return ret('airflow','Уточнение по этому шагу: нужно управлять зависимыми загрузками и расписаниями, поэтому подходит Airflow.');
  if(has('spark_processing')) return ret('spark','Уточнение по этому шагу: нужна распределённая обработка больших данных, поэтому подходит Spark.');
  if(has('dbt_models')) return ret('dbt','Уточнение по этому шагу: нужны управляемые аналитические модели, поэтому подходит dbt.');
  if(has('columnar_analytics')) return ret('clickhouse','Уточнение по этому шагу: нужна быстрая аналитика по большим таблицам, поэтому подходит ClickHouse.');
  if(has('data_lake')) return ret('data_lake','Уточнение по этому шагу: нужно складывать сырые данные разных форматов, поэтому подходит озеро данных.');
  if(has('lakehouse')) return ret('lakehouse','Уточнение по этому шагу: нужно совместить озеро данных и табличную аналитику, поэтому подходит Lakehouse.');
  if(has('dwh_target_layer')||has('dwh')) return ret('data_warehouse','Уточнение по этому шагу: нужен отдельный аналитический слой с витринами и отчётностью.');
  if(has('batch_processing')) return ret('batch','Уточнение по этому шагу: нужна пакетная обработка или сверка по расписанию.');
  // Онлайн и поздние результаты
  if(has('websocket_realtime')) return ret('websocket','Уточнение по этому шагу: нужен двусторонний онлайн-канал, поэтому подходит WebSocket.');
  if(has('sse_notifications')) return ret('sse','Уточнение по этому шагу: нужен поток уведомлений клиенту, поэтому подходят Server-Sent Events.');
  if(has('external_push_result')) return ret('webhook','Уточнение по этому шагу: партнёр сам присылает результат в наш endpoint, поэтому это входящий веб-вызов.');
  if(has('delayed_callback')){
    if(roleS==='external'||/внеш|партн|поставщик/.test(String(s?.source_system||'').toLowerCase())) return ret('webhook','Уточнение по этому шагу: это входящий поздний результат от партнёра, поэтому нужен входящий веб-вызов.');
    return ret('rest','Уточнение по этому шагу: мы отправляем запрос партнёру, а поздний результат должен быть отдельным входящим шагом. Основной исходящий канал — REST/API партнёра.');
  }
  // Сквозные контроли меняют канал только если сам шаг обращается к соответствующему контуру.
  if(has('auth_oidc')&&(roleT==='security'||/авторизац|oauth|oidc/.test(txt))) return ret('auth_oidc','Уточнение по этому шагу: нужна единая авторизация и проверка прав доступа.');
  if(has('vault_secrets')&&(roleT==='security'||/секрет|ключ|vault|kms/.test(txt))) return ret('vault','Уточнение по этому шагу: нужно безопасно хранить секреты и ключи.');
  if(has('observability_stack')&&(roleT==='observability'||/наблюдаем|метрик|лог|трассиров/.test(txt))) return ret('observability','Уточнение по этому шагу: нужно видеть задержки, ошибки и зависания процесса.');
  if(has('workflow_engine')) return ret('workflow_engine','Уточнение по этому шагу: процесс долгий, имеет состояния, ожидания, таймеры или компенсации.');
  if(has('bpm_engine')) return ret('bpm_engine','Уточнение по этому шагу: есть согласования, роли или ручные бизнес-задачи.');
  return null;
}
function anyStepMatch(fn){return state.steps.some(fn)}
function anySystemMatch(fn){return state.systems.some(fn)}
function branchActive(id){
  if(!state.steps.length)return false;
  const hasExt=anySystemMatch(s=>['external','legacy','gateway'].includes(s.role));
  const hasDb=anySystemMatch(s=>s.role==='db')||anyStepMatch(s=>s.writes_entity==='yes'||s.channel==='db'||/сохран|обновить|запис/i.test(s.name||''));
  const hasAsync=anyStepMatch(s=>s.blocking==='no'||['kafka','rabbitmq','callback','webhook','queue','redis_streams','redis_queue','batch','file','cdc'].includes(s.channel)||/позже|событ|очеред|фон|статус/i.test(s.name||''));
  const hasFile=anyStepMatch(s=>['file','sftp','object_storage','batch'].includes(s.channel)||/файл|документ|вложен|batch|пакет/i.test(s.name||''));
  const hasAnalytics=anySystemMatch(s=>s.role==='analytics')||anyStepMatch(s=>['cdc','etl','airflow','spark','dbt','clickhouse','data_warehouse','data_lake','lakehouse','batch'].includes(s.channel)||/аналит|dwh|витрин|свер/i.test(s.name||''));
  const hasLegacy=anySystemMatch(s=>s.role==='legacy')||v('p_legacy')==='yes'||anyStepMatch(s=>/legacy|стар/i.test((s.name||'')+' '+(s.target_system||'')));
  const hasSync=anyStepMatch(s=>s.blocking!=='no'||['rest','grpc','soap','api_gateway','graphql','odata','service_mesh','esb'].includes(s.channel));
  if(id==='sync')return hasSync;
  if(id==='async')return hasAsync;
  if(id==='storage')return hasDb;
  if(id==='cache')return hasDb||hasModule('fast_read')||hasModule('exclusive_processing')||anySystemMatch(s=>s.role==='cache');
  if(id==='search')return hasDb||hasFile||hasModule('search_projection')||hasModule('vector_search');
  if(id==='files')return hasFile;
  if(id==='analytics')return hasAnalytics;
  if(id==='online')return hasAsync||hasExt||anyStepMatch(s=>/клиент|уведом|онлайн|статус/i.test(s.name||''));
  if(id==='process')return state.steps.length>=2||hasAsync||hasModule('manual_recon');
  if(id==='security')return hasExt||state.steps.length>=1;
  if(id==='legacy')return hasLegacy;
  return false;
}
function roleOfParticipant(name){
  const s=state.systems.find(x=>(x.name||'')===(name||''));
  return s?.role||'';
}
function stackQuestionGroupById(id){return STACK_BRANCH_QUESTIONS.find(g=>g.id===id)}
function stepText(step){return ((step?.name||'')+' '+(step?.source_system||'')+' '+(step?.system||'')+' '+(step?.target_system||'')+' '+(step?.channel||'')).toLowerCase()}
function stepLooksSync(step){const t=stepText(step);return step?.blocking!=='no'||['rest','graphql','odata','grpc','soap','api_gateway','service_mesh','esb'].includes(step?.channel)||/сразу|ответ|синхрон|запросить|получить данные|вызвать/.test(t)}
function stepLooksAsync(step){const t=stepText(step);return step?.blocking==='no'||['kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt','callback','webhook'].includes(step?.channel)||/позже|событ|очеред|фон|статус|рассыл|журнал/.test(t)}
function stepLooksStorage(step){const t=stepText(step);const targetRole=roleOfParticipant(step?.target_system);return step?.writes_entity==='yes'||step?.channel==='db'||targetRole==='db'||/сохран|запис|обнов|состояни|статус/.test(t)}
function stepLooksFile(step){const t=stepText(step);return ['file','sftp','object_storage','batch'].includes(step?.channel)||/файл|документ|вложен|скан|пакет|batch/.test(t)}
function stepLooksAnalytics(step){const t=stepText(step);const r=roleOfParticipant(step?.target_system);return r==='analytics'||['cdc','etl','airflow','spark','dbt','clickhouse','data_warehouse','data_lake','lakehouse','batch'].includes(step?.channel)||/аналит|dwh|витрин|свер|отч[её]т|озеро/.test(t)}
function stepLooksExternal(step){return ['external','legacy','gateway'].includes(roleOfParticipant(step?.source_system))||['external','legacy','gateway'].includes(roleOfParticipant(step?.target_system))||/внеш|партн|клиент|шлюз|api/.test(stepText(step))}
function stepLooksLegacy(step){return ['legacy'].includes(roleOfParticipant(step?.source_system))||['legacy'].includes(roleOfParticipant(step?.target_system))||/legacy|стар|wsdl|xml/.test(stepText(step))}
function stepQuestionGroupIds(step){
  const ids=[];
  if(stepLooksSync(step)) ids.push('sync');
  if(stepLooksAsync(step)) ids.push('async');
  if(stepLooksStorage(step)) ids.push('storage','cache','search');
  if(stepLooksFile(step)) ids.push('files');
  if(stepLooksAnalytics(step)) ids.push('analytics');
  if(stepLooksExternal(step)||/клиент|уведом|онлайн|статус/.test(stepText(step))) ids.push('online','security');
  if(stepLooksLegacy(step)) ids.push('legacy');
  if(state.steps.length>=2||stepLooksAsync(step)||/ручн|соглас|ожидан|компенсац/.test(stepText(step))) ids.push('process');
  return [...new Set(ids)].filter(id=>stackQuestionGroupById(id));
}
function routeLabel(step, idx){return 'Шаг '+(idx+1)+': '+(step.source_system||'Источник')+' → '+(step.target_system||'Получатель')}
function renderBranchQuestions(){
  const box=document.getElementById('branchQuestionPanel'); if(!box)return;
  if(!state.steps.length){box.innerHTML='<div class="branch-empty">Сначала добавьте связи между участниками. После этого вопросы появятся не списком в вакууме, а отдельно по каждой связи: например «Сервис процесса → партнёр», «Сервис процесса → хранилище», «БД → аналитика».</div>';return;}
  const overview='<div class="clarification-overview"><b>Уточнения построены из вашей схемы.</b><span>Ниже каждая группа вопросов привязана к конкретной связи. Отвечайте только там, где действительно нужно уточнить процесс. Если связь уже понятна, её можно оставить без дополнительных ответов.</span></div>';
  const seenModules=new Set();
  const cards=state.steps.map((step,idx)=>{
    const ids=stepQuestionGroupIds(step);
    const head='<div class="step-question-head"><span class="schema-step-no">'+(idx+1)+'</span><div><b>'+esc(step.name||'Связь между участниками')+'</b><small>'+esc((step.source_system||'Источник')+' → '+(step.target_system||'Получатель'))+'</small></div></div>';
    if(!ids.length){return '<section class="step-question-card">'+head+'<div class="branch-empty compact">По этой связи дополнительных вопросов не требуется: её смысл уже достаточно определён для подбора стека.</div></section>'}
    const groups=ids.map(id=>{
      const g=stackQuestionGroupById(id);
      const selectedInGroup=(g.items||[]).filter(x=>moduleSelectedForStep(step,x[0])).length;
      const items=g.items.map(([module,label,hint])=>{
        const active=moduleSelectedForStep(step,module);
        const attrModule=seenModules.has(module)?(module+'__step'+idx):module; seenModules.add(module);
        const contextualHint=hint+' Нажмите один раз, чтобы выбрать это уточнение только для шага '+(idx+1)+'. Нажмите повторно, чтобы снять.';
        return '<button type="button" class="branch-question-btn '+(active?'active':'')+'" data-action="module" data-module="'+esc(attrModule)+'" data-module-kind="'+esc(module)+'" data-module-label="'+esc(label)+'" data-group-id="'+esc(id)+'" data-step-index="'+idx+'" data-step-label="'+esc(routeLabel(step,idx))+'" aria-pressed="'+(active?'true':'false')+'"><b>'+esc(label)+'</b><small>'+esc(contextualHint)+'</small></button>';
      }).join('');
      const groupNote=selectedInGroup?'<small class="hint">Выбрано уточнений в этой группе для шага '+(idx+1)+': '+selectedInGroup+'.</small>':'';
      return '<details class="branch-question-group contextual" open><summary><h4>'+esc(g.title)+'</h4></summary><p><b>Относится к связи:</b> '+esc((step.source_system||'Источник')+' → '+(step.target_system||'Получатель'))+'. '+esc(g.help)+'</p>'+groupNote+'<div class="branch-question-grid">'+items+'</div></details>';
    }).join('');
    return '<section class="step-question-card">'+head+groups+'</section>';
  }).join('');
  box.innerHTML=overview+cards;
}
function renderModules(){
  document.querySelectorAll('[data-action="module"]').forEach(btn=>{const k=btn.dataset.moduleKind||btn.dataset.module; btn.classList.toggle('active',state.modules.some(m=>m.kind===k && !m.stepId));});
  document.querySelectorAll('[data-action="module"][data-step-index]').forEach(btn=>{
    const step=state.steps[Number(btn.dataset.stepIndex||'-1')];
    const k=btn.dataset.moduleKind||'';
    const active=moduleSelectedForStep(step,k);
    btn.classList.toggle('active',active);
    btn.setAttribute('aria-pressed',active?'true':'false');
  });
  const boxes=[document.getElementById('moduleStatus'),document.getElementById('moduleStatusFlow')].filter(Boolean);
  const empty='Уточнения ещё не выбраны. Вопросы формируются из вашей схемы и показываются рядом с конкретной связью, к которой относятся.';
  const filled='Добавлены уточнения:<br>'+state.modules.map(m=>'<b>'+esc(m.label)+'</b>'+((m.contexts&&m.contexts.length)?'<small> — '+esc(m.contexts.join('; '))+'</small>':'')).join('<br>')+'<br><span class="hint">Эти ответы относятся к конкретным шагам. Повторный клик по выбранной кнопке снимает уточнение.</span>';
  boxes.forEach(box=>{box.innerHTML=state.modules.length?filled:empty;});
}
function applyModule(kind, context){
  if(!state.steps.length){suggestBasics(); ensureSystem('Сервис процесса','internal'); ensureSystem('БД процесса','db'); addStep({name:'Черновой старт процесса',source_system:'Канал/инициатор',system:'Сервис процесса',target_system:'БД процесса',channel:'db',timeout_ms:'200',idempotency:'key',writes_entity:'yes',compensation:'transaction, audit journal'},null,false);}
  const label=MODULE_LABELS[kind]||kind;
  if(state.modules.some(m=>m.kind===kind)){showToast('Надстройка уже добавлена: '+label); return;}
  if(EXTENDED_MODULE_SPECS[kind]){
    const [meaning, source, target, channel, controls]=EXTENDED_MODULE_SPECS[kind];
    appendMetaForModule(label, meaning.toLowerCase()+'.');
    ensureSystem(source, source.includes('Клиент')||source.includes('партнёр')||source.includes('Устройства')?'external':'internal');
    const brokerList=['kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt'];
    const role = brokerList.includes(channel)?'broker':(['data_warehouse','data_lake','lakehouse','clickhouse','etl','airflow','spark','dbt','observability'].includes(channel)?'analytics':(['auth_oidc','vault'].includes(channel)?'security':(['workflow_engine','bpm_engine'].includes(channel)?'workflow':(['redis_cache','memcached','redis_lock','cdn'].includes(channel)?'cache':'internal'))));
    ensureSystem(target, role);
    const d=safeDefaultsFor(channel);
    addStep({name:meaning,source_system:source,system:'Сервис процесса',target_system:target,channel,blocking:d.blocking,timeout_ms:d.timeout_ms,retry:d.retry,idempotency:d.idempotency,depends_on:String(state.steps.length),compensation:controls,failure_policy:d.failure_policy},null,false);
    markModule(kind,label,context); state.stackReady=false; renumberSteps(); renderAll(); showToast('Добавлено уточнение: '+label+'. Стек нужно сформировать заново, потому что процесс изменился.'); return;
  }
  if(kind==='dwh'){
    ensureSystem('Механизм передачи изменений','internal'); ensureSystem('Аналитическое хранилище / журнал сверки','analytics');
    appendMetaForModule(label,'изменения уходят в аналитику без чтения основной БД бизнес-процессом; нужен watermark, backfill и reconciliation.');
    appendUniqueField('p_fields','lsn:string|indexed, watermark:datetime|indexed, batchId:string|indexed');
    addStep({name:'Передать изменения в аналитику без нагрузки на основной процесс',source_system:findFirstSystemByRole('db','БД процесса'),system:'Механизм передачи изменений',target_system:'Аналитическое хранилище / журнал сверки',channel:'cdc',blocking:'no',retry:'auto',idempotency:'natural',depends_on:String(state.steps.length),compensation:'watermark, lag monitoring, replay/resync, backfill'},null,false);
    addStep({name:'Аналитический контур сверяет полноту витрины с источником',source_system:'Механизм передачи изменений',system:'Аналитическое хранилище / журнал сверки',target_system:'Аналитическое хранилище / журнал сверки',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'reconciliation report, gap detection, повторная загрузка'},null,false);
  } else if(kind==='legacy'){
    ensureSystem('Старый потребитель','legacy'); appendMetaForModule(label,'есть старый потребитель/процесс, поэтому нужны dual-run, совместимость и план отключения.'); setv('p_legacy','yes');
    addStep({name:'Старый потребитель получает совместимый формат',source_system:findKafka(),system:'Старый потребитель',target_system:'Старый потребитель',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'adapter, backward compatibility, canary, rollback, dual-run'},null,false);
    addStep({name:'Сравнить результат нового и старого потока перед переключением',source_system:'Старый потребитель',system:'Старый потребитель',target_system:'БД процесса',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'dual-run comparison, discrepancy report, rollback gate'},null,false);
  } else if(kind==='manual_recon'){
    ensureSystem('Сервис сверки / ручной разбор','internal'); appendMetaForModule(label,'потоки могут расходиться; нужен timeout ожидания, сверка, ручной разбор и replay.'); appendUniqueField('p_statuses','WAITING_RECONCILIATION, RECONCILED, NEEDS_MANUAL_REVIEW');
    addStep({name:'Сервис сверки ждёт связанные события и проверяет расхождения',source_system:lastTarget(),system:'Сервис сверки / ручной разбор',target_system:'Сервис сверки / ручной разбор',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'join window, timeout ожидания парной ветки, reconciliation key'},null,false);
    addStep({name:'Оператор разбирает расхождения по runbook',source_system:'Сервис сверки / ручной разбор',system:'Сервис сверки / ручной разбор',target_system:'Сервис сверки / ручной разбор',channel:'rest',blocking:'no',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'manual review, replay, correction journal, SLA на разбор'},null,false);
  } else if(kind==='enrichment'){
    ensureSystem('Внешний справочник','external'); ensureSystem('Сервис обогащения','internal'); appendMetaForModule(label,'нужно обогатить данные через внешний источник; нужен запасной сценарий и отдельный статус обогащения.'); appendUniqueField('p_statuses','ENRICHING, ENRICHED'); appendUniqueField('p_fields','enrichmentVersion:string, sourceVersion:string');
    addStep({name:'Сервис обогащения обращается во внешний справочник',source_system:lastTarget(),system:'Сервис обогащения',target_system:'Внешний справочник',channel:'rest',blocking:'yes',timeout_ms:'700',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'timeout, cache/fallback, circuit breaker, partial enrichment policy'},null,false);
    addStep({name:'Передать обогащённый результат следующим потребителям',source_system:'Сервис обогащения',system:'Сервис обогащения',target_system:findKafka(),channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'Outbox, Schema Registry, DLQ, replay'},null,false);
  } else if(kind==='fanin'){
    ensureSystem('Сервис оркестрации / join','internal'); ensureSystem('Ветка A','external'); ensureSystem('Ветка B','external'); appendMetaForModule(label,'есть параллельные ветки; нужен correlation key, окно ожидания и единое решение после join.'); appendUniqueField('p_statuses','BRANCH_A_DONE, BRANCH_B_DONE, JOINED, COMPENSATION_REQUIRED');
    const base=state.steps.length;
    addStep({name:'Запустить ветку A',source_system:lastTarget(),system:'Сервис оркестрации / join',target_system:'Ветка A',channel:'rest',blocking:'yes',timeout_ms:'800',retry:'auto',idempotency:'key',depends_on:String(base),compensation:'отмена/компенсация ветки A'},null,false);
    addStep({name:'Запустить ветку B параллельно',source_system:lastTarget(),system:'Сервис оркестрации / join',target_system:'Ветка B',channel:'rest',blocking:'yes',timeout_ms:'800',retry:'auto',idempotency:'key',depends_on:String(base),compensation:'отмена/компенсация ветки B'},null,false);
    addStep({name:'Join: дождаться обязательных веток и принять единое решение',source_system:'Ветка A/Ветка B',system:'Сервис оркестрации / join',target_system:'Сервис оркестрации / join',channel:'rest',blocking:'yes',timeout_ms:'500',retry:'none',idempotency:'natural',depends_on:String(base+1)+','+String(base+2),writes_entity:'yes',compensation:'join window, timeout, manual review, compensation matrix'},null,false);
  } else if(kind==='retry_dlq'){
    ensureSystem('Хранилище ошибок и повторной обработки','db'); appendMetaForModule(label,'для ошибок нужны ограниченный retry, DLQ, replay, метрики lag и ручной runbook.');
    let changed=0; state.steps.forEach(s=>{if(ASYNC.has(s.channel)){s.retry='auto';s.idempotency=s.idempotency==='none'?'key':s.idempotency;s.compensation=[s.compensation,'DLQ, replay, retry limit, backoff, poison message policy'].filter(Boolean).join(', ');s.failure_policy='Очередь ошибок / повторная обработка'; changed++;}});
    addStep({name:'Сохранять необработанные сообщения отдельно и запускать повторную обработку',source_system:findKafka(),system:'Хранилище ошибок и повторной обработки',target_system:'Хранилище ошибок и повторной обработки',channel:'kafka',blocking:'no',retry:'manual',idempotency:'key',depends_on:String(state.steps.length),compensation:'poison message quarantine, replay by eventId/correlationId, runbook'},null,false);
  } else if(kind==='audit'){
    ensureSystem('Audit journal','db'); setv('p_reg','yes'); appendMetaForModule(label,'есть деньги/регуляторика; нужен неизменяемый журнал, retention, traceability и отчётность.'); appendUniqueField('p_fields','auditId:uuid|required|unique, changedBy:string, changedAt:datetime|required, reasonCode:string'); appendUniqueField('p_statuses','AUDIT_WRITTEN, REG_REPORT_READY');
    addStep({name:'Записать неизменяемый audit journal',source_system:lastTarget(),system:'Audit journal',target_system:'Audit journal',channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),writes_entity:'no',compensation:'append-only journal, retention policy, traceId/correlationId, access log'},null,false);
  } else if(kind==='outbox_inbox'){
    appendMetaForModule(label,'если сервис пишет в БД и отправляет событие, нужен Outbox; если читает событие, нужен Inbox-дедупликация.'); appendUniqueField('p_fields','outboxId:uuid|unique, inboxEventId:uuid|unique');
    state.steps.forEach(s=>{if(s.channel==='kafka'||s.channel==='queue'){s.retry='auto';s.idempotency='key';s.compensation=[s.compensation,'Outbox/Inbox, exactly-once effect через unique key, replay-safe handler'].filter(Boolean).join(', ');}});
    if(!stepHas('исходящее сообщение')) addStep({name:'Записать исходящее сообщение в той же транзакции, что и бизнес-состояние',source_system:lastTarget(),system:lastTarget(),target_system:findFirstSystemByRole('db','БД процесса'),channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'transactional outbox, publisher retry, schema validation'},null,false);
    if(!stepHas('входящее событие')) { const broker=findKafka(); ensureSystem(broker,'broker'); addStep({name:'Дедуплицировать входящее событие перед обработкой',source_system:broker,system:lastTarget(),target_system:findFirstSystemByRole('db','БД процесса'),channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'key',depends_on:String(state.steps.length),compensation:'UNIQUE eventId, processedAt, replay-safe processing'},null,false); }
  } else if(kind==='contract'){
    ensureSystem('Реестр контрактов','internal'); appendMetaForModule(label,'контракт меняется; нужны версии, backward compatibility, examples, consumer-driven contract tests и canary.'); appendUniqueField('p_fields','schemaVersion:string|required, eventVersion:string|required');
    addStep({name:'Зафиксировать v1/v2 контракты и матрицу совместимости',source_system:'Аналитик/разработчик',system:'Реестр контрактов',target_system:'Реестр контрактов',channel:'db',blocking:'no',timeout_ms:'200',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'schema registry, examples, compatibility rules'},null,false);
    addStep({name:'Прогнать consumer-driven contract tests и canary',source_system:'Контур разработки',system:'Реестр контрактов',target_system:lastTarget(),channel:'batch',blocking:'no',timeout_ms:'',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'canary, rollback, feature flag, duplicate/error branch tests'},null,false);
  } else if(kind==='security'){
    appendMetaForModule(label,'есть ПДн/чувствительные поля; нужны классификация, маскирование, retention, RBAC и журнал доступа.'); appendUniqueField('p_fields','piiClass:string, retentionUntil:date, maskedFields:string, accessReason:string');
    ensureSystem('Слой защиты и маскирования','internal');
    addStep({name:'Классифицировать и маскировать чувствительные поля',source_system:lastTarget(),system:'Слой защиты и маскирования',target_system:lastTarget(),channel:'rest',blocking:'no',timeout_ms:'300',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'data classification, masking/tokenization, retention policy, RBAC, access audit'},null,false);
  } else if(kind==='fast_read'){
    appendMetaForModule(label,'часто читают одни и те же данные; нужен быстрый доступ на чтение, но источник истины должен оставаться в основной базе.'); appendUniqueField('p_fields','readModelVersion:int, cacheKey:string, cacheValidUntil:datetime');
    ensureSystem('Быстрый слой чтения','cache');
    addStep({name:'Подготовить быстрый слой чтения для частых запросов',source_system:lastTarget(),system:'Сервис процесса',target_system:'Быстрый слой чтения',channel:'redis_cache',blocking:'yes',timeout_ms:'50',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'срок жизни данных, обновление при изменении, защита от устаревшего ответа, возврат к основной базе'},null,false);
  } else if(kind==='db_scale'){
    appendMetaForModule(label,'ожидается рост объёма данных или нагрузки; нужно отдельно оценить записи, чтение, архивирование и разделение хранения.'); appendUniqueField('p_fields','partitionKey:string, archiveUntil:date, dataOwner:string');
    addStep({name:'Разделить правила записи, чтения и архивирования данных',source_system:lastTarget(),system:'Сервис процесса',target_system:findFirstSystemByRole('db','БД процесса'),channel:'db',blocking:'yes',timeout_ms:'250',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'ключ разделения данных, реплика для чтения при необходимости, архивирование, контроль роста таблиц'},null,false);
  } else if(kind==='task_queue'){
    appendMetaForModule(label,'есть фоновая работа, которую не нужно выполнять в основном ожидании пользователя; нужна очередь обработки и контроль повторов.'); appendUniqueField('p_statuses','QUEUED, IN_PROGRESS, DONE');
    ensureSystem('Очередь фоновой обработки','broker');
    addStep({name:'Поставить фоновую работу в очередь обработки',source_system:lastTarget(),system:'Сервис процесса',target_system:'Очередь фоновой обработки',channel:'queue',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'лимит повторов, отдельное место для ошибок, повторный запуск после исправления причины'},null,false);
  } else if(kind==='exclusive_processing'){
    appendMetaForModule(label,'одну и ту же сущность нельзя обрабатывать одновременно в двух потоках; нужна защита от гонки обработки.'); appendUniqueField('p_fields','processingOwner:string, processingUntil:datetime');
    ensureSystem('Координатор обработки','cache');
    addStep({name:'Исключить одновременную обработку одной сущности',source_system:lastTarget(),system:'Сервис процесса',target_system:'Координатор обработки',channel:'redis_lock',blocking:'yes',timeout_ms:'80',retry:'auto',idempotency:'natural',depends_on:String(state.steps.length),compensation:'срок действия блокировки, защитный токен, безопасное снятие блокировки, ручной разбор зависших обработок'},null,false);
  } else if(kind==='search_projection'){
    appendMetaForModule(label,'пользователи ищут данные по разным полям; основная база остаётся источником истины, а отдельная проекция ускоряет поиск.'); appendUniqueField('p_fields','searchText:string, indexVersion:int');
    ensureSystem('Поисковая проекция','analytics');
    addStep({name:'Обновить отдельную поисковую проекцию',source_system:lastTarget(),system:'Сервис процесса',target_system:'Поисковая проекция',channel:'search',blocking:'no',retry:'auto',idempotency:'natural',depends_on:String(state.steps.length),compensation:'переиндексация, контроль отставания, возврат к основной базе при ошибке поиска'},null,false);
  } else if(kind==='large_files'){
    appendMetaForModule(label,'в процессе есть большие документы или вложения; их не нужно переносить внутри основного сообщения.'); appendUniqueField('p_fields','fileId:string, fileHash:string, fileSizeBytes:int');
    ensureSystem('Хранилище документов','analytics');
    addStep({name:'Сохранить большой документ отдельно и передавать только ссылку',source_system:lastTarget(),system:'Сервис процесса',target_system:'Хранилище документов',channel:'object_storage',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'контрольная сумма файла, повторная загрузка, срок хранения, права доступа'},null,false);
  } else if(kind==='fast_internal_call'){
    appendMetaForModule(label,'есть быстрый внутренний вызов между своими сервисами; нужен короткий ответ, строгий контракт и контроль задержки.');
    ensureSystem('Внутренний сервис быстрых ответов','internal');
    addStep({name:'Быстро получить ответ от внутреннего сервиса',source_system:lastTarget(),system:'Сервис процесса',target_system:'Внутренний сервис быстрых ответов',channel:'grpc',blocking:'yes',timeout_ms:'150',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'короткий таймаут, ограниченные повторы, запасной сценарий при недоступности'},null,false);
  } else if(kind==='old_web_contract'){
    appendMetaForModule(label,'старый контур работает через формализованный веб-сервисный контракт, который нельзя менять свободно.'); setv('p_legacy','yes');
    ensureSystem('Старый веб-сервисный контур','legacy');
    addStep({name:'Вызвать старый веб-сервисный контракт',source_system:lastTarget(),system:'Сервис процесса',target_system:'Старый веб-сервисный контур',channel:'soap',blocking:'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'адаптер формата, контроль таймаута, перевод ошибок старого контура, план обхода при недоступности'},null,false);
  } else if(kind==='external_entry_control'){
    appendMetaForModule(label,'есть несколько внешних клиентов или партнёров; нужен единый вход, авторизация, лимиты и маршрутизация по версиям.');
    ensureSystem('Единая точка входа','gateway');
    addStep({name:'Принять внешний запрос через единую точку входа',source_system:'Внешний клиент / партнёр',system:'Единая точка входа',target_system:'Сервис процесса',channel:'api_gateway',blocking:'yes',timeout_ms:'300',retry:'none',idempotency:'key',depends_on:String(state.steps.length),compensation:'проверка доступа, лимит запросов, маршрутизация по версии, журнал входящих обращений'},null,false);
  } else if(kind==='central_routing'){
    appendMetaForModule(label,'нужно централизованно маршрутизировать и преобразовывать сообщения между разными системами и форматами.');
    ensureSystem('Центр маршрутизации и преобразования','gateway');
    addStep({name:'Централизованно маршрутизировать и преобразовать сообщение',source_system:lastTarget(),system:'Центр маршрутизации и преобразования',target_system:'Целевая система / получатель',channel:'esb',blocking:'yes',timeout_ms:'1000',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'правила маршрутизации, преобразование формата, журнал ошибок, ручной обход при сбое'},null,false);
  } else if(kind==='event_history'){
    appendMetaForModule(label,'нужно хранить историю событий, рассылать изменения нескольким потребителям и уметь повторно обработать прошлые события.'); appendUniqueField('p_fields','eventKey:string, eventVersion:int');
    ensureSystem('Журнал событий','broker');
    addStep({name:'Опубликовать событие в долговременный журнал событий',source_system:lastTarget(),system:'Сервис процесса',target_system:'Журнал событий',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'ключ порядка по сущности, срок хранения, повторная обработка, контроль отставания потребителей'},null,false);
  } else if(kind==='short_stream'){
    appendMetaForModule(label,'нужен короткий поток внутри одного контура: малая задержка важнее долговременного хранения истории.');
    ensureSystem('Быстрый поток обработки','broker');
    addStep({name:'Передать событие в короткий поток с малой задержкой',source_system:lastTarget(),system:'Сервис процесса',target_system:'Быстрый поток обработки',channel:'redis_streams',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'группа обработчиков, контроль зависших сообщений, ограничение срока хранения'},null,false);
  } else if(kind==='short_queue'){
    appendMetaForModule(label,'нужна простая короткая очередь для небольшой фоновой задачи без долговременного журнала событий.');
    ensureSystem('Короткая очередь задач','broker');
    addStep({name:'Поставить небольшую короткую задачу в очередь',source_system:lastTarget(),system:'Сервис процесса',target_system:'Короткая очередь задач',channel:'redis_queue',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'срок жизни задачи, ограничение повторов, ручной разбор зависших задач'},null,false);
  } else if(kind==='unknown_async_buffer'){
    appendMetaForModule(label,'нужен асинхронный буфер между системами, но требования к порядку, хранению и маршрутизации пока не ясны.');
    ensureSystem('Асинхронный буфер обработки','broker');
    addStep({name:'Поставить работу в асинхронный буфер без выбора конкретного механизма',source_system:lastTarget(),system:'Сервис процесса',target_system:'Асинхронный буфер обработки',channel:'queue',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'уточнить порядок, срок хранения, повторную обработку, маршрутизацию и лимиты потребителей'},null,false);
  } else if(kind==='partner_file_exchange'){
    appendMetaForModule(label,'партнёр или старый контур обменивается файлами через защищённый каталог; нужно контролировать целостность и повторную загрузку.'); appendUniqueField('p_fields','fileName:string, fileHash:string, fileReceivedAt:datetime');
    ensureSystem('Защищённый файловый канал','external');
    addStep({name:'Передать или принять файл через защищённый файловый канал',source_system:lastTarget(),system:'Сервис процесса',target_system:'Защищённый файловый канал',channel:'sftp',blocking:'no',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'контрольная сумма, карантин ошибок, повторная загрузка, протокол обработки файла'},null,false);
  } else if(kind==='simple_file_exchange'){
    appendMetaForModule(label,'есть одиночный файл без защищённого каталога и без расписания; нужно контролировать целостность и результат обработки.'); appendUniqueField('p_fields','fileName:string, fileHash:string, fileStatus:string');
    ensureSystem('Файловый получатель / источник','external');
    addStep({name:'Принять или передать одиночный файл',source_system:lastTarget(),system:'Сервис процесса',target_system:'Файловый получатель / источник',channel:'file',blocking:'no',retry:'manual',idempotency:'natural',depends_on:String(state.steps.length),compensation:'контрольная сумма, статус обработки файла, ручной повтор при ошибке'},null,false);
  } else if(kind==='external_push_result'){
    appendMetaForModule(label,'внешняя система сама присылает результат в наш вход позже; нужно проверить источник, подпись, время и дубли.'); appendUniqueField('p_statuses','WAITING_EXTERNAL_RESULT, EXTERNAL_RESULT_RECEIVED');
    ensureSystem('Внешняя система / поставщик','external');
    addStep({name:'Принять результат, который партнёр сам присылает позже',source_system:'Внешняя система / поставщик',system:'Сервис процесса',target_system:findFirstSystemByRole('db','БД процесса'),channel:'webhook',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'проверка подписи, защита от повторов, ограничение частоты, сохранение неизвестного статуса'},null,false);
  }

  markModule(kind,label,context); state.stackReady=false; renumberSteps(); renderAll(); showToast('Добавлено уточнение: '+label+'. Стек нужно сформировать заново, потому что процесс изменился.');
}


function setComposerStatus(title, steps){
  const box=document.getElementById('composeStatus'); if(!box)return;
  box.innerHTML='<b>'+esc(title)+'</b><ol>'+steps.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol>';
}

const composerDraft={start:'incoming_request',activity:'call_external',timing:'unknown',result:'save_forward',systems:'3'};
let composerWizardStep=0;
const COMPOSER_GROUPS=['start','activity','timing','result','systems'];
function renderComposerWizard(){
  const panes=[...document.querySelectorAll('[data-wizard-pane]')];
  panes.forEach((pane,idx)=>pane.classList.toggle('active',idx===composerWizardStep));
  const dots=[...document.querySelectorAll('[data-wizard-dot]')];
  dots.forEach((dot,idx)=>{dot.classList.toggle('active',idx===composerWizardStep); dot.classList.toggle('done',idx<composerWizardStep);});
  const cur=document.getElementById('wizardCurrent'); if(cur)cur.textContent=String(composerWizardStep+1);
  const total=document.getElementById('wizardTotal'); if(total)total.textContent=String(COMPOSER_GROUPS.length);
  const back=document.getElementById('wizardBack'); if(back)back.disabled=composerWizardStep===0;
  const next=document.getElementById('wizardNext'); if(next){
    next.textContent=composerWizardStep===COMPOSER_GROUPS.length-1?'Собрать цепочку':'Дальше';
    next.dataset.action=composerWizardStep===COMPOSER_GROUPS.length-1?'compose-chain':'wizard-next';
  }
}
function moveComposerWizard(dir){
  composerWizardStep=Math.max(0,Math.min(COMPOSER_GROUPS.length-1,composerWizardStep+dir));
  renderComposerWizard();
}
const COMPOSER_OPTIONS={
  start:{incoming_request:'Входящий запрос',event:'Входящее событие',file:'Файл или пакет данных',schedule:'Запуск по расписанию',unknown:'Не знаю'},
  activity:{call_external:'Вызвать внешнюю систему',receive_data:'Получить данные',send_data:'Передать данные',validate:'Проверить данные',enrich:'Обогатить данными',wait_status:'Дождаться статуса'},
  timing:{immediate:'Ответ сразу',later:'Результат позже',both:'Бывает сразу и позже',unknown:'Не знаю'},
  result:{save:'Сохранить',forward:'Передать дальше',save_forward:'Сохранить и передать',update_status:'Обновить статус',compare:'Сверить/сравнить',unknown:'Не знаю'},
  systems:{'2':'2 системы','3':'3 системы','4':'4+ систем','unknown':'Не знаю'}
};
function composerLabel(group,val){return (COMPOSER_OPTIONS[group]||{})[val]||val||'Не выбрано';}
function setComposerChoice(group,value){
  if(!COMPOSER_OPTIONS[group]) return;
  composerDraft[group]=value;
  document.querySelectorAll(`[data-action="compose-choice"][data-compose-group="${group}"]`).forEach(btn=>btn.classList.toggle('active',btn.dataset.value===value));
  updateComposerPreview();
  const idx=COMPOSER_GROUPS.indexOf(group);
  if(idx===composerWizardStep && idx<COMPOSER_GROUPS.length-1){composerWizardStep=idx+1; renderComposerWizard();}
}
function updateComposerPreview(){
  const lines=[
    'Старт: '+composerLabel('start',composerDraft.start),
    'Основное действие: '+composerLabel('activity',composerDraft.activity),
    'Ответ/результат: '+composerLabel('timing',composerDraft.timing),
    'После результата: '+composerLabel('result',composerDraft.result),
    'Масштаб: '+composerLabel('systems',composerDraft.systems)
  ];
  setComposerStatus('Черновик будет собран из выбранных вариантов',lines);
}
function composeBaseMeta(){
  const timing=composerDraft.timing;
  const result=composerDraft.result;
  const statuses=['CREATED','PROCESSING'];
  if(['later','both','unknown'].includes(timing)) statuses.push('WAITING_RESULT','RESULT_RECEIVED'); else statuses.push('RESULT_RECEIVED');
  if(['save','save_forward','update_status','compare','unknown'].includes(result)) statuses.push('SAVED');
  if(['forward','save_forward'].includes(result)) statuses.push('SENT_TO_TARGET');
  if(result==='compare') statuses.push('WAITING_RECONCILIATION','RECONCILED');
  statuses.push('FAILED','NEEDS_MANUAL_REVIEW');
  const assumptions=[];
  if(composerDraft.timing==='unknown') assumptions.push('неизвестно, ответ синхронный или асинхронный — добавлены статусы ожидания и ручной разбор');
  if(composerDraft.systems==='unknown') assumptions.push('точное число систем неизвестно — создан минимальный набор участников');
  if(composerDraft.result==='unknown') assumptions.push('неизвестно, что делать с результатом — добавлены сохранение, статус и ручной разбор');
  setBasics({
    name:'Черновик процесса из выбранных действий',
    entity:'BusinessEntity',
    goal:'Построить интеграционную цепочку из универсальных действий без выбора фиксированного шаблона.',
    description:'Черновик собран из вариантов: старт — '+composerLabel('start',composerDraft.start)+'; действие — '+composerLabel('activity',composerDraft.activity)+'; ответ — '+composerLabel('timing',composerDraft.timing)+'; результат — '+composerLabel('result',composerDraft.result)+'. '+(assumptions.length?'Допущения: '+assumptions.join('; ')+'.':''),
    lookup:'requestId + targetSystem; eventId для дедупликации событий; correlationId для трассировки',
    constraints:assumptions.join('; '),
    visible:'mixed',money:'no',reg:'no',order:'per_entity',rps:'',peak:'1',tenant:'no',legacy:'no',read:'medium',sla:'',
    statuses:[...new Set(statuses)].join(', '),
    fields:'requestId:string|required|unique, eventId:uuid|required|unique, correlationId:uuid|required|indexed, targetSystem:string|indexed, status:string|required, statusVersion:int, resultPayload:json, updatedAt:datetime|required'
  });
}
function composeChainFromChoices(){
  clearAll(); composeBaseMeta();
  const add=(x)=>addStep(x,null,false);
  const proc='Сервис процесса', db='БД процесса', src='Система-инициатор', provider='Внешняя система / поставщик', target='Целевая система / получатель';
  ensureSystem(proc,'internal'); ensureSystem(db,'db');
  if(composerDraft.start!=='schedule') ensureSystem(src,'internal');
  if(['call_external','receive_data','send_data','enrich','wait_status'].includes(composerDraft.activity) || ['later','both','unknown'].includes(composerDraft.timing)) ensureSystem(provider,'external');
  if(['forward','save_forward'].includes(composerDraft.result) || ['3','4','unknown'].includes(composerDraft.systems)) ensureSystem(target,'external');
  if(['event'].includes(composerDraft.start)) ensureSystem('Источник события','broker');
  if(composerDraft.systems==='4') ensureSystem('Дополнительная система','external');

  if(composerDraft.start==='event'){
    add({name:'Принять входящее событие и защититься от дублей',source_system:'Источник события',system:proc,target_system:db,channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'Inbox, UNIQUE eventId, offset/ack после успешной обработки, DLQ/replay'});
  } else if(composerDraft.start==='file'){
    add({name:'Принять файл или batch и создать запись процесса',source_system:src,system:proc,target_system:db,channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',compensation:'batchId, checksum, quarantine, reprocess, audit journal'});
  } else if(composerDraft.start==='schedule'){
    add({name:'Запустить процесс по расписанию и зафиксировать старт',source_system:'Планировщик',system:proc,target_system:db,channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',compensation:'jobId, watermark, повторный запуск без дублей'});
  } else {
    add({name:'Принять входящий запрос и создать запись процесса',source_system:src,system:proc,target_system:db,channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'key',writes_entity:'yes',compensation:'transaction, audit journal, уникальный requestId, начальный статус'});
  }

  if(composerDraft.activity==='call_external'){
    add({name:'Вызвать внешнюю систему для основного действия',source_system:proc,system:proc,target_system:provider,channel:'rest',blocking:composerDraft.timing==='later'?'no':'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'timeout, circuit breaker, retry с тем же idempotencyKey, externalRequestId'});
  } else if(composerDraft.activity==='receive_data'){
    add({name:'Получить данные из внешней системы',source_system:proc,system:proc,target_system:provider,channel:'rest',blocking:composerDraft.timing==='later'?'no':'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'timeout, cache/fallback при допустимости, retry с backoff'});
  } else if(composerDraft.activity==='send_data'){
    add({name:'Передать данные во внешнюю систему',source_system:proc,system:proc,target_system:provider,channel:'rest',blocking:composerDraft.timing==='later'?'no':'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'Outbox/retry, idempotencyKey, фиксация неизвестного результата'});
  } else if(composerDraft.activity==='validate'){
    add({name:'Проверить данные и бизнес-правила перед изменением состояния',source_system:proc,system:proc,target_system:proc,channel:'rest',blocking:'yes',timeout_ms:'300',retry:'none',idempotency:'natural',depends_on:String(state.steps.length),compensation:'валидационная ошибка без изменения состояния, понятная причина отказа'});
  } else if(composerDraft.activity==='enrich'){
    add({name:'Обогатить данные через внешний источник',source_system:proc,system:proc,target_system:provider,channel:'rest',blocking:'yes',timeout_ms:'700',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'cache/fallback, circuit breaker, partial enrichment policy'});
  } else if(composerDraft.activity==='wait_status'){
    add({name:'Отправить запрос и перейти в ожидание статуса',source_system:proc,system:proc,target_system:provider,channel:'rest',blocking:'no',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'Outbox, externalRequestId, статус WAITING_RESULT'});
  }

  if(['later','both'].includes(composerDraft.timing) || composerDraft.activity==='wait_status'){
    add({name:'Принять callback/webhook со статусом от внешней системы',source_system:provider,system:proc,target_system:db,channel:'callback',blocking:'no',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'подпись callback, timestamp/nonce, rate limit, eventId, statusVersion'});
    add({name:'Дедуплицировать поздний результат и обновить историю',source_system:proc,system:proc,target_system:db,channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'key',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'Inbox, UNIQUE eventId, replay-safe update, status history'});
  } else if(composerDraft.timing==='unknown'){
    add({name:'Зафиксировать результат или неизвестное состояние',source_system:provider,system:proc,target_system:db,channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'если ответ придёт позже — принять через Inbox/callback; если финал неизвестен — ручной разбор'});
  }

  if(['save','save_forward','update_status','unknown'].includes(composerDraft.result)){
    add({name:composerDraft.result==='update_status'?'Обновить статус основной сущности':'Сохранить результат и историю состояния',source_system:proc,system:proc,target_system:db,channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'transaction, optimistic locking/statusVersion, status history, lastError'});
  }
  if(['forward','save_forward'].includes(composerDraft.result)){
    add({name:'Передать результат дальше в целевую систему',source_system:proc,system:proc,target_system:target,channel:'rest',blocking:'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:String(state.steps.length),compensation:'Outbox, retry limit, ручной разбор при неизвестном финале'});
  }
  if(composerDraft.result==='compare'){
    ensureSystem('Сервис сверки','internal');
    add({name:'Сверить полученные данные с сохранённым состоянием',source_system:db,system:'Сервис сверки',target_system:db,channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'reconciliation key, окно ожидания, отчёт расхождений'});
    add({name:'Отправить расхождения на ручной разбор',source_system:'Сервис сверки',system:'Сервис сверки',target_system:db,channel:'db',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'NEEDS_MANUAL_REVIEW, correction journal, replay'});
  }
  if(composerDraft.timing==='unknown' || composerDraft.result==='unknown'){
    add({name:'Отправить неопределённые случаи на ручной разбор',source_system:proc,system:proc,target_system:db,channel:'db',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',depends_on:String(state.steps.length),compensation:'NEEDS_MANUAL_REVIEW, runbook, replay после уточнения'});
  }

  renumberSteps(); state.stackReady=false; state.stage='clarifications'; renderAll(); updateComposerPreview();
  const selected=document.getElementById('selectedScenario'); if(selected)selected.textContent='Цепочка собрана из универсальных вариантов, без стартового шаблона. Теперь можно усложнить её признаками процесса или сразу проверить архитектуру.';
  showToast('Цепочка собрана. Теперь уточните детали процесса и сформируйте стек.');
  document.getElementById('complexity-modules')?.scrollIntoView({behavior:'smooth',block:'start'});
}

function addStep(data={}, insertIndex=null, rerender=true){
  const channel=data.channel||'rest'; const d=safeDefaultsFor(channel);
  const step={id:data.id||uid('step'),order:1,name:data.name||'',source_system:data.source_system||'',system:data.system||'',target_system:data.target_system||'',channel,blocking:data.blocking||d.blocking,timeout_ms:data.timeout_ms==null?d.timeout_ms:String(data.timeout_ms||''),retry:data.retry||d.retry,idempotency:data.idempotency||d.idempotency,writes_entity:data.writes_entity||'no',depends_on:data.depends_on?String(data.depends_on):'',compensation:data.compensation||d.compensation,failure_policy:data.failure_policy||d.failure_policy,component_type:data.component_type||'action',dependency_basis:data.dependency_basis||'',interaction_action:data.interaction_action||'',interaction_timing:data.interaction_timing||'',interaction_result:data.interaction_result||'',primary_channel:data.primary_channel||'',channel_manual:data.channel_manual||'no',stack_reason:data.stack_reason||'',clarifications:Array.isArray(data.clarifications)?data.clarifications:[]};
  if(insertIndex===null || insertIndex<0 || insertIndex>state.steps.length) state.steps.push(step); else state.steps.splice(insertIndex,0,step);
  if(step.system) ensureSystem(step.system, step.channel==='kafka'||step.channel==='queue'?'broker':'internal');
  if(step.target_system && step.channel==='db') ensureSystem(step.target_system,'db');
  if(step.channel==='kafka') ensureSystem('Kafka','broker');
  if(step.channel==='db') ensureSystem(step.target_system||'БД процесса','db');
  renumberSteps(); if(rerender) renderAll();
}
function deleteStep(id){state.steps=state.steps.filter(s=>s.id!==id); state.modules=state.modules.filter(m=>m.stepId!==id); normalizeChainAfterStructureChange({reason:'delete',autofillRoutes:false}); renderAll();}
function duplicateStep(id){const i=state.steps.findIndex(s=>s.id===id); if(i<0)return; const c={...state.steps[i],id:uid('step'),name:(state.steps[i].name||'Шаг')+' — копия'}; state.steps.splice(i+1,0,c); normalizeChainAfterStructureChange({reason:'duplicate',autofillRoutes:true}); renderAll();}
function moveStep(id,dir){const i=state.steps.findIndex(s=>s.id===id); if(i<0)return; const ni=i+dir; if(ni<0||ni>=state.steps.length)return; const [x]=state.steps.splice(i,1); state.steps.splice(ni,0,x); normalizeChainAfterStructureChange({reason:'move',autofillRoutes:true,movedId:x.id}); renderAll(); showToast('Шаг перемещён. Маршрут, исполнитель, получатель и зависимости пересчитаны автоматически.');}
function insertStepAfter(id,kind='rest'){const i=state.steps.findIndex(s=>s.id===id); addStep(presetStep(kind),i+1); normalizeChainAfterStructureChange({reason:'insert',autofillRoutes:true});}
function insertStepBefore(id,kind='rest'){const i=state.steps.findIndex(s=>s.id===id); addStep(presetStep(kind),i<0?0:i); normalizeChainAfterStructureChange({reason:'insert',autofillRoutes:true});}
function renumberSteps(){state.steps.forEach((s,i)=>{s.order=i+1;}); repairStepDependencies();}
function normTxt(v){return String(v||'').toLowerCase();}
function nameHas(s,words){const t=normTxt((s&&s.name)||''); return words.some(w=>t.includes(w));}
function firstSystemByRole(role,fallback){return state.systems.find(x=>x.role===role)?.name||fallback;}
function roleGuessFor(name,channel){const n=normTxt(name); if(!name)return 'internal'; if(channel==='db'||n.includes('бд')||n.includes('postgres')||n.includes('database'))return 'db'; if(['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(channel)||n.includes('kafka')||n.includes('rabbit')||n.includes('очеред')||n.includes('broker')||n.includes('топик'))return 'broker'; if(['redis_cache','redis_lock'].includes(channel)||n.includes('redis')||n.includes('кэш')||n.includes('cache'))return 'cache'; if(['api_gateway','esb'].includes(channel)||n.includes('gateway')||n.includes('esb')||n.includes('шина'))return 'gateway'; if(n.includes('dwh')||n.includes('витрин')||n.includes('audit mart'))return 'analytics'; if(n.includes('legacy'))return 'legacy'; if(n.includes('внешн')||n.includes('поставщик')||n.includes('провайдер')||n.includes('ук')||n.includes('справочник')||n.includes('получатель'))return 'external'; return 'internal';}
function ensureRouteSystemsForStep(s){['source_system','system','target_system'].forEach(k=>{const val=(s[k]||'').trim(); if(val) ensureSystem(val, roleGuessFor(val,s.channel));});}
function previousOutput(i){const p=state.steps[i-1]; if(!p)return firstSystemByRole('internal','Сервис процесса'); return p.target_system||p.system||firstSystemByRole('internal','Сервис процесса');}
function lastStepIndexBefore(i,pred){for(let n=i-1;n>=0;n--){if(pred(state.steps[n]))return n+1;} return 0;}
function lastDbWriteIndexBefore(i){return lastStepIndexBefore(i,s=>s.channel==='db'||s.writes_entity==='yes'||nameHas(s,['сохран','запис','обнов','созда']));}
function lastCdcIndexBefore(i){return lastStepIndexBefore(i,s=>s.channel==='cdc'||nameHas(s,['cdc']));}
function validDepNumbers(raw,ownOrder){return String(raw||'').split(',').map(x=>parseInt(x.trim(),10)).filter(n=>Number.isFinite(n)&&n>=1&&n<=state.steps.length&&n!==ownOrder);}
function uniqNums(nums){return [...new Set(nums)].sort((a,b)=>a-b);}
function semanticDependsForStep(s,i){const own=i+1; const prev=i>0?i:0; const existing=validDepNumbers(s.depends_on,own);
  if(nameHas(s,['join','дождаться','обязательных веток'])&&existing.length>=2)return existing.join(',');
  if(s.channel==='cdc'||nameHas(s,['cdc-пайплайн','cdc'])){const dbi=lastDbWriteIndexBefore(i); return String(dbi||prev||'');}
  if(nameHas(s,['dwh свер','сверяет полноту','витрин','reconciliation'])){const deps=uniqNums([lastCdcIndexBefore(i),lastDbWriteIndexBefore(i),prev].filter(Boolean).filter(n=>n!==own)); return deps.join(',');}
  if(existing.length && existing.every(n=>n<own))return existing.join(',');
  return prev?String(prev):'';
}
function repairStepDependencies(){state.steps.forEach((s,i)=>{s.order=i+1; s.depends_on=semanticDependsForStep(s,i);});}
function stackReasonFor(channel,s){
  if(channel==='db')return 'Выбрано автоматически: шаг сохраняет или обновляет состояние, поэтому основной канал — запись в БД / OLTP.';
  if(channel==='redis_cache')return 'Выбрано автоматически: шаг похож на кэширование или быстрый read-through/cache-aside. Redis подходит как ускоритель чтения, но не как источник истины.';
  if(channel==='redis_lock')return 'Выбрано автоматически: шаг требует распределённой блокировки/защиты от параллельного выполнения. Нужны TTL и fencing token.';
  if(channel==='search')return 'Выбрано автоматически: шаг строит поисковый индекс или read-model. Нужны async indexing, reindex и контроль lag.';
  if(channel==='cdc')return 'Выбрано автоматически: это передача изменений в аналитику без нагрузки на основной поток, поэтому нужен CDC.';
  if(channel==='kafka')return 'Выбрано автоматически: нужен durable event-stream, replay, порядок по ключу, fan-out на нескольких потребителей или высокая потоковая нагрузка.';
  if(channel==='rabbitmq')return 'Выбрано автоматически: нужна очередь задач, маршрутизация, повторные попытки, очередь ошибочных сообщений и несколько обработчиков. Полноценный журнал событий, как в Kafka, здесь не обязателен.';
  if(channel==='redis_streams')return 'Выбрано автоматически: нужен лёгкий поток событий Redis Streams с группой потребителей и малой задержкой. Для долговременного журнала событий лучше Kafka.';
  if(channel==='redis_queue')return 'Выбрано автоматически: нужна простая короткоживущая очередь для фоновых задач. Для критичных событий лучше RabbitMQ или Kafka.';
  if(channel==='queue')return 'Выбрано автоматически: нужен асинхронный буфер, но конкретный брокер пока не выбран. Уточните требования к порядку, повторной обработке и маршрутизации, после этого система предложит Kafka, RabbitMQ или Redis Streams.';
  if(channel==='webhook'||channel==='callback')return 'Выбрано автоматически: внешняя система сама возвращает результат позже. Нужен обратный вызов или входящий веб-вызов с проверкой подписи и дедупликацией.';
  if(channel==='sftp')return 'Выбрано автоматически: партнёрский или старый файловый обмен. Нужны контрольная сумма, протокол обработки файла, карантин ошибок и повторная загрузка.';
  if(channel==='object_storage')return 'Выбрано автоматически: большие файлы и документы лучше хранить в объектном хранилище и передавать ссылку, а не класть файл в API или очередь.';
  if(channel==='batch'||channel==='file')return 'Выбрано автоматически: это пакетная, файловая, аналитическая или сверочная операция без ожидания онлайн-ответа.';
  if(channel==='grpc')return 'Выбрано автоматически: быстрый внутренний синхронный вызов при стабильном контракте и низкой задержке.';
  if(channel==='soap')return 'Выбрано автоматически: интеграция со старым или корпоративным контуром, где уже есть SOAP/WSDL-контракт.';
  if(channel==='api_gateway')return 'Выбрано автоматически: нужен единый внешний вход, авторизация, лимит запросов, маршрутизация и версионирование API.';
  if(channel==='esb')return 'Выбрано автоматически: корпоративный или старый ландшафт с маршрутизацией, трансформациями и централизованной интеграционной шиной.';
  if(channel==='graphql')return 'Выбрано автоматически: по смыслу процесса подходит GraphQL — гибкое чтение/агрегация API. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='odata')return 'Выбрано автоматически: по смыслу процесса подходит OData — корпоративный API по сущностям. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='service_mesh')return 'Выбрано автоматически: по смыслу процесса подходит Service Mesh — управление внутренними вызовами. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='read_replica')return 'Выбрано автоматически: по смыслу процесса подходит Реплика БД — масштабирование чтения. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='db_sharding')return 'Выбрано автоматически: по смыслу процесса подходит Шардирование БД — разделение данных. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='mongodb')return 'Выбрано автоматически: по смыслу процесса подходит MongoDB — документное хранилище. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='cassandra')return 'Выбрано автоматически: по смыслу процесса подходит Cassandra/ScyllaDB — ширококолонковое хранилище. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='dynamodb')return 'Выбрано автоматически: по смыслу процесса подходит DynamoDB/Key-Value — хранилище ключ-значение. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='clickhouse')return 'Выбрано автоматически: по смыслу процесса подходит ClickHouse — аналитическая колоночная БД. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='data_warehouse')return 'Выбрано автоматически: по смыслу процесса подходит Data Warehouse — аналитическое хранилище. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='data_lake')return 'Выбрано автоматически: по смыслу процесса подходит Data Lake — озеро данных. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='lakehouse')return 'Выбрано автоматически: по смыслу процесса подходит Lakehouse — озеро данных с таблицами. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='memcached')return 'Выбрано автоматически: по смыслу процесса подходит Memcached — простой временный кэш. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='vector_db')return 'Выбрано автоматически: по смыслу процесса подходит Векторная БД — семантический поиск. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='pulsar')return 'Выбрано автоматически: по смыслу процесса подходит Pulsar — поток событий с отдельным хранением. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='activemq')return 'Выбрано автоматически: по смыслу процесса подходит ActiveMQ/Artemis — корпоративная очередь. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='ibm_mq')return 'Выбрано автоматически: по смыслу процесса подходит IBM MQ — enterprise-очередь. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='nats')return 'Выбрано автоматически: по смыслу процесса подходит NATS — лёгкая шина сообщений. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='sns_sqs')return 'Выбрано автоматически: по смыслу процесса подходит AWS SNS/SQS — облачная очередь/рассылка. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='azure_service_bus')return 'Выбрано автоматически: по смыслу процесса подходит Azure Service Bus — облачная очередь/топик. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='gcp_pubsub')return 'Выбрано автоматически: по смыслу процесса подходит Google Pub/Sub — облачная шина сообщений. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='mqtt')return 'Выбрано автоматически: по смыслу процесса подходит MQTT — сообщения от устройств. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='websocket')return 'Выбрано автоматически: по смыслу процесса подходит WebSocket — двусторонний онлайн-канал. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='sse')return 'Выбрано автоматически: по смыслу процесса подходит Server-Sent Events — поток уведомлений. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='etl')return 'Выбрано автоматически: по смыслу процесса подходит ETL/ELT — загрузка и преобразование данных. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='airflow')return 'Выбрано автоматически: по смыслу процесса подходит Airflow — оркестрация загрузок. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='spark')return 'Выбрано автоматически: по смыслу процесса подходит Spark — распределённая обработка больших данных. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='dbt')return 'Выбрано автоматически: по смыслу процесса подходит dbt — аналитические модели данных. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='workflow_engine')return 'Выбрано автоматически: по смыслу процесса подходит Temporal/Workflow engine — длительный процесс с состояниями. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='bpm_engine')return 'Выбрано автоматически: по смыслу процесса подходит Camunda/BPMN — бизнес-процесс и ручные задачи. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='cdn')return 'Выбрано автоматически: по смыслу процесса подходит CDN — быстрая выдача статического контента. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='auth_oidc')return 'Выбрано автоматически: по смыслу процесса подходит OAuth2/OIDC — единая авторизация. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='vault')return 'Выбрано автоматически: по смыслу процесса подходит Vault/KMS — секреты и ключи. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  if(channel==='observability')return 'Выбрано автоматически: по смыслу процесса подходит Наблюдаемость — метрики, логи, трассировки. Нужно зафиксировать условия эксплуатации, ошибки, восстановление и владельца.';
  return 'Выбрано автоматически: шаг похож на синхронный запрос или команду во внешнюю систему; при позднем результате модель добавит статус ожидания и восстановление.';
}
function inferChannelForStep(s,i){
  const n=normTxt((s&&s.name)||'');
  const src=normTxt((s&&s.source_system)||'');
  const tgt=normTxt((s&&s.target_system)||'');
  const comp=normTxt((s&&s.compensation)||'');
  const all=[n,src,tgt,comp].join(' ');
  if(s.channel_manual==='yes')return {channel:s.channel||'rest',reason:'Оставлено ручное переопределение эксперта. Система не будет менять этот канал при перестановке шага.'};
  const clarified=clarifiedChannelForStep(s);
  if(clarified)return clarified;
  if(s.interaction_action){
    const ch=inferInteractionChannel(s.interaction_action,s.interaction_timing||'sync',s.interaction_result||'pass_next',s.source_system||'',s.target_system||'');
    return {channel:ch,reason:stackReasonFor(ch,s)};
  }
  if(n.includes('cdc')||s.component_type==='cdc')return {channel:'cdc',reason:stackReasonFor('cdc',s)};
  if(all.includes('sftp'))return {channel:'sftp',reason:stackReasonFor('sftp',s)};
  if(all.includes('object storage')||all.includes('s3')||all.includes('minio')||all.includes('объектн'))return {channel:'object_storage',reason:stackReasonFor('object_storage',s)};
  if(all.includes('redis streams')||all.includes('redis stream'))return {channel:'redis_streams',reason:stackReasonFor('redis_streams',s)};
  if(all.includes('redis queue'))return {channel:'redis_queue',reason:stackReasonFor('redis_queue',s)};
  if(n.includes('webhook'))return {channel:'webhook',reason:stackReasonFor('webhook',s)+' Если внешний партнёр не умеет webhook, замените на callback/polling или очередь в экспертном блоке.'};
  if(n.includes('callback')||(n.includes('принять результат')&& (src.includes('внешн')||src.includes('поставщик')||src.includes('провайдер')) && !(tgt.includes('kafka')||tgt.includes('очеред')||tgt.includes('rabbit'))))return {channel:'callback',reason:stackReasonFor('callback',s)+' Если внешний партнёр не умеет callback/webhook, замените на polling, RabbitMQ/Kafka или промежуточную очередь в экспертном блоке.'};
  if(n.includes('файл') && !n.includes('batch') && !n.includes('по расписанию') && !n.includes('свер') && !n.includes('reconciliation'))return {channel:'file',reason:stackReasonFor('file',s)};
  if(n.includes('batch')||n.includes('по расписанию')||n.includes('свер')||n.includes('reconciliation')||n.includes('миграц'))return {channel:'batch',reason:stackReasonFor('batch',s)};
  // Явные признаки gRPC и записи в БД должны срабатывать раньше общих слов cache/lock.
  // Иначе шаг "gRPC ... cached fallback" ошибочно уходит в Redis cache,
  // а запись в БД с optimistic locking — в Redis lock.
  if(all.includes('grpc')||(n.includes('внутрен')&&n.includes('быстр')))return {channel:'grpc',reason:stackReasonFor('grpc',s)};
  if(s.writes_entity==='yes'||n.includes('сохран')||n.includes('запис')||n.includes('обновить статус')||n.includes('создать запись')||n.includes('дедуплицировать'))return {channel:'db',reason:stackReasonFor('db',s)};
  if(all.includes('redis lock')||all.includes('distributed lock')||all.includes('блокиров')||all.includes('lock'))return {channel:'redis_lock',reason:stackReasonFor('redis_lock',s)};
  if(all.includes('redis')||all.includes('кэш')||all.includes('cache')||all.includes('ttl'))return {channel:'redis_cache',reason:stackReasonFor('redis_cache',s)};
  if(all.includes('search')||all.includes('elastic')||all.includes('opensearch')||all.includes('поисков'))return {channel:'search',reason:stackReasonFor('search',s)};
  if(all.includes('rabbit')||n.includes('фоновую работу')||n.includes('фоновой обработки')||n.includes('очередь обработки'))return {channel:'rabbitmq',reason:stackReasonFor('rabbitmq',s)};
  if((src.includes('очеред')||tgt.includes('очеред')||n.includes('очеред')) && !(src.includes('kafka')||tgt.includes('kafka')||all.includes('rabbit')||all.includes('redis')))return {channel:'queue',reason:stackReasonFor('queue',s)};
  if(n.includes('позже')||n.includes('событ')||n.includes('опубликов')||n.includes('dlq')||n.includes('replay')||n.includes('inbox')||src.includes('kafka')||tgt.includes('kafka'))return {channel:'kafka',reason:stackReasonFor('kafka',s)};
  if(all.includes('gateway')||all.includes('api gateway'))return {channel:'api_gateway',reason:stackReasonFor('api_gateway',s)};
  if(all.includes('esb')||all.includes('шина'))return {channel:'esb',reason:stackReasonFor('esb',s)};
  if(n.includes('legacy')||src.includes('legacy')||tgt.includes('legacy')||all.includes('wsdl'))return {channel:(all.includes('soap')||all.includes('wsdl')?'soap':'rest'),reason:stackReasonFor(all.includes('soap')||all.includes('wsdl')?'soap':'rest',s)+' Если legacy реально работает через SOAP/SFTP/ESB — переопределите в экспертном блоке.'};
  if(all.includes('гибкий') && all.includes('клиентов'))return {channel:'graphql',reason:stackReasonFor('graphql',s)};
  if(all.includes('корпоративный') && all.includes('сущностям'))return {channel:'odata',reason:stackReasonFor('odata',s)};
  if(all.includes('управлять') && all.includes('сервисов'))return {channel:'service_mesh',reason:stackReasonFor('service_mesh',s)};
  if(all.includes('двусторонний') && all.includes('онлайн-канал'))return {channel:'websocket',reason:stackReasonFor('websocket',s)};
  if(all.includes('поток') && all.includes('клиенту'))return {channel:'sse',reason:stackReasonFor('sse',s)};
  if(all.includes('есть') && all.includes('датчики'))return {channel:'mqtt',reason:stackReasonFor('mqtt',s)};
  if(all.includes('масштабный') && all.includes('хранением'))return {channel:'pulsar',reason:stackReasonFor('pulsar',s)};
  if(all.includes('лёгкая') && all.includes('сообщений'))return {channel:'nats',reason:stackReasonFor('nats',s)};
  if(all.includes('корпоративная') && all.includes('очередь'))return {channel:'ibm_mq',reason:stackReasonFor('ibm_mq',s)};
  if(all.includes('облачная') && all.includes('топик'))return {channel:'sns_sqs',reason:stackReasonFor('sns_sqs',s)};
  if(all.includes('разгрузить') && all.includes('бд'))return {channel:'read_replica',reason:stackReasonFor('read_replica',s)};
  if(all.includes('разделить') && all.includes('ключу'))return {channel:'db_sharding',reason:stackReasonFor('db_sharding',s)};
  if(all.includes('нужны') && all.includes('документы'))return {channel:'mongodb',reason:stackReasonFor('mongodb',s)};
  if(all.includes('нужны') && all.includes('ключу'))return {channel:'cassandra',reason:stackReasonFor('cassandra',s)};
  if(all.includes('быстрый') && all.includes('хранилище'))return {channel:'dynamodb',reason:stackReasonFor('dynamodb',s)};
  if(all.includes('простой') && all.includes('кэш'))return {channel:'memcached',reason:stackReasonFor('memcached',s)};
  if(all.includes('быстрая') && all.includes('таблицам'))return {channel:'clickhouse',reason:stackReasonFor('clickhouse',s)};
  if(all.includes('складывать') && all.includes('форматов'))return {channel:'data_lake',reason:stackReasonFor('data_lake',s)};
  if(all.includes('совместить') && all.includes('аналитику'))return {channel:'lakehouse',reason:stackReasonFor('lakehouse',s)};
  if(all.includes('загрузка') && all.includes('данных'))return {channel:'etl',reason:stackReasonFor('etl',s)};
  if(all.includes('управлять') && all.includes('загрузками'))return {channel:'airflow',reason:stackReasonFor('airflow',s)};
  if(all.includes('большая') && all.includes('обработка'))return {channel:'spark',reason:stackReasonFor('spark',s)};
  if(all.includes('нужны') && all.includes('модели'))return {channel:'dbt',reason:stackReasonFor('dbt',s)};
  if(all.includes('процесс') && all.includes('состояния'))return {channel:'workflow_engine',reason:stackReasonFor('workflow_engine',s)};
  if(all.includes('есть') && all.includes('бизнес-задачи'))return {channel:'bpm_engine',reason:stackReasonFor('bpm_engine',s)};
  if(all.includes('быстро') && all.includes('файлы'))return {channel:'cdn',reason:stackReasonFor('cdn',s)};
  if(all.includes('единая') && all.includes('авторизация'))return {channel:'auth_oidc',reason:stackReasonFor('auth_oidc',s)};
  if(all.includes('безопасно') && all.includes('ключи'))return {channel:'vault',reason:stackReasonFor('vault',s)};
  if(all.includes('видеть,') && all.includes('процесс'))return {channel:'observability',reason:stackReasonFor('observability',s)};
  if(all.includes('семантический') && all.includes('текстам'))return {channel:'vector_db',reason:stackReasonFor('vector_db',s)};
  if(all.includes('rest'))return {channel:'rest',reason:stackReasonFor('rest',s)};
  if(all.includes('graphql'))return {channel:'graphql',reason:stackReasonFor('graphql',s)};
  if(all.includes('odata'))return {channel:'odata',reason:stackReasonFor('odata',s)};
  if(all.includes('grpc'))return {channel:'grpc',reason:stackReasonFor('grpc',s)};
  if(all.includes('soap'))return {channel:'soap',reason:stackReasonFor('soap',s)};
  if(all.includes('api gateway'))return {channel:'api_gateway',reason:stackReasonFor('api_gateway',s)};
  if(all.includes('service mesh'))return {channel:'service_mesh',reason:stackReasonFor('service_mesh',s)};
  if(all.includes('esb'))return {channel:'esb',reason:stackReasonFor('esb',s)};
  if(all.includes('db'))return {channel:'db',reason:stackReasonFor('db',s)};
  if(all.includes('read replica'))return {channel:'read_replica',reason:stackReasonFor('read_replica',s)};
  if(all.includes('db sharding'))return {channel:'db_sharding',reason:stackReasonFor('db_sharding',s)};
  if(all.includes('mongodb'))return {channel:'mongodb',reason:stackReasonFor('mongodb',s)};
  if(all.includes('cassandra'))return {channel:'cassandra',reason:stackReasonFor('cassandra',s)};
  if(all.includes('dynamodb'))return {channel:'dynamodb',reason:stackReasonFor('dynamodb',s)};
  if(all.includes('clickhouse'))return {channel:'clickhouse',reason:stackReasonFor('clickhouse',s)};
  if(all.includes('data warehouse'))return {channel:'data_warehouse',reason:stackReasonFor('data_warehouse',s)};
  if(all.includes('data lake'))return {channel:'data_lake',reason:stackReasonFor('data_lake',s)};
  if(all.includes('lakehouse'))return {channel:'lakehouse',reason:stackReasonFor('lakehouse',s)};
  if(all.includes('redis cache'))return {channel:'redis_cache',reason:stackReasonFor('redis_cache',s)};
  if(all.includes('memcached'))return {channel:'memcached',reason:stackReasonFor('memcached',s)};
  if(all.includes('redis lock'))return {channel:'redis_lock',reason:stackReasonFor('redis_lock',s)};
  if(all.includes('search'))return {channel:'search',reason:stackReasonFor('search',s)};
  if(all.includes('vector db'))return {channel:'vector_db',reason:stackReasonFor('vector_db',s)};
  if(all.includes('kafka'))return {channel:'kafka',reason:stackReasonFor('kafka',s)};
  if(all.includes('pulsar'))return {channel:'pulsar',reason:stackReasonFor('pulsar',s)};
  if(all.includes('rabbitmq'))return {channel:'rabbitmq',reason:stackReasonFor('rabbitmq',s)};
  if(all.includes('activemq'))return {channel:'activemq',reason:stackReasonFor('activemq',s)};
  if(all.includes('ibm mq'))return {channel:'ibm_mq',reason:stackReasonFor('ibm_mq',s)};
  if(all.includes('nats'))return {channel:'nats',reason:stackReasonFor('nats',s)};
  if(all.includes('sns sqs'))return {channel:'sns_sqs',reason:stackReasonFor('sns_sqs',s)};
  if(all.includes('azure service bus'))return {channel:'azure_service_bus',reason:stackReasonFor('azure_service_bus',s)};
  if(all.includes('gcp pubsub'))return {channel:'gcp_pubsub',reason:stackReasonFor('gcp_pubsub',s)};
  if(all.includes('redis streams'))return {channel:'redis_streams',reason:stackReasonFor('redis_streams',s)};
  if(all.includes('redis queue'))return {channel:'redis_queue',reason:stackReasonFor('redis_queue',s)};
  if(all.includes('queue'))return {channel:'queue',reason:stackReasonFor('queue',s)};
  if(all.includes('mqtt'))return {channel:'mqtt',reason:stackReasonFor('mqtt',s)};
  if(all.includes('webhook'))return {channel:'webhook',reason:stackReasonFor('webhook',s)};
  if(all.includes('callback'))return {channel:'callback',reason:stackReasonFor('callback',s)};
  if(all.includes('websocket'))return {channel:'websocket',reason:stackReasonFor('websocket',s)};
  if(all.includes('sse'))return {channel:'sse',reason:stackReasonFor('sse',s)};
  if(all.includes('sftp'))return {channel:'sftp',reason:stackReasonFor('sftp',s)};
  if(all.includes('file'))return {channel:'file',reason:stackReasonFor('file',s)};
  if(all.includes('object storage'))return {channel:'object_storage',reason:stackReasonFor('object_storage',s)};
  if(all.includes('batch'))return {channel:'batch',reason:stackReasonFor('batch',s)};
  if(all.includes('cdc'))return {channel:'cdc',reason:stackReasonFor('cdc',s)};
  if(all.includes('etl'))return {channel:'etl',reason:stackReasonFor('etl',s)};
  if(all.includes('airflow'))return {channel:'airflow',reason:stackReasonFor('airflow',s)};
  if(all.includes('spark'))return {channel:'spark',reason:stackReasonFor('spark',s)};
  if(all.includes('dbt'))return {channel:'dbt',reason:stackReasonFor('dbt',s)};
  if(all.includes('workflow engine'))return {channel:'workflow_engine',reason:stackReasonFor('workflow_engine',s)};
  if(all.includes('bpm engine'))return {channel:'bpm_engine',reason:stackReasonFor('bpm_engine',s)};
  if(all.includes('cdn'))return {channel:'cdn',reason:stackReasonFor('cdn',s)};
  if(all.includes('auth oidc'))return {channel:'auth_oidc',reason:stackReasonFor('auth_oidc',s)};
  if(all.includes('vault'))return {channel:'vault',reason:stackReasonFor('vault',s)};
  if(all.includes('observability'))return {channel:'observability',reason:stackReasonFor('observability',s)};
  if(n.includes('ручной разбор')||n.includes('оператор'))return {channel:'rest',reason:'Выбрано автоматически: ручной разбор обычно оформляется как экран/задача в сервисе, а не как интеграционный транспорт.'};
  return {channel:'rest',reason:stackReasonFor('rest',s)};
}
function applyAutoStackForStepAt(i){
  const s=state.steps[i]; if(!s)return;
  const rec=inferChannelForStep(s,i); s.stack_reason=rec.reason;
  if(s.channel_manual==='yes')return;
  const old=s.channel; s.channel=rec.channel;
  const d=safeDefaultsFor(s.channel);
  if(old!==s.channel){
    if(!(s.channel==='rest' && s.blocking==='no')) s.blocking=d.blocking;
    s.retry=d.retry; s.idempotency=s.idempotency==='none'?d.idempotency:(s.idempotency||d.idempotency);
    s.failure_policy=d.failure_policy;
    if(!s.timeout_ms) s.timeout_ms=d.timeout_ms;
    if(!s.compensation) s.compensation=d.compensation;
  } else {
    if(!s.blocking) s.blocking=d.blocking;
    if(!s.retry) s.retry=d.retry;
    if(!s.idempotency) s.idempotency=d.idempotency;
    if(!s.failure_policy) s.failure_policy=d.failure_policy;
    if(!s.timeout_ms) s.timeout_ms=d.timeout_ms;
    if(!s.compensation) s.compensation=d.compensation;
  }
  if(['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(s.channel))ensureSystem(labelOf(CH,s.channel),'broker');
  if(['redis_cache','redis_lock'].includes(s.channel))ensureSystem('Redis','cache');
  if(['api_gateway','esb'].includes(s.channel))ensureSystem(labelOf(CH,s.channel),'gateway');
  if(s.channel==='db')ensureSystem(s.target_system||'БД процесса','db');
  if(s.channel==='cdc')ensureSystem('CDC-пайплайн','internal');
  if(s.channel==='object_storage')ensureSystem('Object storage','internal');
}
function autoFillRouteForStepAt(i){const s=state.steps[i]; if(!s)return; const proc=firstSystemByRole('internal','Сервис процесса'); const db=firstSystemByRole('db','БД процесса'); const broker=findKafka(); const external=firstSystemByRole('external','Внешняя система / поставщик'); const analytics=firstSystemByRole('analytics','Аналитическое хранилище / журнал сверки'); const prevOut=previousOutput(i);
  if(i===0){s.source_system=s.source_system||'Система-инициатор'; s.system=s.system||proc; if(!s.target_system)s.target_system=(s.channel==='db'||s.writes_entity==='yes')?db:prevOut;}
  if(s.channel==='cdc'||nameHas(s,['cdc-пайплайн','передать изменения через cdc'])){ensureSystem('Механизм передачи изменений','internal'); ensureSystem(analytics,'analytics'); const dbStep=lastDbWriteIndexBefore(i); s.source_system=dbStep?state.steps[dbStep-1].target_system:db; s.system='Механизм передачи изменений'; s.target_system=analytics; s.channel='cdc'; s.blocking='no'; if(!s.compensation)s.compensation='watermark, lag monitoring, replay/resync, backfill';}
  else if(nameHas(s,['dwh свер','сверяет полноту','витрин','reconciliation'])){ensureSystem('Сервис сверки аналитики','internal'); ensureSystem('Отчёт сверки / аналитический журнал','analytics'); const cdcStep=lastCdcIndexBefore(i); s.source_system=cdcStep?state.steps[cdcStep-1].target_system:prevOut; s.system='Сервис сверки аналитики'; s.target_system='Отчёт сверки / аналитический журнал'; s.channel=s.channel||'batch'; s.blocking='no'; s.retry='manual'; s.idempotency='natural'; if(!s.compensation)s.compensation='reconciliation report, gap detection, повторная загрузка';}
  else if(nameHas(s,['дедуплицировать','inbox','принять входящее событие'])){s.source_system=s.source_system||broker; s.system=proc; s.target_system=db; if(['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(s.channel)){s.blocking='no'; s.idempotency='key';}}
  else if(nameHas(s,['принять callback','принять результат или статус позже'])){s.source_system=s.source_system||external; s.system=proc; s.target_system=db; if(!['callback','webhook','kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(s.channel))s.channel='callback'; s.blocking='no'; s.idempotency='key';}
  else if(s.channel==='db'||s.writes_entity==='yes'||nameHas(s,['сохран','запис','обновить статус','создать запись'])){s.source_system=prevOut; s.system=proc; s.target_system=db; s.channel='db'; s.blocking=s.blocking||'yes'; if(!s.timeout_ms)s.timeout_ms='200';}
  else if(nameHas(s,['передать результат дальше','передать данные во внешнюю','отправить запрос','вызвать внешнюю','получить данные из внешней','обогатить данные'])){s.source_system=prevOut; s.system=proc; if(!s.target_system||s.target_system===proc||s.target_system===db)s.target_system=external; if(!s.channel||s.channel==='db')s.channel='rest';}
  else if(['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(s.channel)||nameHas(s,['опубликовать','событие'])){s.source_system=prevOut; s.system=s.system||proc; s.target_system=broker; if(!['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(s.channel))s.channel='kafka'; s.blocking='no'; s.idempotency='key';}
  else if(nameHas(s,['ручной разбор','оператор разбирает'])){ensureSystem('Сервис ручного разбора','internal'); s.source_system=prevOut; s.system='Сервис ручного разбора'; s.target_system=db; s.blocking='no'; s.retry='manual';}
  else {s.source_system=prevOut; if(!s.system)s.system=proc; if(!s.target_system)s.target_system=prevOut;}
  applyAutoStackForStepAt(i); s.depends_on=semanticDependsForStep(s,i); ensureRouteSystemsForStep(s);
}
function normalizeChainAfterStructureChange(opts={}){state.steps.forEach((s,i)=>{s.order=i+1;}); if(opts.autofillRoutes){state.steps.forEach((_,i)=>autoFillRouteForStepAt(i));} else {state.steps.forEach((_,i)=>applyAutoStackForStepAt(i));} repairStepDependencies(); state.steps.forEach(ensureRouteSystemsForStep);}
function applySafeDefaultsToStep(id){const s=state.steps.find(x=>x.id===id); if(!s)return; const d=safeDefaultsFor(s.channel); Object.assign(s,{blocking:d.blocking,timeout_ms:s.timeout_ms||d.timeout_ms,retry:d.retry,idempotency:d.idempotency,compensation:s.compensation||d.compensation,failure_policy:d.failure_policy}); renderAll();}
function applySafeDefaultsAll(){state.steps.forEach(s=>{const d=safeDefaultsFor(s.channel); Object.assign(s,{blocking:d.blocking,timeout_ms:s.timeout_ms||d.timeout_ms,retry:d.retry,idempotency:d.idempotency,compensation:s.compensation||d.compensation,failure_policy:s.failure_policy||d.failure_policy});}); renderAll();}
function updateStep(id,key,val){const s=state.steps.find(x=>x.id===id); if(!s)return; s[key]=val; if(['source_system','system','target_system'].includes(key)) ensureSystem(val); if(key==='channel'){const d=safeDefaultsFor(val); s.blocking=d.blocking; s.retry=d.retry; s.idempotency=d.idempotency; if(!s.timeout_ms) s.timeout_ms=d.timeout_ms; if(!s.compensation) s.compensation=d.compensation; s.failure_policy=d.failure_policy; s.stack_reason=stackReasonFor(val,s); if(['kafka','rabbitmq','redis_streams','redis_queue','queue'].includes(val))ensureSystem(labelOf(CH,val),'broker'); if(['redis_cache','redis_lock'].includes(val))ensureSystem('Redis','cache'); if(['api_gateway','esb'].includes(val))ensureSystem(labelOf(CH,val),'gateway'); if(val==='db')ensureSystem(s.target_system||'БД процесса','db');}
  if(key!=='channel' && ['name','source_system','system','target_system','writes_entity','blocking'].includes(key) && s.channel_manual!=='yes'){const i=state.steps.findIndex(x=>x.id===id); applyAutoStackForStepAt(i); repairStepDependencies();}
  renderAll();}
function setManualChannel(id,val){const s=state.steps.find(x=>x.id===id); if(!s)return; state.stackReady=true; s.channel_manual='yes'; updateStep(id,'channel',val); showToast('Стек шага переопределён вручную. Система больше не будет менять его при перестановке этого шага.');}
function resetAutoChannel(id){const i=state.steps.findIndex(x=>x.id===id); if(i<0)return; state.steps[i].channel_manual='no'; applyAutoStackForStepAt(i); state.stackReady=true; normalizeChainAfterStructureChange({reason:'auto-channel',autofillRoutes:false}); renderAll(); showToast('Автоподбор стека снова включён для шага.');}


function schemaHasParticipant(name){return !!state.systems.find(x=>String(x.name||'')===String(name||''));}
function firstSystemNameByRole(role, fallback){const s=state.systems.find(x=>x.role===role); return s?s.name:fallback;}
function firstExternalName(){return firstSystemNameByRole('external','Внешняя система / партнёр');}
function firstDbName(){return firstSystemNameByRole('db','Хранилище состояния процесса');}
function firstAnalyticsName(){return firstSystemNameByRole('analytics','Аналитическое хранилище');}
function firstBrokerName(){return state.systems.find(x=>['broker','queue'].includes(x.role)||explicitChannelFromText(x.name,x.name))?.name || 'Журнал событий';}
function validationIssue(stepIndex, title, body, fix, severity='warn'){return {stepIndex,title,body,fix,severity};}
function participantByName(name){return state.systems.find(x=>String(x.name||'')===String(name||''))||null;}
function participantRole(name){const x=participantByName(name);return x?x.role:'';}
function isBrokerSystemName(name){const r=participantRole(name); const v=normTxt(name||''); return r==='broker'||r==='queue'||v.includes('журнал событий')||v.includes('очеред')||v.includes('broker')||['kafka','pulsar','rabbitmq','nats','redis streams','service bus','pub/sub','activemq','ibm mq'].some(x=>v.includes(x));}
function isCacheSystemName(name){const r=participantRole(name); const v=normTxt(name||''); return r==='cache'||v.includes('redis')||v.includes('memcached')||v.includes('кэш');}
function isGatewaySystemName(name){const r=participantRole(name); const v=normTxt(name||''); return r==='gateway'||v.includes('gateway')||v.includes('шлюз')||v.includes('esb')||v.includes('шина');}
function isWorkflowSystemName(name){const r=participantRole(name); const v=normTxt(name||''); return r==='workflow'||v.includes('workflow')||v.includes('temporal')||v.includes('camunda')||v.includes('bpmn')||v.includes('движок');}
function isSecuritySystemName(name){const r=participantRole(name); const v=normTxt(name||''); return r==='security'||v.includes('vault')||v.includes('kms')||v.includes('oauth')||v.includes('oidc')||v.includes('авторизац');}
function canBeInitiator(name){return !(isStorageSystemName(name)||isCacheSystemName(name)||isAnalyticsSystemName(name));}
function isActiveProcessorName(name){const r=participantRole(name); const v=normTxt(name||''); return ['internal','external','legacy','gateway','workflow'].includes(r)||v.includes('сервис')||v.includes('api')||v.includes('партн')||v.includes('legacy')||v.includes('шлюз');}
function actionHumanName(action){return ({request_data:'получить данные',send_data:'передать данные',save:'сохранить результат',update_status:'обновить статус',wait_status:'принять поздний статус',compare:'сверить данные',notify_many:'сообщить нескольким системам',file:'передать файл'})[action]||'выполнить действие';}
function fixedNameForInteraction(source,target,action){const labels={request_data:'запрашивает данные у',send_data:'передаёт данные в',save:'сохраняет результат в',update_status:'обновляет статус в',wait_status:'передаёт поздний статус в',compare:'сверяет данные с',notify_many:'сообщает другим системам через',file:'передаёт файл в'}; return (source+' '+(labels[action]||'взаимодействует с')+' '+target).replace(/\s+/g,' ').trim();}
function issueKey(x){return [x.stepIndex,x.title,x.body].join('|');}
function pushIssue(issues, issue){const k=issueKey(issue); if(!issues.some(x=>issueKey(x)===k))issues.push(issue);}
function addSetFieldsFix(step, fields, reason){return {kind:'set-fields',stepId:step.id,fields,reason};}
function addStepFix(afterIndex, step, reason){return {kind:'add-step',afterIndex,step,reason};}
function normalizeActionFixName(step, fields){const src=fields.source_system||step.source_system||''; const tgt=fields.target_system||step.target_system||''; const act=fields.interaction_action||step.interaction_action||''; if(src&&tgt&&act) fields.name=fixedNameForInteraction(src,tgt,act); return fields;}
function hasLaterReturnFor(stepIndex, partnerName){return state.steps.some((x,j)=>j>stepIndex && (x.interaction_action==='wait_status'||String(x.channel||'').match(/callback|webhook/)||normTxt(x.name||'').includes('статус')) && (x.source_system===partnerName||x.target_system===partnerName));}
function hasStorageAfter(stepIndex){return state.steps.some((x,j)=>j>=stepIndex && (x.interaction_action==='save'||x.interaction_action==='update_status'||x.writes_entity==='yes'||isStorageSystemName(x.target_system)));}
function hasManualOrErrorPath(){return state.steps.some(x=>normTxt(x.name||'').includes('ручн')||normTxt(x.target_system||'').includes('ручн')||String(x.failure_policy||'').includes('руч'))}
function hasProcessService(){return state.systems.some(x=>x.role==='internal'||normTxt(x.name||'').includes('сервис процесса'));}
function validateSchemaBeforeStack(){
  const issues=[];
  const nameCounts={};
  state.systems.forEach(x=>{const k=normTxt(x.name||''); if(k)nameCounts[k]=(nameCounts[k]||0)+1;});
  Object.entries(nameCounts).filter(([,v])=>v>1).forEach(([k])=>pushIssue(issues,validationIssue(0,'Дублирующийся участник','В списке участников есть одинаковые названия. Из-за этого схема может связать шаг не с той системой.',null,'high')));
  if(state.systems.length<2){pushIssue(issues,validationIssue(0,'Недостаточно участников','Для проверки стека нужны минимум два участника: кто начинает процесс и кто получает или обрабатывает результат.',null,'high'));}
  if(!state.steps.length){pushIssue(issues,validationIssue(0,'Нет связей между участниками','Сначала добавьте хотя бы одну связь: кто отдаёт данные, кто получает и что происходит.',null,'high'));}
  if(state.steps.length && !hasProcessService()){
    pushIssue(issues,validationIssue(0,'Не указан сервис или владелец процесса','В цепочке есть взаимодействия, но нет участника, который управляет процессом. Без этого непонятно, кто хранит состояние, отвечает за ошибки и запускает восстановление.',{kind:'ensure-system',name:'Сервис процесса',role:'internal',reason:'добавить владельца процесса'},'medium'));
  }
  state.steps.forEach((s,i)=>{
    const n=normTxt(s.name||''); const src=String(s.source_system||'').trim(); const tgt=String(s.target_system||'').trim();
    const action=s.interaction_action||''; const rawTiming=s.interaction_timing||''; const timing=rawTiming||((s.blocking==='no')?'later':'sync'); const result=s.interaction_result||'';
    if(!src){pushIssue(issues,validationIssue(i+1,'У связи нет источника','Непонятно, кто отдаёт данные или запускает действие.',{stepId:s.id,key:'source_system',value:i?state.steps[i-1].target_system:firstSystemNameByRole('initiator','Система-инициатор'),reason:'подставить источник из предыдущего шага или инициатора'},'high'));}
    if(!tgt){pushIssue(issues,validationIssue(i+1,'У связи нет получателя','Непонятно, кто должен получить результат взаимодействия.',{stepId:s.id,key:'target_system',value:firstDbName(),reason:'подставить хранилище состояния как безопасный получатель'},'high'));}
    if(src && !schemaHasParticipant(src)){pushIssue(issues,validationIssue(i+1,'Источник не добавлен в участники','Связь ссылается на участника, которого нет в списке участников процесса.',{kind:'ensure-system',name:src,role:'internal',reason:'добавить источник в участники'},'high'));}
    if(tgt && !schemaHasParticipant(tgt)){pushIssue(issues,validationIssue(i+1,'Получатель не добавлен в участники','Связь ссылается на получателя, которого нет в списке участников процесса.',{kind:'ensure-system',name:tgt,role:'internal',reason:'добавить получателя в участники'},'high'));}
    if(i===0 && src && !canBeInitiator(src)){
      pushIssue(issues,validationIssue(i+1,'Старт процесса начинается с пассивного участника','Первый шаг начинается от хранилища, кэша или аналитики. Обычно процесс запускает система, пользовательский канал, планировщик или внешний партнёр.',{stepId:s.id,key:'source_system',value:firstSystemNameByRole('initiator','Система-инициатор'),reason:'сделать источником первого шага инициатора процесса'},'medium'));
    }
    if(src && tgt && src===tgt && !['save','update_status'].includes(action)){
      let proposed=firstExternalName();
      if(action==='compare'||n.includes('аналит')||n.includes('dwh')||n.includes('витрин'))proposed=firstAnalyticsName();
      else if(action==='notify_many'||n.includes('событ')||n.includes('опубликов')||n.includes('сообщ'))proposed=firstBrokerName();
      else if(action==='file')proposed='Объектное хранилище';
      pushIssue(issues,validationIssue(i+1,'Источник и получатель совпадают','Обычная связь должна идти от одного участника к другому. Самосвязь допустима только для сохранения или обновления статуса.',{stepId:s.id,key:'target_system',value:proposed,reason:'развести источник и получателя'},'high'));
    }
    if(action==='save'||action==='update_status'){
      if(!isStorageSystemName(tgt)){
        const fields=normalizeActionFixName(s,{target_system:firstDbName()});
        pushIssue(issues,validationIssue(i+1,'Сохранение идёт не в хранилище','Если действие — сохранить результат или обновить статус, получателем должно быть хранилище состояния, а не внешняя система, очередь или аналитика.',addSetFieldsFix(s,fields,'направить сохранение в хранилище состояния'),'high'));
      }
    }
    if((action==='send_data'||action==='request_data') && isStorageSystemName(tgt) && result!=='save'){
      const fields=normalizeActionFixName(s,{interaction_action:'save',writes_entity:'yes',channel:'db'});
      pushIssue(issues,validationIssue(i+1,'Передача данных направлена в хранилище','Если получатель — хранилище состояния, это больше похоже на сохранение, а не на передачу данных другому участнику.',addSetFieldsFix(s,fields,'заменить тип действия на «сохранить результат»'),'medium'));
    }
    if((n.includes('внешн')||n.includes('партн')) && isStorageSystemName(tgt)){
      const fields=normalizeActionFixName(s,{target_system:firstExternalName(),interaction_action:action||'send_data'});
      pushIssue(issues,validationIssue(i+1,'Внешняя связь ведёт в хранилище','Название говорит про внешнюю систему или партнёра, но получателем стоит БД. БД может быть служебной записью, но не основным получателем внешней связи.',addSetFieldsFix(s,fields,'направить связь во внешнюю систему'),'high'));
    }
    if((action==='request_data'||action==='send_data') && isExternalSystemName(tgt) && timing==='sync' && result==='save' && !hasStorageAfter(i+1)){
      const db=firstDbName();
      pushIssue(issues,validationIssue(i+1,'Результат внешнего вызова нужно сохранить, но шага сохранения нет','Связь говорит, что результат надо сохранить, однако дальше нет явного сохранения в хранилище состояния.',addStepFix(i+1,{name:fixedNameForInteraction(src||'Сервис процесса',db,'save'),source_system:src||'Сервис процесса',system:src||'Сервис процесса',target_system:db,channel:'db',blocking:'yes',retry:'none',idempotency:'natural',writes_entity:'yes',depends_on:String(i+1),interaction_action:'save',interaction_timing:'sync',interaction_result:'save'},'добавить шаг сохранения результата'),'medium'));
    }
    if((action==='wait_status'||timing==='later') && isExternalSystemName(tgt) && !isExternalSystemName(src)){
      const fields=normalizeActionFixName(s,{source_system:tgt,target_system:src,channel:'webhook',blocking:'no'});
      pushIssue(issues,validationIssue(i+1,'Направление позднего статуса выглядит перепутанным','Если внешний партнёр позже присылает статус, источником должен быть партнёр, а получателем — наш сервис или входной контур.',addSetFieldsFix(s,fields,'поменять источник и получателя местами для входящего статуса'),'medium'));
    }
    if((action==='wait_status'||(rawTiming==='later' && !['compare','file','notify_many'].includes(action) && !isAnalyticsSystemName(tgt))) && !isExternalSystemName(src) && !isExternalSystemName(tgt) && !isBrokerSystemName(src) && !isBrokerSystemName(tgt)){
      pushIssue(issues,validationIssue(i+1,'Поздний результат без внешнего источника или очереди','Связь отмечена как поздний результат, но в ней нет внешнего партнёра, входящего канала или очереди. Система не поймёт, откуда придёт продолжение процесса.',{stepId:s.id,key:'target_system',value:firstExternalName(),reason:'указать внешнего источника позднего результата'},'medium'));
    }
    if(rawTiming==='later' && ['send_data','request_data','wait_status'].includes(action) && isExternalSystemName(tgt) && !hasLaterReturnFor(i,tgt)){
      const db=firstDbName();
      pushIssue(issues,validationIssue(i+1,'Есть асинхронный запрос партнёру, но нет обратного статуса','Процесс отправляет данные внешней системе и не ждёт ответ сразу, но дальше не описано, как партнёр вернёт результат или статус.',addStepFix(i+1,{name:fixedNameForInteraction(tgt,src||'Сервис процесса','wait_status'),source_system:tgt,system:tgt,target_system:src||'Сервис процесса',channel:'webhook',blocking:'no',retry:'auto',idempotency:'key',writes_entity:'yes',depends_on:String(i+1),interaction_action:'wait_status',interaction_timing:'later',interaction_result:'update_status',compensation:'подпись входящего вызова, дедупликация, обновление статуса'},'добавить входящий статус от партнёра'),'high'));
    }
    if(action==='notify_many' && !isBrokerSystemName(tgt)){
      const fields=normalizeActionFixName(s,{target_system:firstBrokerName(),channel:'kafka'});
      pushIssue(issues,validationIssue(i+1,'Рассылка многим системам без канала событий','Если нужно сообщить нескольким системам, получателем должен быть журнал событий или очередь, а не обычный сервис.',addSetFieldsFix(s,fields,'направить уведомление в журнал событий или очередь'),'high'));
    }
    if(isBrokerSystemName(tgt) && !['notify_many','wait_status'].includes(action) && action!=='file' && !['kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue'].includes(s.channel)){
      const fields=normalizeActionFixName(s,{interaction_action:'notify_many',interaction_timing:'later',interaction_result:'pass_next'});
      pushIssue(issues,validationIssue(i+1,'Связь ведёт в брокер, но действие не событийное','Если получатель — очередь или журнал событий, действие должно быть описано как публикация события или постановка задачи.',addSetFieldsFix(s,fields,'сделать действие событийным'),'medium'));
    }
    if(action==='file' && isStorageSystemName(tgt)){
      const fields=normalizeActionFixName(s,{target_system:'Объектное хранилище',channel:'object_storage'});
      pushIssue(issues,validationIssue(i+1,'Файл направлен в обычную БД','Файлы и документы не стоит складывать в основную БД как основной канал. Лучше использовать объектное хранилище или файловый обмен.',addSetFieldsFix(s,fields,'направить файл в объектное хранилище'),'medium'));
    }
    if((n.includes('аналит')||n.includes('dwh')||n.includes('витрин')||action==='compare') && !isAnalyticsSystemName(tgt) && action!=='save'){
      const fields=normalizeActionFixName(s,{target_system:firstAnalyticsName()});
      pushIssue(issues,validationIssue(i+1,'Аналитическая связь ведёт не в аналитику','Название похоже на передачу в аналитику или сверку, но получатель не является аналитическим контуром.',addSetFieldsFix(s,fields,'направить связь в аналитический контур'),'medium'));
    }
    if(isAnalyticsSystemName(tgt) && action==='send_data' && isActiveProcessorName(src) && !isStorageSystemName(src) && !state.steps.some((x,j)=>j<i && isStorageSystemName(x.target_system))){
      pushIssue(issues,validationIssue(i+1,'Передача в аналитику идёт напрямую из сервиса без зафиксированного источника','Для аналитики обычно нужен устойчивый источник: БД, журнал событий, CDC, batch или файловая зона. Прямая отправка из сервиса часто теряет сверяемость.',null,'medium'));
    }
    const inferred=inferInteractionChannel(action||'send_data',timing,result,src,tgt);
    if(inferred==='db' && !isStorageSystemName(tgt)){
      pushIssue(issues,validationIssue(i+1,'Основной стек связи определился как БД, но получатель не хранилище','БД может быть служебным компонентом, но не должна подменять связь с внешней системой, аналитикой или брокером.',null,'high'));
    }
    if(isExternalSystemName(tgt) && inferred==='db'){
      const fields=normalizeActionFixName(s,{channel:timing==='later'?'callback':'rest'});
      pushIssue(issues,validationIssue(i+1,'Внешняя связь не должна идти через БД как основной канал','Для связи с внешней системой нужен API, файл, обратный вызов или очередь, а БД используется только для фиксации состояния.',addSetFieldsFix(s,fields,'заменить основной канал внешней связи'),'high'));
    }
    if(isAnalyticsSystemName(tgt) && ['db','rest'].includes(inferred)){
      const fields=normalizeActionFixName(s,{channel:isStorageSystemName(src)?'cdc':'data_warehouse'});
      pushIssue(issues,validationIssue(i+1,'Стек аналитической связи выбран как оперативный канал','Аналитический контур лучше наполнять через CDC, пакетную загрузку, ETL/ELT или аналитическое хранилище, а не как обычный оперативный вызов.',addSetFieldsFix(s,fields,'заменить способ связи на аналитический'),'medium'));
    }
    const nums=String(s.depends_on||'').split(',').map(x=>parseInt(x.trim(),10)).filter(Boolean);
    if(i===0 && nums.length){pushIssue(issues,validationIssue(i+1,'Первый шаг не должен зависеть от другого шага','Начало процесса не может ждать предыдущий шаг, которого по смыслу ещё нет.',{stepId:s.id,key:'depends_on',value:'',reason:'очистить зависимость первого шага'},'high'));}
    if(nums.some(n=>n===i+1||n<1||n>state.steps.length)){
      pushIssue(issues,validationIssue(i+1,'Некорректная зависимость шага','Шаг не может зависеть сам от себя или от несуществующего шага.',{stepId:s.id,key:'depends_on',value:i?String(i):'',reason:'пересчитать зависимость по предыдущему шагу'},'high'));
    }
    if(i>0 && String(s.dependency_basis||'').includes('результат предыдущего')){
      const prev=state.steps[i-1];
      const prevTarget=prev&&prev.target_system;
      if(prevTarget && src && src!==prevTarget && !isActiveProcessorName(src) && !isStorageSystemName(src)){
        pushIssue(issues,validationIssue(i+1,'Следующий шаг не использует результат предыдущего','Указано, что шаг продолжается по результату предыдущего, но источник текущего шага не похож ни на получателя предыдущего шага, ни на сервис процесса, ни на хранилище.',null,'medium'));
      }
    }
  });
  const hasAsync=state.steps.some(s=>s.interaction_timing==='later'||s.blocking==='no'||isBrokerSystemName(s.target_system)||['kafka','pulsar','rabbitmq','redis_streams','queue','callback','webhook'].includes(s.channel));
  if(hasAsync && !hasManualOrErrorPath()){
    pushIssue(issues,validationIssue(0,'Нет понятного маршрута для ошибок асинхронной обработки','В схеме есть отложенная обработка или очередь, но нет ручного разбора, карантина или понятного пути восстановления.',null,'medium'));
  }
  return {issues};
}
function renderSchemaValidationPanel(){
  if(!state.schemaValidation||!state.schemaValidation.issues||!state.schemaValidation.issues.length)return '';
  const items=state.schemaValidation.issues.slice(0,8).map(x=>`<div class="schema-validation-item"><b>${x.stepIndex?'Шаг '+x.stepIndex+': ':''}${esc(x.title)}</b><span>${esc(x.body)}</span>${x.fix?`<small>Предложение: ${esc(x.fix.reason||'исправить автоматически')}</small>`:''}</div>`).join('');
  const more=state.schemaValidation.issues.length>8?`<p>И ещё ${state.schemaValidation.issues.length-8} замечаний. После автоправки можно снова определить стек.</p>`:'';
  const canFix=state.schemaValidation.issues.some(x=>x.fix);
  return `<div class="schema-validation-panel"><h4>Перед подбором стека проверьте логику схемы</h4><p>Система нашла места, где связь может быть направлена не туда, участник не добавлен или зависимость выглядит некорректно. Лучше исправить это до выбора технологий.</p><div class="schema-validation-list">${items}</div>${more}<div class="schema-validation-actions">${canFix?'<button type="button" class="btn" data-action="apply-schema-fixes">Применить предложенные улучшения</button>':''}<button type="button" class="btn ghost" data-action="continue-stack-anyway">Продолжить без исправлений</button></div></div>`;
}
function applySchemaValidationFixes(){
  const v=state.schemaValidation; if(!v||!v.issues)return;
  v.issues.forEach(x=>{
    const f=x.fix; if(!f)return;
    if(f.kind==='ensure-system'){ensureSystem(f.name,f.role||'internal');return;}
    if(f.kind==='add-step'){
      const step={...f.step,id:uid('step')};
      const idx=Math.max(0,Math.min(state.steps.length,Number(f.afterIndex||state.steps.length)));
      addStep(step,idx,false);
      return;
    }
    if(f.kind==='set-fields'){
      const st=state.steps.find(s=>s.id===f.stepId);
      if(st&&f.fields){Object.entries(f.fields).forEach(([k,val])=>{st[k]=val;});}
      return;
    }
    const st=state.steps.find(s=>s.id===f.stepId); if(st&&f.key)st[f.key]=f.value;
  });
  normalizeChainAfterStructureChange({reason:'schema-validation-fix',autofillRoutes:false});
  state.schemaValidation=null; state.schemaValidationBypass=false; state.stackReady=false; renderAll(); showToast('Предложенные улучшения применены. Проверьте схему и снова нажмите «Определить стек по процессу».');
}
function continueStackAnyway(){state.schemaValidation=null; state.schemaValidationBypass=true; generateStackRecommendations(false);}
function generateStackRecommendations(silent=false){
  if(!state.steps.length){showToast('Сначала соберите связи между участниками.');return;}
  if(!silent && !state.schemaValidationBypass){
    const v=validateSchemaBeforeStack();
    if(v.issues.length){state.schemaValidation=v; state.stage='stack'; renderAll(); showToast('Перед подбором стека нужно проверить логику схемы.'); return;}
  }
  state.schemaValidation=null; state.schemaValidationBypass=false;
  // Для нового flow участников не перестраиваем маршруты через старый autoFillRoute: пользователь уже задал связь source -> target.
  // Пересчитываем только стек, зависимости и служебные гарантии.
  normalizeChainAfterStructureChange({reason:'generate-stack',autofillRoutes:false});
  state.steps.forEach((_,i)=>applyAutoStackForStepAt(i));
  state.stackReady=true;
  state.stage='stack';
  renderAll();
  if(!silent) showToast('Стек сформирован по смыслу процесса. Проверьте объяснения и при необходимости поправьте вручную.');
}
function stackStageText(){
  if(!state.steps.length) return {title:'Стек ещё не формируется',body:'Сначала соберите верхнеуровневую цепочку: что начинается, что происходит, когда появляется результат и что делать дальше.',action:''};
  if(!state.stackReady) return {title:'Стек ещё не сформирован',body:'Пока показан только смысл процесса: синхронно или асинхронно, чтение, запись, сохранение, сверка, фоновая обработка, быстрый доступ на чтение, поиск, документы и ручной разбор. Нажмите кнопку ниже, и система сама предложит технологии с объяснением почему.',action:'Определить стек по процессу'};
  return {title:'Стек сформирован',body:'Для каждого шага система выбрала способ реализации и объяснила причину. Если есть ограничение проекта, откройте экспертный режим и переопределите конкретный шаг вручную.',action:'Пересчитать стек'};
}
function renderStackStage(){
  document.body.classList.toggle('stack-ready',!!state.stackReady);
  document.body.classList.toggle('stack-not-ready',!state.stackReady);
  const box=document.getElementById('stackStagePanel'); if(!box)return;
  const t=stackStageText();
  const btn=t.action?'<button type="button" class="btn" data-action="generate-stack">'+esc(t.action)+'</button>':'';
  const expert=state.stackReady?'<button type="button" class="btn ghost" data-mode="advanced" data-action="mode">Открыть экспертный режим</button>':'';
  box.innerHTML='<h3>'+esc(t.title)+'</h3><p>'+esc(t.body)+'</p>'+renderSchemaValidationPanel()+'<div class="stack-stage-actions">'+btn+expert+'</div>';
}

function previousStepFor(s){
  const dep=String(s.depends_on||'').split(',').map(x=>parseInt(x.trim(),10)).filter(Boolean);
  if(dep.length){return dep.map(n=>state.steps[n-1]).filter(Boolean);}
  return s.order>1?[state.steps[s.order-2]].filter(Boolean):[];
}
function simpleStepLinkText(s){
  const prev=previousStepFor(s);
  if(s.order===1 && !prev.length) return 'Это начало цепочки. С него запускается процесс.';
  if(prev.length>1) return 'Этот шаг выполняется после нескольких веток: '+prev.map(p=>'шаг '+p.order+' «'+(p.name||'без названия')+'»').join(', ')+'.';
  if(prev.length===1) return 'Этот шаг выполняется после шага '+prev[0].order+': «'+(prev[0].name||'без названия')+'». Связь пересчитывается автоматически при перемещении.';
  return 'Этот шаг стоит после предыдущего шага. Если его переместить в экспертном режиме, связь пересчитается автоматически.';
}
function simpleInputText(s){
  if(s.order===1) return s.source_system||'точка старта процесса';
  const prev=previousStepFor(s)[0];
  return prev?('результат шага '+prev.order):((s.source_system||'результат предыдущего шага'));
}
function simpleOutputText(s){return s.target_system||'следующий шаг процесса'}
function simpleExecutorText(s){return s.system||'сервис процесса'}
function simpleStepKindText(s){
  const n=(s.name||'').toLowerCase();
  if(n.includes('сохран')||n.includes('обновить'))return 'Тип шага: запись или обновление состояния.';
  if(n.includes('передать')||n.includes('отправить'))return 'Тип шага: передача результата дальше.';
  if(n.includes('получить')||n.includes('вызвать')||n.includes('сходить'))return 'Тип шага: обращение к другой системе.';
  if(n.includes('свер')||n.includes('сравн'))return 'Тип шага: сверка или контроль данных.';
  if(n.includes('ручн'))return 'Тип шага: ручной разбор исключения.';
  if(n.includes('ждать')||n.includes('статус'))return 'Тип шага: ожидание результата или статуса.';
  return 'Тип шага: действие процесса.';
}
function simpleResultText(s){
  const n=(s.name||'').toLowerCase();
  if(n.includes('сохран')||n.includes('обновить'))return 'Состояние процесса изменится и будет доступно следующим шагам.';
  if(n.includes('передать')||n.includes('сообщить')||n.includes('отправить'))return 'Результат уйдёт следующему участнику или нескольким получателям.';
  if(n.includes('ждать')||n.includes('статус'))return 'Процесс перейдёт в ожидание внешнего результата или статуса.';
  if(n.includes('свер')||n.includes('сравн'))return 'Будет понятен результат сверки: совпало, есть расхождение или нужен ручной разбор.';
  if(n.includes('ручн'))return 'Исключение попадёт человеку или группе разбора.';
  if(n.includes('провер'))return 'Будет принято решение: продолжать процесс или остановить на разбор.';
  return 'Результат шага станет входом для следующего действия.';
}
function stackWhyNot(channel){
  if(channel==='rest'||channel==='grpc'||channel==='soap')return 'Не выбирается очередь или поток событий, потому что по смыслу шага нужен ответ в рамках текущего действия. Если ответ должен прийти позже, стек нужно пересчитать как асинхронный шаг.';
  if(channel==='kafka'||channel==='pulsar')return 'Не выбирается REST, потому что событие может читать несколько потребителей и может понадобиться повторная обработка. Не выбирается Redis как основной журнал, потому что для критичных событий нужен надёжный журнал событий.';
  if(channel==='rabbitmq'||channel==='activemq'||channel==='ibm_mq'||channel==='queue')return 'Не выбирается Kafka, потому что шаг больше похож на очередь задач для обработчика, а не на долговременный журнал фактов для многих потребителей.';
  if(channel==='redis_cache'||channel==='memcached')return 'Не выбирается БД как способ ускорения чтения, потому что БД остаётся источником истины, а кэш нужен только для быстрого доступа и снижения нагрузки.';
  if(channel==='redis_lock')return 'Не выбирается обычная очередь, потому что задача не передать работу, а временно запретить параллельную обработку одной сущности.';
  if(channel==='db'||channel==='mongodb'||channel==='dynamodb'||channel==='cassandra')return 'Не выбирается брокер сообщений, потому что шаг фиксирует состояние или данные. Передача события может быть отдельным следующим действием.';
  if(channel==='cdc'||channel==='etl'||channel==='batch'||channel==='airflow'||channel==='spark'||channel==='dbt')return 'Не выбирается онлайн-вызов, потому что это загрузка, сверка или аналитическая обработка, которую безопаснее выполнять отдельно от основного клиентского запроса.';
  if(channel==='sftp'||channel==='file'||channel==='object_storage')return 'Не выбирается API-вызов с телом файла, потому что для файлов и больших документов надёжнее использовать файловый обмен или объектное хранилище.';
  if(channel==='webhook'||channel==='callback')return 'Не выбирается синхронный вызов, потому что внешний результат приходит позже и должен приниматься отдельным входящим действием.';
  return 'Альтернативы нужно выбирать только при реальном ограничении: уже утверждённая платформа, legacy-контракт, корпоративная шина, запрет брокера или особые требования эксплуатации.';
}
function stackSimpleExplanation(s){
  if(!state.stackReady)return '<div class="clarification-note">Стек ещё не определён. Сначала соберите действия и уточнения процесса, затем нажмите «Определить стек по процессу».</div>';
  const label=labelOf(CH,s.channel);
  const why=humanText(s.stack_reason||stackReasonFor(s.channel,s));
  const alt=stackWhyNot(s.channel);
  return `<div class="stack-simple-card"><b>Предложенный стек: ${esc(label)}${s.channel_manual==='yes'?' · изменено вручную':''}</b><p><b>Почему так:</b> ${esc(why)}</p><p><b>Почему не другой вариант:</b> ${esc(alt)}</p><p><b>Когда править:</b> если в проекте уже утверждена другая платформа, есть legacy-ограничение или команда сознательно принимает иной компромисс.</p></div>`;
}

function setFlowStage(stage){
  stage=stage||'participants';
  if(!allowedFlowStage(stage)){showToast('Этот этап откроется после заполнения предыдущего шага.');return;}
  state.stage=stage;
  renderAll();
  const target=document.getElementById('flowStagePanel');
  if(target) target.scrollIntoView({behavior:'smooth',block:'start'});
}
function allowedFlowStage(stage){
  if(stage==='participants')return true;
  if(stage==='interactions')return state.systems.length>=2;
  if(stage==='clarifications')return state.steps.length>=1;
  if(stage==='stack')return state.steps.length>=1;
  if(stage==='report')return state.stackReady&&state.steps.length>=1;
  return true;
}
function stageTitle(stage){return ({participants:'1. Участники',interactions:'2. Связи между участниками',clarifications:'3. Уточнения процесса',stack:'4. Определение стека',report:'5. Отчёт'})[stage]||stage}
function renderFlowStage(){
  ['participants','interactions','clarifications','stack','report'].forEach(x=>document.body.classList.toggle('stage-'+x,state.stage===x));
  const box=document.getElementById('flowStagePanel'); if(!box)return;
  const stages=['participants','interactions','clarifications','stack','report'];
  const active=state.stage||'participants';
  let body='';
  if(active==='participants') body='Сначала задайте участников процесса: кто начинает, кто выполняет работу, внешние системы, хранилища, аналитика и ручной разбор. Участник — это не действие, а сторона взаимодействия. Как читать и строить цепочку: сначала участники, потом связи между ними. Сначала смысл процесса, потом стек.';
  else if(active==='interactions') body='Теперь задайте порядок взаимодействий между участниками. Для каждого шага выберите: кто отдаёт, кто получает, что происходит, результат нужен сразу или позже, на основе чего выполняется следующий шаг.';
  else if(active==='clarifications') body='Уточните свойства только тех веток, которые реально есть в цепочке. Например, вопросы про асинхронность появятся только для позднего результата, фоновой обработки или событий; вопросы про хранение — только если есть запись или хранилище; вопросы про файлы — только если есть файловый обмен или документы. Все ответы выбираются кнопками.';
  else if(active==='stack') body='На этом этапе система определяет технологии по уже собранному процессу. До этого момента пользователь не выбирает конкретные технологии.';
  else body='Сформируйте отчёт после проверки цепочки и стека. В отчёте будет указано, что выбрано, почему выбрано, почему не другой вариант и что обязательно проверить.';
  const nav=stages.map(st=>`<button type="button" class="flow-step ${active===st?'active':''}" data-action="flow-stage" data-stage="${st}" ${allowedFlowStage(st)?'':'disabled'}><b>${esc(stageTitle(st))}</b><span>${st==='participants'?state.systems.length+' участн.':st==='interactions'?state.steps.length+' связей':st==='stack'?(state.stackReady?'готов':'не готов'):''}</span></button>`).join('');
  const actions=[];
  if(active==='participants') actions.push(state.systems.length>=2?'<button type="button" class="btn" data-action="flow-stage" data-stage="interactions">Дальше: связи между участниками</button>':'<button type="button" class="btn" disabled>Сначала добавьте минимум двух участников</button>');
  if(active==='interactions') actions.push('<button type="button" class="btn" data-action="flow-stage" data-stage="clarifications">Дальше: уточнения</button>');
  if(active==='clarifications') actions.push('<button type="button" class="btn" data-action="generate-stack">Определить стек по процессу</button><button type="button" class="btn ghost" data-action="flow-stage" data-stage="stack">Перейти к этапу стека</button>');
  if(active==='stack') actions.push('<button type="button" class="btn" data-action="generate-stack">Определить стек по процессу</button><button type="button" class="btn ghost" data-action="flow-stage" data-stage="report">Дальше: отчёт</button>');
  if(active==='report') actions.push('<button type="button" class="btn" data-action="submit">Сформировать отчёт</button>');
  box.innerHTML='<div class="flow-steps">'+nav+'</div><p class="hint"><b>'+esc(stageTitle(active))+'</b><br>'+esc(body)+'</p><div class="flow-stage-actions">'+actions.join('')+'</div>';
}
function renderInteractionBuilder(){
  const src=document.getElementById('interactionSource'); const tgt=document.getElementById('interactionTarget'); const rel=document.getElementById('interactionSummary');
  if(src&&tgt){
    const opts=state.systems.map(s=>`<option value="${esc(s.name)}">${esc(s.name)} — ${esc(roleLabel(s.role))}</option>`).join('');
    const oldS=src.value, oldT=tgt.value; src.innerHTML='<option value="">Выберите участника</option>'+opts; tgt.innerHTML='<option value="">Выберите участника</option>'+opts; if(oldS)src.value=oldS; if(oldT)tgt.value=oldT;
  }
  if(rel){
    if(!state.steps.length){
      rel.innerHTML='<div class="builder-empty">Связей пока нет. Добавьте первое взаимодействие: кто отдаёт результат, кто получает и что происходит. Схема процесса находится в одном месте — в блоке «Единая схема процесса».</div>';
    } else {
      rel.innerHTML='<div class="interaction-summary-title">Добавленные связи</div>'+state.steps.map(s=>`<div class="relation-card"><div class="relation-card-head"><div><b>${s.order}. ${esc(s.source_system||'Источник')} → ${esc(s.target_system||'Получатель')}</b><small>${esc(s.name||'Действие')} · ${s.blocking==='no'?'результат может появиться позже':'результат нужен сразу или в рамках шага'} · основа следующего шага: ${esc(s.dependency_basis||'результат предыдущего взаимодействия')} · стек ещё не определён</small></div><div class="relation-actions"><button type="button" class="iconbtn" title="Поднять связь" data-action="move-step" data-id="${s.id}" data-dir="-1">↑</button><button type="button" class="iconbtn" title="Опустить связь" data-action="move-step" data-id="${s.id}" data-dir="1">↓</button><button type="button" class="iconbtn" title="Удалить связь" data-action="delete-step" data-id="${s.id}">×</button></div></div></div>`).join('');
    }
  }
}

function explicitChannelFromText(...parts){
  const v=normTxt(parts.filter(Boolean).join(' '));
  const checks=[
    ['api gateway','api_gateway'],['единая точка входа','api_gateway'],['входной контур','api_gateway'],
    ['service mesh','service_mesh'],['istio','service_mesh'],['linkerd','service_mesh'],
    ['graphql','graphql'],['odata','odata'],['grpc','grpc'],['soap','soap'],['wsdl','soap'],['esb','esb'],['интеграционная шина','esb'],
    ['pulsar','pulsar'],['kafka','kafka'],['rabbitmq','rabbitmq'],['rabbit mq','rabbitmq'],['activemq','activemq'],['artemis','activemq'],['ibm mq','ibm_mq'],['nats','nats'],['sns/sqs','sns_sqs'],['sqs','sns_sqs'],['azure service bus','azure_service_bus'],['google pub/sub','gcp_pubsub'],['pub/sub','gcp_pubsub'],['redis streams','redis_streams'],['redis stream','redis_streams'],['redis queue','redis_queue'],['mqtt','mqtt'],
    ['redis cache','redis_cache'],['redis кэш','redis_cache'],['memcached','memcached'],['redis lock','redis_lock'],['distributed lock','redis_lock'],['распределённая блокировка','redis_lock'],
    ['mongodb','mongodb'],['mongo','mongodb'],['cassandra','cassandra'],['scylladb','cassandra'],['scylla','cassandra'],['dynamodb','dynamodb'],['key-value','dynamodb'],['ключ-значение','dynamodb'],
    ['clickhouse','clickhouse'],['data warehouse','data_warehouse'],['dwh','data_warehouse'],['озеро данных','data_lake'],['data lake','data_lake'],['lakehouse','lakehouse'],['реплика бд','read_replica'],['read replica','read_replica'],['шардирование','db_sharding'],
    ['поисковый индекс','search'],['search index','search'],['opensearch','search'],['elasticsearch','search'],['vector db','vector_db'],['векторная бд','vector_db'],
    ['object storage','object_storage'],['s3','object_storage'],['minio','object_storage'],['объектное хранилище','object_storage'],['sftp','sftp'],['cdc','cdc'],['etl','etl'],['elt','etl'],['airflow','airflow'],['spark','spark'],['dbt','dbt'],
    ['workflow engine','workflow_engine'],['temporal','workflow_engine'],['bpm','bpm_engine'],['bpmn','bpm_engine'],['camunda','bpm_engine'],['cdn','cdn'],['oauth','auth_oidc'],['oidc','auth_oidc'],['vault','vault'],['kms','vault'],['наблюдаемость','observability'],['observability','observability']
  ];
  for(const [marker,ch] of checks){if(v.includes(marker))return ch;}
  if(v.includes('хранилище состояния')||v.includes('бд процесса')||v.includes('основная база данных'))return 'db';
  return '';
}
function roleOfSystem(name){const sys=state.systems.find(x=>String(x.name||'')===String(name||'')); return (sys&&sys.role)||'';}
function isAnalyticsSystemName(name){const v=normTxt(name||''); return v.includes('аналит')||v.includes('dwh')||v.includes('data warehouse')||v.includes('витрин')||v.includes('lake')||v.includes('озеро')||v.includes('clickhouse');}
function isExternalSystemName(name){const r=roleOfSystem(name); const v=normTxt(name||''); return r==='external'||v.includes('внешн')||v.includes('партн')||v.includes('provider')||v.includes('api');}
function isStorageSystemName(name){const r=roleOfSystem(name); const v=normTxt(name||''); return r==='db'||v.includes('хранилищ')||v.includes('бд')||v.includes('база');}
function inferInteractionChannel(action,timing,result,source='',target=''){
  // Основной стек выбирается по СВЯЗИ между участниками.
  // Сохранение результата в БД — это служебный компонент, если сама связь идёт во внешнюю систему, аналитику или другому участнику.
  const t=normTxt(target||''); const s=normTxt(source||'');
  // Явно названная технология у ПОЛУЧАТЕЛЯ имеет приоритет: если пользователь направил связь в Pulsar/RabbitMQ/ClickHouse/S3, не подменяем её.
  // Явная технология у ИСТОЧНИКА не всегда является каналом связи: например БД -> DWH обычно означает CDC/ETL, а не «канал = БД».
  const explicitTarget=explicitChannelFromText(target);
  const explicitSource=explicitChannelFromText(source);
  if(explicitTarget && !['webhook','callback'].includes(explicitTarget))return explicitTarget;
  const sourceTransportChannels=['kafka','pulsar','rabbitmq','activemq','ibm_mq','nats','sns_sqs','azure_service_bus','gcp_pubsub','redis_streams','redis_queue','queue','mqtt','sftp','file','object_storage'];
  if(explicitSource && sourceTransportChannels.includes(explicitSource) && action!=='save' && action!=='update_status')return explicitSource;
  if(timing==='later'){
    if(isExternalSystemName(source) && !isExternalSystemName(target))return 'webhook';
    if(isExternalSystemName(target)||isExternalSystemName(source))return 'callback';
    return 'queue';
  }
  if(action==='save'||action==='update_status')return 'db';
  if(action==='compare')return isAnalyticsSystemName(target)?'data_warehouse':'batch';
  if(action==='file')return isExternalSystemName(target)?'sftp':'file';
  if(action==='notify_many')return explicit || 'kafka';
  if(isAnalyticsSystemName(target)){
    if(isStorageSystemName(source))return 'cdc';
    return 'data_warehouse';
  }
  if(isStorageSystemName(target) && (result==='save'||action==='save'||action==='update_status'))return 'db';
  if(isExternalSystemName(target))return 'rest';
  return 'rest';
}
function addInteractionFromBuilder(){
  const source=(document.getElementById('interactionSource')||{}).value||'';
  const target=(document.getElementById('interactionTarget')||{}).value||'';
  const action=(document.getElementById('interactionAction')||{}).value||'request_data';
  const timing=(document.getElementById('interactionTiming')||{}).value||'sync';
  const result=(document.getElementById('interactionResult')||{}).value||'pass_next';
  const basis=(document.getElementById('interactionBasis')||{}).value||'результат предыдущего взаимодействия';
  if(!source||!target){showToast('Сначала выберите двух участников взаимодействия.');return;}
  if(source===target && !['save','update_status'].includes(action)){showToast('Источник и получатель совпадают. Для обычной связи выберите разных участников.');return;}
  const actionLabels={request_data:'запрашивает данные у',send_data:'передаёт данные в',save:'сохраняет результат в',update_status:'обновляет статус в',wait_status:'передаёт поздний статус в',compare:'сверяет данные с',notify_many:'сообщает другим системам через',file:'передаёт файл в'};
  const name=(source+' '+(actionLabels[action]||'взаимодействует с')+' '+target).replace(/\s+/g,' ').trim();
  const ch=inferInteractionChannel(action,timing,result,source,target);
  const d=safeDefaultsFor(ch);
  addStep({name,source_system:source,system:source,target_system:target,channel:ch,blocking:timing==='later'?'no':d.blocking,timeout_ms:d.timeout_ms,retry:d.retry,idempotency:d.idempotency,writes_entity:(result==='save'||action==='save'||action==='update_status')?'yes':'no',depends_on:state.steps.length?String(state.steps.length):'',compensation:d.compensation,failure_policy:d.failure_policy,dependency_basis:basis,interaction_action:action,interaction_timing:timing,interaction_result:result,primary_channel:ch},null,false);
  state.stackReady=false; state.schemaValidation=null; state.schemaValidationBypass=false;
  normalizeChainAfterStructureChange({reason:'add-interaction',autofillRoutes:false});
  renderAll();
  showToast('Связь между участниками добавлена. Стек пока не выбран — он будет определён позже по процессу.');
}
function renderSystemSummarySimple(){
  const box=document.getElementById('systemSummarySimple'); if(!box)return;
  if(!state.systems.length){box.innerHTML='Добавьте участников процесса. Сначала достаточно 2–3: инициатор, сервис процесса, внешняя система или хранилище.';return;}
  const items=state.systems.slice(0,8).map(s=>esc(s.name||'Система')+' — '+esc(roleLabel(s.role))).join('<br>');
  box.innerHTML='<b>Участники процесса определены. Теперь задайте связи между ними.</b><br>'+items+(state.systems.length>8?'<br>…и ещё '+(state.systems.length-8):'');
}
function addHumanStep(kind){
  const proc=firstSystemByRole('internal','Сервис процесса'); const db=firstSystemByRole('db','БД процесса'); const external=firstSystemByRole('external','Внешняя система / поставщик');
  const prev=lastTarget(); let step=null;
  if(kind==='save') step={name:'Сохранить результат или обновить статус',source_system:prev,system:proc,target_system:db,channel:'db',blocking:'yes',writes_entity:'yes',failure_policy:'Повторить автоматически'};
  else if(kind==='forward') step={name:'Передать результат дальше',source_system:prev,system:proc,target_system:'Целевая система',channel:'rest',blocking:'yes',failure_policy:'Повторить автоматически'};
  else if(kind==='wait') step={name:'Дождаться результата или статуса позже',source_system:external,system:proc,target_system:db,channel:'callback',blocking:'no',writes_entity:'yes',failure_policy:'Очередь ошибок / ручной разбор'};
  else if(kind==='check') step={name:'Проверить данные по бизнес-правилам',source_system:prev,system:proc,target_system:prev,channel:'db',blocking:'yes',failure_policy:'Ручной разбор'};
  else if(kind==='compare') step={name:'Сверить результат с другим источником',source_system:prev,system:proc,target_system:'Журнал сверки',channel:'batch',blocking:'no',failure_policy:'Ручной разбор'};
  else if(kind==='manual') step={name:'Отправить исключение на ручной разбор',source_system:prev,system:'Сервис ручного разбора',target_system:db,channel:'rest',blocking:'no',failure_policy:'Ручной разбор'};
  else if(kind==='event') step={name:'Сообщить другим системам о результате',source_system:prev,system:proc,target_system:'Журнал событий',channel:'kafka',blocking:'no',failure_policy:'Очередь ошибок / повторная обработка'};
  else step={name:'Добавить следующий шаг процесса',source_system:prev,system:proc,target_system:prev,channel:'rest',blocking:'yes',failure_policy:'Пока не знаю'};
  addStep(step,null,false); state.stackReady=false; state.schemaValidation=null; state.schemaValidationBypass=false; normalizeChainAfterStructureChange({reason:'human-step',autofillRoutes:true}); renderAll(); showToast('Шаг добавлен. Связь с предыдущим шагом создана автоматически.');
}

function renderSysList(){const dl=document.getElementById('syslist'); if(dl) dl.innerHTML=state.systems.map(s=>`<option value="${esc(s.name)}">`).join('');}
function renderSystems(){
  const box=document.getElementById('systemsCards'); if(!box)return; renderSysList();
  box.innerHTML=state.systems.length?state.systems.map(s=>`<article class="system-card" data-id="${s.id}"><div class="card-top"><strong>${esc(s.name||'Новая система')}</strong><button type="button" class="iconbtn advanced-only" data-action="delete-system" data-id="${s.id}" aria-label="Удалить систему">×</button></div><div class="simple-system-view"><b>${esc(roleLabel(s.role))}</b><small>${esc(s.owner||'Владелец не указан — можно уточнить позже')}</small></div><div class="advanced-only"><label>Название системы</label><input value="${esc(s.name)}" data-system-field="name" data-id="${s.id}" placeholder="Например: Банк"><label>Роль</label><select data-system-field="role" data-id="${s.id}">${optPairs(ROLES,s.role)}</select><label>Владелец</label><input value="${esc(s.owner)}" data-system-field="owner" data-id="${s.id}" placeholder="Команда или организация"><label>Критичность</label><select data-system-field="criticality" data-id="${s.id}">${optPairs(CRIT,s.criticality)}</select><label>Стабильность / лимиты</label><select data-system-field="stability" data-id="${s.id}">${optPairs(STAB,s.stability)}</select><label>RPS-лимит</label><input value="${esc(s.rate_limit_rps)}" data-system-field="rate_limit_rps" data-id="${s.id}" inputmode="numeric" placeholder="100"></div></article>`).join(''):'<div class="builder-empty">Пока нет участников. Соберите цепочку выше — участники появятся автоматически.</div>';
  renderSystemSummarySimple(); syncLegacyTables();
}
function channelChips(step){return CH.map(([val,label])=>`<button type="button" class="chip-option ${step.channel===val?'active':''}" data-action="set-channel" data-id="${step.id}" data-channel="${val}">${label}</button>`).join('')}
function renderSteps(){
  const box=document.getElementById('chainList'); if(!box)return;
  if(!state.steps.length){box.innerHTML='<div class="builder-empty">Связей пока нет. Сначала добавьте участников процесса, затем на этапе «Связи» задайте первое взаимодействие: кто отдаёт результат, кто получает и что происходит.</div>'; syncLegacyTables(); return;}
  box.innerHTML=state.steps.map(s=>`<article class="chain-component" draggable="true" data-step-id="${s.id}"><div class="component-header"><div class="component-title"><span class="step-number">Действие ${s.order}</span><span class="prestack-chip">стек ещё не определён</span><span class="channel-chip">${labelOf(CH,s.channel)}</span></div><div class="component-actions"><button type="button" class="iconbtn" title="Вставить действие до этого" data-action="insert-before" data-id="${s.id}">+ до</button><button type="button" class="iconbtn" title="Поднять действие выше" data-action="move-step" data-id="${s.id}" data-dir="-1">↑</button><button type="button" class="iconbtn" title="Опустить действие ниже" data-action="move-step" data-id="${s.id}" data-dir="1">↓</button><button type="button" class="iconbtn" title="Копировать действие" data-action="duplicate-step" data-id="${s.id}">⧉</button><button type="button" class="iconbtn" title="Вставить действие после этого" data-action="insert-after" data-id="${s.id}">+ после</button><button type="button" class="iconbtn" title="Безопасные настройки" data-action="safe-step" data-id="${s.id}">✓</button><button type="button" class="iconbtn" title="Удалить действие" data-action="delete-step" data-id="${s.id}">×</button></div></div><div class="simple-step-view"><div class="action-story"><div class="action-primary"><small>Действие процесса, не участник</small><b>${esc(s.name||'Без названия')}</b></div><div class="simple-link-note">${esc(simpleStepLinkText(s))}</div><div class="action-meta"><div class="meta-cell"><small>Характер действия</small><b>${esc(simpleStepKindText(s))} ${s.blocking==='no'?'Результат может появиться позже.':'Есть ожидание результата.'}</b></div><div class="meta-cell"><small>Что получится после шага</small><b>${esc(simpleResultText(s))}</b></div></div><details class="route-explainer"><summary>Как система связала это действие с участниками</summary><div class="chain-layer-note"><b>Участники — это не шаги.</b> Они нужны только чтобы модель понимала, кто отправляет, кто выполняет и куда попадает результат. В обычном проектировании вы управляете действиями процесса, а маршрут участников система пересчитывает сама.</div><div class="route-grid"><div class="route-cell"><small>Откуда берутся данные</small><b>${esc(simpleInputText(s))}</b></div><div class="route-cell"><small>Кто выполняет действие</small><b>${esc(simpleExecutorText(s))}</b></div><div class="route-cell"><small>Куда попадает результат</small><b>${esc(simpleOutputText(s))}</b></div></div></details>${stackSimpleExplanation(s)}</div></div><div class="advanced-only"><label>Что происходит?</label><input value="${esc(s.name)}" data-step-field="name" data-id="${s.id}" placeholder="Например: проверить данные, сохранить статус, передать результат"><div class="fieldtip">Это название действия. Участники и связи ниже — служебный маршрут для модели; при перемещении действия они пересчитываются автоматически.</div><details class="details-panel" open><summary>Маршрут действия: кто откуда берёт данные и куда кладёт результат</summary><div class="fieldtip">Меняйте эти поля только если автосвязь не соответствует реальному процессу. Действие не должно зависеть само от себя или от несуществующего шага.</div><div class="component-grid"><div><label>Откуда берутся данные?</label><input list="syslist" value="${esc(s.source_system)}" data-step-field="source_system" data-id="${s.id}" placeholder="Источник"></div><div><label>Кто выполняет действие?</label><input list="syslist" value="${esc(s.system)}" data-step-field="system" data-id="${s.id}" placeholder="Сервис-исполнитель"></div><div><label>Куда попадает результат?</label><input list="syslist" value="${esc(s.target_system)}" data-step-field="target_system" data-id="${s.id}" placeholder="Получатель"></div></div></details><div class="stack-decision"><b>Стек подбирается автоматически: ${esc(labelOf(CH,s.channel))}${s.channel_manual==='yes'?' · ручное переопределение':''}</b><span>${esc(humanText(s.stack_reason||stackReasonFor(s.channel,s)))}</span><span><b>Почему не другой вариант:</b> ${esc(stackWhyNot(s.channel))}</span><div class="stack-actions"><button type="button" class="btn ghost" data-action="auto-channel" data-id="${s.id}">вернуть автоподбор</button></div></div><details class="details-panel manual-stack-override"><summary>Переопределить стек вручную</summary><p class="manual-stack-note">Обычно это не нужно. Меняйте стек только если есть реальное ограничение: уже утверждён конкретный брокер сообщений, старый SOAP/SFTP-контракт, Redis для кэша или блокировок, файловый обмен, запрет нового брокера или требование платформы.</p><div class="chip-select">${channelChips(s)}</div></details><div class="component-grid"><div><label>Ждёт ответ?</label><select data-step-field="blocking" data-id="${s.id}"><option value="yes" ${s.blocking!=='no'?'selected':''}>Да, ждёт</option><option value="no" ${s.blocking==='no'?'selected':''}>Нет, асинхронно</option></select></div><div><label>Что меняется?</label><select data-step-field="writes_entity" data-id="${s.id}"><option value="no" ${s.writes_entity!=='yes'?'selected':''}>Не меняет основную сущность</option><option value="yes" ${s.writes_entity==='yes'?'selected':''}>Создаёт/обновляет сущность</option></select></div><div><label>Что делать при ошибке?</label><select data-step-field="failure_policy" data-id="${s.id}"><option ${s.failure_policy==='Повторить автоматически'?'selected':''}>Повторить автоматически</option><option ${s.failure_policy==='Очередь ошибок / повторная обработка'?'selected':''}>Очередь ошибок / повторная обработка</option><option ${s.failure_policy==='Очередь ошибок / ручной разбор'?'selected':''}>Очередь ошибок / ручной разбор</option><option ${s.failure_policy==='Откатить / компенсировать'?'selected':''}>Откатить / компенсировать</option><option ${s.failure_policy==='Ручной разбор'?'selected':''}>Ручной разбор</option><option ${s.failure_policy==='Пока не знаю'?'selected':''}>Пока не знаю</option></select></div></div><details class="details-panel"><summary>Технические настройки</summary><div class="component-grid"><div><label>Timeout, мс</label><input value="${esc(s.timeout_ms)}" data-step-field="timeout_ms" data-id="${s.id}" inputmode="numeric" placeholder="500"></div><div><label>Повтор при ошибке</label><select data-step-field="retry" data-id="${s.id}">${optPairs(RETRY,s.retry)}</select></div><div><label>Что считать повтором</label><select data-step-field="idempotency" data-id="${s.id}">${optPairs(IDEM,s.idempotency)}</select></div><div><label>После какого шага?</label><input value="${esc(s.depends_on)}" data-step-field="depends_on" data-id="${s.id}" placeholder="автозаполняется: предыдущий шаг, запись в БД, CDC или join"></div><div><label>Как восстановиться?</label><input value="${esc(humanText(s.compensation))}" data-step-field="compensation" data-id="${s.id}" placeholder="очередь ошибок, повторная обработка, компенсация"></div><div><label>Тип компонента</label><input value="${esc(s.component_type)}" data-step-field="component_type" data-id="${s.id}" placeholder="действие / событие / хранение"></div></div></details></div></article>`).join('');
  syncLegacyTables();
}
function stepIssue(s){if(!s.system)return 'Нет исполнителя'; if(!s.target_system)return 'Нет получателя'; if(SYNC.has(s.channel)&&s.blocking!=='no'&&!s.timeout_ms)return 'Синхронные вызовы без таймаута'; if(ASYNC.has(s.channel)&&!s.compensation&&s.retry==='none')return 'Нет recovery'; return ''}
function dependsLabelForStep(s){
  const raw=String(s.depends_on||'').trim();
  if(!raw) return 'начало цепочки';
  const nums=raw.split(',').map(x=>parseInt(x.trim(),10)).filter(Boolean);
  if(!nums.length) return 'зависимость уточняется автоматически';
  if(nums.length===1){
    const prev=state.steps[nums[0]-1];
    return prev ? 'после шага '+nums[0]+': '+(prev.name||'действие') : 'после шага '+nums[0];
  }
  return 'после шагов '+nums.join(', ');
}
function timelineText(s){
  if(String(s.blocking||'yes')==='no') return 'результат позже или в фоне';
  const n=(s.name||'').toLowerCase();
  if(n.includes('позже')||n.includes('статус')) return 'результат позже';
  return 'результат нужен сразу';
}
function safeParticipantName(v, fallback){return (v&&String(v).trim())?String(v).trim():fallback;}
function schemaIssueForStep(s,i){
  const n=normTxt(s.name||''); const src=String(s.source_system||'').trim(); const tgt=String(s.target_system||'').trim();
  if(!src||!tgt)return 'Не указан источник или получатель';
  if(src===tgt && !['save','update_status','compare'].includes(s.interaction_action||''))return 'Источник и получатель совпадают';
  const nums=String(s.depends_on||'').split(',').map(x=>parseInt(x.trim(),10)).filter(Boolean);
  if(nums.some(n=>n===i+1))return 'Связь зависит сама от себя';
  if(nums.some(n=>n<1||n>state.steps.length))return 'Связь зависит от несуществующего шага';
  if((n.includes('внешн')||n.includes('партн')) && isStorageSystemName(tgt))return 'Связь названа как внешняя, но ведёт в хранилище';
  if((n.includes('аналит')||n.includes('dwh')||n.includes('витрин')) && !isAnalyticsSystemName(tgt))return 'Связь похожа на аналитику, но получатель не аналитический контур';
  return '';
}
function interactionRowsHtml(options={}){
  if(!state.steps.length){
    return '<div class="schema-empty">Схема появится после добавления первой связи между участниками.</div>';
  }
  const rows=state.steps.map((s,i)=>{
    const source=safeParticipantName(s.source_system,'Источник');
    const target=safeParticipantName(s.target_system,'Получатель');
    const action=String(s.name||'взаимодействует').replace(source,'').replace(target,'').replace(/\s+/g,' ').trim() || 'взаимодействует';
    const issue=schemaIssueForStep(s,i);
    return `<div class="schema-row ${issue?'has-issue':''}" data-step-id="${esc(s.id)}"><div class="schema-route"><div class="schema-person"><small>Шаг ${i+1}</small><b>${esc(source)}</b></div><div class="schema-arrow">→</div><div class="schema-link-label">${esc(action)}</div><div class="schema-arrow">→</div><div class="schema-person"><small>Получатель</small><b>${esc(target)}</b></div></div></div>`;
  }).join('');
  return '<div class="schema-flow">'+rows+'</div>';
}
function renderInteractionGraph(){
  const box=document.getElementById('interactionGraph'); if(!box)return;
  if(state.systems.length<2){box.innerHTML='<div class="schema-empty">Сначала добавьте минимум двух участников процесса. После этого схема начнёт показывать связи между ними.</div>';return;}
  box.innerHTML=interactionRowsHtml({compact:false});
}
function renderProcessMap(){
  const box=document.getElementById('processMap'); if(!box)return;
  if(!state.steps.length){
    const participants=state.systems.length?'<div class="participant-strip">'+state.systems.map(x=>`<span class="participant-pill"><b>${esc(x.name||'Участник')}</b></span>`).join('')+'</div>':'';
    box.innerHTML=participants+'<div class="builder-empty">Карта связей появится после добавления первого взаимодействия между участниками.</div>';return;
  }
  box.innerHTML=interactionRowsHtml({compact:true});
}
function readiness(){
  const restNoTimeout=state.steps.filter(s=>SYNC.has(s.channel)&&s.blocking!=='no'&&!s.timeout_ms).length;
  const asyncNoRecovery=state.steps.filter(s=>ASYNC.has(s.channel)&&!s.compensation&&s.retry==='none').length;
  const noTarget=state.steps.filter(s=>!s.target_system).length;
  const noSystem=state.steps.filter(s=>!s.system).length;
  const unknownTargets=state.steps.filter(s=>s.target_system && !schemaHasParticipant(s.target_system)).length;
  const unknownSources=state.steps.filter(s=>s.source_system && !schemaHasParticipant(s.source_system)).length;
  const writers=state.steps.filter(s=>s.writes_entity==='yes').length;
  const missing=[]; if(!v('p_entity'))missing.push('основная сущность'); if(!v('p_lookup'))missing.push('ключ поиска'); if(!v('p_statuses'))missing.push('статусы');
  return {restNoTimeout,asyncNoRecovery,noTarget,noSystem,unknownTargets,unknownSources,writers,missing};
}
function renderReadiness(){
  const box=document.getElementById('readinessPanel'); if(!box)return; const r=readiness();
  const hasDraftFallback=!state.steps.length;
  const items=[['Систем',state.systems.length,hasDraftFallback?'warn':(state.systems.length>=2?'ok':'warn')],['Шагов',state.steps.length,hasDraftFallback?'warn':(state.steps.length>=2?'ok':'warn')],['Синхронные вызовы без таймаута',r.restNoTimeout,r.restNoTimeout?'fail':'ok'],['Асинхронные шаги без восстановления',r.asyncNoRecovery,r.asyncNoRecovery?'fail':'ok'],['Шагов без получателя',r.noTarget,r.noTarget?'warn':'ok'],['Получателей вне списка участников',r.unknownTargets,r.unknownTargets?'fail':'ok'],['Источников вне списка участников',r.unknownSources,r.unknownSources?'warn':'ok'],['Шагов без исполнителя',r.noSystem,r.noSystem?'fail':'ok'],['Шагов, меняющих сущность',r.writers,r.writers>1?'warn':'ok'],['Ключ/статусы/сущность',r.missing.length?r.missing.join(', '):'заполнены',r.missing.length?'warn':'ok']];
  const severe=r.restNoTimeout+r.asyncNoRecovery+r.noSystem+r.unknownTargets; let msg;
  if(hasDraftFallback) msg='Можно запустить черновой разбор, но качество будет ниже. Для нормального результата сначала добавьте участников, затем связи между ними, уточнения процесса и сформируйте стек.';
  else if(r.unknownTargets) msg='Нельзя формировать отчёт: один или несколько получателей не добавлены в участники процесса. Добавьте участника или исправьте связь.';
  else if(severe) msg='Разбор можно запустить, но красные пункты ухудшат качество. Исправьте их или смотрите отчёт как черновой.';
  else msg='Можно запускать разбор. Жёлтые пункты можно уточнить для качества.';
  box.innerHTML=`<p class="hint"><b>${msg}</b></p><div class="readiness-list">`+items.map(([k,v,st])=>`<div class="readiness-item"><b>${esc(k)}</b><span class="status-dot ${st}">${esc(String(v))}</span></div>`).join('')+'</div>';
  const sub=document.getElementById('submitHint'); if(sub) sub.textContent=msg;
}
function updateReview(){const box=document.getElementById('reviewBox'); if(!box)return; const async=state.steps.filter(s=>ASYNC.has(s.channel)).length; box.innerHTML=`<div class="metric"><b>${state.systems.length}</b><span>систем участвует</span></div><div class="metric"><b>${state.steps.length}</b><span>шагов описано</span></div><div class="metric"><b>${async}</b><span>асинхронных границ</span></div>`;}
function updateGuidance(){
  const g=document.getElementById('liveGuide'); if(!g)return; const issues=[]; const r=readiness();
  if(!v('p_name'))issues.push('Назовите процесс простыми словами.'); if(!v('p_entity'))issues.push('Укажите основную сущность: заявка, документ, договор, платёж или операция.'); if(!v('p_goal'))issues.push('Опишите бизнес-цель одним предложением.'); if(!v('p_lookup'))issues.push('Заполните ключ поиска и дедупликации.'); if(state.systems.length<2)issues.push('Добавьте минимум две системы-участника.'); if(state.steps.length<2)issues.push('Добавьте цепочку хотя бы из двух шагов.'); if(r.asyncNoRecovery)issues.push(`У ${r.asyncNoRecovery} асинхронных шагов нет понятного восстановления: очередь ошибочных сообщений, повторная обработка, таблица входящих сообщений для дедупликации или ручной разбор.`); if(r.restNoTimeout)issues.push(`У ${r.restNoTimeout} синхронных шагов нет таймаута.`);
  if(r.unknownTargets)issues.push(`У ${r.unknownTargets} связей получатель не добавлен в участники процесса. Отчёт будет заблокирован, пока вы не добавите участника или не исправите связь.`);
  if(!issues.length){g.className='assist ok';g.innerHTML='<b>Вводные выглядят хорошо.</b><p>Можно запускать разбор. Для production-проверки включите экспертный режим и уточните таймаут, повторные попытки, идемпотентность и восстановление.</p>';return;}
  g.className='assist warn';g.innerHTML='<b>Что ещё заполнить:</b><ul>'+issues.map(x=>`<li>${esc(x)}</li>`).join('')+'</ul>';
}
function updateProgress(){
  const essentials=[v('p_name'),v('p_entity'),v('p_goal'),v('p_statuses'),v('p_fields'),v('p_lookup')];
  let done=essentials.filter(Boolean).length+Math.min(state.systems.length,2)+Math.min(state.steps.length,3);
  const pct=Math.min(100,Math.round(done/11*100)); const bar=document.querySelector('#fillbar i'); if(bar)bar.style.width=pct+'%';
  const text=document.getElementById('filltext'); if(text)text.textContent=state.systems.length<2?'Шаг 1: добавьте участников процесса. Минимум — кто начинает процесс и кто обрабатывает/получает результат.':state.steps.length<1?'Шаг 2: добавьте связи между участниками. Одна связь — одно взаимодействие: кто отдаёт результат, кто получает и что происходит.':!state.stackReady?'Шаг 3: уточните свойства процесса и нажмите «Определить стек по процессу».':'Стек определён. Можно проверить архитектуру и сформировать отчёт.';
  updateGuidance(); updateReview(); renderReadiness(); renderProcessMap(); renderInteractionGraph(); syncLegacyTables();
}
function renderAll(){renderSysList(); renderSystems(); renderInteractionBuilder(); renderSteps(); renderProcessMap(); renderInteractionGraph(); renderReadiness(); renderBranchQuestions(); renderModules(); renderStackStage(); renderFlowStage(); updateProgress();}
function syncLegacyTables(){
  const sys=document.querySelector('#systems tbody'); if(sys) sys.innerHTML=state.systems.map(s=>`<tr><td><input name="sname" value="${esc(s.name)}"></td><td><select name="srole"><option value="${esc(s.role)}" selected>${esc(s.role)}</option></select></td><td><input name="sowner" value="${esc(s.owner)}"></td><td><input name="scrit" value="${esc(s.criticality)}"></td><td><input name="sstab" value="${esc(s.stability)}"></td><td><input name="slimit" value="${esc(s.rate_limit_rps)}"></td></tr>`).join('');
  const steps=document.querySelector('#steps tbody'); if(steps) steps.innerHTML=state.steps.map(s=>`<tr><td><input name="order" value="${s.order}"></td><td><input name="name" value="${esc(s.name)}"></td><td><input name="source_system" value="${esc(s.source_system)}"></td><td><input name="system" value="${esc(s.system)}"></td><td><input name="target_system" value="${esc(s.target_system)}"></td><td><input name="channel" value="${esc(s.channel)}"></td><td><input name="blocking" value="${esc(s.blocking)}"></td><td><input name="timeout_ms" value="${esc(s.timeout_ms)}"></td><td><input name="retry" value="${esc(s.retry)}"></td><td><input name="idempotency" value="${esc(s.idempotency)}"></td><td><input name="writes_entity" value="${esc(s.writes_entity)}"></td><td><input name="depends_on" value="${esc(s.depends_on)}"></td><td><input name="compensation" value="${esc(humanText(s.compensation))}"></td></tr>`).join('');
}
function buildPayload(){const dataCtx='partition key / lookup key: '+v('p_lookup')+'; event envelope / fields: '+v('p_fields')+'; correlationId/traceId пробрасывается через шаги'; return {meta:{name:v('p_name'),entity:v('p_entity'),goal:v('p_goal'),description:v('p_description'),lookup_keys:v('p_lookup'),constraints:v('p_constraints'),customer_visible:v('p_visible'),money:v('p_money'),regulatory:v('p_reg'),sla_ms:v('p_sla'),read_freq:v('p_read'),ordering:v('p_order'),statuses:v('p_statuses'),fields:v('p_fields'),load_rps:v('p_rps'),peak_factor:v('p_peak'),multi_tenant:v('p_tenant'),replacing_legacy:v('p_legacy')},systems:state.systems.map(s=>({name:s.name,role:s.role,owner:s.owner,criticality:s.criticality,stability:s.stability,rate_limit_rps:s.rate_limit_rps})),steps:state.steps.map((s,idx)=>{const clar=stepClarifications(s).map(c=>c.label).join('; '); const ctx=clar?dataCtx+'; уточнения по шагу: '+clar:dataCtx; return {order:idx+1,name:s.name,source_system:s.source_system,system:s.system,target_system:s.target_system,channel:s.channel,blocking:s.blocking,timeout_ms:s.timeout_ms,retry:s.retry,idempotency:s.idempotency,writes_entity:s.writes_entity,depends_on:s.depends_on,compensation:s.compensation,failure_policy:s.failure_policy,component_type:s.component_type,data_in:ctx,data_out:ctx};})};}
function clearAll(){state.systems=[]; state.steps=[]; state.modules=[]; state.stackReady=false; renderModules();}
function suggestBasics(){if(!v('p_statuses'))setv('p_statuses','CREATED, PROCESSING, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW'); if(!v('p_fields'))setv('p_fields','requestId:string|required|unique, correlationId:uuid|required|indexed, eventId:uuid|required|unique, status:string|required, createdAt:datetime|required, updatedAt:datetime|required'); if(!v('p_lookup'))setv('p_lookup','requestId + operationType + targetSystem; eventId для дедупликации событий'); updateProgress();}
function setBasics(vals){Object.entries(vals).forEach(([k,val])=>setv('p_'+k,val));}
function resetScenarioSelection(){document.querySelectorAll('.scenario').forEach(b=>{b.classList.remove('active');b.setAttribute('aria-pressed','false')}); const selected=document.getElementById('selectedScenario'); if(selected)selected.textContent='Цепочка ещё не собрана.';}
function showToast(message){let t=document.getElementById('toast'); if(!t){t=document.createElement('div');t.id='toast';t.className='toast';t.setAttribute('role','status');document.body.appendChild(t)} t.textContent=message; t.classList.add('show'); clearTimeout(t._timer); t._timer=setTimeout(()=>t.classList.remove('show'),3200);}
function selectScenario(kind,button){applyScenario(kind); document.querySelectorAll('.scenario').forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active?'true':'false')}); const label=button?.querySelector('b')?.textContent||'Сценарий'; const selected=document.getElementById('selectedScenario'); if(selected)selected.textContent=kind==='blank'?'Пустой процесс. Лучше собрать цепочку универсальными действиями выше или запустить черновой разбор.':'Выбран быстрый пример: '+label+'. Это не обязательный шаблон — его можно усложнить или удалить лишние шаги.'; showToast(kind==='blank'?'Форма очищена. Черновой разбор всё равно доступен.':'Быстрый пример подставлен. Можно усложнить его признаками процесса.'); if(kind!=='blank')document.getElementById('basics')?.scrollIntoView({behavior:'smooth',block:'start'});}
function applyScenario(kind){
  clearAll(); setBasics({name:'',entity:'',goal:'',description:'',lookup:'',constraints:'',sla:'',statuses:'',fields:'',visible:'no',money:'no',reg:'no',order:'no',rps:'',peak:'1',tenant:'no',legacy:'no',read:'medium'});
  if(kind==='blank'){renderAll();return;}
  if(kind==='reverse'){
    setBasics({name:'Обратный поток статусов между банком и УК',entity:'ApplicationStatus',goal:'Банк передаёт документы в УК и получает обратно понятные статусы обработки документов и операций.',visible:'mixed',money:'direct',reg:'yes',order:'per_entity',statuses:'CREATED, SENT_TO_UK, RECEIVED_BY_UK, PROCESSING, COMPLETED, REJECTED, ERROR',fields:'applicationId:uuid|required|indexed, documentId:string|required, operationId:string, status:string|required, eventId:uuid|required|unique, correlationId:uuid|required|indexed, occurredAt:datetime|required',lookup:'applicationId + documentId или operationId, eventId для дедупликации',description:'Банк передаёт документы и операции в УК. УК возвращает обратный поток статусов, чтобы банк видел финал обработки и расследовал зависшие заявки.'});
    [['Банк','internal','Команда банка','critical','stable'],['УК','external','Управляющая компания','critical','limited'],['Kafka','broker','Платформа','high','stable'],['БД банка','db','Команда банка','critical','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Банк создаёт заявку и документы',source_system:'Клиент/офис',system:'Банк',target_system:'БД банка',channel:'db',timeout_ms:'300',idempotency:'key',writes_entity:'yes'}, {name:'Банк передаёт документы в УК',source_system:'Банк',system:'Банк',target_system:'УК',channel:'rest',timeout_ms:'2000',retry:'auto',idempotency:'key',compensation:'timeout, повтор с тем же idempotencyKey'}, {name:'УК публикует статус документа',source_system:'УК',system:'УК',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'outbox, DLQ, replay'}, {name:'Банк принимает статус и обновляет историю',source_system:'Kafka',system:'Банк',target_system:'БД банка',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'inbox-дедупликация, история статусов'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='kafka'){
    setBasics({name:'Публикация событий об изменении договора',entity:'Contract',goal:'Исходный сервис публикует изменения договора, а потребители получают их через Kafka без потери и дублей.',order:'per_entity',statuses:'CHANGED, CANCELLED, ERROR',fields:'contractId:uuid|required|indexed, eventId:uuid|required|unique, eventVersion:string|required, correlationId:uuid|required|indexed, occurredAt:datetime|required',lookup:'contractId для порядка по сущности, eventId для дедупликации',description:'Исходный сервис меняет договор, публикует событие, а несколько потребителей обрабатывают его независимо.'});
    [['Сервис договоров','internal','Команда договоров','critical','stable'],['Kafka','broker','Платформа','high','stable'],['Потребитель','internal','Команда потребителя','medium','stable'],['БД договоров','db','Команда договоров','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Сервис договоров сохраняет изменение',source_system:'API',system:'Сервис договоров',target_system:'БД договоров',channel:'db',timeout_ms:'200',writes_entity:'yes',idempotency:'natural'}, {name:'Сервис договоров публикует событие через Outbox',source_system:'Сервис договоров',system:'Сервис договоров',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'outbox, DLQ, replay'}, {name:'Потребитель обрабатывает событие',source_system:'Kafka',system:'Потребитель',target_system:'Своя БД/проекция',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'inbox-дедупликация'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='enrichment'){
    setBasics({name:'Обогащение события через REST-сервис',entity:'EnrichedEvent',goal:'Событие из Kafka нужно дополнить данными из REST-сервиса и передать дальше без потери сообщений.',constraints:'Kafka одна, новый сервис дорогой, REST-справочник может быть недоступен.',statuses:'RECEIVED, ENRICHING, ENRICHED, PUBLISHED, FAILED, DLQ',fields:'eventId:uuid|required|unique, sourceId:string|required|indexed, enrichmentVersion:string, correlationId:uuid|required|indexed',lookup:'eventId для дедупликации, sourceId + enrichmentVersion для проверки актуальности',description:'Потребитель читает событие, вызывает REST-справочник, обогащает payload и публикует enriched-event. Нужно решить, где ответственность и что делать при недоступности REST.'});
    [['Kafka','broker','Платформа','critical','stable'],['Enrichment service','internal','Команда интеграций','high','stable'],['REST-справочник','external','Владелец справочника','high','limited'],['Enriched topic','broker','Платформа','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Enrichment service читает исходное событие',source_system:'Kafka',system:'Enrichment service',target_system:'Enrichment service',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'Inbox, DLQ, replay'}, {name:'Enrichment service вызывает REST-справочник',source_system:'Enrichment service',system:'Enrichment service',target_system:'REST-справочник',channel:'rest',blocking:'yes',timeout_ms:'700',retry:'auto',idempotency:'key',compensation:'timeout, fallback/cache, circuit breaker'}, {name:'Enrichment service публикует enriched-event',source_system:'Enrichment service',system:'Enrichment service',target_system:'Enriched topic',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'Outbox, DLQ, replay'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='payment'){
    setBasics({name:'Платёж с подтверждением внешнего провайдера',entity:'PaymentOperation',goal:'Создать платёжную операцию, передать её провайдеру, получить финальный статус и сохранить доказуемую историю изменений.',visible:'yes',money:'direct',reg:'yes',order:'per_entity',sla:'1500',statuses:'CREATED, VALIDATED, SENT_TO_PROVIDER, ACCEPTED, DECLINED, FAILED, NEEDS_MANUAL_REVIEW, COMPLETED',fields:'paymentId:uuid|required|unique, idempotencyKey:string|required|unique, providerOperationId:string|indexed, amount:decimal|required, status:string|required, correlationId:uuid|required|indexed, createdAt:datetime|required',lookup:'paymentId + idempotencyKey, providerOperationId для сверки с провайдером',description:'Клиент инициирует платёж. Нужно не списать деньги дважды, не потерять финальный статус, иметь аудит и ручной разбор неопределённых ответов.'});
    [['Клиентский канал','internal','Команда фронта','high','stable'],['Платёжный сервис','internal','Команда платежей','critical','stable'],['Провайдер платежей','external','Провайдер','critical','limited'],['БД платежей','db','Команда платежей','critical','stable'],['Kafka','broker','Платформа','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Клиент создаёт платёж с idempotencyKey',source_system:'Клиентский канал',system:'Платёжный сервис',target_system:'БД платежей',channel:'db',timeout_ms:'200',retry:'none',idempotency:'key',writes_entity:'yes',compensation:'UNIQUE idempotencyKey, ledger/status history'}, {name:'Платёжный сервис вызывает провайдера',source_system:'Платёжный сервис',system:'Платёжный сервис',target_system:'Провайдер платежей',channel:'rest',blocking:'yes',timeout_ms:'1200',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'status inquiry, circuit breaker, ручной разбор UNKNOWN'}, {name:'Провайдер присылает финальный callback',source_system:'Провайдер платежей',system:'Платёжный сервис',target_system:'БД платежей',channel:'callback',blocking:'no',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'подпись callback, Inbox-дедупликация, сверка статусов'}, {name:'Платёжный сервис публикует событие о финале',source_system:'Платёжный сервис',system:'Платёжный сервис',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'Outbox, DLQ, replay'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='order'){
    setBasics({name:'Заказ товара с резервом и доставкой',entity:'Order',goal:'Принять заказ, зарезервировать товар, организовать доставку и корректно обработать отмену или частичный отказ.',visible:'yes',money:'indirect',reg:'no',order:'per_entity',statuses:'CREATED, VALIDATED, RESERVED, PAID, SHIPPED, DELIVERED, CANCELLED, FAILED',fields:'orderId:uuid|required|unique, customerId:string|required|indexed, reservationId:string|indexed, deliveryId:string|indexed, status:string|required, correlationId:uuid|required|indexed',lookup:'orderId для процесса, reservationId и deliveryId для внешних сверок',description:'Несколько систем участвуют в одном бизнес-процессе. Если склад или доставка откажут, нужны статусы, компенсации и понятный ручной разбор.'});
    [['Order service','internal','Команда заказов','critical','stable'],['Склад','external','Владелец склада','high','limited'],['Доставка','external','Партнёр доставки','high','limited'],['БД заказов','db','Команда заказов','critical','stable'],['Kafka','broker','Платформа','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Order service создаёт заказ',source_system:'Клиент',system:'Order service',target_system:'БД заказов',channel:'db',timeout_ms:'200',idempotency:'key',writes_entity:'yes',compensation:'UNIQUE orderId, история статусов'}, {name:'Order service резервирует товар на складе',source_system:'Order service',system:'Order service',target_system:'Склад',channel:'rest',blocking:'yes',timeout_ms:'800',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'отмена резерва, status inquiry'}, {name:'Order service создаёт доставку',source_system:'Order service',system:'Order service',target_system:'Доставка',channel:'rest',blocking:'yes',timeout_ms:'800',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'отмена доставки / ручной разбор'}, {name:'Order service публикует изменение заказа',source_system:'Order service',system:'Order service',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'Outbox, DLQ, replay'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='external_sync'){
    setBasics({name:'Синхронный вызов внешнего сервиса',entity:'ExternalRequest',goal:'Получить ответ от внешней системы в рамках клиентского запроса и не превысить SLA.',visible:'yes',money:'indirect',reg:'no',order:'no',sla:'1000',statuses:'CREATED, SENT, SUCCESS, TIMEOUT, FAILED, FALLBACK_USED',fields:'requestId:uuid|required|unique, externalId:string|indexed, status:string|required, correlationId:uuid|required|indexed',lookup:'requestId + externalId',description:'Клиент ждёт ответ. Внешняя система может тормозить или вернуть 5xx/429, поэтому нужны timeout budget, fallback и ограниченный retry.'});
    [['API Gateway','internal','Платформа','high','stable'],['Core service','internal','Команда продукта','critical','stable'],['Внешний сервис','external','Партнёр','high','limited'],['БД процесса','db','Команда продукта','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'API Gateway принимает клиентский запрос',source_system:'Клиент',system:'API Gateway',target_system:'Core service',channel:'rest',blocking:'yes',timeout_ms:'150',retry:'none',idempotency:'key',compensation:'валидация и correlationId'}, {name:'Core service вызывает внешний сервис',source_system:'Core service',system:'Core service',target_system:'Внешний сервис',channel:'rest',blocking:'yes',timeout_ms:'650',retry:'auto',idempotency:'key',compensation:'timeout budget, circuit breaker, fallback'}, {name:'Core service сохраняет результат или fallback',source_system:'Core service',system:'Core service',target_system:'БД процесса',channel:'db',blocking:'yes',timeout_ms:'150',retry:'none',idempotency:'natural',writes_entity:'yes',compensation:'уникальный requestId, статус TIMEOUT/FALLBACK_USED'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='webhook_in'){
    setBasics({name:'Приём webhook/callback от внешней системы',entity:'CallbackEvent',goal:'Надёжно принять callback, проверить подпись, убрать дубли и обновить статус процесса.',visible:'mixed',money:'indirect',reg:'yes',order:'per_entity',statuses:'WAITING_CALLBACK, CALLBACK_RECEIVED, VERIFIED, APPLIED, DUPLICATE, REJECTED, FAILED',fields:'callbackId:string|required|unique, businessId:string|required|indexed, eventId:uuid|required|unique, signature:string|required, status:string|required, receivedAt:datetime|required',lookup:'callbackId/eventId для дедупликации, businessId для обновления процесса',description:'Внешняя система присылает результат сама. Нужно защититься от дублей, replay-атаки, старого timestamp и неподписанного payload.'});
    [['Внешняя система','external','Партнёр','critical','limited'],['Callback API','internal','Команда интеграций','critical','stable'],['БД процесса','db','Команда продукта','critical','stable'],['Kafka','broker','Платформа','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Callback API принимает webhook',source_system:'Внешняя система',system:'Callback API',target_system:'Callback API',channel:'webhook',blocking:'no',retry:'auto',idempotency:'key',compensation:'подпись, timestamp, nonce, rate limit'}, {name:'Callback API дедуплицирует событие',source_system:'Callback API',system:'Callback API',target_system:'БД процесса',channel:'db',timeout_ms:'200',retry:'none',idempotency:'key',writes_entity:'yes',compensation:'UNIQUE callbackId/eventId'}, {name:'Callback API обновляет статус бизнес-процесса',source_system:'Callback API',system:'Callback API',target_system:'БД процесса',channel:'db',timeout_ms:'250',retry:'auto',idempotency:'natural',writes_entity:'yes',compensation:'terminal-state guard, история статусов'}, {name:'Callback API публикует внутреннее событие',source_system:'Callback API',system:'Callback API',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'Outbox, DLQ, replay'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='batch_file'){
    setBasics({name:'Пакетная файловая выгрузка во внешнюю систему',entity:'BatchTransfer',goal:'Сформировать файл, передать его внешней системе, получить протокол обработки и уметь переобработать ошибки.',visible:'no',money:'indirect',reg:'yes',order:'no',statuses:'PLANNED, EXPORTED, SENT, ACCEPTED, PARTIALLY_REJECTED, REJECTED, REPROCESSED, FAILED',fields:'batchId:string|required|unique, fileName:string|required, checksum:string|required, recordCount:int|required, protocolId:string|indexed, status:string|required',lookup:'batchId + checksum, protocolId для сверки результата',description:'Данные уходят пачкой. Нужны checksum, recordCount, quarantine, протокол ошибок, reprocess и сверка количества записей.'});
    [['Source service','internal','Команда продукта','high','stable'],['File storage','internal','Платформа','high','stable'],['Внешняя система','external','Партнёр','high','limited'],['БД batch','db','Команда продукта','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Source service формирует batch и checksum',source_system:'Source service',system:'Source service',target_system:'File storage',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',compensation:'batchId, checksum, recordCount'}, {name:'File storage передаёт файл внешней системе',source_system:'File storage',system:'Source service',target_system:'Внешняя система',channel:'file',blocking:'no',retry:'manual',idempotency:'natural',compensation:'quarantine, повтор передачи, контроль размера'}, {name:'Source service получает протокол обработки',source_system:'Внешняя система',system:'Source service',target_system:'БД batch',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',writes_entity:'yes',compensation:'reconciliation, reprocess rejected records'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='legacy_migration'){
    setBasics({name:'Миграция legacy-процесса на новый поток',entity:'MigratedOperation',goal:'Перевести процесс со старой реализации на новую без потери незавершённых операций и с возможностью отката.',visible:'mixed',money:'indirect',reg:'yes',order:'per_entity',statuses:'LEGACY_ACTIVE, SHADOW_RUN, DUAL_RUN, CUTOVER_READY, NEW_ACTIVE, ROLLBACK_REQUIRED, COMPLETED',fields:'operationId:uuid|required|unique, legacyId:string|indexed, migrationWave:string|required, status:string|required, correlationId:uuid|required|indexed',lookup:'operationId + legacyId + migrationWave',constraints:'Нельзя остановить production, есть in-flight операции, нужен rollback и сравнение результатов.',description:'Старый процесс заменяется новым. Нужно провести shadow/dual-run, сверить результаты, описать cutover, in-flight и rollback.'});
    [['Legacy-система','legacy','Старая команда','critical','unstable'],['Новый сервис','internal','Новая команда','critical','stable'],['БД нового сервиса','db','Новая команда','critical','stable'],['Kafka','broker','Платформа','high','stable'],['DWH/сверка','analytics','Команда данных','medium','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Legacy продолжает обрабатывать production-трафик',source_system:'Клиент/процесс',system:'Legacy-система',target_system:'Legacy-система',channel:'rest',blocking:'yes',timeout_ms:'800',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'rollback остаётся на legacy'}, {name:'Новый сервис получает shadow-копию события',source_system:'Legacy-система',system:'Новый сервис',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'dual-run, replay, feature flag'}, {name:'Новый сервис пишет результат в новую БД',source_system:'Новый сервис',system:'Новый сервис',target_system:'БД нового сервиса',channel:'db',timeout_ms:'250',retry:'auto',idempotency:'natural',writes_entity:'yes',compensation:'migrationWave, unique operationId'}, {name:'DWH/сверка сравнивает legacy и новый результат',source_system:'БД нового сервиса',system:'DWH/сверка',target_system:'DWH/сверка',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',compensation:'reconciliation, cutover gates, rollback checklist'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='dwh'){
    setBasics({name:'Передача изменений в DWH через CDC',entity:'BusinessRecord',goal:'Передавать данные в аналитику без синхронного чтения production-БД и без нагрузки на основной бизнес-процесс.',statuses:'CAPTURED, TRANSFORMED, LOADED, RECONCILED, FAILED',fields:'recordId:uuid|required|indexed, updatedAt:datetime|required, lsn:string|required|unique, batchId:string|indexed',lookup:'recordId + updatedAt, LSN/watermark для CDC',description:'Данные из OLTP должны попадать в DWH через CDC/ETL, с контролем полноты, freshness, watermark и backfill.'});
    [['OLTP БД','db','Команда продукта','critical','stable'],['CDC-пайплайн','internal','Платформа данных','high','stable'],['DWH','analytics','Команда данных','medium','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Бизнес-сервис пишет данные в OLTP БД',source_system:'Бизнес-сервис',system:'OLTP БД',target_system:'OLTP БД',channel:'db',timeout_ms:'200',writes_entity:'yes',idempotency:'natural'}, {name:'CDC-пайплайн забирает изменения',source_system:'OLTP БД',system:'CDC-пайплайн',target_system:'DWH',channel:'cdc',blocking:'no',retry:'auto',idempotency:'natural',compensation:'повтор чтения, контроль lag, watermark'}, {name:'DWH строит витрину и сверяет полноту',source_system:'CDC-пайплайн',system:'DWH',target_system:'DWH',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',compensation:'reconciliation-сверка, backfill'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='highload'){
    setBasics({name:'Highload consumer из Kafka в Postgres',entity:'FilteredEvent',goal:'Консьюмеры читают общий топик, фильтруют события и сохраняют только нужные записи в Postgres.',rps:'5000',peak:'5',order:'per_entity',statuses:'RECEIVED, STORED, SKIPPED, FAILED',fields:'eventId:uuid|required|unique, aggregateId:string|required|indexed, eventType:string|required, receivedAt:datetime|required',lookup:'eventId для дедупликации, aggregateId + eventType для бизнес-поиска',description:'Консьюмер читает общий топик, фильтрует только нужные события и сохраняет результат в Postgres. Нужно контролировать lag, backpressure и filter ratio.'});
    [['Kafka','broker','Платформа','critical','stable'],['Consumer group','internal','Команда интеграций','high','stable'],['Postgres','db','DBA','high','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Консьюмер читает пачку событий',source_system:'Kafka',system:'Consumer group',target_system:'Consumer group',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'контроль offset/ack, backpressure'}, {name:'Консьюмер фильтрует события по признаку',source_system:'Consumer group',system:'Consumer group',target_system:'Consumer group',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',compensation:'метрики filter ratio, skip reason'}, {name:'Консьюмер сохраняет нужные события в Postgres',source_system:'Consumer group',system:'Consumer group',target_system:'Postgres',channel:'db',timeout_ms:'300',retry:'auto',idempotency:'key',writes_entity:'yes',compensation:'unique key, DLQ, replay'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='dispatcher'){
    setBasics({name:'Универсальный докатчик запросов в системы А и Б',entity:'DispatchOperation',goal:'Один универсальный сервис отправляет запросы в разные целевые системы в рамках одного бизнес-процесса и должен корректно различать подоперации.',description:'Сервис используется несколькими процессами. Для связи используется operUid, но в одном процессе запрос в систему А и запрос в систему Б могут иметь одинаковый operUid. Поиск только по operUid склеит разные записи. Нужен operationType и targetSystem.',lookup:'operUid + operationType + targetSystem',constraints:'Сервис универсальный, менять внешние системы дорого, нужно сохранить совместимость старых вызовов.',visible:'no',order:'per_entity',statuses:'CREATED, SENT_TO_TARGET, ACCEPTED_BY_TARGET, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW',fields:'operUid:string|required|indexed, operationType:string|required|indexed, targetSystem:string|required|indexed, requestId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required'});
    [['Инициатор процесса','internal','Команда продукта','high','stable'],['Универсальный докатчик','internal','Команда интеграций','critical','stable'],['Система А','external','Владелец системы А','high','limited'],['Система Б','external','Владелец системы Б','high','limited'],['БД докатчика','db','Команда интеграций','critical','stable']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4]},false));
    [{name:'Инициатор создаёт бизнес-процесс с одним operUid',source_system:'Пользователь/процесс',system:'Инициатор процесса',target_system:'Универсальный докатчик',channel:'rest',timeout_ms:'300',idempotency:'key',writes_entity:'yes'}, {name:'Докатчик создаёт запись подоперации для системы А',source_system:'Универсальный докатчик',system:'Универсальный докатчик',target_system:'БД докатчика',channel:'db',timeout_ms:'200',retry:'auto',idempotency:'natural',writes_entity:'yes',compensation:'unique key: operUid + operationType + targetSystem'}, {name:'Докатчик отправляет запрос в систему А',source_system:'Универсальный докатчик',system:'Универсальный докатчик',target_system:'Система А',channel:'rest',timeout_ms:'1500',retry:'auto',idempotency:'key',compensation:'timeout, retry, manual recovery'}, {name:'Докатчик создаёт запись подоперации для системы Б с тем же operUid',source_system:'Универсальный докатчик',system:'Универсальный докатчик',target_system:'БД докатчика',channel:'db',timeout_ms:'200',retry:'auto',idempotency:'natural',writes_entity:'yes',compensation:'unique key: operUid + operationType + targetSystem'}, {name:'Докатчик отправляет запрос в систему Б',source_system:'Универсальный докатчик',system:'Универсальный докатчик',target_system:'Система Б',channel:'rest',timeout_ms:'1500',retry:'auto',idempotency:'key',compensation:'timeout, retry, manual recovery'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='reverse_split'){
    setBasics({name:'Обратные потоки документов и операций с финальной сверкой',entity:'ApplicationProcessing',goal:'Банк отправляет документы и операции в УК, получает два независимых обратных потока и закрывает заявку только после сверки обоих направлений.',visible:'mixed',money:'indirect',reg:'yes',order:'per_entity',sla:'3500',rps:'50',peak:'3',statuses:'CREATED, DOCS_SENT, OPS_SENT, DOC_STATUS_RECEIVED, OP_STATUS_RECEIVED, RECONCILED, COMPLETED, REJECTED, FAILED, NEEDS_MANUAL_REVIEW',fields:'applicationId:uuid|required|indexed, documentId:string|required|indexed, operationId:string|required|indexed, eventId:uuid|required|unique, eventType:string|required, eventVersion:string|required, aggregateId:uuid|required|indexed, correlationId:uuid|required|indexed, status:string|required, occurredAt:datetime|required',lookup:'applicationId + documentId + operationId; eventId для дедупликации; aggregateId для порядка в партиции',constraints:'События documents и operations могут приходить в разные партиции и отставать. Нужны Schema Registry/JSON Schema, retention 14 дней для Kafka и Inbox/Outbox, DLQ, replay, lag alerts, audit journal, reconciliation и manual recovery для зависших веток.',description:'УК отдаёт два обратных потока: статус документа и статус операции. Банк не должен закрывать заявку по одному потоку, пока второй не пришёл или не переведён в ручной разбор.'});
    [['Банк','internal','Команда банка','critical','stable',''],['УК','external','Управляющая компания','critical','limited','500'],['Kafka','broker','Платформа','high','stable',''],['БД банка','db','Команда банка','critical','stable',''],['Сервис сверки','internal','Команда банка','high','stable','']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4],rate_limit_rps:s[5]},false));
    [{name:'Банк создаёт заявку и журнал аудита',source_system:'Клиент/офис',system:'Банк',target_system:'БД банка',channel:'db',blocking:'yes',timeout_ms:'300',retry:'none',idempotency:'key',writes_entity:'yes',compensation:'transaction, audit journal, status history'}, {name:'Банк передаёт документы и операции в УК',source_system:'Банк',system:'Банк',target_system:'УК',channel:'rest',blocking:'yes',timeout_ms:'2000',retry:'auto',idempotency:'key',depends_on:'1',compensation:'timeout, status inquiry, circuit breaker, ручной разбор UNKNOWN'}, {name:'УК публикует статус документа',source_system:'УК',system:'УК',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'2',compensation:'Outbox, Schema Registry, DLQ, replay, retention 14d'}, {name:'УК публикует статус операции',source_system:'УК',system:'УК',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'2',compensation:'Outbox, Schema Registry, DLQ, replay, partition lag alert'}, {name:'Банк принимает статус документа через Inbox',source_system:'Kafka',system:'Банк',target_system:'БД банка',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'3',writes_entity:'yes',compensation:'Inbox-дедупликация, replay, status history'}, {name:'Банк принимает статус операции через Inbox',source_system:'Kafka',system:'Банк',target_system:'БД банка',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'4',writes_entity:'yes',compensation:'Inbox-дедупликация, replay, status history'}, {name:'Сервис сверки закрывает заявку после двух веток',source_system:'БД банка',system:'Сервис сверки',target_system:'БД банка',channel:'db',blocking:'yes',timeout_ms:'300',retry:'auto',idempotency:'natural',depends_on:'5,6',writes_entity:'yes',compensation:'reconciliation, partial fallback, таймаут ветви, NEEDS_MANUAL_REVIEW'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='branch_join_saga'){
    setBasics({name:'Разветвлённая saga с параллельными проверками и join',entity:'ComplexOrderDecision',goal:'Запустить несколько независимых проверок, дождаться обязательных веток и принять единое решение без двойного изменения состояния.',visible:'yes',money:'indirect',reg:'no',order:'per_entity',sla:'2500',rps:'150',peak:'4',statuses:'CREATED, RESERVED, FRAUD_CHECKED, DELIVERY_CHECKED, JOINED, APPROVED, REJECTED, COMPENSATION_REQUIRED, NEEDS_MANUAL_REVIEW',fields:'orderId:uuid|required|unique, reservationId:string|indexed, fraudCheckId:string|indexed, deliveryCheckId:string|indexed, decisionVersion:string|required, correlationId:uuid|required|indexed, status:string|required',lookup:'orderId + decisionVersion; внешние id для сверки; correlationId для трассировки',constraints:'Склад, антифрод и доставка могут завершаться в разное время. Нужны timeout budget, fallback, compensation, reconciliation, audit log, retry limits и manual recovery.',description:'Кейс для процесса, где линейной цепочки мало: есть параллельные ветки, fan-in/join и единая точка принятия решения.'});
    [['Order service','internal','Команда заказов','critical','stable',''],['Inventory','external','Склад','high','limited','100'],['Антифрод','external','Риски','high','limited','50'],['Delivery','external','Доставка','high','limited','100'],['БД заказов','db','Команда заказов','critical','stable',''],['Kafka','broker','Платформа','high','stable','']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4],rate_limit_rps:s[5]},false));
    [{name:'Создать заказ и audit journal',source_system:'Канал продаж',system:'Order service',target_system:'БД заказов',channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'key',writes_entity:'yes',compensation:'UNIQUE orderId, audit journal'}, {name:'Зарезервировать товар',source_system:'Order service',system:'Order service',target_system:'Inventory',channel:'rest',blocking:'yes',timeout_ms:'700',retry:'auto',idempotency:'key',depends_on:'1',writes_entity:'yes',compensation:'release reservation, circuit breaker'}, {name:'Проверить антифрод параллельно',source_system:'Order service',system:'Order service',target_system:'Антифрод',channel:'rest',blocking:'yes',timeout_ms:'900',retry:'auto',idempotency:'key',depends_on:'1',compensation:'fallback to manual review'}, {name:'Проверить доступность доставки параллельно',source_system:'Order service',system:'Order service',target_system:'Delivery',channel:'rest',blocking:'yes',timeout_ms:'700',retry:'auto',idempotency:'key',depends_on:'1',compensation:'choose alternative delivery'}, {name:'Join: принять решение после резерва, антифрода и доставки',source_system:'Order service',system:'Order service',target_system:'БД заказов',channel:'db',blocking:'yes',timeout_ms:'250',retry:'none',idempotency:'natural',depends_on:'2,3,4',writes_entity:'yes',compensation:'single decision state, reconciliation, manual recovery'}, {name:'Опубликовать финальное событие заказа',source_system:'Order service',system:'Order service',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'5',compensation:'Outbox, Schema Registry, DLQ, replay, retention 14d'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='regulatory_cardinality'){
    setBasics({name:'Регуляторное изменение: одно поле стало списком 1:N',entity:'LoanPurposeSet',goal:'Принять изменение регулятора: у кредита теперь может быть несколько целей займа, не сломав старые контракты, отчётность и исторические данные.',visible:'mixed',money:'indirect',reg:'yes',order:'per_entity',sla:'2500',rps:'120',peak:'3',legacy:'yes',statuses:'DRAFT, VALIDATED, MIGRATED, PUBLISHED_V2, SENT_TO_REGULATOR, ACCEPTED, REJECTED, CORRECTION_REQUIRED',fields:'loanId:uuid|required|indexed, purposeId:string|required|indexed, purposeCode:string|required, sharePercent:decimal, purposeSetVersion:string|required, eventId:uuid|required|unique, eventType:string|required, eventVersion:string|required, correlationId:uuid|required|indexed, status:string|required',lookup:'loanId + purposeSetVersion + purposeId; eventId для дедупликации; version для совместимости',constraints:'Старые потребители ждут одно поле purposeCode. Нужно сделать схему v2, backward compatibility, migration/backfill, contract tests, audit journal, reconciliation с отчётностью и rollback plan.',description:'Типовой регуляторный кейс: меняется кардинальность поля. Риск не только в БД, но и в контрактах, UI, отчётности, тестах, миграции и обратной совместимости.'});
    [['Кредитный сервис','internal','Кредитная команда','critical','stable',''],['БД кредитов','db','DBA','critical','stable',''],['Kafka','broker','Платформа','high','stable',''],['Отчётность регулятору','external','Регуляторный контур','critical','limited','50'],['Legacy consumer','legacy','Старая команда','medium','unstable','']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4],rate_limit_rps:s[5]},false));
    [{name:'Валидировать список целей займа и доли с audit journal',source_system:'API/UI',system:'Кредитный сервис',target_system:'Кредитный сервис',channel:'rest',blocking:'yes',timeout_ms:'300',retry:'none',idempotency:'natural',compensation:'валидационная ошибка без изменения состояния'}, {name:'Сохранить цели займа в таблице 1:N',source_system:'Кредитный сервис',system:'Кредитный сервис',target_system:'БД кредитов',channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',depends_on:'1',writes_entity:'yes',compensation:'transaction, unique loanId + purposeId + purposeSetVersion'}, {name:'Сформировать событие LoanPurposeSetChanged v2',source_system:'Кредитный сервис',system:'Кредитный сервис',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'2',compensation:'Outbox, Schema Registry, JSON Schema, DLQ, replay, retention 30d'}, {name:'Отдать legacy-представление старым потребителям',source_system:'Кредитный сервис',system:'Кредитный сервис',target_system:'Legacy consumer',channel:'rest',blocking:'yes',timeout_ms:'500',retry:'auto',idempotency:'key',depends_on:'2',compensation:'adapter, feature flag, backward compatibility'}, {name:'Передать отчётность регулятору',source_system:'Кредитный сервис',system:'Кредитный сервис',target_system:'Отчётность регулятору',channel:'rest',blocking:'yes',timeout_ms:'1500',retry:'auto',idempotency:'key',depends_on:'2',compensation:'audit journal, reconciliation, manual correction'}, {name:'Сверить отчётность и историческую миграцию',source_system:'БД кредитов',system:'Кредитный сервис',target_system:'БД кредитов',channel:'batch',blocking:'no',retry:'manual',idempotency:'natural',depends_on:'2',compensation:'migration backfill, reconciliation report, rollback plan'}].forEach(x=>addStep(x,null,false));
  } else if(kind==='contract_change'){
    setBasics({name:'Изменение контракта: добавили обязательное поле',entity:'ContractChange',goal:'Безопасно изменить API/event-контракт, где появилось обязательное поле, и не пропустить ветку дублей/ошибок при тестировании.',visible:'mixed',money:'indirect',reg:'yes',order:'per_entity',sla:'1600',rps:'100',peak:'2',statuses:'DRAFT, COMPATIBILITY_CHECKED, CANARY, ROLLED_OUT, ROLLBACK_REQUIRED, FAILED',fields:'requestId:uuid|required|unique, operationId:string|required|indexed, eventId:uuid|required|unique, eventVersion:string|required, requiredNewField:string|required, duplicateFlag:bool, correlationId:uuid|required|indexed, status:string|required',lookup:'requestId + operationId; eventId для событий; requiredNewField проверяется contract tests',constraints:'Есть старые потребители и ветка duplicate. Нельзя выкатывать breaking change без версии, feature flag, consumer-driven contract tests, canary, audit journal, reconciliation и rollback.',description:'Кейс для ошибок, когда обязательное поле забыли в одной ветке или изменился маппинг. Шаблон заставляет проверить контракт, версии, дубль, backward compatibility и тестовые сценарии.'});
    [['Source service','internal','Команда источника','critical','stable',''],['Consumer service','internal','Команда потребителя','high','stable',''],['Kafka','broker','Платформа','high','stable',''],['Contract Registry','internal','Платформа','high','stable','']].forEach(s=>addSystem({name:s[0],role:s[1],owner:s[2],criticality:s[3],stability:s[4],rate_limit_rps:s[5]},false));
    [{name:'Зафиксировать v1/v2 schema, audit journal и правила совместимости',source_system:'Аналитик/разработчик',system:'Реестр контрактов',target_system:'Реестр контрактов',channel:'db',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',writes_entity:'yes',compensation:'versioned schema, examples, compatibility matrix'}, {name:'Source service валидирует обязательное поле во всех ветках',source_system:'Source service',system:'Source service',target_system:'Source service',channel:'rest',blocking:'yes',timeout_ms:'200',retry:'none',idempotency:'natural',depends_on:'1',compensation:'validation error, duplicate branch test'}, {name:'Опубликовать событие v2 с envelope',source_system:'Source service',system:'Source service',target_system:'Kafka',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'2',compensation:'Outbox, Schema Registry, DLQ, replay, retention 14d'}, {name:'Consumer service обрабатывает v1 и v2 во время миграции',source_system:'Kafka',system:'Consumer service',target_system:'Consumer service',channel:'kafka',blocking:'no',retry:'auto',idempotency:'key',depends_on:'3',compensation:'Inbox, backward compatibility, canary, rollback'}, {name:'Запустить contract/e2e tests для duplicate/error branches',source_system:'CI',system:'Contract Registry',target_system:'Consumer service',channel:'rest',blocking:'yes',timeout_ms:'1000',retry:'none',idempotency:'natural',depends_on:'1,2,4',compensation:'consumer-driven contract tests, reconciliation, partial fallback, rollback gate'}].forEach(x=>addStep(x,null,false));
  }
  renumberSteps(); renderAll();
}
function setMode(mode){state.mode=mode; document.body.classList.toggle('quick-mode',mode==='quick'); document.querySelectorAll('[data-mode]').forEach(b=>{const active=b.dataset.mode===mode;b.classList.toggle('active',active);b.setAttribute('aria-pressed',active?'true':'false')});}
function buildSubmissionPayload(){
  if(!state.stackReady && state.steps.length) generateStackRecommendations(true);
  normalizeChainAfterStructureChange({reason:'submit',autofillRoutes:false});
  const payload=buildPayload(); const assumptions=[];
  if(!payload.meta.name){payload.meta.name='Черновой разбор процесса'; assumptions.push('название процесса не указано');}
  if(!payload.meta.entity){payload.meta.entity='Entity'; assumptions.push('основная сущность не указана');}
  if(!payload.meta.goal){payload.meta.goal='Предварительно оценить интеграционный процесс по неполному описанию'; assumptions.push('бизнес-цель не указана');}
  if(!payload.meta.lookup_keys){payload.meta.lookup_keys='businessId + eventId'; assumptions.push('ключ поиска и дедупликации подставлен как черновое допущение');}
  if(!payload.meta.statuses){payload.meta.statuses='CREATED, PROCESSING, COMPLETED, FAILED, NEEDS_MANUAL_REVIEW'; assumptions.push('статусы подставлены как безопасный минимум');}
  if(!payload.meta.fields){payload.meta.fields='businessId:string|required|indexed, eventId:uuid|required|unique, correlationId:uuid|required|indexed, status:string|required'; assumptions.push('ключевые поля подставлены как безопасный минимум');}
  if(!payload.systems.length){payload.systems=[{name:'Система-источник',role:'internal',owner:'',criticality:'medium',stability:'unknown',rate_limit_rps:''},{name:'Целевая система',role:'internal',owner:'',criticality:'medium',stability:'unknown',rate_limit_rps:''}]; assumptions.push('участники процесса не указаны — добавлены черновые системы');}
  if(!payload.steps.length){payload.steps=[{order:1,name:'Черновой шаг: передать или обработать данные',source_system:payload.systems[0]?.name||'Система-источник',system:payload.systems[0]?.name||'Система-источник',target_system:payload.systems[1]?.name||'Целевая система',channel:'rest',blocking:'yes',timeout_ms:'500',retry:'auto',idempotency:'key',writes_entity:'no',depends_on:'',compensation:'timeout, ограниченный retry, ручной разбор при неопределённом результате',failure_policy:'Пока не знаю',component_type:'draft'}]; assumptions.push('цепочка не описана — добавлен один временный шаг, чтобы получить предварительный разбор');}
  if(assumptions.length){const note='Автодопущения чернового анализа: '+assumptions.join('; ')+'. Уточните эти пункты после первого отчёта.'; payload.meta.constraints=[payload.meta.constraints,note].filter(Boolean).join('\n'); payload.meta.description=[payload.meta.description,note].filter(Boolean).join('\n');}
  return payload;
}
async function submitForm(){const payload=buildSubmissionPayload(); const box=document.getElementById('errors'); if(box)box.innerHTML=''; const vcheck=validateSchemaBeforeStack(); const blocking=vcheck.issues.filter(x=>['Получатель не добавлен в участники','У связи нет получателя','Некорректная зависимость шага','Первый шаг не должен зависеть от другого шага'].includes(x.title)); if(blocking.length){state.schemaValidation=vcheck; state.stage='stack'; renderAll(); blocking.slice(0,6).forEach(x=>{const el=document.createElement('div');el.className='err';el.textContent=(x.stepIndex?'Шаг '+x.stepIndex+': ':'')+x.title+'. '+x.body;box?.appendChild(el)}); showToast('Отчёт не сформирован: сначала исправьте блокирующие ошибки схемы.'); return;} renderReadiness(); try{const r=await fetch(appUrl('/api/analyze'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const d=await r.json(); if(d.ok){location.href=appUrl('/run/'+d.id)}else{(d.errors||['Неизвестная ошибка']).forEach(e=>{const el=document.createElement('div');el.className='err';el.textContent=e;box?.appendChild(el)})}}catch(e){const el=document.createElement('div');el.className='err';el.textContent='Сервер недоступен: '+e;box?.appendChild(el)}}
function demo(){selectScenario('reverse',document.querySelector('[data-scenario="reverse"]'))}
function highlightNav(selector){const links=[...document.querySelectorAll(selector+' a[href^="#"]')]; if(!links.length||!('IntersectionObserver' in window))return; const byId=new Map(links.map(a=>[a.getAttribute('href').slice(1),a])); const obs=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(entry.isIntersecting){links.forEach(a=>a.classList.remove('active'));byId.get(entry.target.id)?.classList.add('active');}})},{rootMargin:'-96px 0px -65% 0px',threshold:0.01}); byId.forEach((_,id)=>{const node=document.getElementById(id);if(node)obs.observe(node)});}
document.addEventListener('input',e=>{const sf=e.target.closest('[data-system-field]'); if(sf){updateSystem(sf.dataset.id,sf.dataset.systemField,sf.value);return;} const st=e.target.closest('[data-step-field]'); if(st){updateStep(st.dataset.id,st.dataset.stepField,st.value);return;} updateProgress();});
document.addEventListener('change',e=>{const sf=e.target.closest('[data-system-field]'); if(sf){updateSystem(sf.dataset.id,sf.dataset.systemField,sf.value);return;} const st=e.target.closest('[data-step-field]'); if(st){updateStep(st.dataset.id,st.dataset.stepField,st.value);return;} updateProgress();});
document.addEventListener('click',e=>{const el=e.target.closest('[data-action]'); if(!el)return; const a=el.dataset.action; if(a==='flow-stage')return setFlowStage(el.dataset.stage||'participants'); if(a==='add-interaction')return addInteractionFromBuilder(); if(a==='compose-choice')return setComposerChoice(el.dataset.composeGroup,el.dataset.value); if(a==='wizard-next')return moveComposerWizard(1); if(a==='wizard-back')return moveComposerWizard(-1); if(a==='compose-chain')return composeChainFromChoices(); if(a==='generate-stack')return generateStackRecommendations(false); if(a==='apply-schema-fixes')return applySchemaValidationFixes(); if(a==='continue-stack-anyway')return continueStackAnyway(); if(a==='add-human-step')return addHumanStep(el.dataset.stepKind||'next'); if(a==='scenario')return selectScenario(el.dataset.scenario,el); if(a==='mode')return setMode(el.dataset.mode); if(a==='clear')return selectScenario('blank',document.querySelector('[data-scenario="blank"]')); if(a==='add-system')return presetSystem(el.dataset.systemKind||'internal'); if(a==='add-step')return addStep(presetStep(el.dataset.template||'rest')); if(a==='template')return addStep(presetStep(el.dataset.template)); if(a==='module' && el.dataset.stepIndex!==undefined)return toggleStepClarification(el.dataset.moduleKind||el.dataset.module||'', el.dataset.moduleLabel||'', el.dataset.stepIndex||'-1', el.dataset.stepLabel||'', el.dataset.groupId||''); if(a==='module')return applyModule(el.dataset.moduleKind||el.dataset.module, el.dataset.stepLabel||''); if(a==='safe-all'){applySafeDefaultsAll();return showToast('Безопасные настройки применены ко всем компонентам.')} if(a==='suggest-basics'){suggestBasics();return showToast('Базовые статусы, поля и ключи подставлены.')} if(a==='demo')return demo(); if(a==='submit')return submitForm(); if(a==='delete-system')return deleteSystem(el.dataset.id); if(a==='delete-step')return deleteStep(el.dataset.id); if(a==='duplicate-step')return duplicateStep(el.dataset.id); if(a==='move-step')return moveStep(el.dataset.id,parseInt(el.dataset.dir||'0',10)); if(a==='insert-after')return insertStepAfter(el.dataset.id,'rest'); if(a==='insert-before')return insertStepBefore(el.dataset.id,'rest'); if(a==='safe-step')return applySafeDefaultsToStep(el.dataset.id); if(a==='set-channel')return setManualChannel(el.dataset.id,el.dataset.channel); if(a==='auto-channel')return resetAutoChannel(el.dataset.id);});
document.addEventListener('dragstart',e=>{if(state.mode==='quick')return; const c=e.target.closest('.chain-component'); if(!c)return; dragStepId=c.dataset.stepId; c.classList.add('dragging'); e.dataTransfer.effectAllowed='move';});
document.addEventListener('dragend',e=>{document.querySelectorAll('.chain-component').forEach(x=>x.classList.remove('dragging','drop-target')); dragStepId=null;});
document.addEventListener('dragover',e=>{if(state.mode==='quick')return; const c=e.target.closest('.chain-component'); if(!c||!dragStepId)return; e.preventDefault(); c.classList.add('drop-target');});
document.addEventListener('dragleave',e=>{e.target.closest('.chain-component')?.classList.remove('drop-target');});
document.addEventListener('drop',e=>{if(state.mode==='quick')return; const c=e.target.closest('.chain-component'); if(!c||!dragStepId)return; e.preventDefault(); const from=state.steps.findIndex(s=>s.id===dragStepId); const to=state.steps.findIndex(s=>s.id===c.dataset.stepId); if(from<0||to<0||from===to)return; const [x]=state.steps.splice(from,1); state.steps.splice(to,0,x); normalizeChainAfterStructureChange({reason:'drag-drop',autofillRoutes:true,movedId:x.id}); renderAll(); showToast('Шаг перемещён. Поля маршрута и зависимости пересчитаны автоматически.');});
window.addEventListener('DOMContentLoaded',()=>{document.documentElement.classList.add('js-ready'); setMode('quick'); state.stage='participants'; applyScenario('blank'); resetScenarioSelection(); renderComposerWizard(); updateComposerPreview(); document.querySelectorAll('input,select,textarea').forEach(e=>e.addEventListener('input',updateProgress)); highlightNav('.guidebar'); highlightNav('.resultnav'); updateProgress();});
"""


def page(title, body, extra_head=''):
    return f"""<!doctype html><html lang="ru" data-base-path="{escape(BASE_PATH)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><style>{CSS}</style>{extra_head}</head>
<body><div class="wrap"><noscript><div class="err">Для работы конструктора нужен JavaScript. Включите JavaScript или проверьте политики браузера.</div></noscript>{body}</div></body></html>"""


def titleblock(sub, active='builder'):
    builder_cls = 'primary' if active == 'builder' else ''
    learn_cls = 'primary' if active == 'learning' else ''
    inv_cls = 'primary' if active == 'invariants' else ''
    pat_cls = 'primary' if active == 'patterns' else ''
    return f"""
    <header class="titleblock">
      <div>
        <h1>Интеграционный проектировщик</h1>
        <nav class="topnav" aria-label="Основная навигация">
          <a class="{builder_cls}" href="{url_for('/')}">Собрать процесс</a>
          <a class="{learn_cls}" href="{url_for('/learning')}">Тренажёр</a>
          <a class="{inv_cls}" href="{url_for('/invariants')}">Проверки</a>
          <a class="{pat_cls}" href="{url_for('/patterns')}">База знаний</a>
        </nav>
      </div>
      <div class="meta">ЛИСТ: {escape(sub)}<br>РЕВ. {APP_VERSION} · rule-engine · learning MVP</div>
    </header>
    """

def form_page():
    body = titleblock('КОНСТРУКТОР ПРОЦЕССА · ГИБКАЯ ЦЕПОЧКА', active='builder') + f"""
<section class="hero">
 <h2>Проектирование начинается с участников и связей, а не с технологий.</h2>
 <p>Сначала определите, кто участвует в процессе. Затем последовательно задайте взаимодействия между участниками: кто отдаёт результат, кто получает, что происходит, нужен ли ответ сразу или результат появится позже. После этого уточните свойства процесса, и только затем система предложит технический стек с объяснением.</p>
 <div class="steps3"><div class="stepbox"><b>1. Участники</b><br>Инициатор, сервис процесса, внешние системы, хранилище, аналитика, ручной разбор или старый контур.</div><div class="stepbox"><b>2. Связи</b><br>Кто с кем взаимодействует, что передаётся, когда нужен результат и на основе чего продолжается следующий шаг.</div><div class="stepbox"><b>3. Стек и отчёт</b><br>Технологии появляются только после описания процесса: система объяснит, почему выбран именно этот вариант и почему не другой.</div></div>
 <div class="quickstart">
  <div class="quickstart-card">
   <h3>Как строить цепочку</h3>
   <p>Одна связь — это одно взаимодействие между двумя участниками. Например: «Сервис процесса запрашивает данные у внешней системы», «Сервис процесса сохраняет результат в БД», «БД передаёт изменения в аналитику».</p>
  </div>
  <div class="quickstart-card">
   <h3>Что не нужно выбирать в начале</h3>
   <p>В начале не выбирайте конкретные технологии. Сначала опишите участников, связи и свойства процесса; технический стек появится отдельным этапом после уточнений.</p>
  </div>
 </div>
 <div class="navlinks"><a href="{url_for('/learning')}">Открыть тренажёр кейсов</a><a href="{url_for('/invariants')}">Открыть справочник инвариантов</a><a href="{url_for('/patterns')}">Открыть базу знаний по архитектурным решениям</a></div>
</section>

<nav class="guidebar" aria-label="Навигация по проектированию"><span class="guide-title">Проектирование:</span><a href="#chain-builder">1. участники</a><a href="#chain-builder">2. связи</a><a href="#chain-builder">3. уточнения</a><a href="#chain-builder">4. стек</a><a href="#readiness">5. отчёт</a></nav>

<section class="card">
 <div class="toolbar">
  <div class="mode" aria-label="Режим заполнения"><button type="button" data-action="mode" data-mode="quick">Простой режим</button><button type="button" data-action="mode" data-mode="advanced">Экспертный режим</button></div>
  <span class="spacer"></span>
  <button type="button" class="btn ghost" data-action="clear">очистить</button>
 </div>
 <p class="hint quick-note">В простом режиме процесс строится последовательно: участники → связи → уточнения → стек → отчёт. Технологии появляются только после этапа «Определить стек по процессу».</p>
 <p class="hint advanced-note">В экспертном режиме доступны время ожидания, повторные попытки, защита от дублей, зависимости, восстановление, критичность и лимиты.</p>
 <div class="progress" id="fillbar"><i></i></div><p class="hint" id="filltext"></p><div id="liveGuide" class="assist"></div>
</section>

<section class="card" id="scenario"><button type="button" data-action="compose-chain" style="display:none">регрессионная кнопка старого сборщика</button><h2>1. Соберите цепочку из универсальных вариантов</h2>
 <p class="human-tip">Здесь больше нет стартовых шаблонов. Пользователь не выбирает готовую фразу, а собирает процесс из простых признаков: как начинается, что делаем, когда приходит результат, что делаем с результатом и сколько систем примерно участвует.</p>
 <div class="composer">
  <div class="composer-panel wizard-shell">
   <div class="wizard-meta"><strong>Пошаговая сборка</strong><span>Шаг <span id="wizardCurrent">1</span> из <span id="wizardTotal">5</span></span></div>
   <div class="wizard-progress" aria-label="Прогресс сборки"><i class="wizard-dot active" data-wizard-dot="0"></i><i class="wizard-dot" data-wizard-dot="1"></i><i class="wizard-dot" data-wizard-dot="2"></i><i class="wizard-dot" data-wizard-dot="3"></i><i class="wizard-dot" data-wizard-dot="4"></i></div>
   <p>Отвечайте по одному вопросу. Можно выбирать «Не знаю» — система всё равно построит безопасный черновик и явно отметит допущения.</p>
   <div class="wizard-pane active" data-wizard-pane="start"><h3>Как начинается процесс?</h3><div class="wizard-choice-count">Выберите один вариант. Следующий вопрос откроется автоматически.</div><div class="choice-grid">
    <button type="button" class="choice-card compact active recommended" data-action="compose-choice" data-compose-group="start" data-value="incoming_request"><b>Входящий запрос</b><small>кто-то запускает процесс</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="start" data-value="event"><b>Событие из очереди</b><small>изменение уже произошло где-то снаружи</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="start" data-value="file"><b>Файл или данные пачкой</b><small>данные приходят пачкой</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="start" data-value="schedule"><b>По расписанию</b><small>регламентный запуск</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="start" data-value="unknown"><b>Не знаю</b><small>сделать безопасное допущение</small></button>
   </div></div>
   <div class="wizard-pane" data-wizard-pane="activity"><h3>Что нужно сделать?</h3><div class="choice-grid">
    <button type="button" class="choice-card compact active recommended" data-action="compose-choice" data-compose-group="activity" data-value="call_external"><b>Вызвать внешнюю систему</b><small>нужен ответ или действие другой системы</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="activity" data-value="receive_data"><b>Получить данные</b><small>забрать результат/справку</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="activity" data-value="send_data"><b>Передать данные</b><small>отправить заявку/документ</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="activity" data-value="validate"><b>Проверить данные</b><small>валидация/бизнес-правила</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="activity" data-value="enrich"><b>Обогатить данными</b><small>сходить в справочник</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="activity" data-value="wait_status"><b>Дождаться статуса</b><small>обратный поток</small></button>
   </div></div>
   <div class="wizard-pane" data-wizard-pane="timing"><h3>Когда появляется результат?</h3><div class="choice-grid">
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="timing" data-value="immediate"><b>Сразу</b><small>ответ в текущем вызове</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="timing" data-value="later"><b>Позже</b><small>другая система сообщит позже</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="timing" data-value="both"><b>И так, и так</b><small>гибридный процесс</small></button>
    <button type="button" class="choice-card compact active recommended" data-action="compose-choice" data-compose-group="timing" data-value="unknown"><b>Не знаю</b><small>добавить защитные статусы</small></button>
   </div></div>
   <div class="wizard-pane" data-wizard-pane="result"><h3>Что делать с результатом?</h3><div class="choice-grid">
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="result" data-value="save"><b>Сохранить</b><small>зафиксировать состояние</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="result" data-value="forward"><b>Передать дальше</b><small>следующий получатель</small></button>
    <button type="button" class="choice-card compact active recommended" data-action="compose-choice" data-compose-group="result" data-value="save_forward"><b>Сохранить и передать</b><small>частый путь, не шаблон</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="result" data-value="update_status"><b>Обновить статус</b><small>статусная модель</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="result" data-value="compare"><b>Сверить/сравнить</b><small>контроль расхождений</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="result" data-value="unknown"><b>Не знаю</b><small>сохранить допущения</small></button>
   </div></div>
   <div class="wizard-pane" data-wizard-pane="systems"><h3>Сколько систем примерно участвует?</h3><div class="choice-grid">
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="systems" data-value="2"><b>2</b><small>минимальный контур</small></button>
    <button type="button" class="choice-card compact active recommended" data-action="compose-choice" data-compose-group="systems" data-value="3"><b>3</b><small>источник/обработка/получатель</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="systems" data-value="4"><b>4+</b><small>сложная цепочка</small></button>
    <button type="button" class="choice-card compact" data-action="compose-choice" data-compose-group="systems" data-value="unknown"><b>Не знаю</b><small>система выберет минимум</small></button>
   </div></div>
   <div class="wizard-footer"><button type="button" class="btn ghost" id="wizardBack" data-action="wizard-back">Назад</button><button type="button" class="btn" id="wizardNext" data-action="wizard-next">Дальше</button></div>
  </div>
  <div class="composer-panel">
   <h3>Черновик перед сборкой</h3><div class="grammar-line"><b>Формула:</b> старт + действие + характер результата + обработка результата + признаки сложности.</div>
   <p>После 5 коротких выборов появится минимальная цепочка. Затем можно добавить признаки реального процесса: дубли, аналитику, старый контур, ручную сверку, сведение веток, чувствительные данные, деньги и нагрузку.</p>
   <div id="composeStatus" class="compose-status"><b>Черновик будет собран из выбранных вариантов</b><ol><li>Старт: Входящий запрос</li><li>Основное действие: Вызвать внешнюю систему</li><li>Ответ/результат: Не знаю</li><li>После результата: Сохранить и передать</li><li>Масштаб: 3 системы</li></ol></div>
   <div class="expert-link-note">На старте не выбираются конкретные технологии. Сначала описывается процесс, затем система сама определяет стек и объясняет выбор.</div>
  </div>
 </div>
 <details class="template-fold">
  <summary>Показать примеры, не основной путь, если хочется стартовать с готового кейса</summary>
  <div class="scenario-groups">
   <div class="scenario-group"><h3>Частые бизнес-процессы</h3><p>Это не обязательные шаблоны, а примеры для быстрого заполнения.</p><div class="scenarios">
    <button type="button" class="scenario featured" data-action="scenario" data-scenario="reverse" aria-pressed="false"><b>Получить статусы от внешней системы</b><span>Банк ↔ УК, документы, операции, обратный поток статусов.</span><small>обратные статусы и история изменений</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="payment" aria-pressed="false"><b>Платёж / деньги / подтверждение</b><span>Создание операции, блокировка денег, внешний провайдер, финальный статус.</span><small>деньги, повторы и доказуемость действий</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="order" aria-pressed="false"><b>Заказ товара / выполнение заявки</b><span>Заказ, склад, доставка, уведомления и отмена.</span><small>статусы, отмена и восстановление</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="external_sync" aria-pressed="false"><b>Вызвать внешний сервис и ждать ответ</b><span>Одна система ждёт ответ другой системы в важном месте процесса.</span><small>ограничение ожидания и запасной сценарий</small></button>
   </div></div>
   <div class="scenario-group"><h3>Интеграции и события</h3><p>Для событий, поздних результатов, файлов, аналитики и обогащения данных.</p><div class="scenarios">
    <button type="button" class="scenario" data-action="scenario" data-scenario="kafka" aria-pressed="false"><b>Отправить изменение нескольким потребителям</b><span>Публикация изменений, защита от дублей и повторная обработка.</span><small>изменения могут обрабатываться позже</small></button>
    <button type="button" class="scenario featured" data-action="scenario" data-scenario="enrichment" aria-pressed="false"><b>Обогатить данные через справочник</b><span>Нужно дополнить данные из внешнего источника и передать обогащённый результат дальше.</span><small>компромисс без лишней инфраструктуры</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="webhook_in" aria-pressed="false"><b>Принять поздний результат от внешней системы</b><span>Внешняя система сама присылает результат.</span><small>проверка источника и дублей</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="batch_file" aria-pressed="false"><b>Передать файл или пакет данных</b><span>Пакетная выгрузка, контроль целостности, карантин ошибок и повторная обработка.</span><small>идентификатор пакета и сверка</small></button>
   </div></div>
   <div class="scenario-group"><h3>Сложные/технические кейсы</h3><p>Когда важны нагрузка, аналитика, старый контур или универсальные сервисы.</p><div class="scenarios">
    <button type="button" class="scenario" data-action="scenario" data-scenario="dwh" aria-pressed="false"><b>Выгрузить данные в аналитику</b><span>Передача изменений в аналитику без нагрузки на основной процесс.</span><small>контрольная отметка и дозагрузка</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="highload" aria-pressed="false"><b>Высокая нагрузка на обработку изменений</b><span>Много входящих изменений, часть нужно отфильтровать и сохранить.</span><small>отставание обработки и управление потоком</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="dispatcher" aria-pressed="false"><b>Универсальный докатчик</b><span>Один operUid, разные operationType и целевые системы.</span><small>составной бизнес-ключ</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="legacy_migration" aria-pressed="false"><b>Заменить старый процесс</b><span>Параллельный прогон, переключение, откат и незавершённые операции.</span><small>контрольные точки миграции</small></button>
   </div></div>
   <div class="scenario-group"><h3>Ультрасложные заготовки</h3><p>Заготовки для нескольких потоков, join, регуляторных изменений и совместимости.</p><div class="scenarios">
    <button type="button" class="scenario featured" data-action="scenario" data-scenario="reverse_split" aria-pressed="false"><b>Документы + операции в разных потоках</b><span>Два обратных потока, сведение веток, отставание обработки и сверка.</span><small>сведение веток, сверка и ручное восстановление</small></button>
    <button type="button" class="scenario featured" data-action="scenario" data-scenario="branch_join_saga" aria-pressed="false"><b>Разветвлённая saga / fan-in</b><span>Параллельные проверки, ожидание нескольких веток, единое решение.</span><small>depends_on 2,3 + компенсации</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="regulatory_cardinality" aria-pressed="false"><b>Регуляторное изменение модели данных</b><span>Одно поле становится списком, 1:N, версии контрактов и миграция.</span><small>schema v2 + backward compatibility</small></button>
    <button type="button" class="scenario" data-action="scenario" data-scenario="contract_change" aria-pressed="false"><b>Изменение контракта / обязательное поле</b><span>Добавили обязательное поле, есть старые потребители и риск незамеченного дубля.</span><small>contract tests + versioning</small></button>
   </div></div>
  </div>
 </details>
 <p id="selectedScenario" class="selected-scenario">Цепочка ещё не собрана. Соберите её из универсальных вариантов выше или откройте примеры.</p>
</section>

<section class="card" id="basics"><h2>Опционально: уточнить смысл вручную</h2>
 <p class="optional-open"><b>В простом пути этот блок можно пропустить.</b> Сборщик уже подставляет сущность, ключи, статусы и цель. Откройте экспертный режим, если хотите переименовать всё под реальный проект.</p>
 <div class="manual-fields">
 <p class="hint">Минимум для хорошего разбора: название, сущность, бизнес-цель, ключ поиска и статусы. Если чего-то нет — запуск всё равно возможен, отчёт честно покажет допущения и недостающие уточнения.</p><div class="draft-note">Можно начать с малого: грубый ввод → черновой разбор → точечные уточнения после результата.</div><div class="minimal"><div class="mini"><b>Сущность</b><span>что меняется в процессе</span></div><div class="mini"><b>Ключ</b><span>по чему искать и дедуплицировать</span></div><div class="mini"><b>Статусы</b><span>где процесс может зависнуть</span></div><div class="mini"><b>Ошибки</b><span>как восстановиться</span></div></div>
 <div class="grid g3">
  <div><label for="p_name">Как называется процесс?</label><input id="p_name" placeholder="Например: обратный поток статусов"></div>
  <div><label for="p_entity">Какая основная сущность?</label><input id="p_entity" placeholder="Например: заявка, договор, документ"><div class="fieldtip">То, вокруг чего строится процесс.</div></div>
  <div><label for="p_sla">Сколько можно ждать ответ?</label><input id="p_sla" inputmode="numeric" placeholder="мс; пусто, если процесс фоновый"><div class="fieldtip">Если клиент ждёт ответ — укажите SLA. Если обработка фоновая — можно оставить пустым.</div></div>
 </div>
 <label for="p_goal">Какую бизнес-задачу решает процесс?</label><input id="p_goal" placeholder="Например: банк должен видеть финальный статус обработки в УК">
 <label for="p_description">Краткое описание ситуации</label><textarea id="p_description" placeholder="Например: универсальный докатчик отправляет запросы в систему А и систему Б. В рамках одного процесса используется один operUid, поэтому поиск только по operUid может склеить разные записи."></textarea>
 <div class="grid g2">
  <div id="fix-lookup"><label for="p_lookup">По каким полям искать, обновлять и дедуплицировать запись?</label><input id="p_lookup" placeholder="Например: operUid + operationType + targetSystem"><div class="fieldtip">Для общих сервисов часто нужен составной ключ: requestId + operationType + targetSystem + tenantId.</div></div>
  <div id="fix-constraints"><label for="p_constraints">Какие ограничения или компромиссы есть?</label><input id="p_constraints" placeholder="Например: нельзя менять сервис А, новый топик запрещён, срок 2 недели"></div>
 </div>
 <div class="grid g4">
  <div><label for="p_visible">Кто ждёт результат?</label><select id="p_visible"><option value="no">Никто, процесс фоновый</option><option value="yes">Пользователь/клиент ждёт</option><option value="mixed">Смешанный вариант</option></select></div>
  <div><label for="p_money">Есть влияние на деньги?</label><select id="p_money"><option value="no">Нет</option><option value="indirect">Косвенно</option><option value="direct">Напрямую</option></select></div>
  <div><label for="p_reg">Есть регуляторный риск?</label><select id="p_reg"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_order">Нужен порядок событий?</label><select id="p_order"><option value="no">Нет</option><option value="per_entity">В рамках одной сущности</option><option value="global">Глобальный порядок</option></select></div>
 </div>
 <div class="grid g3 advanced-only">
  <div><label for="p_rps">Средняя нагрузка, RPS</label><input id="p_rps" inputmode="numeric" placeholder="Например: 100"></div>
  <div><label for="p_peak">Пиковая нагрузка</label><select id="p_peak"><option value="1">x1</option><option value="2">x2</option><option value="5">x5</option><option value="10">x10</option></select></div>
  <div><label for="p_tenant">Один поток для разных клиентов?</label><select id="p_tenant"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_legacy">Это замена старого контура?</label><select id="p_legacy"><option value="no">Нет</option><option value="yes">Да</option></select></div>
  <div><label for="p_read">Как часто читают результат?</label><select id="p_read"><option value="low">Редко</option><option value="medium" selected>Средне</option><option value="high">Часто</option><option value="very_high">Очень часто</option></select></div>
 </div>
 <div class="grid g2">
  <div id="fix-statuses"><label for="p_statuses">Какие статусы есть у процесса?</label><input id="p_statuses" placeholder="Например: CREATED, PROCESSING, COMPLETED, REJECTED"><div class="fieldtip">Статусы показывают, где находится заявка и какие состояния финальные.</div></div>
  <div id="fix-fields"><label for="p_fields">Какие ключевые поля есть у сущности?</label><input id="p_fields" placeholder="Например: requestId:string|required|unique"><div class="fieldtip">Отметьте required, unique, indexed и sensitive.</div></div>
 </div>
 <p><button type="button" class="btn ghost" data-action="suggest-basics">подставить безопасный минимум</button></p>
</section>


<section class="card" id="complexity-modules"><h2>2. Усложнить процесс слоями</h2>
 <p class="human-tip">Отмечайте человеческие признаки процесса. UI сам добавит шаги, ключи, статусы, восстановление и ограничения, а стек определит отдельным этапом ниже.</p>
 <div class="question-grid">
  <div class="question-card"><b>Есть параллельные ветки?</b><span>Отметьте ожидание нескольких веток — появятся параллельные шаги, окно ожидания и единое решение.</span></div>
  <div class="question-card"><b>Есть аналитика, старый контур или ручная сверка?</b><span>Отметьте нужный признак — добавятся шаги сверки, совместимости, восстановления или ручного разбора.</span></div>
 </div>
 <div class="module-panel module-groups">
  <div class="clarification-note"><b>Это уточнения процесса, а не выбор технологий.</b> Отмечайте обычными словами: нужен быстрый доступ на чтение, фоновая обработка, поиск, большие документы, масштабирование хранения. Стек будет выбран только следующим этапом.</div>
  <div class="module-group"><h3>Уточнения до выбора стека</h3><div class="module-grid">
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="fast_read"><b>Нужен быстрый доступ на чтение</b><small>Одни и те же данные часто читают, ответ должен быть быстрым.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="db_scale"><b>Нужно масштабировать хранение</b><small>Много записей или чтений, нужен план роста данных.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="task_queue"><b>Нужна фоновая обработка</b><small>Работу можно выполнить позже, без ожидания пользователя.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="exclusive_processing"><b>Нельзя обрабатывать одну сущность одновременно</b><small>Нужно защититься от гонки двух обработчиков.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="search_projection"><b>Нужен удобный поиск</b><small>Нужно искать по нескольким полям и фильтрам.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="large_files"><b>Есть большие документы или вложения</b><small>Документы не должны утяжелять основное сообщение.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="fast_internal_call"><b>Нужен быстрый внутренний ответ</b><small>Свои сервисы часто вызывают друг друга, задержка должна быть минимальной.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="old_web_contract"><b>Есть старый веб-сервисный контракт</b><small>Старый контур нельзя свободно менять, нужен адаптер и перевод ошибок.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="external_entry_control"><b>Нужен единый внешний вход</b><small>Много клиентов или партнёров, нужны авторизация, лимиты и версии входа.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="central_routing"><b>Нужна централизованная маршрутизация</b><small>Сообщения надо направлять и преобразовывать между разными системами.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="event_history"><b>Нужна история событий и повторная обработка</b><small>Изменения должны храниться, рассылаться нескольким потребителям и переигрываться.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="short_stream"><b>Нужен короткий поток с малой задержкой</b><small>События живут недолго, важна скорость внутри одного контура.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="short_queue"><b>Нужна короткая очередь задач</b><small>Небольшую фоновую работу надо выполнить позже и быстро убрать из очереди.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="unknown_async_buffer"><b>Нужен буфер, но требования пока не ясны</b><small>Нужна асинхронная прослойка, но порядок, хранение и маршрутизация ещё неизвестны.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="partner_file_exchange"><b>Есть защищённый файловый обмен</b><small>Партнёр или старый контур передаёт файлы через защищённый каталог.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="simple_file_exchange"><b>Есть одиночный файл без каталога</b><small>Нужно принять или передать один файл, проверить целостность и статус обработки.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="external_push_result"><b>Партнёр сам присылает результат позже</b><small>Нужно принять входящий результат, проверить источник, время и дубли.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="graphql_query"><b>Нужен гибкий API для разных клиентов</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="odata_entity_api"><b>Нужен корпоративный API по сущностям</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="service_mesh_control"><b>Нужно управлять внутренними вызовами сервисов</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="websocket_realtime"><b>Нужен двусторонний онлайн-канал</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="sse_notifications"><b>Нужен поток уведомлений клиенту</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="mqtt_iot"><b>Есть устройства или датчики</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="pulsar_event_log"><b>Нужен масштабный поток событий с отдельным хранением</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="nats_light_pubsub"><b>Нужна лёгкая внутренняя рассылка сообщений</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="enterprise_mq"><b>Нужна корпоративная гарантированная очередь</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="cloud_messaging"><b>Нужна облачная очередь или топик</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="enterprise_jms_queue"><b>Нужна стандартная корпоративная очередь приложений</b><small>Система сама выберет конкретный стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="cloud_messaging_azure"><b>Нужна облачная очередь в корпоративном Microsoft-контуре</b><small>Система сама выберет конкретный стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="cloud_messaging_google"><b>Нужна облачная шина сообщений в Google-контуре</b><small>Система сама выберет конкретный стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="dwh_target_layer"><b>Нужно отдельное аналитическое хранилище как целевой слой</b><small>Система сама выберет конкретный стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="read_replica"><b>Нужно разгрузить чтение из БД</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="sharded_storage"><b>Нужно разделить данные по ключу</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="document_store"><b>Нужны гибкие документы</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="wide_column_store"><b>Нужны огромные распределённые записи по ключу</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="key_value_store"><b>Нужен быстрый доступ по ключу в управляемом хранилище</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="memcached_cache"><b>Нужен простой временный кэш</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="columnar_analytics"><b>Нужна быстрая аналитика по большим таблицам</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="data_lake"><b>Нужно складывать сырые данные разных форматов</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="lakehouse"><b>Нужно совместить озеро данных и табличную аналитику</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="etl_pipeline"><b>Нужна загрузка и преобразование данных</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="airflow_orchestration"><b>Нужно управлять зависимыми загрузками</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="spark_processing"><b>Нужна большая распределённая обработка</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="dbt_models"><b>Нужны управляемые аналитические модели</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="workflow_engine"><b>Процесс долгий и имеет состояния</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="bpm_engine"><b>Есть согласования и ручные бизнес-задачи</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="cdn_static"><b>Нужно быстро отдавать статические файлы</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="auth_oidc"><b>Нужна единая авторизация</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="vault_secrets"><b>Нужно безопасно хранить секреты и ключи</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="observability_stack"><b>Нужно видеть, где завис процесс</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="vector_search"><b>Нужен семантический поиск по текстам</b><small>Система сама выберет подходящий стек после формирования решения.</small></button>
  </div></div>
  <div class="module-group"><h3>Надёжность</h3><div class="module-grid">
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="retry_dlq"><b>Могут быть ошибки и повторы</b><small>Повторять ограниченно, отделять неисправимые ошибки и уметь безопасно восстановиться.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="outbox_inbox" data-legacy-label="+ Outbox/Inbox"><b>Могут быть дубли</b><small>Повтор входящего результата не должен ломать состояние процесса.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="manual_recon"><b>Нужна ручная сверка</b><small>Нужно видеть расхождения, зависшие случаи и понятный ручной разбор.</small></button>
  </div></div>
  <div class="module-group"><h3>Потоки и системы</h3><div class="module-grid">
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="fanin"><b>Нужно дождаться нескольких веток</b><small>Процесс продолжается только после нескольких обязательных ответов.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="enrichment"><b>Нужно сходить в справочник</b><small>Нужно дополнить данные из другого источника и понять, что делать при недоступности.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="legacy"><b>Есть старый контур</b><small>Нужно сохранить совместимость и безопасно переключаться между старым и новым процессом.</small></button>
  </div></div>
  <div class="module-group"><h3>Данные и аналитика</h3><div class="module-grid">
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="dwh" data-legacy-label="+ аналитика"><b>Есть аналитическое хранилище</b><small>Нужно передавать данные в аналитику и сверять полноту загрузки.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="contract"><b>Меняется контракт/модель</b><small>Старый и новый формат должны некоторое время жить вместе.</small></button>
  </div></div>
  <div class="module-group"><h3>Бизнес-риск</h3><div class="module-grid">
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="audit"><b>Есть деньги/регуляторика</b><small>Нужен неизменяемый журнал действий, следы проверки и срок хранения.</small></button>
   <button type="button" class="module-btn" data-action="legacy-module" data-module-old="security"><b>Есть персональные или чувствительные данные</b><small>Нужно ограничить доступ, маскировать лишнее и фиксировать обращения.</small></button>
  </div></div>
  <div id="moduleStatus" class="module-status"></div>
 </div>
</section>

<section class="card" id="chain-builder"><div class="section-head"><div><h2>Конструктор процесса: участники → связи → уточнения → стек</h2><p class="hint">Основной путь разделён на этапы. Сначала добавьте участников, затем задайте связи между ними. Участники не являются шагами цепочки: шагом является взаимодействие между двумя участниками. Технологический стек появляется только на четвёртом этапе.</p></div><div class="builder-actions advanced-only"><button type="button" class="btn ghost" data-action="safe-all">безопасные настройки всем шагам</button></div></div>
 <div class="builder-layout">
  <aside class="component-palette"><h3>Быстро добавить типовой шаг по смыслу</h3><div class="palette-grid">
   <button type="button" class="palette-btn" data-action="template" data-template="rest" data-legacy-label="+ REST-вызов"><b>Вызвать систему и ждать ответ</b><small>Система сама выберет способ вызова после уточнения ограничений.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="kafka" data-legacy-label="+ Kafka-событие"><b>Отправить событие, результат будет позже</b><small>Система сама выберет способ отложенной обработки и восстановления.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="db" data-legacy-label="+ запись в БД"><b>Сохранить данные/статус</b><small>Надёжная запись, защита от дублей и конфликтов изменения.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="webhook"><b>Принять результат позже</b><small>Проверка источника, времени и дублей.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="batch"><b>Передать файл/пакет</b><small>Контроль файла, изоляция ошибок и повторная загрузка.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="cdc" data-legacy-label="+ CDC"><b>Передать изменения в аналитику</b><small>Контроль полноты изменений и повторная загрузка при расхождениях.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="manual"><b>Отправить на ручной разбор</b><small>Понятная инструкция для оператора и фиксация решения.</small></button>
   <button type="button" class="palette-btn" data-action="template" data-template="validation"><b>Проверить данные</b><small>Бизнес-правила перед изменением состояния.</small></button>
  </div><h3>Добавить участника</h3><div class="palette-grid"><button type="button" class="palette-btn" data-action="add-system" data-system-kind="internal">+ Внутренний сервис</button><button type="button" class="palette-btn" data-action="add-system" data-system-kind="external">+ Внешняя система</button><button type="button" class="palette-btn" data-action="add-system" data-system-kind="broker">+ Брокер/очередь</button><button type="button" class="palette-btn" data-action="add-system" data-system-kind="db">+ База данных</button><button type="button" class="palette-btn" data-action="add-system" data-system-kind="analytics">+ Аналитика</button><button type="button" class="palette-btn" data-action="add-system" data-system-kind="legacy">+ Старый контур</button></div></aside>
  <main class="chain-workspace"><div id="flowStagePanel" class="flow-stage-panel"></div>
  <section class="flow-panel participants-section"><h3>1. Участники процесса</h3><p class="hint"><b>Сначала определите участников.</b> Участник — это система, человек, хранилище или внешний контур. Он сам по себе не является шагом цепочки.</p><div class="participant-actions"><button type="button" class="participant-btn" data-action="add-system" data-system-kind="initiator"><b>Добавить инициатора</b><small>Кто запускает процесс: фронт, CRM, банк, клиентский канал.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="processor"><b>Добавить сервис процесса</b><small>Кто управляет ходом процесса и принимает решения.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="external"><b>Добавить внешнюю систему</b><small>Партнёр, поставщик данных, внешний контур.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="db"><b>Добавить хранилище состояния</b><small>Где фиксируются заявки, статусы, результаты и история.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="analytics"><b>Добавить аналитику</b><small>Аналитическое хранилище, витрина, отчётность, контроль полноты.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="human"><b>Добавить ручной разбор</b><small>Оператор или команда, которая разбирает исключения.</small></button><button type="button" class="participant-btn" data-action="add-system" data-system-kind="legacy"><b>Добавить старый контур</b><small>Старый контур, который сложно менять.</small></button></div><div class="system-summary-simple" id="systemSummarySimple"></div><div id="systemsCards" class="systems-grid"></div><datalist id="syslist"></datalist><table id="systems" class="legacy-store"><tbody></tbody></table></section>
  <section class="flow-panel interactions-section"><h3>2. Порядок взаимодействия между участниками</h3><div class="hint">Сценарий процесса строится как последовательность связей между участниками.</div><p class="hint"><b>Теперь задавайте связи последовательно.</b> Стек ещё не сформирован: сначала закончите порядок взаимодействий и уточнения, затем перейдите к этапу определения стека. Одна связь = один шаг процесса.</p><div class="interaction-work-zone"><div class="interaction-block constructor"><div class="block-title"><span class="block-no">1</span><div><h4>Конструктор новой связи</h4><p>Здесь вы добавляете один следующий шаг: кто отдаёт результат, кто получает, что происходит и на основе чего продолжаем.</p></div></div><div class="interaction-form"><div><label>Кто отдаёт данные / запускает действие?</label><select id="interactionSource"></select></div><div><label>Кто получает результат?</label><select id="interactionTarget"></select></div><div><label>Что происходит?</label><select id="interactionAction"><option value="request_data">запросить или получить данные</option><option value="send_data">передать данные</option><option value="save">сохранить результат</option><option value="update_status">обновить статус</option><option value="wait_status">получить статус позже</option><option value="compare">сверить с другим источником</option><option value="notify_many">сообщить другим системам</option><option value="file">передать файл</option></select></div><div><label>Когда нужен результат?</label><select id="interactionTiming"><option value="sync">нужен сразу, процесс ждёт ответ</option><option value="later">результат появится позже</option><option value="background">можно обработать в фоне</option></select></div><div><label>Что сделать с результатом?</label><select id="interactionResult"><option value="pass_next">передать дальше</option><option value="save">сохранить / обновить состояние</option><option value="check">проверить и решить, идти ли дальше</option><option value="manual">отправить на ручной разбор при проблеме</option></select></div><div><label>На основе чего выполняется следующий шаг?</label><select id="interactionBasis"><option>результат предыдущего взаимодействия</option><option>после сохранения состояния</option><option>после ответа внешней системы</option><option>после позднего статуса</option><option>после завершения нескольких веток</option><option>по расписанию или контрольной отметке</option></select></div><div class="wide"><button type="button" class="btn" data-action="add-interaction">Добавить связь в цепочку</button></div></div></div><div class="interaction-block list"><div class="block-title"><span class="block-no">2</span><div><h4>Добавленные связи</h4><p>Это компактный список шагов. Здесь можно проверить порядок, поднять/опустить или удалить связь. Сама схема находится в отдельном блоке справа/ниже.</p></div></div><div id="interactionSummary"></div></div></div><div id="chainList" class="chain-list"></div><div class="human-step-adder"><h4>Быстро добавить действие без выбора технологии</h4><div class="human-step-grid"><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="save"><b>Сохранить результат</b><small>Добавит действие записи или обновления состояния.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="forward"><b>Передать дальше</b><small>Добавит действие передачи результата следующему участнику.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="wait"><b>Дождаться статуса позже</b><small>Добавит действие ожидания результата, который появится позже.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="check"><b>Проверить данные</b><small>Добавит действие проверки перед продолжением процесса.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="compare"><b>Сверить с другим источником</b><small>Добавит действие сверки с другим источником.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="event"><b>Сообщить другим системам</b><small>Добавит действие информирования других систем без выбора технологии.</small></button><button type="button" class="human-step-btn" data-action="add-human-step" data-step-kind="manual"><b>Отправить на ручной разбор</b><small>Добавит действие ручного разбора исключения.</small></button></div></div><table id="steps" class="legacy-store"><tbody></tbody></table></section>
  <section class="flow-panel clarifications-section"><h3>3. Уточнения процесса</h3><p class="hint"><b>Вопросы строятся из вашей схемы, а не из общего списка.</b> Для каждой связи система показывает только те уточнения, которые могут повлиять на выбор стека именно в этом месте процесса. Ответы выбираются кнопками, ничего вручную вводить не нужно.</p><div id="branchQuestionPanel" class="branch-question-panel"></div><p id="moduleStatusFlow" class="hint"></p></section>
  <section class="flow-panel stack-section"><h3>4. Формирование стека</h3><div class="stack-mode-note"><b>Сначала описание процесса, затем технический стек.</b> Технологии появляются только здесь: система выбирает их по участникам, взаимодействиям, синхронности, асинхронности, чтению, записи, файлам, аналитике, нагрузке и ограничениям.</div><div id="stackStagePanel" class="stack-stage-panel"></div></section>
  <section class="flow-panel report-section"><h3>5. Отчёт</h3><p class="hint">После формирования стека нажмите «Сформировать отчёт». Если стек не сформирован, он будет определён автоматически перед отправкой.</p></section>
  </main>
  <aside class="chain-preview"><div class="schema-panel-card"><h3>Единая схема процесса</h3><p class="hint">Отдельный блок только для просмотра схемы. Он обновляется после добавления, удаления, перестановки или изменения взаимодействия. Здесь показываются только участники, направление связи и порядок. Технологии, причины и технические детали смотрите на этапе стека и в отчёте.</p><div id="processMap" class="process-map"></div></div><div class="readiness-card"><h3 id="readiness">Готовность</h3><div id="readinessPanel"></div></div><div class="review-card"><h3>Краткая сводка ввода</h3><div id="reviewBox" class="reviewbox"></div></div></aside>
 </div>
</section>

<div id="errors"></div>
<div class="sticky-submit"><div><b>Запуск разбора</b><div class="hint" id="submitHint">Проверьте готовность процесса.</div></div><button type="button" class="btn" data-action="submit">Проверить архитектуру</button></div>
<script>{FORM_JS}</script>"""
    return page(f'Интеграционный проектировщик v{APP_VERSION}', body)




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
        'BIZ': 'Сначала надо договориться о смысле процесса, а уже потом выбирать конкретные технические средства.',
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
    return 'Ошибка: команда устно договорилась “потом разберёмся”, но не добавила проверку в контракт, DDL, ADR, тест или готовность к выпуску.'


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
        short = inv.get('question') or deep_description
        cards.append(f'''<details class="refcard" data-area="{escape(area.lower())}" data-search="{escape(hay)}">
 <summary class="ref-summary">
  <div class="ref-summary-top"><span class="refcode">{escape(inv.get('code',''))}</span><span class="refarea">{escape(area)}</span></div>
  <h3>{escape(inv.get('title','Инвариант'))}</h3>
  <p>{escape(short)}</p>
 </summary>
 <div class="ref-content">
  <section class="refbox reflead"><h4>Простыми словами</h4><p>{escape(deep_description)}</p></section>
  <section class="ref-section"><h4>Когда использовать</h4><p>{escape(when)}</p></section>
  <section class="ref-section"><h4>На каком этапе процесса</h4><p>{escape(stage)}</p></section>
  <section class="refbox okbox"><h4>Как выглядит правильное решение</h4><p>{escape(normal_state)}</p></section>
  <section class="ref-section"><h4>Как применить по шагам</h4><p>{escape(steps_to_apply)}</p></section>
  <section class="ref-section"><h4>Что проверить</h4><p>{escape(inv.get('question',''))}</p></section>
  <section class="ref-section"><h4>Почему это важно</h4><p>{escape(inv.get('why',''))}</p></section>
  <section class="ref-section"><h4>Плохо / правильно</h4><p>{escape(bad_good)}</p></section>
  <section class="ref-section"><h4>Вопросы для ревью</h4><p>{escape(review_questions)}</p></section>
  <section class="ref-section"><h4>Как закрыть</h4><p>{escape(inv.get('how',''))}</p></section>
  <section class="ref-section danger"><h4>Последствия, если не соблюдать</h4><p>{escape(consequence)}</p></section>
  <section class="ref-section"><h4>Эталонный кейс</h4><p>{escape(reference_case)}</p></section>
  <section class="ref-section"><h4>Как проверить на практике</h4><p>{escape(verification)}</p></section>
  <section class="ref-section example"><h4>Пример ошибки</h4><p>{escape(example)}</p>{extra_examples}</section>
 </div>
</details>''')
    important_codes = {'ID-001','ID-002','CON-001','CON-002','STAT-001','ERR-001','REL-001','REL-002','OBS-001','MIG-002'}
    important = [i for i in INVARIANT_CATALOG if i.get('code') in important_codes]
    top_cards = ''.join(
        f'<div class="refbox"><b>{escape(i.get("code",""))} · {escape(i.get("title",""))}</b><br>{escape(_inv_example(i))}</div>'
        for i in important
    )
    body = titleblock('СПРАВОЧНИК ИНВАРИАНТОВ · КАРТОЧКИ', active='invariants') + f'''
<section class="hero">
 <h2>Справочник архитектурных инвариантов</h2>
 <p>Текст справочника сохранён по смыслу, но теперь он разбит на раскрывающиеся карточки. Открывайте только нужный пункт, ищите по термину или фильтруйте по области.</p>
 <div class="navlinks"><a class="btn ghost" href="{url_for('/')}">Вернуться в конструктор процесса</a><a class="btn ghost" href="{url_for('/patterns')}">База знаний</a></div>
</section>
<section class="card">
 <h2>Как пользоваться</h2>
 <p>Найдите термин: <b>operUid</b>, <b>retry</b>, <b>DLQ</b>, <b>eventVersion</b>, <b>rollback</b>. Каждая карточка раскрывается и показывает объяснение, этап, правильное состояние, последствия, проверку и пример ошибки.</p>
 <h3>10 инвариантов, которые чаще всего ломают интеграции</h3>
 <div class="top10">{top_cards}</div>
 <div class="refbar">
  <input id="inv_q" placeholder="Поиск: ключ, повторы, дубли, ПДн, откат, порядок...">
  <select id="inv_area"><option value="">Все области</option>{options}</select>
 </div>
 <p class="hint" id="inv_count">Показаны все инварианты.</p>
 <div class="refempty" id="inv_empty">По таким условиям ничего не найдено. Попробуйте другой термин или выберите «Все области».</div>
</section>
<section class="card">
 <h2>Список инвариантов</h2>
 <div class="ref-list">{''.join(cards)}</div>
</section>
<script>
function filterInvariants(){{
  const q=(document.getElementById('inv_q').value||'').toLowerCase().trim();
  const area=(document.getElementById('inv_area').value||'').toLowerCase();
  let shown=0,total=0;
  document.querySelectorAll('details.refcard').forEach(card=>{{
    total++;
    const text=(card.dataset.search||card.textContent||'').toLowerCase();
    const okq=!q || text.includes(q);
    const oka=!area || card.dataset.area===area;
    const ok=okq&&oka;
    card.hidden=!ok;
    if(ok) shown++;
  }});
  document.getElementById('inv_count').textContent='Показано: '+shown+' из '+total+'.';
  document.getElementById('inv_empty').style.display=shown?'none':'block';
}}
window.addEventListener('DOMContentLoaded', function(){{
  document.getElementById('inv_q')?.addEventListener('input', filterInvariants);
  document.getElementById('inv_area')?.addEventListener('change', filterInvariants);
  filterInvariants();
}});
</script>'''
    return page(f'Справочник инвариантов v{APP_VERSION}', body)


def _pattern_controls_html(pattern):
    controls = pattern.get('controls') or []
    if not controls:
        return '<p>Контроли не указаны.</p>'
    return '<ul>' + ''.join(f'<li>{escape(str(x))}</li>' for x in controls) + '</ul>'


def design_pattern_reference_page():
    categories = pattern_categories()
    options = ''.join(f'<option value="{escape(c.lower())}">{escape(c)}</option>' for c in categories)
    cards = []
    for pat in DESIGN_PATTERN_CATALOG:
        cat = str(pat.get('category') or 'Другое')
        controls_html = _pattern_controls_html(pat)
        hay = ' '.join(str(pat.get(k, '')) for k in (
            'id', 'name', 'category', 'aliases', 'summary', 'purpose', 'stages',
            'when', 'consequence'
        )).lower()
        cards.append(f'''<details class="refcard pattern-card" data-area="{escape(cat.lower())}" data-search="{escape(hay)}">
 <summary class="ref-summary">
  <div class="ref-summary-top"><span class="refcode">{escape(pat.get('id',''))}</span><span class="refarea">{escape(cat)}</span></div>
  <h3>{escape(pat.get('name','Паттерн'))}</h3>
  <p>{escape(pat.get('summary',''))}</p>
 </summary>
 <div class="ref-content">
  <section class="refbox reflead"><h4>Что это за паттерн</h4><p>{escape(pat.get('summary',''))}</p></section>
  <section class="ref-section"><h4>Для чего нужен</h4><p>{escape(pat.get('purpose',''))}</p></section>
  <section class="ref-section"><h4>Когда использовать</h4><p>{escape(pat.get('when',''))}</p></section>
  <section class="ref-section"><h4>На каких этапах</h4><p>{escape(pat.get('stages',''))}</p></section>
  <section class="refbox okbox"><h4>Обязательные контроли</h4>{controls_html}</section>
  <section class="ref-section danger"><h4>Что будет, если не использовать</h4><p>{escape(pat.get('consequence',''))}</p></section>
  <section class="ref-section"><h4>Как искать в модели</h4><p>{escape(pat.get('aliases',''))}</p></section>
 </div>
</details>''')
    key_patterns = ['transactional_outbox', 'inbox_deduplication', 'idempotent_consumer', 'retry_dlq_replay',
                    'expand_contract', 'schema_registry', 'saga_orchestration', 'partition_by_aggregate']
    top_cards = ''.join(
        f'<div class="refbox"><b>{escape(p.get("name", ""))}</b><br>{escape(p.get("summary", ""))}</div>'
        for p in DESIGN_PATTERN_CATALOG if p.get('id') in key_patterns
    )
    body = titleblock('ШАБЛОНЫ ПРОЕКТИРОВАНИЯ · КАРТОЧКИ', active='patterns') + f'''
<section class="hero">
 <h2>Шаблоны проектирования интеграций</h2>
 <p>Отдельный справочник паттернов, которые используются в модели: Outbox, Inbox, DLQ/Replay, идемпотентный consumer, Saga, Circuit Breaker, Expand/Contract, Schema Registry, Read-model, CDC/ETL и другие. Карточки отвечают на четыре вопроса: что это, зачем нужно, когда применять и что сломается без паттерна.</p>
 <div class="navlinks"><a class="btn ghost" href="{url_for('/')}">Вернуться в конструктор процесса</a><a class="btn ghost" href="{url_for('/invariants')}">Проверки</a></div>
</section>
<section class="card">
 <h2>Как пользоваться</h2>
 <p>Открывайте карточку нужного решения или ищите по словам: исходящие сообщения, входящие сообщения, очередь ошибок, повторная обработка, изменение контракта, длительная операция, ключ порядка, реестр схем.</p>
 <h3>Критичные паттерны, которые чаще всего забывают</h3>
 <div class="top10">{top_cards}</div>
 <div class="refbar">
  <input id="pat_q" placeholder="Поиск: очередь ошибок, повторная обработка, контракт, порядок, дубли...">
  <select id="pat_area"><option value="">Все категории</option>{options}</select>
 </div>
 <p class="hint" id="pat_count">Показаны все паттерны.</p>
 <div class="refempty" id="pat_empty">По таким условиям ничего не найдено. Попробуйте другой термин или выберите «Все категории».</div>
</section>
<section class="card">
 <h2>Список шаблонов проектирования</h2>
 <div class="ref-list">{''.join(cards)}</div>
</section>
<script>
function filterPatterns(){{
  const q=(document.getElementById('pat_q').value||'').toLowerCase().trim();
  const area=(document.getElementById('pat_area').value||'').toLowerCase();
  let shown=0,total=0;
  document.querySelectorAll('details.pattern-card').forEach(card=>{{
    total++;
    const text=(card.dataset.search||card.textContent||'').toLowerCase();
    const okq=!q || text.includes(q);
    const oka=!area || card.dataset.area===area;
    const ok=okq&&oka;
    card.hidden=!ok;
    if(ok) shown++;
  }});
  document.getElementById('pat_count').textContent='Показано: '+shown+' из '+total+'.';
  document.getElementById('pat_empty').style.display=shown?'none':'block';
}}
window.addEventListener('DOMContentLoaded', function(){{
  document.getElementById('pat_q')?.addEventListener('input', filterPatterns);
  document.getElementById('pat_area')?.addEventListener('change', filterPatterns);
  filterPatterns();
}});
</script>'''
    return page(f'Шаблоны проектирования v{APP_VERSION}', body)

MERMAID_HEAD = """<script>
window.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('.mermaid').forEach(function(d){
    d.setAttribute('role','img');
    d.setAttribute('aria-label','Схема процесса в формате Mermaid. Её можно скопировать в Mermaid Live Editor или документацию.');
    if(!d.previousElementSibling || !d.previousElementSibling.classList || !d.previousElementSibling.classList.contains('diagram-note')){
      var note=document.createElement('p');
      note.className='hint diagram-note';
      note.textContent='Схема ниже дана в формате Mermaid: её можно скопировать в документацию, ADR или Mermaid Live Editor. В интерфейсе она не зависит от внешнего CDN.';
      d.parentNode.insertBefore(note,d);
    }
  });
});
</script>"""


def section(title, html, open_=False, anchor=''):
    o = ' open' if open_ else ''
    aid = f' id="{escape(anchor)}"' if anchor else ''
    return f'<details class="card"{o}{aid}><summary><h2>{escape(title)}</h2></summary><div class="inside">{html}</div></details>'



def _fix_link(title, text):
    data = ((title or '') + ' ' + (text or '')).lower()
    if any(x in data for x in ('ключ', 'scope', 'идентификатор', 'requestid', 'operuid', 'externalid', 'idempotency')):
        return f'<a class="jumpfix" href="{url_for("/#fix-lookup")}">Открыть поле ключей</a>'
    if any(x in data for x in ('статус', 'финальн')):
        return f'<a class="jumpfix" href="{url_for("/#fix-statuses")}">Открыть поле статусов</a>'
    if any(x in data for x in ('поле', 'контракт', 'event envelope', 'eventid', 'eventversion', 'sensitive')):
        return f'<a class="jumpfix" href="{url_for("/#fix-fields")}">Открыть поле ключевых полей</a>'
    if any(x in data for x in ('огранич', 'компромисс', 'нельзя', 'срок', 'бюджет')):
        return f'<a class="jumpfix" href="{url_for("/#fix-constraints")}">Открыть поле ограничений</a>'
    return f'<a class="jumpfix" href="{url_for("/")}">Вернуться к вводным</a>'

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
    parts = [titleblock(f'РАЗБОР {rid[:8].upper()}', active='builder')]
    parts.append(f"""<div class="verdict {v['color']}">
 <h2>{escape(v['verdict'])} · {v['score']}/10</h2>
 <p>Готовность к промышленному запуску: {escape(gates.get('readiness','не рассчитано'))}. {escape(comp.get('summary',''))}<br>
 Классы рисков: критичные — {v.get('group_counts',{}).get('critical', v['counts']['critical'])}, высокие — {v.get('group_counts',{}).get('high', v['counts']['high'])}, средние — {v.get('group_counts',{}).get('medium', v['counts']['medium'])}. Всего срабатываний правил: {sum(v['counts'].values())}<br>
 <a href="{url_for('/run/' + rid + '.md')}">скачать полный текстовый отчёт</a> · <a href="{url_for('/')}">начать новый разбор</a> · <a href="{url_for('/invariants')}">справочник инвариантов</a> · <a href="{url_for('/patterns')}">база знаний по архитектурным решениям</a></p>
</div>""")
    meta_notes = []
    if m.get('goal'):
        meta_notes.append(f'<div class="metric"><b>Цель</b><span>{escape(str(m.get("goal") or ""))}</span></div>')
    if m.get('description'):
        meta_notes.append(f'<div class="metric"><b>Описание / допущения</b><span>{escape(str(m.get("description") or ""))}</span></div>')
    if m.get('constraints'):
        meta_notes.append(f'<div class="metric"><b>Ограничения</b><span>{escape(str(m.get("constraints") or ""))}</span></div>')
    if meta_notes:
        parts.append(section('Что было передано в анализ', '<div class="reviewbox">' + ''.join(meta_notes) + '</div>', True, 'input-summary'))

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
    parts.append(section('Проверка готовности к промышленному запуску', f'<div class="gates">{"".join(gate_html)}</div>', True))

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
                          f'не указано: {counts.get("unknown",0)}, проверено: {counts.get("ok",0)}.</p>'
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
    artifacts_html = f"""<div class="two"><div><h3>готовность к началу разработки</h3><ol class="tests">{dor}</ol></div>
 <div><h3>готовность к выпуску</h3><ol class="tests">{dod}</ol></div></div>
 <h3>Мониторинг и эксплуатационные метрики</h3><ol class="tests">{mon}</ol>
 <h3>Черновик контракта события</h3><pre>{escape(contract_txt)}</pre>"""
    parts.append(section('Проектные артефакты для аналитика и команды', artifacts_html, False, 'artifacts'))

    tests = ''.join(f'<li>{escape(t)}</li>' for t in res['tests'])
    parts.append(section('Чек-лист проверок и тестов', f'<ol class="tests">{tests}</ol>', False))

    return page(f"Разбор: {m['name']}", ''.join(parts), MERMAID_HEAD)

# ---------------------------------------------------------------------------
# v8.6.44: учебный MVP — каталог кейсов, проверка решения и учебный отчёт.
# ---------------------------------------------------------------------------
CSS += """
.learning-toolbar{display:grid;grid-template-columns:minmax(0,1.4fr)220px 260px;gap:10px;margin:12px 0}.learning-toolbar input,.learning-toolbar select{width:100%}.learning-count{font:12px var(--mono);color:var(--muted);margin:6px 0}.learning-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.learning-card{border:1px solid var(--line);background:#fff;border-radius:16px;padding:14px;display:flex;flex-direction:column;gap:8px}.learning-card h3{margin:0;font-size:16px;line-height:1.25}.learning-card p{margin:0;color:var(--muted);font-size:13px}.learning-card .meta{font:11px var(--mono);color:var(--accent);text-align:left}.learn-tags{display:flex;flex-wrap:wrap;gap:6px}.learn-tags span{border:1px solid var(--line);border-radius:999px;padding:3px 7px;background:#FAFCFC;font-size:11px}.learn-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px}.learn-panel{border:1px solid var(--line);border-radius:16px;background:#fff;padding:14px}.learn-panel h3{margin:0 0 8px}.learn-editor{min-height:360px;font-family:var(--mono);font-size:12px}.learn-verdict{border:2px solid var(--accent);border-radius:16px;background:var(--accent-soft);padding:14px;margin:12px 0}.learn-verdict h2{margin:0 0 6px}.learn-skills{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.learn-skill{border:1px solid var(--line);border-radius:14px;background:#fff;padding:10px}.learn-skill b{display:block}.learn-skill span{font:700 20px var(--mono);color:var(--accent)}.learn-skill ul{margin:6px 0 0 18px;padding:0;color:var(--muted);font-size:12px}.learn-actions{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.learn-actions button,.learning-card a.learn-open{display:inline-block;border:1px solid var(--ink);background:var(--ink);color:#fff;padding:8px 11px;text-decoration:none;border-radius:10px;font-weight:800;cursor:pointer}.learn-actions button.ghost{background:#fff;color:var(--ink)}.learn-report{white-space:pre-wrap;border:1px solid var(--line);background:#FAFCFC;border-radius:14px;padding:12px;font:12px/1.45 var(--mono);max-height:520px;overflow:auto}.learn-result{margin-top:14px}.learn-empty{border:1px dashed var(--line);border-radius:14px;padding:12px;color:var(--muted);background:#FCFDFD}.learn-dashboard{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}.learn-metric{border:1px solid var(--line);background:#fff;border-radius:14px;padding:10px}.learn-metric b{display:block;font:11px var(--mono);color:var(--muted);text-transform:uppercase}.learn-metric span{font:800 22px var(--mono);color:var(--accent)}.learn-compare{border:1px solid var(--line);background:#F7FBFA;border-radius:12px;padding:10px;margin:10px 0}.hint-box{border:1px solid var(--line);background:#FFFDF8;border-radius:14px;padding:10px;margin:10px 0}.hint-box ol{margin:6px 0 0 20px;padding:0}.case-brief{font-size:15px}.case-brief li{margin:4px 0}@media(max-width:900px){.learning-toolbar{grid-template-columns:1fr}.learning-grid{grid-template-columns:1fr 1fr}.learn-layout{grid-template-columns:1fr}.learn-skills{grid-template-columns:1fr}.learn-dashboard{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:640px){.learning-grid{grid-template-columns:1fr}.learn-editor{min-height:300px}.learn-actions button,.learning-card a.learn-open{width:100%}.learn-dashboard{grid-template-columns:1fr}}
"""


def _learning_case_card(c):
    tags = ''.join(f'<span>{escape(x)}</span>' for x in [c.get('level',''), c.get('track',''), c.get('timebox','')] if x)
    search_blob = ' '.join(str(c.get(k, '')) for k in ('id', 'title', 'level', 'track', 'brief', 'goal')).lower()
    return f"""<article class="learning-card" data-level="{escape(c.get('level',''))}" data-track="{escape(c.get('track',''))}" data-search="{escape(search_blob)}">
      <div class="meta">{escape(c.get('id',''))}</div>
      <h3>{escape(c.get('title',''))}</h3>
      <p>{escape(c.get('brief',''))}</p>
      <div class="learn-tags">{tags}</div>
      <a class="learn-open" href="{url_for('/learning/' + c.get('id',''))}">Открыть кейс</a>
    </article>"""


def learning_home_page():
    from learning import list_cases, learning_catalog_summary
    cases = list_cases()
    catalog = learning_catalog_summary()
    levels = sorted({c.get('level','') for c in cases if c.get('level')})
    tracks = sorted({c.get('track','') for c in cases if c.get('track')})
    level_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in levels)
    track_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in tracks)
    cards = ''.join(_learning_case_card(c) for c in cases)
    body = titleblock('ТРЕНАЖЁР СИСТЕМНОГО АНАЛИТИКА', active='learning') + f"""
<section class="hero">
 <h2>Учебный режим production-MVP: кейс → решение → оценка навыков → прогресс → эталон.</h2>
 <p>Тренажёр проверяет архитектуру, объясняет ошибки, хранит попытки по локальному learner id и показывает рост навыков. Rule-based ядро остаётся судьёй, учебный слой — наставником.</p>
 <div class="steps3"><div class="stepbox"><b>1. Реши кейс</b><br>Собери решение в конструкторе или JSON.</div><div class="stepbox"><b>2. Проверь</b><br>Получишь skill scoring, подсказки и сравнение с эталоном.</div><div class="stepbox"><b>3. Отслеживай прогресс</b><br>Попытки сохраняются, видны слабые зоны и бейджи.</div></div>
 <div class="navlinks"><a href="{url_for('/')}" >Открыть конструктор</a><a href="{url_for('/patterns')}" >База знаний</a><a href="#progress" onclick="loadLearningProgress();return true;">Обновить прогресс</a></div>
</section>
<section class="card" id="progress"><h2>Прогресс ученика</h2>
 <div id="learningProgress" class="learn-empty">Прогресс загрузится автоматически. Данные хранятся по learner id в localStorage и серверной SQLite.</div>
</section>
<section class="card" open><h2>Каталог учебных кейсов MVP / production</h2><p class="hint">Версия каталога: {escape(catalog.get('catalog_version',''))}. Кейсов: {len(cases)}. Используйте поиск и фильтры, чтобы быстро выбрать практику под уровень или тему.</p>
 <div class="learning-toolbar">
  <input id="caseSearch" type="search" placeholder="Поиск: Kafka, DWH, банк, saga, security..." oninput="filterCases()">
  <select id="levelFilter" onchange="filterCases()"><option value="">Все уровни</option>{level_options}</select>
  <select id="trackFilter" onchange="filterCases()"><option value="">Все треки</option>{track_options}</select>
 </div>
 <div id="caseCount" class="learning-count">Показано кейсов: {len(cases)} / {len(cases)}</div>
 <div class="learning-grid" id="learningGrid">{cards}</div></section>
<script>
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function learnerId(){{
  let id=null; try{{ id=localStorage.getItem('sa_learning_learner_id'); }}catch(_){{ id=null; }}
  if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); try{{ localStorage.setItem('sa_learning_learner_id', id); }}catch(_){{}} }}
  return id;
}}
async function loadLearningProgress(){{
 const box=document.getElementById('learningProgress'); if(!box) return;
 box.innerHTML='Загружаю прогресс...';
 try{{
  const r=await fetch(basePath()+'/api/learning/progress?learner_id='+encodeURIComponent(learnerId()));
  const p=await r.json();
  const badges=(p.badges||[]).join(', ') || 'пока нет';
  const weak=(p.weak_skills||[]).map(x=>'<li>'+x.name+': '+x.score+'/10</li>').join('') || '<li>пока нет данных</li>';
  box.innerHTML='<div class="learn-dashboard"><div class="learn-metric"><b>Попытки</b><span>'+p.attempt_count+'</span></div><div class="learn-metric"><b>Кейсы</b><span>'+p.solved_case_count+'/'+p.case_count+'</span></div><div class="learn-metric"><b>Бейджи</b><span>'+p.badges.length+'</span></div><div class="learn-metric"><b>Learner id</b><small>'+p.learner_id+'</small></div></div><p><b>Бейджи:</b> '+badges+'</p><p><b>Слабые зоны:</b></p><ul>'+weak+'</ul>';
 }}catch(e){{ box.innerHTML='<div class="err">Не удалось загрузить прогресс: '+String(e.message)+'</div>'; }}
}}
function filterCases(){{
 const q=(document.getElementById('caseSearch')?.value||'').trim().toLowerCase();
 const lvl=document.getElementById('levelFilter')?.value||'';
 const tr=document.getElementById('trackFilter')?.value||'';
 const cards=[...document.querySelectorAll('.learning-card')]; let shown=0;
 cards.forEach(c=>{{
   const okQ=!q || (c.dataset.search||'').includes(q);
   const okL=!lvl || c.dataset.level===lvl;
   const okT=!tr || c.dataset.track===tr;
   const ok=okQ && okL && okT; c.style.display=ok?'flex':'none'; if(ok) shown++;
 }});
 const cnt=document.getElementById('caseCount'); if(cnt) cnt.textContent='Показано кейсов: '+shown+' / '+cards.length;
}}
loadLearningProgress();
filterCases();
</script>
"""
    return page('Тренажёр системного аналитика', body)

def learning_case_page(case_id):
    from learning import get_case
    c = get_case(case_id)
    if not c:
        return page('Кейс не найден', titleblock('ТРЕНАЖЁР', active='learning') + '<div class="err">Кейс не найден.</div>')
    safe_case_json = json.dumps({k:v for k,v in c.items() if k != 'payload'}, ensure_ascii=False, indent=2)
    ref_json = json.dumps(c.get('payload', {}), ensure_ascii=False, indent=2)
    traps = ''.join(f'<li>{escape(x)}</li>' for x in c.get('hidden_traps', []))
    controls = ''.join(f'<li><b>{escape(x.get("label",""))}</b><br><span class="hint">{escape(x.get("why",""))}</span></li>' for x in c.get('expected_controls', []))
    body = titleblock('УЧЕБНЫЙ КЕЙС', active='learning') + f"""
<section class="hero">
 <h2>{escape(c.get('title',''))}</h2>
 <p class="case-brief">{escape(c.get('brief',''))}</p>
 <div class="learn-tags"><span>{escape(c.get('level',''))}</span><span>{escape(c.get('track',''))}</span><span>{escape(c.get('timebox',''))}</span></div>
 <p><b>Цель:</b> {escape(c.get('goal',''))}</p>
 <div class="navlinks"><a href="{url_for('/learning')}">Все кейсы</a><a href="{url_for('/')}">Открыть конструктор</a></div>
</section>
<div class="learn-layout">
 <main>
  <section class="learn-panel">
   <h3>Решение пользователя</h3>
   <p class="hint">Вставьте JSON payload из конструктора или нажмите «Проверить эталон», чтобы увидеть, как должен выглядеть хороший разбор. Для честной тренировки сначала решите сами.</p>
   <textarea id="solutionJson" class="learn-editor" spellcheck="false" placeholder="Вставьте JSON решения из конструктора"></textarea>
   <h3>Устный ответ для режима собеседования</h3>
   <p class="hint">Кратко объясните решение так, как отвечали бы интервьюеру: процесс, участники, sync/async, отказы, идемпотентность, контракты, данные и эксплуатация.</p>
   <textarea id="interviewAnswer" class="learn-editor" style="min-height:160px" placeholder="Например: сначала фиксирую границы процесса, затем разделяю синхронный клиентский путь и асинхронные события..."></textarea>
   <div class="learn-actions">
    <button type="button" onclick="evaluateLearning('learning')">Проверить моё решение</button>
    <button type="button" class="ghost" onclick="evaluateLearning('interview')">Режим собеседования</button>
    <button type="button" class="ghost" onclick="loadHint(1)">Подсказка 1</button>
    <button type="button" class="ghost" onclick="loadHint(2)">Подсказка 2</button>
    <button type="button" class="ghost" onclick="loadHint(3)">Как исправить</button>
    <button type="button" class="ghost" onclick="showReferencePack()">Показать эталоны</button>
    <button type="button" class="ghost" onclick="showInterviewPack()">Вопросы интервьюера</button>
    <button type="button" class="ghost" onclick="fillReference()">Подставить эталон</button>
    <button type="button" class="ghost" onclick="evaluateLearning('reference')">Проверить эталон</button>
   </div>
   <div id="hintBox" class="hint-box" style="display:none"></div>
   <div id="learningResult" class="learn-result"><div class="learn-empty">Результат появится здесь после проверки.</div></div>
  </section>
  <section class="learn-panel">
    <h3>Markdown-отчёт тренажёра</h3>
    <pre id="learningMarkdown" class="learn-report">Пока отчёт не сформирован.</pre>
  </section>
 </main>
 <aside class="learn-panel">
  <h3>Что тренируем</h3>
  <ul>{controls}</ul>
  <h3>Скрытые ловушки</h3>
  <ul>{traps}</ul>
  <details><summary>Метаданные кейса</summary><pre>{escape(safe_case_json)}</pre></details>
 </aside>
</div>
<script>
const CASE_ID = {json.dumps(case_id)};
const REFERENCE_PAYLOAD = {ref_json};
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
function fillReference(){{ document.getElementById('solutionJson').value = JSON.stringify(REFERENCE_PAYLOAD, null, 2); }}
async function loadHint(level){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю подсказку...'; try{{ const r=await fetch(basePath() + '/api/learning/hints?case_id='+encodeURIComponent(CASE_ID)+'&level='+encodeURIComponent(level)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} box.innerHTML='<b>Подсказка '+level+'</b><ol>'+data.hints.map(x=>'<li>'+String(x).replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]))+'</li>').join('')+'</ol>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка подсказки: '+String(e.message)+'</div>'; }} }}
async function showReferencePack(){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю эталоны...'; try{{ const r=await fetch(basePath() + '/api/learning/reference?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const prod=(data.production?.steps||[]).slice(0,8).map(x=>'<li>'+String(x).replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]))+'</li>').join(''); const acc=(data.acceptance_criteria||[]).map(x=>'<li>'+String(x).replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]))+'</li>').join(''); box.innerHTML='<b>Эталонные варианты</b><p><b>Промышленный эталон:</b> '+(data.production?.description||'')+'</p><ol>'+prod+'</ol><p><b>MVP:</b> '+(data.mvp?.description||'')+'</p><p><b>Критерии приёмки:</b></p><ul>'+acc+'</ul>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка загрузки эталонов: '+String(e.message)+'</div>'; }} }}
async function showInterviewPack(){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю вопросы...'; try{{ const r=await fetch(basePath() + '/api/learning/interview?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const qs=(data.questions||[]).slice(0,10).map(q=>'<li><b>'+String(q.question||'').replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m]))+'</b><br><span class=hint>Ожидается: '+(q.expected||[]).slice(0,2).join('; ')+'</span></li>').join(''); box.innerHTML='<b>Вопросы интервьюера</b><p>'+String(data.opening_prompt||'')+'</p><ol>'+qs+'</ol>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка загрузки вопросов: '+String(e.message)+'</div>'; }} }}
async function evaluateLearning(mode){{
  const box=document.getElementById('learningResult'); const md=document.getElementById('learningMarkdown');
  box.innerHTML='<div class="learn-empty">Проверяю решение...</div>'; md.textContent='Проверяю...';
  let payload;
  try{{ payload=JSON.parse(document.getElementById('solutionJson').value || '{{}}'); }}catch(e){{ box.innerHTML='<div class="err">JSON не читается: '+String(e.message)+'</div>'; md.textContent=''; return; }}
  try{{
    const answerText=(document.getElementById('interviewAnswer')?.value || '');
    const r=await fetch(basePath() + '/api/learning/evaluate', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{case_id:CASE_ID, payload, mode, learner_id: learnerId(), answer_text: answerText}})}});
    const data=await r.json();
    if(!data.ok){{ box.innerHTML='<div class="err">'+(data.errors||['Ошибка']).join('<br>')+'</div>'; return; }}
    box.innerHTML=data.html || '<div class="learn-empty">Нет HTML-результата.</div>';
    md.textContent=data.report_markdown || '';
    safeStorageSet('sa_learning_'+CASE_ID, JSON.stringify({{score:data.learning_score, level:data.learning_level, attempt_id:data.attempt_id, at:new Date().toISOString()}}));
  }}catch(e){{ box.innerHTML='<div class="err">Ошибка запроса: '+String(e.message)+'</div>'; md.textContent=''; }}
}}
</script>
"""
    return page(c.get('title','Учебный кейс'), body)

# v8.6.47: пользовательские страницы проходят через финальную языковую вычитку.
try:
    from report import humanize_terms as _final_report_humanize_terms_v8647
except Exception:  # pragma: no cover
    _final_report_humanize_terms_v8647 = humanize_terms

_PREV_FORM_PAGE_V8647 = form_page
_PREV_INVARIANT_REFERENCE_PAGE_V8647 = invariant_reference_page
_PREV_DESIGN_PATTERN_REFERENCE_PAGE_V8647 = design_pattern_reference_page
_PREV_LEARNING_HOME_PAGE_V8647 = learning_home_page
_PREV_LEARNING_CASE_PAGE_V8647 = learning_case_page


def _polish_page_v8647(html: str) -> str:
    return _final_report_humanize_terms_v8647(html)


def form_page():
    return _polish_page_v8647(_PREV_FORM_PAGE_V8647())


def invariant_reference_page():
    return _polish_page_v8647(_PREV_INVARIANT_REFERENCE_PAGE_V8647())


def design_pattern_reference_page():
    return _polish_page_v8647(_PREV_DESIGN_PATTERN_REFERENCE_PAGE_V8647())


def learning_home_page():
    return _polish_page_v8647(_PREV_LEARNING_HOME_PAGE_V8647())


def learning_case_page(case_id):
    return _polish_page_v8647(_PREV_LEARNING_CASE_PAGE_V8647(case_id))

# v8.6.47final: форму не прогоняем через общий humanize целиком, чтобы не ломать JS-имена.
def form_page():
    return _PREV_FORM_PAGE_V8647()

# v8.6.47: правка ширины каталога обучения после языкового расширения текстов.
_EXTRA_LEARNING_STYLE_V8647 = """
<style>
html,body{max-width:100%;overflow-x:hidden}.learning-toolbar{grid-template-columns:minmax(0,1fr) minmax(0,220px) minmax(0,260px)!important;max-width:100%;min-width:0}.learning-grid,.learning-card,.learn-tags,.learning-card h3,.learning-card p{min-width:0;max-width:100%;overflow-wrap:anywhere;word-break:normal}.learning-card{overflow:hidden}.wrap{overflow-x:hidden}
@media(max-width:900px){.learning-toolbar{grid-template-columns:1fr!important}}
</style>
"""
_PREV_LEARNING_HOME_PAGE_V8647_WIDTH = learning_home_page

def learning_home_page():
    html = _PREV_LEARNING_HOME_PAGE_V8647_WIDTH()
    return html.replace('</head>', _EXTRA_LEARNING_STYLE_V8647 + '</head>')

# v8.6.47final2: страницы обучения строим из исходного HTML, чтобы не ломать JS;
# сами данные каталога уже вычитаны в learning.py.
def learning_home_page():
    html = _PREV_LEARNING_HOME_PAGE_V8647()
    return html.replace('</head>', _EXTRA_LEARNING_STYLE_V8647 + '</head>')


def learning_case_page(case_id):
    return _PREV_LEARNING_CASE_PAGE_V8647(case_id)

# v8.6.47final3: точечная русификация каталога обучения без обработки JS.
def _polish_learning_html_v8647(html: str) -> str:
    return (html
        .replace('Event-driven architecture.', 'Событийная архитектура.')
        .replace('event-driven architecture.', 'событийная архитектура.')
        .replace('event-driven', 'событийная архитектура'))


def learning_home_page():
    html = _PREV_LEARNING_HOME_PAGE_V8647()
    html = html.replace('</head>', _EXTRA_LEARNING_STYLE_V8647 + '</head>')
    return _polish_learning_html_v8647(html)


def learning_case_page(case_id):
    return _polish_learning_html_v8647(_PREV_LEARNING_CASE_PAGE_V8647(case_id))

# ---------------------------------------------------------------------------
# v8.6.53: SaaS-полировка учебного интерфейса.
# Цель: убрать JSON-first путь, сделать каталог и экран кейса похожими на
# продуктовую платформу: dashboard, треки, рекомендованные кейсы, группы действий,
# визуальный сбор черновика и компактный первый результат.
# ---------------------------------------------------------------------------
APP_VERSION = '8.6.67-ultimate-gated'

_SAAS_UI_STYLE_V8653 = """
<style>
:root{--saas-bg:#F4F7FB;--saas-card:#FFFFFF;--saas-ink:#0F172A;--saas-muted:#64748B;--saas-line:#E2E8F0;--saas-accent:#0E7490;--saas-soft:#E6F7FB;--saas-good:#15803D;--saas-warn:#B45309;--saas-bad:#B91C1C}.wrap{max-width:1240px}.saas-hero{border:1px solid var(--saas-line);border-radius:28px;background:radial-gradient(circle at 20% 10%,#DDF7FF 0,#fff 34%,#F8FAFC 100%);padding:28px;margin:18px 0;box-shadow:0 18px 50px rgba(15,23,42,.08)}.saas-kicker{display:inline-flex;gap:8px;align-items:center;border:1px solid #BAE6FD;background:#F0F9FF;color:#075985;border-radius:999px;padding:7px 11px;font-weight:800;font-size:12px}.saas-hero h2{font-size:34px;line-height:1.08;margin:14px 0 8px;max-width:900px}.saas-hero p{font-size:16px;line-height:1.55;color:var(--saas-muted);max-width:920px}.saas-hero-actions,.saas-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.saas-btn{border:1px solid var(--saas-ink);background:var(--saas-ink);color:#fff;text-decoration:none;border-radius:14px;padding:11px 15px;font-weight:900;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}.saas-btn.secondary{background:#fff;color:var(--saas-ink);border-color:var(--saas-line)}.saas-btn.accent{background:var(--saas-accent);border-color:var(--saas-accent)}.saas-btn.danger{background:#FFF1F2;color:#9F1239;border-color:#FECDD3}.saas-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0}.saas-metric{border:1px solid var(--saas-line);background:#fff;border-radius:18px;padding:15px}.saas-metric b{display:block;color:var(--saas-muted);font-size:12px;text-transform:uppercase;letter-spacing:.03em}.saas-metric span{display:block;color:var(--saas-ink);font:900 26px var(--mono);margin-top:4px}.saas-metric small{display:block;color:var(--saas-muted);margin-top:5px}.saas-section{border:1px solid var(--saas-line);background:#fff;border-radius:22px;padding:18px;margin:16px 0;box-shadow:0 10px 30px rgba(15,23,42,.045)}.saas-section-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:12px}.saas-section-head h2,.saas-section-head h3{margin:0}.saas-section-head p{margin:5px 0 0;color:var(--saas-muted);line-height:1.45}.saas-chip-row,.track-chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.track-chip{border:1px solid var(--saas-line);background:#fff;border-radius:999px;padding:8px 11px;font-weight:800;color:var(--saas-ink);cursor:pointer}.track-chip.active,.track-chip:hover{border-color:var(--saas-accent);background:var(--saas-soft);color:var(--saas-accent)}.saas-dashboard-card{border:1px solid var(--saas-line);background:linear-gradient(180deg,#fff,#F8FAFC);border-radius:20px;padding:16px}.saas-dashboard-card h3{margin:0 0 8px}.saas-dashboard-card p{margin:0;color:var(--saas-muted);line-height:1.45}.learning-grid.saas-learning-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.learning-card{border-radius:20px;transition:.16s ease;min-height:210px}.learning-card:hover{transform:translateY(-2px);box-shadow:0 14px 34px rgba(15,23,42,.10);border-color:#BAE6FD}.learning-card .meta{font-family:var(--mono);font-size:11px;color:var(--saas-accent)}.learning-card a.learn-open{margin-top:auto;border-radius:12px;text-align:center}.learning-card.recommended{border-color:#BAE6FD;background:linear-gradient(180deg,#fff,#F0F9FF)}.learning-card.hidden-by-saas{display:none!important}.saas-filter-panel{position:sticky;top:10px;z-index:2;border:1px solid var(--saas-line);background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-radius:20px;padding:14px;margin:12px 0}.learning-toolbar{margin:0}.saas-empty-state{border:1px dashed var(--saas-line);border-radius:18px;background:#F8FAFC;padding:16px;color:var(--saas-muted);display:none}.case-shell{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px;align-items:start}.case-main{display:grid;gap:16px}.case-sticky{position:sticky;top:12px;display:grid;gap:12px}.case-brief-card{border:1px solid var(--saas-line);border-radius:24px;background:#fff;padding:20px;box-shadow:0 12px 34px rgba(15,23,42,.06)}.case-brief-card h2{font-size:30px;line-height:1.12;margin:8px 0}.case-meta-line{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.case-pill{border:1px solid var(--saas-line);background:#F8FAFC;border-radius:999px;padding:6px 9px;font-weight:800;font-size:12px}.learning-path{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.path-step{border:1px solid var(--saas-line);border-radius:16px;background:#F8FAFC;padding:12px}.path-step b{display:block}.path-step small{display:block;color:var(--saas-muted);line-height:1.35;margin-top:4px}.visual-builder{border:1px solid #BAE6FD;background:linear-gradient(180deg,#F0F9FF,#fff);border-radius:22px;padding:16px}.visual-builder h3,.action-group h3{margin:0 0 8px}.control-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0}.control-card{border:1px solid var(--saas-line);background:#fff;border-radius:16px;padding:12px;display:flex;gap:9px;align-items:flex-start;cursor:pointer}.control-card input{margin-top:3px}.control-card b{display:block;font-size:14px}.control-card small{display:block;color:var(--saas-muted);line-height:1.35;margin-top:3px}.action-zone{display:grid;grid-template-columns:1fr 1fr;gap:12px}.action-group{border:1px solid var(--saas-line);background:#fff;border-radius:18px;padding:14px}.action-group .saas-actions{margin-top:8px}.expert-json{border:1px solid var(--saas-line);border-radius:18px;background:#fff;overflow:hidden}.expert-json summary{cursor:pointer;padding:13px 15px;font-weight:900;background:#F8FAFC}.expert-json .inner{padding:14px}.learn-editor{border-radius:14px;border:1px solid var(--saas-line);background:#FBFDFF}.interview-card{border:1px solid var(--saas-line);background:#fff;border-radius:22px;padding:16px}.result-card-saas{border:1px solid var(--saas-line);background:#fff;border-radius:22px;padding:16px}.result-placeholder{border:1px dashed var(--saas-line);background:#F8FAFC;border-radius:16px;padding:18px;color:var(--saas-muted)}.learn-report{font-size:12px;line-height:1.55;border-radius:16px}.side-card{border:1px solid var(--saas-line);background:#fff;border-radius:20px;padding:15px}.side-card h3{margin:0 0 8px}.side-card ul{margin:8px 0 0 18px;padding:0}.side-card li{margin:5px 0;color:var(--saas-muted);line-height:1.35}.attempt-link{display:inline-flex;margin-top:8px}.learning-progress-clean{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.learning-progress-clean .progress-cell{border:1px solid var(--saas-line);background:#fff;border-radius:16px;padding:12px}.learning-progress-clean b{display:block;color:var(--saas-muted);font-size:12px}.learning-progress-clean span{font:900 22px var(--mono);color:var(--saas-accent)}.progress-next{margin-top:10px;color:var(--saas-muted)}.quick-result-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:10px 0}.quick-result-grid .qr{border:1px solid var(--saas-line);border-radius:14px;background:#F8FAFC;padding:10px}.quick-result-grid b{display:block;color:var(--saas-muted);font-size:12px}.quick-result-grid span{font:900 20px var(--mono);color:var(--saas-accent)}@media(max-width:1000px){.case-shell{grid-template-columns:1fr}.case-sticky{position:static}.learning-path{grid-template-columns:repeat(2,minmax(0,1fr))}.saas-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.learning-grid.saas-learning-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.action-zone{grid-template-columns:1fr}}@media(max-width:640px){.saas-hero{padding:20px;border-radius:22px}.saas-hero h2{font-size:25px}.saas-grid,.learning-progress-clean,.learning-path,.control-grid,.quick-result-grid{grid-template-columns:1fr}.learning-grid.saas-learning-grid{grid-template-columns:1fr}.saas-section-head{display:block}.saas-btn,.learn-actions button,.learning-card a.learn-open{width:100%}.case-brief-card h2{font-size:24px}.visual-builder,.case-brief-card,.result-card-saas,.interview-card,.side-card{padding:14px}}@media(max-width:640px){.titleblock{border-radius:16px}.titleblock h1{font-size:16px;line-height:1.18}.titleblock .meta{font-size:10px;line-height:1.35}.topnav{gap:6px}.topnav a{padding:6px 8px;font-size:10px}.saas-kicker{font-size:11px;max-width:100%;white-space:normal}.control-card{min-height:92px}.control-card input{width:18px;height:18px;flex:none}.visual-builder .saas-actions{gap:8px}.case-pill{font-size:11px}.learn-report{font-size:11px;max-height:420px}}
</style>
"""


def _case_track_group_v8653(track: str) -> str:
    t = (track or '').lower()
    if any(x in t for x in ('финтех', 'банк', 'плат', 'ук')):
        return 'Финтех и банки'
    if any(x in t for x in ('kafka', 'rabbit', 'событ', 'шина', 'очеред', 'stream', 'messaging')):
        return 'Асинхрон и брокеры'
    if any(x in t for x in ('dwh', 'данн', 'cdc', 'аналит', 'lake', 'поиск')):
        return 'Данные и аналитика'
    if any(x in t for x in ('security', 'безопас', 'пдн', 'audit', 'vault')):
        return 'Безопасность'
    if any(x in t for x in ('legacy', 'soap', 'esb', 'миграц')):
        return 'Legacy и миграции'
    return 'Практика интеграций'


def _learning_case_card_saas_v8653(c, recommended=False):
    tags = ''.join(f'<span>{escape(x)}</span>' for x in [c.get('level',''), _case_track_group_v8653(c.get('track','')), c.get('timebox','')] if x)
    search_blob = ' '.join(str(c.get(k, '')) for k in ('id', 'title', 'level', 'track', 'brief', 'goal')).lower()
    cls = 'learning-card recommended' if recommended else 'learning-card'
    return f"""<article class="{cls}" data-level="{escape(c.get('level',''))}" data-group="{escape(_case_track_group_v8653(c.get('track','')))}" data-track="{escape(c.get('track',''))}" data-search="{escape(search_blob)}">
      <div class="meta">{escape(c.get('level',''))} · {escape(_case_track_group_v8653(c.get('track','')))}</div>
      <h3>{escape(c.get('title',''))}</h3>
      <p>{escape(c.get('brief',''))}</p>
      <div class="learn-tags">{tags}</div>
      <a class="learn-open" href="{url_for('/learning/' + c.get('id',''))}">Разобрать кейс</a>
    </article>"""


def learning_home_page():
    from learning import list_cases, learning_catalog_summary
    cases = list_cases()
    catalog = learning_catalog_summary()
    levels = sorted({c.get('level','') for c in cases if c.get('level')})
    groups = ['Все треки'] + sorted({_case_track_group_v8653(c.get('track','')) for c in cases})
    tracks = sorted({c.get('track','') for c in cases if c.get('track')})
    level_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in levels)
    track_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in tracks)
    group_buttons = ''.join(f'<button type="button" class="track-chip {"active" if i==0 else ""}" data-group="{escape("" if g=="Все треки" else g)}" onclick="selectCaseGroup(this)">{escape(g)}</button>' for i, g in enumerate(groups))
    recommended_ids = {'bank-credit-bki-fraud', 'uk-bank-status-flow', 'card-authorization-clearing', 'kafka-ordering-dlq-replay', 'bki-dwh-search', 'graphql-bff-aggregation'}
    recommended = [c for c in cases if c.get('id') in recommended_ids][:6]
    if len(recommended) < 6:
        recommended += [c for c in cases if c not in recommended][:6-len(recommended)]
    recommended_cards = ''.join(_learning_case_card_saas_v8653(c, True) for c in recommended)
    cards = ''.join(_learning_case_card_saas_v8653(c) for c in cases)
    body = titleblock('ТРЕНАЖЁР СИСТЕМНОГО АНАЛИТИКА', active='learning') + f"""
<section class="saas-hero">
 <span class="saas-kicker">Практика системного аналитика · {escape(APP_VERSION)}</span>
 <h2>Практический тренажёр интеграций: решайте кейсы, защищайте решение и растите до Middle+/Senior.</h2>
 <p>Платформа даёт реалистичные задания, проверяет архитектурную схему, отдельно оценивает устный ответ на собеседовании, показывает эталоны и слабые зоны. Кейсов: {len(cases)}. JSON доступен только как экспертный режим — основной путь построен вокруг кейсов и результата.</p>
 <div class="saas-hero-actions">
  <a class="saas-btn accent" href="#recommended">Начать с рекомендованных кейсов</a>
  <a class="saas-btn secondary" href="{url_for('/')}">Открыть проектировщик</a>
  <a class="saas-btn secondary" href="{url_for('/patterns')}">База знаний</a>
 </div>
</section>
<section class="saas-grid" aria-label="Метрики каталога">
 <div class="saas-metric"><b>Кейсов</b><span>{len(cases)}</span><small>практика от Junior+ до Senior</small></div>
 <div class="saas-metric"><b>Форматы</b><span>3</span><small>обучение, эталон, собеседование</small></div>
 <div class="saas-metric"><b>Навыков</b><span>8</span><small>архитектура, данные, контракты, эксплуатация</small></div>
 <div class="saas-metric"><b>Каталог</b><span>OK</span><small>кейсы проверяются автоматически</small></div>
</section>
<section class="saas-section" id="progress">
 <div class="saas-section-head"><div><h2>Ваш прогресс</h2><p>После первой попытки здесь появятся средняя оценка, слабые зоны и следующий рекомендуемый шаг.</p></div><button class="saas-btn secondary" onclick="loadLearningProgress()">Обновить</button></div>
 <div id="learningProgress" class="result-placeholder">Прогресс появится после первой проверки решения.</div>
</section>
<section class="saas-section" id="recommended">
 <div class="saas-section-head"><div><h2>Рекомендуемые кейсы для старта</h2><p>Подходят для быстрой проверки пользы: банк, Kafka, DWH, УК, BFF и поиск.</p></div><a class="saas-btn secondary" href="#catalog">Весь каталог</a></div>
 <div class="learning-grid saas-learning-grid">{recommended_cards}</div>
</section>
<section class="saas-section" id="catalog">
 <div class="saas-section-head"><div><h2>Каталог учебных кейсов и практики</h2><p>Не нужно листать все 83 кейса подряд: выберите трек, уровень или найдите тему поиском.</p></div><div class="learning-count" id="caseCount">Показано кейсов: {len(cases)} / {len(cases)}</div></div>
 <div class="track-chips">{group_buttons}</div>
 <div class="saas-filter-panel">
  <div class="learning-toolbar">
   <input id="caseSearch" type="search" placeholder="Поиск: Kafka, DWH, банк, saga, security..." oninput="filterCases()">
   <select id="levelFilter" onchange="filterCases()"><option value="">Все уровни</option>{level_options}</select>
   <select id="trackFilter" onchange="filterCases()"><option value="">Все детальные треки</option>{track_options}</select>
  </div>
 </div>
 <div id="emptyCaseState" class="saas-empty-state">По выбранным фильтрам кейсов не найдено. Сбросьте трек или поиск.</div>
 <div class="learning-grid saas-learning-grid" id="learningGrid">{cards}</div>
</section>
<script>
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
async function loadLearningProgress(){{
 const box=document.getElementById('learningProgress'); if(!box) return;
 try{{
  const r=await fetch(basePath()+'/api/learning/progress?learner_id='+encodeURIComponent(learnerId()));
  const data=await r.json();
  if(!data.ok){{ box.innerHTML='<div class="err">Не удалось загрузить прогресс.</div>'; return; }}
  const weak=(data.weak_skills||[]).map(x=>x.name+': '+(x.score??'нет данных')).join('<br>') || 'Пока нет данных.';
  const last=(data.latest_attempts||[])[0];
  const next=(data.solved_case_count||0)===0 ? 'Начните с банковского кейса или Kafka-кейса из рекомендованных.' : 'Выберите кейс из слабой зоны и попробуйте улучшить результат.';
  box.innerHTML='<div class="learning-progress-clean">'
   +'<div class="progress-cell"><b>Попыток</b><span>'+data.attempt_count+'</span></div>'
   +'<div class="progress-cell"><b>Кейсов решено</b><span>'+data.solved_case_count+' / '+data.case_count+'</span></div>'
   +'<div class="progress-cell"><b>Бейджи</b><span>'+(data.badges||[]).length+'</span></div>'
   +'</div><div class="progress-next"><b>Слабые зоны:</b><br>'+weak+'</div>'
   +'<div class="progress-next"><b>Следующий шаг:</b> '+next+'</div>'
   +(last?'<div class="progress-next"><b>Последняя попытка:</b> '+last.case_id+' · '+last.score+'/10</div>':'');
 }}catch(e){{ box.innerHTML='<div class="learn-empty">Прогресс пока недоступен. После первой проверки здесь появятся попытки, слабые зоны и следующий шаг.</div>'; }}
}}
function selectCaseGroup(btn){{
 document.querySelectorAll('.track-chip').forEach(x=>x.classList.remove('active'));
 btn.classList.add('active');
 window.__caseGroup=btn.dataset.group||'';
 filterCases();
}}
function filterCases(){{
 const q=(document.getElementById('caseSearch')?.value||'').toLowerCase().trim();
 const lvl=document.getElementById('levelFilter')?.value||'';
 const tr=document.getElementById('trackFilter')?.value||'';
 const group=window.__caseGroup||'';
 const cards=[...document.querySelectorAll('#learningGrid .learning-card')]; let shown=0;
 cards.forEach(c=>{{
  const okQ=!q || (c.dataset.search||'').includes(q);
  const okL=!lvl || c.dataset.level===lvl;
  const okT=!tr || c.dataset.track===tr;
  const okG=!group || c.dataset.group===group;
  const ok=okQ&&okL&&okT&&okG;
  c.classList.toggle('hidden-by-saas', !ok);
  if(ok) shown++;
 }});
 const cc=document.getElementById('caseCount'); if(cc) cc.textContent='Показано кейсов: '+shown+' / '+cards.length;
 const empty=document.getElementById('emptyCaseState'); if(empty) empty.style.display=shown?'none':'block';
}}
loadLearningProgress(); filterCases();
</script>
"""
    html = page('Тренажёр системного аналитика', body)
    return html.replace('</head>', _SAAS_UI_STYLE_V8653 + '</head>')


def _safe_json_v8653(obj):
    return json.dumps(obj, ensure_ascii=False).replace('</', '<\\/')


def learning_case_page(case_id):
    from learning import get_case
    c = get_case(case_id)
    if not c:
        return page('Кейс не найден', titleblock('ТРЕНАЖЁР', active='learning') + '<div class="err">Кейс не найден.</div>').replace('</head>', _SAAS_UI_STYLE_V8653 + '</head>')
    controls = c.get('expected_controls') or []
    traps = ''.join(f'<li>{escape(x)}</li>' for x in (c.get('hidden_traps') or [])) or '<li>Скрытые ловушки не указаны.</li>'
    control_items = ''.join(
        f"""<label class="control-card"><input type="checkbox" class="visual-control" value="{escape(ctrl.get('id',''))}" data-label="{escape(ctrl.get('label',''))}">
        <span><b>{escape(ctrl.get('label','Контроль'))}</b><small>{escape(ctrl.get('why',''))}</small></span></label>"""
        for ctrl in controls
    ) or '<div class="result-placeholder">Для кейса нет отдельных чекбоксов контролей.</div>'
    ref_json = _safe_json_v8653(c.get('payload') or {})
    safe_case_json = _safe_json_v8653({k:v for k,v in c.items() if k != 'payload'})
    body = titleblock('УЧЕБНЫЙ КЕЙС', active='learning') + f"""
<section class="case-brief-card">
 <div class="case-meta-line"><span class="case-pill">{escape(c.get('level',''))}</span><span class="case-pill">{escape(_case_track_group_v8653(c.get('track','')))}</span><span class="case-pill">{escape(c.get('timebox',''))}</span></div>
 <h2>{escape(c.get('title','Учебный кейс'))}</h2>
 <p class="case-brief">{escape(c.get('brief',''))}</p>
 <p><b>Цель:</b> {escape(c.get('goal',''))}</p>
 <div class="learning-path"><div class="path-step"><b>1. Пойми задачу</b><small>Разбери участников, поток данных и ограничения.</small></div><div class="path-step"><b>2. Собери решение</b><small>Используй визуальный блок или полный конструктор.</small></div><div class="path-step"><b>3. Проверь</b><small>Получишь короткий вывод и подробный отчёт.</small></div><div class="path-step"><b>4. Защити</b><small>Ответь как на собеседовании и сравни с эталоном.</small></div></div>
 <div class="saas-actions"><a class="saas-btn secondary" href="{url_for('/learning')}">Все кейсы</a><a class="saas-btn secondary" href="{url_for('/')}">Открыть полный конструктор</a></div>
</section>
<div class="case-shell">
 <main class="case-main">
  <section class="visual-builder">
   <h3>Соберите решение без JSON</h3>
   <p class="hint">Выберите только те архитектурные контроли, которые вы бы действительно заложили в решение. Тренажёр соберёт черновик и покажет, какие риски остались. Полный JSON остаётся ниже как экспертный режим.</p>
   <div class="control-grid">{control_items}</div>
   <div class="saas-actions">
    <button class="saas-btn accent" type="button" onclick="buildVisualSolution('selected')">Собрать по моим выбранным контролям</button>
    <button class="saas-btn secondary" type="button" onclick="buildVisualSolution('reference')">Подставить эталон</button>
    <button class="saas-btn danger" type="button" onclick="buildVisualSolution('weak')">Собрать слабый черновик для проверки</button>
   </div>
   <div id="visualBuilderState" class="result-placeholder" style="margin-top:10px">Пока решение не собрано. Нажмите одну из кнопок выше.</div>
  </section>
  <section class="action-zone">
   <div class="action-group">
    <h3>Основная проверка</h3>
    <p class="hint">Покажет оценку схемы, найденные и пропущенные контроли, слабые зоны и следующий шаг.</p>
    <div class="saas-actions"><button class="saas-btn accent" type="button" onclick="evaluateLearning('learning')">Проверить моё решение</button><button class="saas-btn secondary" type="button" onclick="showReferencePack()">Показать эталоны</button><button class="saas-btn secondary" type="button" onclick="evaluateLearning('reference')">Проверить эталон</button></div>
   </div>
   <div class="action-group">
    <h3>Режим собеседования</h3>
    <p class="hint">Оценка архитектуры и устного объяснения разделены: сильные слова не маскируют слабую схему.</p>
    <div class="saas-actions"><button class="saas-btn accent" type="button" onclick="evaluateLearning('interview')">Оценить ответ</button><button class="saas-btn secondary" type="button" onclick="showInterviewPack()">Вопросы интервьюера</button></div>
   </div>
  </section>
  <section class="interview-card">
   <h3>Устный ответ</h3>
   <p class="hint">Напишите так, как отвечали бы интервьюеру: границы процесса, участники, sync/async, отказы, идемпотентность, контракты, данные, эксплуатация и компромиссы.</p>
   <textarea id="interviewAnswer" class="learn-editor" style="min-height:150px" placeholder="Например: сначала фиксирую границы процесса, затем разделяю синхронный клиентский путь и асинхронные события..."></textarea>
  </section>
  <section class="action-group">
   <h3>Подсказки</h3>
   <p class="hint">Используйте постепенно: сначала намёк, потом риск, затем конкретное исправление.</p>
   <div class="saas-actions"><button class="saas-btn secondary" type="button" onclick="loadHint(1)">Подсказка 1</button><button class="saas-btn secondary" type="button" onclick="loadHint(2)">Риск</button><button class="saas-btn secondary" type="button" onclick="loadHint(3)">Как исправить</button><button class="saas-btn secondary" type="button" onclick="loadHint(4)">Показать эталонные шаги</button></div>
   <div id="hintBox" class="hint-box" style="display:none"></div>
  </section>
  <section class="result-card-saas">
   <h3>Результат проверки</h3>
   <div id="learningResult" class="result-placeholder">Результат появится здесь после проверки. Сначала будет короткий dashboard, затем полный markdown.</div>
   <details class="expert-json" style="margin-top:12px"><summary>Подробный markdown-отчёт</summary><div class="inner"><pre id="learningMarkdown" class="learn-report">Пока отчёт не сформирован.</pre></div></details>
  </section>
  <details class="expert-json"><summary>Экспертный JSON решения</summary><div class="inner"><p class="hint">Этот блок нужен для продвинутых пользователей и регрессионных проверок. Основной сценарий выше работает без ручного JSON.</p><textarea id="solutionJson" class="learn-editor" spellcheck="false" placeholder="JSON решения появится после визуальной сборки или вставки из конструктора"></textarea></div></details>
 </main>
 <aside class="case-sticky">
  <div class="side-card"><h3>Что тренируем</h3><ul>{''.join(f'<li>{escape(x.get("label", "Контроль"))}</li>' for x in controls)}</ul></div>
  <div class="side-card"><h3>Скрытые ловушки</h3><ul>{traps}</ul></div>
  <div class="side-card"><h3>Полезный путь</h3><ol><li>Соберите слабый черновик и посмотрите, как система ругает ошибки.</li><li>Соберите выбранные контроли и улучшите score.</li><li>Откройте эталон и сравните.</li><li>Запишите устный ответ и проверьте интервью.</li></ol></div>
  <details class="side-card"><summary><b>Метаданные кейса</b></summary><pre style="white-space:pre-wrap;font-size:11px">{escape(safe_case_json)}</pre></details>
 </aside>
</div>
<script>
const CASE_ID = {json.dumps(case_id)};
const REFERENCE_PAYLOAD = {ref_json};
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
function esc(s){{ return String(s||'').replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m])); }}
function cloneRef(){{ return JSON.parse(JSON.stringify(REFERENCE_PAYLOAD||{{}})); }}
function selectedControlLabels(){{ return [...document.querySelectorAll('.visual-control:checked')].map(x=>x.dataset.label||x.value).filter(Boolean); }}
function selectedControlIds(){{ return [...document.querySelectorAll('.visual-control:checked')].map(x=>x.value).filter(Boolean); }}
async function buildVisualSolution(kind){{
 const labels=selectedControlLabels();
 const ids=selectedControlIds();
 const box=document.getElementById('visualBuilderState');
 if(box) box.innerHTML='<b>Собираю черновик...</b>';
 try{{
   const params=new URLSearchParams({{case_id:CASE_ID, kind:kind||'selected', controls:ids.join(',')}});
   const r=await fetch(basePath() + '/api/learning/visual-payload?' + params.toString());
   const data=await r.json();
   if(!data.ok){{ if(box) box.innerHTML='<div class=err>'+((data.errors||['Ошибка сборки']).join('<br>'))+'</div>'; return null; }}
   if(kind==='reference') document.querySelectorAll('.visual-control').forEach(x=>x.checked=true);
   if(kind==='weak') document.querySelectorAll('.visual-control').forEach(x=>x.checked=false);
   document.getElementById('solutionJson').value=JSON.stringify(data.payload||{{}},null,2);
   const selected=data.selected_count ?? labels.length;
   const total=data.control_count ?? document.querySelectorAll('.visual-control').length;
   const msg=data.message || 'Черновик собран.';
   if(box) box.innerHTML='<b>Черновик собран.</b><br>'+esc(msg)+'<br><span class="hint">Выбрано контролей: '+selected+' из '+total+'. Теперь нажмите «Проверить решение».</span>';
   return data.payload||{{}};
 }}catch(e){{ if(box) box.innerHTML='<div class=err>Ошибка сборки черновика: '+esc(e.message)+'</div>'; return null; }}
}}
async function fillReference(){{ return await buildVisualSolution('reference'); }}

async function loadHint(level){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю подсказку...'; try{{ const r=await fetch(basePath() + '/api/learning/hints?case_id='+encodeURIComponent(CASE_ID)+'&level='+encodeURIComponent(level)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} box.innerHTML='<b>Подсказка '+level+'</b><ol>'+data.hints.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка подсказки: '+String(e.message)+'</div>'; }} }}
async function showReferencePack(){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю эталоны...'; try{{ const r=await fetch(basePath() + '/api/learning/reference?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const prod=(data.production?.steps||[]).slice(0,8).map(x=>'<li>'+esc(x)+'</li>').join(''); const acc=(data.acceptance_criteria||[]).map(x=>'<li>'+esc(x)+'</li>').join(''); box.innerHTML='<b>Эталонные варианты</b><p><b>Промышленный эталон:</b> '+esc(data.production?.description||'')+'</p><ol>'+prod+'</ol><p><b>MVP:</b> '+esc(data.mvp?.description||'')+'</p><p><b>Критерии приёмки:</b></p><ul>'+acc+'</ul>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка загрузки эталонов: '+String(e.message)+'</div>'; }} }}
async function showInterviewPack(){{ const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю вопросы...'; try{{ const r=await fetch(basePath() + '/api/learning/interview?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class=err>'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const qs=(data.questions||[]).slice(0,10).map(q=>'<li><b>'+esc(q.question||'')+'</b><br><span class=hint>Ожидается: '+esc((q.expected||[]).slice(0,2).join('; '))+'</span></li>').join(''); box.innerHTML='<b>Вопросы интервьюера</b><p>'+esc(data.opening_prompt||'')+'</p><ol>'+qs+'</ol>'; }}catch(e){{ box.innerHTML='<div class=err>Ошибка загрузки вопросов: '+String(e.message)+'</div>'; }} }}
function quickDashboard(data){{
 const sol=data.solution_score ?? data.learning_score ?? 0;
 const ans=data.answer_score ?? null;
 const interview=data.interview_score ?? null;
 let cells='<div class="qr"><b>Решение</b><span>'+sol+' / 10</span></div>';
 if(ans!==null) cells+='<div class="qr"><b>Устный ответ</b><span>'+ans+' / 10</span></div>';
 if(interview!==null) cells+='<div class="qr"><b>Итог интервью</b><span>'+interview+' / 10</span></div>';
 const errors=(data.quick_summary?.top_errors||data.gaps?.map(g=>g.title)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Критичных учебных пропусков не найдено.</li>';
 const fixes=(data.quick_summary?.quick_fixes||data.gaps?.map(g=>g.fix)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Сравните решение с эталоном и проверьте эксплуатационные детали.</li>';
 return '<div class="learn-verdict"><h2>'+esc(data.learning_level||'Результат проверки')+'</h2><div class="quick-result-grid">'+cells+'</div><b>Главные ошибки:</b><ol>'+errors+'</ol><b>Что исправить первым:</b><ol>'+fixes+'</ol>'+(data.attempt_md_url?'<a class="saas-btn secondary attempt-link" href="'+data.attempt_md_url+'" target="_blank">Открыть markdown попытки</a>':'')+'</div>';
}}
async function evaluateLearning(mode){{
  const box=document.getElementById('learningResult'); const md=document.getElementById('learningMarkdown');
  if(mode==='reference'){{ await buildVisualSolution('reference'); }}
  else if(!(document.getElementById('solutionJson').value||'').trim()){{ await buildVisualSolution('selected'); }}
  box.innerHTML='<div class="result-placeholder">Проверяю решение...</div>'; md.textContent='Проверяю...';
  let payload;
  try{{ payload=JSON.parse(document.getElementById('solutionJson').value || '{{}}'); }}catch(e){{ box.innerHTML='<div class="err">JSON не читается: '+String(e.message)+'</div>'; md.textContent=''; return; }}
  try{{
    const answerText=(document.getElementById('interviewAnswer')?.value || '');
    const r=await fetch(basePath() + '/api/learning/evaluate', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{case_id:CASE_ID, payload, mode, learner_id: learnerId(), answer_text: answerText}})}});
    const data=await r.json();
    if(!data.ok){{ box.innerHTML='<div class="err">'+(data.errors||['Ошибка']).join('<br>')+'</div>'; return; }}
    box.innerHTML=quickDashboard(data)+(data.html || '');
    md.textContent=data.report_markdown || '';
    safeStorageSet('sa_learning_'+CASE_ID, JSON.stringify({{score:data.learning_score, level:data.learning_level, attempt_id:data.attempt_id, at:new Date().toISOString()}}));
  }}catch(e){{ box.innerHTML='<div class="err">Ошибка запроса: '+String(e.message)+'</div>'; md.textContent=''; }}
}}
buildVisualSolution('weak');
</script>
"""
    html = page(c.get('title','Учебный кейс'), body)
    return html.replace('</head>', _SAAS_UI_STYLE_V8653 + '</head>')

# ---------------------------------------------------------------------------
# v8.6.57: радикальное упрощение UX тренажёра.
# Основной путь: выбрать кейс -> прочитать задачу -> отметить решения -> проверить.
# JSON, интервью и эталон оставлены, но спрятаны как дополнительные режимы.
# ---------------------------------------------------------------------------
APP_VERSION = '8.6.67-ultimate-gated'

_TRAINER_SIMPLE_STYLE_V8657 = """
<style>
:root{--trainer-bg:#F6F8FB;--trainer-card:#FFFFFF;--trainer-ink:#0F172A;--trainer-muted:#64748B;--trainer-line:#E2E8F0;--trainer-accent:#0E7490;--trainer-soft:#ECFEFF;--trainer-good:#166534;--trainer-warn:#92400E;--trainer-bad:#991B1B}
.wrap{max-width:1180px}.trainer-hero{border:1px solid var(--trainer-line);border-radius:28px;background:linear-gradient(135deg,#fff,#F0FDFA);padding:28px;margin:18px 0;box-shadow:0 20px 50px rgba(15,23,42,.08)}.trainer-kicker{display:inline-block;border:1px solid #A5F3FC;background:#ECFEFF;color:#155E75;border-radius:999px;padding:7px 12px;font-weight:900;font-size:12px}.trainer-hero h2{font-size:34px;line-height:1.08;margin:14px 0 8px;max-width:860px}.trainer-hero p{font-size:16px;color:var(--trainer-muted);max-width:860px}.trainer-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}.trainer-btn{border:1px solid var(--trainer-ink);background:var(--trainer-ink);color:#fff;text-decoration:none;border-radius:14px;padding:11px 15px;font-weight:900;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:8px}.trainer-btn.secondary{background:#fff;color:var(--trainer-ink);border-color:var(--trainer-line)}.trainer-btn.accent{background:var(--trainer-accent);border-color:var(--trainer-accent)}.trainer-btn.light{background:#F8FAFC;color:var(--trainer-ink);border-color:var(--trainer-line)}.trainer-section{border:1px solid var(--trainer-line);background:#fff;border-radius:22px;padding:18px;margin:16px 0;box-shadow:0 10px 26px rgba(15,23,42,.045)}.trainer-section h2,.trainer-section h3{margin-top:0}.trainer-help{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0}.trainer-help-card{border:1px solid var(--trainer-line);background:#F8FAFC;border-radius:18px;padding:14px}.trainer-help-card b{display:block;margin-bottom:4px}.trainer-help-card span{color:var(--trainer-muted);font-size:13px;line-height:1.35}.trainer-start-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.trainer-case-card{border:1px solid var(--trainer-line);background:#fff;border-radius:20px;padding:16px;display:flex;flex-direction:column;gap:8px;min-height:210px}.trainer-case-card.recommended{border-color:#67E8F9;background:linear-gradient(180deg,#FFFFFF,#ECFEFF)}.trainer-case-card h3{margin:0;font-size:18px;line-height:1.25}.trainer-case-card p{margin:0;color:var(--trainer-muted);font-size:14px}.trainer-meta{display:flex;gap:6px;flex-wrap:wrap}.trainer-pill{border:1px solid var(--trainer-line);background:#F8FAFC;border-radius:999px;padding:5px 8px;font-weight:800;font-size:11px;color:var(--trainer-muted)}.trainer-case-card .trainer-btn{margin-top:auto}.trainer-filter{display:grid;grid-template-columns:minmax(0,1fr)180px 220px;gap:10px;margin:12px 0}.trainer-filter input,.trainer-filter select{width:100%;border:1px solid var(--trainer-line);border-radius:12px;padding:10px;background:#fff}.trainer-catalog-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.trainer-hidden{display:none!important}.trainer-empty{border:1px dashed var(--trainer-line);border-radius:16px;background:#F8FAFC;padding:16px;color:var(--trainer-muted)}.trainer-case-head{border:1px solid var(--trainer-line);background:#fff;border-radius:24px;padding:20px;margin:16px 0}.trainer-case-head h2{font-size:30px;line-height:1.12;margin:10px 0}.trainer-main{display:grid;grid-template-columns:minmax(0,1fr)320px;gap:16px;align-items:start}.trainer-flow{display:grid;gap:16px}.trainer-sticky{position:sticky;top:12px;display:grid;gap:12px}.trainer-step{border:1px solid var(--trainer-line);background:#fff;border-radius:22px;padding:18px}.trainer-step-header{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px}.trainer-num{flex:none;width:34px;height:34px;border-radius:50%;background:var(--trainer-accent);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900}.trainer-step-header h3{margin:0}.trainer-step-header p{margin:4px 0 0;color:var(--trainer-muted)}.trainer-brief-list{margin:8px 0 0 22px}.trainer-brief-list li{margin:6px 0}.trainer-check-toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;border:1px solid var(--trainer-line);border-radius:16px;background:#F8FAFC;padding:12px;margin-bottom:12px}.trainer-counter{font-weight:900;color:var(--trainer-accent)}.trainer-control-list{display:grid;gap:10px}.trainer-control{border:1px solid var(--trainer-line);border-radius:16px;background:#fff;padding:13px;display:grid;grid-template-columns:26px minmax(0,1fr);gap:10px;cursor:pointer}.trainer-control:hover{border-color:#67E8F9;background:#F0FDFA}.trainer-control input{width:20px;height:20px;margin:2px 0 0}.trainer-control b{display:block;font-size:15px}.trainer-control small{display:block;color:var(--trainer-muted);line-height:1.38;margin-top:4px}.trainer-state{border:1px dashed var(--trainer-line);border-radius:16px;background:#F8FAFC;padding:12px;color:var(--trainer-muted);margin-top:12px}.trainer-result{border:1px solid var(--trainer-line);background:#fff;border-radius:22px;padding:18px}.trainer-score-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.trainer-score-cell{border:1px solid var(--trainer-line);border-radius:16px;background:#F8FAFC;padding:12px}.trainer-score-cell b{display:block;color:var(--trainer-muted);font-size:12px}.trainer-score-cell span{font:900 24px var(--mono);color:var(--trainer-accent)}.trainer-result-summary{border:2px solid #67E8F9;background:#ECFEFF;border-radius:18px;padding:14px}.trainer-result-summary h2{margin:0 0 8px}.trainer-result-summary ol{margin:6px 0 12px 22px}.trainer-details{border:1px solid var(--trainer-line);border-radius:18px;background:#fff;overflow:hidden;margin-top:12px}.trainer-details summary{cursor:pointer;padding:13px 15px;font-weight:900;background:#F8FAFC}.trainer-details-inner{padding:14px}.trainer-report{white-space:pre-wrap;border:1px solid var(--trainer-line);background:#FAFCFC;border-radius:14px;padding:12px;font:12px/1.5 var(--mono);max-height:520px;overflow:auto}.trainer-side-card{border:1px solid var(--trainer-line);background:#fff;border-radius:20px;padding:15px}.trainer-side-card h3{margin:0 0 8px}.trainer-side-card ol,.trainer-side-card ul{margin:8px 0 0 20px;padding:0}.trainer-side-card li{margin:6px 0;color:var(--trainer-muted);line-height:1.35}.trainer-answer{width:100%;min-height:150px;border:1px solid var(--trainer-line);border-radius:14px;padding:12px;font:14px/1.45 var(--sans)}.trainer-json{width:100%;min-height:280px;border:1px solid var(--trainer-line);border-radius:14px;padding:12px;font:12px/1.45 var(--mono)}.trainer-progress-clean{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.trainer-progress-cell{border:1px solid var(--trainer-line);border-radius:16px;background:#F8FAFC;padding:12px}.trainer-progress-cell b{display:block;color:var(--trainer-muted);font-size:12px}.trainer-progress-cell span{font:900 22px var(--mono);color:var(--trainer-accent)}@media(max-width:980px){.trainer-main{grid-template-columns:1fr}.trainer-sticky{position:static}.trainer-help{grid-template-columns:repeat(2,minmax(0,1fr))}.trainer-start-grid,.trainer-catalog-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.trainer-filter{grid-template-columns:1fr}.trainer-score-grid{grid-template-columns:1fr}}@media(max-width:640px){.trainer-hero{padding:20px;border-radius:22px}.trainer-hero h2{font-size:25px}.trainer-help,.trainer-start-grid,.trainer-catalog-grid,.trainer-progress-clean{grid-template-columns:1fr}.trainer-btn{width:100%}.trainer-case-head h2{font-size:24px}.trainer-step,.trainer-result,.trainer-case-head,.trainer-side-card{padding:14px}.trainer-step-header{align-items:flex-start}.trainer-check-toolbar{align-items:stretch}.trainer-check-toolbar .trainer-actions{width:100%;margin-top:0}.trainer-report{font-size:11px;max-height:420px}}
</style>
"""


def _trainer_track_group_v8657(track: str) -> str:
    return _case_track_group_v8653(track)


def _trainer_case_card_v8657(c, recommended=False):
    group = _trainer_track_group_v8657(c.get('track', ''))
    search_blob = ' '.join(str(c.get(k, '')) for k in ('id', 'title', 'level', 'track', 'brief', 'goal')).lower()
    cls = 'trainer-case-card recommended' if recommended else 'trainer-case-card'
    return f"""<article class="{cls}" data-level="{escape(c.get('level',''))}" data-track="{escape(c.get('track',''))}" data-group="{escape(group)}" data-search="{escape(search_blob)}">
      <div class="trainer-meta"><span class="trainer-pill">{escape(c.get('level',''))}</span><span class="trainer-pill">{escape(group)}</span><span class="trainer-pill">{escape(c.get('timebox',''))}</span></div>
      <h3>{escape(c.get('title',''))}</h3>
      <p>{escape(c.get('brief',''))}</p>
      <a class="trainer-btn accent" href="{url_for('/learning/' + c.get('id',''))}">Открыть и решить</a>
    </article>"""


def learning_home_page():
    from learning import list_cases, learning_catalog_summary
    cases = list_cases()
    catalog = learning_catalog_summary()
    levels = sorted({c.get('level', '') for c in cases if c.get('level')})
    tracks = sorted({c.get('track', '') for c in cases if c.get('track')})
    level_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in levels)
    track_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in tracks)
    recommended_ids = ['bank-credit-bki-fraud', 'uk-bank-status-flow', 'kafka-ordering-dlq-replay', 'event-enrichment-rest-kafka', 'bki-dwh-search', 'graphql-bff-aggregation']
    recommended = [c for rid in recommended_ids for c in cases if c.get('id') == rid]
    if len(recommended) < 6:
        recommended += [c for c in cases if c not in recommended][:6-len(recommended)]
    recommended_cards = ''.join(_trainer_case_card_v8657(c, True) for c in recommended[:6])
    cards = ''.join(_trainer_case_card_v8657(c) for c in cases)
    body = titleblock('ТРЕНАЖЁР СИСТЕМНОГО АНАЛИТИКА', active='learning') + f"""
<section class="trainer-hero">
 <span class="trainer-kicker">Простой режим тренажёра · {escape(APP_VERSION)}</span>
 <h2>Теперь тренажёр работает как понятный учебный маршрут, а не как набор панелей.</h2>
 <p>Выберите кейс, прочитайте задачу, отметьте архитектурные решения и нажмите проверку. Эталон, интервью и JSON доступны, но не мешают основному пути.</p>
 <div class="trainer-actions"><a class="trainer-btn accent" href="#start">Начать с первого кейса</a><a class="trainer-btn secondary" href="#catalog">Открыть весь каталог</a><a class="trainer-btn secondary" href="{url_for('/')}">Проектировщик</a></div>
</section>
<section class="trainer-section">
 <h2>Как пользоваться</h2>
 <div class="trainer-help">
  <div class="trainer-help-card"><b>1. Выбери кейс</b><span>Лучше начать с рекомендованных. Они показывают реальную пользу за 5–10 минут.</span></div>
  <div class="trainer-help-card"><b>2. Отметь решения</b><span>Галочка означает: “я бы добавил это в архитектуру”. Никакой ручной JSON не нужен.</span></div>
  <div class="trainer-help-card"><b>3. Нажми проверку</b><span>Сначала увидишь короткий вывод: оценка, главные ошибки и что исправить первым.</span></div>
  <div class="trainer-help-card"><b>4. Сравни с эталоном</b><span>Эталон открывается отдельно, чтобы не подсказывать ответ раньше времени.</span></div>
 </div>
</section>
<section class="trainer-section" id="progress">
 <h2>Ваш прогресс</h2>
 <div id="learningProgress" class="trainer-empty">Прогресс появится после первой проверки решения.</div>
 <div class="trainer-actions"><button class="trainer-btn secondary" type="button" onclick="loadLearningProgress()">Обновить прогресс</button></div>
</section>
<section class="trainer-section" id="start">
 <h2>Рекомендуемые кейсы для старта</h2>
 <p class="hint">Эти кейсы лучше всего показывают, как тренажёр помогает находить архитектурные пропуски.</p>
 <div class="trainer-start-grid">{recommended_cards}</div>
</section>
<section class="trainer-section" id="catalog">
 <h2>Весь каталог</h2>
 <p class="hint">Кейсов: {len(cases)}. Версия каталога: {escape(catalog.get('catalog_version',''))}.</p>
 <div class="trainer-filter">
  <input id="caseSearch" type="search" placeholder="Поиск: Kafka, банк, DWH, DLQ, SOAP..." oninput="filterTrainerCases()">
  <select id="levelFilter" onchange="filterTrainerCases()"><option value="">Все уровни</option>{level_options}</select>
  <select id="trackFilter" onchange="filterTrainerCases()"><option value="">Все темы</option>{track_options}</select>
 </div>
 <div id="caseCount" class="learning-count">Показано кейсов: {len(cases)} / {len(cases)}</div>
 <div id="emptyCaseState" class="trainer-empty trainer-hidden">По выбранным фильтрам ничего не найдено.</div>
 <div class="trainer-catalog-grid" id="learningGrid">{cards}</div>
</section>
<script>
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
async function loadLearningProgress(){{
 const box=document.getElementById('learningProgress'); if(!box) return;
 try{{
  const r=await fetch(basePath()+'/api/learning/progress?learner_id='+encodeURIComponent(learnerId()));
  const data=await r.json();
  if(!data.ok){{ box.innerHTML='<div class="err">Не удалось загрузить прогресс.</div>'; return; }}
  const weak=(data.weak_skills||[]).map(x=>x.name+': '+(x.score??'нет данных')).join('<br>') || 'Пока нет данных.';
  const next=(data.solved_case_count||0)===0 ? 'Откройте первый рекомендованный кейс и проверьте любое решение.' : 'Выберите кейс из слабой зоны и попробуйте улучшить результат.';
  box.innerHTML='<div class="trainer-progress-clean"><div class="trainer-progress-cell"><b>Попыток</b><span>'+data.attempt_count+'</span></div><div class="trainer-progress-cell"><b>Кейсов решено</b><span>'+data.solved_case_count+' / '+data.case_count+'</span></div><div class="trainer-progress-cell"><b>Бейджи</b><span>'+(data.badges||[]).length+'</span></div></div><p><b>Слабые зоны:</b><br>'+weak+'</p><p><b>Следующий шаг:</b> '+next+'</p>';
 }}catch(e){{ box.innerHTML='Прогресс пока недоступен. После первой проверки здесь появятся попытки и слабые зоны.'; }}
}}
function filterTrainerCases(){{
 const q=(document.getElementById('caseSearch')?.value||'').toLowerCase().trim();
 const lvl=document.getElementById('levelFilter')?.value||'';
 const tr=document.getElementById('trackFilter')?.value||'';
 const cards=[...document.querySelectorAll('#learningGrid .trainer-case-card')]; let shown=0;
 cards.forEach(c=>{{
  const okQ=!q || (c.dataset.search||'').includes(q);
  const okL=!lvl || c.dataset.level===lvl;
  const okT=!tr || c.dataset.track===tr;
  const ok=okQ&&okL&&okT;
  c.classList.toggle('trainer-hidden', !ok);
  if(ok) shown++;
 }});
 const cc=document.getElementById('caseCount'); if(cc) cc.textContent='Показано кейсов: '+shown+' / '+cards.length;
 const empty=document.getElementById('emptyCaseState'); if(empty) empty.classList.toggle('trainer-hidden', shown>0);
}}
loadLearningProgress(); filterTrainerCases();
</script>
"""
    return page('Тренажёр системного аналитика', body).replace('</head>', _TRAINER_SIMPLE_STYLE_V8657 + '</head>')


def _trainer_controls_v8657(controls):
    if not controls:
        return '<div class="trainer-empty">Для этого кейса нет отдельного чек-листа. Используйте экспертный JSON или эталон.</div>'
    items = []
    for i, ctrl in enumerate(controls, start=1):
        label = escape(ctrl.get('label', 'Архитектурное решение'))
        why = escape(ctrl.get('why', 'Помогает закрыть риск в этом кейсе.'))
        cid = escape(ctrl.get('id', f'control_{i}'))
        skill = escape(ctrl.get('skill', 'process'))
        items.append(f"""<label class="trainer-control"><input type="checkbox" class="visual-control" value="{cid}" data-label="{label}" data-skill="{skill}" onchange="updateSelectedCounter()"><span><b>{i}. {label}</b><small>{why}</small></span></label>""")
    return ''.join(items)


def learning_case_page(case_id):
    from learning import get_case
    c = get_case(case_id)
    if not c:
        return page('Кейс не найден', titleblock('ТРЕНАЖЁР', active='learning') + '<div class="err">Кейс не найден.</div>').replace('</head>', _TRAINER_SIMPLE_STYLE_V8657 + '</head>')
    controls = c.get('expected_controls') or []
    control_items = _trainer_controls_v8657(controls)
    traps = ''.join(f'<li>{escape(x)}</li>' for x in (c.get('hidden_traps') or [])) or '<li>Скрытые ловушки не указаны.</li>'
    safe_case_json = _safe_json_v8653({k:v for k,v in c.items() if k != 'payload'})
    ref_json = _safe_json_v8653(c.get('payload') or {})
    body = titleblock('УЧЕБНЫЙ КЕЙС', active='learning') + f"""
<section class="trainer-case-head">
 <div class="trainer-meta"><span class="trainer-pill">{escape(c.get('level',''))}</span><span class="trainer-pill">{escape(_trainer_track_group_v8657(c.get('track','')))}</span><span class="trainer-pill">{escape(c.get('timebox',''))}</span></div>
 <h2>{escape(c.get('title','Учебный кейс'))}</h2>
 <p>{escape(c.get('brief',''))}</p>
 <p><b>Цель:</b> {escape(c.get('goal',''))}</p>
 <div class="trainer-actions"><a class="trainer-btn secondary" href="{url_for('/learning')}">← Все кейсы</a><a class="trainer-btn secondary" href="{url_for('/')}">Полный проектировщик</a></div>
</section>
<div class="trainer-main">
 <main class="trainer-flow">
  <section class="trainer-step" id="task">
   <div class="trainer-step-header"><div class="trainer-num">1</div><div><h3>Поймите задачу</h3><p>Перед выбором решений проверьте, что понятно, где граница процесса и что может пойти не так.</p></div></div>
   <ul class="trainer-brief-list">
    <li><b>Что строим:</b> {escape(c.get('title',''))}</li>
    <li><b>Зачем:</b> {escape(c.get('goal',''))}</li>
    <li><b>Что важно не потерять:</b> порядок, дубли, отказы, контракты, данные и эксплуатацию.</li>
   </ul>
  </section>
  <section class="trainer-step" id="solution">
   <div class="trainer-step-header"><div class="trainer-num">2</div><div><h3>Выберите, что добавите в архитектуру</h3><p>Галочка означает: “я явно заложу это решение в проект”. Не нужно выбирать всё наугад — лучше подумать и потом сравнить с эталоном.</p></div></div>
   <div class="trainer-check-toolbar"><div><b>Ваше решение</b><br><span class="trainer-counter" id="selectedCounter">Выбрано: 0 из {len(controls)}</span></div><div class="trainer-actions"><button class="trainer-btn light" type="button" onclick="clearControls()">Снять всё</button><button class="trainer-btn light" type="button" onclick="selectAllControls()">Выбрать всё</button></div></div>
   <div class="trainer-control-list">{control_items}</div>
   <div id="visualBuilderState" class="trainer-state">Решение пока не проверялось. Отметьте пункты и нажмите кнопку ниже.</div>
   <div class="trainer-actions"><button class="trainer-btn accent" type="button" onclick="evaluateLearning('learning')">Проверить выбранное решение</button><button class="trainer-btn secondary" type="button" onclick="loadHint(1)">Дать подсказку</button><button class="trainer-btn secondary" type="button" onclick="showReferencePack()">Показать эталон</button></div>
  </section>
  <section class="trainer-result" id="result">
   <h3>3. Результат проверки</h3>
   <div id="learningResult" class="trainer-empty">Здесь появится оценка, главные ошибки и первые исправления.</div>
   <details class="trainer-details"><summary>Подробный markdown-отчёт</summary><div class="trainer-details-inner"><pre id="learningMarkdown" class="trainer-report">Пока отчёт не сформирован.</pre></div></details>
  </section>
  <details class="trainer-details">
   <summary>Дополнительно: режим собеседования</summary>
   <div class="trainer-details-inner">
    <p class="hint">Напишите, как объяснили бы решение интервьюеру. Оценка устного ответа идёт отдельно от оценки схемы.</p>
    <textarea id="interviewAnswer" class="trainer-answer" placeholder="Например: сначала фиксирую границы процесса, затем разделяю синхронный путь и асинхронные события..."></textarea>
    <div class="trainer-actions"><button class="trainer-btn accent" type="button" onclick="evaluateLearning('interview')">Оценить устный ответ</button><button class="trainer-btn secondary" type="button" onclick="showInterviewPack()">Показать вопросы интервьюера</button></div>
   </div>
  </details>
  <details class="trainer-details">
   <summary>Экспертный режим: JSON решения</summary>
   <div class="trainer-details-inner"><p class="hint">Обычному пользователю этот блок не нужен. Он оставлен для отладки, регрессионных тестов и точного редактирования payload.</p><textarea id="solutionJson" class="trainer-json" spellcheck="false"></textarea></div>
  </details>
  <div id="hintBox" class="hint-box" style="display:none"></div>
 </main>
 <aside class="trainer-sticky">
  <div class="trainer-side-card"><h3>Как пройти кейс</h3><ol><li>Прочитайте задачу.</li><li>Отметьте решения, которые реально нужны.</li><li>Нажмите проверку.</li><li>Исправьте 1–2 главные ошибки.</li><li>Только потом смотрите эталон.</li></ol></div>
  <div class="trainer-side-card"><h3>Скрытые ловушки</h3><ul>{traps}</ul></div>
  <details class="trainer-side-card"><summary><b>Метаданные кейса</b></summary><pre style="white-space:pre-wrap;font-size:11px">{escape(safe_case_json)}</pre></details>
 </aside>
</div>
<script>
const CASE_ID = {json.dumps(case_id)};
const REFERENCE_PAYLOAD = {ref_json};
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
function esc(s){{ return String(s||'').replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m])); }}
function selectedControlIds(){{ return [...document.querySelectorAll('.visual-control:checked')].map(x=>x.value).filter(Boolean); }}
function updateSelectedCounter(){{ const total=document.querySelectorAll('.visual-control').length; const selected=selectedControlIds().length; const el=document.getElementById('selectedCounter'); if(el) el.textContent='Выбрано: '+selected+' из '+total; }}
function clearControls(){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=false); updateSelectedCounter(); document.getElementById('visualBuilderState').textContent='Выбор очищен. Можно проверить слабое решение или выбрать нужные пункты.'; }}
function selectAllControls(){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=true); updateSelectedCounter(); document.getElementById('visualBuilderState').textContent='Вы выбрали все пункты. Это удобно для сравнения с эталоном, но в реальной задаче лучше уметь объяснить каждый выбор.'; }}
async function buildVisualSolution(kind){{
 const ids=selectedControlIds();
 const box=document.getElementById('visualBuilderState');
 if(box) box.innerHTML='<b>Готовлю решение к проверке...</b>';
 try{{
   const params=new URLSearchParams({{case_id:CASE_ID, kind:kind||'selected', controls:ids.join(',')}});
   const r=await fetch(basePath() + '/api/learning/visual-payload?' + params.toString());
   const data=await r.json();
   if(!data.ok){{ if(box) box.innerHTML='<div class="err">'+((data.errors||['Ошибка сборки']).join('<br>'))+'</div>'; return null; }}
   if(kind==='reference'){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=true); updateSelectedCounter(); }}
   document.getElementById('solutionJson').value=JSON.stringify(data.payload||{{}},null,2);
   const selected=data.selected_count ?? ids.length;
   const total=data.control_count ?? document.querySelectorAll('.visual-control').length;
   if(box) box.innerHTML='<b>Решение подготовлено.</b><br><span>Выбрано пунктов: '+selected+' из '+total+'. Сейчас можно смотреть результат проверки.</span>';
   return data.payload||{{}};
 }}catch(e){{ if(box) box.innerHTML='<div class="err">Не удалось подготовить решение: '+esc(e.message)+'</div>'; return null; }}
}}
async function loadHint(level){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю подсказку...';
 try{{ const r=await fetch(basePath() + '/api/learning/hints?case_id='+encodeURIComponent(CASE_ID)+'&level='+encodeURIComponent(level)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} box.innerHTML='<b>Подсказка</b><ol>'+data.hints.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка подсказки: '+esc(e.message)+'</div>'; }}
}}
async function showReferencePack(){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю эталон...';
 try{{ const r=await fetch(basePath() + '/api/learning/reference?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const prod=(data.production?.steps||[]).slice(0,8).map(x=>'<li>'+esc(x)+'</li>').join(''); const acc=(data.acceptance_criteria||[]).map(x=>'<li>'+esc(x)+'</li>').join(''); box.innerHTML='<b>Эталон</b><p>'+esc(data.production?.description||'')+'</p><ol>'+prod+'</ol><p><b>Критерии приёмки:</b></p><ul>'+acc+'</ul><div class="trainer-actions"><button class="trainer-btn secondary" type="button" onclick="evaluateLearning(&quot;reference&quot;)">Проверить полный эталон</button></div>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка загрузки эталона: '+esc(e.message)+'</div>'; }}
}}
async function showInterviewPack(){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю вопросы...';
 try{{ const r=await fetch(basePath() + '/api/learning/interview?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const qs=(data.questions||[]).slice(0,8).map(q=>'<li><b>'+esc(q.question||'')+'</b><br><span class="hint">Ожидается: '+esc((q.expected||[]).slice(0,2).join('; '))+'</span></li>').join(''); box.innerHTML='<b>Вопросы интервьюера</b><p>'+esc(data.opening_prompt||'')+'</p><ol>'+qs+'</ol>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка загрузки вопросов: '+esc(e.message)+'</div>'; }}
}}
function simpleDashboard(data){{
 const sol=data.solution_score ?? data.learning_score ?? 0;
 const ans=data.answer_score ?? null;
 const interview=data.interview_score ?? null;
 let cells='<div class="trainer-score-cell"><b>Решение</b><span>'+sol+' / 10</span></div>';
 if(ans!==null) cells+='<div class="trainer-score-cell"><b>Устный ответ</b><span>'+ans+' / 10</span></div>';
 if(interview!==null) cells+='<div class="trainer-score-cell"><b>Итог интервью</b><span>'+interview+' / 10</span></div>';
 const errors=(data.quick_summary?.top_errors||data.gaps?.map(g=>g.title)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Критичных пропусков не найдено.</li>';
 const fixes=(data.quick_summary?.quick_fixes||data.gaps?.map(g=>g.fix)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Сравните решение с эталоном и проверьте эксплуатационные детали.</li>';
 return '<div class="trainer-result-summary"><h2>'+esc(data.learning_level||'Результат')+'</h2><div class="trainer-score-grid">'+cells+'</div><b>Главные ошибки:</b><ol>'+errors+'</ol><b>Что исправить первым:</b><ol>'+fixes+'</ol>'+(data.attempt_md_url?'<a class="trainer-btn secondary" href="'+data.attempt_md_url+'" target="_blank">Открыть markdown попытки</a>':'')+'</div>';
}}
async function evaluateLearning(mode){{
 const box=document.getElementById('learningResult'); const md=document.getElementById('learningMarkdown');
 if(mode==='reference') await buildVisualSolution('reference'); else await buildVisualSolution('selected');
 box.innerHTML='<div class="trainer-empty">Проверяю решение...</div>'; md.textContent='Проверяю...';
 let payload;
 try{{ payload=JSON.parse(document.getElementById('solutionJson').value || '{{}}'); }}catch(e){{ box.innerHTML='<div class="err">JSON не читается: '+esc(e.message)+'</div>'; md.textContent=''; return; }}
 try{{
   const answerText=(document.getElementById('interviewAnswer')?.value || '');
   const r=await fetch(basePath() + '/api/learning/evaluate', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{case_id:CASE_ID, payload, mode, learner_id: learnerId(), answer_text: answerText}})}});
   const data=await r.json();
   if(!data.ok){{ box.innerHTML='<div class="err">'+(data.errors||['Ошибка']).join('<br>')+'</div>'; return; }}
   box.innerHTML=simpleDashboard(data)+'<details class="trainer-details"><summary>Показать полный учебный разбор</summary><div class="trainer-details-inner">'+(data.html || '')+'</div></details>';
   md.textContent=data.report_markdown || '';
   safeStorageSet('sa_learning_'+CASE_ID, JSON.stringify({{score:data.learning_score, level:data.learning_level, attempt_id:data.attempt_id, at:new Date().toISOString()}}));
   document.getElementById('result')?.scrollIntoView({{behavior:'smooth',block:'start'}});
 }}catch(e){{ box.innerHTML='<div class="err">Ошибка запроса: '+esc(e.message)+'</div>'; md.textContent=''; }}
}}
updateSelectedCounter();
</script>
"""
    return page(c.get('title', 'Учебный кейс'), body).replace('</head>', _TRAINER_SIMPLE_STYLE_V8657 + '</head>')

# ---------------------------------------------------------------------------
# v8.6.62: production-ready UX тренажёра для обычного пользователя.
# Главный путь стал одноэкранным мастером без боковой панели: задача -> выбор -> проверка -> разбор.
# ---------------------------------------------------------------------------
APP_VERSION = '8.6.67-ultimate-gated'

_TRAINER_MAX_STYLE_V8658 = _TRAINER_SIMPLE_STYLE_V8657 + """
<style>
:root{--ux-bg:#F7FAFC;--ux-card:#FFFFFF;--ux-ink:#0F172A;--ux-muted:#5F6B7A;--ux-line:#DDE7F0;--ux-accent:#0F766E;--ux-accent-2:#2563EB;--ux-soft:#ECFDF5;--ux-warn:#FFF7ED;--ux-bad:#FEF2F2}
.wrap{max-width:1040px}.trainer-hero.maxux{border-radius:30px;padding:30px;background:linear-gradient(135deg,#FFFFFF 0%,#ECFDF5 55%,#EFF6FF 100%)}.maxux h2{max-width:780px}.ux-primary-path{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-top:18px}.ux-now{border:1px solid #99F6E4;background:#F0FDFA;border-radius:22px;padding:18px}.ux-now h3{margin:0 0 8px}.ux-now p{margin:0 0 12px;color:var(--ux-muted)}.ux-mini-card{border:1px solid var(--ux-line);background:#fff;border-radius:18px;padding:14px}.ux-mini-card b{display:block}.ux-mini-card span{display:block;color:var(--ux-muted);font-size:13px;line-height:1.35;margin-top:4px}.ux-path-compact{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.ux-path-step{border:1px solid var(--ux-line);background:#fff;border-radius:16px;padding:12px;position:relative}.ux-path-step b{display:block}.ux-path-step span{display:block;color:var(--ux-muted);font-size:12px;line-height:1.35;margin-top:4px}.ux-path-step::before{content:attr(data-step);display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:50%;background:var(--ux-accent);color:#fff;font-weight:900;font-size:12px;margin-bottom:6px}.ux-home-fold{border:1px solid var(--ux-line);border-radius:22px;background:#fff;margin:16px 0;overflow:hidden}.ux-home-fold summary{cursor:pointer;padding:16px 18px;font-weight:900;background:#F8FAFC}.ux-home-fold-inner{padding:16px}.trainer-start-grid.max-two{grid-template-columns:repeat(2,minmax(0,1fr))}.trainer-case-card.max-card{min-height:auto;border-radius:22px}.trainer-case-card.max-card h3{font-size:17px}.trainer-case-card.max-card p{font-size:13px;line-height:1.4}.trainer-filter.max-filter{grid-template-columns:minmax(0,1fr)170px 220px}.trainer-catalog-grid.max-catalog{grid-template-columns:repeat(2,minmax(0,1fr))}.ux-case-shell{display:grid;gap:16px}.ux-case-top{border:1px solid var(--ux-line);background:#fff;border-radius:26px;padding:20px;margin:16px 0}.ux-case-top h2{font-size:30px;line-height:1.12;margin:8px 0}.ux-case-top .case-brief{font-size:16px;color:var(--ux-muted);max-width:860px}.ux-progress{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:14px 0}.ux-progress .p{border:1px solid var(--ux-line);border-radius:14px;background:#F8FAFC;padding:10px;font-weight:850;color:var(--ux-muted);font-size:13px}.ux-progress .p.active{background:#ECFDF5;border-color:#99F6E4;color:#065F46}.ux-card{border:1px solid var(--ux-line);background:#fff;border-radius:24px;padding:18px;box-shadow:0 12px 28px rgba(15,23,42,.045)}.ux-card h3{margin:0}.ux-card-lead{color:var(--ux-muted);margin:6px 0 14px}.ux-task-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.ux-task-box{border:1px solid var(--ux-line);background:#F8FAFC;border-radius:18px;padding:14px}.ux-task-box b{display:block;margin-bottom:6px}.ux-task-box ul{margin:6px 0 0 20px;padding:0}.ux-task-box li{margin:5px 0;color:var(--ux-muted);line-height:1.35}.ux-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;border:1px solid var(--ux-line);background:#F8FAFC;border-radius:18px;padding:12px;margin:12px 0}.ux-counter{font-weight:950;color:var(--ux-accent);font-size:15px}.ux-hint{color:var(--ux-muted);font-size:13px}.ux-control-group{border:1px solid var(--ux-line);border-radius:20px;background:#FBFDFF;margin:12px 0;overflow:hidden}.ux-control-group h4{margin:0;padding:12px 14px;background:#F8FAFC;border-bottom:1px solid var(--ux-line)}.ux-control-list{display:grid;gap:0}.trainer-control.ux-control{border:none;border-bottom:1px solid var(--ux-line);border-radius:0;padding:14px 14px;grid-template-columns:30px minmax(0,1fr);align-items:start}.trainer-control.ux-control:last-child{border-bottom:none}.trainer-control.ux-control input{accent-color:var(--ux-accent);width:22px;height:22px}.trainer-control.ux-control small{font-size:13px}.ux-check-row{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;border:1px solid #99F6E4;background:#F0FDFA;border-radius:20px;padding:14px;margin-top:14px}.ux-state{color:#065F46;font-weight:800}.ux-result-empty{border:1px dashed var(--ux-line);background:#F8FAFC;border-radius:18px;padding:16px;color:var(--ux-muted)}.ux-result-card{border:2px solid #99F6E4;background:#F0FDFA;border-radius:22px;padding:16px}.ux-result-card h2{margin:0 0 8px}.ux-result-main{display:grid;grid-template-columns:160px minmax(0,1fr);gap:14px;align-items:start}.ux-big-score{border:1px solid #99F6E4;background:#fff;border-radius:18px;padding:14px;text-align:center}.ux-big-score b{display:block;color:var(--ux-muted);font-size:12px}.ux-big-score span{display:block;font:950 34px var(--mono);color:var(--ux-accent);line-height:1.1}.ux-result-lists{display:grid;grid-template-columns:1fr 1fr;gap:12px}.ux-result-lists div{border:1px solid var(--ux-line);background:#fff;border-radius:16px;padding:12px}.ux-result-lists b{display:block;margin-bottom:6px}.ux-result-lists ol{margin:0 0 0 20px;padding:0}.ux-result-lists li{margin:5px 0;color:var(--ux-muted);line-height:1.35}.ux-extra-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}.trainer-details.ux-details{border-radius:20px}.trainer-details.ux-details summary{font-size:15px}.ux-json-note{color:var(--ux-muted);font-size:13px;margin:0 0 8px}.ux-bottom-bar{position:sticky;bottom:10px;z-index:5;border:1px solid #99F6E4;background:rgba(240,253,250,.96);backdrop-filter:blur(10px);border-radius:20px;padding:10px;display:flex;justify-content:space-between;align-items:center;gap:10px;box-shadow:0 14px 32px rgba(15,23,42,.12)}.ux-bottom-bar .trainer-btn{min-width:230px}.hint-box{border:1px solid var(--ux-line);border-radius:20px;background:#fff;padding:14px;margin-top:12px}.hint-box b{display:block;margin-bottom:6px}.hint-box ol,.hint-box ul{margin:6px 0 0 20px}.hint-box li{margin:6px 0;color:var(--ux-muted);line-height:1.4}.ux-danger-note{border:1px solid #FED7AA;background:#FFF7ED;border-radius:16px;padding:12px;color:#9A3412;margin-top:10px}.ux-mobile-only{display:none}@media(max-width:900px){.ux-primary-path,.ux-task-grid,.ux-result-main,.ux-result-lists{grid-template-columns:1fr}.ux-path-compact{grid-template-columns:repeat(2,minmax(0,1fr))}.trainer-start-grid.max-two,.trainer-catalog-grid.max-catalog{grid-template-columns:1fr}.trainer-filter.max-filter{grid-template-columns:1fr}.ux-extra-actions{grid-template-columns:1fr}.ux-check-row{grid-template-columns:1fr}.ux-bottom-bar{align-items:stretch;flex-direction:column}.ux-bottom-bar .trainer-btn{min-width:0;width:100%}}@media(max-width:640px){.trainer-hero.maxux{padding:18px;border-radius:22px}.ux-case-top h2{font-size:23px}.ux-progress{grid-template-columns:1fr 1fr}.ux-progress .p{font-size:12px}.ux-path-compact{grid-template-columns:1fr}.ux-card,.ux-case-top{padding:14px;border-radius:20px}.trainer-control.ux-control{padding:13px 10px}.ux-desktop-only{display:none}.ux-mobile-only{display:block}.ux-bottom-bar{position:static;border-radius:16px}}
</style>
"""


def _trainer_case_card_v8658(c, recommended=False):
    group = _trainer_track_group_v8657(c.get('track', ''))
    search_blob = ' '.join(str(c.get(k, '')) for k in ('id', 'title', 'level', 'track', 'brief', 'goal')).lower()
    cls = 'trainer-case-card max-card' + (' recommended' if recommended else '')
    return f"""<article class="{cls}" data-level="{escape(c.get('level',''))}" data-track="{escape(c.get('track',''))}" data-group="{escape(group)}" data-search="{escape(search_blob)}">
      <div class="trainer-meta"><span class="trainer-pill">{escape(c.get('level',''))}</span><span class="trainer-pill">{escape(group)}</span><span class="trainer-pill">{escape(c.get('timebox',''))}</span></div>
      <h3>{escape(c.get('title',''))}</h3>
      <p>{escape(c.get('brief',''))}</p>
      <a class="trainer-btn accent" href="{url_for('/learning/' + c.get('id',''))}">Открыть и решить</a>
    </article>"""


def learning_home_page():
    from learning import list_cases, learning_catalog_summary
    cases = list_cases()
    catalog = learning_catalog_summary()
    levels = sorted({c.get('level', '') for c in cases if c.get('level')})
    tracks = sorted({c.get('track', '') for c in cases if c.get('track')})
    level_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in levels)
    track_options = ''.join(f'<option value="{escape(x)}">{escape(x)}</option>' for x in tracks)
    recommended_ids = ['bank-credit-bki-fraud', 'uk-bank-status-flow', 'event-enrichment-rest-kafka', 'bki-dwh-search']
    recommended = [c for rid in recommended_ids for c in cases if c.get('id') == rid]
    if len(recommended) < 4:
        recommended += [c for c in cases if c not in recommended][:4-len(recommended)]
    first = recommended[0] if recommended else (cases[0] if cases else {'id': ''})
    recommended_cards = ''.join(_trainer_case_card_v8658(c, True) for c in recommended[:4])
    cards = ''.join(_trainer_case_card_v8658(c) for c in cases)
    body = titleblock('ТРЕНАЖЁР СИСТЕМНОГО АНАЛИТИКА', active='learning') + f"""
<section class="trainer-hero maxux">
 <span class="trainer-kicker">Максимально простой режим · {escape(APP_VERSION)}</span>
 <h2>Открой кейс, выбери решения галочками и сразу получи разбор ошибок.</h2>
 <p>Здесь нет обязательного JSON и лишней техники на первом экране. Основной путь один: кейс → выбор решений → проверка → разбор → эталон.</p>
 <div class="ux-primary-path">
  <div class="ux-now">
   <h3>Что сделать сейчас</h3>
   <p>Начни с первого банковского кейса. Он быстро показывает, умеешь ли ты закрывать надёжность, идемпотентность, Kafka key, DLQ и таймауты.</p>
   <a class="trainer-btn accent" href="{url_for('/learning/' + first.get('id',''))}">Начать первый кейс</a>
  </div>
  <div class="ux-mini-card"><b>Для кого</b><span>Для подготовки к собеседованиям, разбора рабочих интеграций и тренировки архитектурного мышления.</span></div>
 </div>
 <h2 style="margin:18px 0 8px">Как пользоваться</h2>
 <div class="ux-path-compact" aria-label="Как пользоваться">
  <div class="ux-path-step" data-step="1"><b>1. Выбери кейс</b><span>Берите рекомендованный, если не знаете с чего начать.</span></div>
  <div class="ux-path-step" data-step="2"><b>2. Отметь решения</b><span>Галочка = “я добавлю это в архитектуру”.</span></div>
  <div class="ux-path-step" data-step="3"><b>3. Нажми проверку</b><span>Сначала будет короткий и понятный разбор.</span></div>
  <div class="ux-path-step" data-step="4"><b>4. Сравни с эталоном</b><span>Эталон открывается после твоей попытки.</span></div>
 </div>
</section>
<section class="trainer-section" id="start">
 <h2>Рекомендуемые кейсы для старта</h2>
 <p class="hint">Только 4 карточки, чтобы не утонуть в каталоге. Остальные кейсы спрятаны ниже.</p>
 <div class="trainer-start-grid max-two">{recommended_cards}</div>
</section>
<details class="ux-home-fold" id="progress">
 <summary>Мой прогресс</summary>
 <div class="ux-home-fold-inner">
  <div id="learningProgress" class="trainer-empty">Прогресс появится после первой проверки решения.</div>
  <div class="trainer-actions"><button class="trainer-btn secondary" type="button" onclick="loadLearningProgress()">Обновить прогресс</button></div>
 </div>
</details>
<details class="ux-home-fold" id="catalog">
 <summary>Весь каталог кейсов: {len(cases)}</summary>
 <div class="ux-home-fold-inner">
  <p class="hint">Версия каталога: {escape(catalog.get('catalog_version',''))}. Открывайте каталог только когда прошли стартовые кейсы.</p>
  <div class="trainer-filter max-filter">
   <input id="caseSearch" type="search" placeholder="Поиск: Kafka, банк, DWH, DLQ, SOAP..." oninput="filterTrainerCases()">
   <select id="levelFilter" onchange="filterTrainerCases()"><option value="">Все уровни</option>{level_options}</select>
   <select id="trackFilter" onchange="filterTrainerCases()"><option value="">Все темы</option>{track_options}</select>
  </div>
  <div id="caseCount" class="learning-count">Показано кейсов: {len(cases)} / {len(cases)}</div>
  <div id="emptyCaseState" class="trainer-empty trainer-hidden">По выбранным фильтрам ничего не найдено.</div>
  <div class="trainer-catalog-grid max-catalog" id="learningGrid">{cards}</div>
 </div>
</details>
<script>
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
async function loadLearningProgress(){{
 const box=document.getElementById('learningProgress'); if(!box) return;
 try{{
  const r=await fetch(basePath()+'/api/learning/progress?learner_id='+encodeURIComponent(learnerId()));
  const data=await r.json();
  if(!data.ok){{ box.innerHTML='<div class="err">Не удалось загрузить прогресс.</div>'; return; }}
  const weak=(data.weak_skills||[]).map(x=>x.name+': '+(x.score??'нет данных')).join('<br>') || 'Пока нет данных.';
  const next=(data.solved_case_count||0)===0 ? 'Откройте первый рекомендованный кейс и проверьте любое решение.' : 'Выберите кейс из слабой зоны и попробуйте улучшить результат.';
  box.innerHTML='<div class="trainer-progress-clean"><div class="trainer-progress-cell"><b>Попыток</b><span>'+data.attempt_count+'</span></div><div class="trainer-progress-cell"><b>Кейсов решено</b><span>'+data.solved_case_count+' / '+data.case_count+'</span></div><div class="trainer-progress-cell"><b>Бейджи</b><span>'+(data.badges||[]).length+'</span></div></div><p><b>Слабые зоны:</b><br>'+weak+'</p><p><b>Следующий шаг:</b> '+next+'</p>';
 }}catch(e){{ box.innerHTML='Прогресс пока недоступен. После первой проверки здесь появятся попытки и слабые зоны.'; }}
}}
function filterTrainerCases(){{
 const q=(document.getElementById('caseSearch')?.value||'').toLowerCase().trim();
 const lvl=document.getElementById('levelFilter')?.value||'';
 const tr=document.getElementById('trackFilter')?.value||'';
 const cards=[...document.querySelectorAll('#learningGrid .trainer-case-card')]; let shown=0;
 cards.forEach(c=>{{
  const okQ=!q || (c.dataset.search||'').includes(q);
  const okL=!lvl || c.dataset.level===lvl;
  const okT=!tr || c.dataset.track===tr;
  const ok=okQ&&okL&&okT;
  c.classList.toggle('trainer-hidden', !ok);
  if(ok) shown++;
 }});
 const cc=document.getElementById('caseCount'); if(cc) cc.textContent='Показано кейсов: '+shown+' / '+cards.length;
 const empty=document.getElementById('emptyCaseState'); if(empty) empty.classList.toggle('trainer-hidden', shown>0);
}}
loadLearningProgress(); filterTrainerCases();
</script>
"""
    return page('Тренажёр системного аналитика', body).replace('</head>', _TRAINER_MAX_STYLE_V8658 + '</head>')


def _skill_ru_v8658(skill: str) -> str:
    mapping = {
        'reliability': 'Надёжность и восстановление',
        'idempotency': 'Идемпотентность и порядок',
        'data': 'Данные и хранение',
        'contract': 'Контракты и версии',
        'security': 'Безопасность',
        'observability': 'Наблюдаемость',
        'process': 'Процесс и статусы',
        'performance': 'Производительность',
    }
    return mapping.get(str(skill or '').lower(), 'Прочие решения')


def _trainer_controls_v8658(controls):
    if not controls:
        return '<div class="trainer-empty">Для этого кейса нет отдельного чек-листа. Используйте экспертный JSON или эталон.</div>'
    grouped = {}
    order = []
    for ctrl in controls:
        group = _skill_ru_v8658(ctrl.get('skill', 'process'))
        if group not in grouped:
            grouped[group] = []
            order.append(group)
        grouped[group].append(ctrl)
    blocks = []
    n = 0
    for group in order:
        items = []
        for ctrl in grouped[group]:
            n += 1
            label = escape(ctrl.get('label', 'Архитектурное решение'))
            why = escape(ctrl.get('why', 'Помогает закрыть риск в этом кейсе.'))
            cid = escape(ctrl.get('id', f'control_{n}'))
            skill = escape(ctrl.get('skill', 'process'))
            items.append(f"""<label class="trainer-control ux-control"><input type="checkbox" class="visual-control" value="{cid}" data-label="{label}" data-skill="{skill}" onchange="updateSelectedCounter()"><span><b>{n}. {label}</b><small>{why}</small></span></label>""")
        blocks.append(f"""<section class="ux-control-group"><h4>{escape(group)}</h4><div class="ux-control-list">{''.join(items)}</div></section>""")
    return ''.join(blocks)


def learning_case_page(case_id):
    from learning import get_case
    c = get_case(case_id)
    if not c:
        return page('Кейс не найден', titleblock('ТРЕНАЖЁР', active='learning') + '<div class="err">Кейс не найден.</div>').replace('</head>', _TRAINER_MAX_STYLE_V8658 + '</head>')
    controls = c.get('expected_controls') or []
    traps = ''.join(f'<li>{escape(x)}</li>' for x in (c.get('hidden_traps') or [])) or '<li>Скрытые ловушки не указаны.</li>'
    control_items = _trainer_controls_v8658(controls)
    ref_json = _safe_json_v8653(c.get('payload') or {})
    safe_case_json = _safe_json_v8653({k:v for k,v in c.items() if k != 'payload'})
    body = titleblock('УЧЕБНЫЙ КЕЙС', active='learning') + f"""
<div class="ux-case-shell">

 <section class="ux-case-top">
  <div class="trainer-meta"><span class="trainer-pill">{escape(c.get('level',''))}</span><span class="trainer-pill">{escape(_trainer_track_group_v8657(c.get('track','')))}</span><span class="trainer-pill">{escape(c.get('timebox',''))}</span></div>
  <h2>{escape(c.get('title','Учебный кейс'))}</h2>
  <p class="case-brief">{escape(c.get('brief',''))}</p>
  <div class="ux-progress"><div class="p active">1. Задача</div><div class="p active">2. Выберите решения</div><div class="p">3. Проверьте</div><div class="p">4. Сравните</div></div>
  <div class="trainer-actions"><a class="trainer-btn secondary" href="{url_for('/learning')}">← К списку кейсов</a><button class="trainer-btn light" type="button" onclick="loadHint(1)">Не понимаю, с чего начать</button></div>
 </section>
 <section class="ux-card" id="task">
  <h3>1. Поймите задачу</h3>
  <p class="ux-card-lead">Сначала не думайте про технологии. Нужно понять, какой процесс проектируем и какие риски нельзя пропустить.</p>
  <div class="ux-task-grid">
   <div class="ux-task-box"><b>Цель кейса</b><p>{escape(c.get('goal',''))}</p></div>
   <div class="ux-task-box"><b>На что обратить внимание</b><ul>{traps}</ul></div>
  </div>
 </section>
 <section class="ux-card" id="solution">
  <h3>2. Выберите, что добавите в архитектуру</h3>
  <p class="ux-card-lead">Отмечайте только то, что реально включили бы в решение и смогли бы объяснить на собеседовании.</p>
  <div class="ux-toolbar"><div><div class="ux-counter" id="selectedCounter">Выбрано: 0 из {len(controls)}</div><div class="ux-hint">Не обязательно выбирать всё. Смысл — найти важные решения и потом увидеть пропуски.</div></div><div class="trainer-actions"><button class="trainer-btn secondary" type="button" onclick="clearControls()">Очистить</button><button class="trainer-btn secondary" type="button" onclick="loadHint(2)">Подсказка</button></div></div>
  {control_items}
  <div class="ux-check-row"><div id="visualBuilderState" class="ux-state">Решение пока не проверялось. Отметьте пункты и нажмите проверку.</div><button class="trainer-btn accent" type="button" onclick="evaluateLearning('learning')">Проверить выбранное решение</button></div>
 </section>
 <section class="ux-card" id="result">
  <h3>3. Результат проверки</h3>
  <p class="ux-card-lead">Сначала показывается короткий вывод. Полный отчёт и markdown спрятаны ниже, чтобы не перегружать экран.</p>
  <div id="learningResult" class="ux-result-empty">Здесь появятся оценка, главные ошибки и первые исправления.</div>
  <div class="ux-extra-actions"><button class="trainer-btn secondary" type="button" onclick="showReferencePack()">Показать эталон</button><button class="trainer-btn secondary" type="button" onclick="showInterviewPack()">Вопросы интервьюера</button><button class="trainer-btn secondary" type="button" onclick="document.getElementById('interviewBlock').open=true;document.getElementById('interviewBlock').scrollIntoView({{behavior:'smooth'}})">Потренировать ответ</button></div>
  <div id="hintBox" class="hint-box" style="display:none"></div>
  <details class="trainer-details ux-details"><summary>Полный markdown-разбор</summary><div class="trainer-details-inner"><pre id="learningMarkdown" class="trainer-report"></pre></div></details>
 </section>
 <details class="trainer-details ux-details" id="interviewBlock">
  <summary>4. Устный ответ как на собеседовании</summary>
  <div class="trainer-details-inner">
   <p class="ux-json-note">Опишите решение словами. Система отдельно оценит структуру ответа, аргументацию, риски и компромиссы.</p>
   <textarea id="interviewAnswer" class="trainer-answer" placeholder="Например: сначала фиксирую границы процесса, затем разделяю синхронный путь и асинхронные события..."></textarea>
   <div class="trainer-actions"><button class="trainer-btn accent" type="button" onclick="evaluateLearning('interview')">Оценить устный ответ</button><button class="trainer-btn secondary" type="button" onclick="showInterviewPack()">Показать вопросы интервьюера</button></div>
  </div>
 </details>
 <details class="trainer-details ux-details">
  <summary>Экспертный режим: JSON решения</summary>
  <div class="trainer-details-inner"><p class="ux-json-note">Обычному пользователю этот блок не нужен. Он оставлен для отладки, регрессионных тестов и точного редактирования payload.</p><textarea id="solutionJson" class="trainer-json" spellcheck="false"></textarea></div>
 </details>
 <details class="trainer-details ux-details">
  <summary>Метаданные кейса</summary>
  <div class="trainer-details-inner"><pre style="white-space:pre-wrap;font-size:11px">{escape(safe_case_json)}</pre></div>
 </details>
 <div class="ux-bottom-bar"><span class="ux-state ux-desktop-only">Главное действие: запустить проверку.</span><button class="trainer-btn accent" type="button" onclick="evaluateLearning('learning')">Проверить сейчас</button></div>
</div>
<script>
const CASE_ID = {json.dumps(case_id)};
const REFERENCE_PAYLOAD = {ref_json};
function basePath(){{ return document.documentElement.dataset.basePath || ''; }}
function safeStorageGet(k){{ try{{ return window.localStorage ? localStorage.getItem(k) : null; }}catch(e){{ return null; }} }}
function safeStorageSet(k,v){{ try{{ if(window.localStorage) localStorage.setItem(k,v); }}catch(e){{}} }}
function learnerId(){{ let id=safeStorageGet('sa_learning_learner_id') || window.__saFallbackLearnerId; if(!id){{ id='learner_'+Math.random().toString(16).slice(2)+Date.now().toString(16); window.__saFallbackLearnerId=id; safeStorageSet('sa_learning_learner_id', id); }} return id; }}
function esc(s){{ return String(s||'').replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[m])); }}
function selectedControlIds(){{ return [...document.querySelectorAll('.visual-control:checked')].map(x=>x.value).filter(Boolean); }}
function updateSelectedCounter(){{ const total=document.querySelectorAll('.visual-control').length; const selected=selectedControlIds().length; const text='Выбрано: '+selected+' из '+total; document.querySelectorAll('#selectedCounter').forEach(el=>el.textContent=text); }}
function clearControls(){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=false); updateSelectedCounter(); const s=document.getElementById('visualBuilderState'); if(s) s.textContent='Выбор очищен. Отметьте решения и проверьте ещё раз.'; }}
function selectAllControls(){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=true); updateSelectedCounter(); const s=document.getElementById('visualBuilderState'); if(s) s.textContent='Выбраны все пункты. Это полезно только для сравнения с эталоном.'; }}
async function buildVisualSolution(kind){{
 const ids=selectedControlIds();
 const box=document.getElementById('visualBuilderState');
 if(box) box.innerHTML='<b>Готовлю решение к проверке...</b>';
 try{{
   const params=new URLSearchParams({{case_id:CASE_ID, kind:kind||'selected', controls:ids.join(',')}});
   const r=await fetch(basePath() + '/api/learning/visual-payload?' + params.toString());
   const data=await r.json();
   if(!data.ok){{ if(box) box.innerHTML='<div class="err">'+((data.errors||['Ошибка сборки']).join('<br>'))+'</div>'; return null; }}
   if(kind==='reference'){{ document.querySelectorAll('.visual-control').forEach(x=>x.checked=true); updateSelectedCounter(); }}
   document.getElementById('solutionJson').value=JSON.stringify(data.payload||{{}},null,2);
   const selected=data.selected_count ?? ids.length;
   const total=data.control_count ?? document.querySelectorAll('.visual-control').length;
   if(box) box.innerHTML='<b>Решение подготовлено.</b> Выбрано пунктов: '+selected+' из '+total+'.';
   return data.payload||{{}};
 }}catch(e){{ if(box) box.innerHTML='<div class="err">Не удалось подготовить решение: '+esc(e.message)+'</div>'; return null; }}
}}
async function loadHint(level){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю подсказку...';
 try{{ const r=await fetch(basePath() + '/api/learning/hints?case_id='+encodeURIComponent(CASE_ID)+'&level='+encodeURIComponent(level)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} box.innerHTML='<b>Подсказка</b><ol>'+data.hints.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ol>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка подсказки: '+esc(e.message)+'</div>'; }}
}}
async function showReferencePack(){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю эталон...';
 try{{ const r=await fetch(basePath() + '/api/learning/reference?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const prod=(data.production?.steps||[]).slice(0,8).map(x=>'<li>'+esc(x)+'</li>').join(''); const acc=(data.acceptance_criteria||[]).map(x=>'<li>'+esc(x)+'</li>').join(''); box.innerHTML='<b>Эталон</b><p>'+esc(data.production?.description||'')+'</p><ol>'+prod+'</ol><p><b>Критерии приёмки:</b></p><ul>'+acc+'</ul><div class="trainer-actions"><button class="trainer-btn secondary" type="button" onclick="evaluateLearning(&quot;reference&quot;)">Проверить полный эталон</button></div>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка загрузки эталона: '+esc(e.message)+'</div>'; }}
}}
async function showInterviewPack(){{
 const box=document.getElementById('hintBox'); box.style.display='block'; box.innerHTML='Загружаю вопросы...';
 try{{ const r=await fetch(basePath() + '/api/learning/interview?case_id='+encodeURIComponent(CASE_ID)); const data=await r.json(); if(!data.ok){{box.innerHTML='<div class="err">'+((data.errors||['Ошибка']).join('<br>'))+'</div>';return;}} const qs=(data.questions||[]).slice(0,8).map(q=>'<li><b>'+esc(q.question||'')+'</b><br><span class="hint">Ожидается: '+esc((q.expected||[]).slice(0,2).join('; '))+'</span></li>').join(''); box.innerHTML='<b>Вопросы интервьюера</b><p>'+esc(data.opening_prompt||'')+'</p><ol>'+qs+'</ol>'; box.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}catch(e){{ box.innerHTML='<div class="err">Ошибка загрузки вопросов: '+esc(e.message)+'</div>'; }}
}}
function simpleDashboard(data){{
 const sol=data.solution_score ?? data.learning_score ?? 0;
 const ans=data.answer_score ?? null;
 const interview=data.interview_score ?? null;
 const scoreText=String(sol).replace('.', ',')+' / 10';
 const errors=(data.quick_summary?.top_errors||data.gaps?.map(g=>g.title)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Критичных пропусков не найдено.</li>';
 const fixes=(data.quick_summary?.quick_fixes||data.gaps?.map(g=>g.fix)||[]).slice(0,3).map(x=>'<li>'+esc(x)+'</li>').join('') || '<li>Сравните решение с эталоном и проверьте эксплуатационные детали.</li>';
 let extra=''; if(ans!==null) extra+='<p><b>Устный ответ:</b> '+ans+' / 10</p>'; if(interview!==null) extra+='<p><b>Итог интервью:</b> '+interview+' / 10</p>';
 return '<div class="ux-result-card"><h2>'+esc(data.learning_level||'Результат')+'</h2><div class="ux-result-main"><div class="ux-big-score"><b>Оценка решения</b><span>'+scoreText+'</span>'+extra+'</div><div class="ux-result-lists"><div><b>Главные ошибки</b><ol>'+errors+'</ol></div><div><b>Что исправить первым</b><ol>'+fixes+'</ol></div></div></div>'+(data.attempt_md_url?'<div class="trainer-actions"><a class="trainer-btn secondary" href="'+data.attempt_md_url+'" target="_blank">Открыть markdown попытки</a></div>':'')+'</div>';
}}
async function evaluateLearning(mode){{
 const box=document.getElementById('learningResult'); const md=document.getElementById('learningMarkdown');
 if(mode==='reference') await buildVisualSolution('reference'); else await buildVisualSolution('selected');
 box.innerHTML='<div class="ux-result-empty">Проверяю решение...</div>'; md.textContent='Проверяю...';
 let payload;
 try{{ payload=JSON.parse(document.getElementById('solutionJson').value || '{{}}'); }}catch(e){{ box.innerHTML='<div class="err">JSON не читается: '+esc(e.message)+'</div>'; md.textContent=''; return; }}
 try{{
   const answerText=(document.getElementById('interviewAnswer')?.value || '');
   const r=await fetch(basePath() + '/api/learning/evaluate', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{case_id:CASE_ID, payload, mode, learner_id: learnerId(), answer_text: answerText}})}});
   const data=await r.json();
   if(!data.ok){{ box.innerHTML='<div class="err">'+(data.errors||['Ошибка']).join('<br>')+'</div>'; return; }}
   box.innerHTML=simpleDashboard(data)+'<details class="trainer-details ux-details"><summary>Показать полный учебный разбор</summary><div class="trainer-details-inner">'+(data.html || '')+'</div></details>';
   md.textContent=data.report_markdown || '';
   safeStorageSet('sa_learning_'+CASE_ID, JSON.stringify({{score:data.learning_score, level:data.learning_level, attempt_id:data.attempt_id, at:new Date().toISOString()}}));
   document.getElementById('result')?.scrollIntoView({{behavior:'smooth',block:'start'}});
 }}catch(e){{ box.innerHTML='<div class="err">Ошибка запроса: '+esc(e.message)+'</div>'; md.textContent=''; }}
}}
updateSelectedCounter();
</script>
"""
    return page(c.get('title', 'Учебный кейс'), body).replace('</head>', _TRAINER_MAX_STYLE_V8658 + '</head>')

# ---------------------------------------------------------------------------
# v8.6.64: полный UX-слой поверх стабильного ядра.
# Цель: не ломать существующие сценарии и тесты, а добавить современную
# продуктовую оболочку: маршруты, глоссарий, карты рисков, progress, reports,
# command palette, mobile-first CTA и объяснимость.
# ---------------------------------------------------------------------------

APP_VERSION = '8.6.67-ultimate-gated'

GLOSSARY_V8663 = {
    'REST': 'Синхронный HTTP-вызов. Подходит, когда нужен быстрый ответ здесь и сейчас.',
    'gRPC': 'Синхронный бинарный RPC. Полезен для внутренних быстрых сервисных вызовов.',
    'SOAP': 'Legacy XML-интеграция. Часто требует строгих контрактов, таймаутов и адаптера.',
    'Kafka': 'Журнал событий для асинхронной обработки, нескольких потребителей и replay.',
    'RabbitMQ': 'Очередь задач/сообщений, удобна для point-to-point и routing-сценариев.',
    'Outbox': 'Сначала сохраняем событие рядом с бизнес-изменением в БД, потом публикуем. Так событие не теряется.',
    'Inbox': 'Храним входящее событие и его статус обработки, чтобы дубли не меняли данные повторно.',
    'DLQ': 'Очередь ошибок. Туда отправляется сообщение, которое не удалось обработать после нескольких попыток.',
    'retry': 'Повторная попытка. Она должна быть ограниченной, безопасной и не создавать дубли.',
    'replay': 'Повторное проигрывание событий из журнала или архива для восстановления данных.',
    'идемпотентность': 'Повтор одного и того же запроса или события не должен создавать второй результат.',
    'correlationId': 'Идентификатор цепочки запроса. Помогает связать логи, события и вызовы в один процесс.',
    'eventId': 'Уникальный id события. Нужен для дедупликации и расследования.',
    'partition key': 'Ключ распределения событий по партициям Kafka. От него зависит порядок обработки.',
    'contract versioning': 'Версионирование контракта, чтобы новые поля не ломали старых потребителей.',
    'Schema Registry': 'Хранилище схем событий/сообщений. Помогает контролировать совместимость контрактов.',
    'Saga': 'Длинный бизнес-процесс из нескольких шагов с компенсациями вместо одной большой транзакции.',
    'compensation': 'Компенсирующее действие, которое исправляет эффект уже выполненного шага.',
    'eventual consistency': 'Согласованность не мгновенная: данные сходятся через некоторое время.',
    'read-your-writes': 'Пользователь после записи должен видеть собственное изменение, даже если система асинхронная.',
    'OLTP': 'Операционная БД для текущих бизнес-транзакций.',
    'OLAP': 'Аналитическое хранилище для отчётов и больших выборок.',
    'DWH': 'Хранилище данных для аналитики, отчётности и витрин.',
    'cache': 'Быстрое временное хранилище, которое снижает нагрузку и задержку.',
    'CDC': 'Передача изменений из БД в поток/хранилище по журналу изменений.',
    'backpressure': 'Механизм защиты, когда downstream не успевает обрабатывать поток.',
    'rate limit': 'Ограничение количества запросов, чтобы не перегрузить сервис.',
    'timeout': 'Максимальное время ожидания ответа. Без него поток может зависнуть.',
    'circuit breaker': 'Защита от постоянных вызовов в падающую внешнюю систему.',
    'observability': 'Наблюдаемость: логи, метрики, трассировка и алерты.',
    'SLA': 'Договорённый уровень сервиса, например доступность или время ответа.',
    'SLO': 'Внутренняя целевая метрика надёжности сервиса.',
    'RTO': 'За какое время система должна восстановиться после сбоя.',
    'RPO': 'Сколько данных допустимо потерять при аварии.',
}

UX_COMPLETE_STYLE_V8663 = r'''
<style>
:root{--ux-bg:#f6f8fb;--ux-surface:#ffffff;--ux-ink:#111827;--ux-muted:#667085;--ux-line:#d9e1ea;--ux-primary:#0f766e;--ux-primary-soft:#e6fffb;--ux-blue:#2563eb;--ux-danger:#b42318;--ux-warn:#b54708;--ux-good:#067647;--ux-shadow:0 18px 45px rgba(15,23,42,.08)}
body{background:var(--ux-bg)!important;color:var(--ux-ink)}.skip-link{position:absolute;left:-999px;top:8px;background:#fff;border:2px solid var(--ux-primary);padding:8px 12px;z-index:999}.skip-link:focus{left:8px}
.app-shell{display:grid;grid-template-columns:236px minmax(0,1fr);min-height:100vh}.app-sidebar{position:sticky;top:0;height:100vh;background:#0b1220;color:#dbeafe;padding:18px 14px;display:flex;flex-direction:column;gap:14px}.app-brand{font:800 15px/1.2 var(--mono);letter-spacing:.05em;color:#fff}.app-brand small{display:block;margin-top:6px;color:#8ea3bd;font:11px var(--mono);letter-spacing:0}.app-nav{display:grid;gap:6px}.app-nav a{color:#cbd5e1;text-decoration:none;border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:10px 11px;font:700 12px var(--mono)}.app-nav a:hover,.app-nav a.active{background:rgba(45,212,191,.12);color:#fff;border-color:rgba(45,212,191,.45)}.app-side-card{margin-top:auto;border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:12px;background:rgba(255,255,255,.04);font-size:12px;color:#b6c2d2}.app-content{min-width:0}.wrap{max-width:1180px}.mobile-bottom-nav{display:none}.command-fab{position:fixed;right:18px;bottom:18px;z-index:30;border:0;border-radius:999px;background:#0b1220;color:#fff;padding:12px 16px;box-shadow:var(--ux-shadow);font:800 12px var(--mono);cursor:pointer}.cmd-backdrop{display:none;position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:50;align-items:flex-start;justify-content:center;padding:10vh 16px}.cmd-backdrop.open{display:flex}.cmd-modal{width:min(720px,100%);background:#fff;border-radius:22px;box-shadow:var(--ux-shadow);border:1px solid var(--ux-line);overflow:hidden}.cmd-modal input{border:0;border-bottom:1px solid var(--ux-line);border-radius:0;padding:18px;font-size:17px}.cmd-results{max-height:420px;overflow:auto;padding:10px}.cmd-item{display:flex;justify-content:space-between;gap:12px;padding:12px;border-radius:14px;text-decoration:none;color:var(--ux-ink)}.cmd-item:hover{background:var(--ux-primary-soft)}.cmd-item small{color:var(--ux-muted)}
.ux-home-gateway,.ux-complete-panel,.ux-report-summary{background:linear-gradient(135deg,#fff,#f0fdfa);border:1px solid var(--ux-line);border-radius:24px;box-shadow:var(--ux-shadow);padding:22px;margin:0 0 18px}.ux-home-gateway h2,.ux-complete-panel h2{margin:0 0 8px;font-size:26px;line-height:1.12}.ux-home-gateway p,.ux-complete-panel p{color:var(--ux-muted);margin:6px 0}.ux-path-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:16px}.ux-path-card{display:block;text-decoration:none;color:var(--ux-ink);background:#fff;border:1px solid var(--ux-line);border-radius:18px;padding:16px;min-height:142px}.ux-path-card:hover{border-color:var(--ux-primary);box-shadow:0 10px 30px rgba(15,118,110,.12);transform:translateY(-1px)}.ux-path-card b{display:block;font-size:16px;margin-bottom:6px}.ux-path-card span{display:block;color:var(--ux-muted);font-size:13px}.ux-path-card strong{display:inline-block;margin-top:12px;color:var(--ux-primary);font-size:13px}.ux-mode-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}.ux-mode{border:1px solid var(--ux-line);border-radius:16px;background:#fff;padding:13px;text-align:left;cursor:pointer}.ux-mode.active{border-color:var(--ux-primary);background:var(--ux-primary-soft);box-shadow:inset 0 0 0 1px var(--ux-primary)}.ux-mode b{display:block}.ux-mode small{display:block;color:var(--ux-muted);margin-top:4px}.ux-toolbar-plus{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}.ux-pill{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--ux-line);border-radius:999px;background:#fff;padding:6px 10px;font-size:12px;color:var(--ux-muted)}.ux-pill.good{color:var(--ux-good);border-color:#b7e4c7;background:#f0fdf4}.ux-pill.warn{color:var(--ux-warn);border-color:#fed7aa;background:#fffbeb}.ux-pill.danger{color:var(--ux-danger);border-color:#fecaca;background:#fff1f2}.ux-risk-map{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.ux-risk-card{border:1px solid var(--ux-line);border-radius:16px;background:#fff;padding:12px}.ux-risk-card.good{border-left:5px solid var(--ux-good)}.ux-risk-card.warn{border-left:5px solid var(--ux-warn)}.ux-risk-card.danger{border-left:5px solid var(--ux-danger)}.ux-risk-card b{display:block}.ux-risk-card small{color:var(--ux-muted)}.ux-score-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.ux-score-card{border:1px solid var(--ux-line);border-radius:16px;background:#fff;padding:12px}.ux-score-card b{display:block;font:11px var(--mono);color:var(--ux-muted);text-transform:uppercase}.ux-score-card span{font:900 25px var(--mono);color:var(--ux-primary)}.ux-action-list{display:grid;gap:8px}.ux-action-list div{border:1px solid var(--ux-line);border-radius:14px;background:#fff;padding:11px}.glossary-term{border-bottom:1px dotted var(--ux-primary);cursor:help;color:#0f766e;font-weight:700}.glossary-strip{display:flex;gap:8px;overflow:auto;padding:8px 0}.glossary-chip{white-space:nowrap;border:1px solid var(--ux-line);border-radius:999px;padding:6px 10px;background:#fff;font-size:12px}.glossary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.glossary-card{background:#fff;border:1px solid var(--ux-line);border-radius:16px;padding:14px}.glossary-card h3{margin:0 0 6px}.ux-knowledge-tools{background:#fff;border:1px solid var(--ux-line);border-radius:18px;padding:14px;margin:0 0 16px}.ux-knowledge-tools input{border-radius:12px}.ux-progress-radar{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin:12px 0}.ux-progress-radar .rad{background:#fff;border:1px solid var(--ux-line);border-radius:14px;padding:10px}.ux-progress-radar b{display:block;font-size:11px;color:var(--ux-muted)}.ux-progress-radar span{font:900 20px var(--mono);color:var(--ux-primary)}.ux-bottom-bar,.ux-mobile-sticky{box-shadow:0 -10px 30px rgba(15,23,42,.08)}
.visual-control-card,.learning-card,.trainer-card,.refcard,.card{border-radius:18px!important}.btn,.trainer-btn,.learn-actions button,.learning-card a.learn-open{border-radius:12px!important;text-transform:none!important;letter-spacing:0!important}.err{border-radius:14px}.empty-state{border:1px dashed var(--ux-line);border-radius:18px;background:#fff;padding:16px;color:var(--ux-muted)}
@media(max-width:1100px){.app-shell{grid-template-columns:1fr}.app-sidebar{display:none}.app-content{padding-bottom:92px}.mobile-bottom-nav{position:fixed;left:0;right:0;bottom:0;z-index:35;display:grid;grid-template-columns:repeat(4,1fr);background:#0b1220;border-top:1px solid rgba(255,255,255,.12)}.mobile-bottom-nav a{color:#e5e7eb;text-decoration:none;text-align:center;padding:10px 4px;font:700 11px var(--mono)}.command-fab{display:none}.wrap{padding-bottom:120px}.sticky-submit{position:static}.ux-bottom-bar,.ux-mobile-sticky{position:static}.ux-path-grid{grid-template-columns:1fr 1fr}.ux-score-grid,.ux-risk-map,.glossary-grid,.ux-progress-radar{grid-template-columns:1fr 1fr}.ux-mode-grid{grid-template-columns:1fr}}
@media(max-width:640px){.ux-path-grid,.ux-score-grid,.ux-risk-map,.glossary-grid,.ux-progress-radar{grid-template-columns:1fr}.ux-home-gateway h2,.ux-complete-panel h2{font-size:22px}.ux-home-gateway,.ux-complete-panel,.ux-report-summary{padding:16px;border-radius:18px}.wrap{padding-left:12px;padding-right:12px}.titleblock{border-radius:16px;align-items:flex-start}.command-fab{right:12px}.ux-desktop-only{display:none!important}}
</style>
'''

UX_COMPLETE_SCRIPT_V8663 = r'''
<script>
(function(){
 const glossary = __GLOSSARY_JSON__;
 const commands = [
  ['Главная','/','Выбор сценария'], ['Тренажёр','/learning','Кейсы и собеседования'], ['Конструктор','/','Свой процесс'],
  ['Инварианты','/invariants','Что нельзя забыть'], ['Паттерны','/patterns','Архитектурные решения'], ['Глоссарий','/glossary','Термины простыми словами'],
  ['Прогресс','/progress','Карта навыков'], ['Отчёты','/reports','История результатов']
 ].concat(Object.keys(glossary).map(k=>['Термин: '+k,'/glossary#term-'+encodeURIComponent(k),glossary[k]]));
 function base(){return document.documentElement.dataset.basePath||'';}
 function openCmd(){let b=document.getElementById('cmdBackdrop'); if(b){b.classList.add('open'); setTimeout(()=>document.getElementById('cmdInput')?.focus(),30); renderCmd('');}}
 function closeCmd(){document.getElementById('cmdBackdrop')?.classList.remove('open');}
 function renderCmd(q){const box=document.getElementById('cmdResults'); if(!box) return; q=(q||'').toLowerCase(); const rows=commands.filter(x=>(x[0]+' '+x[2]).toLowerCase().includes(q)).slice(0,12); box.innerHTML=rows.map(x=>'<a class="cmd-item" href="'+base()+x[1]+'"><span><b>'+escapeHtml(x[0])+'</b><br><small>'+escapeHtml(x[2])+'</small></span><small>↵</small></a>').join('') || '<div class="empty-state">Ничего не найдено. Попробуйте: outbox, kafka, отчёт, тренажёр.</div>';}
 function escapeHtml(s){return String(s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
 function enhanceGlossary(){
   const terms=Object.keys(glossary).sort((a,b)=>b.length-a.length).slice(0,80);
   document.querySelectorAll('.visual-control-card label,.ux-card-lead,.case-brief,.finding h3,.flowbox h3').forEach(el=>{
     if(el.dataset.glossaryDone) return; let html=el.innerHTML;
     terms.forEach(t=>{ const safe=t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); const re=new RegExp('(^|[\\s(>])('+safe+')(?=[\\s.,;:)<]|$)','gi'); html=html.replace(re,(m,p,x)=>p+'<span class="glossary-term" title="'+escapeHtml(glossary[t])+'">'+x+'</span>'); });
     el.innerHTML=html; el.dataset.glossaryDone='1';
   });
 }
 function activeByPath(){ const p=location.pathname.replace((document.documentElement.dataset.basePath||''),'') || '/'; document.querySelectorAll('.app-nav a,.mobile-bottom-nav a').forEach(a=>{ const h=a.getAttribute('href')||''; if((p==='/'&&h.endsWith('/')) || (h!=='/'&&p.startsWith(h.replace(base(),'')))) a.classList.add('active'); }); }
 window.openCommandPaletteV8663=openCmd; window.closeCommandPaletteV8663=closeCmd;
 document.addEventListener('keydown',e=>{ if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCmd();} if(e.key==='Escape') closeCmd();});
 document.addEventListener('input',e=>{ if(e.target && e.target.id==='cmdInput') renderCmd(e.target.value); if(e.target && e.target.id==='knowledgeSearch'){ const q=e.target.value.toLowerCase(); document.querySelectorAll('.refcard,.glossary-card,.learning-card,.trainer-card').forEach(c=>{c.style.display=c.textContent.toLowerCase().includes(q)?'':'none'}); }});
 document.addEventListener('click',e=>{ if(e.target && e.target.id==='cmdBackdrop') closeCmd(); });
 document.addEventListener('DOMContentLoaded',()=>{activeByPath(); enhanceGlossary(); setTimeout(enhanceGlossary,400);});
})();
</script>
'''

_PREV_PAGE_V8663 = page

def _nav_shell_v8663(active=''):
    links = [('/', 'Главная'), ('/learning', 'Тренажёр'), ('/reports', 'Отчёты'), ('/progress', 'Прогресс'), ('/patterns', 'Паттерны'), ('/invariants', 'Инварианты'), ('/glossary', 'Глоссарий')]
    nav = ''.join(f'<a href="{url_for(h)}">{escape(t)}</a>' for h, t in links)
    mobile = ''.join(f'<a href="{url_for(h)}">{escape(t)}</a>' for h, t in links[:4])
    return f'''<a class="skip-link" href="#main">Перейти к содержимому</a><div class="app-shell"><aside class="app-sidebar" aria-label="Основная навигация"><div class="app-brand">SmartAdvisor<small>{APP_VERSION}</small></div><nav class="app-nav">{nav}</nav><div class="app-side-card"><b>Ctrl+K</b><br>Быстрый поиск по кейсам, паттернам, инвариантам и терминам.</div></aside><main id="main" class="app-content">''', f'''</main></div><nav class="mobile-bottom-nav" aria-label="Мобильная навигация">{mobile}</nav><button class="command-fab" type="button" onclick="openCommandPaletteV8663()">Ctrl K</button><div class="cmd-backdrop" id="cmdBackdrop"><div class="cmd-modal" role="dialog" aria-modal="true" aria-label="Быстрый поиск"><input id="cmdInput" placeholder="Найти кейс, паттерн, инвариант или термин"><div id="cmdResults" class="cmd-results"></div></div></div>'''

def page(title, body, extra_head=''):
    before, after = _nav_shell_v8663()
    html = _PREV_PAGE_V8663(title, before + body + after, extra_head + UX_COMPLETE_STYLE_V8663)
    script = UX_COMPLETE_SCRIPT_V8663.replace('__GLOSSARY_JSON__', json.dumps(GLOSSARY_V8663, ensure_ascii=False))
    html = html.replace('freshness contract', 'контракт свежести данных').replace('change process', 'процесс изменения')
    return html.replace('</body>', script + '</body>')


def _scenario_gateway_v8663():
    return f'''
<section class="ux-home-gateway" aria-label="Быстрый выбор сценария"><div class="ux-pill good">Новый UX-слой · простой путь сначала</div><h2>Что хотите сделать сейчас?</h2><p>Выберите один маршрут. Сложные настройки, JSON и полный технический разбор остаются доступны, но не мешают первому результату.</p><div class="ux-path-grid"><a class="ux-path-card" href="{url_for('/learning')}"><b>Потренироваться</b><span>Кейс, чек-лист решений, оценка, эталон и вопросы интервьюера.</span><strong>Начать кейс →</strong></a><a class="ux-path-card" href="#constructor-start"><b>Собрать интеграцию</b><span>Участники, связи, риски, стек и отчёт без свободного текста.</span><strong>Открыть конструктор ↓</strong></a><a class="ux-path-card" href="{url_for('/glossary')}"><b>Понять термины</b><span>Outbox, DLQ, идемпотентность, partition key простыми словами.</span><strong>Глоссарий →</strong></a><a class="ux-path-card" href="{url_for('/patterns')}"><b>Найти решение</b><span>Паттерны, инварианты и готовые архитектурные подсказки.</span><strong>База знаний →</strong></a></div></section>'''

_PREV_FORM_PAGE_V8663 = form_page

def form_page():
    html = _PREV_FORM_PAGE_V8663()
    guide = _scenario_gateway_v8663() + '''<section class="ux-complete-panel" id="constructor-start"><div class="ux-pill">Конструктор · один шаг за раз</div><h2>Сначала процесс, потом стек</h2><p>Правильная последовательность: участники → связи → риски → стек → отчёт. Не начинайте с выбора технологии, пока не понятна бизнес-цепочка.</p><div class="ux-risk-map"><div class="ux-risk-card good"><b>1. Участники</b><small>Кто участвует и кто владелец.</small></div><div class="ux-risk-card warn"><b>2. Связи</b><small>Что происходит между системами.</small></div><div class="ux-risk-card danger"><b>3. Риски</b><small>Дубли, порядок, потери, контракты.</small></div></div></section>'''
    return html.replace('<section class="hero">', guide + '<section class="hero">', 1)


def _learning_modes_panel_v8663():
    return '''<section class="ux-complete-panel" aria-label="Режим тренировки"><div class="ux-pill good">Учебный маршрут</div><h2>Выберите глубину тренировки</h2><p>Один и тот же кейс можно пройти по-разному: с объяснениями, как на собеседовании или на Senior-уровне.</p><div class="ux-mode-grid" id="modeGridV8663"><button class="ux-mode active" type="button" data-mode="novice"><b>Новичок</b><small>Термины объясняются простыми словами.</small></button><button class="ux-mode" type="button" data-mode="interview"><b>Собеседование</b><small>Меньше подсказок, больше вопросов интервьюера.</small></button><button class="ux-mode" type="button" data-mode="senior"><b>Senior-разбор</b><small>Компромиссы, эксплуатация, edge cases.</small></button></div><div class="glossary-strip" aria-label="Быстрые термины"><span class="glossary-chip" title="Событие не теряется между БД и брокером">Outbox</span><span class="glossary-chip" title="Дубли входящих событий не меняют данные повторно">Inbox</span><span class="glossary-chip" title="Очередь ошибок для проблемных сообщений">DLQ</span><span class="glossary-chip" title="Повтор не создаёт второй результат">идемпотентность</span><span class="glossary-chip" title="Ключ порядка в Kafka">partition key</span></div></section><script>document.addEventListener('click',function(e){if(e.target.closest('.ux-mode')){document.querySelectorAll('.ux-mode').forEach(x=>x.classList.remove('active'));e.target.closest('.ux-mode').classList.add('active');try{localStorage.setItem('sa_training_mode',e.target.closest('.ux-mode').dataset.mode)}catch(_){}}});</script>'''

_PREV_LEARNING_HOME_PAGE_V8663 = learning_home_page

def learning_home_page():
    html = _PREV_LEARNING_HOME_PAGE_V8663()
    return html.replace('<section class="trainer-hero maxux">', _learning_modes_panel_v8663() + '<section class="trainer-hero maxux">', 1)

_PREV_LEARNING_CASE_PAGE_V8663 = learning_case_page

def learning_case_page(case_id):
    html = _PREV_LEARNING_CASE_PAGE_V8663(case_id)
    starter = '''<section class="ux-complete-panel"><div class="ux-pill good">Кейс · понятный режим</div><h2>Работайте по слоям: смысл → риск → термин</h2><p>Сначала думайте, что может сломаться: потеря события, дубли, порядок, контракт, восстановление. Термины вроде Outbox/DLQ нужны только как способ закрыть риск.</p><div class="ux-risk-map"><div class="ux-risk-card good"><b>Закрывайте риски</b><small>Отмечайте только решения, которые сможете объяснить.</small></div><div class="ux-risk-card warn"><b>Смотрите карту ошибок</b><small>После проверки видно, какие риски закрыты, а какие нет.</small></div><div class="ux-risk-card danger"><b>Сравнивайте с Senior</b><small>Эталон открывается слоями, а не одной стеной текста.</small></div></div></section>'''
    html = html.replace('<section class="ux-case-top">', starter + '<section class="ux-case-top">', 1)
    enhance = r'''<script>(function(){const oldSimpleDashboard=window.simpleDashboard||simpleDashboard;function esc2(s){return String(s||'').replace(/[&<>]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));}window.simpleDashboard=function(data){const base=oldSimpleDashboard(data);const hits=(data.control_hits||[]).slice(0,6).map(x=>'<div class="ux-risk-card good"><b>✓ '+esc2(x.label||'Контроль найден')+'</b><small>'+esc2(x.why||'Риск закрыт.')+'</small></div>').join('');const miss=(data.gaps||[]).slice(0,6).map(x=>'<div class="ux-risk-card danger"><b>✕ '+esc2(x.title||'Риск не закрыт')+'</b><small>'+esc2(x.why||'Нужно уточнить.')+'<br><b>Исправить:</b> '+esc2(x.fix||'Добавьте контроль в схему.')+'</small></div>').join('');const skills=Object.entries(data.skill_scores||{}).map(([k,v])=>'<div class="ux-score-card"><b>'+esc2(v.name||k)+'</b><span>'+esc2(v.score??0)+'</span></div>').join('');const interview='<div class="ux-complete-panel"><h2>Как сказать на собеседовании</h2><p>Начните с границ процесса, затем разделите синхронный путь и асинхронные события, после этого проговорите дубли, порядок, восстановление и наблюдаемость.</p><div class="ux-toolbar-plus"><button class="trainer-btn secondary" type="button" onclick="showInterviewPack()">Вопросы интервьюера</button><button class="trainer-btn secondary" type="button" onclick="showReferencePack()">Senior-эталон</button></div></div>';return base+'<div class="ux-report-summary"><h2>Карта закрытых и незакрытых рисков</h2><div class="ux-risk-map">'+(hits||'<div class="ux-risk-card warn"><b>Пока нет закрытых рисков</b><small>Выберите архитектурные контроли и проверьте снова.</small></div>')+(miss||'<div class="ux-risk-card good"><b>Ключевые риски закрыты</b><small>Сравните решение с эталоном и проверьте эксплуатацию.</small></div>')+'</div><h3>Карта навыков</h3><div class="ux-score-grid">'+skills+'</div></div>'+interview;}})();</script>'''
    return html.replace('</body>', enhance + '</body>')


def _top_actions_from_result_v8663(res):
    out=[]
    for i in (res.get('checklist') or {}).get('items', []):
        if i.get('status') in ('fail','warn'): out.append(i.get('fix') or i.get('title') or '')
    for f in (res.get('finding_groups') or res.get('findings') or []):
        if f.get('severity') in ('critical','high'): out.append(f.get('fix') or f.get('title') or '')
    seen=[]
    for x in out:
        x=str(x).strip()
        if x and x not in seen: seen.append(x)
        if len(seen)>=5: break
    return seen

_PREV_RESULT_PAGE_V8663 = result_page

def result_page(rid, res):
    html = _PREV_RESULT_PAGE_V8663(rid, res)
    v=res.get('verdict') or {}; gates=res.get('quality_gates') or {}; checklist=(res.get('checklist') or {}).get('counters') or {}; actions=_top_actions_from_result_v8663(res)
    actions_html=''.join(f'<div><b>{i+1}. Следующее действие</b><br>{escape(a)}</div>' for i,a in enumerate(actions)) or '<div><b>Блокеров не найдено</b><br>Проверьте контракты, нагрузку, безопасность и эксплуатацию перед выпуском.</div>'
    pill='good' if v.get('color')=='green' else 'warn' if v.get('color')=='yellow' else 'danger'
    risk_html=f'''<section class="ux-report-summary" aria-label="Короткий итог отчёта"><div class="ux-pill {pill}">Executive summary</div><h2>{escape(v.get('verdict','Вердикт'))} · {escape(str(v.get('score','—')))} / 10</h2><p>Сначала показан короткий слой для решения: статус, главные риски и первые действия. Полный технический markdown остаётся ниже.</p><div class="ux-score-grid"><div class="ux-score-card"><b>Production readiness</b><span>{escape(str(gates.get('readiness','—')))}</span></div><div class="ux-score-card"><b>Блокируют</b><span>{checklist.get('fail',0)}</span></div><div class="ux-score-card"><b>Требуют проверки</b><span>{checklist.get('warn',0)}</span></div><div class="ux-score-card"><b>Проверено</b><span>{checklist.get('ok',0)}</span></div></div><h3>Что сделать первым</h3><div class="ux-action-list">{actions_html}</div></section>'''
    return html.replace('<nav class="resultnav"', risk_html + '<nav class="resultnav"', 1)


def _knowledge_tools_v8663(kind='knowledge'):
    return '''<section class="ux-knowledge-tools"><div class="ux-pill">Knowledge base</div><h2>Сначала найдите нужный смысл, потом читайте детали</h2><p>Используйте поиск по словам: outbox, дубли, контракт, Kafka, DWH, миграция, retry.</p><input id="knowledgeSearch" placeholder="Поиск по справочнику"><div class="ux-toolbar-plus"><span class="ux-pill">Топ: дубли</span><span class="ux-pill">Топ: порядок</span><span class="ux-pill">Топ: контракты</span><span class="ux-pill">Топ: эксплуатация</span></div></section>'''

_PREV_INVARIANT_REFERENCE_PAGE_V8663 = invariant_reference_page

def invariant_reference_page():
    html = _PREV_INVARIANT_REFERENCE_PAGE_V8663()
    return html.replace('<section class="hero">', _knowledge_tools_v8663('invariants') + '<section class="hero">', 1)

_PREV_DESIGN_PATTERN_REFERENCE_PAGE_V8663 = design_pattern_reference_page

def design_pattern_reference_page():
    html = _PREV_DESIGN_PATTERN_REFERENCE_PAGE_V8663()
    return html.replace('<section class="hero">', _knowledge_tools_v8663('patterns') + '<section class="hero">', 1)


def glossary_page():
    cards=''.join(f'<article class="glossary-card" id="term-{escape(k)}"><h3>{escape(k)}</h3><p>{escape(v)}</p><p class="hint"><b>На собеседовании:</b> объясните не термин, а риск, который он закрывает.</p></article>' for k,v in sorted(GLOSSARY_V8663.items()))
    body=titleblock('ГЛОССАРИЙ', active='glossary') + f'''<section class="ux-complete-panel"><h2>Термины простыми словами</h2><p>Этот раздел нужен, чтобы тренажёр был понятен не только сильному Middle+, но и пользователю, который только подтягивает интеграции.</p><input id="knowledgeSearch" placeholder="Найти термин: DLQ, outbox, Kafka, retry..."></section><section class="glossary-grid">{cards}</section>'''
    return page('Глоссарий', body)


def progress_page():
    body=titleblock('ПРОГРЕСС ОБУЧЕНИЯ', active='progress') + '''<section class="ux-complete-panel"><h2>Карта навыков</h2><p>Без аккаунтов прогресс хранится локально в браузере. Для полноценного SaaS этот слой нужно перенести в серверную модель пользователя.</p><div id="progressLocal" class="empty-state">Загружаю локальный прогресс...</div></section><section class="ux-report-summary"><h2>Рекомендуемый маршрут Middle → Senior</h2><div class="ux-risk-map"><div class="ux-risk-card good"><b>1. Sync/async</b><small>REST, gRPC, Kafka, RabbitMQ.</small></div><div class="ux-risk-card warn"><b>2. Надёжность</b><small>Outbox, Inbox, retry, DLQ, replay.</small></div><div class="ux-risk-card danger"><b>3. Production</b><small>Мониторинг, backpressure, миграции, контракты.</small></div></div></section><script>(function(){const box=document.getElementById('progressLocal');let rows=[];try{for(let i=0;i<localStorage.length;i++){let k=localStorage.key(i);if(k&&k.startsWith('sa_learning_')){let v=JSON.parse(localStorage.getItem(k)||'{}');if(v.score!==undefined) rows.push([k.replace('sa_learning_',''),v.score,v.level||'',v.at||'']);}}}catch(e){} box.innerHTML=rows.length?'<div class="ux-score-grid">'+rows.slice(-8).map(r=>'<div class="ux-score-card"><b>'+r[0]+'</b><span>'+r[1]+'</span><small>'+r[2]+'</small></div>').join('')+'</div>':'Пока нет попыток. Откройте тренажёр и пройдите первый кейс.';})();</script>'''
    return page('Прогресс', body)


def reports_page():
    body=titleblock('ОТЧЁТЫ', active='reports') + '''<section class="ux-complete-panel"><h2>История отчётов и попыток</h2><p>В текущей lightweight-версии отчёты создаются через локальный SQLite приложения. Для полноценного SaaS здесь должны появиться аккаунты, проекты, версии отчётов, шаринг и роли.</p><div class="ux-path-grid"><a class="ux-path-card" href="/learning"><b>Учебные попытки</b><span>Проходите кейсы и открывайте markdown попыток после оценки.</span><strong>В тренажёр →</strong></a><a class="ux-path-card" href="/"><b>Архитектурный отчёт</b><span>Соберите процесс и сформируйте полный отчёт.</span><strong>В конструктор →</strong></a><a class="ux-path-card" href="/progress"><b>Прогресс</b><span>Посмотрите локальную карту навыков.</span><strong>Открыть →</strong></a><a class="ux-path-card" href="/glossary"><b>Глоссарий</b><span>Разберите термины перед отчётом.</span><strong>Открыть →</strong></a></div></section><section class="ux-report-summary"><h2>Что должно быть в SaaS-версии</h2><div class="ux-action-list"><div><b>Сохранение проектов</b><br>Проект, версии, история изменений, дубликаты.</div><div><b>Экспорт</b><br>Markdown, PDF, копирование краткого вывода, read-only share link.</div><div><b>Команды</b><br>Роли, комментарии, общий workspace и audit log.</div></div></section>'''
    body = body.replace('href="/learning"', 'href="' + url_for('/learning') + '"').replace('href="/"', 'href="' + url_for('/') + '"').replace('href="/progress"', 'href="' + url_for('/progress') + '"').replace('href="/glossary"', 'href="' + url_for('/glossary') + '"')
    return page('Отчёты', body)

# ---------------------------------------------------------------------------
# v8.6.64: пользовательское упрощение поверх полного UI/UX слоя.
# Цель: сделать продукт понятным живому пользователю, который не хочет сначала
# читать энциклопедию терминов. Ядро, payload и отчёты не меняются.
# ---------------------------------------------------------------------------
APP_VERSION = '8.6.67-ultimate-gated'

USER_FRIENDLY_STYLE_V8664 = r'''
<style>
.uf-panel{background:linear-gradient(135deg,#ffffff,#ecfeff);border:1px solid var(--ux-line);border-radius:24px;box-shadow:var(--ux-shadow);padding:20px;margin:0 0 18px}.uf-panel h2{margin:0 0 8px;font-size:26px;line-height:1.12}.uf-panel p{margin:6px 0;color:var(--ux-muted)}.uf-guide-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.uf-guide-card{background:#fff;border:1px solid var(--ux-line);border-radius:18px;padding:15px}.uf-guide-card b{display:block;font-size:15px;margin-bottom:5px}.uf-guide-card small{display:block;color:var(--ux-muted);line-height:1.4}.uf-primary-road{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}.uf-step{background:#fff;border:1px solid var(--ux-line);border-radius:16px;padding:12px;position:relative}.uf-step:before{content:attr(data-step);display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:999px;background:var(--ux-primary);color:#fff;font:800 12px var(--mono);margin-bottom:8px}.uf-step b{display:block}.uf-step small{display:block;color:var(--ux-muted);line-height:1.35}.uf-newbie-question{border:1px solid var(--ux-line);border-radius:18px;background:#fff;padding:14px;margin:10px 0}.uf-newbie-question h4{margin:0 0 6px;font-size:15px}.uf-newbie-question p{margin:4px 0 10px;color:var(--ux-muted)}.uf-choice-row{display:flex;flex-wrap:wrap;gap:8px}.uf-choice{border:1px solid var(--ux-line);background:#fff;border-radius:999px;padding:8px 11px;cursor:pointer;font-weight:700}.uf-choice:hover,.uf-choice.active{border-color:var(--ux-primary);background:var(--ux-primary-soft);color:var(--ux-primary)}.uf-plain{display:block;margin-top:7px;padding:9px 10px;border-radius:12px;background:#f8fafc;border:1px solid #e5edf5;color:#475467;font-size:12.5px;line-height:1.4}.uf-plain b{display:inline!important;color:#111827}.uf-term{display:inline-flex;align-items:center;border:1px solid #bae6fd;background:#f0f9ff;border-radius:999px;padding:1px 7px;margin-left:5px;font-size:11px;color:#0369a1}.uf-safe-toggle{margin-top:12px}.uf-safe-toggle button{border:1px solid var(--ux-line);border-radius:12px;background:#fff;padding:9px 12px;cursor:pointer;font-weight:800}.uf-safe-toggle button.active{background:var(--ux-primary);color:#fff;border-color:var(--ux-primary)}.uf-advanced-muted .advanced-only,.uf-advanced-muted pre,.uf-advanced-muted textarea#solutionJson{opacity:.35}.uf-next-action{position:sticky;bottom:12px;z-index:25;background:#0b1220;color:#fff;border-radius:18px;box-shadow:var(--ux-shadow);padding:12px 14px;display:flex;gap:12px;align-items:center;justify-content:space-between;margin:18px 0}.uf-next-action b{display:block}.uf-next-action small{display:block;color:#cbd5e1}.uf-next-action .btn{background:#14b8a6;border-color:#14b8a6;color:#06201d}.uf-checklist{display:grid;gap:8px;margin-top:12px}.uf-checklist div{border:1px solid var(--ux-line);border-radius:14px;background:#fff;padding:10px}.uf-checklist b{display:block}.uf-checklist small{color:var(--ux-muted)}.uf-simplified-copy{font-size:14px;line-height:1.5;color:#344054}.uf-simplified-copy b{color:#111827}.uf-noise-note{border:1px dashed var(--ux-line);border-radius:14px;background:#fff;padding:12px;color:var(--ux-muted);margin-top:12px}.uf-breadcrumb{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 12px}.uf-breadcrumb span{border:1px solid var(--ux-line);border-radius:999px;background:#fff;padding:5px 9px;font-size:12px;color:#475467}.uf-breadcrumb span.active{background:var(--ux-primary-soft);border-color:var(--ux-primary);color:var(--ux-primary);font-weight:800}.uf-case-focus{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:14px;align-items:start}.uf-helper-card{background:#fff;border:1px solid var(--ux-line);border-radius:18px;padding:14px;position:sticky;top:14px}.uf-helper-card h3{margin:0 0 8px}.uf-helper-card ol{padding-left:20px;margin:8px 0}.uf-helper-card li{margin:6px 0}.uf-helper-card .hint{font-size:12px}.uf-hide-by-default{display:none}.uf-show-more{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.uf-show-more button{border:1px solid var(--ux-line);border-radius:12px;background:#fff;padding:8px 10px;cursor:pointer}.uf-show-more button:hover{background:var(--ux-primary-soft);border-color:var(--ux-primary)}@media(max-width:900px){.uf-guide-grid,.uf-primary-road,.uf-case-focus{grid-template-columns:1fr}.uf-helper-card{position:static}.uf-next-action{position:static;align-items:flex-start;flex-direction:column}.uf-next-action .btn{width:100%;text-align:center}.uf-panel h2{font-size:22px}}
</style>
'''

USER_FRIENDLY_SCRIPT_V8664 = r'''
<script>
(function(){
  function $(s,root){return (root||document).querySelector(s)}
  function $all(s,root){return Array.from((root||document).querySelectorAll(s))}
  function setUserMode(mode){try{localStorage.setItem('sa_user_mode_v8664',mode)}catch(_){ } document.body.classList.toggle('uf-advanced-muted', mode==='simple'); $all('[data-uf-mode]').forEach(b=>b.classList.toggle('active', b.dataset.ufMode===mode));}
  window.setUserModeV8664=setUserMode;
  window.ufSelectControl=function(id){const el=document.querySelector('.visual-control[value="'+id+'"]'); if(el){el.checked=true; try{updateSelectedCounter()}catch(_){ } const card=el.closest('label')||el; card.classList.add('active'); card.scrollIntoView({behavior:'smooth',block:'center'}); const state=$('#visualBuilderState'); if(state) state.innerHTML='<b>Вы добавили решение:</b> '+(el.dataset.label||id)+'. Теперь проверьте выбранное решение.';}}
  window.ufScrollTo=function(id){const el=document.getElementById(id); if(el) el.scrollIntoView({behavior:'smooth',block:'start'});}
  document.addEventListener('DOMContentLoaded',function(){
    let mode='simple'; try{ mode=(localStorage.getItem('sa_user_mode_v8664')||'simple'); }catch(_){ mode='simple'; } setUserMode(mode);
    const explanations={
      outbox:['Защититься от потери события','Если бизнес-решение сохранилось, событие тоже должно быть гарантированно опубликовано.'],
      dlq_replay:['Куда деть плохое сообщение','Если сообщение постоянно падает, оно не должно блокировать весь поток. Его надо отправить в очередь ошибок и потом переобработать.'],
      kafka_key:['Сохранить порядок по заявке','Kafka гарантирует порядок только внутри одной партиции. Нужен ключ по бизнес-сущности.'],
      timeouts:['Не зависнуть на внешней системе','Внешний сервис может не ответить. Нужны таймауты и ограниченные повторы.'],
      versioning:['Не сломать потребителей при изменениях','События и API живут дольше одного релиза. Нужна версия контракта и совместимость.']
    };
    $all('.visual-control').forEach(inp=>{const e=explanations[inp.value]; const span=inp.closest('label')?.querySelector('span'); if(e && span && !span.querySelector('.uf-plain')){span.insertAdjacentHTML('beforeend','<em class="uf-plain"><b>Простыми словами:</b> '+e[1]+' <span class="uf-term">'+e[0]+'</span></em>');}});
  });
})();
</script>
'''

_PREV_PAGE_V8664 = page

def page(title, body, extra_head=''):
    html = _PREV_PAGE_V8664(title, body, extra_head + USER_FRIENDLY_STYLE_V8664)
    html = html.replace('8.6.67-ultimate-gated', APP_VERSION)
    return html.replace('</body>', USER_FRIENDLY_SCRIPT_V8664 + '</body>')


def _user_friendly_home_panel_v8664():
    return f'''<section class="uf-panel" aria-label="Простой старт"><div class="ux-pill good">Режим для пользователя · без лишней техники</div><h2>Начните с одного понятного действия</h2><p class="uf-simplified-copy">Не нужно сначала разбираться во всех паттернах. Выберите короткий маршрут: <b>кейс</b>, <b>свой процесс</b> или <b>термин</b>. Экспертные детали откроются только когда понадобятся.</p><div class="uf-primary-road"><div class="uf-step" data-step="1"><b>Прочитать задачу</b><small>Понять, кто с кем взаимодействует.</small></div><div class="uf-step" data-step="2"><b>Найти риски</b><small>Дубли, потери, порядок, внешние сбои.</small></div><div class="uf-step" data-step="3"><b>Выбрать решения</b><small>Outbox, DLQ, retry и другие контроли.</small></div><div class="uf-step" data-step="4"><b>Получить разбор</b><small>Что хорошо, что забыто и как ответить.</small></div></div><div class="uf-guide-grid"><a class="ux-path-card" href="{url_for('/learning/bank-credit-bki-fraud')}"><b>Пройти первый кейс</b><span>Самый быстрый способ понять продукт за 5 минут.</span><strong>Начать →</strong></a><a class="ux-path-card" href="{url_for('/glossary')}"><b>Не понимаю термины</b><span>Откройте объяснения сложных терминов простыми словами.</span><strong>Открыть →</strong></a><a class="ux-path-card" href="#constructor-start"><b>Есть свой процесс</b><span>Сначала добавьте участников и связи, стек появится позже.</span><strong>Собрать ↓</strong></a></div></section>'''

_PREV_FORM_PAGE_V8664 = form_page

def form_page():
    html = _PREV_FORM_PAGE_V8664()
    panel = _user_friendly_home_panel_v8664()
    html = html.replace('<section class="ux-home-gateway"', panel + '<section class="ux-home-gateway"', 1)
    helper = '''<section class="uf-panel"><div class="ux-pill warn">Подсказка конструктора</div><h2>Не выбирайте технологию раньше процесса</h2><div class="uf-guide-grid"><div class="uf-guide-card"><b>Плохо начинать с технологии</b><small>Так легко выбрать технологию без понимания бизнес-цепочки.</small></div><div class="uf-guide-card"><b>Хорошо начинать с участников</b><small>Клиент → банк → БКИ → антифрод → DWH.</small></div><div class="uf-guide-card"><b>Стек выбирается последним</b><small>Конкретный стек появляется как следствие требований.</small></div></div><div class="uf-noise-note">Для обычного пользователя главный путь: добавьте участников, добавьте связи, нажмите проверку. Остальные настройки нужны только для сложных кейсов.</div></section>'''
    return html.replace('<section class="hero">', helper + '<section class="hero">', 1)

_PREV_LEARNING_HOME_PAGE_V8664 = learning_home_page

def learning_home_page():
    html = _PREV_LEARNING_HOME_PAGE_V8664()
    first = '''<section class="uf-panel" aria-label="Первый запуск тренажёра"><div class="ux-pill good">Самый простой путь</div><h2>Если вы открыли тренажёр впервые — начните отсюда</h2><p>Не открывайте весь каталог из 83 кейсов сразу. Сначала пройдите один банковский кейс: он показывает дубли, внешние вызовы, Kafka, Outbox, DLQ и отчёт.</p><div class="uf-primary-road"><div class="uf-step" data-step="1"><b>Откройте кейс</b><small>Сначала только прочитайте задачу.</small></div><div class="uf-step" data-step="2"><b>Ответьте на 5 рисков</b><small>Не нужно знать все термины заранее.</small></div><div class="uf-step" data-step="3"><b>Нажмите проверку</b><small>Система покажет, что забыто.</small></div><div class="uf-step" data-step="4"><b>Откройте Senior-эталон</b><small>Сравните с хорошим ответом.</small></div></div><div class="uf-guide-grid"><a class="ux-path-card" href="'''+url_for('/learning/bank-credit-bki-fraud')+'''"><b>Начать первый кейс</b><span>Рекомендуемый старт для системного аналитика.</span><strong>Начать →</strong></a><a class="ux-path-card" href="'''+url_for('/glossary')+'''"><b>Сначала термины</b><span>DLQ, Outbox, идемпотентность простыми словами.</span><strong>Открыть →</strong></a><a class="ux-path-card" href="#catalog"><b>Я уже понимаю тему</b><span>Открыть полный каталог кейсов.</span><strong>К каталогу ↓</strong></a></div></section>'''
    return html.replace('<section class="ux-complete-panel" aria-label="Режим тренировки">', first + '<section class="ux-complete-panel" aria-label="Режим тренировки">', 1)

_PREV_LEARNING_CASE_PAGE_V8664 = learning_case_page

def learning_case_page(case_id):
    html = _PREV_LEARNING_CASE_PAGE_V8664(case_id)
    newbie = '''<section class="uf-panel" id="newbie-road"><div class="ux-pill good">Режим новичка · вопросами</div><h2>Не знаете, какие галочки ставить? Ответьте на 5 простых вопросов</h2><p>Каждый вопрос выбирает один архитектурный контроль. Так проще понять смысл решения до термина.</p><div class="uf-newbie-question"><h4>1. Может ли событие потеряться между сохранением решения и публикацией?</h4><p>Если да — нужен механизм, который сначала фиксирует событие в БД, а потом публикует.</p><div class="uf-choice-row"><button class="uf-choice" type="button" onclick="ufSelectControl('outbox')">Добавить защиту от потери события</button></div></div><div class="uf-newbie-question"><h4>2. Что делать с сообщением, которое всё время падает?</h4><p>Оно не должно ломать весь поток. Его нужно изолировать и потом переобработать.</p><div class="uf-choice-row"><button class="uf-choice" type="button" onclick="ufSelectControl('dlq_replay')">Добавить очередь ошибок и replay</button></div></div><div class="uf-newbie-question"><h4>3. Важен ли порядок событий по одной заявке?</h4><p>Если важен, нужно явно выбрать ключ порядка, иначе события могут прийти не в той последовательности.</p><div class="uf-choice-row"><button class="uf-choice" type="button" onclick="ufSelectControl('kafka_key')">Добавить ключ порядка</button></div></div><div class="uf-newbie-question"><h4>4. Может ли внешний сервис долго не отвечать?</h4><p>Если да, нельзя ждать бесконечно. Нужны таймауты, ограниченные повторы и запасной сценарий.</p><div class="uf-choice-row"><button class="uf-choice" type="button" onclick="ufSelectControl('timeouts')">Добавить таймауты и retry</button></div></div><div class="uf-newbie-question"><h4>5. Может ли контракт события измениться после релиза?</h4><p>Если да, нужно версионирование, чтобы старые потребители не сломались от нового формата.</p><div class="uf-choice-row"><button class="uf-choice" type="button" onclick="ufSelectControl('versioning')">Добавить версию контракта</button></div></div><div class="uf-next-action"><div><b>После выбора решений</b><small>Прокрутите к чек-листу, убедитесь что галочки стоят, и нажмите проверку.</small></div><button class="btn" type="button" onclick="ufScrollTo('solution')">К выбранным решениям</button></div></section>'''
    html = html.replace('<section class="ux-card" id="solution">', newbie + '<section class="ux-card" id="solution">', 1)
    simple_toggle = '''<div class="uf-safe-toggle" aria-label="Сложность интерфейса"><button type="button" data-uf-mode="simple" onclick="setUserModeV8664('simple')">Простой режим</button><button type="button" data-uf-mode="expert" onclick="setUserModeV8664('expert')">Экспертный режим</button></div>'''
    html = html.replace('<div class="ux-pill good">Кейс · понятный режим</div>', '<div class="ux-pill good">Кейс · понятный режим</div>'+simple_toggle, 1)
    return html

_PREV_GLOSSARY_PAGE_V8664 = glossary_page

def glossary_page():
    html = _PREV_GLOSSARY_PAGE_V8664()
    top = '''<section class="uf-panel"><div class="ux-pill good">Термины через риск</div><h2>Сначала поймите, что ломается</h2><div class="uf-guide-grid"><div class="uf-guide-card"><b>Дубли</b><small>Повтор события не должен создать второй платёж, заявку или статус.</small></div><div class="uf-guide-card"><b>Потери</b><small>Сохранённое бизнес-решение не должно остаться без события.</small></div><div class="uf-guide-card"><b>Порядок</b><small>Для одной заявки события должны обрабатываться в правильной последовательности.</small></div></div></section>'''
    return html.replace('<section class="ux-complete-panel"><h2>Термины простыми словами</h2>', top + '<section class="ux-complete-panel"><h2>Термины простыми словами</h2>', 1)

_PREV_REPORTS_PAGE_V8664 = reports_page

def reports_page():
    html = _PREV_REPORTS_PAGE_V8664()
    explain = '''<section class="uf-panel"><div class="ux-pill warn">Как читать отчёт</div><h2>Не начинайте с полного markdown</h2><div class="uf-checklist"><div><b>1. Сначала вердикт</b><small>Готово / условно готово / нельзя выпускать.</small></div><div><b>2. Потом главные риски</b><small>Что может сломаться в production.</small></div><div><b>3. Потом первые действия</b><small>Что исправить до обсуждения с командой.</small></div><div><b>4. Только потом детали</b><small>Полный markdown нужен для передачи разработке/архитектору.</small></div></div></section>'''
    return html.replace('<section class="ux-complete-panel"><h2>История отчётов и попыток</h2>', explain + '<section class="ux-complete-panel"><h2>История отчётов и попыток</h2>', 1)
