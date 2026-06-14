# Проверка конструктора и автоподбора стека — v8.4.9

## Что проверено

1. Синтаксис Python и JavaScript.
2. Базовые unit/regression тесты ядра.
3. Pytest по UI/semantic/auto-route/auto-stack.
4. Матрица action grammar: 2880 базовых конфигураций.
5. Проверка именно фактического JS/UI-слоя: 2880 конфигураций, собранных через функции UI `composeChainFromChoices()` и `buildSubmissionPayload()`.
6. Надстройки сложности: single/pairwise на 4 seed-сценариях.
7. Все подмножества 10 надстроек на hard seed: 1024 сценария.
8. Проверка ссылочной целостности: нет шагов на отсутствующие системы, нет self-dependency, нет ссылок на несуществующие шаги.
9. Проверка ручного override канала: ручной SOAP сохраняется при перемещении шага, а `вернуть автоподбор` возвращает REST.
10. HTTP smoke: `/`, `/health`, `/api/analyze`.

## Найденное и исправленное

В v8.4.8 для сценариев `результат позже / дождаться статуса` UI часто выбирал Kafka как дефолтный канал входа результата от внешней системы.
Это технически возможно только если есть адаптер/интеграционная шина, но для внешнего партнёра более естественный безопасный дефолт — callback/webhook с подписью, timestamp/nonce и дедупликацией.

Исправлено в v8.4.9:

- поздний внешний результат теперь по умолчанию создаётся как `callback/webhook`;
- следующая стадия дедупликации и обновления истории идёт в БД;
- Kafka остаётся для событий, DLQ/replay, outbox/inbox, legacy/event-потоков и надстроек;
- эксперт всё ещё может вручную переопределить канал на Kafka/SOAP/Batch/файл, если это реальное ограничение инфраструктуры.

## Результаты

```text
python -m py_compile app.py engine.py report.py design_patterns.py invariant_catalog.py ui.py
OK
```

```text
python run_tests.py
68/68 passed
```

```text
pytest -q -rs
13 passed, 2 skipped
```

`2 skipped` — browser/Playwright без установленного Chromium в окружении.

```text
python verify_action_grammar_matrix.py
checked=2880 failures=0 colors={'green': 420, 'yellow': 2400, 'red': 60}
```

Фактический JS/UI-слой:

```text
baseCount=2880
issues=0
moduleCaseCount=220
moduleIssues=0
subsetChecked=1024
subsetIssues=0
```

Распределение каналов в базовой UI-матрице:

```text
db: 7488
rest: 3840
batch: 1632
callback: 1680
```

Для позднего результата:

```text
callbackLater=1680
kafkaLater=0
```

То есть внешний поздний результат больше не превращается по умолчанию в Kafka.

Фактические UI payload через `analyze()`:

```text
actual_ui_analyze=3100
fail=0
colors={'green': 588, 'yellow': 2136, 'red': 376}
score_avg=6.7
min=0.0
max=9.0
```

Каналы в проанализированных UI payload:

```text
db: 8348
rest: 4486
batch: 1877
callback: 1790
kafka: 84
cdc: 40
```

Ручное переопределение:

```text
before:     rest, manual=no
afterMove:  soap, manual=yes
afterReset: rest, manual=no
```

HTTP smoke:

```text
GET /        200
GET /health  200
POST /api/analyze 200
```

## Вывод

Конструктор работает, автоподбор стека стал адекватнее:

- пользователь не выбирает Kafka/REST как основной путь;
- REST подбирается для синхронных внешних вызовов;
- callback/webhook подбирается для позднего внешнего результата;
- БД подбирается для сохранения/обновления состояния;
- Batch подбирается для файла, расписания, сверки и DWH/DQ;
- CDC подбирается для передачи изменений в аналитику;
- Kafka остаётся для event-flow, DLQ/replay, outbox/inbox и event/legacy надстроек;
- ручное переопределение сохраняется, но не является основным пользовательским путём.
