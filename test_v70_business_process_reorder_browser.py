import json
import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from urllib.request import urlopen

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')


def _free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _wait(url, proc, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f'server exited: {proc.returncode}')
        try:
            with urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return
        except Exception as e:
            last = e
        time.sleep(0.2)
    raise RuntimeError(f'not started: {last}')


def test_business_process_reorder_browser():
    try:
        from playwright.sync_api import sync_playwright, Error as PlaywrightError
    except ModuleNotFoundError as exc:
        pytest.skip(f'Playwright is not installed in this environment: {exc}')
    port = _free_port()
    env = os.environ.copy(); env.update({'HOST': '127.0.0.1', 'PORT': str(port)})
    proc = subprocess.Popen([sys.executable, 'integration_architect_pro.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    try:
        url = f'http://127.0.0.1:{port}/'
        _wait(url, proc)
        errors = []
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except PlaywrightError as exc:
                pytest.skip(f'Chromium executable is not installed in this environment: {exc}')
            page = browser.new_page()
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.goto(url, wait_until='networkidle')
            page.get_by_role('button', name='Начать').click()
            page.get_by_role('button', name='Клиент / пользователь создаёт заявку').click()
            page.locator('#constructorNext').click()
            page.locator("section.constructor-screen.is-active[data-constructor-screen='1']").wait_for()
            page.get_by_role('button', name='Заявка с отложенной обработкой').click()
            cards = page.locator('#businessStepList .business-step-card')
            assert cards.count() >= 4
            first_before = cards.nth(0).inner_text()
            second_before = cards.nth(1).inner_text()
            json_before = page.locator('#businessStepsJson').input_value()
            cards.nth(0).locator('[data-step-down]').click()
            assert second_before.split('\n')[1] in cards.nth(0).inner_text()
            assert first_before.split('\n')[1] in cards.nth(1).inner_text()
            json_after = page.locator('#businessStepsJson').input_value()
            assert json_after != json_before
            parsed_after = json.loads(json_after)
            assert [s['order'] for s in parsed_after] == list(range(1, len(parsed_after) + 1))
            cards.nth(1).locator('[data-step-up]').click()
            assert first_before.split('\n')[1] in cards.nth(0).inner_text()
            # Leave a real reordered state for submit/report verification.
            cards.nth(0).locator('[data-step-down]').click()
            submitted_steps = json.loads(page.locator('#businessStepsJson').input_value())
            expected_first = submitted_steps[0]['actorLabel']
            expected_second = submitted_steps[1]['actorLabel']
            assert expected_first != expected_second
            page.locator('#constructorNext').click()
            page.locator('#constructorNext').click()
            page.locator("section.constructor-screen.is-active[data-constructor-screen='3']").wait_for()
            business_scheme = page.locator('#autoSchemeReview').inner_text()
            assert 'Бизнес-процесс' in business_scheme
            assert expected_first in business_scheme
            page.locator('#constructorNext').click()
            page.locator('#constructorNext').click()
            page.locator("section.constructor-screen.is-active[data-constructor-screen='5']").wait_for()
            result_text = page.locator('#resultBusinessProcess').inner_text()
            assert expected_first in result_text
            assert expected_second in result_text
            assert result_text.index(expected_first) < result_text.index(expected_second)
            page.locator('#submitBtn').click()
            page.wait_for_load_state('networkidle')
            full_text = page.locator('body').inner_text()
            assert 'Результат' in full_text
            assert '1. Бизнес-процесс' in full_text
            assert expected_first in full_text
            assert expected_second in full_text
            assert full_text.index(expected_first) < full_text.index(expected_second)
            assert 'Порядок бизнес-шагов учтён' in full_text
            page.get_by_text('Открыть полный отчёт').click()
            markdown_text = page.locator('details.full-report .result').first.inner_text()
            assert '## 1. Бизнес-процесс' in markdown_text
            assert expected_first in markdown_text
            assert expected_second in markdown_text
            assert markdown_text.index(expected_first) < markdown_text.index(expected_second)
            assert 'Порядок бизнес-шагов учтён' in markdown_text
            browser.close()
        assert errors == []
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
