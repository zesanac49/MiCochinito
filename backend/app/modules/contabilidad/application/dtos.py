"""DTOs de lectura del módulo contabilidad (CQRS-lite, doc 05 §4).

Las lecturas devuelven estos DTOs (no agregados de dominio ni modelos ORM), lo
que mantiene el dominio puro y evita filtrar SQLAlchemy hacia la API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.shared.domain.dinero import Dinero


@dataclass(frozen=True, slots=True)
class AsientoLeido:
    uuid: str
    creado_en: datetime
    fondo: TipoFondo
    naturaleza: Naturaleza
    concepto: ConceptoContable
    monto: Dinero
    descripcion: str
    origen_tipo: str
    origen_id: int
    participante_id: int | None
    id: int | None = None  # id interno (para enlazar cuota↔asiento); no se expone en API


@dataclass(frozen=True, slots=True)
class SaldoFondo:
    fondo: TipoFondo
    saldo: Dinero


@dataclass(frozen=True, slots=True)
class SaldosCuentaCorriente:
    """Saldos por concepto de un participante (proyección, RF-203)."""

    ahorros: Dinero
    intereses_pagados: Dinero
    multas_pagadas: Dinero


@dataclass(frozen=True, slots=True)
class LineaReconciliacion:
    fondo: TipoFondo
    saldo_ledger: Dinero
    saldo_cache: Dinero

    @property
    def cuadra(self) -> bool:
        return self.saldo_ledger == self.saldo_cache


@dataclass(frozen=True, slots=True)
class ReporteReconciliacion:
    lineas: list[LineaReconciliacion]

    @property
    def cuadra(self) -> bool:
        return all(linea.cuadra for linea in self.lineas)
