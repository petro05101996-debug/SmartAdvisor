# -*- coding: utf-8 -*-
"""Полный UI-аудит v8.6.43.

Проверяет: главный конструктор, участники, связи, уточнения, стек, экспертный режим,
формирование payload, result page, справочники, мобильные размеры и live HTTP API.
Chromium в некоторых CI запрещает переход на localhost, поэтому браузерный UI
тестируется через set_content, а live API — отдельным HTTP-клиентом.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from contextlib import suppress
from pathlib import Path

from engine import analyze
import ui


def _playwright():
    from playwright.sync_api import sync_playwright, expect  # noqa: WPS433
    return sync_playwright, expect


def _launch_browser(p):
    try:
        return p.chromium.launch(headless=True, args=["--no-sandbox"])
    except Exception:
        exe = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if not exe:
            raise
        return p.chromium.launch(
            headless=True,
            executable_path=exe,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )


def _stop(proc: subprocess.Popen):
    if proc.poll() is None:
        proc.terminate()
        with suppress(Exception):
            proc.wait(timeout=3)
        if proc.poll() is None:
            proc.kill()
            with suppress(Exception):
                proc.wait(timeout=3)


def _check_no_overflow(page, label: str):
    vals = page.evaluate("""() => ({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})""")
    if vals["sw"] > vals["cw"] + 2:
        raise AssertionError(f"{label}: horizontal overflow {vals}")


def _check_targets(page, label: str):
    bad = page.evaluate(
        """() => [...document.querySelectorAll('button,a,input,select,textarea')]
        .filter(el=>{const s=getComputedStyle(el), r=el.getBoundingClientRect();
          return s.display!=='none' && s.visibility!=='hidden' && r.width>0 && r.height>0;})
        .map(el=>{const r=el.getBoundingClientRect(); return {
          txt:(el.innerText||el.value||el.getAttribute('aria-label')||el.id||el.tagName).trim().slice(0,60),
          w:r.width,h:r.height,left:r.left,right:r.right};})
        .filter(x=>x.w<24 || x.h<24 || x.left<-2 || x.right>document.documentElement.clientWidth+2)
        .slice(0,20)"""
    )
    if bad:
        raise AssertionError(f"{label}: bad click targets {bad}")


def _fetch_mock(html: str) -> str:
    return html.replace(
        "</head>",
        """<script>
