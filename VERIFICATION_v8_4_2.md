# Проверка v8.4.2 coverage verified

Проверка выполнена для входа через action grammar: старт + действие + характер результата + обработка результата + число систем.

## Что проверено

- Все базовые комбинации конфигуратора: 5 стартов × 6 действий × 4 варианта результата по времени × 6 действий с результатом × 4 масштаба = 2880 конфигураций.
- Надстройки сложности: DWH, legacy, ручная сверка, enrichment, fan-in/join, retry/DLQ/replay, audit, outbox/inbox, contract migration, security.
- Single-модули на 8 seed-конфигурациях: 80 прогонов.
- Pairwise-модули на 8 seed-конфигурациях: 360 прогонов.
- Все 1024 подмножества модулей на самом неопределённом hard-seed: unknown start + wait_status + unknown timing + unknown result + unknown system count.
- Регрессионные тесты ядра: 68/68 passed.
- Pytest UI/semantic smoke: 5 passed, 2 skipped. Skipped только browser Playwright из-за отсутствия Chromium в окружении.
- Python compile и JS syntax check пройдены.

## Результат

- Падений analyze(payload) не найдено.
- Пустых systems/steps не найдено.
- Синхронных шагов без timeout не найдено.
- Асинхронных шагов без recovery не найдено.
- Генерация сценариев, DDL, checklist и артефактов доступна для проверенных payload.
- Старые плохие стартовые фразы из основного UI отсутствуют.

## Ограничение проверки

Полный декартов перебор всех base-конфигураций × всех 2^10 комбинаций модулей = 2 949 120 прогонов. Это слишком тяжёлая матрица для обычного CI. Вместо этого выполнены:

1. полный перебор всех base-конфигураций;
2. pairwise-покрытие модулей;
3. полный перебор всех модульных подмножеств на самом неопределённом hard-seed.

Это ловит основные классы поломок: пустые payload, несовместимость каналов, missing recovery, broken dependencies, schema/report/checklist generation.
