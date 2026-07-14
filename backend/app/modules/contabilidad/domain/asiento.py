"""`Asiento` — registro inmutable de un hecho financiero (INV-11, doc 02 §4.3).

El monto es siempre positivo (`Dinero`); el signo contable lo da la
`naturaleza` (DEBITO/CREDITO). El asiento apunta a su origen
(`ReferenciaOrigen`, RN-062) y, si es una reversión, al asiento revertido
(`reversa_de_id`, RN-061). No tiene setters: una vez creado no cambia.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.referencia import ReferenciaOrigen


@dataclass(frozen=True, slots=True)
class Asiento:
    """Asiento inmutable del ledger. Igualdad estructural por valor."""

    monto: Dinero
    naturaleza: Naturaleza
    concepto: ConceptoContable
    fondo: TipoFondo
    referencia: ReferenciaOrigen
    descripcion: str
    participante_id: int | None = None
    periodo_id: int | None = None
    reversa_de_id: int | None = None
    id: int | None = field(default=None)

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Dinero):
            raise ErrorDeValidacionDeDominio("El monto de un asiento debe ser Dinero.")
        if not self.monto.es_positivo():
            raise ErrorDeValidacionDeDominio(
                "El monto de un asiento debe ser positivo; el signo lo da la "
                "naturaleza (INV-11).",
                {"monto": self.monto.como_str()},
            )
        if not self.descripcion.strip():
            raise ErrorDeValidacionDeDominio("El asiento requiere descripción.")
