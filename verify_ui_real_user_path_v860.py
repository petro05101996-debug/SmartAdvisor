# -*- coding: utf-8 -*-
"""End-to-end UI probe for the process builder.

It uses the rendered HTML and a fetch stub, so it checks real DOM buttons without
requiring a running server. If Playwright is unavailable, this script exits with
an explicit error.
"""
import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

import ui


def launch_browser(p):
    system = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    try:
        return p.chromium.launch(headless=True, args=["--no-sandbox"])
    except Exception:
        if not system:
            raise
        return p.chromium.launch(headless=True, executable_path=system, args=["--no-sandbox", "--disable-dev-shm-usage"])


def main():
    html = ui.form_page().replace(
        "</head>",
        """<script>
        window.__submittedPayloads = [];
        window.fetch = async function(url, opts) {
          if (String(url).includes('/api/analyze')) {
            try { window.__submittedPayloads.push(JSON.parse(opts && opts.body || '{}')); }
            catch (e) { window.__submittedPayloads.push({parseError: String(e)}); }
            return new Response(JSON.stringify({ok:true,id:'ui-probe-run'}), {status:200, headers:{'Content-Type':'application/json'}});
          }
          return new Response('{}', {status:200, headers:{'Content-Type':'application/json'}});
        };
        </script></head>""",
    )
    checks = []

    def ok(name, details=""):
        checks.append(("OK", name, details))

    def fail(name, details=""):
        checks.append(("FAIL", name, details))

    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.set_default_timeout(5000)
        console = []
        page.on("console", lambda msg: console.append((msg.type, msg.text)))
        page.on("pageerror", lambda exc: console.append(("pageerror", str(exc))))
        page.set_content(html, wait_until="load")
        ok("open_page", page.title())
        if page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"):
            ok("mobile_no_horizontal_scroll")
        else:
            fail("mobile_no_horizontal_scroll", str(page.evaluate("document.documentElement.scrollWidth + ' / ' + document.documentElement.clientWidth")))

        # Step 1: semantic wizard, no stack terms required.
        for group, value in [
            ("start", "incoming_request"),
            ("activity", "call_external"),
            ("timing", "later"),
            ("result", "save_forward"),
            ("systems", "4"),
        ]:
            page.locator(f'[data-action="compose-choice"][data-compose-group="{group}"][data-value="{value}"]').click()
            ok(f"wizard_choice_{group}_{value}")
        page.get_by_role("button", name="Собрать цепочку").click()
        steps_before = page.locator("[data-step-id]").count()
        ok("compose_chain", f"steps={steps_before}") if steps_before else fail("compose_chain", "no steps")
        if page.locator(".prestack-chip").first.is_visible():
            ok("pre_stack_mode_visible")
        else:
            fail("pre_stack_mode_visible")

        # Step 2: click every semantic module once.
        modules = page.locator('[data-action="module"]')
        module_count = modules.count()
        for i in range(module_count):
            modules.nth(i).click()
        ok("all_semantic_module_buttons", f"clicked={module_count}")

        # Step 3: stack generation and expert correction.
        page.get_by_role("button", name="Определить стек по процессу").click()
        if page.locator(".channel-chip").first.is_visible():
            ok("generate_stack")
        else:
            fail("generate_stack", "channel chips not visible")
        page.get_by_role("button", name="Открыть экспертный режим").click()
        if not page.locator("body").evaluate("el => el.classList.contains('quick-mode')"):
            ok("open_expert_from_stack_panel")
        else:
            fail("open_expert_from_stack_panel")
        if page.locator('[data-action="move-step"][data-dir="1"]').count():
            page.locator('[data-action="move-step"][data-dir="1"]').first.click(); ok("move_step_down")
        if page.locator('[data-action="move-step"][data-dir="-1"]').count():
            page.locator('[data-action="move-step"][data-dir="-1"]').first.click(); ok("move_step_up")
        for selector, name in [
            ('[data-action="duplicate-step"]', "duplicate_step"),
            ('[data-action="insert-before"]', "insert_before"),
            ('[data-action="insert-after"]', "insert_after"),
            ('[data-action="safe-step"]', "safe_step"),
        ]:
            if page.locator(selector).count():
                page.locator(selector).first.click(); ok(name)
            else:
                fail(name, "not found")
        page.evaluate('document.querySelectorAll("details").forEach(d => d.open = true)')
        channels = page.locator('[data-action="set-channel"]')
        channel_count = channels.count()
        # Click a representative sample plus ensure the full channel list is present.
        for ch in ["rest", "soap", "kafka", "rabbitmq", "redis_cache", "redis_lock", "sftp", "cdc", "workflow_engine"]:
            loc = page.locator(f'[data-action="set-channel"][data-channel="{ch}"]')
            if loc.count():
                page.evaluate('document.querySelectorAll("details").forEach(d => d.open = true)')
                loc.first.click(force=True); ok(f"manual_channel_{ch}")
            else:
                fail(f"manual_channel_{ch}", "not found")
        if page.locator('[data-action="auto-channel"]').count():
            page.locator('[data-action="auto-channel"]').first.click(); ok("reset_auto_stack")
        else:
            fail("reset_auto_stack", "not found")
        ok("manual_channel_catalog_present", f"buttons={channel_count}") if channel_count >= 55 else fail("manual_channel_catalog_present", f"buttons={channel_count}")

        # Step 4: submit and validate payload references.
        page.get_by_role("button", name="Проверить архитектуру").click()
        page.wait_for_timeout(700)
        submitted = page.evaluate("window.__submittedPayloads.length")
        if submitted < 1:
            fail("submit_fetch_called", f"submitted={submitted}")
            payload = {}
        else:
            ok("submit_fetch_called", f"submitted={submitted}")
            payload = page.evaluate("window.__submittedPayloads[window.__submittedPayloads.length-1]")
        sysnames = {s.get("name") for s in payload.get("systems", [])}
        ref_issues = []
        for idx, step in enumerate(payload.get("steps", []), start=1):
            for field in ("source_system", "system", "target_system"):
                val = step.get(field)
                if val and val not in sysnames:
                    ref_issues.append(f"step {idx}: {field}={val}")
            deps = [int(x.strip()) for x in str(step.get("depends_on", "")).replace(";", ",").split(",") if x.strip().isdigit()]
            if idx in deps:
                ref_issues.append(f"step {idx}: self dependency")
            ref_issues += [f"step {idx}: bad dependency {d}" for d in deps if d < 1 or d > len(payload.get("steps", []))]
        ok("payload_references_valid", f"steps={len(payload.get('steps', []))}, systems={len(payload.get('systems', []))}") if not ref_issues else fail("payload_references_valid", "; ".join(ref_issues[:10]))

        errors = [x for x in console if x[0] in ("error", "pageerror")]
        ok("console_errors", "0") if not errors else fail("console_errors", str(errors[:5]))
        browser.close()

    report = ["# UI real-user path probe", ""]
    for status, name, details in checks:
        report.append(f"- {status}: {name}" + (f" — {details}" if details else ""))
    ok_count = sum(1 for s, _, _ in checks if s == "OK")
    fail_count = sum(1 for s, _, _ in checks if s != "OK")
    report.append("")
    report.append(f"SUMMARY: {ok_count} ok, {fail_count} fail")
    Path("UI_REAL_USER_PATH_v8_6_0.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
