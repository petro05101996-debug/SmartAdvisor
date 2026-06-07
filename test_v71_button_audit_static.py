import ast
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

SOURCE = Path('integration_architect_pro.py')


def _content_template():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'content_template':
                    return ast.literal_eval(node.value)
    raise AssertionError('content_template not found')


HTML = _content_template()
SCRIPT = HTML.split('<script>', 1)[1].split('</script>', 1)[0]


class ButtonAuditParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.buttons = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        self.stack.append((tag, data))
        if 'id' in data:
            self.ids.append(data['id'])
        if tag == 'button':
            in_form = any(t == 'form' for t, _ in self.stack)
            self.buttons.append({'attrs': data, 'in_form': in_form})

    def handle_endtag(self, tag):
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx][0] == tag:
                del self.stack[idx:]
                break


def _parser():
    parser = ButtonAuditParser()
    parser.feed(HTML)
    return parser


def test_all_form_buttons_have_type():
    missing = [button for button in _parser().buttons if button['in_form'] and not button['attrs'].get('type')]
    assert missing == []


def test_no_duplicate_ids():
    ids = _parser().ids
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert duplicates == []


def test_critical_buttons_exist():
    ids = {button['attrs'].get('id') for button in _parser().buttons}
    data_buttons = {key: set(re.findall(rf"{key}='([^']+)'", HTML)) for key in ['data-business-case', 'data-business-preset', 'data-chain-preset']}
    for critical_id in [
        'startNoTextBtn', 'backToStart', 'addBusinessActorBtn', 'addBusinessStepBtn',
        'resetBusinessBtn', 'openTechnicalConstructor', 'openTechnicalConstructorReview',
        'approveAutoScheme', 'editBusinessProcess', 'confirmUnderstanding', 'editAnswers',
        'addParticipantBtn', 'addConnectionBtn', 'resetCustomChainBtn', 'constructorPrev',
        'constructorNext', 'prevBtn', 'submitBtn',
    ]:
        assert critical_id in ids
    assert {'application_creation', 'data_change_distribution', 'external_check', 'data_enrichment', 'status_screen', 'reporting', 'legacy_file', 'audit', 'long_process', 'helper'} <= data_buttons['data-business-case']
    assert {'deferred_application', 'data_change_many_systems', 'enrichment_before_send', 'status_screen_collection', 'reporting', 'legacy_file'} <= data_buttons['data-business-preset']
    assert {'async', 'kafka', 'status', 'legacy'} <= data_buttons['data-chain-preset']


def test_critical_buttons_have_handlers():
    for critical_id in [
        'startNoTextBtn', 'backToStart', 'addBusinessActorBtn', 'addBusinessStepBtn',
        'resetBusinessBtn', 'openTechnicalConstructor', 'openTechnicalConstructorReview',
        'approveAutoScheme', 'editBusinessProcess', 'confirmUnderstanding', 'editAnswers',
        'addParticipantBtn', 'addConnectionBtn', 'resetCustomChainBtn', 'constructorPrev',
        'constructorNext', 'prevBtn',
    ]:
        assert f"on('{critical_id}'" in SCRIPT or f'getElementById(\'{critical_id}\')' in SCRIPT
    for selector in ['[data-start-goal]', '[data-case]', '[data-business-preset]', '[data-chain-preset]']:
        assert f"querySelectorAll('{selector}')" in SCRIPT


def test_no_open_technical_constructor_go_call():
    handler = re.search(r"on\('openTechnicalConstructor','click',\(\)=>openTechnicalConstructorAt\('autoTechnicalConstructorHost'\)\)", SCRIPT)
    assert handler, 'auto technical constructor button must use openTechnicalConstructorAt'
    assert "on('openTechnicalConstructor','click',()=>go(" not in SCRIPT
    assert "on('openTechnicalConstructorReview','click',()=>go(" not in SCRIPT


def test_default_business_process_function_exists():
    definition = SCRIPT.find('function defaultBusinessProcess')
    assert definition >= 0
    call_sites = [m.start() for m in re.finditer(r'defaultBusinessProcess\(', SCRIPT)]
    assert call_sites
    assert all(definition <= call for call in call_sites)


def test_no_inline_js_broken_newline_join():
    assert "join('\n')" not in SCRIPT
    Path('extracted-ui-script.js').write_text(SCRIPT, encoding='utf-8')
    subprocess.run(['node', '--check', 'extracted-ui-script.js'], check=True)
