# -*- coding: utf-8 -*-
import ui


def test_auto_stack_ui_present_and_manual_override_hidden():
    html = ui.form_page()
    assert "Стек подбирается автоматически" in html
    assert "Переопределить стек вручную" in html
    assert "setManualChannel" in html
    assert "resetAutoChannel" in html
    assert "applyAutoStackForStepAt" in html
    assert "Пользователь описывает смысл шага" in html


def test_tech_stack_not_primary_user_instruction():
    html = ui.form_page()
    assert "технический способ взаимодействия подбирается автоматически" in html
    assert "Обычно это не нужно" in html



def test_late_external_result_defaults_to_callback_not_kafka_only():
    html = ui.form_page()
    assert "Принять callback/webhook со статусом от внешней системы" in html
    assert "подпись callback" in html
    assert "Если внешний партнёр не умеет callback/webhook" in html
