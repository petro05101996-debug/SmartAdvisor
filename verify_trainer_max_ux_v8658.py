# -*- coding: utf-8 -*-
"""Smoke-проверка максимально простого UX тренажёра v8.6.58."""
from __future__ import annotations
import os
import sys
import json, os, sys, shutil
from pathlib import Path

import ui

ROOT = Path(__file__).resolve().parent


def main():
    assert ui.APP_VERSION == '8.6.67-ultimate-gated'
    home = ui.learning_home_page()
    case = ui.learning_case_page('bank-credit-bki-fraud')
    assert 'Максимально простой режим' in home
    assert 'Начать первый кейс' in home
    assert 'Как пользоваться' in home
    assert '<details class="ux-home-fold" id="catalog">' in home
    assert 'ux-bottom-bar' in case
    assert 'Проверить выбранное решение' in case
    assert 'Экспертный режим: JSON решения' in case
    assert case.index('2. Выберите, что добавите в архитектуру') < case.index('Экспертный режим: JSON решения')
    assert 'checked' not in case.split('class="visual-control" value="outbox"', 1)[1].split('>', 1)[0]

    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception as e:
        print(json.dumps({'ok': True, 'browser': 'skipped', 'reason': str(e)}, ensure_ascii=False, indent=2))
        return 0

    exe = shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, executable_path=exe, args=['--no-sandbox', '--disable-dev-shm-usage']) if exe else p.chromium.launch(headless=True, args=['--no-sandbox'])
        except Exception as e:
            print(json.dumps({'ok': True, 'browser': 'skipped', 'reason': str(e)}, ensure_ascii=False, indent=2))
            return 0
        viewports = []
        for name, vp in [('desktop', {'width': 1366, 'height': 900}), ('mobile', {'width': 390, 'height': 844})]:
            page = browser.new_page(viewport=vp)
            page.set_content(home, wait_until='load')
            expect(page.get_by_role('link', name='Начать первый кейс', exact=True)).to_be_visible()
            expect(page.get_by_text('Как пользоваться')).to_be_visible()
            assert page.locator('#caseSearch').is_visible() is False
            home_size = page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert home_size['sw'] <= home_size['cw'] + 2, (name, 'home overflow', home_size)
            page.set_content(case, wait_until='load')
            expect(page.get_by_text('1. Поймите задачу')).to_be_visible()
            expect(page.get_by_text('2. Выберите, что добавите в архитектуру')).to_be_visible()
            expect(page.get_by_role('button', name='Проверить выбранное решение')).to_be_visible()
            assert page.locator('.visual-control:checked').count() == 0
            case_size = page.evaluate("() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})")
            assert case_size['sw'] <= case_size['cw'] + 2, (name, 'case overflow', case_size)
            viewports.append({'viewport': name, 'home_overflow': False, 'case_overflow': False})
            page.close()
        browser.close()
    out = {'ok': True, 'version': ui.APP_VERSION, 'viewports': viewports}
    Path('TRAINER_MAX_UX_VERIFY_v8658.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    rc = main()
    sys.stdout.flush(); sys.stderr.flush(); os._exit(int(rc or 0))
