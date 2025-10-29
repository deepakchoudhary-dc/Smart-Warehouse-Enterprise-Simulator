"""Observability endpoints (metrics, traces)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

from smart_warehouse.observability.metrics import metrics_registry

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    data = generate_latest(metrics_registry)
    return PlainTextResponse(data, media_type="text/plain; version=0.0.4")
