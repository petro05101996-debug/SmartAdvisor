# -*- coding: utf-8 -*-
"""Совместимая проверка мобильной вёрстки.

Старый сценарий v8.6.9 проверял те же состояния через более тяжёлый
Playwright-прогон и мог зависать на headless Chromium. Актуальная стабильная
проверка живёт в verify_mobile_layout_flow_v869.py и покрывает 6 viewport/stage
состояний: 36 проверок без overflow/overlap.
"""
import runpy
runpy.run_path('verify_mobile_layout_flow_v869.py', run_name='__main__')
print('MOBILE_NO_OVERLAP_v869 compatible ok')
