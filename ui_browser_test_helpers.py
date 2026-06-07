import json
import os
import socket
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from urllib.request import urlopen

import pytest


def free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for_server(url, proc, timeout=20):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ''
            raise RuntimeError(f'server exited: {proc.returncode}\n{out}')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last = exc
        time.sleep(0.2)
    raise RuntimeError(f'server did not start: {last}')


@contextmanager
def running_app():
    port = free_port()
    env = os.environ.copy()
    env.update({'HOST': '127.0.0.1', 'PORT': str(port)})
    proc = subprocess.Popen(
        [sys.executable, 'integration_architect_pro.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        url = f'http://127.0.0.1:{port}/'
        wait_for_server(url, proc)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@contextmanager
def chromium_page(url):
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ModuleNotFoundError as exc:
        pytest.skip(f'Playwright is not installed in this environment: {exc}')
    js_errors = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except PlaywrightError as exc:
            pytest.skip(f'Chromium executable is not installed in this environment: {exc}')
        page = browser.new_page()
        page.on('console', lambda msg: js_errors.append(f'console {msg.type}: {msg.text}') if msg.type == 'error' else None)
        page.on('pageerror', lambda exc: js_errors.append(f'pageerror: {exc}'))
        page.goto(url, wait_until='networkidle')
        try:
            yield page, js_errors
        finally:
            browser.close()


def active_step(page):
    return page.locator('section.constructor-screen.is-active').get_attribute('data-constructor-screen')


def click_next(page, expected_step=None):
    page.locator('#constructorNext').click()
    if expected_step is not None:
        page.locator(f"section.constructor-screen.is-active[data-constructor-screen='{expected_step}']").wait_for()


def start_flow(page, business_case=None):
    page.get_by_role('button', name='Начать').click()
    page.locator("section.constructor-screen.is-active[data-constructor-screen='0']").wait_for()
    if business_case:
        page.locator(f"[data-business-case='{business_case}']").click()


def hidden_json(page, selector):
    raw = page.locator(selector).input_value()
    assert raw.strip(), f'{selector} should not be empty'
    return json.loads(raw)


def go_to_result_with_preset(page, preset='deferred_application'):
    start_flow(page)
    click_next(page, 1)
    page.locator(f"[data-business-preset='{preset}']").click()
    click_next(page, 2)
    click_next(page, 3)
    click_next(page, 4)
    click_next(page, 5)
