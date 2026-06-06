from integration_architect_pro import form_page, Engine, parse_post
from urllib.parse import urlencode
import re
import subprocess
import shutil
import pytest


def _start_screen(html: str) -> str:
    return html.split("<div class='app-shell", 1)[0]


def test_simple_wizard_exposes_required_beginner_flow_and_working_controls():
    html = form_page()
    start = _start_screen(html)
    for text in [
        'Интеграционный инструктор',
        'Начать проектирование',
        'Проверить существующее решение',
        'Расширенный режим',
    ]:
        assert text in start
    assert 'Быстро разобрать задачу' not in start
    assert 'Продвинутый режим</b>' not in start
    assert 'Начать выбранный режим' not in start
    for text in [
        'Не знаю, помогите выбрать',
        'Мини-опрос для выбора сценария',
        'Применить этот сценарий',
        'Шаг 1. Что нужно сделать?',
        'Шаг 2. Что происходит в бизнесе?',
        'Шаг 3. Какие системы участвуют?',
        'Шаг 4. Как идёт процесс?',
        'Готовность к отчёту',
        '+ Добавить систему',
        'Дублировать систему',
        '+ Добавить шаг',
        'Переместить выше',
        'Показать экспертную матрицу',
    ]:
        assert text in html
    assert 'disabled title=' not in html
    assert 'id=\'simpleGenerateBtn\'' in html
    assert 'id=\'startDesignBtn\'' in html


def test_legacy_wizard_hidden_from_simple_mode_and_result_step_removed():
    html = form_page()
    assert 'legacy-wizard-compat' in html
    assert 'body.advanced-mode .legacy-wizard-compat' in html
    assert 'body.expert-mode .legacy-wizard-compat' in html
    assert 'body.simple-mode #progressRail' in html
    assert 'body.simple-mode .quick-mode-panel' in html
    assert 'body.simple-mode .sticky-submit' in html
    assert "const simpleWizardLabels = ['Что нужно сделать?', 'Бизнес', 'Системы', 'Процесс', 'Проверка'];" in html
    assert "data-simple-panel='5'" not in html
    assert 'К результату' not in html


def test_simple_wizard_javascript_is_syntax_valid(tmp_path):
    if not shutil.which('node'):
        pytest.skip('node is not installed')
    html = form_page()
    script = '\n'.join(re.findall(r'<script>(.*?)</script>', html, flags=re.S))
    js_path = tmp_path / 'ui.js'
    js_path.write_text(script, encoding='utf-8')
    subprocess.run(['node', '--check', str(js_path)], check=True)


def test_simple_wizard_mapping_uses_engine_enums_and_scenario_defaults():
    html = form_page()
    assert 'const responseMap=' in html
    assert "result_model:'sync'" in html
    assert "response_time_expectation:'under_3s'" in html
    assert "response_time_expectation:'async_ok'" in html
    assert "result_model:'mixed'" in html
    assert "unavailableMap={show_error:'show_error',degraded:'show_stale',queue_for_later:'queue_for_later',manual_recovery:'manual_review'}" in html
    assert "function isMeaningful(value)" in html
    assert "function isMeaningfulNumber(value)" in html
    assert "setField('rps','уточнить')" in html
    assert "setField('target_lag_seconds','уточнить')" in html
    assert "Заполнить</button>" in html
    assert "business_exactly_once" in html
    assert "duplicate_callback | callback_api" in html
    assert "file_reprocess_with_checksum" in html
    assert "replayable_batch_or_cdc" in html
    assert "function checkRequiredButtons()" in html
    assert "function safeOn(id,event,handler)" in html



def test_required_buttons_are_present_in_html():
    html = form_page()
    required = [
        'startDesignBtn', 'startReviewBtn', 'startExpertBtn', 'backToStart',
        'simplePrevBtn', 'simpleNextBtn', 'simplePowerBtn', 'simpleGenerateBtn',
        'fillMissingBtn', 'openAdvancedFromReadyBtn', 'addSystemBtn', 'syncSystemsBtn',
        'toggleSystemsMatrixBtn', 'addStepBtn', 'syncStepsBtn', 'toggleStepsMatrixBtn',
        'applyChainTemplateBtn', 'applyHelperScenarioBtn'
    ]
    for btn in required:
        assert f'id="{btn}"' in html or f"id='{btn}'" in html
    assert 'aria-disabled="true"' not in html
    assert 'будет включено' not in html

