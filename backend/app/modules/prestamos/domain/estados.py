"""Máquina de estados del préstamo (RN-032, doc 02 §4.4)."""

from __future__ import annotations

from enum import Enum


class EstadoPrestamo(str, Enum):
    SOLICITADO = "SOLICITADO"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    DESEMBOLSADO = "DESEMBOLSADO"
    EN_PAGO = "EN_PAGO"
    EN_MORA = "EN_MORA"
    PAGADO = "PAGADO"


E = EstadoPrestamo

# Transiciones válidas (RN-032). EN_MORA <-> EN_PAGO es reversible.
TRANSICIONES: dict[EstadoPrestamo, frozenset[EstadoPrestamo]] = {
    E.SOLICITADO: frozenset({E.APROBADO, E.RECHAZADO}),
    E.APROBADO: frozenset({E.DESEMBOLSADO}),
    E.RECHAZADO: frozenset(),
    E.DESEMBOLSADO: frozenset({E.EN_PAGO}),
    E.EN_PAGO: frozenset({E.EN_MORA, E.PAGADO}),
    E.EN_MORA: frozenset({E.EN_PAGO, E.PAGADO}),
    E.PAGADO: frozenset(),
}


def transicion_valida(desde: EstadoPrestamo, hacia: EstadoPrestamo) -> bool:
    return hacia in TRANSICIONES.get(desde, frozenset())
