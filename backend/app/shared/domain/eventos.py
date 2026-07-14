"""Base de eventos de dominio (doc 02 §6, TEC-05).

Los hechos de negocio relevantes se modelan como eventos inmutables. El bus
síncrono (core/eventbus) los despacha dentro de la misma transacción (UoW).
Los traspasos al Fondo de Rentabilidad se disparan por estos eventos, no por
llamadas directas dispersas.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EventoDeDominio:
    """Marca base de todos los eventos de dominio.

    Inmutable (frozen). Las subclases agregan sus datos como campos frozen.
    No incluye timestamp: el reloj es una dependencia inyectada en la capa de
    aplicación (el dominio no lee la hora del sistema, para ser testeable).
    """

    natillera_id: int = field(kw_only=True)
