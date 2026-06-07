# Mixed complex cases core fix

Что исправлено:
- добавлена модель `primary_specialized_case + secondary_modifiers`;
- вторичные признаки `multi_tenant/highload/pii/regulatory/active_active` больше не заменяют главный сценарий;
- схема строится по primary, modifiers расширяют must-have/risks/handoff;
- readiness учитывает business-first поля;
- ограничения выводятся человеческим языком, а не сырыми flags;
- technical details соответствуют primary case;
- custom technical chain сохраняет высший приоритет над canonical schema.

Проверка:
- `python -m pytest -q` → 163 passed, 24 skipped.
- Browser tests в текущем окружении не были прокликаны, потому что Chromium для Playwright не установлен; сами browser tests остаются в проекте и запускаются при наличии Chromium.
