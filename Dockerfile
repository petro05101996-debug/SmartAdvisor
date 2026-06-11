FROM python:3.11-slim

WORKDIR /app

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8110

EXPOSE 8110

CMD ["python", "app.py"]
