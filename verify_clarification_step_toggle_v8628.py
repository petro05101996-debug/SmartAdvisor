from playwright.sync_api import sync_playwright, expect
import re
import shutil
import ui

html = ui.form_page()

def launch(p):
    try:
        return p.chromium.launch(headless=True, args=["--no-sandbox"])
    except Exception as first:
        system = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if not system:
            raise RuntimeError(f"Chromium is not available: {first}")
        return p.chromium.launch(headless=True, executable_path=system, args=["--no-sandbox", "--disable-dev-shm-usage"])

with sync_playwright() as p:
    browser = launch(p)
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(7000)
    page.set_content(html, wait_until="load")

    for name in ["Добавить инициатора", "Добавить сервис процесса", "Добавить внешнюю систему", "Добавить хранилище состояния", "Добавить аналитику"]:
        page.get_by_role("button", name=name).click()
    page.get_by_role("button", name="Дальше: связи между участниками").click()

    def add_link(src_idx, tgt_idx, action, timing, result):
        page.locator('#interactionSource').select_option(index=src_idx)
        page.locator('#interactionTarget').select_option(index=tgt_idx)
        page.locator('#interactionAction').select_option(action)
        page.locator('#interactionTiming').select_option(timing)
        page.locator('#interactionResult').select_option(result)
        page.get_by_role("button", name="Добавить связь в цепочку").click()

    add_link(1, 2, 'send_data', 'sync', 'pass_next')
    add_link(2, 3, 'request_data', 'sync', 'save')
    add_link(2, 4, 'save', 'sync', 'save')
    add_link(4, 5, 'compare', 'background', 'check')
    page.get_by_role("button", name="Дальше: уточнения").click()

    # Одинаковые варианты могут встречаться в разных шагах, но data-module должен быть уникальным для строгих селекторов.
    assert page.locator('[data-action="module"][data-module="fast_read"]').count() == 1
    assert page.locator('[data-action="module"][data-module-kind="fast_read"]').count() >= 2

    first = page.locator('[data-action="module"][data-module-kind="fast_read"][data-step-index="1"]')
    second = page.locator('[data-action="module"][data-module-kind="fast_read"][data-step-index="2"]')

    first.click()
    expect(first).to_have_class(re.compile(r'.*active.*'))
    expect(second).not_to_have_class(re.compile(r'.*active.*'))

    first.click()
    expect(first).not_to_have_class(re.compile(r'.*active.*'))

    second.click()
    expect(second).to_have_class(re.compile(r'.*active.*'))
    expect(first).not_to_have_class(re.compile(r'.*active.*'))

    # В одной группе у одного шага выбор взаимоисключающий: REST -> gRPC снимает REST.
    rest = page.locator('[data-action="module"][data-module-kind="sync_external_api"][data-step-index="0"]')
    grpc = page.locator('[data-action="module"][data-module-kind="fast_internal_call"][data-step-index="0"]')
    rest.click()
    expect(rest).to_have_class(re.compile(r'.*active.*'))
    grpc.click()
    expect(grpc).to_have_class(re.compile(r'.*active.*'))
    expect(rest).not_to_have_class(re.compile(r'.*active.*'))

    # Снятие повторным нажатием.
    grpc.click()
    expect(grpc).not_to_have_class(re.compile(r'.*active.*'))

    browser.close()

print('CLARIFICATION_STEP_TOGGLE_v8628 ok')
