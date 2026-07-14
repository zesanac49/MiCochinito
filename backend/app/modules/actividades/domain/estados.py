"""Enumeraciones y máquina de estados de actividades (doc 02 §4.5, RN-040/043)."""

from __future__ import annotations

from enum import Enum


class TipoActividad(str, Enum):
    POLLA = "POLLA"
    RIFA = "RIFA"
    BINGO = "BINGO"
    BAZAR = "BAZAR"
    VENTA = "VENTA"
    OTRO = "OTRO"


class EstadoActividad(str, Enum):
    BORRADOR = "BORRADOR"
    ABIERTA = "ABIERTA"
    SORTEADA = "SORTEADA"  # sorteada/realizada
    CERRADA = "CERRADA"


class TipoMovimiento(str, Enum):
    INGRESO = "INGRESO"
    GASTO = "GASTO"
    PREMIO = "PREMIO"


E = EstadoActividad

# Transiciones válidas (RN-043). Solo CERRADA afecta el Fondo de Rentabilidad.
TRANSICIONES: dict[EstadoActividad, frozenset[EstadoActividad]] = {
    E.BORRADOR: frozenset({E.ABIERTA}),
    E.ABIERTA: frozenset({E.SORTEADA, E.CERRADA}),
    E.SORTEADA: frozenset({E.CERRADA}),
    E.CERRADA: frozenset(),
}


def transicion_valida(desde: EstadoActividad, hacia: EstadoActividad) -> bool:
    return hacia in TRANSICIONES.get(desde, frozenset())
