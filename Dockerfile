FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8110 \
    MAX_POST_BYTES=2097152 \
    APP_DIR=/tmp/architect6

WORKDIR /app
COPY . /app

RUN mkdir -p /tmp/architect6 \
    && chmod 777 /tmp/architect6 \
    && adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app /tmp/architect6

USER appuser

EXPOSE 8110

# Timeweb/App Platform может иметь собственный probe; приложение отдаёт /readyz.
HEALTHCHECK NONE

CMD ["python", "-u", "app.py"]
