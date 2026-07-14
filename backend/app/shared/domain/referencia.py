"""Value object `ReferenciaOrigen` — todo asiento apunta a su origen (RN-062).

Identifica el agregado de negocio que causó un hecho financiero (cuota,
préstamo, actividad, multa, liquidación...). Se guarda en el ledger como par
(origen_tipo, origen_id) — doc 04 §3.4.
"""

from __future__ import annotations

from enum import Enum

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


class TipoOrigen(str, Enum):
    """Tipos de agregado que pueden originar un asiento (doc 04 §3.4)."""

    CUOTA = "CUOTA"
    PRESTAMO = "PRESTAMO"
    PAGO_PRESTAMO = "PAGO_PRESTAMO"
    ACTIVIDAD = "ACTIVIDAD"
    MULTA = "MULTA"
    LIQUIDACION = "LIQUIDACION"
    REVERSION = "REVERSION"
    APORTE_EXTRAORDINARIO = "APORTE_EXTRAORDINARIO"


class ReferenciaOrigen:
    """Referencia inmutable (tipo, id) al agregado de origen de un asiento."""

    __slots__ = ("_tipo", "_id")
    _tipo: TipoOrigen
    _id: int

    def __init__(self, tipo: TipoOrigen, id_origen: int) -> None:
        if not isinstance(tipo, TipoOrigen):
            raise ErrorDeValidacionDeDominio(
                "tipo debe ser un TipoOrigen.", {"tipo": repr(tipo)}
            )
        if isinstance(id_origen, bool) or not isinstance(id_origen, int) or id_origen <= 0:
            raise ErrorDeValidacionDeDominio(
                "id_origen debe ser un entero positivo.", {"id_origen": repr(id_origen)}
            )
        object.__setattr__(self, "_tipo", tipo)
        object.__setattr__(self, "_id", id_origen)

    @property
    def tipo(self) -> TipoOrigen:
        return self._tipo

    @property
    def id_origen(self) -> int:
        return self._id

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorDeValidacionDeDominio("ReferenciaOrigen es inmutable.")

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, ReferenciaOrigen):
            return NotImplemented
        return (self._tipo, self._id) == (otro._tipo, otro._id)

    def __hash__(self) -> int:
        return hash((self._tipo, self._id))

    def __repr__(self) -> str:
        return f"ReferenciaOrigen({self._tipo.value}, {self._id})"
