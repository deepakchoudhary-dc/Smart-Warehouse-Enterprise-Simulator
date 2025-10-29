"""FastAPI application exposing simulation services."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from smart_warehouse.enterprise.config.settings import get_settings
from smart_warehouse.observability import configure_logging, configure_tracer
from smart_warehouse.observability.metrics import REQUEST_COUNTER
from smart_warehouse.server.api.routers import (
	analytics_router,
	health_router,
	observability_router,
	robots_router,
	scenarios_router,
	simulation_router,
)

settings = get_settings()
configure_logging(settings.logging)
configure_tracer("smart-warehouse-api", settings.telemetry.otlp_endpoint)

app = FastAPI(title="Smart Warehouse API", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def count_requests(request: Request, call_next):
	REQUEST_COUNTER.inc()
	response = await call_next(request)
	return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(simulation_router, prefix="/api/v1")
app.include_router(robots_router, prefix="/api/v1")
app.include_router(observability_router, prefix="/api/v1")
app.include_router(scenarios_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
	return {"message": "Smart Warehouse API"}
