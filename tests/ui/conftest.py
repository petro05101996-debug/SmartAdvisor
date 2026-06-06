import os
import socket
import subprocess
import sys
import time

import pytest


def wait_port(host: str, port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="session")
def browser_available():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception:
        pytest.skip("Playwright is not installed. Run: pip install -r requirements-dev.txt")
    return True


@pytest.fixture(scope="session")
def app_server():
    port = int(os.environ["TEST_PORT"]) if os.environ.get("TEST_PORT") else free_port()
    proc = subprocess.Popen(
        [sys.executable, "integration_architect_pro.py"],
        env={**os.environ, "PORT": str(port)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not wait_port("127.0.0.1", port):
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        pytest.fail(f"App did not start on test port {port}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    yield f"http://127.0.0.1:{port}"

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture()
def page(browser_available):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:
            pytest.skip("Chromium is not installed. Run: python -m playwright install chromium")

        page = browser.new_page(viewport={"width": 1366, "height": 768}, accept_downloads=True)
        ignored_console_errors = ["favicon"]
        console_errors = []

        def on_console(msg):
            if msg.type != "error":
                return
            if any(ignored in msg.text.lower() for ignored in ignored_console_errors):
                return
            console_errors.append(msg.text)

        page.on("console", on_console)

        yield page

        browser.close()
        assert not console_errors, f"Browser console errors: {console_errors}"
