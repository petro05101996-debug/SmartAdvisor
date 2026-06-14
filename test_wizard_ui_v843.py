# -*- coding: utf-8 -*-
"""UI regression for v8.4.3 wizard-first constructor."""
import ui


def test_wizard_first_entry_reduces_first_screen_choices():
    html = ui.form_page()
    assert "wizard-shell" in html
    assert html.count("data-wizard-pane=") == 5
    assert "data-action=\"wizard-next\"" in html
    assert "data-action=\"wizard-back\"" in html
    assert "data-action=\"compose-chain\"" in html
    assert "Грамматика процесса" not in html
    assert "Как начинается?</h4>" not in html
    assert "Как начинается процесс?" in html


def test_quick_mode_chain_is_readable_before_editable():
    html = ui.form_page()
    assert "simple-step-view" in html
    assert "simple-system-view" in html
    assert "В простом режиме показан смысл шага" in html
    assert "component-actions" in html  # still exists for expert mode
    assert ".quick-mode .component-actions{display:none}" in html


def test_complexity_options_are_grouped_by_human_reason():
    html = ui.form_page()
    for title in ["Надёжность", "Потоки и системы", "Данные и аналитика", "Бизнес-риск"]:
        assert title in html
    assert "module-groups" in html
