# Timeweb deploy checklist

## Перед деплоем

- Dockerfile лежит в корне проекта.
- Приложение слушает `HOST=0.0.0.0`.
- Порт берётся из переменной `PORT`, по умолчанию `8110`.
- В Dockerfile указан `EXPOSE 8110`.
- Healthcheck ходит на `/`.
- `.dockerignore` исключает кэш, локальную SQLite-базу и сгенерированные отчёты из Docker build context.
- `.gitignore` исключает runtime-файлы: `.integration_architect_pro/*.sqlite3` и `generated_integration_architect_reports/`.
- Для production-хранения SQLite/generated_reports лучше подключить volume или заменить на внешнее хранилище, если нужно сохранять историю между redeploy.

## Локальная проверка

```bash
python -m pip install -r requirements-dev.txt
python -m py_compile integration_architect_pro.py
python -m pytest -q
python integration_architect_pro.py
```

Открыть:

```text
http://127.0.0.1:8110/
```


## Docker smoke-check

```bash
docker build -t integration-architect-pro .
docker run --rm -p 8110:8110 integration-architect-pro
```

После запуска проверьте `http://localhost:8110/`. Для другого порта используйте, например, `docker run --rm -e PORT=8080 -p 8080:8080 integration-architect-pro`.

## CI gate

GitHub Actions workflow `.github/workflows/ci.yml` запускает `py_compile` и весь `pytest` regression suite на Python 3.11 при `push`, `pull_request` и ручном запуске.
