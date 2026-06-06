import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from urllib.request import urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="browser regression requires RUN_BROWSER_TESTS=1",
)


def _free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_app(url, proc, timeout=20):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early with code {proc.returncode}")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - diagnostic path
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"server did not start at {url}: {last_error}")


def _assert_in_order(text, expected):
    cursor = -1
    for item in expected:
        next_pos = text.find(item, cursor + 1)
        assert next_pos > cursor, f"{item!r} was not found in order in {text!r}"
        cursor = next_pos


def test_v66_no_text_constructor_buttons_in_real_chromium():
    try:
        import playwright.sync_api as playwright
    except ModuleNotFoundError as exc:
        pytest.fail(f"RUN_BROWSER_TESTS=1 requires Playwright to be installed: {exc}")
    port = _free_port()
    env = os.environ.copy()
    env.update({"HOST": "127.0.0.1", "PORT": str(port)})
    proc = subprocess.Popen(
        [sys.executable, "integration_architect_pro.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    url = f"http://127.0.0.1:{port}/"
    try:
        _wait_for_app(url, proc)
        js_errors = []
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.on(
                "console",
                lambda msg: js_errors.append(f"console {msg.type}: {msg.text}")
                if msg.type == "error"
                else None,
            )
            page.on("pageerror", lambda exc: js_errors.append(f"pageerror: {exc}"))

            def open_chain_builder():
                page.goto(url, wait_until="networkidle")
                page.get_by_role("button", name="Начать").click()
                page.locator("#constructorNext").click()
                page.locator("section.constructor-screen.is-active[data-constructor-screen='1']").wait_for()

            def go_to_result():
                page.locator("#constructorNext").click()
                page.locator("section.constructor-screen.is-active[data-constructor-screen='2']").wait_for()
                page.locator("#constructorNext").click()
                page.locator("section.constructor-screen.is-active[data-constructor-screen='3']").wait_for()
                page.locator("#constructorNext").click()
                page.locator("section.constructor-screen.is-active[data-constructor-screen='4']").wait_for()

            open_chain_builder()

            page.locator("#addParticipantBtn").click()
            page.locator("#addParticipantBtn").click()
            page.wait_for_function("document.querySelectorAll('#participantList .participant-card').length >= 2")
            assert "2 участников" in page.locator("#participantCounter").inner_text()

            page.locator("#addConnectionBtn").click()
            page.wait_for_function("document.querySelectorAll('#connectionList .connection-card').length >= 1")
            assert "1 связ" in page.locator("#connectionCounter").inner_text()
            first_payload = page.locator("#customChainJson").input_value()
            assert first_payload and "participants" in first_payload and "connections" in first_payload

            # Repeated click with same from/to/type must not create a duplicate edge.
            page.locator("#addConnectionBtn").click()
            assert "1 связ" in page.locator("#connectionCounter").inner_text()
            assert "Такая связь уже есть" in page.locator("#builderMessage").inner_text()

            for hidden_id in [
                "#systemsMatrixHidden",
                "#processStepsHidden",
                "#targetIntegrationHidden",
                "#errorMatrixHidden",
                "#processGraphJson",
                "#businessGoalHidden",
            ]:
                assert page.locator(hidden_id).input_value().strip(), hidden_id

            go_to_result()

            for text in [
                "Схема взаимодействия",
                "Что обязательно сделать",
                "Главные риски",
                "Что отдать разработке",
            ]:
                assert page.get_by_text(text).first.is_visible()

            open_chain_builder()
            async_chain = ["Service 1", "Service 2 API", "integration_task DB", "Worker", "Service 3"]
            page.locator("[data-chain-preset='async']").click()
            page.wait_for_function("document.querySelectorAll('#participantList .participant-card').length >= 5")
            participant_text = page.locator("#participantList").inner_text()
            for item in async_chain:
                assert item in participant_text
            assert all(item in page.locator("#customChainJson").input_value() for item in async_chain)
            go_to_result()
            _assert_in_order(page.locator("#resultSchema").inner_text(), async_chain)

            open_chain_builder()
            kafka_expected = ["Source Service", "Outbox", "Kafka", "Consumer", "Inbox"]
            page.locator("[data-chain-preset='kafka']").click()
            page.wait_for_function("document.querySelectorAll('#participantList .participant-card').length >= 7")
            participant_text = page.locator("#participantList").inner_text()
            for item in kafka_expected:
                assert item in participant_text
            assert all(item in page.locator("#customChainJson").input_value() for item in kafka_expected)
            go_to_result()
            result_text = page.locator("#resultSchema").inner_text()
            for item in ["Outbox", "Kafka", "Inbox"]:
                assert item in result_text
            _assert_in_order(result_text, kafka_expected)

            browser.close()
        assert not js_errors
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup path
            proc.kill()
