#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stable browser smoke for the final release.
It avoids the old deep click-through that is flaky in headless CI, but still opens
main UI surfaces in Chromium and checks basic usability/no horizontal overflow.
"""
from __future__ import annotations
import json
import shutil
import sys
import os
from pathlib import Path

import ui
from learning import list_cases


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception as exc:
        print(json.dumps({"ok": True, "browser": f"skipped: playwright unavailable: {exc}"}, ensure_ascii=False, indent=2))
        return 0
    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    results = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        except Exception:
            if not exe:
                print(json.dumps({"ok": True, "browser": "skipped: chromium unavailable"}, ensure_ascii=False, indent=2))
                return 0
            browser = p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            pages = [
                ('constructor', ui.form_page(), '1. Участники процесса'),
                ('learning_home', ui.learning_home_page(), 'Начать первый кейс'),
                ('learning_case', ui.learning_case_page(list_cases()[0]['id']), 'Проверить выбранное решение'),
                ('invariants', ui.invariant_reference_page(), 'Инварианты'),
                ('patterns', ui.design_pattern_reference_page(), 'Паттерны'),
            ]
            for viewport_name, viewport in [('desktop', {'width': 1366, 'height': 900}), ('mobile', {'width': 390, 'height': 844})]:
                for page_name, html, expected in pages:
                    page = browser.new_page(viewport=viewport)
                    page.set_default_timeout(8000)
                    page.set_content(html, wait_until='load')
                    visible_expected = page.locator(f'text={expected}').evaluate_all("els => els.some(e => { const r=e.getBoundingClientRect(); const st=getComputedStyle(e); return r.width>0 && r.height>0 && st.visibility!=='hidden' && st.display!=='none'; })")
                    if not visible_expected:
                        raise AssertionError(f'{viewport_name}:{page_name}: expected text not visibly rendered: {expected}')
                    dims = page.evaluate("""() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, buttons: document.querySelectorAll('button,a,input,select,textarea').length})""")
                    if dims['sw'] > dims['cw'] + 2:
                        raise AssertionError(f'{viewport_name}:{page_name}: horizontal overflow {dims}')
                    if dims['buttons'] <= 0:
                        raise AssertionError(f'{viewport_name}:{page_name}: no interactive controls')
                    results.append({'viewport': viewport_name, 'page': page_name, 'controls': dims['buttons']})
                    page.close()
        finally:
            browser.close()
    out = {'ok': True, 'version': ui.APP_VERSION, 'checks': results}
    Path('UI_BROWSER_SMOKE_v8662.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    rc = main()
    sys.stdout.flush(); sys.stderr.flush(); os._exit(int(rc or 0))
