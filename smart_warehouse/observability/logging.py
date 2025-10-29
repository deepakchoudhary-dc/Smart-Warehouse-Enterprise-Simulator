"""Structured logging configuration for the Smart Warehouse platform."""

from __future__ import annotations

import logging
import sys
from typing import Any, Dict

import structlog

from smart_warehouse.enterprise.config.settings import LoggingSettings


def _build_structlog_processors(json_output: bool) -> list[structlog.types.Processor]:
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    return processors


def configure_logging(settings: LoggingSettings) -> None:
    """Configure stdlib + structlog logging based on settings."""

    level = getattr(logging, settings.level.upper(), logging.INFO)
    json_output = settings.json

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=_build_structlog_processors(json_output),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def bind_global_context(**context: Any) -> Dict[str, Any]:
    """Bind context vars that should be included in all subsequent logs."""

    structlog.contextvars.bind_contextvars(**context)
    return context
