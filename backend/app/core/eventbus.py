"""Bus de eventos de dominio síncrono en memoria (TEC-05, doc 02 §6).

Los handlers se ejecutan dentro de la MISMA transacción que produjo el evento
(los invoca el Unit of Work al hacer commit). La interfaz `BusDeEventos` deja
la puerta abierta a un despacho asíncrono (outbox/colas) sin tocar el dominio.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

from app.shared.domain.eventos import EventoDeDominio

E = TypeVar("E", bound=EventoDeDominio)
Handler = Callable[[EventoDeDominio], None]


class BusDeEventos(Protocol):
    """Puerto del bus de eventos."""

    def suscribir(self, tipo: type[EventoDeDominio], handler: Handler) -> None: ...

    def publicar(self, evento: EventoDeDominio) -> None: ...


class BusDeEventosEnMemoria:
    """Implementación síncrona. Despacha por tipo exacto de evento."""

    def __init__(self) -> None:
        self._handlers: dict[type[EventoDeDominio], list[Handler]] = {}

    def suscribir(self, tipo: type[EventoDeDominio], handler: Handler) -> None:
        self._handlers.setdefault(tipo, []).append(handler)

    def publicar(self, evento: EventoDeDominio) -> None:
        for handler in self._handlers.get(type(evento), []):
            handler(evento)
