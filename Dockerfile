FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8110 \
    MAX_POST_BYTES=2097152

WORKDIR /app
COPY . /app

RUN mkdir -p /tmp/architect6 && chmod 777 /tmp/architect6

EXPOSE 8110

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import os, urllib.request; port=os.environ.get('PORT','8110'); urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=3).read(200)" || exit 1

CMD ["python", "-u", "app.py"]
