# -*- coding: utf-8 -*-
import ui


def test_auto_route_logic_is_present_in_ui():
    html = ui.form_page()
    assert "autoFillRouteForStepAt" in html
    assert "normalizeChainAfterStructureChange" in html
    assert "Поля маршрута и зависимости пересчитаны автоматически" in html or "Маршрут, исполнитель, получатель и зависимости пересчитаны автоматически" in html
    assert "Откуда берутся данные?" in html
    assert "Кто выполняет шаг?" in html
    assert "Куда попадает результат?" in html


def test_expert_mode_explains_autofill_after_reorder():
    html = ui.form_page()
    assert "При перемещении шага внутри цепочки маршрут и зависимости пересчитываются автоматически" in html
    assert "автозаполняется: предыдущий шаг, запись в БД, CDC или join" in html
