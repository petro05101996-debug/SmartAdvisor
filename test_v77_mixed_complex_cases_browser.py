import os

import pytest

from ui_browser_test_helpers import chromium_page, click_next, running_app, start_flow

pytestmark = pytest.mark.skipif(os.environ.get('RUN_BROWSER_TESTS') != '1', reason='browser test requires RUN_BROWSER_TESTS=1')


def _check_if_exists(page, flag):
    loc = page.locator(f"input[name='constraint_flags'][value='{flag}']")
    assert loc.count() == 1, f'missing constraint checkbox: {flag}'
    loc.check()


def test_mixed_application_saga_with_modifiers_browser():
    """Mixed conflict case must keep saga as primary and use tenant/highload/PII as modifiers."""
    with running_app() as url, chromium_page(url) as (page, js_errors):
        start_flow(page, 'application_creation')
        click_next(page, 1)
        page.locator("[data-business-preset='deferred_application']").click()
        for flag in ['highload', 'regulatory', 'pii', 'compensation', 'multi_tenant', 'active_active']:
            _check_if_exists(page, flag)
        click_next(page, 2)
        graph = page.locator('#processGraphJson').input_value()
        assert 'saga_state_machine' in graph
        assert 'Process State DB' in graph
        assert 'Compensation / Manual Recovery' in graph
        assert 'Shared Stream' not in graph
        assert 'multi_tenant_noisy_neighbor' in graph
        click_next(page, 3)
        click_next(page, 4)
        click_next(page, 5)
        result = page.locator('section[data-constructor-screen="5"]').inner_text()
        assert 'Process State DB' in result
        assert 'Compensation' in result
        assert 'tenantId key' in result
        assert 'access control' in result or 'audit trail' in result
        assert 'Shared Stream' not in result
        page.locator('#submitBtn').click()
        page.wait_for_load_state('networkidle')
        body = page.locator('body').inner_text()
        assert 'saga_state_machine' in body
        assert 'Process State DB' in body
        assert 'tenantId key' in body
        assert 'compensation_failed' in body
        assert 'Shared Stream → Tenant-aware Consumer Pool' not in body
        assert not js_errors