window.__submittedPayloads=[];
window.fetch=async function(url, opts){
  if(String(url).includes('/api/analyze')){
    try{window.__submittedPayloads.push(JSON.parse((opts&&opts.body)||'{}'));}catch(e){window.__submittedPayloads.push({parseError:String(e)});}
    return new Response(JSON.stringify({ok:true,id:'1234567890abcdef1234567890abcdef'}), {status:200, headers:{'Content-Type':'application/json'}});
  }
  return new Response('{}', {status:200, headers:{'Content-Type':'application/json'}});
};
</script></head>""",
    )


def _add_participants(page):
    for name in [
        "Добавить инициатора",
        "Добавить сервис процесса",
        "Добавить внешнюю систему",
        "Добавить хранилище состояния",
        "Добавить аналитику",
        "Добавить ручной разбор",
    ]:
        page.get_by_role("button", name=name).click()


def _add_link(page, src_idx: int, tgt_idx: int, action: str, timing: str, result: str):
    page.locator("#interactionSource").select_option(index=src_idx)
    page.locator("#interactionTarget").select_option(index=tgt_idx)
    page.locator("#interactionAction").select_option(action)
    page.locator("#interactionTiming").select_option(timing)
    page.locator("#interactionResult").select_option(result)
    page.get_by_role("button", name="Добавить связь в цепочку").click()


def _live_api_check(root: Path, out: Path) -> str:
    port = 8143
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(root),
        env={**os.environ, "PORT": str(port), "HOST": "127.0.0.1", "APP_DIR": str(out / "appdb")},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            try:
                urllib.request.urlopen(base + "/health", timeout=1).read()
                break
            except Exception:
                time.sleep(0.2)
        else:
            raise AssertionError("live server did not start")

        payload = {
            "meta": {"name": "UI live API", "entity": "Order", "goal": "Проверка UI payload", "lookup_keys": "orderId", "statuses": "NEW,DONE,FAILED"},
            "systems": [
                {"name": "Клиент", "role": "external"},
                {"name": "Сервис процесса", "role": "internal"},
                {"name": "Партнёр", "role": "external"},
                {"name": "БД процесса", "role": "db"},
                {"name": "DWH", "role": "analytics"},
            ],
            "steps": [
                {"order": 1, "name": "Клиент передаёт заявку", "source_system": "Клиент", "system": "Сервис процесса", "target_system": "Сервис процесса", "channel": "rest", "blocking": "yes", "retry": "auto", "idempotency": "key", "depends_on": "", "writes_entity": "no", "timeout_ms": "800", "compensation": "timeout, retry"},
                {"order": 2, "name": "Сервис вызывает партнёра", "source_system": "Сервис процесса", "system": "Сервис процесса", "target_system": "Партнёр", "channel": "rest", "blocking": "yes", "retry": "auto", "idempotency": "key", "depends_on": "1", "writes_entity": "no", "timeout_ms": "1200", "compensation": "circuit breaker, fallback"},
                {"order": 3, "name": "Сервис сохраняет результат", "source_system": "Сервис процесса", "system": "Сервис процесса", "target_system": "БД процесса", "channel": "db", "blocking": "yes", "retry": "none", "idempotency": "natural", "depends_on": "2", "writes_entity": "yes", "timeout_ms": "200", "compensation": "transaction"},
                {"order": 4, "name": "Передать изменения в DWH", "source_system": "БД процесса", "system": "БД процесса", "target_system": "DWH", "channel": "clickhouse", "blocking": "no", "retry": "auto", "idempotency": "natural", "depends_on": "3", "writes_entity": "no", "timeout_ms": "", "compensation": "watermark, replay"},
            ],
        }
        req = urllib.request.Request(
            base + "/api/analyze",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
        if not res.get("ok"):
            raise AssertionError(f"live API failed: {res}")
        md = urllib.request.urlopen(base + f"/run/{res['id']}.md", timeout=20).read().decode("utf-8")
        if len(md) < 1000 or "ClickHouse" not in md:
            raise AssertionError("live markdown report is incomplete")
        return res["id"]
    finally:
        _stop(proc)


def main() -> int:
    root = Path(__file__).resolve().parent
    out = Path("ui_audit_v8643")
    out.mkdir(exist_ok=True)
    live_id = _live_api_check(root, out)

    sync_playwright, expect = _playwright()
    viewports = [
        ("desktop", {"width": 1366, "height": 900}),
        ("tablet768", {"width": 768, "height": 1024}),
        ("mobile360", {"width": 360, "height": 760}),
        ("mobile390", {"width": 390, "height": 844}),
    ]
    results = []
    with sync_playwright() as p:
        browser = _launch_browser(p)
        for name, vp in viewports:
            page = browser.new_page(viewport=vp)
            console, errors = [], []
            page.on("console", lambda msg: console.append((msg.type, msg.text)))
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.set_content(_fetch_mock(ui.form_page()), wait_until="load")
            expect(page.get_by_role("heading", name="1. Участники процесса")).to_be_visible()
            expect(page.get_by_text("REST API — синхронный вызов")).not_to_be_visible()
            _check_no_overflow(page, f"{name} initial"); _check_targets(page, f"{name} initial")

            _add_participants(page)
            page.get_by_role("button", name="Дальше: связи между участниками").click()
            _add_link(page, 1, 2, "send_data", "sync", "pass_next")
            _add_link(page, 2, 3, "request_data", "sync", "save")
            _add_link(page, 2, 4, "save", "sync", "save")
            _add_link(page, 4, 5, "send_data", "background", "check")
            expect(page.locator(".schema-row")).to_have_count(4)
            _check_no_overflow(page, f"{name} interactions"); _check_targets(page, f"{name} interactions")

            page.get_by_role("button", name="Дальше: уточнения").click()
            visible_keys = page.evaluate(
                """() => [...document.querySelectorAll('[data-action=module]')]
                .filter(b=>getComputedStyle(b).display!=='none' && b.offsetParent!==null)
                .map(b=>[(b.dataset.groupId||'global'),(b.dataset.moduleKind||b.dataset.module||''),(b.textContent||'').trim().replace(/\\s+/g,' ')])"""
            )
            seen = set()
            for item in visible_keys:
                key = tuple(item)
                if key in seen:
                    raise AssertionError(f"{name}: duplicate clarification option {key}")
                seen.add(key)
            fast = page.locator('[data-action="module"][data-module="fast_read"]').first
            if fast.count():
                fast.click(); assert "active" in (fast.get_attribute("class") or "")
                fast.click(); assert "active" not in (fast.get_attribute("class") or "")
                fast.click()
            dwh = page.locator('[data-action="module"][data-module="dwh"]').first
            if dwh.count():
                dwh.click()

            page.get_by_role("button", name="Определить стек по процессу").click()
            if page.locator(".schema-validation-panel").count():
                page.get_by_role("button", name="Продолжить без исправлений").click()
            expect(page.get_by_text("Предложенный стек:").first).to_be_visible()
            expect(page.locator(".channel-chip").first).to_be_visible()
            _check_no_overflow(page, f"{name} stack"); _check_targets(page, f"{name} stack")

            if name == "desktop":
                page.get_by_role("button", name="Открыть экспертный режим").click()
                expect(page.locator("body")).not_to_have_class(re.compile("quick-mode"))
                page.locator('[data-action="duplicate-step"]').first.click()
                before = page.locator("#chainList .chain-component").count()
                page.locator('[data-action="delete-step"]').first.click()
                after = page.locator("#chainList .chain-component").count()
                if after != before - 1:
                    raise AssertionError(f"delete did not reduce step count {before}->{after}")
                page.locator('[data-action="move-step"][data-dir="1"]').first.click()

            page.get_by_role("button", name="Дальше: отчёт").click()
            expect(page.get_by_role("button", name="Сформировать отчёт")).to_be_visible()
            payload = page.evaluate("buildSubmissionPayload()")
            res = analyze(payload)
            if not res.get("ok"):
                raise AssertionError(f"{name}: generated UI payload rejected: {res}")
            result = browser.new_page(viewport=vp)
            result.set_content(ui.result_page("1234567890abcdef1234567890abcdef", res), wait_until="load")
            expect(result.locator(".verdict")).to_be_visible()
            expect(result.get_by_text("Что сделать в первую очередь")).to_be_visible()
            _check_no_overflow(result, f"{name} result"); _check_targets(result, f"{name} result")
            result.close()

            for ref_name, html, selector in [
                ("invariants", ui.invariant_reference_page(), "details.refcard"),
                ("patterns", ui.design_pattern_reference_page(), ".pattern-card, details.refcard"),
            ]:
                ref = browser.new_page(viewport=vp)
                ref.set_content(html, wait_until="load")
                if ref.locator(selector).count() <= 5:
                    raise AssertionError(f"{name} {ref_name}: too few cards")
                _check_no_overflow(ref, f"{name} {ref_name}"); _check_targets(ref, f"{name} {ref_name}")
                ref.close()

            err = [x for x in console if x[0] == "error"]
            if err or errors:
                raise AssertionError(f"{name}: console errors {err}, page errors {errors}")
            results.append({"viewport": name, "steps": len(payload.get("steps", [])), "systems": len(payload.get("systems", [])), "findings": len(res.get("findings", []))})
            page.close()
        browser.close()

    output = {"ok": True, "version": ui.APP_VERSION, "live_api_id": live_id, "viewports": results}
    (out / "verify_ui_full_v8643_results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
