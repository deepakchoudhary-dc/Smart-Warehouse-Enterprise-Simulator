# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY smart_warehouse /app/smart_warehouse
COPY tests /app/tests

RUN pip install --upgrade pip && \
	pip install \
	  paho-mqtt \
	  pydantic \
	  pydantic-settings \
	  PyYAML \
	  python-dotenv \
	  fastapi \
	  uvicorn[standard] \
	  sqlalchemy[asyncio] \
	  asyncpg \
	  structlog \
	  prometheus-client \
	  opentelemetry-api \
	  opentelemetry-sdk \
	  opentelemetry-exporter-otlp \
	  opentelemetry-instrumentation-fastapi \
	  grpcio \
	  grpcio-tools \
	  googleapis-common-protos \
	  aio-pika

EXPOSE 8000

CMD ["uvicorn", "smart_warehouse.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
