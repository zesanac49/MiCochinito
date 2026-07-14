"""Dependencias transversales de FastAPI (doc 05 §2).

`obtener_settings` lee la configuración desde `app.state`, de modo que la
aplicación creada con `crear_app(settings)` es autoritativa para SU configuración
(incluye el secreto JWT). Así los tests pueden crear apps con settings propios
sin chocar con el singleton global de entorno.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.eventbus import BusDeEventos, BusDeEventosEnMemoria


def obtener_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if isinstance(settings, Settings):
        return settings
    return get_settings()


def obtener_session(request: Request) -> Iterator[Session]:
    """Cede una sesión de BD por request (se cierra al terminar)."""
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise RuntimeError("session_factory no configurada en la app.")
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def obtener_bus(request: Request) -> BusDeEventos:
    bus: BusDeEventos | None = getattr(request.app.state, "bus", None)
    return bus if bus is not None else BusDeEventosEnMemoria()
