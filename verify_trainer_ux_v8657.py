# -*- coding: utf-8 -*-
"""Smoke-проверка упрощённого UX тренажёра v8.6.57."""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import closing, suppress
from urllib.request import urlopen


def free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_http(url: str, timeout: float = 20.0) -> None:
    start = time.time()
    last = None
    while time.time() - start < timeout:
        try:
            with urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except Exception as exc:  # pragma: no cover
            last = exc
        time.sleep(0.25)
    raise RuntimeError(f"server did not start: {last}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright, expect
    except Exception as exc:
        print(f"SKIP: playwright unavailable: {exc}")
        return 0

    port = free_port()
    app_dir = tempfile.mkdtemp(prefix="sa_trainer_ux_")
    env = os.environ.copy()
    env.update({"HOST": "127.0.0.1", "PORT": str(port), "APP_DIR": app_dir})
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=os.getcwd(), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    errors: list[str] = []
    try:
        wait_http(f"http://127.0.0.1:{port}/health")
        with urlopen(f"http://127.0.0.1:{port}/learning", timeout=5) as r:
            home_html = r.read().decode("utf-8")
        with urlopen(f"http://127.0.0.1:{port}/learning/bank-credit-bki-fraud", timeout=5) as r:
            case_html = r.read().decode("utf-8")
        fetch_stub = """<script>
        window.fetch = async function(url, opts) {
          const u = String(url);
          if (u.includes('/api/learning/progress')) {
            return new Response(JSON.stringify({ok:true, attempt_count:0, solved_case_count:0, case_count:83, badges:[], weak_skills:[]}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          if (u.includes('/api/learning/visual-payload')) {
            const params = new URLSearchParams(u.split('?')[1] || '');
            const controls = (params.get('controls') || '').split(',').filter(Boolean);
            return new Response(JSON.stringify({ok:true, selected_count:controls.length, control_count:5, payload:{meta:{name:'ui-test'}, systems:[], steps:[]}}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          if (u.includes('/api/learning/evaluate')) {
            return new Response(JSON.stringify({ok:true, learning_score:6.2, solution_score:6.2, learning_level:'Нужно доработать', quick_summary:{top_errors:['Не указан outbox'], quick_fixes:['Добавить outbox и идемпотентность']}, report_markdown:'# test', html:'<p>Полный разбор</p>'}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          if (u.includes('/api/learning/hints')) {
            return new Response(JSON.stringify({ok:true, hints:['Сначала подумайте про дубли и отказы.']}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          if (u.includes('/api/learning/reference')) {
            return new Response(JSON.stringify({ok:true, production:{description:'Эталон', steps:['Шаг 1']}, acceptance_criteria:['Критерий']}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          if (u.includes('/api/learning/interview')) {
            return new Response(JSON.stringify({ok:true, opening_prompt:'Вопрос', questions:[{question:'Почему Kafka?', expected:['порядок']}]}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          return new Response('{}', {status:200, headers:{'Content-Type':'application/json'}});
        };
        </script>"""
        home_html = home_html.replace('</head>', fetch_stub + '</head>')
        case_html = case_html.replace('</head>', fetch_stub + '</head>')
        with sync_playwright() as p:
            executable = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
            kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
            if executable:
                kwargs["executable_path"] = executable
            browser = p.chromium.launch(**kwargs)
            page = browser.new_page(viewport={"width": 1366, "height": 900})
            page.set_default_timeout(10000)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.set_content(home_html, wait_until="load")
            expect(page.get_by_text("Как пользоваться")).to_be_visible()
            expect(page.get_by_text("1. Выбери кейс")).to_be_visible()
            expect(page.get_by_role("link", name="Открыть и решить").first).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            page.set_content(case_html, wait_until="load")
            expect(page.get_by_text("Поймите задачу")).to_be_visible()
            expect(page.get_by_text("Выберите, что добавите в архитектуру")).to_be_visible()
            expect(page.get_by_role("button", name="Проверить выбранное решение")).to_be_visible()
            assert page.locator(".visual-control:checked").count() == 0
            total = page.locator(".visual-control").count()
            assert total >= 3
            page.locator(".trainer-control").nth(0).click()
            page.locator(".trainer-control").nth(1).click()
            expect(page.locator("#selectedCounter")).to_contain_text("Выбрано: 2")
            page.get_by_role("button", name="Проверить выбранное решение").click()
            expect(page.locator("#learningResult")).to_contain_text("Главные ошибки", timeout=15000)
            assert page.locator("#solutionJson").input_value().strip().startswith("{")
            assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            mobile.set_content(case_html, wait_until="load")
            expect(mobile.get_by_text("Проверить выбранное решение")).to_be_visible()
            assert mobile.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")
            browser.close()
        assert not errors, "JS/browser errors: " + "; ".join(errors[:5])
        print("OK: trainer UX v8.6.57 browser smoke passed")
        return 0
    finally:
        proc.terminate()
        with suppress(Exception):
            proc.wait(timeout=5)
        if proc.poll() is None:
            proc.kill()
        shutil.rmtree(app_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
