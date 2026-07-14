"""Value object `Descomposicion` de un pago de préstamo (RN-033).

Un pago se parte en componente de capital (→ Fondo Ahorro) e interés (→ Fondo
Rentabilidad). Invariante: `capital + interes == pago`, ambos ≥ 0.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


@dataclass(frozen=True, slots=True)
class Descomposicion:
    capital: Dinero
    interes: Dinero

    def __post_init__(self) -> None:
        if self.capital.es_negativo() or self.interes.es_negativo():
            raise ErrorDeValidacionDeDominio("Componentes de pago no pueden ser negativos.")

    @property
    def total(self) -> Dinero:
        return self.capital + self.interes
