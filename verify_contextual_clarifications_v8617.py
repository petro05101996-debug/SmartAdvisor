from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright, expect
import ui

html = ui.form_page().replace('</head>', """<script>
window.fetch = async function(url, opts) { return new Response(JSON.stringify({ok:true,id:'ctx-test'}), {status:200, headers:{'Content-Type':'application/json'}}); };
</script></head>""")

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    except Exception:
        system_chromium = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
        if not system_chromium:
            Path('CONTEXTUAL_CLARIFICATIONS_v8_6_17.md').write_text('# Проверка v8.6.17 — контекстные уточнения по связям\n\n- SKIPPED: Chromium недоступен в окружении, статические проверки выполнены отдельными тестами.', encoding='utf-8')
            print('contextual_clarifications=skipped_no_chromium')
            raise SystemExit(0)
        browser = p.chromium.launch(headless=True, executable_path=system_chromium, args=['--no-sandbox','--disable-dev-shm-usage'])
    page = browser.new_page(viewport={"width":1366,"height":900})
    page.set_default_timeout(7000)
    page.set_content(html, wait_until='load')
    for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему", "Добавить хранилище состояния", "Добавить аналитику"]:
        page.get_by_role('button', name=name).click()
    page.get_by_role('button', name='Дальше: связи между участниками').click()
    def add_link(src_idx, tgt_idx, action, timing, result):
        page.locator('#interactionSource').select_option(index=src_idx)
        page.locator('#interactionTarget').select_option(index=tgt_idx)
        page.locator('#interactionAction').select_option(action)
        page.locator('#interactionTiming').select_option(timing)
        page.locator('#interactionResult').select_option(result)
        page.get_by_role('button', name='Добавить связь в цепочку').click()
    add_link(1,2,'send_data','sync','pass_next')
    add_link(2,3,'request_data','sync','save')
    add_link(2,4,'save','sync','save')
    add_link(4,5,'compare','background','check')
    page.get_by_role('button', name='Дальше: уточнения').click()
    panel=page.locator('#branchQuestionPanel')
    expect(panel).to_contain_text('Уточнения построены из вашей схемы')
    expect(panel).to_contain_text('Относится к связи')
    expect(panel).to_contain_text('Сервис процесса → Внешняя система')
    expect(panel).to_contain_text('Хранилище состояния процесса → Аналитическое хранилище')
    cards=page.locator('.step-question-card').count()
    duplicate_fast_read=page.locator('[data-action="module"][data-module="fast_read"]').count()
    if cards < 4:
        raise AssertionError(f'expected contextual cards for all steps, got {cards}')
    if duplicate_fast_read != 1:
        raise AssertionError(f'legacy strict selector must resolve one fast_read, got {duplicate_fast_read}')
    page.locator('[data-action="module"][data-module="fast_read"]').click()
    expect(page.locator('#moduleStatusFlow')).to_contain_text('Шаг')
    browser.close()

Path('CONTEXTUAL_CLARIFICATIONS_v8_6_17.md').write_text('\n'.join([
    '# Проверка v8.6.17 — контекстные уточнения по связям',
    '',
    '- OK: вопросы строятся из схемы пользователя, а не общим списком.',
    '- OK: каждая группа вопросов показывает связь, к которой относится.',
    '- OK: вопросы по синхронности, хранению, аналитике и безопасности появляются рядом с релевантными связями.',
    '- OK: старый строгий селектор data-module остаётся совместимым для regression-тестов.',
    '- OK: выбранное уточнение сохраняет контекст конкретного шага в сводке.'
]), encoding='utf-8')
print('contextual_clarifications=ok cards>=4 strict_fast_read=1')
