"""Logging estructurado JSON con `request_id` (TEC-08, doc 05 §8).

Cada request lleva un `request_id` (lo fija el middleware, ver main.py) que se
propaga a todos los logs vía `structlog.contextvars`. En local se puede usar
salida de consola legible; en prod/CI, JSON.
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import Settings


def configurar_logging(settings: Settings) -> None:
    """Configura structlog una vez, al arrancar la app."""
    nivel = getattr(logging, settings.log_nivel.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=nivel)

    procesadores: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.log_json:
        procesadores.append(structlog.processors.JSONRenderer())
    else:
        procesadores.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=procesadores,
        wrapper_class=structlog.make_filtering_bound_logger(nivel),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def nuevo_request_id() -> str:
    return str(uuid.uuid4())


def vincular_contexto_request(request_id: str, **extra: object) -> None:
    """Vincula request_id (y datos como usuario/natillera) al contexto de logs."""
    bind_contextvars(request_id=request_id, **extra)


def limpiar_contexto_request() -> None:
    clear_contextvars()


def obtener_logger(nombre: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(nombre)  # type: ignore[no-any-return]