def test_new_wizard_post_still_reuses_engine_and_exports_structured_result():
    body = urlencode({
        'ux_mode': 'wizard',
        'wizard_task_type': 'kafka_event',
        'wizard_source_name': 'Contract Service',
        'wizard_target_name': 'Reporting Service',
        'wizard_process_template': 'kafka',
        'business_goal': 'Сервис договоров публикует событие изменения договора, другой сервис читает и обновляет БД.',
        'risk_duplicate_event': 'yes',
        'risk_lost_event': 'yes',
    })
    form = parse_post(body)
    assert 'Contract Service' in form['systems_matrix']
    assert 'Kafka' in form['target_integration_matrix']
    extra_body = urlencode({
        'delivery_guarantee': 'business_exactly_once',
        'audit_required': 'yes',
        'rollback_plan': 'уточнить перед production',
        'manual_recovery_owner': 'уточнить',
        'lineage_required': 'yes',
        'data_quality_required': 'yes',
    })
    extra_form = parse_post(extra_body)
    assert extra_form['rollback_plan'] == 'уточнить перед production'
    assert extra_form['manual_recovery_owner'] == 'уточнить'
    assert extra_form['lineage_required'] == 'yes'
    assert extra_form['data_quality_required'] == 'yes'
    res = Engine().generate(form)
    assert res['markdown']
    assert res['structured_result']
    assert res['wizard_production_gate']


def test_required_buttons_have_handlers_or_safe_bindings():
    html = form_page()
    script = '\n'.join(re.findall(r'<script>(.*?)</script>', html, flags=re.S))
    required_handlers = {
        'startDesignBtn': 'startDesignBtn.addEventListener',
        'startReviewBtn': 'startReviewBtn.addEventListener',
        'startExpertBtn': 'startExpertBtn.addEventListener',
        'backToStart': 'backToStart.addEventListener',
        'simplePrevBtn': 'simplePrevBtn.addEventListener',
        'simpleNextBtn': 'simpleNextBtn.addEventListener',
        'simplePowerBtn': 'simplePowerBtn.addEventListener',
        'simpleGenerateBtn': 'simpleGenerateBtn.addEventListener',
        'fillMissingBtn': 'fillMissingBtn.addEventListener',
        'openAdvancedFromReadyBtn': 'openAdvancedFromReadyBtn.addEventListener',
        'addSystemBtn': 'addSystemBtn.addEventListener',
        'syncSystemsBtn': 'syncSystemsBtn.addEventListener',
        'toggleSystemsMatrixBtn': 'toggleSystemsMatrixBtn.addEventListener',
        'addStepBtn': 'addStepBtn.addEventListener',
        'syncStepsBtn': 'syncStepsBtn.addEventListener',
        'toggleStepsMatrixBtn': 'toggleStepsMatrixBtn.addEventListener',
        'applyChainTemplateBtn': 'applyChainTemplateBtn.addEventListener',
        'applyHelperScenarioBtn': "safeOn('applyHelperScenarioBtn'",
    }
    for btn, needle in required_handlers.items():
        assert needle in script, f'{btn} has no obvious handler binding'
    assert "const ids=['startDesignBtn'" in script
    assert "'applyHelperScenarioBtn'" in script


def test_result_page_keeps_beginner_summary_and_all_download_actions():
    form = parse_post(urlencode({
        'task_type': 'event_integration',
        'business_goal': 'Kafka event smoke from simple master',
        'allowed_channels': 'kafka',
        'delivery_guarantee': 'business_exactly_once',
        'systems_matrix': 'Source | source | high | team | Kafka\nConsumer | target | high | team | Kafka',
        'process_steps': '0 | 1 | root | publish event | Source | Kafka | input | output | SLA уточнить | yes | retry + DLQ | non_blocking | owner team',
        'process_flow_matrix': 'S1 | root | publish | Source | Kafka | END | E_VALIDATION | E_TIMEOUT | retry + DLQ | yes',
        'target_integration_matrix': 'Source | Target | Kafka | async | event | payload | Event.v1 | 30s | yes/backoff | 3 | yes | idempotencyKey | auth | уточнить | owner',
        'error_matrix': 'duplicate | consumer | non_blocking | no | ignore by eventId/idempotencyKey | consumer team',
        'observability_matrix': 'consumer_lag | kafka consumer | warning | yes | team | dashboard',
    }))
    res = Engine().generate(form)
    from integration_architect_pro import result_page
    page = result_page(res, 'rid', 'report.md', 'bundle.zip', 'bundle.json')
    for text in [
        'Короткий итог',
        'Визуальная схема',
        'Обязательные элементы решения',
        'Риски и вопросы',
        'Скачать markdown',
        'Скачать JSON bundle',
        'Скачать export bundle',
        'Показать полный технический отчёт',
        'Вернуться к форме',
    ]:
        assert text in page
    assert page.index('Короткий итог') < page.index('Показать полный технический отчёт')


