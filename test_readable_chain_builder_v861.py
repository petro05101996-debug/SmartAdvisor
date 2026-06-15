import ui


def test_quick_mode_chain_is_explained_without_raw_routing():
    html = ui.form_page()
    assert 'Как читать и строить цепочку' in html
    assert 'Сценарий процесса' in html
    assert 'Продолжить цепочку простым действием' in html
    assert 'В простом режиме не нужно двигать стрелки' in html
    assert 'add-human-step' in html


def test_chain_helpers_and_quick_drag_guard_exist():
    js = ui.FORM_JS
    assert 'function simpleStepLinkText' in js
    assert 'function addHumanStep' in js
    assert "if(state.mode==='quick')return; const c=e.target.closest('.chain-component')" in js
    assert 'Связь пересчитывается автоматически при перемещении' in js
