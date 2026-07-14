"""Estrategias de distribución de la rentabilidad (RN-073, PA-01).

Tres estrategias intercambiables. Postcondición común: la suma de las
participaciones es EXACTAMENTE el saldo del Fondo de Rentabilidad; el residuo por
redondeo se asigna al participante de mayor participación.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


@dataclass(frozen=True, slots=True)
class ParticipanteLiquidable:
    participante_id: int
    ahorros: Dinero
    meses_permanencia: int


def _repartir(fondo: Dinero, pesos: dict[int, Decimal]) -> dict[int, Dinero]:
    """Reparte `fondo` según `pesos`, garantizando suma exacta == fondo."""
    if not pesos:
        return {}
    total = sum(pesos.values(), Decimal(0))
    if total == 0:  # pesos degenerados (p. ej. sin ahorros) => partes iguales
        pesos = {k: Decimal(1) for k in pesos}
        total = Decimal(len(pesos))
    partes: dict[int, Dinero] = {
        pid: Dinero(fondo.monto * peso / total) for pid, peso in pesos.items()
    }
    suma = Dinero.cero()
    for p in partes.values():
        suma = suma + p
    residuo = fondo - suma
    if not residuo.es_cero():
        pid_max = max(partes, key=lambda k: partes[k].monto)
        partes[pid_max] = partes[pid_max] + residuo
    return partes


class EstrategiaDistribucion(Protocol):
    def distribuir(
        self, fondo: Dinero, participantes: list[ParticipanteLiquidable]
    ) -> dict[int, Dinero]: ...


class PartesIguales:
    def distribuir(
        self, fondo: Dinero, participantes: list[ParticipanteLiquidable]
    ) -> dict[int, Dinero]:
        return _repartir(fondo, {p.participante_id: Decimal(1) for p in participantes})


class ProporcionalAlAhorro:
    def distribuir(
        self, fondo: Dinero, participantes: list[ParticipanteLiquidable]
    ) -> dict[int, Dinero]:
        return _repartir(fondo, {p.participante_id: p.ahorros.monto for p in participantes})


class ProporcionalPonderadaPorTiempo:
    def distribuir(
        self, fondo: Dinero, participantes: list[ParticipanteLiquidable]
    ) -> dict[int, Dinero]:
        return _repartir(
            fondo,
            {p.participante_id: p.ahorros.monto * p.meses_permanencia for p in participantes},
        )


_ESTRATEGIAS: dict[str, EstrategiaDistribucion] = {
    "PARTES_IGUALES": PartesIguales(),
    "PROPORCIONAL_AHORRO": ProporcionalAlAhorro(),
    "PROPORCIONAL_TIEMPO": ProporcionalPonderadaPorTiempo(),
}


def crear_estrategia(nombre: str) -> EstrategiaDistribucion:
    estrategia = _ESTRATEGIAS.get(nombre)
    if estrategia is None:
        raise ErrorDeValidacionDeDominio(
            "Estrategia de distribución desconocida.", {"nombre": nombre}
        )
    return estrategia
