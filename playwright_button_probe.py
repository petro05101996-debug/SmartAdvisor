from pathlib import Path
from playwright.sync_api import sync_playwright
html = Path('/tmp/index855.html').read_text(encoding='utf-8')
stub = """<script>
window.__submittedPayloads=[];
const __origFetch = window.fetch;
window.fetch = async function(url, opts){
  if(String(url).includes('/api/analyze')){
    try { window.__submittedPayloads.push(JSON.parse(opts && opts.body || '{}')); } catch(e) { window.__submittedPayloads.push({parseError:String(e)}); }
    return new Response(JSON.stringify({ok:true,id:'ui-probe-run'}), {status:200, headers:{'Content-Type':'application/json'}});
  }
  return __origFetch(url, opts);
};
</script>"""
html = html.replace('</head>', stub + '</head>')
checks=[]
def ok(n,d=''): checks.append((n,'OK',d))
def fail(n,d=''): checks.append((n,'FAIL',d))
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':390,'height':844}); page.set_default_timeout(2500)
    console=[]; page.on('console', lambda msg: console.append((msg.type,msg.text))); page.on('pageerror', lambda e: console.append(('pageerror',str(e))))
    try:
        page.set_content(html, wait_until='domcontentloaded'); page.wait_for_timeout(200)
        ok('open_page', page.title())
        ok('button_count', str(page.locator('button').count())) if page.locator('button').count()>=70 else fail('button_count', str(page.locator('button').count()))
        page.locator('[data-action="mode"][data-mode="advanced"]').click(); page.wait_for_timeout(100); ok('advanced_mode_click')
        ok('advanced_fields_visible') if page.locator('.advanced-only').first.is_visible() else fail('advanced_fields_visible')
        page.locator('[data-action="mode"][data-mode="quick"]').click(); page.wait_for_timeout(100); ok('quick_mode_click')
        page.locator('[data-action="compose-chain"]').click(); page.wait_for_timeout(100); ok('compose_chain_click')
        for group,value in [('start','incoming_request'),('activity','call_external'),('timing','later'),('result','save_forward'),('systems','4')]:
            loc=page.locator(f'[data-action="compose-choice"][data-compose-group="{group}"][data-value="{value}"]')
            if not loc.first.is_visible():
                try: page.locator('[data-action="wizard-next"]').click(); page.wait_for_timeout(100)
                except Exception: pass
            loc.click(); page.wait_for_timeout(150); ok(f'wizard_choice_{group}_{value}')
        steps=page.locator('[data-step-id]').count(); ok('wizard_build_steps', str(steps)) if steps>0 else fail('wizard_build_steps','0')
        for mod in ['outbox_inbox','retry_dlq','manual_recon','fanin','enrichment','legacy','dwh','contract','audit','security']:
            page.locator(f'[data-action="module"][data-module="{mod}"]').click(); page.wait_for_timeout(30)
        ok('all_modules_click')
        steps_after=page.locator('[data-step-id]').count(); ok('modules_add_steps', f'{steps}->{steps_after}') if steps_after>=steps else fail('modules_add_steps', f'{steps}->{steps_after}')
        page.locator('[data-action="mode"][data-mode="advanced"]').click(); page.wait_for_timeout(100); ok('advanced_mode_second_click')
        if page.locator('[data-action="safe-all"]').count(): page.locator('[data-action="safe-all"]').click(); page.wait_for_timeout(50); ok('safe_all_click')
        for tpl in ['rest','kafka','db','webhook','batch','cdc','manual','validation']:
            page.locator(f'[data-action="template"][data-template="{tpl}"]').click(); page.wait_for_timeout(25)
        ok('all_template_buttons_click')
        for kind in ['internal','external','broker','db','analytics','legacy']:
            page.locator(f'[data-action="add-system"][data-system-kind="{kind}"]').click(); page.wait_for_timeout(25)
        ok('all_add_system_buttons_click')
        for sel,name in [('[data-action="move-step"][data-dir="1"]','move_down_click'),('[data-action="move-step"][data-dir="-1"]','move_up_click'),('[data-action="duplicate-step"]','duplicate_click'),('[data-action="insert-before"]','insert_before_click'),('[data-action="insert-after"]','insert_after_click'),('[data-action="safe-step"]','safe_step_click')]:
            if page.locator(sel).count(): page.locator(sel).first.click(); page.wait_for_timeout(80); ok(name)
            else: fail(name,'not found')
        page.evaluate('document.querySelectorAll("details").forEach(d=>d.open=true)'); page.wait_for_timeout(80)
        if page.locator('[data-action="set-channel"][data-channel="rabbitmq"]').count(): page.locator('[data-action="set-channel"][data-channel="rabbitmq"]').first.click(); page.wait_for_timeout(80); ok('manual_channel_rabbit_click')
        else: fail('manual_channel_rabbit_click','not found')
        if page.locator('[data-action="auto-channel"]').count(): page.locator('[data-action="auto-channel"]').first.click(); page.wait_for_timeout(80); ok('reset_auto_channel_click')
        else: fail('reset_auto_channel_click','not found')
        page.locator('[data-action="submit"]').click(); page.wait_for_timeout(700)
        submitted=page.evaluate('window.__submittedPayloads.length')
        ok('submit_fetch_called', str(submitted)) if submitted>0 else fail('submit_fetch_called','0')
        payload=page.evaluate('window.__submittedPayloads[window.__submittedPayloads.length-1]') if submitted else {}
        sysnames=set([s.get('name') for s in payload.get('systems',[])])
        ref=[]
        for idx,s in enumerate(payload.get('steps',[]), start=1):
            for k in ['source_system','system','target_system']:
                v=s.get(k)
                if v and v not in sysnames: ref.append(f'step {idx} {k}={v}')
            deps=[]
            for part in str(s.get('depends_on','')).replace(';',',').split(','):
                part=part.strip()
                if part.isdigit(): deps.append(int(part))
            if idx in deps: ref.append(f'step {idx} self_dep')
            for d in deps:
                if d<1 or d>len(payload.get('steps',[])): ref.append(f'step {idx} bad_dep {d}')
        ok('payload_references_valid', f"steps={len(payload.get('steps',[]))}, systems={len(payload.get('systems',[]))}") if not ref else fail('payload_references_valid', '; '.join(ref[:10]))
        errs=[x for x in console if x[0] in ('error','pageerror')]
        ok('console_errors','0') if not errs else fail('console_errors', str(errs[:5]))
    except Exception as e:
        fail('probe_exception', repr(e))
    finally:
        browser.close()
for n,s,d in checks: print(f'{s}\t{n}\t{d}')
print('SUMMARY', sum(1 for _,s,_ in checks if s=='OK'), 'ok', sum(1 for _,s,_ in checks if s!='OK'), 'fail')
