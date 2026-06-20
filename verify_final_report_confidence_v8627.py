#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v8.6.27: финальная sanity-проверка отчёта после ручной вычитки."""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
# Генерируем актуальный all-tech отчёт через существующий сценарий v8.6.26.
subprocess.run([sys.executable, str(ROOT / 'verify_all_tech_report_v8626.py')], check=True)
md_path = ROOT / 'ALL_TECH_REPORT_v8_6_26_FINAL_AUDIT.md'
md = md_path.read_text(encoding='utf-8')
errors = []
def must(cond, msg):
    if not cond:
        errors.append(msg)

# Проверяем, что all-tech отчёт не выдаётся за линейный happy path.
must('карту множества интеграционных возможностей' in md, 'all-tech warning missing')
must('### Основной сценарий' not in md, 'all-tech has fake happy path')
must('Выполняется после:' not in md, 'all-tech step cards imply strict sequence')

# Проверяем старые классы логических ошибок.
for bad in [
    'Сервис процесса → Сервис процесса →',
    'Сервис процесса → Сервис процесса или весь процесс',
    'Audit journal → Audit journal',
    'Аналитическое хранилище → Внутренний сервис быстрых ответов',
    'Основной способ взаимодействия: Аналитическое хранилище',
    'Основной способ взаимодействия: Data Warehouse',
    'Основной способ взаимодействия: Озеро данных',
    'Классифицировать и маскировать чувствительные поля». Основной способ взаимодействия: REST API',
    'Записать неизменяемый audit journal». Основной способ взаимодействия: Основная база данных',
    'Основной способ взаимодействия: Обратный вызов.\n**Где:** связь идёт от «Сервис процесса» к «Внешний партнёр»',
]:
    must(bad not in md, f'logic leftover: {bad}')

# Остатки машинного языка, которые ранее всплывали в отчётах.
for bad in [
    'попыткамии', 'лимит запросовing', 'лимит запросовs', 'table', "{'tables'",
    'Payload', 'payload', 'повторная обработка должен', 'повторная попытка должен',
    'каждый повторная попытка', 'коммитьте позиция', 'неизменяемый модель',
    'documentation', 'repair/compaction', 'throughput', 'cross-shard', 'hot partition',
    'standard-очереди', 'проверка горячая партиция', 'сценариях доступа',
    'транзакционная таблица исходящих', 'outbox/inbox', 'строгой outbox', 'outbox-записей',
]:
    must(bad not in md, f'language leftover: {bad}')

# Должны быть ключевые разделы.
for section in [
    '## Короткий человеческий вывод', '## Что блокирует запуск', '## Рекомендуемый порядок действий',
    '## Почему выбраны технологии и способы взаимодействия', '## Сквозные контроли и служебные компоненты',
    '## Сценарная основа для дальнейшей разработки', '## Диаграммы процесса'
]:
    must(section in md, f'missing section: {section}')

must(md.count('```mermaid') >= 3, 'mermaid diagrams missing')

if errors:
    print('FINAL_REPORT_CONFIDENCE_v8627 FAILED')
    for e in errors:
        print('-', e)
    print('report:', md_path)
    sys.exit(1)

out = ROOT / 'ALL_TECH_REPORT_v8_6_27_FINAL_CHECK.md'
out.write_text(md, encoding='utf-8')
print(f'FINAL_REPORT_CONFIDENCE_v8627 ok: lines={len(md.splitlines())} report={out}')
