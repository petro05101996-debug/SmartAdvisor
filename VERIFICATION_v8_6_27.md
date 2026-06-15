# Verification v8.6.27

Финальная проверка отчёта после ручной вычитки v8.6.26.

## Что исправлено

- Убрана последняя неудачная формулировка в сценариях сквозных контролей: `Сервис процесса → Сервис процесса или весь процесс`.
- Для сквозных контролей теперь показывается либо реальный компонент контроля, либо `весь процесс`, без ложного self-loop.
- Добавлена проверка `verify_final_report_confidence_v8627.py`.

## Проверки

```text
python run_tests.py
68/68 passed

pytest -q -rs
31 passed

python verify_report_logic_no_contradictions_v8620.py
REPORT_LOGIC_v8620 ok: payloads=7 checked_steps=104

python verify_readable_report_v8622.py
READABLE_REPORT_v8622 ok

python verify_diagrams_v8623.py
DIAGRAMS_v8623 ok: diagrams=3

python verify_scenarios_v8624.py
SCENARIOS_v8624 ok

python verify_report_sections_v8625.py
REPORT_SECTIONS_v8625 ok: sections=17 lines=1577 steps=58

python verify_all_tech_report_v8626.py
ALL_TECH_REPORT_v8626 ok: lines=1577 steps=58 findings=80

python verify_final_report_confidence_v8627.py
FINAL_REPORT_CONFIDENCE_v8627 ok: lines=1577
```
