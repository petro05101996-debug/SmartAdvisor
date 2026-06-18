# -*- coding: utf-8 -*-
import ui


def test_trainer_home_has_simple_user_path_v8657():
    html = ui.learning_home_page()
    assert '8.6.67-ultimate-gated' in html
    assert 'Как пользоваться' in html
    assert '1. Выбери кейс' in html
    assert '2. Отметь решения' in html
    assert '3. Нажми проверку' in html
    assert '4. Сравни с эталоном' in html
    assert 'JSON доступен только как экспертный режим' not in html


def test_trainer_case_main_path_is_not_json_first_v8657():
    html = ui.learning_case_page('bank-credit-bki-fraud')
    assert 'Поймите задачу' in html
    assert 'Выберите, что добавите в архитектуру' in html
    assert 'Проверить выбранное решение' in html
    assert 'Экспертный режим: JSON решения' in html
    assert html.index('Выберите, что добавите в архитектуру') < html.index('Экспертный режим: JSON решения')
    assert 'buildVisualSolution(\'weak\')' not in html
    assert 'checked' not in html.split('class="visual-control" value="outbox"', 1)[1].split('>', 1)[0]