def test_ten_core_scenarios_generate_reports_from_simple_mode_payloads():
    base = {
        'project_name': 'Scenario smoke',
        'business_goal': 'Smoke scenario goal',
        'systems_matrix': 'Source | source | high | team | REST\nTarget | target | high | team | REST',
        'process_steps': '0 | 1 | root | do work | Source | REST | input | output | SLA уточнить | yes | retry/manual | blocking | owner team',
        'process_flow_matrix': 'S1 | root | do work | Source | REST | END | E_VALIDATION | E_TIMEOUT | retry/manual | yes',
        'target_integration_matrix': 'Source | Target | REST | sync | user_action | payload | Contract.v1 | 3s | yes/backoff | 3 | no | correlationId | auth | уточнить | owner',
        'error_matrix': 'timeout | integration | blocking | yes | retry with backoff + manual recovery | owner team',
        'observability_matrix': 'latency | api | warning | yes | team | dashboard',
    }
    scenarios = {
        'REST A → B': {'task_type': 'new_from_scratch', 'allowed_channels': 'rest', 'result_model': 'sync', 'response_time_expectation': 'under_3s', 'delivery_guarantee': 'at_most_once_with_retry_policy'},
        'Kafka event': {'task_type': 'event_integration', 'allowed_channels': 'kafka', 'result_model': 'tracking', 'response_time_expectation': 'async_ok', 'delivery_guarantee': 'business_exactly_once'},
        'Outbox → Kafka → Inbox': {'task_type': 'event_integration', 'allowed_channels': 'kafka', 'result_model': 'tracking', 'delivery_guarantee': 'business_exactly_once', 'existing_capabilities': 'outbox,kafka,inbox,dlq,monitoring,reconciliation'},
        'Shared Kafka topic + filter': {'task_type': 'event_integration', 'allowed_channels': 'kafka', 'business_goal': 'Shared topic consumer filters events by field', 'delivery_guarantee': 'business_exactly_once'},
        'REST enrichment before Kafka': {'task_type': 'event_integration', 'allowed_channels': 'rest,kafka', 'business_goal': 'REST enrichment before Kafka publication', 'result_model': 'tracking', 'delivery_guarantee': 'business_exactly_once'},
        'Webhook callback': {'task_type': 'external_integration', 'allowed_channels': 'webhook,rest', 'result_model': 'callback', 'delivery_guarantee': 'at_least_once_with_idempotency', 'webhook_signature_required': 'yes'},
        'DWH / CDC': {'task_type': 'dwh_reporting', 'allowed_channels': 'cdc,etl,sftp', 'result_model': 'report', 'freshness_requirement': 'daily', 'delivery_guarantee': 'replayable_batch_or_cdc', 'lineage_required': 'yes', 'data_quality_required': 'yes'},
        'Hot status screen': {'task_type': 'new_from_scratch', 'allowed_channels': 'rest,kafka', 'business_goal': 'Hot status read model cache with freshness policy', 'result_model': 'sync', 'delivery_guarantee': 'business_exactly_once'},
        'Financial operation': {'task_type': 'event_integration', 'allowed_channels': 'rest,kafka', 'money_impact': 'yes', 'regulatory_impact': 'yes', 'delivery_guarantee': 'business_exactly_once', 'audit_required': 'yes'},
        'Legacy file exchange': {'task_type': 'legacy_integration', 'allowed_channels': 'sftp', 'result_model': 'report', 'delivery_guarantee': 'file_reprocess_with_checksum'},
    }
    from integration_architect_pro import result_page
    for name, extra in scenarios.items():
        payload = dict(base)
        payload.update(extra)
        payload['business_goal'] = extra.get('business_goal', name + ' smoke')
        form = parse_post(urlencode(payload))
        res = Engine().generate(form)
        page = result_page(res, 'rid', 'report.md', 'bundle.zip', 'bundle.json')
        assert res['markdown'] and '##' in res['markdown'], name
        assert res['structured_result'], name
        assert 'Короткий итог' in page and 'Визуальная схема' in page and 'Риски и вопросы' in page, name
